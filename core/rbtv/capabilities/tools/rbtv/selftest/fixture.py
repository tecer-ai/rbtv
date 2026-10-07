"""The throwaway tree every check runs against, and the one probe that needs to
build its own."""
from __future__ import annotations

import json
from pathlib import Path

from discovery import HUB_DIR, Refuse, SKILLS_DIR, SKILL_FILE

from lib.constants import HARNESSES
from lib.operations import do_install


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _file_md(path: Path, name: str, description: str, body: str = "",
             extra: str = "") -> None:
    _w(path, f"---\nname: {name}\ndescription: {json.dumps(description)}\n"
             f"{extra}---\n\n{body}")


def _module(root: Path, module: str) -> Path:
    _w(root / module / f"{module}.json",
       json.dumps({"description": f"The {module} module"}))
    return root / module


def _component(root: Path, module: str, comp: str) -> Path:
    _module(root, module)
    _w(root / module / comp / f"{comp}.json",
       json.dumps({"description": f"The {comp} component", "dependencies": []}))
    return root / module / comp


def _fixture(root: Path, mirror: Path) -> None:
    """A throwaway tree covering every method: a tool, a folder-instructions
    file, a whole-folder skill, an invalid file, a component with no record."""
    good = _component(root, "fixmod", "goodcomp")
    _file_md(good / "skills/fixskill.md", "fixskill",
             "A fixture skill: with a colon", "# the skill\n")
    _file_md(good / "commands/fixcmd.md", "fixcmd", "The fixture command",
             "# the command\n")
    _file_md(good / "rules/fixrule.md", "fixrule", "the fixture rule",
             "# THE RULE\n\nAlways do the thing.\n")
    _w(good / "agents/fixagent/prompt.md", "---\nname: fixagent\n---\n\n## Role\n\nthe agent\n")
    _w(good / "agents/fixagent/agent.json", json.dumps({
        "name": "fixagent", "description": "The fixture agent"}) + "\n")
    _w(good / "agents/research/prompt.md", "---\nname: research\n---\n\nResearch.\n")
    _w(good / "agents/research/agent.json", json.dumps({
        "name": "research", "description": "The fixture research agent",
        "files": ["fixskill"], "packs": []}) + "\n")
    _w(good / "hooks/fixhook.json", json.dumps({
        "name": "fixhook", "description": "The fixture hook",
        "event": "PreToolUse", "matcher": "Bash", "command": "true"}))
    _w(good / "mcp-servers/fixmcp.json", json.dumps({
        "name": "fixmcp", "description": "The fixture MCP server",
        "url": "https://example.invalid/mcp"}))
    _w(good / "folder-instructions/fixguide.md",
       "---\ntarget: .\n---\n\n# guidance for the root\n")
    tool = good / "capabilities/tools/fixtool"
    _w(tool / "fixtool.json", json.dumps({
        "name": "fixtool", "description": "The fixture tool",
        "entry": "thing.py"}))
    _w(tool / "thing.py", "#!/usr/bin/env python3\nprint('inventory only')\n")
    (tool / "thing.py").chmod(0o755)
    _w(good / "packs/starter.json", json.dumps({
        "description": "The fixture starter pack",
        "files": ["fixmod/goodcomp#fixskill", "fixmod/goodcomp#fixrule"],
    }))
    _w(good / "packs/second.json", json.dumps({
        "description": "The fixture overlapping pack",
        "files": ["fixmod/goodcomp#fixrule"],
    }))

    codexc = _component(root, "fixmod", "codexcomp")
    _file_md(codexc / "rules/codexrule.md", "codexrule", "the codex-side rule",
             "# CODEX RULE\n")
    _w(codexc / "folder-instructions/codexguide.md",
       "---\ntarget: .\n---\n\n# codex guidance\n")

    # A folder with no record and no file folders is not a component: invisible.
    _w(root / "fixmod" / "barecomp" / "notes.md", "# barecomp — no record\n")

    res = _component(root, "fixmod", "reservedcomp")
    _file_md(res / "skills/rbtv-legacy.md", "rbtv-legacy", "A reserved name",
             "# the skill\n")

    # A component deeper than depth 2 is not a component.
    old = _component(root, "oldmod", "oldcomp")
    _file_md(old / "skills/old.md", "old", "An old skill", "# old\n")
    nested = root / "deepmod" / "deepcomp" / "nested"
    _component(root, "deepmod", "deepcomp")
    _w(nested / "nested.json", json.dumps({
        "description": "too deep", "dependencies": []}))
    _file_md(nested / "skills/deep.md", "deep", "A deep skill", "# deep\n")

    # D15 — a whole skill folder: SKILL.md + a nested reference + a binary
    # asset + a directory the copier must skip.
    # Whole-folder skills live only in an installation's mirror (owner ruling J0).
    vend = mirror / SKILLS_DIR / "vendored"
    (vend / "references").mkdir(parents=True)
    (vend / "__pycache__").mkdir()
    (vend / SKILL_FILE).write_text(
        "---\nname: vendored\ndescription: A vendored skill\n---\n\n"
        "# Vendored\n\nRead references/deep.md.\n", encoding="utf-8")
    (vend / "LICENSE.txt").write_text("MIT\n", encoding="utf-8")
    (vend / "references/deep.md").write_text("# deep reference\n",
                                             encoding="utf-8")
    (vend / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n binary")
    (vend / "__pycache__/junk.pyc").write_bytes(b"\x00junk")

    # A file that fails its schema: its file name and its `name` disagree.
    bad = _component(root, "badmod", "badcomp")
    _file_md(bad / "skills/boom.md", "not-boom", "Names itself wrongly", "x\n")

    # Two files of one component with one name.
    dup = _component(root, "fixmod", "dupcomp")
    _file_md(dup / "skills/same.md", "same", "a skill", "a\n")
    _file_md(dup / "rules/same.md", "same", "a rule", "b\n")


# The model and effort the fixture agent `fixagent` is installed with as a
# harness-native sub-agent, for every harness, and the file id that keys them.
FIXAGENT = "fixmod/goodcomp#fixagent"
FIXAGENT_ON = {FIXAGENT: {
    harness: {"model": f"{harness}-m", "model_id": f"id/{harness}-m", "effort": "high"}
    for harness in HARNESSES}}


def _reserved_id_refuses(tmp: Path, catalog: dict[str, dict]) -> bool:
    """A file with a `rbtv-*` name refuses, and writes nothing — the old
    installer's sweep would delete that file behind our back (D12)."""
    ws = tmp / "ws-reserved-id"
    ws.mkdir()
    try:
        do_install(ws, catalog, ["fixmod/reservedcomp"], list(HARNESSES),
                   dry_run=False)
        return False
    except Refuse as exc:
        return (exc.code == "name-reserved"
                and not any(ws.rglob("*.md")))
