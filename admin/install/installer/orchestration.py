"""Orchestration model-package install behavior (D18).

The `rbtv-orchestrating` skill ships per-model DOC PACKAGES under
`orchestration/models/<model>/` (manifest, delta, rendered manual, mirror
config). Unlike skills/commands, these packages are NOT copied into the target
`.claude/` — they are read just-in-time from the RBTV source repo (`{rbtv_path}`),
exactly like the cards. "Installing a model package" therefore means TWO things:

  1. Recording which packages the workspace elects (persisted in rbtv.json), so a
     re-install remembers the selection — the per-model conditional install flag.
  2. Baking the resulting availability line into the skill-loaded core
     (`core-protocol.md`) between the `ORCH:AVAILABILITY` markers, so the
     always-loaded capability summary names what is present and what is absent in
     THIS workspace.

Plus a render-freshness check: the rendered manuals are generated from the
dispatch-wrapper template + each delta; this verifies they are not stale relative
to their sources (it calls `render-manuals.py --check`).

Single-shared-source caveat: the `ORCH:AVAILABILITY` markers live in the repo's
`core-protocol.md`, which every workspace's installed SKILL.md loads BY REFERENCE
(it is not copied per workspace). The bake writes the line into that one shared
file. When a single RBTV source repo serves multiple workspaces, the LAST install
wins the availability line. The markers are preserved so re-install is idempotent.
This is the same single-source property the cards and rendered manuals already
have (one repo, N workspaces by reference); per-workspace divergence is out of
D18's scope.

No external dependencies — Python 3.11+ only (the manifest read is a single line
scan, not a YAML parse).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Where the model packages live, relative to the RBTV repo root.
MODELS_RELATIVE = Path("orchestration") / "models"
# The skill-loaded core that carries the availability marker region.
CORE_PROTOCOL_RELATIVE = (
    Path("orchestration") / "skills" / "orchestrating" / "core-protocol.md"
)
# The render script whose --check reports manual drift.
RENDER_SCRIPT_RELATIVE = MODELS_RELATIVE / "render-manuals.py"

# A directory under orchestration/models/ is a MODEL PACKAGE iff it carries a
# manifest.yaml. Infra dirs (_fixture, mirror) are not packages and are skipped.
PACKAGE_MARKER_FILE = "manifest.yaml"

# Availability marker region (namespace ORCH:, distinct from the render script's
# RENDER: namespace). Decision recorded in shape.md (p2-7 core-protocol). The
# installer replaces ONLY the content BETWEEN these markers; the markers
# themselves are preserved so re-install is idempotent.
AVAILABILITY_BEGIN = "<!-- ORCH:AVAILABILITY:BEGIN -->"
AVAILABILITY_END = "<!-- ORCH:AVAILABILITY:END -->"
_AVAILABILITY_RE = re.compile(
    re.escape(AVAILABILITY_BEGIN) + r".*?" + re.escape(AVAILABILITY_END),
    re.DOTALL,
)


def discover_model_packages(rbtv_root: Path) -> list[str]:
    """Return the sorted names of every model package present in the repo.

    A package = a directory under orchestration/models/ that carries a
    manifest.yaml. Returns [] if the models folder is absent (the orchestration
    module may be installed before any package ships).
    """
    models_dir = rbtv_root / MODELS_RELATIVE
    if not models_dir.is_dir():
        return []
    return sorted(
        d.name
        for d in models_dir.iterdir()
        if d.is_dir() and (d / PACKAGE_MARKER_FILE).is_file()
    )


def read_model_display(rbtv_root: Path, pkg: str) -> str:
    """Return a package's human-facing display label (its manifest `display:` field).

    Falls back to the package folder name when the field is absent. Single-line
    scan, no YAML parse — matches discover_model_packages' stdlib-only posture.
    """
    manifest = rbtv_root / MODELS_RELATIVE / pkg / PACKAGE_MARKER_FILE
    try:
        for line in manifest.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("display:"):
                val = stripped[len("display:"):].strip()
                if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
                    val = val[1:-1]
                return val or pkg
    except OSError:
        pass
    return pkg


def discover_model_displays(rbtv_root: Path) -> dict[str, str]:
    """Map every model package folder name → its display label (manifest `display:`)."""
    return {pkg: read_model_display(rbtv_root, pkg) for pkg in discover_model_packages(rbtv_root)}


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


def is_package_configurable(rbtv_root: Path, pkg: str) -> bool:
    """True when a package manifest declares a configurable backend set
    (``configurable_model.is_configurable: true`` on any variant).

    A configurable package's individual backends are surfaced as separately-electable
    rows in the installer; a non-configurable package is a single row. Line scan, no
    YAML parse — matches read_model_display's posture.
    """
    manifest = rbtv_root / MODELS_RELATIVE / pkg / PACKAGE_MARKER_FILE
    try:
        for line in manifest.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("is_configurable:"):
                if _scalar_value(stripped[len("is_configurable:"):]).lower() == "true":
                    return True
    except OSError:
        pass
    return False


def read_variant_displays(rbtv_root: Path, pkg: str) -> list[tuple[str, str]]:
    """Return a package's variants as ordered ``(variant_id, display_label)`` pairs.

    The label is the variant's ``display:`` field; absent, it falls back to the
    variant id. Order follows the manifest. Only the FIRST ``display:`` after each
    ``- variant:`` (and before the next) is taken. Line scan, no YAML parse.
    """
    manifest = rbtv_root / MODELS_RELATIVE / pkg / PACKAGE_MARKER_FILE
    pairs: list[tuple[str, str]] = []
    current_id: str | None = None
    current_display: str | None = None
    in_variants = False
    try:
        for line in manifest.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not in_variants:
                if stripped == "variants:":
                    in_variants = True
                continue
            if stripped.startswith("- variant:"):
                if current_id is not None:
                    pairs.append((current_id, current_display or current_id))
                current_id = _scalar_value(stripped[len("- variant:"):])
                current_display = None
            elif (
                current_id is not None
                and current_display is None
                and stripped.startswith("display:")
            ):
                current_display = _scalar_value(stripped[len("display:"):])
    except OSError:
        return []
    if current_id is not None:
        pairs.append((current_id, current_display or current_id))
    return pairs


def read_provider_label(rbtv_root: Path, pkg: str) -> str:
    """Return a configurable package's provider-path label for backend election rows.

    Reads ``configurable_model.provider_label`` when present; otherwise derives it
    from the package ``display`` by dropping the trailing parenthetical
    (e.g. ``"qwen-code (CLI)"`` → ``"qwen-code"``). Line scan, no YAML parse.
    """
    manifest = rbtv_root / MODELS_RELATIVE / pkg / PACKAGE_MARKER_FILE
    try:
        for line in manifest.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("provider_label:"):
                val = _scalar_value(stripped[len("provider_label:"):])
                if val:
                    return val
    except OSError:
        pass
    display = read_model_display(rbtv_root, pkg)
    base = display.split("(", 1)[0].strip()
    return base or display


def read_manifest_context_ceiling(rbtv_root: Path, pkg: str) -> int | None:
    """Return a package's largest manifest `context_window` (its true ceiling, in tokens).

    Scans every `context_window: <int>` line under the package manifest and returns
    the MAX (a package's variants may differ; the ceiling is the most permissive). The
    per-user plan cap (model-plans.yaml) caps AT this ceiling — a preset above it has no
    effect (route.py uses min(manifest, cap)). Returns None when no integer value is
    found. Line scan, no YAML parse — matches read_model_display's stdlib-only posture.
    """
    manifest = rbtv_root / MODELS_RELATIVE / pkg / PACKAGE_MARKER_FILE
    best: int | None = None
    try:
        for line in manifest.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("context_window:"):
                raw = _scalar_value(stripped[len("context_window:"):])
                try:
                    val = int(raw)
                except (TypeError, ValueError):
                    continue
                if best is None or val > best:
                    best = val
    except OSError:
        pass
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


def build_electable_entries(rbtv_root: Path) -> list[dict[str, str | None]]:
    """The ordered list of independently-electable worker rows the installer offers.

    A NON-configurable package contributes ONE entry (id = the package id). A
    configurable package (is_package_configurable) contributes ONE entry PER native
    backend (id = ``"{pkg}:{variant}"``) so the owner elects any subset, each row
    labeled with its provider path so a both-paths model (e.g. DeepSeek, reachable
    via qwen-code AND via a direct-API package) is unambiguous.

    Each entry: ``{id, package, variant, label, hint}`` — ``variant`` is None for a
    whole-package row; ``hint`` carries the provider-path label for backend rows.
    Shared by the interactive picker AND ``--list-model-backends`` so both render
    identically.
    """
    entries: list[dict[str, str | None]] = []
    for pkg in discover_model_packages(rbtv_root):
        if is_package_configurable(rbtv_root, pkg):
            provider = read_provider_label(rbtv_root, pkg)
            for variant_id, v_display in read_variant_displays(rbtv_root, pkg):
                entries.append(
                    {
                        "id": f"{pkg}:{variant_id}",
                        "package": pkg,
                        "variant": variant_id,
                        "label": v_display,
                        "hint": f"via {provider}",
                    }
                )
        else:
            entries.append(
                {
                    "id": pkg,
                    "package": pkg,
                    "variant": None,
                    "label": read_model_display(rbtv_root, pkg),
                    "hint": "",
                }
            )
    return entries


def resolve_selection_from_entry_ids(
    rbtv_root: Path, selected_ids: list[str]
) -> tuple[list[str], dict[str, list[str]]]:
    """Map a set of selected electable-entry ids to (packages, model_variants).

    - packages: ordered, de-duplicated package ids with >=1 selected entry.
    - model_variants: for each configurable package, the elected backend ids — but
      ONLY when a PROPER SUBSET is elected. A configurable package with ALL its
      backends elected records no entry (so a backend added later is auto-included,
      and pre-variant installs stay back-compatible: an absent entry => all backends).
    """
    selected = set(selected_ids)
    packages: list[str] = []
    chosen_by_pkg: dict[str, list[str]] = {}
    for e in build_electable_entries(rbtv_root):
        if e["id"] not in selected:
            continue
        pkg = e["package"]
        assert pkg is not None
        if pkg not in packages:
            packages.append(pkg)
        if e["variant"] is not None:
            chosen_by_pkg.setdefault(pkg, []).append(e["variant"])
    variants_map: dict[str, list[str]] = {}
    for pkg, chosen in chosen_by_pkg.items():
        all_ids = [v for v, _ in read_variant_displays(rbtv_root, pkg)]
        if set(chosen) != set(all_ids):
            variants_map[pkg] = [v for v in all_ids if v in set(chosen)]
    return packages, variants_map


def normalize_model_variants(
    rbtv_root: Path, requested: dict[str, list[str]]
) -> tuple[dict[str, list[str]], list[str]]:
    """Validate a requested ``{package: [variants]}`` restriction against the manifests.

    Returns (variants_map, warnings). Drops unknown packages / unknown variants (each
    warned), keeps manifest order, and applies omit-when-all (a package with ALL its
    backends listed records no entry). Only configurable packages are eligible; a
    non-configurable package named here is warned and ignored.
    """
    variants_map: dict[str, list[str]] = {}
    warnings: list[str] = []
    available = discover_model_packages(rbtv_root)
    for pkg, req_vars in requested.items():
        if pkg not in available:
            warnings.append(f"unknown model package '{pkg}' in --model-variants — ignored")
            continue
        if not is_package_configurable(rbtv_root, pkg):
            warnings.append(
                f"'{pkg}' has no electable backends (not configurable) — --model-variants ignored for it"
            )
            continue
        all_ids = [v for v, _ in read_variant_displays(rbtv_root, pkg)]
        chosen_set = set(req_vars)
        chosen = [v for v in all_ids if v in chosen_set]
        for u in req_vars:
            if u not in all_ids:
                warnings.append(
                    f"unknown backend '{pkg}:{u}' — ignored (available: {', '.join(all_ids)})"
                )
        if chosen and set(chosen) != set(all_ids):
            variants_map[pkg] = chosen
    return variants_map, warnings


def resolve_selected_packages(
    available: list[str], requested: tuple[str, ...] | None
) -> tuple[list[str], list[str], list[str]]:
    """Split the available packages into (installed, absent, unknown).

    - requested is None  -> elect ALL available packages (default: full install).
    - requested is a set -> elect only the named ones that actually exist;
      names that do not exist are returned as `unknown` (caller warns).

    `installed` = elected AND present; `absent` = present but NOT elected (so the
    core's availability line can name them as absent in this workspace).
    """
    if requested is None:
        return list(available), [], []
    requested_set = list(dict.fromkeys(requested))  # de-dup, preserve order
    installed = [m for m in available if m in requested_set]
    absent = [m for m in available if m not in requested_set]
    unknown = [m for m in requested_set if m not in available]
    return installed, absent, unknown


def _availability_block(
    installed: list[str], absent: list[str], displays: dict[str, str] | None = None
) -> str:
    """The two-line availability block written between the ORCH markers.

    Names render as their human-facing display labels (manifest `display:`) when a
    `displays` map is supplied, falling back to the folder name otherwise. The first line is
    the workspace's ELECTED packages (routable here); the second is packages present in the
    repo but NOT elected (rbtv.json `model_packages`) — routing (`route.py`) skips them, so
    they are not routable in this workspace (election-authoritative), even though they ship in
    the catalog folder.
    Format matches the marker region's fallback shape (two blockquote lines):
        > **Model packages installed:** a, b
        > **Not elected:** c, d
    """
    displays = displays or {}
    def _fmt(names: list[str]) -> str:
        return ", ".join(displays.get(n, n) for n in names) if names else "_(none)_"
    installed_text = _fmt(installed)
    absent_text = _fmt(absent)
    return (
        f"{AVAILABILITY_BEGIN}\n"
        f"> **Model packages installed:** {installed_text}\n"
        f"> **Not elected:** {absent_text}\n"
        f"{AVAILABILITY_END}"
    )


def bake_availability_line(
    rbtv_root: Path, installed: list[str], absent: list[str]
) -> tuple[bool, str]:
    """Replace the content between the ORCH:AVAILABILITY markers in core-protocol.md.

    Returns (changed, message). Idempotent: the markers are preserved and an
    unchanged line rewrites nothing. Fails soft (returns False + a message) when
    the core file or the markers are absent — never raises, so an install of a
    workspace without the orchestration skill core still completes.
    """
    core_path = rbtv_root / CORE_PROTOCOL_RELATIVE
    if not core_path.is_file():
        return False, f"availability bake skipped: {CORE_PROTOCOL_RELATIVE.as_posix()} not found"

    text = core_path.read_text(encoding="utf-8")
    if AVAILABILITY_BEGIN not in text or AVAILABILITY_END not in text:
        return False, (
            f"availability bake skipped: ORCH:AVAILABILITY markers not found in "
            f"{CORE_PROTOCOL_RELATIVE.as_posix()}"
        )

    new_block = _availability_block(installed, absent, discover_model_displays(rbtv_root))
    new_text, n = _AVAILABILITY_RE.subn(new_block, text)
    if n == 0:
        # Markers present individually but not as an ordered pair — leave untouched.
        return False, (
            f"availability bake skipped: ORCH:AVAILABILITY:BEGIN/END not a matched "
            f"pair in {CORE_PROTOCOL_RELATIVE.as_posix()}"
        )
    if new_text == text:
        return False, (
            f"availability line already current "
            f"(installed: {', '.join(installed) or 'none'}; absent: {', '.join(absent) or 'none'})"
        )
    core_path.write_text(new_text, encoding="utf-8")
    return True, (
        f"availability line baked into {CORE_PROTOCOL_RELATIVE.as_posix()} "
        f"(installed: {', '.join(installed) or 'none'}; absent: {', '.join(absent) or 'none'})"
    )


def read_permission_rules(rbtv_root: Path, pkg: str) -> list[str]:
    """Return a package manifest's top-level `permission_rules:` list.

    These are the literal permission-allowlist strings (e.g. "Bash(qwen:*)")
    the target workspace needs so a conductor session may spawn this CLI
    worker in-session (D17). Packages without the field (API workers, the
    native carrier) return []. Line scan, no YAML parse — matches
    read_model_display's stdlib-only posture. Only a TOP-LEVEL (column-0)
    `permission_rules:` key is honored; nested keys of the same name (e.g.
    under a variant) are ignored.
    """
    manifest = rbtv_root / MODELS_RELATIVE / pkg / PACKAGE_MARKER_FILE
    rules: list[str] = []
    try:
        in_block = False
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if not in_block:
                if line.startswith("permission_rules:"):
                    in_block = True
                continue
            stripped = line.strip()
            if stripped.startswith("- "):
                val = stripped[2:].split("#", 1)[0].strip()
                if len(val) >= 2 and val[0] in "\"'" and val[-1] == val[0]:
                    val = val[1:-1]
                if val:
                    rules.append(val)
            elif stripped == "" or stripped.startswith("#"):
                continue
            else:
                break  # next top-level key — the list is closed
    except OSError:
        pass
    return rules


def sync_permission_rules(
    target_root: Path, rbtv_root: Path, installed: list[str], absent: list[str]
) -> tuple[bool, str]:
    """Reconcile the target's `.claude/settings.local.json` permission allowlist
    with the elected model packages (D17).

    - ELECTED package  -> its manifest's `permission_rules` strings are ensured
      present in `permissions.allow`.
    - NON-ELECTED package (present in the repo but not elected) -> its declared
      strings are removed.

    Touches ONLY the exact strings the manifests declare — hand-added entries
    are never modified. Idempotent. Fails soft (returns False + message) on a
    malformed settings file rather than clobbering it.
    """
    settings_path = target_root / ".claude" / "settings.local.json"

    wanted: list[str] = []
    for pkg in installed:
        for rule in read_permission_rules(rbtv_root, pkg):
            if rule not in wanted:
                wanted.append(rule)
    unwanted: set[str] = set()
    for pkg in absent:
        unwanted.update(read_permission_rules(rbtv_root, pkg))
    unwanted -= set(wanted)  # a rule shared with an elected package stays

    if not wanted and not unwanted:
        return False, "permission sync: no model package declares permission rules"

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
    """
    if not isinstance(entry, dict):
        return False
    if entry.get("__rbtv__") == _HOOK_SENTINEL:
        return True
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

    The hook ``command`` is built from Claude Code's ``$CLAUDE_PROJECT_DIR`` hook
    variable (the project root, resolved per-machine when the hook runs) joined with
    ``rbtv_relative`` (the per-user relative path to the RBTV install, baked at install
    time) — so it resolves from ANY working directory and on ANY machine, never a
    hardcoded absolute path. (A bare relative command broke when Claude Code ran the
    hook from a non-project-root CWD.)

    Idempotent: re-running replaces any stale entry with the current resolved path.
    Fails soft (returns False + message) on a malformed settings file.

    Scope: WIRE only. The unwire/removal path is p2-2's job.
    """
    settings_path = target_root / ".claude" / "settings.local.json"

    # Resolve the script path relative to target_root using rbtv_relative.
    # The command string uses forward slashes and quotes the path to handle spaces.
    script_posix = (rbtv_relative / _CONTEXT_MONITOR_RELATIVE).as_posix()
    command_str = f'python "$CLAUDE_PROJECT_DIR/{script_posix}"'

    # The entry the installer owns, identifiable by _HOOK_SENTINEL.
    rbtv_entry: dict = {
        "__rbtv__": _HOOK_SENTINEL,
        "matcher": "",
        "hooks": [{"type": "command", "command": command_str}],
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


def check_manual_render(rbtv_root: Path) -> tuple[str, str]:
    """Run the render-freshness check (render-manuals.py --check).

    Returns (status, message) where status is one of:
      - 'fresh'   : all manuals consistent with template + deltas (render exit 0)
      - 'stale'   : at least one manual is stale relative to its sources (exit 1)
      - 'error'   : the render check could not run / malformed markers (exit 2+)
      - 'skipped' : the render script is not present

    NON-FATAL by design (matches the installer's _check_plugin_prereqs warn-not-
    abort convention): the caller WARNS on 'stale'/'error' and proceeds. Manuals
    are read JIT from {rbtv_path}, so a stale manual is corrected on the next render
    rather than blocking the install.
    """
    script = rbtv_root / RENDER_SCRIPT_RELATIVE
    if not script.is_file():
        return "skipped", f"render check skipped: {RENDER_SCRIPT_RELATIVE.as_posix()} not found"
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "--check"],
            cwd=str(rbtv_root),
            capture_output=True,
            text=True,
        )
    except OSError as exc:  # pragma: no cover - environment failure
        return "error", f"render check could not run: {exc}"

    detail = (proc.stdout + proc.stderr).strip()
    if proc.returncode == 0:
        return "fresh", "render check: all manuals fresh"
    if proc.returncode == 1:
        return "stale", "render check: STALE manual(s) — manuals are out of date with their sources:\n" + detail
    return "error", f"render check: ERROR (exit {proc.returncode}) — manuals could not be verified:\n" + detail
