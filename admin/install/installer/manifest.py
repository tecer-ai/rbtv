"""Module manifest parser for RBTV install.

Parses admin/install/module-manifest.json into typed dataclasses. Each module
declares skills, commands, rules, and subagents with source paths (relative to
the RBTV root) and target paths (relative to the target workspace root).

The manifest is the single source of truth for what gets installed per module.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillEntry:
    source_template: Path
    target_relative: Path
    bake_keys: tuple[str, ...]
    description: str = ""


@dataclass(frozen=True)
class CommandEntry:
    source_template: Path
    target_relative: Path
    bake_keys: tuple[str, ...]
    description: str = ""


@dataclass(frozen=True)
class RuleEntry:
    source: Path
    target_relative: Path
    mode: str  # "copy"
    description: str = ""


@dataclass(frozen=True)
class SubagentEntry:
    source: Path
    target_relative: Path
    mode: str  # "copy"
    description: str = ""


@dataclass(frozen=True)
class Module:
    name: str
    description: str
    always_installed: bool
    skills: tuple[SkillEntry, ...]
    commands: tuple[CommandEntry, ...]
    rules: tuple[RuleEntry, ...]
    subagents: tuple[SubagentEntry, ...]


def load_manifest(manifest_path: Path) -> dict[str, Module]:
    """Parse the manifest JSON and return a dict of {module_name: Module}."""
    raw: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    modules: dict[str, Module] = {}
    for name, data in raw.items():
        if name == "cross_module_agents":
            continue
        skills = tuple(
            SkillEntry(
                source_template=Path(s["source_template"]),
                target_relative=Path(s["target"]),
                bake_keys=tuple(s.get("bake", [])),
                description=s.get("description", ""),
            )
            for s in data.get("skills", [])
        )
        commands = tuple(
            CommandEntry(
                source_template=Path(c["source_template"]),
                target_relative=Path(c["target"]),
                bake_keys=tuple(c.get("bake", [])),
                description=c.get("description", ""),
            )
            for c in data.get("commands", [])
        )
        rules = tuple(
            RuleEntry(
                source=Path(r["source"]),
                target_relative=Path(r["target"]),
                mode=r.get("mode", "copy"),
                description=r.get("description", ""),
            )
            for r in data.get("rules", [])
        )
        subagents = tuple(
            SubagentEntry(
                source=Path(s["source"]),
                target_relative=Path(s["target"]),
                mode=s.get("mode", "copy"),
                description=s.get("description", ""),
            )
            for s in data.get("subagents", [])
        )
        modules[name] = Module(
            name=name,
            description=data.get("description", ""),
            always_installed=bool(data.get("always_installed", False)),
            skills=skills,
            commands=commands,
            rules=rules,
            subagents=subagents,
        )
    return modules
