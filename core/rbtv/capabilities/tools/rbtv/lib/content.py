"""Rendering the body of every file the installer writes, and recognising the
ones it owns.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from discovery import Refuse, SKILL_FILE

from . import frontmatter
from .constants import (
    EFFORT_INERT,
    GENERATED_MARKERS,
    LEGACY_MARKS,
    LEGACY_PREFIX,
    MANAGED_BANNER,
    SUB_AGENT_SETTINGS,
    TOML_BANNER,
    MANAGED_MARK,
)
from .link_paths import absolute_links


def _yq(text: str) -> str:
    """A YAML-safe quoted scalar — json quoting is valid YAML (the colon-space
    in a `description:` is the failure class this closes)."""
    return json.dumps(str(text), ensure_ascii=False)


def _head(part: str, desc: str, named: bool,
          settings: dict[str, str] | None = None) -> str:
    """The frontmatter a harness lists a generated file by."""
    name_line = f"name: {part}\n" if named else ""
    extra = "".join(f"{key}: {_yq(value)}\n"
                    for key, value in (settings or {}).items())
    return f"---\n{name_line}description: {_yq(desc)}\n{extra}---\n"


def _loader(part: str, desc: str, entry: str, settings: dict[str, str]) -> str:
    """A harness's own sub-agent file: it points at the agent's prompt."""
    return (_head(part, desc, named=True, settings=settings)
            + f"\nRead `{entry}` NOW and follow it as this agent's full "
            "instructions.\n")


def _copy(head: str, source: Path, installation: Path | None,
          base: Path | None) -> str:
    """A source as the harness reads it: `head`, then the source's body after
    its own frontmatter. The copy sits away from the source's folder, so a
    link written from `base` becomes an absolute path."""
    _front, body = frontmatter.split(source.read_text(encoding="utf-8"))
    return head + absolute_links(body, installation, base=base)


def rule_skill_description(name: str) -> str:
    """What Codex lists a rule by. Codex has no always-loaded rules folder, so
    the description is what makes the model open the rule in every session."""
    return (f"CONTAINS: the standing rule {name}, which holds for every task "
            "in this workspace "
            "PURPOSE: act under this rule from the first action of a session "
            "to the last "
            "ALWAYS LOAD WHEN: a session starts, before the first action of "
            "any task, including a short question "
            "DO NOT LOAD WHEN: this rule is already open in this session")


def sub_agent_settings(harness: str, values: dict) -> tuple[dict[str, str], list[dict]]:
    """One harness's model and effort as its own sub-agent file names them,
    and the values that file cannot carry: [{setting, value, reason}]. The
    model is the harness's own id for it; a model with no effort dial has no
    effort to write."""
    applied: dict[str, str] = {}
    unapplied: list[dict] = []
    for setting, value in (("model", values["model_id"]), ("effort", values["effort"])):
        key = SUB_AGENT_SETTINGS[harness][setting]
        if setting == "effort" and value == EFFORT_INERT:
            unapplied.append({"setting": setting, "value": value,
                              "reason": f"{values['model']} has no effort setting"})
        elif key is None:
            unapplied.append({"setting": setting, "value": values[setting],
                              "reason": f"a {harness} sub-agent file has no "
                                        f"setting for {setting}"})
        else:
            applied[key] = value
    return applied, unapplied


def sub_agent_content(rel: str, harness: str, part: str, desc: str, entry: str,
                      values: dict) -> str:
    """An agent written as one harness's own sub-agent file: its name, its
    description, the instruction to read its prompt, and that harness's model
    and effort."""
    settings, _unapplied = sub_agent_settings(harness, values)
    if rel.endswith(".toml"):
        # Codex's own sub-agent definition.
        return TOML_BANNER + (
            f"name = {json.dumps(part)}\n"
            f"description = {json.dumps(desc, ensure_ascii=False)}\n"
            + "".join(f"{key} = {json.dumps(value)}\n"
                      for key, value in settings.items())
            + "developer_instructions = "
            + json.dumps(f"Read `{entry}` NOW and follow it as this "
                         "agent's full instructions.") + "\n")
    return _mark(_loader(part, desc, entry, settings))


_FRONTMATTER = re.compile(r"---\r?\n(?:.*?\r?\n)?---\r?\n", re.S)


def _mark(text: str) -> str:
    """Stamp *text* with the ownership marker (D12), AFTER any YAML frontmatter
    — a marker above a file's `---` block would stop that block parsing.
    CRLF counts: a Windows checkout (core.autocrlf) delivers `---\\r\\n`."""
    front = _FRONTMATTER.match(text)
    if front:
        cut = front.end()
        return text[:cut] + MANAGED_BANNER + text[cut:]
    return MANAGED_BANNER + text


def _marked(path: Path) -> bool:
    """True when this one file's head carries a machine-readable owner mark —
    ours, or a generated-mirror banner (D13 adoption). Unreadable proves
    nothing."""
    try:
        head = path.read_text(encoding="utf-8")[:2000]
    except (OSError, UnicodeDecodeError):
        return False
    return any(m in head for m in (MANAGED_MARK, *LEGACY_MARKS, *GENERATED_MARKERS))


def _is_ours(target: Path, rel: str) -> bool:
    """True when the FILE ITSELF proves this installer wrote it (D12): our
    ownership marker, a generated-mirror banner, a legacy `rbtv2-` name from a
    run that predates the marker, or — D15 — membership in a copied skill
    folder whose `SKILL.md` carries the marker. A verbatim copy keeps its files
    byte-identical to the source, so the FOLDER is what is owned, and one
    stripped marker releases all of it."""
    if (Path(rel).name.startswith(LEGACY_PREFIX)
            or Path(rel).parent.name.startswith(LEGACY_PREFIX)):
        return True
    if _marked(target / rel):
        return True
    parts = Path(rel).parts
    return any(_marked(target.joinpath(*parts[:i], SKILL_FILE))
               for i in range(len(parts) - 1, 0, -1))


def _content_for(rel: str, method: str, part: str, desc: str,
                 comp_dir: Path, entry_rel: str, installation: Path | None) -> str:
    return _mark(_body_for(rel, method, part, desc, comp_dir / entry_rel,
                           installation))


def _body_for(rel: str, method: str, part: str, desc: str, source: Path,
              installation: Path | None) -> str:
    if method == "rule":
        if rel.endswith("/" + SKILL_FILE):
            # Codex: the rule as a skill. A rule's links are written from the
            # repository root, so no source-folder base applies.
            return _copy(_head(part, rule_skill_description(part), named=True),
                         source, installation, base=None)
        # A copy — CMP-12's fallback row is a mirror, not a pointer. It differs
        # from the source in its link targets, which open from where the copy
        # sits, and in the ownership marker `_content_for` stamps on (D12).
        return absolute_links(source.read_text(encoding="utf-8"), installation)
    if method == "skill":
        return _copy(_head(part, desc, named=True), source, installation,
                     base=source.parent)
    if method == "command":
        # codex prompt files are plain markdown — no frontmatter.
        head = ("" if rel.startswith(".codex/prompts/")
                else _head(part, desc, named=False))
        return _copy(head, source, installation, base=source.parent)
    raise Refuse("internal", f"no content rule for method {method!r}")


def _claude_mcp_entry(spec: dict) -> dict:
    """An rbtv MCP server as a `.mcp.json` entry. `env` maps each variable the
    server reads to the NAME of the environment variable holding its value;
    Claude Code expands `${NAME}` when it starts the server."""
    if spec.get("url"):
        return {"type": "http", "url": str(spec["url"])}
    entry: dict = {"command": str(spec.get("command", ""))}
    if spec.get("args"):
        entry["args"] = [str(a) for a in spec["args"]]
    if spec.get("env"):
        entry["env"] = {k: "${" + v + "}" for k, v in spec["env"].items()}
    return entry


def _codex_mcp_toml_block(servers: dict) -> str:
    """The `[mcp_servers.*]` tables for `.codex/config.toml`, from the rbtv
    server shape. json.dumps of a str/list is valid TOML for both, so the
    stdlib's missing TOML writer is not needed. Codex forwards an environment
    variable to the server by its own name (`env_vars`), so a server whose
    variable holds a value under another name cannot be written for Codex."""
    lines: list[str] = []
    for name in sorted(servers):
        spec = servers[name]
        lines.append(f"[mcp_servers.{name}]")
        if spec.get("url"):
            lines.append(f"url = {json.dumps(str(spec['url']))}")
        else:
            lines.append(f"command = {json.dumps(str(spec.get('command', '')))}")
            if spec.get("args"):
                lines.append("args = " + json.dumps([str(a) for a in spec["args"]]))
            env = spec.get("env") or {}
            renamed = sorted(k for k, v in env.items() if k != v)
            if renamed:
                raise Refuse(
                    "mcp-env-unsupported",
                    f"MCP server {name!r}: Codex forwards an environment "
                    "variable under its own name, so "
                    + ", ".join(renamed)
                    + " cannot be mapped to a differently named variable")
            if env:
                lines.append("env_vars = " + json.dumps(sorted(env)))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _opencode_mcp_entry(spec: dict) -> dict:
    if spec.get("url"):
        return {"type": "remote", "url": str(spec["url"]), "enabled": True}
    entry: dict = {
        "type": "local",
        "command": [str(spec.get("command", ""))]
        + [str(a) for a in (spec.get("args") or [])],
        "enabled": True,
    }
    env = spec.get("env") or {}
    if env:
        entry["environment"] = {k: "{env:" + v + "}" for k, v in env.items()}
    return entry
