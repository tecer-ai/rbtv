"""CLI entry point for install.py."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
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
from .state import read_state, write_state


def _find_rbtv_root() -> Path:
    """Walk up from this file until a parent contains install.py AND admin/install/defaults.yaml.

    This is robust against future installer-package restructuring — we don't
    assume a fixed number of parent-directory hops (O7).
    """
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


def _prompt_modules(
    available: list[str],
    always: list[str],
    existing: tuple[str, ...] | None,
) -> tuple[str, ...]:
    print("\nAvailable modules:")
    for m in available:
        marker = " (always installed)" if m in always else ""
        pre_selected = (
            " [currently installed]" if existing and m in existing else ""
        )
        print(f"  - {m}{marker}{pre_selected}")
    if existing is not None:
        print(
            "\nPress Enter to keep current modules, "
            "or enter comma-separated module names to change."
        )
        raw = input("Modules: ").strip()
        if not raw:
            return existing
    else:
        raw = input(
            "\nComma-separated modules to install (core is always included): "
        ).strip()
    if not raw:
        return tuple(always)
    chosen = [m.strip() for m in raw.split(",") if m.strip()]
    for m in always:
        if m not in chosen:
            chosen.insert(0, m)
    for m in chosen:
        if m not in available:
            raise SystemExit(f"Unknown module: {m}")
    return tuple(chosen)


def _check_plugin_prereqs() -> None:
    """O8: warn if Claude Code plugins that RBTV menu items invoke are missing."""
    home = Path.home()
    candidates = [home / ".claude" / "plugins", home / ".claude" / "plugins" / "cache"]
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
            # Plugins may be stored as plugin-name dirs or nested under vendor dirs
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
        required=True,
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
    target_root = args.target.resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    existing_state = read_state(target_root)

    manifest = load_manifest(rbtv_root / "admin" / "install" / "module-manifest.yaml")
    always = [name for name, mod in manifest.items() if mod.always_installed]
    available = list(manifest.keys())

    if args.modules:
        chosen_modules = tuple(m.strip() for m in args.modules.split(",") if m.strip())
        for m in always:
            if m not in chosen_modules:
                chosen_modules = (m,) + chosen_modules
        # Validate
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
        chosen_modules = _prompt_modules(available, always, existing_modules)

    ctx = resolve_from_cli(
        target=target_root,
        rbtv_path=rbtv_root,
        modules=chosen_modules,
    )

    removed = clear_previous_install(ctx.target_root)
    print(f"\nRemoved {len(removed)} previously-installed rbtv-* files.")

    installed_paths: list[str] = []

    def _record(p: Path) -> None:
        rel = p.relative_to(ctx.target_root)
        installed_paths.append(str(rel).replace("\\", "/"))

    for module_name in chosen_modules:
        module = manifest[module_name]
        print(f"\nInstalling module: {module_name}")
        for skill in module.skills:
            written = install_skill(skill, module, ctx)
            _record(written)
            print(f"  skill    → {written.relative_to(ctx.target_root)}")
        for command in module.commands:
            written = install_command(command, module, ctx)
            _record(written)
            print(f"  cmd      → {written.relative_to(ctx.target_root)}")
        for rule in module.rules:
            written = install_rule(rule, module, ctx)
            _record(written)
            print(f"  rule     → {written.relative_to(ctx.target_root)}")
        for subagent in module.subagents:
            written = install_subagent(subagent, module, ctx)
            _record(written)
            print(f"  subagent → {written.relative_to(ctx.target_root)}")

    state_file = write_state(
        ctx.target_root,
        rbtv_version=str(defaults["rbtv"]["version"]),
        rbtv_relative=str(ctx.rbtv_relative).replace("\\", "/"),
        modules=chosen_modules,
        installed_files=installed_paths,
    )
    print(f"\nState written to {state_file.relative_to(ctx.target_root)}")

    _check_plugin_prereqs()

    print("\nInstall complete.")
    print("")
    print("Next step: configure output path routing.")
    print("  Open a Claude Code session in the target workspace and run:")
    print("      /rbtv-output-routing")
    print("  This scans your CLAUDE.md files and interactively writes")
    print("  `## File Routing` blocks so RBTV components know")
    print("  where to place outputs. See the rbtv-output-resolution rule")
    print("  for how components consume these blocks.")
    print("")
    print("  Skipping this step is OK — components fall back to degraded mode")
    print("  (ask-per-write) until routing is populated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
