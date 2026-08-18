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
    build_plan_size_presets,
    clobbered_variants,
    read_manifest_context_ceiling,
    read_model_plan_caps,
    read_model_plan_models,
    remove_hook_entry,
    sync_hook_entry,
    sync_permission_rules,
    write_model_plan_caps,
)
from .state import find_state_upward, read_state, update_mirror_state, write_state

# Orchestration module: permission-rule sync, hook wire, plan-cap pointer.
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
    displays: dict[str, str] = {}

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

    The driver package lives at ``ignite/team-kit/mirror/driver/`` (team-kit
    owns the one implementation; per decision 5 / W4 of the 2026-08-18
    models-tree-retirement build) and is imported as a top-level ``driver``
    package — the same reachability shim the driver's own ``cli.py`` uses for
    loose-script invocation: insert the PARENT of ``driver/`` onto ``sys.path``
    (it has no ancestor ``__init__.py`` chain to the installer package) and
    import by name. The import is lazy (called only when the orchestration
    module is installed) so a non-orchestration install never pays the cost and
    a driver-import failure surfaces only when a mirror is actually requested.

    Returns ``(render, uninstall)`` callables.
    """
    driver_parent = rbtv_root / "ignite" / "team-kit" / "mirror"
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
    silently (never a missing-assets warning). A package the driver knows as
    CONFIG-LESS (``PackageFacts.config_dir is None``, e.g. opencode — no
    config assets seed by design) is mirrorable WITHOUT an assets tree (it
    renders only the shared ``.agents/`` library). Any
    OTHER elected package whose ``ignite/team-kit/mirror/assets/`` subtree is
    absent is skipped with a NAMED warning (matches the spec's "ships no assets"
    edge case — a skip, never a crash), because the driver's config renderer raises on
    a missing assets tree. The driver itself further drops ids it does not know.
    """
    mirror_dir = rbtv_root / "ignite" / "team-kit" / "mirror"
    assets_dir = mirror_dir / "assets"
    # Config-less driver-known packages: mirrorable with no assets. Also derive
    # each config-bearing package's assets-subdir name from its config_dir
    # (".codex" -> "codex") so the existence check below tracks the driver's own
    # assets layout without duplicating its per-package mapping here.
    # Lazy import with the same reachability shim as _import_mirror_driver; on any
    # import failure fall back to treating every non-native package as unmirrorable
    # (never crash the install).
    try:
        driver_parent = mirror_dir
        if str(driver_parent) not in sys.path:
            sys.path.insert(0, str(driver_parent))
        from driver import PACKAGE_FACTS  # type: ignore[import-not-found]
        configless = {p for p, f in PACKAGE_FACTS.items() if f.config_dir is None}
        assets_subdir = {
            p: f.config_dir.lstrip(".")
            for p, f in PACKAGE_FACTS.items()
            if f.config_dir is not None
        }
    except Exception:
        configless = set()
        assets_subdir = {}
    # No election: an empty caller list means "every package the driver knows".
    pkgs = list(elected) if elected else sorted(set(configless) | set(assets_subdir))
    mirrorable: list[str] = []
    for pkg in pkgs:
        if pkg == "claude-code-cli":
            continue  # native, mirror-less — silently skipped
        if pkg in configless:
            mirrorable.append(pkg)  # config-less package — no assets tree needed
        elif pkg in assets_subdir and (assets_dir / assets_subdir[pkg]).is_dir():
            mirrorable.append(pkg)
        else:
            print(
                f"\n  WARNING — mirror skipped for '{pkg}': no config assets "
                f"shipped at ignite/team-kit/mirror/assets/ "
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
    parser = argparse.ArgumentParser(
        description=(
            "Install RBTV into a target workspace. Leftover model_packages / "
            "model_variants keys in an existing rbtv.json are left in place and unread."
        ),
        epilog=(
            "Leftover rbtv.json keys: model_packages and model_variants in an "
            "existing rbtv.json are left in place and unread. The installer no "
            "longer elects model packages; the routable set is the cast catalog "
            "intersect availability."
        ),
    )
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
            "Mirror-only mode: refresh the mirror artifacts (the shared .agents/ "
            "library and per-model config dirs) for every package the driver "
            "knows, without running target/module/component prompts or "
            "reinstalling components. Does not read leftover model_packages / "
            "model_variants keys. Guidance files (AGENTS.md/QWEN.md) are NOT "
            "rendered — that leg is retired. Resolves the target via --target or "
            "the nearest rbtv.json."
        ),
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        metavar="PATH",
        default=None,
        help=(
            "Workspace-root-relative posix path(s) recorded in rbtv.json "
            "(model_mirror.excluded_paths). INERT since the guidance retirement "
            "(d-hard-guard-retire-model-mirror, 2026-08-10) — they only ever "
            "constrained the CLAUDE.md walk; the library and config artifacts "
            "render to fixed paths. Passing --exclude REPLACES the recorded list; "
            "omitting it PRESERVES it."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "With --mirror: read-only drift probe. Writes NOTHING — reports every "
            "managed file that is missing or has fallen behind its source, then "
            "exits 1 if the mirror is out of sync and 0 if it is current. Use it "
            "to ask 'is my mirror current?' without refreshing it; a plain "
            "--mirror run is what refreshes."
        ),
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help=(
            "With --mirror: remove ALL generated mirror artifacts for the target "
            "(the shared .agents/ library, per-model config dirs, and any guidance "
            "file still recorded from a pre-retirement install) and clear the "
            "model_mirror block from rbtv.json. A full mirror teardown. A worker "
            "dir emptied of rbtv's files is removed; one still holding files rbtv "
            "did not create is named (not deleted) so you can remove it by hand."
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

    # --check is a mirror-probe flag. Guarding it here rather than silently ignoring
    # it matters: a caller who types `install.py --check` expecting a dry run would
    # otherwise get a FULL INSTALL.
    if args.check and not args.mirror:
        raise SystemExit(
            "--check applies only with --mirror (read-only mirror drift probe). "
            "Run: install.py --mirror --check [--target <workspace>]."
        )
    # Mirrors the driver's own rejection: one writes nothing, the other deletes
    # everything — there is no coherent combined meaning.
    if args.check and args.uninstall:
        print(
            "ERROR: --check and --uninstall are mutually exclusive "
            "(--check writes nothing; --uninstall removes every mirror artifact).",
            file=sys.stderr,
        )
        raise SystemExit(2)

    rbtv_root = _find_rbtv_root()

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

        # Installer no longer elects: refresh every package the driver knows.
        # Leftover model_packages / model_variants keys are unread.
        mirrorable = _split_mirrorable(rbtv_root, [])

        # --- --mirror --uninstall: full mirror teardown for the target ---------
        if args.uninstall:
            try:
                _mirror_render, mirror_uninstall = _import_mirror_driver(rbtv_root)
                # Tear down every driver-known package (remaining_elected
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
                + (
                    f"protected {len(un.protected)} recorded file(s) under an "
                    "always-excluded prefix (left on disk, un-managed); "
                    if un.protected
                    else ""
                )
                + "model_mirror cleared."
            )
            _print_leftover_worker_dirs(un)
            print("\nMirror uninstall complete.")
            return 0

        # Deselection does not apply on a mirror-only run (no election).
        # We still call the driver in the same render/uninstall order as the full
        # install for consistency.
        try:
            mirror_render, _mirror_uninstall = _import_mirror_driver(rbtv_root)

            if mirrorable:
                rendered = mirror_render(
                    mirror_target,
                    mirrorable,
                    check=args.check,
                    excluded_paths=requested_excluded_paths,
                )

                # --- --mirror --check: report drift, write nothing, exit-code it ---
                if args.check:
                    for rel in rendered.stale_paths:
                        print(f"  stale: {rel} is missing or differs from its source")
                    if rendered.stale:
                        print(
                            f"\n  Mirror: [{', '.join(sorted(mirrorable))}] is OUT OF SYNC "
                            f"— {len(rendered.managed_files)} managed file(s) expected."
                        )
                        print(
                            "\nRefresh it with: install.py --mirror "
                            "--non-interactive --target <workspace>"
                        )
                        return 1
                    print(
                        f"  Mirror: [{', '.join(sorted(mirrorable))}] is in sync "
                        f"— {len(rendered.managed_files)} managed file(s)."
                    )
                    print("\nMirror check complete — no drift.")
                    return 0

                # The driver already wrote model_mirror to rbtv.json via
                # state.write_mirror_block (preserving all other keys). Call
                # update_mirror_state with the driver's final block so the
                # --mirror contract is satisfied and the state is consistent.
                # NEVER reached under --check: this is a write, and a probe writes
                # nothing at all.
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
                noun = "check" if args.check else "render"
                print(f"  Mirror: no mirrorable packages — nothing to {noun}.")
        except Exception as exc:
            verb = "check" if args.check else "refresh"
            raise SystemExit(
                f"\nERROR — mirror {verb} failed: {exc}\n"
                + (
                    "  Nothing was written.\n"
                    if args.check
                    else "  The workspace's mirror artifacts may be incomplete.\n"
                )
                + "  Re-run once the cause is resolved."
            ) from exc

        print("\nMirror refresh complete." if not args.check else "\nMirror check complete.")
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

    # --- Orchestration: permission sync + hook wire + plan caps (D18) --------

    # model_mirror block to persist in write_state. None => preserve any prior
    # block (write_state carries it forward from disk). Set to the driver-written
    # block when a mirror render runs below.
    model_mirror_block: dict[str, Any] | None = None

    if ORCHESTRATION_MODULE in chosen_modules:
        # Permission allowlist sync (D17): union of catalog-declared rules for
        # launchable CLI workers into the target's .claude/settings.local.json.
        # No elected/absent split. Only catalog-declared strings are touched.
        _, perm_msg = sync_permission_rules(ctx.target_root, rbtv_root)
        print(f"  {perm_msg}")
        # Wire the context-monitor PostToolUse hook (p2-1). Module-scoped.
        _, hook_msg = sync_hook_entry(ctx.target_root, ctx.rbtv_relative)
        print(f"  {hook_msg}")
        # Per-model plan-size presets → write the chosen context-window caps into
        # model-plans.yaml (D14, p4-3). The effective pointer is the freshly-resolved
        # value or the carried-forward one from rbtv.json. A prior cap is re-confirmed
        # (offered as the default), never silently wiped. Only context_window is
        # written. Advisory: a None result means the step did not apply (no pointer
        # / no packages passed — the installer no longer elects a package set).
        effective_plans_file = model_plans_file_value
        if effective_plans_file is None and existing_state is not None:
            recorded = existing_state.get("model_plans_file")
            if isinstance(recorded, str):
                effective_plans_file = recorded
        plan_caps_result = _resolve_model_plan_caps(
            rbtv_root=rbtv_root,
            target_root=ctx.target_root,
            model_plans_file=effective_plans_file,
            installed_packages=[],
            non_interactive=args.non_interactive,
            used_modules_flag=bool(args.modules),
        )
        if plan_caps_result is not None:
            print(f"  {plan_caps_result[1]}")

        # --- Mirror render (driver-owned) ------------------------------------
        # Runs ONLY inside the orchestration block, AFTER components are written.
        # No election: refresh every package the driver knows. Leftover
        # model_packages keys are unread — no deselection from them. No guidance
        # file is ever rendered — retired by d-hard-guard-retire-model-mirror.
        mirrorable = _split_mirrorable(rbtv_root, [])
        deselected: list[str] = []

        try:
            mirror_render, mirror_uninstall = _import_mirror_driver(rbtv_root)

            # 1. Uninstall first so ref-counting frees only artifacts no remaining
            #    worker needs. Deselection is empty (no election).
            if deselected:
                un = mirror_uninstall(
                    ctx.target_root, deselected, remaining_elected=mirrorable
                )
                print(
                    f"\n  Mirror: deselected [{', '.join(sorted(deselected))}] — "
                    f"deleted {len(un.deleted)} file(s), "
                    f"spared {len(un.spared)} hand-authored guidance file(s)."
                    + (
                        f" Protected {len(un.protected)} recorded file(s) under an "
                        "always-excluded prefix (left on disk, un-managed)."
                        if un.protected
                        else ""
                    )
                )
                _print_leftover_worker_dirs(un)

            # 2. Render the driver-known worker set. Re-running changes
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
            # failure, its model_mirror is on disk (write_state is skipped).
            # The workspace is therefore in a known-recoverable partial state,
            # not a false success — re-running the installer heals it fully.
            raise SystemExit(
                f"\nERROR — mirror reconcile failed: {exc}\n"
                "  The workspace's mirror artifacts may be incomplete. No "
                "success model_mirror was written for the failed render. Re-run "
                "the installer once the cause is resolved — the re-run "
                "reconciles the workspace fully."
            ) from exc

        # The driver wrote the final model_mirror block to rbtv.json (render runs
        # last, so the on-disk block reflects the post-uninstall+render truth).
        # Read it back and hand it to write_state so the block — carrying the
        # driver's records — persists in the SAME single payload as the installer
        # keys. Absent (block dropped) => None => no key written.
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
