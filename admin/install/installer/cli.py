"""CLI entry point for the RBTV installer.

Orchestrates the full install flow:

  1. Resolve target workspace path (--target flag or interactive prompt)
  2. Load module manifest from admin/install/module-manifest.yaml
  3. Select modules (--modules flag, --non-interactive, or interactive checkbox)
  4. Optionally customize individual components within selected modules
  5. Clear previous rbtv-* files from .claude/ in the target
  6. Install selected components (baked skills/commands, copied rules/subagents)
  7. Write rbtv.yaml state file (persists choices for future re-installs)
  8. Check for required Claude Code plugins and warn if missing

The interactive flow uses installer.tui for arrow-key navigation and checkbox
selection. No external dependencies beyond PyYAML — the TUI is pure stdlib.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from .context import resolve_from_cli
from .generator import (
    clear_previous_install,
    install_command,
    install_rule,
    install_skill,
    install_subagent,
)
from .manifest import Module, load_manifest
from .state import find_state_upward, read_state, write_state


def _find_rbtv_root() -> Path:
    """Walk up from this file until a parent contains install.py AND admin/install/defaults.yaml."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "install.py").is_file() and (
            parent / "admin" / "install" / "defaults.yaml"
        ).is_file():
            return parent
    raise SystemExit(
        f"Cannot locate RBTV root — no ancestor of {current} contains "
        f"install.py AND admin/install/defaults.yaml."
    )


def _load_defaults(rbtv_root: Path) -> dict[str, Any]:
    defaults_path = rbtv_root / "admin" / "install" / "defaults.yaml"
    return yaml.safe_load(defaults_path.read_text(encoding="utf-8"))


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
        ("Skills", [(_component_name(s.target_relative), s.description) for s in module.skills]),
        ("Commands", [(_component_name(c.target_relative), c.description) for c in module.commands]),
        ("Rules", [(_component_name(r.target_relative), r.description) for r in module.rules]),
        ("Subagents", [(_component_name(a.target_relative), a.description) for a in module.subagents]),
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
        return set()

    excluded: set[str] = set()

    for mod_name in chosen_modules:
        mod = manifest[mod_name]
        items: list[dict[str, Any]] = []
        keys: list[str] = []

        for s in mod.skills:
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
        help="Skip all prompts; use existing rbtv.yaml + --modules only.",
    )
    args = parser.parse_args(argv)

    rbtv_root = _find_rbtv_root()
    defaults = _load_defaults(rbtv_root)

    print(f"\n  RBTV Installer v{defaults['rbtv']['version']}\n")

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
            print(f"  Found existing rbtv.yaml at: {found_dir}")
            if confirm("Install to this path?", default=True):
                target_root = found_dir
            else:
                target_root = _prompt_target(existing_state)
        else:
            target_root = _prompt_target(None)

    target_root.mkdir(parents=True, exist_ok=True)
    existing_state = read_state(target_root)

    # --- Load manifest -------------------------------------------------------

    manifest = load_manifest(rbtv_root / "admin" / "install" / "module-manifest.yaml")
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

    # --- Install -------------------------------------------------------------

    ctx = resolve_from_cli(
        target=target_root,
        rbtv_path=rbtv_root,
        modules=chosen_modules,
    )

    removed = clear_previous_install(ctx.target_root)
    print(f"\nRemoved {len(removed)} previously-installed rbtv-* files.")

    installed_paths: list[str] = []
    skipped_count = 0

    def _record(p: Path) -> None:
        rel = p.relative_to(ctx.target_root)
        installed_paths.append(str(rel).replace("\\", "/"))

    def _is_excluded(target_relative: Path) -> bool:
        return str(target_relative).replace("\\", "/") in excluded_components

    for module_name in chosen_modules:
        module = manifest[module_name]
        print(f"\nInstalling module: {module_name} — {module.description}")
        for skill in module.skills:
            if _is_excluded(skill.target_relative):
                skipped_count += 1
                continue
            written = install_skill(skill, module, ctx)
            _record(written)
            print(f"  skill    {_component_name(skill.target_relative)}")
        for command in module.commands:
            if _is_excluded(command.target_relative):
                skipped_count += 1
                continue
            written = install_command(command, module, ctx)
            _record(written)
            print(f"  cmd      {_component_name(command.target_relative)}")
        for rule in module.rules:
            if _is_excluded(rule.target_relative):
                skipped_count += 1
                continue
            written = install_rule(rule, module, ctx)
            _record(written)
            print(f"  rule     {_component_name(rule.target_relative)}")
        for subagent in module.subagents:
            if _is_excluded(subagent.target_relative):
                skipped_count += 1
                continue
            written = install_subagent(subagent, module, ctx)
            _record(written)
            print(f"  subagent {_component_name(subagent.target_relative)}")

    if skipped_count:
        print(f"\n  ({skipped_count} component(s) skipped by custom selection)")

    # --- Write state ---------------------------------------------------------

    state_file = write_state(
        ctx.target_root,
        rbtv_version=str(defaults["rbtv"]["version"]),
        rbtv_relative=str(ctx.rbtv_relative).replace("\\", "/"),
        modules=chosen_modules,
        installed_files=installed_paths,
        excluded_components=excluded_components,
    )
    print(f"\nState written to {state_file.relative_to(ctx.target_root)}")

    _check_plugin_prereqs()

    print("\nInstall complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
