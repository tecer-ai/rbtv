#!/usr/bin/env python
"""Router script — deterministic (model, variant, carrier) resolution from a task profile.

Reads a structured task-profile JSON on stdin or via --profile, resolves against
the live manifests on disk, and emits one machine-readable verdict:
  route {model, variant, carrier, effort?, other_routing_audit?}
  self_execute
  halt_seam {seam: <name>}

Decision flow: GATE -> RANK -> PIN over the comparable integer 1-7 axes
(reasoning / coding / cost) plus the routable_for role-eligibility gate, then
effort = f(boundedness) set AFTER the pin from the chosen variant's reasoning_modes.
See manifest-schema.md (the field source of truth) and
../../../2-areas/rbtv/model-benchmarking/5b-routing-build/specs/routing-rebuild-spec.md.

With --explain, also prints the enumerate->filter->rank trace.
Stdlib only. No network, clock, or randomness.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Capability + cost are now comparable INTEGERS 1-7 (manifest-schema.md §0), so there is
# no value-lookup table for them anymore (the old TIER_VALUES / COST_ORDER are removed):
# reasoning/coding are compared directly (7 = strongest); cost is compared directly and
# ranked ASCENDING (1 = cheapest, ranked first; 7 = priciest, ranked last / never auto-picked).
EVIDENCE_ORDER = ["validated", "probe-pending"]

# GATE reasoning floors per boundedness band (1-7 scale; designed at p2-1 for utilization
# diversity — a LOW floor on fully-bounded leaves lets many models qualify, so the
# cost-ascending RANK then picks the cheapest-capable and cheap models actually get used).
# The boundedness master cut (_scope_eligible_set) is the binding constraint for
# partially-/unbounded leaves (it scopes to Claude sonnet / opus); these floors are the
# numeric expression of the same band ordering and the floor used by the pinned-role logic.
REASONING_FLOOR_BY_BAND = {
    "fully-bounded": 1,       # every real reasoner qualifies -> cheapest-capable wins bounded work
    "partially-bounded": 6,   # sonnet-class and up (sonnet reasoning = 6); excludes haiku
    "unbounded": 7,           # top-tier only (opus reasoning = 7)
}

# GATE coding floors per boundedness band, applied ONLY to code leaves. Same diversity
# logic: a low floor on fully-bounded code lets the cheap code executors qualify.
CODING_FLOOR_BY_BAND = {
    "fully-bounded": 1,       # any code-eligible executor qualifies -> cheapest-capable wins
    "partially-bounded": 4,   # bounded-agentic-coder and up
    "unbounded": 5,           # capable-agentic-coder and up
}

# The two code-leaf roles (manifest-schema.md §2 closed routable_for vocabulary). A variant
# with a NON-EMPTY routable_for that omits BOTH of these is code-ineligible regardless of its
# coding score (D13: never let an honest coding score re-enable an ineligible code route).
CODE_ROLES = {"bounded-code", "unbounded-code"}

# Closed routable_for role vocabulary (manifest-schema.md §2; `judgment` removed per D12).
# Informational — an unknown role string the profile requests is treated as not-matching
# (the variant is dropped for that leaf), never a crash.
ROLE_VOCABULARY = {
    "bounded-code", "unbounded-code", "reasoning",
    "web-research", "text-synthesis", "other",
}

REQUIRED_PROFILE_FIELDS = [
    "boundedness",
    "task_type",          # "code" or "text"
    "inlined_context_size",
]

REQUIRED_VARIANT_FIELDS = [
    "variant", "reasoning", "context_window", "cost",
    "coding", "web_access",
]

SKIP_DIRS = {"_api", "_fixture", "mirror"}

# routing.md §2 STAKES filter: a `stakes` VALUE signalling irreversible or cross-cutting work
# tiers the pick UP one band ("Stakes override cheapness — a 'bounded' task with irreversible
# blast radius does not go to the cheapest worker"). The router normalizes these tokens into the
# existing `stakes_tier="tier_up"` trigger so the downstream tier-up path is reused verbatim.
# `stakes="unresolved"` is NOT here — it is the halt-seam (a decision the owner must take before
# routing), handled by _check_halt_seams; any other/absent value is a no-op.
STAKES_TIER_UP_TOKENS = {"irreversible", "cross-cutting"}

# Footprint-aware routing (spec Behavior 4): the window-utilization cap is read from rbtv.json
# (`window_utilization_cap`). When absent or malformed (non-numeric, or outside the open-closed
# range (0, 1]) the router falls back to this default and logs it. A worker passes the footprint
# GATE only if its effective window holds the known input at no more than `cap` utilization, i.e.
# effective_window >= ceil(known_input_size / cap). At the default 0.20 that is window >= 5×input.
DEFAULT_WINDOW_UTILIZATION_CAP = 0.20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_vault_root() -> Path:
    """Walk up from this script to find the vault root (where rbtv.json lives)."""
    here = Path(__file__).resolve().parent
    # This script lives at 3-resources/tools/rbtv/orchestration/models/
    # Vault root is 4 levels up: models/ → orchestration/ → rbtv/ → tools/ → 3-resources/ → vault_root
    candidate = here
    for _ in range(10):
        if (candidate / "rbtv.json").exists():
            return candidate
        candidate = candidate.parent
    # Fallback: assume standard layout
    return here.parents[3]


def _load_rbtv_json(vault_root: Path) -> dict:
    path = vault_root / "rbtv.json"
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _resolve_window_cap(rbtv_cfg: dict, explain_log: list) -> float:
    """Resolve the window-utilization cap from rbtv.json (spec Behavior 4).

    Reads `window_utilization_cap`. Absent → default 0.20. A value that is non-numeric, or
    numeric but outside the open-closed interval (0, 1], → fall back to 0.20 and log a one-line
    note (never crash). The cap is a single workspace-global value, NOT a per-task profile field.
    Booleans are rejected (a bool is an int subclass in Python but is never a valid cap).
    """
    raw = rbtv_cfg.get("window_utilization_cap")
    if raw is None:
        return DEFAULT_WINDOW_UTILIZATION_CAP
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        explain_log.append({
            "stage": "footprint", "action": "cap_invalid",
            "value": raw, "fallback": DEFAULT_WINDOW_UTILIZATION_CAP,
            "reason": "window_utilization_cap not a number -- using default",
        })
        return DEFAULT_WINDOW_UTILIZATION_CAP
    cap = float(raw)
    if not (0.0 < cap <= 1.0):
        explain_log.append({
            "stage": "footprint", "action": "cap_invalid",
            "value": raw, "fallback": DEFAULT_WINDOW_UTILIZATION_CAP,
            "reason": "window_utilization_cap outside (0, 1] -- using default",
        })
        return DEFAULT_WINDOW_UTILIZATION_CAP
    return cap


def _load_model_plans(vault_root: Path, rbtv_cfg: dict) -> dict:
    """Load the model-plans YAML if the pointer exists and the file is readable.

    Returns a {model: {context_window, ...}} map keyed by package id — the shape
    _apply_plan_caps consumes (route.py only reads context_window from this file; per D14
    the file is cap-only). Graceful skip (empty dict) on absent pointer, unreadable file,
    or unparseable content. Read-path UNCHANGED per D14 (the cap stays in model-plans.yaml).
    """
    plans_file = rbtv_cfg.get("model_plans_file")
    if not plans_file:
        return {}
    plans_path = vault_root / plans_file
    try:
        return _parse_plans_yaml(plans_path)
    except (OSError, ValueError):
        return {}


def _parse_plans_yaml(path: Path) -> dict:
    """Parse the model-plans file (a YAML list of plan entries under `plans:`).

    Per model-plans-schema.md the file shape is:
        plans:
          - model: codex
            plan_name: basic
            context_window: 200000
            ...
    Returns {model_id: {field: value, ...}} keyed by the entry's `model`. Entries
    whose `model` is missing/blank are skipped (no key to attach them to). Stdlib
    only — no PyYAML dependency. Fields left blank (e.g. `# TODO owner`) parse to
    None and are simply absent-valued, so an unfilled template applies no caps.
    """
    result: dict = {}
    current: dict = {}

    def _flush():
        model_id = current.get("model")
        if model_id:
            entry = {k: v for k, v in current.items() if k != "model"}
            result[model_id] = entry

    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip()
            stripped = line.strip()
            # Skip blanks, comments, and the YAML document marker
            if not stripped or stripped.startswith("#") or stripped == "---":
                continue
            # The top-level `plans:` key itself carries no value — ignore it
            if stripped == "plans:" or stripped.rstrip(":") == "plans":
                continue
            # A new list item starts a new plan entry. The dash may carry the
            # first field inline (e.g. "- model: codex").
            if stripped.startswith("-"):
                _flush()
                current = {}
                inline = stripped[1:].strip()  # drop the leading dash
                if inline:
                    key, _, val = inline.partition(":")
                    current[key.strip()] = _yaml_value(val.strip())
                continue
            # A continuation field of the current entry
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                current[key.strip()] = _yaml_value(val.strip())
    _flush()
    return result


def _yaml_value(s: str):
    """Convert a YAML scalar string to a Python value."""
    if not s:
        return None
    s = s.strip()
    if s.startswith("#"):
        return None
    # Strip inline comment
    if " #" in s:
        s = s[:s.index(" #")].strip()
    # Inline list, e.g. [bounded-code, reasoning] or []
    if s.startswith("[") and s.endswith("]"):
        return _parse_inline_list(s)
    # Quoted strings
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    # Booleans
    if s.lower() in ("true", "yes"):
        return True
    if s.lower() in ("false", "no"):
        return False
    # Numbers
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _parse_inline_list(s: str) -> list:
    """Parse a YAML inline (flow) list, e.g. `[bounded-code, reasoning]` -> [...].

    Grown at p2-1 so the manifest parser handles the new inline-list fields:
    routable_for (e.g. [web-research]) and reasoning_modes.depths (e.g. [low, medium, high]).
    Stdlib only. `[]` -> []. Each element is run through _yaml_value (minus the list branch)
    so quoted/typed elements convert; unquoted role/depth strings stay strings.
    """
    inner = s[1:-1].strip()
    if not inner:
        return []
    items = []
    for raw in inner.split(","):
        item = raw.strip()
        if not item:
            continue
        # Strip quotes on individual elements
        if (item.startswith('"') and item.endswith('"')) or (item.startswith("'") and item.endswith("'")):
            items.append(item[1:-1])
            continue
        # Try numeric, else keep as bare string (role names, depth labels)
        try:
            items.append(int(item))
            continue
        except ValueError:
            pass
        try:
            items.append(float(item))
            continue
        except ValueError:
            pass
        items.append(item)
    return items


def _split_flow_items(inner: str) -> list:
    """Split a flow collection's inner text on top-level commas only.

    Respects nesting (`[...]`, `{...}`) and quotes (`"..."`, `'...'`) so a comma
    inside a nested list, nested map, or quoted scalar does NOT split the item.
    e.g. `depths: [low, high], invocation: "a, b"` -> two items, not four.
    """
    items = []
    buf = []
    depth = 0
    quote = ""
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = ""
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
            continue
        if ch in ("[", "{"):
            depth += 1
            buf.append(ch)
            continue
        if ch in ("]", "}"):
            depth = max(0, depth - 1)
            buf.append(ch)
            continue
        if ch == "," and depth == 0:
            items.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        items.append(tail)
    return items


def _parse_inline_map(s: str) -> dict:
    """Parse a YAML inline (flow) map, e.g. `{method: none, required: false}` -> {...}.

    Grown at p2-1 review so the manifest parser NEVER stores a flow-map carried on a
    map-key (e.g. `auth: {method: none}`, `reasoning_modes: {depths: [low, high]}`) as a
    RAW STRING — a raw string later gets `.get()`'d (e.g. _get_auth_method) and crashes
    (manifest-schema.md §4 + spec Edge Cases require LOG + degrade, never raise). Each
    value runs through _yaml_value, so nested inline lists (`depths: [low, high]`), quoted
    strings, bools, and numbers convert. `{}` -> {}. A malformed/non-flow-map input that
    cannot be split into `key: value` pairs degrades to {} (no crash). Stdlib only.
    """
    inner = s.strip()
    if inner.startswith("{") and inner.endswith("}"):
        inner = inner[1:-1].strip()
    if not inner:
        return {}
    out: dict = {}
    for pair in _split_flow_items(inner):
        if ":" not in pair:
            # Not a key: value pair — skip it rather than crash (degrade, never raise).
            continue
        key, _, val = pair.partition(":")
        key = key.strip()
        # Strip quotes on the key
        if (key.startswith('"') and key.endswith('"')) or (key.startswith("'") and key.endswith("'")):
            key = key[1:-1]
        if key:
            out[key] = _yaml_value(val.strip())
    return out


def _load_manifest(manifest_path: Path) -> dict:
    """Parse a manifest YAML file (minimal parser, stdlib only)."""
    try:
        return _parse_manifest_yaml(manifest_path)
    except (OSError, ValueError):
        return {}


def _parse_manifest_yaml(path: Path) -> dict:
    """Parse the manifest YAML structure we care about: model, evidence_status, variants[]."""
    result: dict = {"variants": []}
    current_variant: dict = {}
    in_variants = False
    current_map_key: str = ""  # e.g. "headless", "auth", "tool_surface", "reasoning_modes"
    current_map_value: dict = {}

    MAP_KEYS = {
        "headless", "auth", "tool_surface", "confinement",
        "swarm_support", "configurable_model", "guidance_file", "os_quirks",
        "reasoning_modes", "axis_evidence",
    }
    SCALAR_KEYS = {
        "specialty", "failure_modes", "invocation_pointer",
        "manual_path", "delta_path", "rate_budget_notes",
        "reasoning", "context_window", "max_output",
        "cost", "coding", "web_access",
        "multimodal", "parallel_safe", "resume_support",
        "evidence_status", "variant", "available",
        "routable_for", "display", "cost_evidence",
    }
    ALL_VARIANT_KEYS = MAP_KEYS | SCALAR_KEYS

    def _flush_variant():
        nonlocal current_map_key, current_map_value
        _flush_map()
        if current_variant:
            result["variants"].append(current_variant)

    def _flush_map():
        nonlocal current_map_key, current_map_value
        if current_map_key:
            if current_variant:
                current_variant[current_map_key] = dict(current_map_value)
            current_map_key = ""
            current_map_value = {}

    def _get_indent(line: str) -> int:
        return len(line) - len(line.lstrip())

    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip()
            stripped = line.strip()
            # Skip comments and blank lines
            if not stripped or stripped.startswith("#"):
                continue

            indent = _get_indent(line)

            # Top-level keys (indent == 0, no dash)
            if indent == 0 and ":" in stripped and not stripped.startswith("-"):
                _flush_variant()
                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()
                if key == "model":
                    result["model"] = _yaml_value(val)
                elif key == "evidence_status":
                    result["evidence_status"] = _yaml_value(val)
                elif key == "variants":
                    in_variants = True
                continue

            # Inside variants block
            if in_variants:
                # Detect variant list items (e.g. "  - variant: opus")
                if stripped.startswith("- variant:"):
                    _flush_variant()
                    val = stripped[len("- variant:"):].strip()
                    current_variant = {"variant": _yaml_value(val)}
                    current_map_key = ""
                    current_map_value = {}
                    continue

                if current_variant:
                    # Indented sub-keys of a map (e.g. "      required: false" under "auth:",
                    # or "      depths: [low, high]" under "reasoning_modes:"). The inline-list
                    # value parses via _yaml_value (e.g. depths -> [low, high]).
                    if current_map_key and indent >= 6 and ":" in stripped:
                        sub_key, _, sub_val = stripped.partition(":")
                        sub_key = sub_key.strip()
                        sub_val = sub_val.strip()
                        if sub_val:
                            current_map_value[sub_key] = _yaml_value(sub_val)
                        continue

                    # Variant-level keys (indent 4, e.g. "    auth:" or "    routable_for: [...]")
                    if indent == 4 and ":" in stripped:
                        _flush_map()  # flush any previous map
                        key, _, val = stripped.partition(":")
                        key = key.strip()
                        val = val.strip()
                        if key in MAP_KEYS and not val:
                            # A map header with no inline value — collect its indented sub-keys.
                            current_map_key = key
                            current_map_value = {}
                        elif key in MAP_KEYS:
                            # A map-key carrying an INLINE value (e.g. `auth: {method: none}`,
                            # `reasoning_modes: {depths: [low, high]}`). It MUST become a dict —
                            # storing it as a raw string makes _get_auth_method (and any later
                            # .get() on the map) crash (manifest-schema.md §4 + spec Edge Cases:
                            # LOG + degrade, never raise). Parse a flow-map to a dict; any other
                            # unexpected inline value degrades to {} (the old no-crash behavior).
                            if val.startswith("{") and val.endswith("}"):
                                current_variant[key] = _parse_inline_map(val)
                            else:
                                current_variant[key] = {}
                        elif key in SCALAR_KEYS:
                            # Scalars and inline-list values (routable_for: [..]) — _yaml_value
                            # handles the list form. cost_evidence is a SCALAR_KEY that may carry
                            # a flow map ({source: .., confidence: ..}); it is not a routing input
                            # (route.py reads only the bare scores), so its exact stored shape is
                            # immaterial downstream — _yaml_value's string is harmless here.
                            current_variant[key] = _yaml_value(val)
                        elif key in ALL_VARIANT_KEYS:
                            # Treat as scalar with empty value
                            current_variant[key] = _yaml_value(val) if val else ""
                        continue

    _flush_variant()
    return result


def _check_api_key_present(model_name: str, rbtv_cfg: dict, vault_root: Path, env_var: str | None = None) -> bool:
    """Check if an API key resolves for a model package. OS env first, then env_file.

    Root: VAULT root (where rbtv.json was found). rbtv.json's env_file is vault-relative
    (e.g. `.user/config/env/.env`), so it MUST resolve against vault_root, never the rbtv
    repo root. Manifest enumeration stays at rbtv_root (models/ folder lives there).

    env_var: optional manifest-declared override (variant `auth.env_var`) for packages whose
    backends authenticate under provider-specific key names the package-id derivation cannot
    produce (e.g. a multi-provider harness package like opencode: z1 → ZHIPU_API_KEY,
    sakana → SAKANA_API_KEY). None → derive from the package id (the canonical path).
    """
    if env_var:
        env_var_name = env_var
    else:
        # The API-key env var is keyed by PROVIDER, not by the package's runtime-suffixed
        # id. Strip the runtime suffix (-api / -code-cli / -code-native / -cli) so e.g.
        # deepseek-api → DEEPSEEK_API_KEY and manus-api → MANUS_API_KEY (the canonical
        # provider key names — and the names used before the carrier+runtime rename).
        provider = model_name
        for _suffix in ("-code-cli", "-code-native", "-cli", "-api"):
            if provider.endswith(_suffix):
                provider = provider[: -len(_suffix)]
                break
        env_var_name = f"{provider.upper()}_API_KEY"
    if os.environ.get(env_var_name):
        return True
    env_file = rbtv_cfg.get("env_file")
    if env_file:
        # env_file is vault-relative — resolve against vault_root
        env_path = vault_root / env_file
        try:
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue
                    key, _, _ = line.partition("=")
                    if key.strip() == env_var_name:
                        return True
        except OSError:
            pass
    return False


def _opencode_auth_store_path() -> Path:
    """Resolve opencode's credential-store path (XDG_DATA_HOME, else ~/.local/share).

    opencode persists the credentials created by `opencode auth login` in a JSON file that
    `opencode auth list` names in its OWN output header (observed on the ignite VPS,
    opencode 1.17.18: "Credentials ~/.local/share/opencode/auth.json") — so this path is the
    store the CLI itself reports, not an assumed location. XDG_DATA_HOME is honored first to
    match opencode's own resolution; it also keeps the probe hermetically testable (a test
    points XDG_DATA_HOME at a temp dir to control the store on any platform).
    """
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "opencode" / "auth.json"


# Credential-store resolvers, keyed by the `auth.credential_store` id a variant may declare
# (manifest-schema.md §2). A store id with no resolver here reads as "no stored credential"
# (False) — an unknown id never crashes the router.
CREDENTIAL_STORE_RESOLVERS = {
    "opencode": _opencode_auth_store_path,
}


def _is_windows() -> bool:
    """Is this process running on NATIVE Windows?

    `win32` is sys.platform's value on every native Windows build (32- and 64-bit alike).
    Deliberately NOT matching `cygwin`/`msys`: those are POSIX-emulating environments where the
    XDG_DATA_HOME / ~/.local/share resolution above works as it does on Linux, so they are not
    the unverified case the Windows notice exists to flag.

    Factored out (rather than inlined) so a test can pin the platform on any host: the Windows
    notice in `_unavailable_reason` must be assertable from the Linux VPS this suite runs on.
    """
    return sys.platform == "win32"


def _check_stored_credential(store_id: str | None, store_key: str | None) -> bool:
    """Is `store_key` a stored login in CLI `store_id`'s credential store?

    The SECOND resolution path for an `api-key` variant (owner ruling 2026-07-15): a harness
    that keeps its own credential store authenticates a backend from that store with NO API-key
    env var exported. Only a variant that DECLARES `auth.credential_store` reaches here, so
    every other package's api-key gate is byte-identical to before.

    Reads the store FILE directly instead of shelling out to the CLI's `auth list`: the file IS
    what `auth list` reports (it prints that path as its header), so this reads the same
    authority at the cost of a small stdlib JSON read rather than a process spawn plus an
    ANSI/TUI output parse — the gate runs at routing time, per variant, and route.py spawns no
    subprocesses.

    Presence of the provider key in the store IS the credential: `opencode auth list` lists
    exactly the store's top-level keys, and `opencode auth logout` removes the key. The payload
    shape is deliberately NOT inspected (it differs across auth types — `api` carries `key`,
    oauth carries tokens), so this stays honest about what was observed.

    Unknown store id, blank key, absent/unreadable file, or malformed JSON → False (degrade,
    never raise — manifest-schema.md §4: a manifest must NEVER crash route.py).
    """
    if not store_id or not store_key:
        return False
    resolver = CREDENTIAL_STORE_RESOLVERS.get(store_id)
    if resolver is None:
        return False
    try:
        path = resolver()
        with open(path, encoding="utf-8") as f:
            store = json.load(f)
    except (OSError, RuntimeError, ValueError):
        # OSError: absent/unreadable file. RuntimeError: home dir undeterminable.
        # ValueError: malformed JSON (json.JSONDecodeError subclasses it).
        return False
    if not isinstance(store, dict):
        return False
    entry = store.get(store_key)
    return isinstance(entry, dict) and bool(entry)


def _get_auth_method(variant: dict) -> str:
    # Defense-in-depth: a manifest must NEVER crash route.py (manifest-schema.md §4 + spec
    # Edge Cases). The parser now coerces a map-key's inline value to a dict, but a malformed
    # manifest could still leave `auth` a non-dict — treat any non-dict auth as method "none".
    auth = variant.get("auth")
    if not isinstance(auth, dict):
        return "none"
    return auth.get("method", "none")


def _is_variant_available(variant: dict, model_name: str, rbtv_cfg: dict, vault_root: Path) -> bool:
    """Availability gate.

    An explicit `available: false` mark drops the variant regardless of auth method; otherwise
    availability = key-present for api-key variants, and cli-login/none are always available.

    The `available:` field (default true — an absent field or `true` means available) is the
    GENERAL override for a variant the provider has taken offline that the api-key probe cannot
    detect — e.g. a `cli-login`/`none`-auth model such as Fable 5 during an access-gated rollout.
    Without it, cli-login/none variants always read available and a marked-unavailable variant
    could still be resolved by a pin/selector.

    vault_root: vault root (where rbtv.json was found) — env_file resolution requires it.
    rbtv_root is the models/ folder root — NOT used here.
    """
    # Explicit availability override: ONLY an explicit `available: false` drops the variant.
    # A missing field or `available: true` falls through to the auth-based checks (default true).
    if variant.get("available") is False:
        return False
    auth_method = _get_auth_method(variant)
    if auth_method == "api-key":
        auth = variant.get("auth") if isinstance(variant.get("auth"), dict) else {}
        # Optional manifest-declared key-name override (variant auth.env_var) for
        # multi-provider packages whose backend keys the package-id derivation cannot name.
        env_var = auth.get("env_var")
        if _check_api_key_present(model_name, rbtv_cfg, vault_root, env_var=env_var):
            return True
        # EITHER path satisfies the gate (owner ruling 2026-07-15). A variant MAY declare that
        # its credential ALSO resolves from a harness's stored CLI login (auth.credential_store
        # + auth.credential_store_key), because such a harness authenticates that backend with
        # NO env var exported — keying availability on the env var alone reports the backend
        # unavailable while it demonstrably works. The env-var path above stays first and
        # unchanged (it is the piloted one); this is a fallback, never a replacement.
        # Variants that do NOT declare a credential_store are unaffected: `store_id` is None
        # ⇒ _check_stored_credential returns False ⇒ behavior identical to before.
        return _check_stored_credential(auth.get("credential_store"), auth.get("credential_store_key"))
    # cli-login and none are not key-tested by the script
    return True


def _unavailable_reason(variant: dict) -> str:
    """The explain-trace reason a variant was dropped at the availability stage.

    Called ONLY at the availability-stage drop sites, so reaching the `store_id` branch below
    already means all three of: the variant declares a credential store, the env-var path did
    NOT resolve, and the store lookup found nothing — i.e. the store path is what decided the
    verdict. That is exactly the case the Windows notice qualifies.
    """
    if variant.get("available") is False:
        return "marked available: false in manifest"
    auth = variant.get("auth") if isinstance(variant.get("auth"), dict) else {}
    store_id = auth.get("credential_store")
    if store_id:
        reason = (
            "api-key absent in both OS env and env_file, and no stored "
            f"'{auth.get('credential_store_key')}' credential in the {store_id} auth store"
        )
        if _is_windows():
            # The store path is the deciding factor here, and on Windows this resolver has NOT
            # been verified: CREDENTIAL_STORE_RESOLVERS resolves XDG_DATA_HOME, else
            # ~/.local/share — where the CLI stores credentials on Windows is UNKNOWN (it may
            # be %LOCALAPPDATA% or elsewhere), so a real stored login there reads as absent.
            # The verdict stays UNAVAILABLE — guessing a path would be worse than saying
            # "unverified" — but it is flagged as non-authoritative rather than silently wrong.
            reason += (
                " -- NOT AUTHORITATIVE ON WINDOWS: this variant MAY in fact be available via a "
                f"stored {store_id} login. This resolver does not yet cover the Windows "
                f"credential-store path (it looks only at XDG_DATA_HOME, else ~/.local/share), "
                f"so a store kept elsewhere on Windows reads as absent. Run `{store_id} auth "
                "list` on this machine and add the store path it reports to this store's "
                "resolver in CREDENTIAL_STORE_RESOLVERS to close the gap."
            )
        return reason
    return "api-key absent in both OS env and env_file"


# ---------------------------------------------------------------------------
# Profile → requirement helpers
# ---------------------------------------------------------------------------

def _leaf_role(profile: dict) -> str:
    """Resolve the leaf-kind ROLE the task requests (the routable_for GATE key).

    Order: an explicit `leaf_role` on the profile wins; otherwise derive from task_type
    (code -> bounded-code / unbounded-code by boundedness; web -> web-research; else
    text-synthesis). A profile may also set `leaf_role: other` to force the catch-all
    (audit-logged). The closed vocabulary lives in ROLE_VOCABULARY; an unknown string the
    profile supplies is honored verbatim and simply matches no variant's routable_for.
    """
    explicit = profile.get("leaf_role")
    if explicit:
        return explicit
    task_type = profile.get("task_type", "text")
    if task_type == "code":
        band = profile.get("boundedness", "fully-bounded")
        return "unbounded-code" if band == "unbounded" else "bounded-code"
    if profile.get("needs_web", False):
        return "web-research"
    return "text-synthesis"


def _reasoning_floor(profile: dict) -> int:
    """The minimum reasoning integer needed for this profile's boundedness band (1-7)."""
    explicit = profile.get("needed_reasoning_floor")
    if explicit is not None:
        return int(explicit)
    band = profile.get("boundedness", "fully-bounded")
    return REASONING_FLOOR_BY_BAND.get(band, REASONING_FLOOR_BY_BAND["fully-bounded"])


def _coding_floor(profile: dict) -> int:
    """The minimum coding integer needed for a code leaf in this band (1-7).

    Returns 0 for a non-code leaf (no coding floor applies). 0 is below the 1-7 scale, so
    every variant passes — the coding GATE is inert on text leaves.
    """
    if profile.get("task_type", "text") != "code":
        return 0
    explicit = profile.get("needed_coding_floor")
    if explicit is not None:
        return int(explicit)
    band = profile.get("boundedness", "fully-bounded")
    return CODING_FLOOR_BY_BAND.get(band, CODING_FLOOR_BY_BAND["fully-bounded"])


def _routable_for_allows(variant_entry: dict, leaf_role: str) -> bool:
    """The routable_for role-eligibility GATE (D12/D13; manifest-schema.md §2).

    Rules:
      - routable_for ABSENT or empty -> eligible for ALL leaves (back-compat default).
      - PRESENT -> eligible ONLY if leaf_role is in the list; dropped from every other leaf.
      - An unknown leaf_role string is treated as not-matching (variant dropped), never a crash.
      - CODE-ELIGIBILITY (D13): a code leaf (leaf_role in CODE_ROLES) requires routable_for
        MEMBERSHIP of a code role when routable_for is non-empty — an honest coding score never
        re-enables an ineligible code route (a non-executor with routable_for omitting the code
        roles is dropped from code leaves regardless of its coding integer). Absent/empty
        routable_for stays code-eligible (back-compat).
    """
    rf = variant_entry.get("routable_for")
    # Normalize: a malformed scalar/None/"" all read as "absent" (eligible for all).
    if not rf or not isinstance(rf, list):
        return True
    # Non-empty allow-list: the requested role must be a member.
    return leaf_role in rf


# ---------------------------------------------------------------------------
# Core routing logic
# ---------------------------------------------------------------------------

def _enumerate_models(rbtv_root: Path, vault_root: Path, rbtv_cfg: dict, explain_log: list, elected: list | None = None, elected_variants: dict | None = None) -> list:
    """Stage 1: enumerate every (model, variant) from the live models/ folder.

    rbtv_root: rbtv repo root (orchestration/models/ lives here — enumeration root).
    vault_root: vault root (where rbtv.json was found — env_file resolution root for availability).
    elected: when not None, the workspace's elected model-package ids (rbtv.json
        `model_packages`). A package directory present on disk but NOT in this list is skipped
        at enumerate — routing honors the owner's election, not raw disk presence
        (election-authoritative). elected=None disables the filter so every present package
        enumerates: the back-compat path AND the --models-dir confinement bypass.
    elected_variants: when not None, a {package_id: [variant_id, ...]} map confining a
        CONFIGURABLE package to a backend subset (rbtv.json `model_variants`). A backend of
        such a package NOT in its list is skipped at enumerate; a package with no entry has
        all its variants enumerate. None disables the backend filter entirely.
    """
    models_dir = rbtv_root / "orchestration" / "models"
    if not models_dir.exists():
        explain_log.append({"stage": "enumerate", "action": "no_models_folder", "details": "models/ folder absent"})
        return []

    entries = []
    for d in sorted(models_dir.iterdir()):
        if not d.is_dir() or d.name in SKIP_DIRS or d.name.startswith("_"):
            if d.name in SKIP_DIRS:
                explain_log.append({"stage": "enumerate", "action": "skip", "model": d.name, "reason": "infra/fixture dir"})
            continue
        manifest_path = d / "manifest.yaml"
        if not manifest_path.exists():
            explain_log.append({"stage": "enumerate", "action": "skip", "model": d.name, "reason": "no manifest.yaml"})
            continue
        # Election filter (election-authoritative): a real package present on disk but not in
        # the workspace's elected set is not routable here. elected=None disables the filter.
        if elected is not None and d.name not in elected:
            explain_log.append({"stage": "enumerate", "action": "skip", "model": d.name, "reason": "not elected (rbtv.json model_packages)"})
            continue
        manifest = _load_manifest(manifest_path)
        model_name = manifest.get("model", d.name)
        pkg_evidence = manifest.get("evidence_status", "probe-pending")
        for v in manifest.get("variants", []):
            # Variant-election filter (election-authoritative at the backend level): a
            # CONFIGURABLE package confined to a backend subset (rbtv.json model_variants)
            # skips any backend not in its subset. No entry for a package => all its
            # variants enumerate (back-compat with pre-variant installs).
            if (
                elected_variants
                and d.name in elected_variants
                and v.get("variant") not in elected_variants[d.name]
            ):
                explain_log.append({
                    "stage": "enumerate", "action": "skip", "model": model_name,
                    "variant": v.get("variant", "?"),
                    "reason": "not elected (rbtv.json model_variants)",
                })
                continue
            # Check required fields
            missing = [f for f in REQUIRED_VARIANT_FIELDS if f not in v]
            if missing:
                explain_log.append({
                    "stage": "enumerate", "action": "drop", "model": model_name,
                    "variant": v.get("variant", "?"), "reason": f"missing required fields: {missing}",
                })
                continue
            # Merge package-level evidence_status if variant doesn't override
            variant_evidence = v.get("evidence_status", pkg_evidence)
            entries.append({
                "model": model_name,
                "model_dir": d.name,
                "variant": v["variant"],
                "reasoning": int(v["reasoning"]),
                "context_window": int(v["context_window"]),
                "cost": int(v["cost"]),
                "coding": int(v["coding"]),
                "web_access": bool(v.get("web_access", False)),
                "routable_for": v.get("routable_for") if isinstance(v.get("routable_for"), list) else None,
                "reasoning_modes": v.get("reasoning_modes") if isinstance(v.get("reasoning_modes"), dict) else {},
                "evidence_status": variant_evidence,
                "auth_method": _get_auth_method(v),
                "specialty": v.get("specialty", ""),
                "invocation_pointer": v.get("invocation_pointer", ""),
                "raw_variant": v,
            })

    explain_log.append({"stage": "enumerate", "action": "complete", "count": len(entries), "models": sorted(set(e["model"] for e in entries))})
    return entries


def _present_package_dirs(models_dir: Path) -> list:
    """Return the sorted names of present package dirs under models_dir.

    "Present package dir" = a directory holding a manifest.yaml, EXCLUDING `_`-prefixed
    dirs and the SKIP_DIRS infra/fixture dirs — i.e. exactly the dirs `_enumerate_models`
    walks. This mirrors `_enumerate_models`'s dir-level skip rules (SKIP_DIRS + `_`-prefix +
    manifest.yaml presence); it is the package-presence predicate WITHOUT the variant/field
    parsing or explain-log side effects, so `--availability` can report election over disk
    presence. Kept separate (not folded into `_enumerate_models`) so enumerate's per-dir skip
    trace rows are preserved unchanged.
    """
    if not models_dir.exists():
        return []
    names = []
    for d in sorted(models_dir.iterdir()):
        if not d.is_dir() or d.name in SKIP_DIRS or d.name.startswith("_"):
            continue
        if not (d / "manifest.yaml").exists():
            continue
        names.append(d.name)
    return names


def build_availability(rbtv_root: Path, rbtv_cfg: dict) -> dict:
    """Compute the elected / not-elected package-id partition for `--availability`.

    elected = `rbtv.json` `model_packages` (the workspace election authority) INTERSECTED with
    the package dirs actually present on disk; ids only, sorted alphabetically. When
    `model_packages` is absent/None (election filter off — mirrors route.py's `elected=None ⇒
    no filter` semantics) ALL present packages are elected.
    not_elected = present package dirs MINUS elected; ids only, sorted alphabetically.

    Reports ELECTION only — NOT availability-now (api-key resolution / per-dispatch checks),
    which route.py decides at routing time.
    """
    models_dir = rbtv_root / "orchestration" / "models"
    present = _present_package_dirs(models_dir)
    present_set = set(present)
    elected_cfg = rbtv_cfg.get("model_packages")
    if elected_cfg is None:
        elected = sorted(present_set)
    else:
        elected = sorted(present_set & set(elected_cfg))
    not_elected = sorted(present_set - set(elected))
    return {"elected": elected, "not_elected": not_elected}


def _apply_plan_caps(entries: list, plans: dict, explain_log: list) -> list:
    """Apply plan-overlay context window caps from the plans file.

    Read-path UNCHANGED per D14 — the per-user context cap stays in model-plans.yaml,
    read via the model_plans_file pointer in rbtv.json. p2-1 does NOT touch this.
    """
    if not plans:
        return entries
    for entry in entries:
        model = entry["model"]
        # Plans file might have per-model caps
        model_plan = plans.get(model, {})
        if isinstance(model_plan, dict):
            cap = model_plan.get("context_window") or model_plan.get("context_cap")
            if cap is not None:
                cap_int = int(cap)
                original = entry["context_window"]
                entry["context_window"] = min(original, cap_int)
                entry["plan_cap_applied"] = True
                explain_log.append({
                    "stage": "plan_cap", "model": model, "variant": entry["variant"],
                    "manifest_window": original, "plan_cap": cap_int, "effective_window": entry["context_window"],
                })
    return entries


def _filter(entries: list, profile: dict, explain_log: list, cap: float = DEFAULT_WINDOW_UTILIZATION_CAP, skip_window: bool = False) -> list:
    """Stage 2: GATE — drop any variant failing a hard requirement.

    GATE (manifest-schema.md §0 + spec § Decision flow):
      - reasoning >= the boundedness band's numeric floor
      - context_window window check (AFTER plan cap) — one of two forms:
          * profile carries `known_input_size` (footprint-aware GATE, spec Behavior 1-4):
            effective_window >= ceil(known_input_size / cap)  (a worker fits only if the
            known input is at most `cap` of its window — default cap 0.20 ⇒ window >= 5×input).
            This REPLACES the inlined_context_size check for that worker (the known input ⊇ the
            inlined prompt, so the utilization cap is the stricter bound).
          * no `known_input_size` (back-compat): context_window >= inlined_context_size — the
            window check byte-identical to pre-footprint behavior; cap is inert.
      - web_access when the leaf needs web
      - coding >= the code leaf's numeric floor (code leaves only; floor 0 = inert on text)
      - routable_for allows this leaf-kind role (role-eligibility, independent of capability;
        D13 code-eligibility is enforced inside _routable_for_allows for code leaves)

    skip_window: when True the window check is bypassed entirely (used by the footprint fallback,
    which keeps every NON-window gate but deliberately admits over-cap workers so the biggest-
    capable worker is reachable as the last resort — spec Behavior 5).
    """
    reasoning_floor = _reasoning_floor(profile)
    coding_floor = _coding_floor(profile)
    needs_web = profile.get("needs_web", False)
    inlined_size = profile.get("inlined_context_size", 0)
    known_input_size = profile.get("known_input_size")  # optional (.get) — NOT in REQUIRED_PROFILE_FIELDS
    leaf_role = _leaf_role(profile)

    survivors = []
    for e in entries:
        reasons_dropped = []

        # reasoning floor check (integer 1-7 direct compare)
        if e["reasoning"] < reasoning_floor:
            reasons_dropped.append(f"reasoning {e['reasoning']} < floor {reasoning_floor}")

        # context_window check (skipped entirely for the footprint fallback)
        if not skip_window:
            if known_input_size is not None:
                # Footprint-aware GATE (spec Behavior 3): the known input must fit within `cap`
                # of the effective window. min_window = ceil(known_input_size / cap). This is the
                # utilization cap and REPLACES the inlined_size check for this worker.
                min_window = math.ceil(int(known_input_size) / cap)
                if e["context_window"] < min_window:
                    reasons_dropped.append(
                        f"context_window {e['context_window']} < {min_window} "
                        f"(known_input_size {known_input_size} > {cap:g}x window -- utilization cap)"
                    )
            else:
                # Back-compat window check: byte-identical to pre-footprint behavior.
                if e["context_window"] < inlined_size:
                    reasons_dropped.append(f"context_window {e['context_window']} < inlined_size {inlined_size}")

        # web_access check
        if needs_web and not e["web_access"]:
            reasons_dropped.append("needs web but web_access=false")

        # coding floor check (integer 1-7 direct compare; floor 0 on text leaves -> inert)
        if coding_floor and e["coding"] < coding_floor:
            reasons_dropped.append(f"coding {e['coding']} < floor {coding_floor}")

        # routable_for role-eligibility GATE (independent of capability; D13 for code leaves)
        if not _routable_for_allows(e, leaf_role):
            reasons_dropped.append(
                f"routable_for {e.get('routable_for')} does not allow leaf role '{leaf_role}'"
            )

        if reasons_dropped:
            explain_log.append({
                "stage": "filter", "action": "drop", "model": e["model"],
                "variant": e["variant"], "reasons": reasons_dropped,
            })
        else:
            survivors.append(e)

    explain_log.append({"stage": "filter", "action": "complete", "survivors": len(survivors), "leaf_role": leaf_role})
    return survivors


def _rank(entries: list, profile: dict, explain_log: list) -> list:
    """Stage 3: RANK survivors by the total order.

    Order: cost ASCENDING (integer 1-7, cheapest=1 first; priciest=7 last, never auto-picked)
    -> evidence_status (validated before probe-pending) -> capability score (the coding 1-7
    orders code-task survivors directly; no separate sub-rank step). The carrier tiebreak
    (claude-code-native before claude-code-cli) and the model/variant name tiebreak close it.
    """
    is_code = profile.get("task_type", "text") == "code"

    def _sort_key(e):
        cost_idx = e["cost"]  # integer 1-7, ascending (cheapest first)
        evidence_idx = EVIDENCE_ORDER.index(e["evidence_status"]) if e["evidence_status"] in EVIDENCE_ORDER else 99
        # Capability score: on a code leaf the coding 1-7 orders survivors directly (higher
        # first); otherwise reasoning. Negated so HIGHER capability sorts EARLIER (ascending sort).
        capability = e["coding"] if is_code else e["reasoning"]
        cap_rank = -capability
        # Carrier tiebreak: among otherwise-tied Claude, the agent-tool carrier
        # (claude-code-native) is the default — rank the process carrier (claude-code-cli)
        # AFTER it. Preserves the pre-rename order where `claude` < `claude-cli`.
        return (cost_idx, evidence_idx, cap_rank, e["model"] == "claude-code-cli", e["model"], e["variant"])

    ranked = sorted(entries, key=_sort_key)
    explain_log.append({
        "stage": "rank", "action": "ranked",
        "order": [{"model": e["model"], "variant": e["variant"], "cost": e["cost"],
                   "evidence_status": e["evidence_status"], "reasoning": e["reasoning"],
                   "coding": e["coding"]} for e in ranked],
    })
    return ranked


def _exclude_haiku(entries: list, profile: dict, explain_log: list) -> list:
    """S7 haiku exclusion: drop every `haiku` variant from the eligible set BEFORE Stage-3
    ranking, UNLESS the profile carries `delegation_map_allows_haiku` (the user-approved
    delegation map IS the explicit request — routing.md §7).

    `delegation_map_allows_haiku` is an OPTIONAL boolean profile field (default false,
    `.get` access — mirrors `reviews_external_cli_code`, D12); it is NOT in
    REQUIRED_PROFILE_FIELDS. Flag true → haiku variants stay eligible and rank normally
    (cost-ascending — a cheapest haiku may win a fully-bounded leaf). Flag absent/false →
    no `haiku` variant ever reaches Stage-3 ranking or the verdict.

    Pinned-role floors (S1 Stage 4 / routing.md §3) are sonnet regardless and never yield
    haiku even under the flag — those floors are claude/sonnet/opus-pinned in the pin paths,
    so haiku is structurally unreachable as a pinned pick; this guard governs only the
    cost-ranked cheapest-capable selection.
    """
    if profile.get("delegation_map_allows_haiku"):
        explain_log.append({
            "stage": "haiku", "action": "admitted",
            "note": "delegation_map_allows_haiku=true -- haiku variants stay eligible (routing.md §7)",
        })
        return entries
    kept = []
    for e in entries:
        if e["variant"] == "haiku":
            explain_log.append({
                "stage": "haiku", "action": "exclude", "model": e["model"], "variant": e["variant"],
                "reason": "no delegation_map_allows_haiku flag -- haiku excluded from eligible set (routing.md §7)",
            })
        else:
            kept.append(e)
    return kept


def _scope_eligible_set(entries: list, profile: dict, explain_log: list) -> list:
    """Scope the enumerated set per boundedness band before Stage 2-3 (S2 keystone).

    UNCHANGED behavior (D14): the boundedness master cut — partially-bounded scopes to the
    Claude mid-tier (sonnet), unbounded scopes to top-tier Claude (opus). Re-expressed in the
    new 1-7 vocab: sonnet's reasoning = 6 (the partially-bounded floor), opus's reasoning = 7
    (the unbounded floor), so the scope keys on the same numeric reasoning floors that the
    band defines (REASONING_FLOOR_BY_BAND) over the Claude packages — selecting exactly the
    same variants the old reasoning_tier=="mid"/"top" scope did.
    """
    band = profile.get("boundedness", "fully-bounded")
    claude_pkgs = ("claude-code-native", "claude-code-cli")
    if band == "fully-bounded":
        # No scoping — all variants eligible
        return entries
    elif band == "partially-bounded":
        # Scope to Claude sonnet-class variants (reasoning >= the partially-bounded floor = 6)
        floor = REASONING_FLOOR_BY_BAND["partially-bounded"]
        scoped = [e for e in entries if e["model"] in claude_pkgs and e["reasoning"] >= floor]
        explain_log.append({
            "stage": "scope", "action": "partially-bounded",
            "scoped_to": f"Claude variants with reasoning >= {floor} (sonnet-class)",
            "before": len(entries), "after": len(scoped),
        })
        return scoped
    else:  # unbounded — keystone: scope to top-tier Claude variants (opus, reasoning >= 7)
        floor = REASONING_FLOOR_BY_BAND["unbounded"]
        scoped = [e for e in entries if e["model"] in claude_pkgs and e["reasoning"] >= floor]
        explain_log.append({
            "stage": "scope", "action": "unbounded",
            "scoped_to": f"top-tier Claude variants with reasoning >= {floor} (opus, keystone)",
            "before": len(entries), "after": len(scoped),
        })
        return scoped


def _resolve_carrier(entry: dict, profile: dict) -> str:
    """S8: resolve carrier based on chosen variant and profile flags."""
    model = entry["model"]
    needs_process = profile.get("needs_process_boundary", False)

    if model in ("kimi-code-cli", "codex-cli", "opencode", "claude-code-cli"):
        return "cli-process"
    elif model == "claude-code-native":
        if needs_process:
            return "cli-process"
        return "agent-tool"
    # API chat workers (deepseek, gemini, manus, etc.)
    return "api"


def _resolve_effort(entry: dict, profile: dict, explain_log: list) -> str | None:
    """Spec row 6 / step 5: AFTER the pin, set effort = f(boundedness) for the chosen variant.

    Read from the chosen variant's reasoning_modes.depths:
      fully-bounded -> low; partially-bounded -> medium; unbounded -> high (or max where exposed).
    A single-mode worker (depths empty or a single entry — Haiku, Agent-tool Claude, Manus,
    inert toggles) is a NO-OP: returns None (route normally, no effort dial). The chosen target
    depth label must actually exist in the variant's depths; if the family does not expose it,
    the nearest-available is not invented — the configured target is returned only when present,
    else the highest available depth is used as the band-appropriate ceiling.
    """
    band = profile.get("boundedness", "fully-bounded")
    modes = entry.get("reasoning_modes") or {}
    depths = modes.get("depths")
    if not isinstance(depths, list) or len(depths) <= 1:
        # Single-mode worker (or no reasoning_modes) — effort is a no-op.
        explain_log.append({
            "stage": "effort", "action": "no_op",
            "model": entry["model"], "variant": entry["variant"],
            "reason": "single-mode worker (depths empty or one entry) -- no effort dial",
        })
        return None

    # Map band -> preferred target label (with the 'max'/'high' fallback for unbounded).
    if band == "fully-bounded":
        preferred = ["low"]
    elif band == "partially-bounded":
        preferred = ["medium"]
    else:  # unbounded / judgment-dense
        preferred = ["max", "high"]  # prefer max where the family exposes it, else high

    chosen_effort = None
    for label in preferred:
        if label in depths:
            chosen_effort = label
            break
    if chosen_effort is None:
        # The family labels its depths differently (e.g. kimi no-think/think, API off/on).
        # Use the lowest depth for fully-bounded, the highest otherwise — the band-appropriate
        # end of whatever ladder the family exposes, without inventing a label.
        chosen_effort = depths[0] if band == "fully-bounded" else depths[-1]

    explain_log.append({
        "stage": "effort", "action": "set",
        "model": entry["model"], "variant": entry["variant"],
        "band": band, "effort": chosen_effort, "available_depths": depths,
    })
    return chosen_effort


def _raise_band_one_level(band: str) -> str:
    """Raise a boundedness band one level: fully-bounded → partially-bounded → unbounded."""
    if band == "fully-bounded":
        return "partially-bounded"
    elif band == "partially-bounded":
        return "unbounded"
    else:
        return "unbounded"  # already at top


def _apply_stakes_tier_up(
    chosen: dict, profile: dict, original_entries: list,
    rbtv_root: Path, vault_root: Path, rbtv_cfg: dict, plans: dict, explain_log: list,
    cap: float = DEFAULT_WINDOW_UTILIZATION_CAP,
) -> dict:
    """Behavior row 9 / S1 Stage 4: raise band one level, RE-RESOLVE, return the raised pick.

    The profile carries an already-assessed `stakes_tier` field. When it signals tier-up,
    we raise the band, re-scope, re-filter, re-rank — deterministically, no clock/randomness.
    cap: the window-utilization cap, threaded into the re-filter so a tier-up on a profile carrying
        known_input_size sizes against the same utilization cap (spec Behavior 8).
    """
    band = profile.get("boundedness", "fully-bounded")
    raised_band = _raise_band_one_level(band)
    raised_profile = dict(profile)
    raised_profile["boundedness"] = raised_band

    explain_log.append({
        "stage": "stakes", "action": "tier_up",
        "original_band": band, "raised_band": raised_band,
        "note": "re-resolving at raised band",
    })

    # Re-scope at the raised band
    scoped = _scope_eligible_set(list(original_entries), raised_profile, explain_log)

    # Re-apply plan caps
    scoped = _apply_plan_caps(scoped, plans, explain_log)

    # Re-check availability (vault_root for env_file resolution)
    available = []
    for e in scoped:
        if _is_variant_available(e["raw_variant"], e["model_dir"], rbtv_cfg, vault_root):
            available.append(e)
        else:
            explain_log.append({
                "stage": "availability", "action": "drop",
                "model": e["model"], "variant": e["variant"],
                "reason": _unavailable_reason(e["raw_variant"]),
                "context": "stakes-tier-up re-resolution",
            })

    if not available:
        explain_log.append({
            "stage": "stakes", "action": "no_candidates_after_tier_up",
            "note": "zero variants available after stakes tier-up -- falling back to original pick",
        })
        return chosen

    # Re-filter at the raised requirement (same utilization cap as the primary GATE — Behavior 8)
    survivors = _filter(available, raised_profile, explain_log, cap=cap)
    if not survivors:
        explain_log.append({
            "stage": "stakes", "action": "no_survivors_after_tier_up",
            "note": "zero survivors after stakes tier-up -- falling back to original pick",
        })
        return chosen

    # S7: exclude haiku before the raised-band re-rank as well — a rank never picks haiku
    # absent the delegation-map flag (in practice the raised band's reasoning floor already
    # drops the low-reasoning haiku, but the guard holds wherever a rank decides a worker).
    survivors = _exclude_haiku(survivors, raised_profile, explain_log)
    if not survivors:
        explain_log.append({
            "stage": "stakes", "action": "no_survivors_after_tier_up",
            "note": "zero non-haiku survivors after stakes tier-up -- falling back to original pick",
        })
        return chosen

    # Re-rank
    ranked = _rank(survivors, raised_profile, explain_log)
    raised_chosen = ranked[0]

    explain_log.append({
        "stage": "stakes", "action": "tier_up_result",
        "original_pick": f"{chosen['model']}:{chosen['variant']}",
        "raised_pick": f"{raised_chosen['model']}:{raised_chosen['variant']}",
    })

    return raised_chosen


# Pinned-role floor definitions per spec Behavior row 10 / routing.md §3.
# floor_reasoning is the new 1-7 numeric floor (sonnet=6, opus=7) replacing the old band words.
_PINNED_FLOORS = {
    "reviewer": {
        "description": "≥ executor reasoning + 1, floor sonnet (reasoning 6), never haiku",
        "floor_variant": "sonnet",
        "floor_models": ("claude-code-native", "claude-code-cli"),
        "floor_reasoning": 6,
    },
    "debug": {
        "description": "Any code-eligible executor with reasoning >= 7 (D17: fable + opus + codex-cli:gpt-5.5); opus is the default on cost",
        "floor_variant": "opus",
        "floor_reasoning": 7,
    },
    "commit": {
        "description": "Agent-tool Claude sonnet floor; strongest-available-reasoner fallback when no Claude is available",
        "floor_variant": "sonnet",
        "floor_models": ("claude-code-native",),
        "floor_carrier": "agent-tool",
    },
}


def _apply_pinned_role_floor(
    chosen: dict, profile: dict, original_entries: list,
    rbtv_root: Path, vault_root: Path, rbtv_cfg: dict, plans: dict, explain_log: list,
    empty_pipeline: bool = False,
) -> dict | None:
    """Behavior row 10 / S1 Stage 4: enforce pinned-role floors AFTER the cheapest pick.

    Raises the result to the floor when the pick lands below it.
    vault_root: vault root for env_file resolution (used by availability checks in re-scoping).
    Floors re-expressed in the 1-7 reasoning vocab (sonnet=6, opus=7) — behavior UNCHANGED.

    empty_pipeline: True when the normal band-scoped pipeline yielded NO candidate (the route()
        no_available_variants / zero_candidates exits) and there is therefore no valid `chosen`.
        In that case the pin's OWN floor is computed directly over `original_entries` (the FULL
        pre-scope enumeration), with plan-caps AND availability applied so an unavailable worker
        never enters the floor. Each pin keeps its OWN scoping: debug admits any reasoning-7 code-
        eligible executor; reviewer / conductor / final-plan-reviewer stay Claude-only, so a
        Claude-only pin still finds nothing and route() returns the error when Claude is unavailable;
        commit is the EXCEPTION — when no Claude sonnet is available it falls back to the strongest
        available reasoner (reasoning-descending, cost ignored) rather than erroring. Returns the
        floor-survivor (or commit fallback) pick, or None when nothing is available at all (route()
        then returns the original error). The passed `chosen` is a non-routable sentinel (carries
        model/variant for the explain log only) and is NEVER returned in this mode.
    """
    pinned_role = profile.get("pinned_role")
    if not pinned_role or pinned_role not in _PINNED_FLOORS:
        return chosen

    floor_def = _PINNED_FLOORS[pinned_role]
    explain_log.append({
        "stage": "pin", "action": "check_floor", "role": pinned_role,
        "current_pick": f"{chosen['model']}:{chosen['variant']}",
        "floor": floor_def["description"],
        **({"note": "empty band-scoped pipeline -- computing pin floor over full enumeration"} if empty_pipeline else {}),
    })

    if pinned_role == "reviewer":
        # Opus reviews ALL external-CLI code (routing.md §3 / S3a).
        if profile.get("reviews_external_cli_code"):
            external_cli_opus = [
                e for e in original_entries
                if e["model"] in ("claude-code-native", "claude-code-cli")
                and e["variant"] == "opus"
            ]
            # In the empty-pipeline path the FULL enumeration has NOT been availability-filtered,
            # so an unavailable opus must not enter the floor (the Claude-only pin must still error
            # when opus is gone).
            if empty_pipeline:
                external_cli_opus = [
                    e for e in external_cli_opus
                    if _is_variant_available(e["raw_variant"], e["model_dir"], rbtv_cfg, vault_root)
                ]
            if external_cli_opus:
                opus_ranked = _rank(external_cli_opus, profile, explain_log)
                raised = opus_ranked[0]
                explain_log.append({
                    "stage": "pin", "action": "floor_raised_external_cli",
                    "role": pinned_role,
                    "original_pick": f"{chosen['model']}:{chosen['variant']}",
                    "raised_pick": f"{raised['model']}:{raised['variant']}",
                    "note": "reviews_external_cli_code=true -> opus floor",
                })
                return raised
            explain_log.append({
                "stage": "pin", "action": "floor_not_found",
                "role": pinned_role,
                "reason": "reviews_external_cli_code=true but no opus variant found -- keeping original pick",
            })
            return None if empty_pipeline else chosen

        # Reviewer >= executor reasoning + 1, floor sonnet (reasoning 6), never haiku.
        # executor_reasoning is the executor's 1-7 reasoning score (profile-supplied; defaults
        # to 1, the floor of the scale).
        executor_reasoning = int(profile.get("executor_reasoning", profile.get("executor_tier_reasoning", 1)))
        required_reasoning = min(executor_reasoning + 1, 7)  # cap at the top of the scale
        # Floor at sonnet (reasoning 6) — reviewer is a Claude-specific floor per routing.md §3
        required_reasoning = max(required_reasoning, floor_def["floor_reasoning"])

        # empty_pipeline: no valid `chosen` to compare — go straight to the floor recompute.
        if not empty_pipeline and chosen["reasoning"] >= required_reasoning:
            explain_log.append({
                "stage": "pin", "action": "floor_already_met",
                "role": pinned_role, "reason": f"current reasoning {chosen['reasoning']} >= required {required_reasoning}",
            })
            return chosen

        # Need to raise: reviewer floors at Claude sonnet+ (routing.md §3)
        scoped_entries = list(original_entries)
        # Scope to Claude variants for reviewer pin
        claude_entries = [e for e in scoped_entries if e["model"] in ("claude-code-native", "claude-code-cli")]
        scoped = _scope_eligible_set(claude_entries, profile, explain_log)
        scoped = _apply_plan_caps(scoped, plans, explain_log)
        # empty_pipeline: the full enumeration is pre-availability — drop unavailable Claude so the
        # Claude-only floor finds nothing when Claude is unavailable (returns the error, never a
        # non-Claude fallback).
        if empty_pipeline:
            scoped = [
                e for e in scoped
                if _is_variant_available(e["raw_variant"], e["model_dir"], rbtv_cfg, vault_root)
            ]

        # Filter to Claude variants meeting the floor reasoning
        floor_survivors = [e for e in scoped if e["reasoning"] >= required_reasoning]

        if floor_survivors:
            floor_ranked = _rank(floor_survivors, profile, explain_log)
            raised = floor_ranked[0]
            explain_log.append({
                "stage": "pin", "action": "floor_raised",
                "role": pinned_role,
                "original_pick": f"{chosen['model']}:{chosen['variant']}",
                "raised_pick": f"{raised['model']}:{raised['variant']}",
            })
            return raised

    elif pinned_role == "debug":
        # Reasoning-7 code-eligible executor (D17: de-carrier-locked). The debug floor admits
        # ANY elected, available, code-eligible executor with reasoning >= 7 — fable, opus,
        # AND codex-cli:gpt-5.5, never a reasoning-6 worker (sonnet/kimi/gpt-5.4) or a non-code
        # API worker. Opus stays the default on cost (cost 6 < gpt-5.5 cost 7), so the
        # observable default is unchanged; gpt-5.5 wins only when opus is unavailable/capped.
        floor_reasoning = floor_def["floor_reasoning"]
        # Code-eligibility key: the leaf role the profile requests (a code role for a code task);
        # _routable_for_allows drops non-executors (deepseek/gemini/manus) from code leaves.
        leaf_role = _leaf_role(profile)
        # empty_pipeline: no valid `chosen` to accept — go straight to the floor recompute.
        if not empty_pipeline and _routable_for_allows(chosen, leaf_role) and chosen["reasoning"] >= floor_reasoning:
            explain_log.append({
                "stage": "pin", "action": "floor_already_met",
                "role": pinned_role,
                "reason": f"already reasoning-7 code-eligible executor: {chosen['model']}:{chosen['variant']}",
            })
            return chosen
        # Find the cheapest reasoning-7 code-eligible executor (available + plan caps applied;
        # ranked cheapest). Availability is re-checked here because original_entries is the FULL
        # pre-scope enumeration (an unavailable worker NEVER enters the debug floor — D17).
        scoped = _apply_plan_caps(list(original_entries), plans, explain_log)
        scoped = [
            e for e in scoped
            if _is_variant_available(e["raw_variant"], e["model_dir"], rbtv_cfg, vault_root)
        ]
        top_survivors = [
            e for e in scoped
            if e["reasoning"] >= floor_reasoning and _routable_for_allows(e, leaf_role)
        ]
        if top_survivors:
            top_ranked = _rank(top_survivors, profile, explain_log)
            raised = top_ranked[0]
            explain_log.append({
                "stage": "pin", "action": "floor_raised",
                "role": pinned_role,
                "original_pick": f"{chosen['model']}:{chosen['variant']}",
                "raised_pick": f"{raised['model']}:{raised['variant']}",
            })
            return raised

    elif pinned_role == "commit":
        # Agent-tool Claude sonnet floor (reasoning >= 6 = sonnet or opus, never haiku).
        sonnet_floor = _PINNED_FLOORS["reviewer"]["floor_reasoning"]  # 6
        # empty_pipeline: no valid `chosen` to accept — go straight to the floor recompute.
        if not empty_pipeline and chosen["model"] in ("claude-code-native",) and chosen["reasoning"] >= sonnet_floor:
            explain_log.append({
                "stage": "pin", "action": "floor_already_met",
                "role": pinned_role, "reason": f"already Claude sonnet/opus: {chosen['model']}:{chosen['variant']}",
            })
            return chosen
        # Find cheapest Claude sonnet
        scoped_entries = list(original_entries)
        scoped = _scope_eligible_set(scoped_entries, profile, explain_log)
        # empty_pipeline: drop unavailable variants so the Claude-sonnet floor only raises to an
        # AVAILABLE Claude sonnet (an unavailable sonnet never satisfies the floor). When no Claude
        # sonnet is available, the strongest-reasoner fallback below handles the commit pin — it no
        # longer errors (the commit pin's Claude-excluded fallback, distinct from reviewer/conductor).
        if empty_pipeline:
            scoped = [
                e for e in scoped
                if _is_variant_available(e["raw_variant"], e["model_dir"], rbtv_cfg, vault_root)
            ]
        sonnet_variants = [e for e in scoped if e["model"] in ("claude-code-native",) and e["variant"] == "sonnet"]
        if sonnet_variants:
            sonnet_ranked = _rank(sonnet_variants, profile, explain_log)
            raised = sonnet_ranked[0]
            explain_log.append({
                "stage": "pin", "action": "floor_raised",
                "role": pinned_role,
                "original_pick": f"{chosen['model']}:{chosen['variant']}",
                "raised_pick": f"{raised['model']}:{raised['variant']}",
            })
            return raised

        # Claude-excluded fallback (commit-specific): no AVAILABLE agent-tool Claude sonnet/opus
        # exists for the commit pin. Per routing.md §3 the commit pin must NOT keep the cheapest
        # non-Claude `chosen` (the cost-ascending pick) and must NOT error — commit-message/hygiene
        # quality outweighs cost here, so fall back to the STRONGEST AVAILABLE REASONER (highest
        # `reasoning` integer, cost ignored). Scanned over the FULL enumeration (original_entries) so
        # the fallback escapes the band's Claude-only scope; plan-caps + availability applied so an
        # unavailable worker never enters; haiku excluded (the commit floor is never-haiku). Fires
        # for BOTH the normal and the empty-pipeline path — commit is the ONLY Claude-floor pin with
        # a non-Claude fallback (reviewer / conductor / final-plan-reviewer stay Claude-only-or-error).
        fallback_pool = _apply_plan_caps(list(original_entries), plans, explain_log)
        fallback_pool = [
            e for e in fallback_pool
            if e["variant"] != "haiku"
            and _is_variant_available(e["raw_variant"], e["model_dir"], rbtv_cfg, vault_root)
        ]
        if fallback_pool:
            # Rank by reasoning DESCENDING (cost ignored for the primary choice). _rank yields the
            # house total order (cost-ascending + evidence + capability + carrier + name); a STABLE
            # re-sort by -reasoning lifts the strongest reasoner to the top while that house order
            # breaks ties among equal-reasoning workers deterministically.
            house_ranked = _rank(fallback_pool, profile, explain_log)
            strongest = sorted(house_ranked, key=lambda e: -e["reasoning"])[0]
            explain_log.append({
                "stage": "pin", "action": "floor_raised_strongest_reasoner",
                "role": pinned_role,
                "original_pick": f"{chosen['model']}:{chosen['variant']}",
                "raised_pick": f"{strongest['model']}:{strongest['variant']}",
                "note": (
                    "no available agent-tool Claude sonnet -- commit pin falls back to the "
                    "strongest available reasoner (reasoning-descending, cost ignored), never the "
                    "cheapest non-Claude worker and never an error (routing.md §3)"
                ),
            })
            return strongest

    explain_log.append({
        "stage": "pin", "action": "floor_not_found",
        "role": pinned_role, "reason": "no variant met the floor -- keeping original pick",
    })
    # empty_pipeline: nothing to keep — signal "no pin survivor" so route() returns the error.
    return None if empty_pipeline else chosen


def _apply_pins_and_stakes(
    chosen: dict, profile: dict, original_entries: list,
    rbtv_root: Path, vault_root: Path, rbtv_cfg: dict, plans: dict, explain_log: list,
    cap: float = DEFAULT_WINDOW_UTILIZATION_CAP,
) -> dict:
    """S1 Stage 4 / S3: apply stakes tier-up and pinned-role floors AFTER the cheapest pick.

    Stakes tier-up raises the band and RE-RESOLVES the selection (re-filter + re-rank).
    Pinned-role floors raise the result when the pick lands below the floor.
    vault_root: vault root for env_file resolution (used by _apply_stakes_tier_up availability).
    cap: the window-utilization cap, threaded into the stakes tier-up re-filter so a re-resolution
        on a profile carrying known_input_size sizes against the same cap (spec Behavior 8).
    """
    result = chosen

    # Stakes tier-up (Behavior row 9)
    if profile.get("stakes_tier") == "tier_up":
        result = _apply_stakes_tier_up(
            result, profile, original_entries, rbtv_root, vault_root, rbtv_cfg, plans, explain_log, cap=cap,
        )

    # Pinned-role floors (Behavior row 10)
    if profile.get("pinned_role"):
        result = _apply_pinned_role_floor(
            result, profile, original_entries, rbtv_root, vault_root, rbtv_cfg, plans, explain_log,
        )

    return result


def _check_self_execute(profile: dict) -> bool:
    """Behavior 6: self_execute flag from the caller."""
    return bool(profile.get("self_execute", False))


def _check_halt_seams(profile: dict) -> str | None:
    """S3: return halt_seam if a seam is unresolved."""
    # Stakes seam
    if profile.get("stakes") == "unresolved":
        return "stakes"
    # Cross-strategy seam
    if profile.get("cross_strategy") == "multiple_surviving":
        return "cross-strategy"
    return None


def _validate_profile(profile: dict) -> list[str]:
    """Validate required profile fields. Returns list of errors."""
    errors = []
    for field in REQUIRED_PROFILE_FIELDS:
        if field not in profile:
            errors.append(f"missing required field: {field}")
    # Check for contradiction: self_execute + unresolved stakes
    if profile.get("self_execute") and profile.get("stakes") == "unresolved":
        errors.append("contradiction: self_execute flag set but stakes is unresolved")
    return errors


def _build_other_routing_audit(profile: dict, chosen: dict, leaf_role: str) -> dict:
    """Schema §2b / D4 / spec row 3: the `other`-routing audit-trail entry.

    Whenever a task routes via the `other` catch-all role, route.py MUST record the specific
    task instructions/arguments of that routing so under-served task types surface and get
    promoted to first-class roles. Only `other` carries this obligation. The audit captures the
    routed (model, variant) plus the task-identifying fields the profile carries (instructions/
    arguments/description/task_id where present), so the catch-all routing is reconstructable.
    """
    instructions = (
        profile.get("task_instructions")
        or profile.get("instructions")
        or profile.get("arguments")
        or profile.get("task_arguments")
        or profile.get("description")
    )
    return {
        "role": "other",
        "routed_to": f"{chosen['model']}:{chosen['variant']}",
        "task_instructions": instructions,
        "task_id": profile.get("task_id"),
        "note": (
            "routed via the `other` catch-all role -- recorded so under-served task types "
            "surface and get promoted to a first-class role (schema §2b)"
        ),
    }


def _apply_footprint_fallback(
    profile: dict, all_entries: list, cap: float,
    rbtv_root: Path, vault_root: Path, rbtv_cfg: dict, plans: dict, explain_log: list,
) -> dict | None:
    """Footprint fallback (spec Behavior 5-7): the deliberate biggest-capable last resort.

    Fires ONLY when the profile carries `known_input_size` AND the normal post-_filter survivor
    set is EMPTY — i.e. no worker's window holds the known input within the utilization cap. This
    is a DIRECT biggest-capable pick (NOT a reuse of _apply_stakes_tier_up — that routine raises
    the boundedness band one level and, from fully-bounded, lands on Sonnet/200k, never reaching
    Opus/1M for a bounded big job; see decisions.md Collaborative Decisions #1 + the 2026-06-19
    correction).

    Mechanism:
      - Work over the FULL enumeration (`all_entries`), escaping the boundedness scope so the
        largest-window worker (Opus/1M) is reachable even for a fully-bounded leaf.
      - Apply plan-caps + availability (an unavailable / capped worker never enters the pick).
      - Keep workers passing EVERY non-window gate (reasoning floor, coding floor, web,
        routable_for) via _filter(..., skip_window=True) — the window check (and so the cap) is
        deliberately bypassed; this is the accepted over-cap end-of-line.
      - Exclude haiku (the fallback is never a haiku pick, mirroring the normal pipeline).
      - Pick the worker with the LARGEST effective context_window; ties broken deterministically
        by the house RANK order (_rank).

    Returns the chosen entry, or None when NO worker passes the non-window gates (e.g. a code/web
    leaf where only small workers are eligible and none survives) — route() then proceeds to its
    existing zero_candidates path UNCHANGED (spec Behavior 7).
    """
    explain_log.append({
        "stage": "footprint", "action": "fallback_fired",
        "known_input_size": profile.get("known_input_size"), "cap": cap,
        "note": (
            "no worker holds the known input within the utilization cap -- selecting the "
            "biggest-capable worker over the full enumeration (deliberate over-cap last resort)"
        ),
    })

    # Full enumeration → plan caps → availability (escape the boundedness scope).
    pool = _apply_plan_caps(list(all_entries), plans, explain_log)
    available = []
    for e in pool:
        if _is_variant_available(e["raw_variant"], e["model_dir"], rbtv_cfg, vault_root):
            available.append(e)
        else:
            explain_log.append({
                "stage": "availability", "action": "drop", "model": e["model"],
                "variant": e["variant"], "reason": _unavailable_reason(e["raw_variant"]),
                "context": "footprint-fallback",
            })
    if not available:
        explain_log.append({
            "stage": "footprint", "action": "fallback_no_available",
            "note": "no available variant in the full enumeration -- fallback yields nothing",
        })
        return None

    # Keep every NON-window gate (window check bypassed via skip_window) — reasoning/coding/web/
    # routable_for still bind, so a code leaf still excludes non-executors, a web leaf still
    # requires web_access, etc. (spec Behavior 5 + the web/role Edge Cases).
    survivors = _filter(available, profile, explain_log, cap=cap, skip_window=True)
    if not survivors:
        explain_log.append({
            "stage": "footprint", "action": "fallback_no_survivors",
            "note": "no worker passes the non-window gates -- fallback yields nothing (route() -> zero_candidates)",
        })
        return None

    # Exclude haiku (the fallback is never a haiku pick — mirrors the normal pipeline).
    survivors = _exclude_haiku(survivors, profile, explain_log)
    if not survivors:
        explain_log.append({
            "stage": "footprint", "action": "fallback_no_survivors",
            "note": "no non-haiku worker passes the non-window gates -- fallback yields nothing",
        })
        return None

    # Pick the LARGEST effective context_window; deterministic tie-break via the house RANK order.
    max_window = max(e["context_window"] for e in survivors)
    biggest = [e for e in survivors if e["context_window"] == max_window]
    chosen = _rank(biggest, profile, explain_log)[0]
    explain_log.append({
        "stage": "footprint", "action": "fallback_pick",
        "model": chosen["model"], "variant": chosen["variant"],
        "effective_window": chosen["context_window"],
        "note": "biggest-capable worker by effective context_window (ties broken by house RANK)",
    })
    return chosen


def route(profile: dict, rbtv_root: Path, vault_root: Path, rbtv_cfg: dict, plans: dict, explain: bool = False, elected: list | None = None, elected_variants: dict | None = None) -> dict:
    """Main routing function. Returns a verdict dict.

    rbtv_root: rbtv repo root (orchestration/models/ lives here — enumeration root).
    vault_root: vault root (where rbtv.json was found — env_file/model_plans_file resolution root).
    elected: workspace's elected model packages (rbtv.json `model_packages`); None disables the
        election filter (back-compat + --models-dir confinement). Passed to _enumerate_models.
    elected_variants: workspace's per-package backend-subset election (rbtv.json `model_variants`);
        None disables the backend filter. Passed to _enumerate_models.
    """
    explain_log: list = []

    # Validate profile
    errors = _validate_profile(profile)
    if errors:
        return {"error": "malformed_profile", "details": errors}

    # Check self_execute
    if _check_self_execute(profile):
        verdict = {"verdict": "self_execute"}
        if explain:
            verdict["explain"] = [{"stage": "self_execute", "action": "short_circuit", "note": "triviality flag set -- selector not run"}]
        return verdict

    # Check halt seams
    seam = _check_halt_seams(profile)
    if seam:
        verdict = {"verdict": "halt_seam", "seam": seam}
        if explain:
            verdict["explain"] = [{"stage": "halt_seam", "seam": seam, "note": f"judgment seam '{seam}' unresolved -- halting"}]
        return verdict

    # Card fidelity (routing.md §2a/§3): `reviews_external_cli_code: true` IS the reviewer
    # role — the card lists it as a standalone profile field that floors the pick at opus
    # ("Opus reviews ALL external-CLI code"), so it must fire even when the profile omits
    # `pinned_role`. Normalize: flag set + no pinned_role → pinned_role="reviewer" (an
    # explicit different pinned_role is honored unchanged — never overwritten).
    if profile.get("reviews_external_cli_code") and not profile.get("pinned_role"):
        profile = dict(profile)
        profile["pinned_role"] = "reviewer"
        explain_log.append({
            "stage": "pin", "action": "role_implied",
            "role": "reviewer",
            "note": "reviews_external_cli_code=true implies the reviewer role (routing.md §3 opus pin) -- pinned_role set to reviewer",
        })

    # Card fidelity (routing.md §2 STAKES filter): a `stakes` VALUE signalling irreversible or
    # cross-cutting work tiers the pick UP one band. The card lists `stakes` as a standalone
    # profile field (§2a step 1) alongside the pre-digested `stakes_tier`, so the router must act
    # on the value itself — not only on `stakes_tier="tier_up"`. Normalize: an irreversible/
    # cross-cutting `stakes` value + no explicit `stakes_tier` → set `stakes_tier="tier_up"`, so
    # the downstream tier-up path (_apply_pins_and_stakes → _apply_stakes_tier_up) is reused
    # verbatim. `stakes="unresolved"` already short-circuited at the halt-seam above; an
    # absent/reversible/unknown value stays a no-op. An explicit `stakes_tier` is honored unchanged.
    if profile.get("stakes") in STAKES_TIER_UP_TOKENS and not profile.get("stakes_tier"):
        profile = dict(profile)
        profile["stakes_tier"] = "tier_up"
        explain_log.append({
            "stage": "stakes", "action": "tier_up_implied",
            "stakes": profile["stakes"],
            "note": "irreversible/cross-cutting stakes value tiers up (routing.md §2 STAKES filter) -- stakes_tier normalized to tier_up",
        })

    # Stage 1: enumerate (rbtv_root = models/ folder; vault_root = env_file resolution)
    entries = _enumerate_models(rbtv_root, vault_root, rbtv_cfg, explain_log, elected=elected, elected_variants=elected_variants)
    if not entries:
        return {"error": "no_models", "details": "No installed model packages found in models/"}

    # Preserve the FULL enumerated set (pre-scope) for the pins/stakes layer. Stakes tier-up
    # and the pinned-role floors must re-scope at the RAISED band over the full enumeration —
    # not over this band's leftovers. Passing the band-scoped set here would empty the raised-band
    # re-scope (e.g. partially-bounded scoped to Claude sonnet → stakes raise to top-tier Claude
    # finds zero in a sonnet-only set), silently masking the escalation.
    all_entries = list(entries)

    # Footprint-aware routing (spec Behavior 4): resolve the window-utilization cap once from
    # rbtv.json. Threaded into _filter (the footprint GATE) and the stakes tier-up re-filter, and
    # used by the footprint fallback. A single workspace-global value (default 0.20).
    cap = _resolve_window_cap(rbtv_cfg, explain_log)

    def _build_route_verdict(chosen: dict) -> dict:
        """Construct the route verdict (carrier + effort + `other` audit) from a chosen worker.

        Shared by the normal RANK→PIN path and the empty-pipeline pinned-role fallback so both
        emit an identical verdict shape (carrier, post-pin effort, `other`-routing audit).
        """
        carrier = _resolve_carrier(chosen, profile)
        effort = _resolve_effort(chosen, profile, explain_log)
        verdict = {
            "verdict": "route",
            "model": chosen["model"],
            "variant": chosen["variant"],
            "carrier": carrier,
        }
        if effort is not None:
            verdict["effort"] = effort
        leaf_role = _leaf_role(profile)
        if leaf_role == "other":
            verdict["other_routing_audit"] = _build_other_routing_audit(profile, chosen, leaf_role)
        if explain:
            verdict["explain"] = explain_log
        return verdict

    def _pin_fallback_or_error(error_verdict: dict) -> dict:
        """Empty-pipeline pinned-role fallback (the defect fix).

        The normal band-scoped pipeline emptied (no_available_variants / zero_candidates). Before
        returning the error, if a pinned_role is set, run that pin's OWN floor over the FULL
        enumeration (all_entries) — plan-caps + availability applied inside the floor — so a pin
        that COULD reach a worker beyond the empty band (debug → codex-cli:gpt-5.5 when opus is
        unavailable) still routes. Each pin keeps its own scoping (reviewer/commit stay Claude-only
        and still find nothing → return the error, NEVER a non-Claude fallback). No pin survivor →
        return the original error unchanged.
        """
        if not profile.get("pinned_role"):
            if explain:
                error_verdict = {**error_verdict, "explain": explain_log}
            return error_verdict
        # Sentinel `chosen`: non-routable; carries model/variant for the explain log only and is
        # never returned (empty_pipeline=True forces the floor recompute and a None-on-miss).
        sentinel = {"model": "<none>", "variant": "<empty-pipeline>", "reasoning": -1}
        pinned = _apply_pinned_role_floor(
            sentinel, profile, all_entries, rbtv_root, vault_root, rbtv_cfg, plans, explain_log,
            empty_pipeline=True,
        )
        if pinned is not None:
            return _build_route_verdict(pinned)
        if explain:
            error_verdict = {**error_verdict, "explain": explain_log}
        return error_verdict

    # Scope eligible set per boundedness band (S2 keystone)
    entries = _scope_eligible_set(entries, profile, explain_log)

    # Apply plan caps (S4)
    entries = _apply_plan_caps(entries, plans, explain_log)

    # Check availability (S4) — drop unavailable api-key variants
    available = []
    for e in entries:
        if _is_variant_available(e["raw_variant"], e["model_dir"], rbtv_cfg, vault_root):
            available.append(e)
        else:
            explain_log.append({
                "stage": "availability", "action": "drop", "model": e["model"],
                "variant": e["variant"], "reason": _unavailable_reason(e["raw_variant"]),
            })

    if not available:
        return _pin_fallback_or_error({"error": "no_available_variants", "details": "All variants dropped due to availability (api-key absent)"})

    # Stage 2: GATE (filter) — cap threaded so the footprint window check uses the resolved cap.
    survivors = _filter(available, profile, explain_log, cap=cap)
    if not survivors:
        # Footprint fallback (spec Behavior 5-7): when the profile carries `known_input_size` and
        # NO worker's window holds it within the cap, route to the biggest-capable worker over the
        # full enumeration (the deliberate over-cap last resort) BEFORE the zero_candidates error.
        # Absent `known_input_size` this branch never fires (back-compat — byte-identical to today).
        if profile.get("known_input_size") is not None:
            fb_chosen = _apply_footprint_fallback(
                profile, all_entries, cap, rbtv_root, vault_root, rbtv_cfg, plans, explain_log,
            )
            if fb_chosen is not None:
                # Pinned roles still win where applicable (they only raise). Apply the pinned-role
                # floor to the fallback pick (spec Behavior 6); in practice the biggest worker is
                # already top-window/top-reasoning Opus, so the floor is a no-op for most pins.
                fb_chosen = _apply_pinned_role_floor(
                    fb_chosen, profile, all_entries, rbtv_root, vault_root, rbtv_cfg, plans, explain_log,
                )
                if fb_chosen is not None:
                    return _build_route_verdict(fb_chosen)
        return _pin_fallback_or_error({
            "error": "zero_candidates",
            "details": "No installed+available variant meets the leaf's hard requirements",
            "failed_requirements": [log for log in explain_log if log.get("action") == "drop"]
        })

    # S7: exclude haiku variants from the eligible set BEFORE Stage-3 ranking (unless the
    # delegation-map flag admits them). Default-excludes so a future cheapest haiku is never
    # auto-picked by cost-ascending ranking absent an approved delegation map (routing.md §7).
    survivors = _exclude_haiku(survivors, profile, explain_log)
    if not survivors:
        return _pin_fallback_or_error({
            "error": "zero_candidates",
            "details": "No installed+available non-haiku variant meets the leaf's hard requirements (haiku excluded per routing.md §7; set delegation_map_allows_haiku to admit haiku for a mechanical batch)",
            "failed_requirements": [log for log in explain_log if log.get("action") in ("drop", "exclude")]
        })

    # Stage 3: RANK
    ranked = _rank(survivors, profile, explain_log)
    chosen = ranked[0]

    # Apply pins/stakes over the FULL enumeration (re-resolution re-scopes at the raised band).
    # cap threaded so a stakes tier-up's re-filter sizes against the same utilization cap (Behavior 8).
    chosen = _apply_pins_and_stakes(
        chosen, profile, all_entries, rbtv_root, vault_root, rbtv_cfg, plans, explain_log, cap=cap,
    )

    # Resolve carrier
    carrier = _resolve_carrier(chosen, profile)

    # Step 5: set effort = f(boundedness) from the chosen variant's reasoning_modes (post-pin).
    effort = _resolve_effort(chosen, profile, explain_log)

    verdict = {
        "verdict": "route",
        "model": chosen["model"],
        "variant": chosen["variant"],
        "carrier": carrier,
    }
    if effort is not None:
        verdict["effort"] = effort

    # Schema §2b / D4: when the routed leaf is the `other` catch-all role, record the audit trail.
    leaf_role = _leaf_role(profile)
    if leaf_role == "other":
        verdict["other_routing_audit"] = _build_other_routing_audit(profile, chosen, leaf_role)

    if explain:
        verdict["explain"] = explain_log

    return verdict


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Deterministic router script — task profile → (model, variant, carrier)")
    parser.add_argument("--profile", type=str, help="Path to task profile JSON file (default: stdin)")
    parser.add_argument("--explain", action="store_true", help="Print the enumerate→filter→rank trace")
    parser.add_argument(
        "--availability", action="store_true",
        help=(
            "Profile-free recall mode. Print the ELECTED vs NOT-ELECTED model-package ids as "
            "JSON {\"elected\":[ids],\"not_elected\":[ids]} (sorted) and exit 0, reading NO task "
            "profile and NO stdin. elected = rbtv.json `model_packages` ∩ packages present on "
            "disk (all-present when model_packages is absent/None); not_elected = present − "
            "elected. Honors --rbtv-json / --models-dir; ignores --explain. Reports ELECTION "
            "only — NOT availability-now (api-key/per-dispatch checks route.py makes at routing time)."
        ),
    )
    parser.add_argument(
        "--models-dir", type=str, default=None,
        help=(
            "Override the catalog root (the orchestration/models/ directory). "
            "When given, EVERY catalog-resolution path (enumeration, manifest loading) uses this "
            "directory instead of the live orchestration/models/ tree. "
            "Confinement boundary: rbtv.json-derived inputs that are NOT catalog content "
            "(env_file key presence, plan-overlay caps) are still resolved from the live vault root. "
            "Default: None — resolves the live orchestration/models/ tree from the rbtv repo root."
        ),
    )
    parser.add_argument(
        "--rbtv-json", type=str, default=None,
        help=(
            "Resolve the workspace election (model_packages / model_variants) and config "
            "(env_file, model_plans_file) from THIS rbtv.json instead of the one found by "
            "walking up from this script. The catalog (models/) is unaffected. A test / "
            "what-if seam: route a scratch install's election without touching live config."
        ),
    )
    args = parser.parse_args()

    # Resolve paths / cfg / election FIRST — this block is profile-independent. It is hoisted
    # above the profile load so --availability (a profile-free recall mode) can branch and exit
    # before any stdin/profile is read. The verdict path below is byte-identical to before: it
    # still loads the profile, then routes against these same resolved inputs.
    # Resolve paths
    vault_root = _resolve_vault_root()
    rbtv_root = vault_root  # rbtv is at vault root level in 3-resources/tools/rbtv
    # Actually, rbtv_root should be the rbtv repo path
    rbtv_root = vault_root / "3-resources" / "tools" / "rbtv"
    if not (rbtv_root / "orchestration" / "models").exists():
        # Fallback: maybe we're running from within the rbtv repo
        fallback = Path(__file__).resolve().parents[2]
        if (fallback / "orchestration" / "models").exists():
            rbtv_root = fallback

    # --models-dir override: when given, replace the catalog root used by _enumerate_models.
    # We accomplish this by replacing rbtv_root with a synthetic root whose
    # orchestration/models/ subtree points to the override directory.
    # rbtv.json-derived inputs (env_file, plan-overlay) always come from vault_root — unaffected.
    if args.models_dir:
        override_models_dir = Path(args.models_dir).resolve()
        # Build a synthetic rbtv_root: a temporary shim so that
        # rbtv_root / "orchestration" / "models" == override_models_dir.
        # We do this by computing the parent two levels up from override_models_dir,
        # which makes rbtv_root = override_models_dir.parent.parent
        # (override_models_dir is treated as orchestration/models/).
        rbtv_root = override_models_dir.parent.parent

    # --rbtv-json override: resolve election + config from an explicit rbtv.json (test/what-if
    # seam) instead of the walked-up one. env_file / model_plans_file in that file resolve
    # relative to ITS parent; the catalog (models/) still comes from the real rbtv_root (or
    # --models-dir). Lets a scratch install's election be routed without touching live config.
    if args.rbtv_json:
        cfg_path = Path(args.rbtv_json).resolve()
        try:
            with open(cfg_path, encoding="utf-8") as f:
                rbtv_cfg = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(json.dumps({"error": "rbtv_json_load_failed", "details": str(e)}), file=sys.stderr)
            sys.exit(1)
        vault_root = cfg_path.parent
    else:
        rbtv_cfg = _load_rbtv_json(vault_root)
    plans = _load_model_plans(vault_root, rbtv_cfg)

    # Election (election-authoritative): the workspace's elected model packages gate routing.
    # --models-dir confinement is an explicit catalog override and BYPASSES the election (route
    # from exactly that catalog). Absent model_packages -> None -> no filter (back-compat).
    elected = None if args.models_dir else rbtv_cfg.get("model_packages")
    elected_variants = None if args.models_dir else rbtv_cfg.get("model_variants")

    # --availability: profile-free recall mode. Branch BEFORE the profile load — print the
    # elected/not-elected package ids (over the inputs resolved above; honors --rbtv-json /
    # --models-dir, ignores --explain) and exit. Reads no profile and no stdin.
    if args.availability:
        print(json.dumps(build_availability(rbtv_root, rbtv_cfg), indent=2, ensure_ascii=False))
        sys.exit(0)

    # Load profile (verdict path only — reached when --availability is not set).
    if args.profile:
        try:
            with open(args.profile, encoding="utf-8") as f:
                profile = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(json.dumps({"error": "profile_load_failed", "details": str(e)}), file=sys.stderr)
            sys.exit(1)
    else:
        try:
            profile = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(json.dumps({"error": "profile_parse_failed", "details": str(e)}), file=sys.stderr)
            sys.exit(1)

    # Route
    result = route(profile, rbtv_root, vault_root, rbtv_cfg, plans, explain=args.explain, elected=elected, elected_variants=elected_variants)

    # Output
    output = json.dumps(result, indent=2, ensure_ascii=False)
    print(output)

    # Exit code
    if "error" in result:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
