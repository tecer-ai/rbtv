#!/usr/bin/env python
"""Router script — deterministic (model, variant, carrier) resolution from a task profile.

Reads a structured task-profile JSON on stdin or via --profile, resolves against
the live manifests on disk, and emits one machine-readable verdict:
  route {model, variant, carrier}
  self_execute
  halt_seam {seam: <name>}

With --explain, also prints the enumerate→filter→rank trace.
Stdlib only. No network, clock, or randomness.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COST_ORDER = ["cheapest", "low", "mid", "high", "premium"]
EVIDENCE_ORDER = ["validated", "probe-pending"]
TIER_VALUES = {"non-reasoning": 0, "mid": 1, "top": 2}

REQUIRED_PROFILE_FIELDS = [
    "boundedness",
    "task_type",          # "code" or "text"
    "inlined_context_size",
]

REQUIRED_VARIANT_FIELDS = [
    "variant", "reasoning_tier", "context_window", "cost_class",
    "code_competence", "web_access",
]

SKIP_DIRS = {"_api", "_fixture", "mirror"}


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


def _load_model_plans(vault_root: Path, rbtv_cfg: dict) -> dict:
    """Load the model-plans YAML if the pointer exists and the file is readable.

    Returns a {model: {context_window, cost_usd_per_m_in, cost_usd_per_m_out, plan_name}}
    map keyed by package id — the shape _apply_plan_caps consumes. Graceful skip
    (empty dict) on absent pointer, unreadable file, or unparseable content.
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
    current_map_key: str = ""  # e.g. "headless", "auth", "tool_surface"
    current_map_value: dict = {}

    MAP_KEYS = {
        "headless", "auth", "tool_surface", "confinement",
        "swarm_support", "configurable_model", "guidance_file", "os_quirks",
    }
    SCALAR_KEYS = {
        "specialty", "failure_modes", "invocation_pointer",
        "manual_path", "delta_path", "rate_budget_notes",
        "reasoning_tier", "context_window", "max_output",
        "cost_class", "code_competence", "web_access",
        "multimodal", "parallel_safe", "resume_support",
        "evidence_status", "variant",
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
                    # Indented sub-keys of a map (e.g. "      required: false" under "auth:")
                    if current_map_key and indent >= 6 and ":" in stripped:
                        sub_key, _, sub_val = stripped.partition(":")
                        sub_key = sub_key.strip()
                        sub_val = sub_val.strip()
                        if sub_val:
                            current_map_value[sub_key] = _yaml_value(sub_val)
                        continue

                    # Variant-level keys (indent 4, e.g. "    auth:")
                    if indent == 4 and ":" in stripped:
                        _flush_map()  # flush any previous map
                        key, _, val = stripped.partition(":")
                        key = key.strip()
                        val = val.strip()
                        if key in MAP_KEYS:
                            current_map_key = key
                            current_map_value = {}
                            # If there's an inline value, set it
                            if val and key not in MAP_KEYS:
                                current_variant[key] = _yaml_value(val)
                                current_map_key = ""
                        elif key in SCALAR_KEYS:
                            current_variant[key] = _yaml_value(val)
                        elif key in ALL_VARIANT_KEYS:
                            # Treat as scalar with empty value
                            current_variant[key] = _yaml_value(val) if val else ""
                        continue

    _flush_variant()
    return result


def _check_api_key_present(model_name: str, rbtv_cfg: dict, vault_root: Path) -> bool:
    """Check if an API key resolves for a model package. OS env first, then env_file.

    Root: VAULT root (where rbtv.json was found). rbtv.json's env_file is vault-relative
    (e.g. `.user/config/env/.env`), so it MUST resolve against vault_root, never the rbtv
    repo root. Manifest enumeration stays at rbtv_root (models/ folder lives there).
    """
    # The API-key env var is keyed by PROVIDER, not by the package's runtime-suffixed
    # id. Strip the runtime suffix (-api / -code-cli / -code-native / -cli) so e.g.
    # qwen-code-cli → QWEN_API_KEY and deepseek-api → DEEPSEEK_API_KEY (the canonical
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


def _get_auth_method(variant: dict) -> str:
    return variant.get("auth", {}).get("method", "none")


def _is_variant_available(variant: dict, model_name: str, rbtv_cfg: dict, vault_root: Path) -> bool:
    """Availability = key-present for api-key variants; cli-login/none always available.

    vault_root: vault root (where rbtv.json was found) — env_file resolution requires it.
    rbtv_root is the models/ folder root — NOT used here.
    """
    auth_method = _get_auth_method(variant)
    if auth_method == "api-key":
        return _check_api_key_present(model_name, rbtv_cfg, vault_root)
    # cli-login and none are not key-tested by the script
    return True


# ---------------------------------------------------------------------------
# Core routing logic
# ---------------------------------------------------------------------------

def _enumerate_models(rbtv_root: Path, vault_root: Path, rbtv_cfg: dict, explain_log: list) -> list:
    """Stage 1: enumerate every (model, variant) from the live models/ folder.

    rbtv_root: rbtv repo root (orchestration/models/ lives here — enumeration root).
    vault_root: vault root (where rbtv.json was found — env_file resolution root for availability).
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
        manifest = _load_manifest(manifest_path)
        model_name = manifest.get("model", d.name)
        pkg_evidence = manifest.get("evidence_status", "probe-pending")
        for v in manifest.get("variants", []):
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
                "reasoning_tier": v["reasoning_tier"],
                "context_window": int(v["context_window"]),
                "cost_class": v["cost_class"],
                "code_competence": v["code_competence"],
                "web_access": bool(v.get("web_access", False)),
                "evidence_status": variant_evidence,
                "auth_method": _get_auth_method(v),
                "specialty": v.get("specialty", ""),
                "invocation_pointer": v.get("invocation_pointer", ""),
                "raw_variant": v,
            })

    explain_log.append({"stage": "enumerate", "action": "complete", "count": len(entries), "models": sorted(set(e["model"] for e in entries))})
    return entries


def _apply_plan_caps(entries: list, plans: dict, explain_log: list) -> list:
    """Apply plan-overlay context window caps from the plans file."""
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


def _filter(entries: list, profile: dict, explain_log: list) -> list:
    """Stage 2: filter to variants meeting the leaf's hard requirements."""
    needed_tier = profile.get("needed_reasoning_tier", _boundedness_to_tier(profile))
    needed_code = profile.get("needed_code_competence", _task_type_to_code_level(profile))
    needs_web = profile.get("needs_web", False)
    inlined_size = profile.get("inlined_context_size", 0)

    survivors = []
    for e in entries:
        reasons_dropped = []

        # reasoning_tier check
        tier_val = TIER_VALUES.get(e["reasoning_tier"], -1)
        needed_val = TIER_VALUES.get(needed_tier, 0)
        if tier_val < needed_val:
            reasons_dropped.append(f"reasoning_tier {e['reasoning_tier']} < needed {needed_tier}")

        # context_window check
        if e["context_window"] < inlined_size:
            reasons_dropped.append(f"context_window {e['context_window']} < inlined_size {inlined_size}")

        # web_access check
        if needs_web and not e["web_access"]:
            reasons_dropped.append("needs web but web_access=false")

        # code_competence check
        code_levels = {"none": 0, "bounded": 1, "strong": 2}
        e_code = code_levels.get(e["code_competence"], 0)
        n_code = code_levels.get(needed_code, 0)
        if e_code < n_code:
            reasons_dropped.append(f"code_competence {e['code_competence']} < needed {needed_code}")

        if reasons_dropped:
            explain_log.append({
                "stage": "filter", "action": "drop", "model": e["model"],
                "variant": e["variant"], "reasons": reasons_dropped,
            })
        else:
            survivors.append(e)

    explain_log.append({"stage": "filter", "action": "complete", "survivors": len(survivors)})
    return survivors


def _boundedness_to_tier(profile: dict) -> str:
    """Map boundedness band to the minimum reasoning tier needed."""
    band = profile.get("boundedness", "fully-bounded")
    if band == "fully-bounded":
        return "non-reasoning"
    elif band == "partially-bounded":
        return "mid"
    else:  # unbounded
        return "top"


def _task_type_to_code_level(profile: dict) -> str:
    """Map task_type to required code_competence."""
    tt = profile.get("task_type", "text")
    if tt == "code":
        return "bounded"
    return "none"


def _rank(entries: list, profile: dict, explain_log: list) -> list:
    """Stage 3: rank survivors by the total order."""
    def _sort_key(e):
        cost_idx = COST_ORDER.index(e["cost_class"]) if e["cost_class"] in COST_ORDER else 99
        evidence_idx = EVIDENCE_ORDER.index(e["evidence_status"]) if e["evidence_status"] in EVIDENCE_ORDER else 99
        tier_val = TIER_VALUES.get(e["reasoning_tier"], 99)
        # For closest-not-over: we want the lowest tier that meets the requirement
        # Since we already filtered, all survivors meet the requirement.
        # closest-not-over = lowest tier value among survivors
        # Carrier tiebreak: among otherwise-tied top-tier Claude, the agent-tool
        # carrier (claude-code-native) is the default — rank the process carrier
        # (claude-code-cli) AFTER it. This preserves the pre-rename order, where the
        # old ids `claude` < `claude-cli` made agent-tool Claude the default pick;
        # the rename to claude-code-{cli,native} would otherwise flip that order.
        return (cost_idx, evidence_idx, tier_val, e["model"] == "claude-code-cli", e["model"], e["variant"])

    ranked = sorted(entries, key=_sort_key)
    explain_log.append({
        "stage": "rank", "action": "ranked",
        "order": [{"model": e["model"], "variant": e["variant"], "cost_class": e["cost_class"],
                   "evidence_status": e["evidence_status"], "reasoning_tier": e["reasoning_tier"]} for e in ranked],
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
    """Scope the enumerated set per boundedness band before Stage 2-3 (S2 keystone)."""
    band = profile.get("boundedness", "fully-bounded")
    if band == "fully-bounded":
        # No scoping — all variants eligible
        return entries
    elif band == "partially-bounded":
        # Scope to Claude mid-tier variants
        scoped = [e for e in entries if e["model"] in ("claude-code-native", "claude-code-cli") and e["reasoning_tier"] == "mid"]
        explain_log.append({
            "stage": "scope", "action": "partially-bounded",
            "scoped_to": "Claude mid-tier variants", "before": len(entries), "after": len(scoped),
        })
        return scoped
    else:  # unbounded — keystone: scope to top-tier Claude variants
        scoped = [e for e in entries if e["model"] in ("claude-code-native", "claude-code-cli") and e["reasoning_tier"] == "top"]
        explain_log.append({
            "stage": "scope", "action": "unbounded",
            "scoped_to": "top-tier Claude variants (keystone)", "before": len(entries), "after": len(scoped),
        })
        return scoped


def _resolve_carrier(entry: dict, profile: dict) -> str:
    """S8: resolve carrier based on chosen variant and profile flags."""
    model = entry["model"]
    needs_process = profile.get("needs_process_boundary", False)

    if model in ("kimi-code-cli", "codex-cli", "qwen-code-cli", "claude-code-cli"):
        return "cli-process"
    elif model == "claude-code-native":
        if needs_process:
            return "cli-process"
        return "agent-tool"
    # API chat workers (deepseek, gemini, manus, etc.)
    return "api"


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
) -> dict:
    """Behavior row 9 / S1 Stage 4: raise band one level, RE-RESOLVE, return the raised pick.

    The profile carries an already-assessed `stakes_tier` field. When it signals tier-up,
    we raise the band, re-scope, re-filter, re-rank — deterministically, no clock/randomness.
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
                "reason": "api-key absent in both OS env and env_file",
                "context": "stakes-tier-up re-resolution",
            })

    if not available:
        explain_log.append({
            "stage": "stakes", "action": "no_candidates_after_tier_up",
            "note": "zero variants available after stakes tier-up -- falling back to original pick",
        })
        return chosen

    # Re-filter at the raised requirement
    survivors = _filter(available, raised_profile, explain_log)
    if not survivors:
        explain_log.append({
            "stage": "stakes", "action": "no_survivors_after_tier_up",
            "note": "zero survivors after stakes tier-up -- falling back to original pick",
        })
        return chosen

    # S7: exclude haiku before the raised-band re-rank as well — a rank never picks haiku
    # absent the delegation-map flag (in practice the raised band's tier filter already drops
    # the non-reasoning haiku, but the guard holds wherever a rank decides a worker).
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


# Pinned-role floor definitions per spec Behavior row 10 / routing.md §3
_PINNED_FLOORS = {
    "reviewer": {
        "description": "≥ executor tier + 1, floor sonnet, never haiku",
        "floor_variant": "sonnet",
        "floor_models": ("claude-code-native", "claude-code-cli"),
        "floor_tier": "mid",
    },
    "debug": {
        "description": "Top-tier Claude (opus) — never a CLI/API worker (routing.md §3: never let a CLI worker root-cause)",
        "floor_variant": "opus",
        "floor_models": ("claude-code-native", "claude-code-cli"),
        "floor_tier": "top",
    },
    "commit": {
        "description": "Agent-tool Claude sonnet floor",
        "floor_variant": "sonnet",
        "floor_models": ("claude-code-native",),
        "floor_carrier": "agent-tool",
    },
}


def _apply_pinned_role_floor(
    chosen: dict, profile: dict, original_entries: list,
    rbtv_root: Path, vault_root: Path, rbtv_cfg: dict, plans: dict, explain_log: list,
) -> dict:
    """Behavior row 10 / S1 Stage 4: enforce pinned-role floors AFTER the cheapest pick.

    Raises the result to the floor when the pick lands below it.
    vault_root: vault root for env_file resolution (used by availability checks in re-scoping).
    """
    pinned_role = profile.get("pinned_role")
    if not pinned_role or pinned_role not in _PINNED_FLOORS:
        return chosen

    floor_def = _PINNED_FLOORS[pinned_role]
    explain_log.append({
        "stage": "pin", "action": "check_floor", "role": pinned_role,
        "current_pick": f"{chosen['model']}:{chosen['variant']}",
        "floor": floor_def["description"],
    })

    if pinned_role == "reviewer":
        # Opus reviews ALL external-CLI code (routing.md §3 / S3a).
        if profile.get("reviews_external_cli_code"):
            external_cli_opus = [
                e for e in original_entries
                if e["model"] in ("claude-code-native", "claude-code-cli")
                and e["variant"] == "opus"
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
            return chosen

        # Reviewer ≥ executor tier + 1, floor sonnet, never haiku
        executor_tier = profile.get("executor_tier", "non-reasoning")
        executor_idx = TIER_VALUES.get(executor_tier, 0)
        required_idx = min(executor_idx + 1, 2)  # cap at top
        # Floor at sonnet (mid) — reviewer is a Claude-specific floor per routing.md §3
        required_idx = max(required_idx, TIER_VALUES.get("mid", 1))

        chosen_tier_idx = TIER_VALUES.get(chosen["reasoning_tier"], 0)
        if chosen_tier_idx >= required_idx:
            explain_log.append({
                "stage": "pin", "action": "floor_already_met",
                "role": pinned_role, "reason": f"current tier {chosen['reasoning_tier']} ≥ required idx {required_idx}",
            })
            return chosen

        # Need to raise: reviewer floors at Claude mid+ (routing.md §3)
        scoped_entries = list(original_entries)
        # Scope to Claude variants for reviewer pin
        claude_entries = [e for e in scoped_entries if e["model"] in ("claude-code-native", "claude-code-cli")]
        scoped = _scope_eligible_set(claude_entries, profile, explain_log)
        scoped = _apply_plan_caps(scoped, plans, explain_log)

        # Filter to Claude variants meeting the floor tier
        floor_survivors = []
        for e in scoped:
            e_idx = TIER_VALUES.get(e["reasoning_tier"], 0)
            if e_idx >= required_idx:
                floor_survivors.append(e)

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
        # Top-tier CLAUDE (opus) — routing.md §3: debug floors at opus and NEVER lets a
        # CLI/API worker root-cause. A top-tier non-Claude (e.g. deepseek:v4-pro) does NOT
        # satisfy this floor; require BOTH top-tier AND Claude membership.
        if chosen["model"] in ("claude-code-native", "claude-code-cli") and chosen["reasoning_tier"] == "top":
            explain_log.append({
                "stage": "pin", "action": "floor_already_met",
                "role": pinned_role, "reason": f"already top-tier Claude: {chosen['model']}:{chosen['variant']}",
            })
            return chosen
        # Find cheapest top-tier CLAUDE variant
        scoped_entries = [e for e in original_entries if e["model"] in ("claude-code-native", "claude-code-cli")]
        scoped = _apply_plan_caps(scoped_entries, plans, explain_log)
        top_survivors = [e for e in scoped if e["reasoning_tier"] == "top"]
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
        # Agent-tool Claude sonnet floor
        if chosen["model"] in ("claude-code-native",) and chosen.get("reasoning_tier") in ("mid", "top"):
            explain_log.append({
                "stage": "pin", "action": "floor_already_met",
                "role": pinned_role, "reason": f"already Claude mid/top: {chosen['model']}:{chosen['variant']}",
            })
            return chosen
        # Find cheapest Claude sonnet
        scoped_entries = list(original_entries)
        scoped = _scope_eligible_set(scoped_entries, profile, explain_log)
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

    explain_log.append({
        "stage": "pin", "action": "floor_not_found",
        "role": pinned_role, "reason": "no variant met the floor -- keeping original pick",
    })
    return chosen


def _apply_pins_and_stakes(
    chosen: dict, profile: dict, original_entries: list,
    rbtv_root: Path, vault_root: Path, rbtv_cfg: dict, plans: dict, explain_log: list,
) -> dict:
    """S1 Stage 4 / S3: apply stakes tier-up and pinned-role floors AFTER the cheapest pick.

    Stakes tier-up raises the band and RE-RESOLVES the selection (re-filter + re-rank).
    Pinned-role floors raise the result when the pick lands below the floor.
    vault_root: vault root for env_file resolution (used by _apply_stakes_tier_up availability).
    """
    result = chosen

    # Stakes tier-up (Behavior row 9)
    if profile.get("stakes_tier") == "tier_up":
        result = _apply_stakes_tier_up(
            result, profile, original_entries, rbtv_root, vault_root, rbtv_cfg, plans, explain_log,
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


def route(profile: dict, rbtv_root: Path, vault_root: Path, rbtv_cfg: dict, plans: dict, explain: bool = False) -> dict:
    """Main routing function. Returns a verdict dict.

    rbtv_root: rbtv repo root (orchestration/models/ lives here — enumeration root).
    vault_root: vault root (where rbtv.json was found — env_file/model_plans_file resolution root).
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

    # Stage 1: enumerate (rbtv_root = models/ folder; vault_root = env_file resolution)
    entries = _enumerate_models(rbtv_root, vault_root, rbtv_cfg, explain_log)
    if not entries:
        return {"error": "no_models", "details": "No installed model packages found in models/"}

    # Preserve the FULL enumerated set (pre-scope) for the pins/stakes layer. Stakes tier-up
    # and the pinned-role floors must re-scope at the RAISED band over the full enumeration —
    # not over this band's leftovers. Passing the band-scoped set here would empty the raised-band
    # re-scope (e.g. partially-bounded scoped to Claude mid-tier → stakes raise to top-tier Claude
    # finds zero in a mid-tier-only set), silently masking the escalation.
    all_entries = list(entries)

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
                "variant": e["variant"], "reason": "api-key absent in both OS env and env_file",
            })

    if not available:
        return {"error": "no_available_variants", "details": "All variants dropped due to availability (api-key absent)"}

    # Stage 2: filter
    survivors = _filter(available, profile, explain_log)
    if not survivors:
        return {
            "error": "zero_candidates",
            "details": "No installed+available variant meets the leaf's hard requirements",
            "failed_requirements": [log for log in explain_log if log.get("action") == "drop"]
        }

    # S7: exclude haiku variants from the eligible set BEFORE Stage-3 ranking (unless the
    # delegation-map flag admits them). Default-excludes so a future cheapest haiku is never
    # auto-picked by cost-ascending ranking absent an approved delegation map (routing.md §7).
    survivors = _exclude_haiku(survivors, profile, explain_log)
    if not survivors:
        return {
            "error": "zero_candidates",
            "details": "No installed+available non-haiku variant meets the leaf's hard requirements (haiku excluded per routing.md §7; set delegation_map_allows_haiku to admit haiku for a mechanical batch)",
            "failed_requirements": [log for log in explain_log if log.get("action") in ("drop", "exclude")]
        }

    # Stage 3: rank
    ranked = _rank(survivors, profile, explain_log)
    chosen = ranked[0]

    # Apply pins/stakes over the FULL enumeration (re-resolution re-scopes at the raised band).
    chosen = _apply_pins_and_stakes(
        chosen, profile, all_entries, rbtv_root, vault_root, rbtv_cfg, plans, explain_log,
    )

    # Resolve carrier
    carrier = _resolve_carrier(chosen, profile)

    verdict = {
        "verdict": "route",
        "model": chosen["model"],
        "variant": chosen["variant"],
        "carrier": carrier,
    }

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
    args = parser.parse_args()

    # Load profile
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

    rbtv_cfg = _load_rbtv_json(vault_root)
    plans = _load_model_plans(vault_root, rbtv_cfg)

    # Route
    result = route(profile, rbtv_root, vault_root, rbtv_cfg, plans, explain=args.explain)

    # Output
    output = json.dumps(result, indent=2, ensure_ascii=False)
    print(output)

    # Exit code
    if "error" in result:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
