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
    bake_availability_line,
    check_manual_render,
    discover_model_packages,
    resolve_selected_packages,
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
        return set()

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


def _prompt_model_packages(
    available: list[str],
    previous_selection: list[str] | None,
) -> tuple[str, ...]:
    """Interactive checkbox for orchestration model-package selection.

    Each package is independently toggleable (no always-on packages). On a
    re-install, the previous selection is pre-checked; on a first install every
    available package is pre-checked (full install is the default).
    """
    from .tui import checkbox

    items = []
    for name in available:
        if previous_selection is None:
            pre = True
        else:
            pre = name in previous_selection
        items.append({"label": name, "selected": pre})

    selected_indices = checkbox(
        "\nSelect orchestration model packages (kimi/codex/claude-cli/qwen) "
        "to make available in this workspace:",
        items,
    )
    return tuple(available[i] for i in selected_indices)


def _resolve_model_packages(
    rbtv_root: Path,
    chosen_modules: tuple[str, ...],
    requested_flag: tuple[str, ...] | None,
    non_interactive: bool,
    used_modules_flag: bool,
    existing_state: dict[str, Any] | None,
) -> tuple[list[str], list[str], list[str] | None]:
    """Resolve which model packages this workspace elects.

    Returns (installed, absent, persisted) where:
      - installed / absent feed the availability-line bake,
      - persisted is the list written to rbtv.json (None => key omitted, i.e. the
        orchestration module is not installed so packages do not apply).

    Selection precedence mirrors module resolution:
      --model-packages flag > non-interactive(prev state or all) > interactive picker.
    """
    if ORCHESTRATION_MODULE not in chosen_modules:
        return [], [], None

    available = discover_model_packages(rbtv_root)
    if not available:
        # Orchestration installed but no packages shipped yet — nothing to elect.
        return [], [], []

    previous = None
    if existing_state is not None and "model_packages" in existing_state:
        previous = list(existing_state["model_packages"])

    if requested_flag is not None:
        requested: tuple[str, ...] | None = requested_flag
    elif non_interactive or used_modules_flag:
        # Scripted path: reuse prior selection if any, else elect all available.
        requested = tuple(previous) if previous is not None else None
    else:
        requested = _prompt_model_packages(available, previous)

    installed, absent, unknown = resolve_selected_packages(available, requested)
    if unknown:
        print(
            f"\n  WARNING — unknown model package(s) ignored: {', '.join(unknown)} "
            f"(available: {', '.join(available)})",
            file=sys.stderr,
        )
    return installed, absent, installed


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
    ).strip()
    return entered or None


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

    ``claude-cli`` loads its guidance natively and is mirror-less — it is dropped
    silently (never a missing-assets warning). Any OTHER elected package whose
    ``orchestration/models/<pkg>/mirror-assets/`` tree is absent is skipped with a
    NAMED warning (matches the spec's "ships no mirror-assets" edge case — a skip,
    never a crash), because the driver's config renderer raises on a missing
    assets tree. The driver itself further drops ids it does not know.
    """
    models_dir = rbtv_root / "orchestration" / "models"
    mirrorable: list[str] = []
    for pkg in elected:
        if pkg == "claude-cli":
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
            "(kimi, codex, claude-cli, qwen). Omit to keep the previous selection "
            "or elect all available packages. Empty string elects none. Only "
            "applies when the orchestration module is installed."
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
            "teardown for every currently-elected package."
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

    mp_installed, mp_absent, mp_persisted = _resolve_model_packages(
        rbtv_root=rbtv_root,
        chosen_modules=chosen_modules,
        requested_flag=requested_model_packages,
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

    # --- Orchestration: availability-line bake + render-freshness check (D18) -

    # model_mirror block to persist in write_state. None => preserve any prior
    # block (write_state carries it forward from disk). Set to the driver-written
    # block when a mirror render runs below.
    model_mirror_block: dict[str, Any] | None = None

    if ORCHESTRATION_MODULE in chosen_modules:
        if mp_installed or mp_absent:
            changed, msg = bake_availability_line(rbtv_root, mp_installed, mp_absent)
            print(f"\n  {msg}")
        # Render-freshness check is advisory (WARN, never abort) — matches the
        # plugin-prereq convention. A stale manual degrades gracefully (manuals
        # are read JIT from the source repo; the routing card trusts the live
        # folder over any baked line).
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
        # no longer elected. claude-cli is native (never mirrored) so its presence
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
        model_mirror=model_mirror_block,
        env_file=env_file_value,
    )
    print(f"\nState written to {state_file.relative_to(ctx.target_root)}")

    _check_plugin_prereqs()

    print("\nInstall complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
