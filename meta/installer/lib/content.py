"""Rendering the body of every file the installer writes, and recognising the
ones it owns.
"""
from __future__ import annotations

import json
from pathlib import Path

from discovery import Refuse, SKILL_FILE

from .constants import (
    FORCED_READ_HARNESSES,
    GENERATED_MARKERS,
    GUIDANCE_FILE,
    LEGACY_PREFIX,
    LOADER_NOTE,
    MANAGED_BANNER,
    MANAGED_MARK,
)
from .claims import _fence


def _yq(text: str) -> str:
    """A YAML-safe quoted scalar — json quoting is valid YAML (the colon-space
    in a `description:` is the failure class this closes)."""
    return json.dumps(str(text), ensure_ascii=False)


def _loader(part: str, desc: str, entry: str, what: str, named: bool) -> str:
    name_line = f"name: {part}\n" if named else ""
    return (f"---\n{name_line}description: {_yq(desc)}\n---\n\n"
            + LOADER_NOTE + "\n\n"
            f"Read `{entry}` NOW and follow it as this {what}'s full "
            "instructions.\n")


def _mark(text: str) -> str:
    """Stamp *text* with the ownership marker (D12), AFTER any YAML frontmatter
    — a marker above a loader's `---` block would stop that block parsing."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 3)
        if end != -1:
            cut = end + len("\n---\n")
            return text[:cut] + "\n" + MANAGED_BANNER + text[cut:]
    return MANAGED_BANNER + text


def _marked(path: Path) -> bool:
    """True when this one file's head carries a machine-readable owner mark —
    ours, or a generated-mirror banner (D13 adoption). Unreadable proves
    nothing."""
    try:
        head = path.read_text(encoding="utf-8")[:2000]
    except (OSError, UnicodeDecodeError):
        return False
    return MANAGED_MARK in head or any(m in head for m in GENERATED_MARKERS)


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


def _content_for(rel: str, method: str, part: str, desc: str, entry: str,
                 comp_dir: Path, entry_rel: str) -> str:
    return _mark(_body_for(rel, method, part, desc, entry, comp_dir, entry_rel))


def _body_for(rel: str, method: str, part: str, desc: str, entry: str,
              comp_dir: Path, entry_rel: str) -> str:
    if method == "rule":
        # Verbatim copy — CMP-12's fallback row is a mirror, not a pointer. The
        # ONE addition is the ownership marker `_content_for` stamps on (D12).
        return (comp_dir / entry_rel).read_text(encoding="utf-8")
    if method == "skill":
        return _loader(part, desc, entry, "skill", named=True)
    if method == "sub-agent":
        return _loader(part, desc, entry, "sub-agent", named=True)
    if method == "command":
        if rel.startswith(".codex/prompts/"):
            # codex prompt files are plain markdown — no frontmatter.
            return (LOADER_NOTE + "\n\n"
                    f"Read `{entry}` NOW and follow it as this command's full "
                    "instructions.\n")
        return _loader(part, desc, entry, "command", named=False)
    raise Refuse("internal", f"no content rule for method {method!r}")


def _codex_mcp_toml_block(servers: dict) -> str:
    """The `[mcp_servers.*]` tables for `.codex/config.toml`, from the neutral
    `mcpServers` shape. json.dumps of a str/list is valid TOML for both, so the
    stdlib's missing TOML writer is not needed."""
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
            if env:
                lines.append("")
                lines.append(f"[mcp_servers.{name}.env]")
                for k in sorted(env):
                    lines.append(f"{k} = {json.dumps(str(env[k]))}")
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
        entry["environment"] = {k: str(v) for k, v in env.items()}
    return entry


def _exposure_block(name: str, harnesses: list[str],
                    agents_parts: list[tuple[str, str, str]],
                    rule_parts: list[tuple[str, str]]) -> str:
    """The rbtv exposure preamble ONE guidance file carries (D8), fenced.

    `name` is the guidance FILENAME this block is for. The Step-0 forced read is
    emitted only for the harnesses that auto-inject no rule folder
    (`FORCED_READ_HARNESSES` — CMP-12 § Fallback mechanics) AND read that name;
    claude and opencode never get it. It enumerates the paths those harnesses'
    rule files were ACTUALLY written to — a rule realized only under
    `.claude/rules/` (its component installed claude-only) is never named to
    codex, whose copy does not exist. The `agents.md` rows are named in every
    guidance file, because that method's realization IS the guidance file.

    Empty string when there is nothing to say — no block, no fence, no file
    churn.
    """
    readers = [h for h in harnesses
               if h in FORCED_READ_HARNESSES and GUIDANCE_FILE.get(h) == name]
    forced: list[tuple[str, str]] = []
    for _pid, desc, by_harness in rule_parts:
        for rel in sorted({by_harness[h] for h in readers if h in by_harness}):
            forced.append((rel, desc))
    if not agents_parts and not forced:
        return ""
    out = ["# rbtv exposure — installed components", ""]
    if forced:
        out += [
            "## Step 0 — MANDATORY, before anything else",
            "",
            "Read EACH of these behavior-rule files, one at a time, IN THIS "
            "ORDER. They are always-on rules; this harness auto-injects no rule "
            "folder, so this enumeration is the read. Do not bulk-read them — "
            "a bulk read truncates the last entries.",
            "",
        ]
        for i, (rel, desc) in enumerate(forced, 1):
            suffix = f" — {desc}" if desc else ""
            out.append(f"{i}. `{rel}`{suffix}")
        out.append("")
    if agents_parts:
        out += ["## Guidance parts", ""]
        for pid, desc, entry in agents_parts:
            suffix = f" — {desc}" if desc else ""
            out.append(f"- **{pid}**: read `{entry}`{suffix}")
    start, end = _fence("<!--")
    return f"{start}\n" + "\n".join(out).rstrip() + f"\n{end}\n"
