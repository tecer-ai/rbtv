"""CLI entry point for the RBTV installer.

Orchestrates the full install flow:

  1. Resolve target workspace path (--target flag or interactive prompt)
  2. Load module manifest from admin/install/module-manifest.json
  3. Select modules (--modules flag, --non-interactive, or interactive checkbox)
  4. Optionally customize individual components within selected modules
  5. Clear previous rbtv-* files from .claude/ in the target
  6. Install selected components (baked skills/commands, copied rules/subagents)
  7. Write rbtv.json state file (persists choices for future re-installs)
  8. Check for required Claude Code plugins and warn if missing

No external dependencies — the TUI is pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from .context import resolve_from_cli
from .generator import (
    clear_previous_install,
    install_command,
    install_rule,
    install_skill,
    install_subagent,
)
from .manifest import Module, load_manifest
from .orchestration import (
    build_electable_entries,
    build_plan_size_presets,
    check_manual_render,
    clobbered_variants,
    discover_model_displays,
    discover_model_packages,
    normalize_model_variants,
    read_manifest_context_ceiling,
    read_model_plan_caps,
    read_model_plan_models,
    remove_hook_entry,
    resolve_selected_packages,
    resolve_selection_from_entry_ids,
    sync_hook_entry,
    sync_permission_rules,
    write_model_plan_caps,
)
from .state import find_state_upward, read_state, update_mirror_state, write_state

# The module that owns the model packages — package selection is offered only
# when this module is installed.
ORCHESTRATION_MODULE = "orchestration"


def _find_rbtv_root() -> Path:
    """Walk up from this file until a parent contains install.py AND admin/install/defaults.json."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "install.py").is_file() and (
            parent / "admin" / "install" / "defaults.json"
        ).is_file():
            return parent
    raise SystemExit(
        f"Cannot locate RBTV root — no ancestor of {current} contains "
        f"install.py AND admin/install/defaults.json."
    )


def _load_defaults(rbtv_root: Path) -> dict[str, Any]:
    defaults_path = rbtv_root / "admin" / "install" / "defaults.json"
    return json.loads(defaults_path.read_text(encoding="utf-8"))


def _component_name(target_relative: Path) -> str:
    """Extract a human-readable name from a target path."""
    p = PurePosixPath(str(target_relative).replace("\\", "/"))
    if p.name == "SKILL.md":
        return p.parent.name
    return p.stem


def _module_detail_text(module: Module) -> str:
    """Format a module's components for the interactive detail view (press 'i')."""
    lines = [f"  {module.name} — {module.description}", ""]

    groups: list[tuple[str, list[tuple[str, str]]]] = [
        ("Skills", [(_component_name(s.target_relative), s.description) for s in module.skills if not s.stale]),
        ("Commands", [(_component_name(c.target_relative), c.description) for c in module.commands if not c.stale]),
        ("Rules", [(_component_name(r.target_relative), r.description) for r in module.rules if not r.stale]),
        ("Subagents", [(_component_name(a.target_relative), a.description) for a in module.subagents if not a.stale]),
    ]
    for group_name, entries in groups:
        if entries:
            lines.append(f"  {group_name} ({len(entries)}):")
            for name, desc in entries:
                if desc:
                    lines.append(f"    • {name} — {desc}")
                else:
                    lines.append(f"    • {name}")
        else:
            lines.append(f"  {group_name}: (none)")
        lines.append("")

    stale_names = [
        _component_name(e.target_relative)
        for group in (module.skills, module.commands, module.rules, module.subagents)
        for e in group
        if e.stale
    ]
    if stale_names:
        lines.append(f"  Stale (retired — not installed): {', '.join(stale_names)}")
        lines.append("")

    return "\n".join(lines)


def _validate_target(value: str) -> str | None:
    p = Path(value).resolve()
    if p.is_file():
        return f"'{value}' is a file, not a directory."
    return None


def _prompt_target(existing_state: dict[str, Any] | None) -> Path:
    """Prompt for the target workspace path. Uses previous target as default if available."""
    from .tui import text_input

    default = ""
    if existing_state:
        default = str(existing_state.get("_target_hint", ""))
    return Path(
        text_input(
            "Installation path (target workspace)",
            default=default,
            validator=_validate_target,
        )
    ).resolve()


def _prompt_modules_interactive(
    manifest: dict[str, Module],
    always: list[str],
    existing_modules: tuple[str, ...] | None,
) -> tuple[str, ...]:
    """Show an interactive checkbox for module selection.

    Always-installed modules are shown as disabled (checked, not toggleable).
    Previously installed modules are pre-selected on re-installs.
    Press 'i' on any module to view its skills, commands, rules, and subagents.
    """
    from .tui import checkbox

    available = list(manifest.keys())

    items = []
    for name in available:
        mod = manifest[name]
        is_always = name in always
        pre_selected = is_always or (
            existing_modules is not None and name in existing_modules
        )
        items.append(
            {
                "label": name,
                "hint": mod.description,
                "selected": pre_selected,
                "disabled": is_always,
            }
        )

    def detail_cb(index: int) -> str:
        mod_name = available[index]
        return _module_detail_text(manifest[mod_name])

    selected_indices = checkbox(
        "\nSelect modules to install:",
        items,
        min_selected=1,
        detail_callback=detail_cb,
    )

    chosen = [available[i] for i in selected_indices]
    for m in always:
        if m not in chosen:
            chosen.insert(0, m)
    return tuple(chosen)


def _prompt_custom_components(
    manifest: dict[str, Module],
    chosen_modules: tuple[str, ...],
    previous_excluded: set[str],
) -> set[str]:
    """Let the user deselect individual components. Returns excluded target paths."""
    from .tui import checkbox, confirm

    if not confirm(
        "\nCustomize individual components?",
        default=False,
    ):
        # Declining customization means "keep my prior choices", not "reset to
        # all components" — preserve the exclusions we were handed.
        return set(previous_excluded)

    excluded: set[str] = set()

    for mod_name in chosen_modules:
        mod = manifest[mod_name]
        items: list[dict[str, Any]] = []
        keys: list[str] = []

        for s in mod.skills:
            if s.stale:
                continue
            key = str(s.target_relative).replace("\\", "/")
            items.append(
                {
                    "label": f"skill    {_component_name(s.target_relative)}",
                    "hint": s.description,
                    "selected": key not in previous_excluded,
                }
            )
            keys.append(key)
        for c in mod.commands:
            if c.stale:
                continue
            key = str(c.target_relative).replace("\\", "/")
            items.append(
                {
                    "label": f"cmd      {_component_name(c.target_relative)}",
                    "hint": c.description,
                    "selected": key not in previous_excluded,
                }
            )
            keys.append(key)
        for r in mod.rules:
            if r.stale:
                continue
            key = str(r.target_relative).replace("\\", "/")
            items.append(
                {
                    "label": f"rule     {_component_name(r.target_relative)}",
                    "hint": r.description,
                    "selected": key not in previous_excluded,
                }
            )
            keys.append(key)
        for a in mod.subagents:
            if a.stale:
                continue
            key = str(a.target_relative).replace("\\", "/")
            items.append(
                {
                    "label": f"agent    {_component_name(a.target_relative)}",
                    "hint": a.description,
                    "selected": key not in previous_excluded,
                }
            )
            keys.append(key)

        if not items:
            continue

        selected_indices = checkbox(
            f"\nComponents for '{mod_name}' ({mod.description}):",
            items,
        )
        selected_set = set(selected_indices)
        for i, key in enumerate(keys):
            if i not in selected_set:
                excluded.add(key)

    return excluded


def _prompt_model_selection(
    rbtv_root: Path,
    previous_packages: list[str] | None,
    previous_variants: dict[str, list[str]] | None,
) -> tuple[list[str], dict[str, list[str]]]:
    """Interactive checkbox over the electable worker entries (build_electable_entries).

    A configurable package (e.g. qwen-code-cli) contributes one row PER native backend,
    each provider-path labeled so a both-paths model (DeepSeek via qwen-code vs via a
    direct-API package) is unambiguous; every other package is a single row. On a
    re-install the previous election is pre-checked; on a first install everything is
    pre-checked (full install is the default). Returns (packages, model_variants) via
    resolve_selection_from_entry_ids (model_variants carries only proper-subset
    configurable packages).
    """
    from .tui import checkbox

    entries = build_electable_entries(rbtv_root)
    previous_variants = previous_variants or {}
    items: list[dict[str, Any]] = []
    for e in entries:
        pkg = e["package"]
        if previous_packages is None:
            pre = True
        elif pkg not in previous_packages:
            pre = False
        elif e["variant"] is None:
            pre = True
        else:
            restricted = previous_variants.get(pkg)
            pre = restricted is None or e["variant"] in restricted
        item: dict[str, Any] = {"label": e["label"], "selected": pre}
        if e["hint"]:
            item["hint"] = e["hint"]
        items.append(item)

    selected_indices = checkbox(
        "\nSelect orchestration model workers / backends to make available in this "
        "workspace\n  (a configurable CLI lists each native backend separately, "
        "provider-path labeled):",
        items,
    )
    selected_ids = [str(entries[i]["id"]) for i in selected_indices]
    return resolve_selection_from_entry_ids(rbtv_root, selected_ids)


def _carry_variants(
    previous_variants: dict[str, list[str]] | None, elected_packages: list[str] | None
) -> dict[str, list[str]]:
    """Carry forward a previous model_variants map, dropping entries for packages no
    longer elected. Used on the scripted (non-interactive / --modules) path and when
    --model-packages is given without --model-variants — a re-install preserves the
    recorded backend subset for still-elected configurable packages."""
    if not previous_variants:
        return {}
    elected = set(elected_packages or [])
    return {p: list(vs) for p, vs in previous_variants.items() if p in elected}


def _resolve_model_packages(
    rbtv_root: Path,
    chosen_modules: tuple[str, ...],
    requested_packages: tuple[str, ...] | None,
    requested_variants: dict[str, list[str]] | None,
    non_interactive: bool,
    used_modules_flag: bool,
    existing_state: dict[str, Any] | None,
) -> tuple[list[str], list[str], list[str] | None, dict[str, list[str]] | None]:
    """Resolve which model packages — and, for configurable packages, which native
    backends — this workspace elects.

    Returns (installed, absent, persisted_packages, persisted_variants):
      - installed / absent feed the permission-allowlist reconcile (package granularity),
      - persisted_packages is written to rbtv.json `model_packages` (None => key omitted:
        the orchestration module is not installed so packages do not apply),
      - persisted_variants is written to rbtv.json `model_variants` (None => key omitted:
        no proper-subset restriction on any configurable package).

    Selection precedence mirrors module resolution:
      --model-packages / --model-variants flags > non-interactive(prev state or all)
      > interactive picker.
    """
    if ORCHESTRATION_MODULE not in chosen_modules:
        return [], [], None, None

    available = discover_model_packages(rbtv_root)
    if not available:
        # Orchestration installed but no packages shipped yet — nothing to elect.
        return [], [], [], None

    prev_packages: list[str] | None = None
    prev_variants: dict[str, list[str]] | None = None
    if existing_state is not None:
        if "model_packages" in existing_state:
            prev_packages = list(existing_state["model_packages"])
        if isinstance(existing_state.get("model_variants"), dict):
            prev_variants = {
                k: list(v) for k, v in existing_state["model_variants"].items()
            }

    variants_map: dict[str, list[str]]
    if requested_packages is not None or requested_variants is not None:
        # Flag path.
        if requested_packages is not None:
            req_pkgs = list(dict.fromkeys(requested_packages))
        else:
            req_pkgs = list(prev_packages) if prev_packages is not None else list(available)
        # A package named only in --model-variants is implicitly elected.
        if requested_variants:
            for p in requested_variants:
                if p in available and p not in req_pkgs:
                    req_pkgs.append(p)
        if requested_variants is not None:
            variants_map, warns = normalize_model_variants(rbtv_root, requested_variants)
            for w in warns:
                print(f"\n  WARNING — {w}", file=sys.stderr)
        else:
            variants_map = _carry_variants(prev_variants, req_pkgs)
        requested: tuple[str, ...] | None = tuple(req_pkgs)
    elif non_interactive or used_modules_flag:
        # Scripted path: reuse prior selection if any, else elect all available.
        requested = tuple(prev_packages) if prev_packages is not None else None
        variants_map = _carry_variants(
            prev_variants, prev_packages if prev_packages is not None else available
        )
    else:
        packages, variants_map = _prompt_model_selection(
            rbtv_root, prev_packages, prev_variants
        )
        requested = tuple(packages)

    installed, absent, unknown = resolve_selected_packages(available, requested)
    if unknown:
        print(
            f"\n  WARNING — unknown model package(s) ignored: {', '.join(unknown)} "
            f"(available: {', '.join(available)})",
            file=sys.stderr,
        )
    # Confine model_variants to actually-installed packages; empty => None (omit the key).
    variants_map = {p: vs for p, vs in variants_map.items() if p in installed}
    return installed, absent, installed, (variants_map or None)


def _resolve_env_file(
    requested_flag: str | None,
    existing_state: dict[str, Any] | None,
    chosen_modules: tuple[str, ...],
    non_interactive: bool,
    used_modules_flag: bool,
) -> str | None:
    """Resolve the env_file PATH to record in rbtv.json (path only — never keys).

    Precedence: --env-file flag > interactive prompt (orchestration + interactive
    only) > None. Returning None lets write_state carry forward any previously
    recorded value, so re-installs preserve env_file (D-exec-1 / D-exec-7).
    """
    if requested_flag is not None:
        return requested_flag.strip() or None

    existing_value = None
    if existing_state is not None and isinstance(existing_state.get("env_file"), str):
        existing_value = existing_state["env_file"]

    # Scripted path, no flag: keep whatever exists (write_state carries it forward).
    if non_interactive or used_modules_flag:
        return None

    # Interactive prompt only when the orchestration module is being installed.
    if ORCHESTRATION_MODULE not in chosen_modules:
        return None

    from .tui import text_input
    entered = text_input(
        "Path to your env file with API keys for model workers "
        "(optional — blank to skip / keep current)",
        default=existing_value or "",
        allow_empty=True,
    ).strip()
    return entered or None


def _resolve_model_plans_file(
    requested_flag: str | None,
    existing_state: dict[str, Any] | None,
    chosen_modules: tuple[str, ...],
    non_interactive: bool,
    used_modules_flag: bool,
) -> str | None:
    """Resolve the model_plans_file PATH to record in rbtv.json (path only).

    Precedence: --model-plans-file flag > interactive prompt (orchestration +
    interactive only) > None. Returning None lets write_state carry forward any
    previously recorded value, so re-installs preserve model_plans_file.
    """
    if requested_flag is not None:
        return requested_flag.strip() or None

    existing_value = None
    if existing_state is not None and isinstance(
        existing_state.get("model_plans_file"), str
    ):
        existing_value = existing_state["model_plans_file"]

    # Scripted path, no flag: keep whatever exists (write_state carries it forward).
    if non_interactive or used_modules_flag:
        return None

    # Interactive prompt only when the orchestration module is being installed.
    if ORCHESTRATION_MODULE not in chosen_modules:
        return None

    from .tui import text_input
    entered = text_input(
        "Path to your model plans YAML with per-model context caps and $/M-token "
        "reference data (optional — blank to skip / keep current)",
        default=existing_value or "",
        allow_empty=True,
    ).strip()
    return entered or None


def _prompt_plan_size(
    label: str, presets: list[tuple[str, int | None]], prior: int | None
) -> int | None:
    """Pick-list (numbered menu) for ONE model's plan size (D14 — never a raw token entry).

    Prints each preset as a numbered choice; the option matching `prior` (a re-installed
    workspace's previously-chosen cap, or None for first install) is marked the default and
    is chosen on a bare Enter — re-confirming the prior value, never wiping it. Returns the
    chosen context_window (int) or None ("no cap"). Out-of-range / non-numeric input
    re-prompts.
    """
    from .tui import text_input

    # The default index: the preset whose value equals `prior`; else the "No cap" row.
    default_index = 0
    for i, (_, val) in enumerate(presets):
        if val == prior:
            default_index = i
            break

    print(f"\n  Plan size for {label}:")
    for i, (preset_label, _) in enumerate(presets):
        marker = "  (current)" if i == default_index else ""
        print(f"    {i + 1}) {preset_label}{marker}")

    def _validate(value: str) -> str | None:
        if not value.isdigit():
            return "Enter the NUMBER of a choice above."
        n = int(value)
        if not (1 <= n <= len(presets)):
            return f"Choose 1–{len(presets)}."
        return None

    chosen = text_input(
        "  Choose a plan size by number",
        default=str(default_index + 1),
        validator=_validate,
    )
    return presets[int(chosen) - 1][1]


def _format_tokens(n: int) -> str:
    """Render a token count compactly: 1000000 -> '1M', 200000 -> '200K', else the int."""
    if n % 1_000_000 == 0:
        return f"{n // 1_000_000}M"
    if n % 1_000 == 0:
        return f"{n // 1_000}K"
    return str(n)


def _warn_if_cap_clobbers(
    rbtv_root: Path, pkg: str, cap: int | None, label: str
) -> None:
    """WARN when a chosen plan-size ``cap`` shrinks a higher-window variant of ``pkg`` below its
    native context window — the multi-model clobber (D14).

    A single per-package cap applies to EVERY variant (route.py ``min(window, cap)``); when a
    package's variants have different native windows (e.g. claude-code-native: opus 1M,
    sonnet/haiku 200K), a sub-largest cap silently shrinks the bigger variant. This names the
    clobbered variant(s) so the owner can tell a deliberate uniform-subscription ceiling from an
    accidental foot-gun. ADVISORY only — the cap is still applied (the subscription may genuinely
    enforce it); it never blocks. No-op when nothing is clobbered (cap None, or at/above every
    native window). Printed to stderr, matching the installer's WARNING convention.
    """
    clobbered = clobbered_variants(rbtv_root, pkg, cap)
    if not clobbered:
        return
    cap_label = _format_tokens(cap)  # type: ignore[arg-type]  # cap is int here (clobbered non-empty)
    print(
        f"\n  WARNING — {cap_label} is below {label}'s largest native context window. A single "
        "plan-size cap applies to EVERY model in this package, so it shrinks these below their "
        "native size:",
        file=sys.stderr,
    )
    for v_label, win in clobbered:
        print(f"    - {v_label}: {_format_tokens(win)} -> {cap_label}", file=sys.stderr)
    print(
        "  The other models keep their native window. If your subscription genuinely caps every "
        f"model at {cap_label}, keep this; otherwise choose \"No cap\" (or a size at or above the "
        "largest window) to preserve the bigger model's full context.",
        file=sys.stderr,
    )


def _resolve_model_plan_caps(
    rbtv_root: Path,
    target_root: Path,
    model_plans_file: str | None,
    installed_packages: list[str],
    non_interactive: bool,
    used_modules_flag: bool,
) -> tuple[bool, str] | None:
    """Offer per-model plan-size PRESETS and write the chosen caps to model-plans.yaml (D14).

    For each elected package, the owner picks a plan size from a numbered menu (never a raw
    token number); the chosen `context_window` is written cap-only to the file pointed at by
    `model_plans_file`. A previously-chosen cap is read back from that file and offered as the
    pre-selected default — re-confirmed on reinstall, never silently wiped.

    Returns the write (changed, message), or None when the step does not apply:
      - no model_plans_file pointer (nothing to write into),
      - no elected packages,
      - the scripted path (non-interactive / --modules): the existing caps are PRESERVED
        verbatim (no prompts), so a CI re-install never wipes a hand-/installer-set cap.
    """
    if not model_plans_file or not installed_packages:
        return None

    plans_path = (target_root / model_plans_file).resolve()
    prior_caps = read_model_plan_caps(plans_path)
    displays = discover_model_displays(rbtv_root)

    # Scripted path: preserve every prior cap verbatim, prompt for nothing. A package
    # with no prior cap stays uncapped. Re-confirms by re-writing the same values, so a
    # stale cost row in an old file is dropped (the file is rebuilt cap-only).
    if non_interactive or used_modules_flag:
        caps: dict[str, int | None] = {
            pkg: prior_caps.get(pkg) for pkg in installed_packages
        }
        return write_model_plan_caps(plans_path, caps, displays)

    # Skip per-model re-prompting when nothing about the size choice has changed.
    # A package PRESENT in the plans file was already sized by the owner (including
    # those set to "no cap", which prior_caps omits) — read_model_plan_models reports
    # presence. A package ABSENT from the file is genuinely new and still needs one menu.
    prior_models = set(read_model_plan_models(plans_path))
    new_packages = [pkg for pkg in installed_packages if pkg not in prior_models]

    from .tui import confirm

    if not prior_models:
        # First-ever sizing (no saved file): prompt every model, no "new model" note.
        prompt_set = set(installed_packages)
    elif not new_packages:
        # Every elected model was sized before — one yes/no instead of a menu per model.
        if confirm(
            "\n  Keep your saved context-window sizes for all models "
            "(answer No to change them)?",
            default=True,
        ):
            caps = {pkg: prior_caps.get(pkg) for pkg in installed_packages}
            return write_model_plan_caps(plans_path, caps, displays)
        prompt_set = set(installed_packages)
    else:
        # New model(s) elected — ask only for those; keep the rest's saved sizes.
        new_labels = ", ".join(displays.get(p, p) for p in new_packages)
        print(
            f"\n  New model(s) added: {new_labels}. Setting the context-window size "
            "only for those — your other models keep their saved sizes."
        )
        prompt_set = set(new_packages)

    print(
        "\n  Set each model's plan size (the context-window cap your subscription "
        "enforces).\n  Pick a size from the menu — a current value is re-confirmed on Enter."
    )
    caps = {}
    for pkg in installed_packages:
        if pkg in prompt_set:
            ceiling = read_manifest_context_ceiling(rbtv_root, pkg)
            presets = build_plan_size_presets(ceiling)
            label = displays.get(pkg, pkg)
            caps[pkg] = _prompt_plan_size(label, presets, prior_caps.get(pkg))
            _warn_if_cap_clobbers(rbtv_root, pkg, caps[pkg], label)
        else:
            caps[pkg] = prior_caps.get(pkg)
    return write_model_plan_caps(plans_path, caps, displays)


def _import_mirror_driver(rbtv_root: Path):
    """Import the mirror driver's ``render`` / ``uninstall`` entry points.

    The driver package lives at ``orchestration/models/mirror/driver/`` and is
    imported as a top-level ``driver`` package — the same reachability shim the
    driver's own ``cli.py`` uses for loose-script invocation: insert the PARENT
    of ``driver/`` onto ``sys.path`` (it has no ancestor ``__init__.py`` chain to
    the installer package) and import by name. The import is lazy (called only
    when the orchestration module is installed) so a non-orchestration install
    never pays the cost and a driver-import failure surfaces only when a mirror is
    actually requested.

    Returns ``(render, uninstall)`` callables.
    """
    driver_parent = rbtv_root / "orchestration" / "models" / "mirror"
    if str(driver_parent) not in sys.path:
        sys.path.insert(0, str(driver_parent))
    from driver import (  # type: ignore[import-not-found]
        render as mirror_render,
        uninstall as mirror_uninstall,
    )

    return mirror_render, mirror_uninstall


def _split_mirrorable(rbtv_root: Path, elected: list[str]) -> list[str]:
    """Return the elected packages the driver can mirror, warning on skips.

    ``claude-code-cli`` loads its guidance natively and is mirror-less — it is dropped
    silently (never a missing-assets warning). Any OTHER elected package whose
    ``orchestration/models/<pkg>/mirror-assets/`` tree is absent is skipped with a
    NAMED warning (matches the spec's "ships no mirror-assets" edge case — a skip,
    never a crash), because the driver's config renderer raises on a missing
    assets tree. The driver itself further drops ids it does not know.
    """
    models_dir = rbtv_root / "orchestration" / "models"
    mirrorable: list[str] = []
    for pkg in elected:
        if pkg == "claude-code-cli":
            continue  # native, mirror-less — silently skipped
        if (models_dir / pkg / "mirror-assets").is_dir():
            mirrorable.append(pkg)
        else:
            print(
                f"\n  WARNING — mirror skipped for '{pkg}': no mirror-assets "
                f"shipped at orchestration/models/{pkg}/mirror-assets/ "
                f"(its artifacts will not be rendered).",
                file=sys.stderr,
            )
    return mirrorable


def _print_leftover_worker_dirs(uninstall_result: Any) -> None:
    """Surface worker dirs an uninstall left in place because they still hold files
    rbtv did not create (tool-written leftovers / prior-install orphans).

    The mirror only deletes files it created and prunes a dir that empties; a dir
    kept alive by a foreign file is reported here so the owner can remove it by
    hand. No-op when there are none.
    """
    leftovers = getattr(uninstall_result, "leftover_dirs", None)
    if not leftovers:
        return
    print(
        f"  Note — {len(leftovers)} worker dir(s) left in place because they still "
        "hold file(s) rbtv did not create:"
    )
    for entry in leftovers:
        print(f"    ~ {entry['dir']}/ ({len(entry['files'])} non-rbtv file(s))")
    print("    Delete them by hand if you no longer need them.")


def _check_plugin_prereqs() -> None:
    """Warn if Claude Code plugins required by certain RBTV menu items are missing."""
    home = Path.home()
    candidates = [
        home / ".claude" / "plugins",
        home / ".claude" / "plugins" / "cache",
    ]
    required = {
        "bmad-method-lifecycle": "Ana's [B] Brief, [PRD], and [UX] menu items",
        "bmad-pro-skills": "DomCobb's [PV] Problem Solving menu item",
    }
    missing: dict[str, str] = {}
    for plugin_name, used_by in required.items():
        found = False
        for candidate in candidates:
            if not candidate.is_dir():
                continue
            for child in candidate.rglob(plugin_name):
                if child.is_dir():
                    found = True
                    break
            if found:
                break
        if not found:
            missing[plugin_name] = used_by

    if missing:
        print("\nWARNING — missing Claude Code plugins:", file=sys.stderr)
        for plugin_name, used_by in missing.items():
            print(
                f"  - {plugin_name} (required for: {used_by})",
                file=sys.stderr,
            )
        print(
            "  These RBTV menu items will silently fail until the plugins are installed.\n",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install RBTV into a target workspace.")
    parser.add_argument(
        "--target",
        type=Path,
        default=None,
        help="Absolute path to the workspace where loaders will be installed.",
    )
    parser.add_argument(
        "--modules",
        type=str,
        default="",
        help="Comma-separated module names (skips interactive prompt if provided).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip all prompts; use existing rbtv.json + --modules only.",
    )
    parser.add_argument(
        "--model-packages",
        type=str,
        default=None,
        help=(
            "Comma-separated orchestration model packages to make available "
            "(folder-safe ids, e.g. kimi-code-cli, codex-cli, claude-code-cli, "
            "qwen-code-cli). Omit to keep the previous selection "
            "or elect all available packages. Empty string elects none. Only "
            "applies when the orchestration module is installed."
        ),
    )
    parser.add_argument(
        "--model-variants",
        type=str,
        default=None,
        help=(
            "Restrict CONFIGURABLE packages to a backend subset, as "
            "'package=variant,variant' groups separated by ';' "
            "(e.g. 'qwen-code-cli=deepseek-flash,deepseek-pro'). A package named here is "
            "implicitly elected. Recorded in rbtv.json 'model_variants'; the router then "
            "routes only the listed backends of that package. Omit to keep the previous "
            "subset (re-installs preserve it); a package not listed keeps ALL its backends. "
            "Only applies when the orchestration module is installed."
        ),
    )
    parser.add_argument(
        "--list-model-packages",
        action="store_true",
        help=(
            "Print every available orchestration model package as "
            "'<id>\\t<display label>' (one per line) and exit. Non-interactive view "
            "of the same id→label rendering the worker pick-menu shows."
        ),
    )
    parser.add_argument(
        "--list-model-backends",
        action="store_true",
        help=(
            "Print every independently-electable worker ROW as "
            "'<id>\\t<label>\\t<provider-path>' (one per line) and exit — the exact "
            "rows the interactive picker shows, with each configurable CLI expanded into "
            "its native backends (id '<pkg>:<variant>'). Non-interactive view of the "
            "backend-election menu."
        ),
    )
    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help=(
            "Path (workspace-relative or absolute) to the env file holding API keys "
            "for orchestration model workers. Recorded in rbtv.json as 'env_file' so "
            "the API-worker runner resolves keys via file-fallback. Omit to keep any "
            "previously-recorded value (re-installs preserve it). Only the PATH is "
            "recorded — keys are never read or stored."
        ),
    )
    parser.add_argument(
        "--model-plans-file",
        type=str,
        default=None,
        help=(
            "Path (workspace-relative or absolute) to the YAML file with per-model "
            "subscription-plan caps and reference $/M-token data. Recorded in rbtv.json "
            "as 'model_plans_file' so the router script reads plan-overlay caps. "
            "Omit to keep any previously-recorded value (re-installs preserve it)."
        ),
    )
    parser.add_argument(
        "--mirror",
        action="store_true",
        help=(
            "Mirror-only mode: refresh the mirror artifacts for the packages "
            "already recorded in rbtv.json without running target/module/component "
            "prompts or reinstalling components. Resolves the target via --target "
            "or the nearest rbtv.json."
        ),
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="PATH",
        default=None,
        help=(
            "Workspace-root-relative posix path(s) the mirror skips — no guidance "
            "file is rendered beside any CLAUDE.md inside an excluded path. The list "
            "is recorded in rbtv.json (model_mirror.excluded_paths) as the per-user "
            "default. Passing --exclude REPLACES the recorded list; omitting it "
            "PRESERVES the recorded list. Applies on both a full install and "
            "--mirror."
        ),
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help=(
            "With --mirror: remove ALL generated mirror artifacts for the target "
            "(guidance files, the shared .agents/ library, and per-model config "
            "dirs) and clear the model_mirror block from rbtv.json. A full mirror "
            "teardown for every currently-elected package. A worker dir emptied of "
            "rbtv's files is removed; one still holding files rbtv did not create "
            "is named (not deleted) so you can remove it by hand."
        ),
    )
    args = parser.parse_args(argv)

    # --exclude: None (omitted → preserve recorded list) vs an explicit list
    # (replace the recorded list). The driver defaults excluded_paths from prior
    # state when None, so omitting the flag preserves the recorded exclusions.
    requested_excluded_paths: list[str] | None = None
    if args.exclude is not None:
        requested_excluded_paths = [
            p.strip().replace("\\", "/") for p in args.exclude if p.strip()
        ]

    # --uninstall is a mirror-teardown flag — it only acts in --mirror mode.
    if args.uninstall and not args.mirror:
        raise SystemExit(
            "--uninstall applies only with --mirror (full mirror teardown). "
            "Run: install.py --mirror --uninstall [--target <workspace>]."
        )

    # Parse the model-packages flag: None (omitted) vs an explicit (possibly empty) set.
    requested_model_packages: tuple[str, ...] | None = None
    if args.model_packages is not None:
        requested_model_packages = tuple(
            m.strip() for m in args.model_packages.split(",") if m.strip()
        )

    # Parse the model-variants flag: None (omitted) vs an explicit map. Format:
    # 'pkg=v1,v2;pkg2=v3'. An empty string parses to {} (clears any recorded subset).
    requested_model_variants: dict[str, list[str]] | None = None
    if args.model_variants is not None:
        requested_model_variants = {}
        for chunk in args.model_variants.split(";"):
            chunk = chunk.strip()
            if not chunk:
                continue
            if "=" not in chunk:
                raise SystemExit(
                    "--model-variants: expected 'package=variant,variant' groups "
                    f"separated by ';', got '{chunk}'"
                )
            pkg, _, vars_str = chunk.partition("=")
            pkg = pkg.strip()
            if pkg:
                requested_model_variants[pkg] = [
                    v.strip() for v in vars_str.split(",") if v.strip()
                ]

    rbtv_root = _find_rbtv_root()

    # --list-model-packages: non-interactive view of the worker pick-menu's id→label
    # rendering (the same display read the interactive picker uses). Print and exit.
    if args.list_model_packages:
        displays = discover_model_displays(rbtv_root)
        for pkg in discover_model_packages(rbtv_root):
            print(f"{pkg}\t{displays.get(pkg, pkg)}")
        return 0

    # --list-model-backends: non-interactive view of the backend-election menu (each
    # configurable package expanded into its native backends with provider-path labels).
    if args.list_model_backends:
        for e in build_electable_entries(rbtv_root):
            print(f"{e['id']}\t{e['label']}\t{e['hint'] or ''}")
        return 0

    defaults = _load_defaults(rbtv_root)

    print(f"\n  RBTV Installer v{defaults['rbtv']['version']}\n")

    # --- --mirror short-circuit: refresh only mirror artifacts, no component install ---

    if args.mirror:
        # Resolve target: --target flag wins; else walk upward for rbtv.json.
        if args.target:
            mirror_target = args.target.resolve()
            mirror_state = read_state(mirror_target)
            if mirror_state is None:
                raise SystemExit(
                    "ERROR — nothing to mirror from: no rbtv.json found at "
                    f"'{mirror_target}'. Run a full install first."
                )
        else:
            found = find_state_upward(Path.cwd())
            if found is None:
                raise SystemExit(
                    "ERROR — nothing to mirror from: no rbtv.json found in this "
                    "directory or any ancestor. Run a full install first, or pass "
                    "--target <workspace> to specify the installed workspace."
                )
            mirror_target, mirror_state = found

        # Read model_packages BEFORE any write so deselect computation is correct.
        elected_workers: list[str] = list(mirror_state.get("model_packages") or [])
        mirrorable = _split_mirrorable(rbtv_root, elected_workers)

        # --- --mirror --uninstall: full mirror teardown for the target ---------
        if args.uninstall:
            try:
                _mirror_render, mirror_uninstall = _import_mirror_driver(rbtv_root)
                # Tear down EVERY currently-elected package (remaining_elected
                # empty) so the driver deletes all generated artifacts and drops
                # the model_mirror block from rbtv.json.
                un = mirror_uninstall(
                    mirror_target, mirrorable, remaining_elected=[]
                )
            except Exception as exc:
                raise SystemExit(
                    f"\nERROR — mirror uninstall failed: {exc}\n"
                    "  The workspace's mirror artifacts may be partially removed. "
                    "Re-run once the cause is resolved."
                ) from exc
            print(
                f"  Mirror uninstall: deleted {len(un.deleted)} file(s), "
                f"spared {len(un.spared)} hand-authored guidance file(s); "
                "model_mirror cleared."
            )
            _print_leftover_worker_dirs(un)
            print("\nMirror uninstall complete.")
            return 0

        # Deselect computation: --mirror reads from the SAME rbtv.json, so there
        # is no prior-vs-new divergence — deselection does not apply on a
        # mirror-only run (the election is identical to the recorded state).
        # We still call the driver in the same render/uninstall order as the full
        # install for consistency, but deselected is always empty here.
        try:
            mirror_render, _mirror_uninstall = _import_mirror_driver(rbtv_root)

            if mirrorable:
                rendered = mirror_render(
                    mirror_target,
                    mirrorable,
                    excluded_paths=requested_excluded_paths,
                )
                # The driver already wrote model_mirror to rbtv.json via
                # state.write_mirror_block (preserving all other keys). Call
                # update_mirror_state with the driver's final block so the
                # --mirror contract is satisfied and the state is consistent.
                post_state = read_state(mirror_target)
                if post_state is not None and isinstance(
                    post_state.get("model_mirror"), dict
                ):
                    update_mirror_state(
                        mirror_target, model_mirror=post_state["model_mirror"]
                    )
                verb = "updated" if rendered.files_written else "verified (no changes)"
                print(
                    f"  Mirror: [{', '.join(sorted(mirrorable))}] — "
                    f"{len(rendered.managed_files)} managed file(s) {verb}."
                )
            else:
                print("  Mirror: no mirrorable packages elected — nothing to render.")
        except Exception as exc:
            raise SystemExit(
                f"\nERROR — mirror refresh failed: {exc}\n"
                "  The workspace's mirror artifacts may be incomplete. "
                "Re-run once the cause is resolved."
            ) from exc

        print("\nMirror refresh complete.")
        return 0

    # --- Resolve target path -------------------------------------------------

    if args.target:
        target_root = args.target.resolve()
    elif args.non_interactive:
        raise SystemExit("--target is required in non-interactive mode.")
    else:
        found = find_state_upward(Path.cwd())
        if found:
            from .tui import confirm
            found_dir, existing_state = found
            print(f"  Found existing install at: {found_dir}")
            if confirm("Install to this path?", default=True):
                target_root = found_dir
            else:
                target_root = _prompt_target(existing_state)
        else:
            target_root = _prompt_target(None)

    target_root.mkdir(parents=True, exist_ok=True)
    existing_state = read_state(target_root)

    # --- Load manifest -------------------------------------------------------

    manifest = load_manifest(rbtv_root / "admin" / "install" / "module-manifest.json")
    always = [name for name, mod in manifest.items() if mod.always_installed]
    available = list(manifest.keys())

    # --- Resolve modules -----------------------------------------------------

    if args.modules:
        chosen_modules = tuple(m.strip() for m in args.modules.split(",") if m.strip())
        for m in always:
            if m not in chosen_modules:
                chosen_modules = (m,) + chosen_modules
        for m in chosen_modules:
            if m not in available:
                raise SystemExit(f"Unknown module: {m}")
    elif args.non_interactive and existing_state:
        chosen_modules = tuple(existing_state.get("modules", always))
    elif args.non_interactive:
        chosen_modules = tuple(always)
    else:
        existing_modules = (
            tuple(existing_state["modules"]) if existing_state else None
        )
        chosen_modules = _prompt_modules_interactive(manifest, always, existing_modules)

    # --- Resolve custom component exclusions ---------------------------------

    previous_excluded: set[str] = set()
    if existing_state:
        previous_excluded = set(existing_state.get("excluded_components", []))

    if args.non_interactive or args.modules:
        excluded_components = previous_excluded
    else:
        excluded_components = _prompt_custom_components(
            manifest, chosen_modules, previous_excluded
        )

    # --- Resolve orchestration model packages (D18) --------------------------

    mp_installed, mp_absent, mp_persisted, mv_persisted = _resolve_model_packages(
        rbtv_root=rbtv_root,
        chosen_modules=chosen_modules,
        requested_packages=requested_model_packages,
        requested_variants=requested_model_variants,
        non_interactive=args.non_interactive,
        used_modules_flag=bool(args.modules),
        existing_state=existing_state,
    )

    env_file_value = _resolve_env_file(
        requested_flag=args.env_file,
        existing_state=existing_state,
        chosen_modules=chosen_modules,
        non_interactive=args.non_interactive,
        used_modules_flag=bool(args.modules),
    )

    model_plans_file_value = _resolve_model_plans_file(
        requested_flag=args.model_plans_file,
        existing_state=existing_state,
        chosen_modules=chosen_modules,
        non_interactive=args.non_interactive,
        used_modules_flag=bool(args.modules),
    )

    # --- Install -------------------------------------------------------------

    ctx = resolve_from_cli(
        target=target_root,
        rbtv_path=rbtv_root,
        modules=chosen_modules,
    )

    removed = clear_previous_install(ctx.target_root)
    print(f"\nRemoved {len(removed)} previously-installed rbtv-* files.")
    # Remove the rbtv-managed hook entry on every install (cleanup/uninstall path,
    # spec row 4). If orchestration is elected the hook is re-wired below; if not,
    # it stays absent (spec row 2). Idempotent: a no-op when already absent.
    _, hook_unwire_msg = remove_hook_entry(ctx.target_root)
    print(f"  {hook_unwire_msg}")

    installed_paths: list[str] = []
    skipped_count = 0
    stale_count = 0

    def _record(p: Path) -> None:
        rel = p.relative_to(ctx.target_root)
        installed_paths.append(str(rel).replace("\\", "/"))

    def _is_excluded(target_relative: Path) -> bool:
        return str(target_relative).replace("\\", "/") in excluded_components

    for module_name in chosen_modules:
        module = manifest[module_name]
        print(f"\nInstalling module: {module_name} — {module.description}")
        for skill in module.skills:
            if skill.stale:
                stale_count += 1
                continue
            if _is_excluded(skill.target_relative):
                skipped_count += 1
                continue
            written = install_skill(skill, module, ctx)
            _record(written)
            print(f"  skill    {_component_name(skill.target_relative)}")
        for command in module.commands:
            if command.stale:
                stale_count += 1
                continue
            if _is_excluded(command.target_relative):
                skipped_count += 1
                continue
            written = install_command(command, module, ctx)
            _record(written)
            print(f"  cmd      {_component_name(command.target_relative)}")
        for rule in module.rules:
            if rule.stale:
                stale_count += 1
                continue
            if _is_excluded(rule.target_relative):
                skipped_count += 1
                continue
            written = install_rule(rule, module, ctx)
            _record(written)
            print(f"  rule     {_component_name(rule.target_relative)}")
        for subagent in module.subagents:
            if subagent.stale:
                stale_count += 1
                continue
            if _is_excluded(subagent.target_relative):
                skipped_count += 1
                continue
            written = install_subagent(subagent, module, ctx)
            _record(written)
            print(f"  subagent {_component_name(subagent.target_relative)}")

    if skipped_count:
        print(f"\n  ({skipped_count} component(s) skipped by custom selection)")
    if stale_count:
        print(f"  ({stale_count} stale component(s) retired — not installed)")

    # --- Orchestration: permission sync + hook wire + plan caps + render check (D18) -

    # model_mirror block to persist in write_state. None => preserve any prior
    # block (write_state carries it forward from disk). Set to the driver-written
    # block when a mirror render runs below.
    model_mirror_block: dict[str, Any] | None = None

    if ORCHESTRATION_MODULE in chosen_modules:
        if mp_installed or mp_absent:
            # Permission allowlist reconcile (D17): elected CLI packages get
            # their manifest-declared entries in the target's
            # .claude/settings.local.json; non-elected packages' entries are
            # removed. Only manifest-declared strings are touched.
            _, perm_msg = sync_permission_rules(
                ctx.target_root, rbtv_root, mp_installed, mp_absent
            )
            print(f"  {perm_msg}")
        # Wire the context-monitor PostToolUse hook (p2-1). Runs for any
        # orchestration-elected install regardless of model-package selection,
        # because the hook is module-scoped (not package-scoped).
        _, hook_msg = sync_hook_entry(ctx.target_root, ctx.rbtv_relative)
        print(f"  {hook_msg}")
        # Per-model plan-size presets → write the chosen context-window caps into
        # model-plans.yaml (D14, p4-3). The effective pointer is the freshly-resolved
        # value or the carried-forward one from rbtv.json. A prior cap is re-confirmed
        # (offered as the default), never silently wiped. Only context_window is
        # written — cost is board-derived in the manifests (D11). Advisory: a None
        # result means the step did not apply (no pointer / no elected packages).
        effective_plans_file = model_plans_file_value
        if effective_plans_file is None and existing_state is not None:
            recorded = existing_state.get("model_plans_file")
            if isinstance(recorded, str):
                effective_plans_file = recorded
        plan_caps_result = _resolve_model_plan_caps(
            rbtv_root=rbtv_root,
            target_root=ctx.target_root,
            model_plans_file=effective_plans_file,
            installed_packages=mp_installed,
            non_interactive=args.non_interactive,
            used_modules_flag=bool(args.modules),
        )
        if plan_caps_result is not None:
            print(f"  {plan_caps_result[1]}")
        # Render-freshness check is advisory (WARN, never abort) — matches the
        # plugin-prereq convention. A stale manual degrades gracefully (manuals
        # are read JIT from the source repo; the routing card reads the live
        # folder, not a stored copy).
        status, render_msg = check_manual_render(rbtv_root)
        if status in ("stale", "error"):
            print(f"\n  WARNING — {render_msg}", file=sys.stderr)
            print(
                "  Manuals are read just-in-time from the RBTV source — re-render "
                "with:\n    python "
                + str(rbtv_root / "orchestration" / "models" / "render-manuals.py"),
                file=sys.stderr,
            )
        else:
            print(f"  {render_msg}")

        # --- Mirror render-on-elect / delete-on-deselect (driver-owned) ------
        # Runs ONLY inside the orchestration block, AFTER components are written.
        # The elected worker set is mp_installed (elected AND present). The driver
        # renders each elected worker's artifacts and ref-counted-deletes those a
        # worker DESELECTED since the prior rbtv.json no longer needs (shared
        # AGENTS.md / .agents/ survive while another worker needs them).
        elected_workers = list(mp_installed)
        mirrorable = _split_mirrorable(rbtv_root, elected_workers)

        # Deselection: packages in the prior rbtv.json's model_packages that are
        # no longer elected. claude-code-cli is native (never mirrored) so its presence
        # or absence in either set is inert to the driver.
        prior_packages: list[str] = []
        if existing_state is not None and "model_packages" in existing_state:
            prior_packages = list(existing_state["model_packages"])
        deselected = [p for p in prior_packages if p not in set(elected_workers)]

        try:
            mirror_render, mirror_uninstall = _import_mirror_driver(rbtv_root)

            # 1. Uninstall first so ref-counting frees only artifacts no remaining
            #    elected worker needs; covers the "elected none" case too (the
            #    deselection path removes now-unelected workers' artifacts even
            #    when nothing is rendered).
            if deselected:
                un = mirror_uninstall(
                    ctx.target_root, deselected, remaining_elected=elected_workers
                )
                print(
                    f"\n  Mirror: deselected [{', '.join(sorted(deselected))}] — "
                    f"deleted {len(un.deleted)} file(s), "
                    f"spared {len(un.spared)} hand-authored guidance file(s)."
                )
                _print_leftover_worker_dirs(un)

            # 2. Render the elected (mirrorable) worker set. Re-running changes
            #    nothing; the driver records the canonical managed-file set in
            #    rbtv.json's model_mirror block. excluded_paths: passing
            #    --exclude REPLACES the recorded list; omitting it (None) lets the
            #    driver default from prior state, PRESERVING the recorded list.
            if mirrorable:
                rendered = mirror_render(
                    ctx.target_root,
                    mirrorable,
                    excluded_paths=requested_excluded_paths,
                )
                print(
                    f"  Mirror: rendered [{', '.join(sorted(mirrorable))}] — "
                    f"{len(rendered.managed_files)} managed file(s) recorded."
                )
        except Exception as exc:  # driver raised mid-reconcile — fail loud.
            # Surface the error and abort before write_state so no success
            # model_mirror is claimed for a failed render (spec edge case). The
            # driver writes rbtv.json itself in two sub-steps (uninstall, then
            # render); if the uninstall sub-step already committed before the
            # failure, its model_mirror is on disk while model_packages is left
            # stale (write_state is skipped). The workspace is therefore in a
            # known-recoverable partial state, not a false success — re-running
            # the installer with the intended election heals it fully.
            raise SystemExit(
                f"\nERROR — mirror reconcile failed: {exc}\n"
                "  The workspace's mirror artifacts may be incomplete and "
                "rbtv.json's model_packages / model_mirror may disagree. No "
                "success model_mirror was written for the failed render. Re-run "
                "the installer with the intended worker set once the cause is "
                "resolved — the re-run reconciles the workspace fully."
            ) from exc

        # The driver wrote the final model_mirror block to rbtv.json (render runs
        # last, so the on-disk block reflects the post-uninstall+render truth).
        # Read it back and hand it to write_state so the block — carrying the
        # driver's records — persists in the SAME single payload as the installer
        # keys. Absent (elected none / block dropped) => None => no key written.
        post_state = read_state(ctx.target_root)
        if post_state is not None and isinstance(post_state.get("model_mirror"), dict):
            model_mirror_block = post_state["model_mirror"]

    # --- Write state ---------------------------------------------------------

    state_file = write_state(
        ctx.target_root,
        rbtv_version=str(defaults["rbtv"]["version"]),
        rbtv_relative=str(ctx.rbtv_relative).replace("\\", "/"),
        modules=chosen_modules,
        installed_files=installed_paths,
        excluded_components=excluded_components,
        model_packages=mp_persisted,
        model_variants=mv_persisted,
        model_mirror=model_mirror_block,
        env_file=env_file_value,
        model_plans_file=model_plans_file_value,
    )
    print(f"\nState written to {state_file.relative_to(ctx.target_root)}")

    _check_plugin_prereqs()

    print("\nInstall complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
