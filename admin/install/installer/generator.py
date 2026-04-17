"""Generate thin loaders and copy rules/subagents into the target."""
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


def clear_previous_install(target_root: Path, installed_files: list[str]) -> list[Path]:
    """O3: delete only the files from the previous install, not by prefix.

    `installed_files` is a list of target-relative paths stored in rbtv.yaml
    from the previous install. For skills (directories), we also remove the
    parent directory if it becomes empty.

    Returns list of paths removed for logging.
    """
    removed: list[Path] = []
    skill_dirs_seen: set[Path] = set()
    for rel in installed_files:
        abs_path = target_root / rel
        if abs_path.is_file():
            abs_path.unlink()
            removed.append(abs_path)
            # Track parent dir — if it's a skill SKILL.md, the dir is
            # meaningful and should be removed if empty
            parent = abs_path.parent
            if (
                parent.is_dir()
                and parent.name.startswith("rbtv-")
                and parent.parent.name == "skills"
            ):
                skill_dirs_seen.add(parent)
    # Remove now-empty skill dirs
    for d in skill_dirs_seen:
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
            removed.append(d)
    return removed
