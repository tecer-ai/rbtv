"""Generate thin loaders and copy rules/subagents into the target.

Two installation modes per component type:

  - Bake (skills, commands): Read a source template, replace {rbtv_path}
    placeholders with the resolved relative path, write the result.
    The installed file is a thin loader that points back to the RBTV source.

  - Copy (rules, subagents): Straight file copy from RBTV source to target.
    No placeholder substitution — these files are self-contained.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .context import InstallContext
from .manifest import CommandEntry, Module, RuleEntry, SkillEntry, SubagentEntry


def _resolve_bake_value(key: str, ctx: InstallContext) -> str:
    """Resolve template placeholder to a literal string.

    Per D7: only `rbtv_path` is baked. Output paths are resolved at runtime
    by the rbtv-output-resolution rule reading `## File Routing` blocks.
    """
    if key == "rbtv_path":
        # Vault-relative path (per D19) — portable across vault relocations.
        return str(ctx.rbtv_relative).replace("\\", "/")
    raise KeyError(f"Unknown bake key: {key}")


def _bake(template_text: str, keys: tuple[str, ...], ctx: InstallContext) -> str:
    baked = template_text
    for key in keys:
        placeholder = "{" + key + "}"
        baked = baked.replace(placeholder, _resolve_bake_value(key, ctx))
    return baked


def _write_file(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def install_skill(entry: SkillEntry, module: Module, ctx: InstallContext) -> Path:
    source = ctx.rbtv_root / entry.source_template
    target = ctx.target_root / entry.target_relative
    template_text = source.read_text(encoding="utf-8")
    _write_file(target, _bake(template_text, entry.bake_keys, ctx))
    return target


def install_command(entry: CommandEntry, module: Module, ctx: InstallContext) -> Path:
    source = ctx.rbtv_root / entry.source_template
    target = ctx.target_root / entry.target_relative
    template_text = source.read_text(encoding="utf-8")
    _write_file(target, _bake(template_text, entry.bake_keys, ctx))
    return target


def install_rule(entry: RuleEntry, module: Module, ctx: InstallContext) -> Path:
    source = ctx.rbtv_root / entry.source
    target = ctx.target_root / entry.target_relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target


def install_subagent(entry: SubagentEntry, module: Module, ctx: InstallContext) -> Path:
    source = ctx.rbtv_root / entry.source
    target = ctx.target_root / entry.target_relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target


def clear_previous_install(target_root: Path) -> list[Path]:
    """Delete all rbtv-prefixed files from .claude/ before a fresh install.

    Scans skills, commands, rules, and agents directories for any entry
    whose name starts with 'rbtv-' and removes it. This ensures a clean
    slate regardless of whether rbtv.yaml tracked the previous install.

    Returns list of paths removed for logging.
    """
    removed: list[Path] = []
    claude_dir = target_root / ".claude"

    scan_targets = [
        (claude_dir / "rules", "file"),
        (claude_dir / "commands", "file"),
        (claude_dir / "agents", "file"),
        (claude_dir / "skills", "dir"),
    ]

    for parent, kind in scan_targets:
        if not parent.is_dir():
            continue
        for entry in sorted(parent.iterdir()):
            if not entry.name.startswith("rbtv-"):
                continue
            if kind == "dir" and entry.is_dir():
                shutil.rmtree(entry)
                removed.append(entry)
            elif kind == "file" and entry.is_file():
                entry.unlink()
                removed.append(entry)

    return removed
