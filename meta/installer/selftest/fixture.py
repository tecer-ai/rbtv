"""The throwaway tree every check runs against, and the one probe that needs to
build its own."""
from __future__ import annotations

import json
from pathlib import Path

from discovery import EXPOSURE_NAME, HUB_DIR, Refuse, SKILLS_DIR, SKILL_FILE

from lib.constants import HARNESSES
from lib.operations import do_install


def _fixture(root: Path) -> None:
    """A throwaway tree covering every method, incl. a `path` row that must be
    skipped, a component with NO manifest, and an unknown-method component."""
    good = root / "fixmod" / "goodcomp"
    (good / "tool").mkdir(parents=True)
    for name, body in (
        ("skill-entry.md", "# the skill\n"),
        ("cmd-entry.md", "# the command\n"),
        ("rule-entry.md", "# THE RULE\n\nAlways do the thing.\n"),
        ("agent-entry.md", "# the sub-agent\n"),
        ("guide.md", "# guidance part\n"),
        ("tool/thing.py", "print('inventory only')\n"),
    ):
        (good / name).write_text(body, encoding="utf-8")
    (good / "hooks.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "true"}]}]}}),
        encoding="utf-8")
    (good / "mcp.json").write_text(json.dumps({"mcpServers": {
        "fix": {"type": "http", "url": "https://example.invalid/mcp"}}}),
        encoding="utf-8")
    (good / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "fixskill,capability,skill,exhibit,skill-entry.md,A fixture skill: with a colon,\n"
        "fixcmd,workflow,command,,cmd-entry.md,,\n"
        "fixrule,reference,rule,,rule-entry.md,the fixture rule,\n"
        "fixagent,prompt,sub-agent,,agent-entry.md,,\n"
        "fixhook,capability,hook,,hooks.json,,\n"
        "fixmcp,plugin/MCP,config,,mcp.json,,\n"
        "fixguide,prompt,agents.md,exhibit,guide.md,,\n"
        "fixtool,tool,path,,tool/thing.py,,\n"
        "fixpool,prompt,pool,,guide.md,a pool member — shopped, never minted,\n",
        encoding="utf-8")

    codexc = root / "fixmod" / "codexcomp"
    codexc.mkdir(parents=True)
    (codexc / "rule-entry.md").write_text("# CODEX RULE\n", encoding="utf-8")
    (codexc / "guide.md").write_text("# codex guidance part\n", encoding="utf-8")
    (codexc / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "codexrule,reference,rule,,rule-entry.md,the codex-side rule,\n"
        "codexguide,prompt,agents.md,,guide.md,,\n", encoding="utf-8")

    bare = root / "fixmod" / "barecomp"
    bare.mkdir(parents=True)
    (bare / "component.md").write_text("# barecomp — no manifest\n",
                                       encoding="utf-8")

    res = root / "fixmod" / "reservedcomp"
    res.mkdir(parents=True)
    (res / "skill-entry.md").write_text("# the skill\n", encoding="utf-8")
    (res / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "rbtv-legacy,prompt,skill,,skill-entry.md,,\n", encoding="utf-8")

    # D2 — depth-1 module-root manifest (invisible) and a depth-2 manifest
    # with no component.md (a component). Depth-3 is added below.
    old = root / "oldmod"
    (old / "oldcomp").mkdir(parents=True)
    old_rows = ("part-id,part-kind,method,rbtv-cli,entry-point,description,"
                "write-roots\nold,prompt,skill,,entry.md,,\n")
    (old / EXPOSURE_NAME).write_text(old_rows, encoding="utf-8")
    (old / "entry.md").write_text("# old\n", encoding="utf-8")
    (old / "oldcomp" / EXPOSURE_NAME).write_text(old_rows, encoding="utf-8")
    (old / "oldcomp" / "entry.md").write_text("# old\n", encoding="utf-8")

    # D15 — a whole skill folder: SKILL.md + a nested reference + a binary
    # asset + a directory the copier must skip.
    vend = root / SKILLS_DIR / "vendored"
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

    hub = root / HUB_DIR
    skill = hub / "skills" / "hubskill"
    skill.mkdir(parents=True)
    (skill / SKILL_FILE).write_text(
        "---\nname: hubskill\ndescription: A hub skill\n---\n\n# Hub skill\n",
        encoding="utf-8")
    (hub / "command").mkdir()
    (hub / "command" / "hubcmd.md").write_text("# hub command\n", encoding="utf-8")
    (hub / "rules").mkdir()
    (hub / "rules" / "hubrule.md").write_text("# HUB RULE\n\nDo the hub thing.\n",
                                              encoding="utf-8")
    (hub / "hook").mkdir()
    (hub / "hook" / "hubhook.json").write_text(json.dumps({"hooks": {"SessionStart": [
        {"matcher": "", "hooks": [{"type": "command", "command": "true"}]}]}}),
        encoding="utf-8")
    (hub / "sub-agent").mkdir()
    (hub / "sub-agent" / "hubagent.md").write_text("# hub sub-agent\n",
                                                   encoding="utf-8")
    (hub / "agents.md").mkdir()
    (hub / "agents.md" / "hubguide.md").write_text("# hub guidance fragment\n",
                                                   encoding="utf-8")
    (hub / "config").mkdir()
    (hub / "config" / "hubmcp.json").write_text(json.dumps({"mcpServers": {
        "hubfix": {"type": "http", "url": "https://hub.example.invalid/mcp"}}}),
        encoding="utf-8")
    (hub / "path").mkdir()
    (hub / "path" / "hubbin.py").write_text("#!/usr/bin/env python3\nprint(1)\n",
                                            encoding="utf-8")
    (hub / "path" / "hubbindir").mkdir()
    (hub / "path" / "hubbindir" / "child.py").write_text("print(2)\n",
                                                         encoding="utf-8")
    (hub / "pool").mkdir()
    (hub / "pool" / "hubpool.md").write_text("# not a pool\n", encoding="utf-8")

    # Depth 3 — not a component (D2).
    deep = root / "deepmod" / "deepcomp" / "nested"
    deep.mkdir(parents=True)
    (deep / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "deep,prompt,skill,,entry.md,,\n", encoding="utf-8")

    bad = root / "badmod" / "badcomp"
    bad.mkdir(parents=True)
    (bad / "x.md").write_text("x\n", encoding="utf-8")
    (bad / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "boom,capability,telepathy,,x.md,,\n", encoding="utf-8")

    dup = root / "fixmod" / "dupcomp"
    dup.mkdir(parents=True)
    (dup / "a.md").write_text("a\n", encoding="utf-8")
    (dup / "b.md").write_text("b\n", encoding="utf-8")
    (dup / EXPOSURE_NAME).write_text(
        "part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots\n"
        "same,capability,skill,,a.md,,\n"
        "same,reference,rule,,b.md,,\n", encoding="utf-8")


def _reserved_id_refuses(tmp: Path, catalog: dict[str, dict]) -> bool:
    """A manifest declaring a `rbtv-*` part id refuses, and writes nothing —
    the old installer's sweep would delete that file behind our back (D12)."""
    ws = tmp / "ws-reserved-id"
    ws.mkdir()
    try:
        do_install(ws, catalog, ["fixmod/reservedcomp"], list(HARNESSES),
                   dry_run=False)
        return False
    except Refuse as exc:
        return (exc.code == "part-id-reserved"
                and not any(ws.rglob("*.md")))
