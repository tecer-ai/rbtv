"""Orchestration install behavior: permission-rules sync, plan-cap IO, hook wire.

The routable worker set is the cast catalog intersect availability — the
installer does not elect it. Leftover rbtv.json keys model_packages /
model_variants are left in place and unread.

Permission-rule strings and per-model context windows are read from the cast
catalog (catalog.js), not from orchestration/models manifests.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

# Vault-relative path to the one catalog. Walked from rbtv_root toward filesystem
# root so a scratch target still resolves the workspace catalog.
_CATALOG_RELATIVE = (
    Path(".rbtv") / "mirror" / "meta" / "providers" / "capabilities" / "cast" / "tool" / "catalog.js"
)


def find_catalog_js(start: Path) -> Path | None:
    """Walk from *start* toward the filesystem root for the cast catalog.js."""
    current = start.resolve()
    for directory in [current] + list(current.parents):
        candidate = directory / _CATALOG_RELATIVE
        if candidate.is_file():
            return candidate
    return None


def load_catalog(rbtv_root: Path) -> dict:
    """Read catalog.js as data via node: {rows, permission_rules}.

    Soft-empty on a missing catalog or a failed node invoke — callers treat
    that as 'no rules / no windows', never an install abort.
    """
    catalog = find_catalog_js(rbtv_root)
    if catalog is None:
        return {"rows": [], "permission_rules": {}}
    script = (
        "const c=require(process.argv[1]);"
        "process.stdout.write(JSON.stringify({"
        "rows:c.ROWS,"
        "permission_rules:c.PERMISSION_RULES||{}"
        "}))"
    )
    try:
        proc = subprocess.run(
            ["node", "-e", script, str(catalog)],
            capture_output=True,
            text=True,
        )
    except OSError:
        return {"rows": [], "permission_rules": {}}
    if proc.returncode != 0:
        return {"rows": [], "permission_rules": {}}
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"rows": [], "permission_rules": {}}
    if not isinstance(data, dict):
        return {"rows": [], "permission_rules": {}}
    rows = data.get("rows") if isinstance(data.get("rows"), list) else []
    rules = data.get("permission_rules") if isinstance(data.get("permission_rules"), dict) else {}
    return {"rows": rows, "permission_rules": rules}


def _scalar_value(raw: str) -> str:
    """Extract a YAML scalar from a line's value portion: unwrap one layer of quotes,
    else strip an inline ``#`` comment. Stdlib-only line-scan posture (no YAML parser),
    matching read_model_display. Handles a quoted value followed by a comment
    (e.g. ``"DeepSeek V4 Flash"   # note`` → ``DeepSeek V4 Flash``)."""
    raw = raw.strip()
    if raw and raw[0] in "\"'":
        end = raw.find(raw[0], 1)
        if end != -1:
            return raw[1:end]
    return raw.split("#", 1)[0].strip()


def _model_family(model: str) -> str:
    """Short family label: ``fable-5`` → ``fable``, ``haiku-4-5`` → ``haiku``."""
    return (model or "").split("-", 1)[0]


def _cli_rows_for_harness(rbtv_root: Path, harness: str) -> list[dict]:
    return [
        row
        for row in load_catalog(rbtv_root).get("rows") or []
        if isinstance(row, dict)
        and row.get("harness") == harness
        and row.get("carrier") == "cli"
    ]


def read_variant_windows(rbtv_root: Path, pkg: str) -> list[tuple[str, int]]:
    """Return a harness's CLI catalog rows as ``(family_label, context_window)`` pairs.

    ``pkg`` is a catalog harness (``claude``, ``codex``, ``opencode``). Order
    follows the catalog. Rows with no integer ``context_window`` are skipped.
    Duplicate family labels keep the first (CLI) window.

    Backs the plan-cap clobber warning (clobbered_variants): a harness whose
    models carry DIFFERENT windows (e.g. claude: opus 1M, haiku 200K) is exactly
    where a single cap silently shrinks the bigger model below its native window.
    """
    pairs: list[tuple[str, int]] = []
    seen: set[str] = set()
    for row in _cli_rows_for_harness(rbtv_root, pkg):
        label = _model_family(str(row.get("model") or ""))
        win = row.get("context_window")
        if not label or not isinstance(win, int) or label in seen:
            continue
        seen.add(label)
        pairs.append((label, win))
    return pairs


def read_manifest_context_ceiling(rbtv_root: Path, pkg: str) -> int | None:
    """Return a harness's largest catalog ``context_window`` (its true ceiling).

    The per-user plan cap (model-plans.yaml) caps AT this ceiling — a preset
    above it has no effect. Returns None when no integer value is found.
    """
    best: int | None = None
    for _label, win in read_variant_windows(rbtv_root, pkg):
        if best is None or win > best:
            best = win
    return best


# Standard per-model plan-size presets (tokens) offered by the installer's cap
# pick-list (D14). The owner picks a plan SIZE from this menu — never types a raw
# token number. Each label names the size in K/M for readability; the value is the
# context_window cap written to model-plans.yaml. A preset above a package's manifest
# ceiling is omitted from that package's menu (it would never bind — route.py caps at
# the manifest window). "No cap" writes no context_window (the manifest window stands).
PLAN_SIZE_PRESETS: list[tuple[str, int | None]] = [
    ("No cap (use the model's full context window)", None),
    ("128K tokens", 128000),
    ("200K tokens", 200000),
    ("256K tokens", 256000),
    ("512K tokens", 512000),
    ("1M tokens", 1000000),
]


def build_plan_size_presets(ceiling: int | None) -> list[tuple[str, int | None]]:
    """Return the plan-size presets offered for a package, given its manifest ceiling.

    Drops any numeric preset ABOVE the ceiling (it could never bind — route.py applies
    min(manifest_window, cap)), always keeping the "No cap" option. When the ceiling is
    unknown (None), returns the full ladder. Order preserves PLAN_SIZE_PRESETS.
    """
    if ceiling is None:
        return list(PLAN_SIZE_PRESETS)
    return [
        (label, val)
        for label, val in PLAN_SIZE_PRESETS
        if val is None or val <= ceiling
    ]


def clobbered_variants(
    rbtv_root: Path, pkg: str, cap: int | None
) -> list[tuple[str, int]]:
    """The package variants a chosen plan-size ``cap`` would shrink below their native
    context window — every variant whose manifest ``context_window`` EXCEEDS ``cap``.

    Empty when ``cap`` is None ("no cap") or no variant's window exceeds it (a cap at or
    above the largest native window — no clobber). A NON-EMPTY result is the multi-model
    foot-gun: one per-harness cap applies as ``min(window, cap)`` to EVERY model, so
    a sub-largest cap silently shrinks the bigger model (e.g. cap 200K on claude
    clobbers opus's 1M while haiku, native 200K, is untouched). The installer WARNS,
    naming these models, so the owner tells a deliberate uniform-subscription ceiling from an
    accidental clobber. Order follows the catalog (read_variant_windows).
    """
    if cap is None:
        return []
    return [
        (label, win)
        for label, win in read_variant_windows(rbtv_root, pkg)
        if win > cap
    ]


def read_model_plan_caps(plans_path: Path) -> dict[str, int]:
    """Read the existing model-plans.yaml → {package_id: context_window} (cap-only, D14).

    Returns only entries that carry an integer `context_window`. Used to RE-CONFIRM a
    previously-chosen cap on reinstall (the prior value is pre-selected in the pick-list,
    never silently wiped). Absent/unreadable file or no caps => empty dict. Stdlib-only
    line scan over the `plans:` list — mirrors route.py's _parse_plans_yaml shape but
    keeps only the cap field. Tolerates inline (`- model: codex-cli`) and continuation
    forms.
    """
    caps: dict[str, int] = {}
    current_model: str | None = None
    current_cap: int | None = None

    def _flush() -> None:
        if current_model and current_cap is not None:
            caps[current_model] = current_cap

    if not plans_path.is_file():
        return caps
    try:
        text = plans_path.read_text(encoding="utf-8")
    except OSError:
        return caps
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped == "---":
            continue
        if stripped == "plans:" or stripped.rstrip(":") == "plans":
            continue
        if stripped.startswith("-"):
            _flush()
            current_model = None
            current_cap = None
            inline = stripped[1:].strip()
            if inline and ":" in inline:
                key, _, val = inline.partition(":")
                if key.strip() == "model":
                    current_model = _scalar_value(val) or None
                elif key.strip() == "context_window":
                    try:
                        current_cap = int(_scalar_value(val))
                    except (TypeError, ValueError):
                        current_cap = None
            continue
        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            if key == "model":
                current_model = _scalar_value(val) or None
            elif key == "context_window":
                try:
                    current_cap = int(_scalar_value(val))
                except (TypeError, ValueError):
                    current_cap = None
    _flush()
    return caps


def read_model_plan_models(plans_path: Path) -> list[str]:
    """Read the existing model-plans.yaml → ordered list of every package id present.

    Unlike read_model_plan_caps (which keeps only entries carrying an integer
    `context_window`), this returns EVERY `- model:` entry — including packages set to
    "no cap" (no `context_window` line). Used to tell a PREVIOUSLY-CONFIGURED package
    (present in the file, regardless of its cap) from a genuinely NEW one (absent), so the
    installer can skip re-prompting models the owner already sized. Absent/unreadable file
    => empty list. Stdlib-only line scan mirroring read_model_plan_caps' posture.
    """
    models: list[str] = []
    if not plans_path.is_file():
        return models
    try:
        text = plans_path.read_text(encoding="utf-8")
    except OSError:
        return models
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or stripped == "---":
            continue
        if stripped == "plans:" or stripped.rstrip(":") == "plans":
            continue
        model_id: str | None = None
        if stripped.startswith("-"):
            inline = stripped[1:].strip()
            if inline.startswith("model:"):
                model_id = _scalar_value(inline[len("model:"):]) or None
        elif stripped.startswith("model:"):
            model_id = _scalar_value(stripped[len("model:"):]) or None
        if model_id and model_id not in models:
            models.append(model_id)
    return models


def write_model_plan_caps(
    plans_path: Path,
    caps: dict[str, int | None],
    displays: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """Write the cap-only model-plans.yaml from {package_id: context_window | None} (D14).

    One `plans:` entry per package in `caps`, in the order given. A package mapped to an
    integer writes `context_window: <int>`; a package mapped to None writes NO
    context_window (the manifest window stands — the router applies no cap). The file is
    rewritten cap-only — the retired cost rows (cost_usd_per_m_*) are never emitted (D11).
    `displays` supplies a per-package comment label (the manifest display) when present.

    Returns (changed, message). Idempotent: an unchanged file is not rewritten. Creates
    the parent directory if needed. The package id MUST equal the manifest `model:` id so
    route.py's _apply_plan_caps (keyed on that id) actually binds the cap.
    """
    displays = displays or {}
    lines = [
        "# model-plans.yaml — per-model subscription-plan context-window caps (cap-only, D14).",
        "# Read by the router script (route.py) for effective context-window caps.",
        "# Cost is NOT here: it is a board-derived 1-7 integer in the model manifests (D11).",
        "# Filled by the installer from a per-model plan-size preset pick-list; a prior",
        "# choice is re-confirmed (offered as the default) on reinstall, never wiped.",
        "---",
        "plans:",
    ]
    for pkg, cap in caps.items():
        label = displays.get(pkg)
        comment = f"  # {label}" if label else ""
        lines.append(f"  - model: {pkg}{comment}")
        if cap is not None:
            lines.append(f"    context_window: {int(cap)}")
        else:
            lines.append("    # context_window: (no cap — the model's full window applies)")
        lines.append("")
    # Drop the trailing blank separator line, keep a single trailing newline.
    while lines and lines[-1] == "":
        lines.pop()
    new_text = "\n".join(lines) + "\n"

    existing = ""
    if plans_path.is_file():
        try:
            existing = plans_path.read_text(encoding="utf-8")
        except OSError:
            existing = ""
    if existing == new_text:
        return False, f"model plans: caps already current ({plans_path.as_posix()})"

    plans_path.parent.mkdir(parents=True, exist_ok=True)
    plans_path.write_text(new_text, encoding="utf-8")
    set_caps = [f"{p}={c}" for p, c in caps.items() if c is not None]
    detail = ", ".join(set_caps) if set_caps else "no caps set"
    return True, f"model plans: wrote caps to {plans_path.as_posix()} ({detail})"


def read_permission_rules(rbtv_root: Path, harness: str | None = None) -> list[str]:
    """Return the catalog's permission-rule strings for launchable CLI workers.

    These are the literal permission-allowlist strings (e.g. "Bash(opencode:*)")
    the target workspace needs so a conductor session may spawn this CLI
    worker in-session (D17). API / agent-tool carriers declare none. When
    *harness* is None, returns the union across every harness the catalog
    exports, in catalog order. A named harness with no export returns [].
    """
    rules_map = load_catalog(rbtv_root).get("permission_rules") or {}
    if not isinstance(rules_map, dict):
        return []
    if harness is not None:
        raw = rules_map.get(harness) or []
        return [r for r in raw if isinstance(r, str) and r]
    wanted: list[str] = []
    for raw in rules_map.values():
        if not isinstance(raw, list):
            continue
        for rule in raw:
            if isinstance(rule, str) and rule and rule not in wanted:
                wanted.append(rule)
    return wanted


def sync_permission_rules(
    target_root: Path, rbtv_root: Path
) -> tuple[bool, str]:
    """Reconcile the target's `.claude/settings.local.json` permission allowlist
    with the catalog's launchable-CLI rules (D17).

    Ensures every string the catalog declares for launchable CLI workers is
    present in `permissions.allow`. There is no elected/absent split — the
    union is synced. Touches ONLY those catalog-declared strings — hand-added
    entries are never modified. Idempotent. Fails soft (returns False +
    message) on a malformed settings file rather than clobbering it.
    """
    settings_path = target_root / ".claude" / "settings.local.json"

    wanted = read_permission_rules(rbtv_root)
    unwanted: set[str] = set()

    if not wanted and not unwanted:
        return False, "permission sync: catalog declares no permission rules"

    settings: dict = {}
    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return False, (
                f"permission sync skipped: could not parse "
                f"{settings_path.as_posix()} ({exc}) — fix the file and re-run"
            )
        if not isinstance(settings, dict):
            return False, (
                f"permission sync skipped: {settings_path.as_posix()} is not a "
                "JSON object — fix the file and re-run"
            )

    permissions = settings.setdefault("permissions", {})
    if not isinstance(permissions, dict):
        return False, (
            f"permission sync skipped: 'permissions' in "
            f"{settings_path.as_posix()} is not an object — fix the file and re-run"
        )
    allow = permissions.setdefault("allow", [])
    if not isinstance(allow, list):
        return False, (
            f"permission sync skipped: 'permissions.allow' in "
            f"{settings_path.as_posix()} is not a list — fix the file and re-run"
        )

    added = [r for r in wanted if r not in allow]
    removed = [r for r in allow if r in unwanted]
    if not added and not removed:
        return False, (
            "permission sync: allowlist already current "
            f"(managed entries: {', '.join(wanted) or 'none'})"
        )

    permissions["allow"] = [r for r in allow if r not in unwanted] + added
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8"
    )
    parts = []
    if added:
        parts.append(f"added {', '.join(added)}")
    if removed:
        parts.append(f"removed {', '.join(removed)}")
    return True, (
        f"permission sync: {'; '.join(parts)} in "
        f"{settings_path.relative_to(target_root).as_posix()}"
    )


# The rbtv-managed hook entry is identified by this stable sentinel so a later
# unwire (p2-2) removes ONLY it and never touches hand-added entries.
_HOOK_SENTINEL = "rbtv:context-monitor"

# Path to the hook script, relative to the RBTV repo root.
_CONTEXT_MONITOR_RELATIVE = Path("orchestration") / "hooks" / "context-monitor.py"

# Stable command-path signature of the rbtv hook (the rbtv-owned script the entry
# always invokes). Used as a HARNESS-ROBUST fallback identifier: Claude Code owns
# settings.local.json at runtime and may re-serialize it (it persists /config,
# /model, /effort, permission-prompt edits), with no documented guarantee that an
# unknown top-level entry key (`__rbtv__`) survives that round-trip. So identity
# keys on EITHER the sentinel (fast path, present when preserved) OR this intrinsic
# script signature (survives even if the sentinel is stripped) — so neither this
# wire's idempotency nor p2-2's unwire can orphan an entry whose key was dropped.
_HOOK_COMMAND_SIGNATURE = _CONTEXT_MONITOR_RELATIVE.as_posix()

# POSIX prefix resolving the interpreter NAME at hook-run time. `.claude/
# settings.local.json` is git-tracked and shared across machines, so an
# install-time interpreter breaks every other machine — see
# `_build_cwd_independent_command`.
_PY_PICK = 'command -v python >/dev/null 2>&1 && RBTVPY=python || RBTVPY=python3;'


def _build_cwd_independent_command(
    interpreter: str, script_posix: str, extra_args: list[str] | None = None
) -> str:
    """A hook command whose script resolution does not depend on the session's cwd.

    Claude Code sets `$CLAUDE_PROJECT_DIR` to the SESSION's cwd, not necessarily the
    repo root — a session one or more levels below the repo root (a worktree, a
    per-seat subfolder) gets a non-existent joined path and the plain
    `$CLAUDE_PROJECT_DIR`-relative command errors on every matched tool call
    (observed 2026-07-24, a team-kit run with per-seat working directories). This
    wraps the invocation in a small Python resolver that reads `CLAUDE_PROJECT_DIR`
    from `os.environ` directly (shell-syntax independent — the same command runs
    under sh/bash/cmd/PowerShell), walks up from there to the nearest ancestor
    holding a `.git` directory (the real repo root), then joins `script_posix`. No
    match (e.g. a differently laid out machine) exits 0 silently — never a hard
    error.

    ``interpreter`` is IGNORED for the emitted name (kept for call compatibility):
    the interpreter is resolved when the hook RUNS, via `_PY_PICK`. Baking one at
    install time is wrong here because `.claude/settings.local.json` is git-tracked
    and shared across machines — an absolute ``sys.executable`` captured on the
    Linux VPS is a nonexistent path on Windows, and vice versa (observed 2026-07-31:
    a baked ``/usr/bin/python3`` failed every hook run on the Windows desktop).
    `_PY_PICK` is POSIX-shell syntax, so the entry pins ``"shell": "bash"``.
    """
    tail = "" if not extra_args else "," + ",".join(repr(a) for a in extra_args)
    code = (
        "import os,sys,subprocess as s;"
        "c=os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd();"
        "parts=c.split(os.sep);"
        "cands=[os.sep.join(parts[:len(parts)-i]) or os.sep for i in range(0,len(parts))];"
        "d=next((x for x in cands if x and os.path.isdir(os.path.join(x,'.git'))),None);"
        f"p=os.path.join(d,{script_posix!r}) if d else None;"
        f"sys.exit(s.call([sys.executable,p{tail}]) if p and os.path.isfile(p) else 0)"
    )
    return f'{_PY_PICK} "$RBTVPY" -c "{code}"'


def _entry_commands(entry: dict) -> list[str]:
    """Every ``command`` string inside a PostToolUse matcher entry's ``hooks`` list.

    Tolerates a malformed-but-parseable entry (missing/empty/oddly-typed ``hooks``)
    without raising — returns ``[]`` so the caller's membership test is simply False.
    """
    if not isinstance(entry, dict):
        return []
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        return []
    out: list[str] = []
    for h in hooks:
        if isinstance(h, dict):
            cmd = h.get("command")
            if isinstance(cmd, str):
                out.append(cmd)
    return out


def _is_rbtv_hook_entry(entry: dict) -> bool:
    """True when a PostToolUse entry is the rbtv-managed one.

    Matches on EITHER the injected sentinel key (fast path) OR the intrinsic rbtv
    script-path signature in any of its commands (harness-robust: survives the
    sentinel being stripped on a settings re-serialize). A foreign hook invoking an
    unrelated command matches neither and is left untouched.

    OWNERSHIP OUTRANKS THE SIGNATURE. An entry carrying ANOTHER component's `__*__`
    ownership marker (`__sb__`, …) is foreign no matter what it invokes — a wrapper
    around the rbtv script is still someone else's entry, and `sync_hook_entry()`
    DELETES what this returns True for, so an over-match destroys a foreign entry
    whole (marker, matcher and command). The signature fallback exists only to
    re-adopt an entry whose OWN `__rbtv__` key the harness stripped, and a stripped
    entry carries no ownership marker at all — so declining on a foreign marker
    costs that fallback nothing.
    """
    if not isinstance(entry, dict):
        return False
    if entry.get("__rbtv__") == _HOOK_SENTINEL:
        return True
    if any(
        k != "__rbtv__" and k.startswith("__") and k.endswith("__") and len(k) > 4
        for k in entry
    ):
        return False
    return any(_HOOK_COMMAND_SIGNATURE in cmd for cmd in _entry_commands(entry))


def sync_hook_entry(
    target_root: Path, rbtv_relative: Path
) -> tuple[bool, str]:
    """Wire the context-monitor PostToolUse hook into `.claude/settings.local.json`.

    Mirrors the `sync_permission_rules()` read→merge→write pattern:
    - Reads the settings file (or starts from {}).
    - Removes any existing rbtv-managed hook entry (identified by `_HOOK_SENTINEL`).
    - Inserts exactly one fresh entry at the end of the PostToolUse list.
    - Writes back, preserving every unrelated key.

    The hook ``command`` is built by `_build_cwd_independent_command()`: a small Python
    resolver, wrapping ``rbtv_relative`` (the per-user relative path to the RBTV
    install, baked at install time), that reads Claude Code's ``$CLAUDE_PROJECT_DIR``
    from its OWN environment and walks up to the nearest ``.git`` ancestor before
    joining the script path — so it resolves from ANY working directory (including a
    session whose cwd sits below the repo root) and on ANY machine, never a hardcoded
    absolute path. (A bare ``$CLAUDE_PROJECT_DIR``-relative command broke when Claude
    Code ran the hook from a non-repo-root CWD — see `_build_cwd_independent_command`.)

    The interpreter is NOT baked at install time. It is picked when the hook runs —
    ``python`` if present, else ``python3`` — and the entry pins ``"shell": "bash"``
    so that POSIX prefix parses on Windows too. Baking either a bare name or the
    installing machine's ``sys.executable`` is wrong: this settings file is commonly
    git-tracked and shared across machines, so whichever machine installed last
    breaks the hook on all the others (observed 2026-07-31 — a ``/usr/bin/python3``
    baked on the Linux VPS errored on every hook run on the Windows desktop).

    Idempotent: re-running replaces any stale entry with the current resolved path.
    Fails soft (returns False + message) on a malformed settings file.

    Scope: WIRE only. The unwire/removal path is p2-2's job.
    """
    settings_path = target_root / ".claude" / "settings.local.json"

    # Resolve the script path relative to target_root using rbtv_relative.
    # The command string uses forward slashes and quotes the path to handle spaces.
    script_posix = (rbtv_relative / _CONTEXT_MONITOR_RELATIVE).as_posix()
    # No interpreter is baked: the emitted command picks python/python3 when it
    # RUNS (see `_build_cwd_independent_command`), because this settings file is
    # shared across machines with different Python names and locations.
    command_str = _build_cwd_independent_command("", script_posix)

    # The entry the installer owns, identifiable by _HOOK_SENTINEL.
    rbtv_entry: dict = {
        "__rbtv__": _HOOK_SENTINEL,
        "matcher": "",
        # shell: bash — the command carries a POSIX interpreter picker (_PY_PICK)
        # that PowerShell cannot parse.
        "hooks": [{"type": "command", "command": command_str, "shell": "bash"}],
    }

    settings: dict = {}
    if settings_path.is_file():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return False, (
                f"hook sync skipped: could not parse "
                f"{settings_path.as_posix()} ({exc}) — fix the file and re-run"
            )
        if not isinstance(settings, dict):
            return False, (
                f"hook sync skipped: {settings_path.as_posix()} is not a "
                "JSON object — fix the file and re-run"
            )

    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        return False, (
            f"hook sync skipped: 'hooks' in "
            f"{settings_path.as_posix()} is not an object — fix the file and re-run"
        )
    post_tool_use = hooks.setdefault("PostToolUse", [])
    if not isinstance(post_tool_use, list):
        return False, (
            f"hook sync skipped: 'hooks.PostToolUse' in "
            f"{settings_path.as_posix()} is not a list — fix the file and re-run"
        )

    # Remove any existing rbtv-managed entry (idempotent: stale path gets replaced).
    # Identity is sentinel-OR-script-signature so an entry whose injected key the
    # harness dropped is still recognized (and replaced, not duplicated).
    without_rbtv = [e for e in post_tool_use if not _is_rbtv_hook_entry(e)]
    already_current = (
        len(without_rbtv) == len(post_tool_use) - 1
        and any(
            _is_rbtv_hook_entry(e) and command_str in _entry_commands(e)
            for e in post_tool_use
        )
    )
    if already_current:
        return False, (
            f"hook sync: PostToolUse entry already current "
            f"({settings_path.relative_to(target_root).as_posix()})"
        )

    hooks["PostToolUse"] = without_rbtv + [rbtv_entry]
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8"
    )
    verb = "updated" if len(without_rbtv) < len(post_tool_use) else "added"
    return True, (
        f"hook sync: {verb} rbtv PostToolUse entry in "
        f"{settings_path.relative_to(target_root).as_posix()}"
    )


def remove_hook_entry(target_root: Path) -> tuple[bool, str]:
    """Unwire the rbtv-managed context-monitor PostToolUse hook from `.claude/settings.local.json`.

    Mirrors the `sync_hook_entry()` read→merge→write pattern but REMOVES
    rather than inserts:
    - Reads the settings file (or returns a no-op success when absent).
    - Drops every entry where `_is_rbtv_hook_entry` is True (sentinel OR command
      signature — ADX-1: never key-only).
    - Writes back, preserving every unrelated key (foreign hooks, permissions, …).

    No-op success when:
    - The settings file does not exist.
    - The ``hooks`` key or ``PostToolUse`` list is absent.
    - No rbtv-managed entry is present (already-unwired / idempotent).

    Fails soft (returns False + message) on a malformed settings file.

    Scope: UNWIRE only (p2-2). The wire path lives in `sync_hook_entry`.
    """
    settings_path = target_root / ".claude" / "settings.local.json"

    if not settings_path.is_file():
        return False, "hook unwire: no settings file — nothing to remove"

    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, (
            f"hook unwire skipped: could not parse "
            f"{settings_path.as_posix()} ({exc}) — fix the file and re-run"
        )
    if not isinstance(settings, dict):
        return False, (
            f"hook unwire skipped: {settings_path.as_posix()} is not a "
            "JSON object — fix the file and re-run"
        )

    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False, "hook unwire: no hooks object — nothing to remove"

    post_tool_use = hooks.get("PostToolUse")
    if not isinstance(post_tool_use, list):
        return False, "hook unwire: no PostToolUse list — nothing to remove"

    without_rbtv = [e for e in post_tool_use if not _is_rbtv_hook_entry(e)]
    if len(without_rbtv) == len(post_tool_use):
        return False, (
            f"hook unwire: no rbtv PostToolUse entry found — already absent "
            f"({settings_path.relative_to(target_root).as_posix()})"
        )

    hooks["PostToolUse"] = without_rbtv
    settings_path.write_text(
        json.dumps(settings, indent=2) + "\n", encoding="utf-8"
    )
    n_removed = len(post_tool_use) - len(without_rbtv)
    return True, (
        f"hook unwire: removed {n_removed} rbtv PostToolUse "
        f"{'entry' if n_removed == 1 else 'entries'} from "
        f"{settings_path.relative_to(target_root).as_posix()}"
    )



