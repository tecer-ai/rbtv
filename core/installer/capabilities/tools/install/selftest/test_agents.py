"""`rbtv install agent add|update|remove`: an agent file becomes an installed agent."""
from __future__ import annotations

import json
from unittest.mock import patch

from discovery import Refuse, scan_all

from lib.agents import add_agent, launch_values, remove_agent, update_agent
from lib.state import read_state

from .fixture import _component, _unit_md, _w

CAST = {"claude": {"m1": ["low", "high"], "plain": []},
        "codex": {"m2": ["low", "medium", "high"]}}


def _agent_file(path, skills=(), rules=(), folders=("notes",)):
    body = "---\nname: sara\ndescription: A test agent.\n"
    for key, values in (("skills", skills), ("rules", rules),
                        ("folders", folders)):
        if values:
            body += f"{key}: [{', '.join(values)}]\n"
    _w(path, body + "---\n\n## Role\n\nYou are Sara.\n")
    return path


def installed_agents(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp

    print("\nA — an agent file becomes an installed agent")
    root = tmp / "agents-src"
    a = _component(root, "moda", "comp")
    _unit_md(a / "skills/alpha.md", "alpha", "Alpha skill", "alpha\n")
    _unit_md(a / "skills/shared.md", "shared", "Shared in A", "a\n")
    _unit_md(a / "rules/law.md", "law", "A rule", "law\n")
    b = _component(root, "modb", "comp")
    _unit_md(b / "skills/shared.md", "shared", "Shared in B", "b\n")
    cat, _ = scan_all(tmp / "no-mirror-a", root)
    ws = tmp / "ws-agents"
    ws.mkdir()
    home = ws / ".rbtv/agents/sara"
    src = _agent_file(tmp / "sara.md", skills=["alpha"], rules=["law"])

    with patch("lib.agents.cast_catalog", return_value=CAST):
        before = sorted(p.name for p in ws.rglob("*"))
        dry = add_agent(ws, src, "claude", "m1", "3", cat, True)
        check("A-add — a dry run writes nothing",
              sorted(p.name for p in ws.rglob("*")) == before
              and dry["units"] == ["moda/comp#alpha", "moda/comp#law"]
              and dry["launch"] == {"harness": "claude", "model": "m1",
                                    "effort": "high"}, str(dry))
        add_agent(ws, src, "claude", "m1", "3", cat, False)
        files = {p.relative_to(home).as_posix()
                 for p in home.rglob("*") if p.is_file()}
        check("A-add — the folder holds the agent file, launch values, settings, "
              "ignore file, units and instructions",
              {"agent.md", "launch.json", "settings.json", ".gitignore",
               "CLAUDE.md", ".claude/skills/alpha/SKILL.md",
               ".claude/rules/law.md", ".rbtv/config/install.json"} <= files
              and (home / "agent.md").read_bytes() == src.read_bytes()
              and json.loads((home / "launch.json").read_text(encoding="utf-8"))
              == {"harness": "claude", "model": "m1", "effort": "high"}
              and "state.sqlite*" in (home / ".gitignore").read_text(encoding="utf-8"),
              str(sorted(files)))
        section = (home / "CLAUDE.md").read_text(encoding="utf-8")
        check("A-add — its folder instructions point to agent.md and list the "
              "key folders",
              "<!-- rbtv:start agent -->" in section
              and "`agent.md`" in section and "- `notes`" in section, section)
        check("A-add — the agent folder keeps its own install record",
              set(read_state(home)["components"]["moda/comp"]["units"])
              == {"alpha", "law"})
        try:
            add_agent(ws, src, "claude", "m1", "3", cat, False)
            again = None
        except Refuse as exc:
            again = exc.code
        check("A-add — a second add refuses and points to update",
              again == "agent-exists", str(again))

        _agent_file(tmp / "sara2.md", skills=["alpha"], rules=[])
        (home / "agent.md").write_bytes((tmp / "sara2.md").read_bytes())
        (home / "launch.json").write_text(json.dumps(
            {"harness": "claude", "model": "m1", "effort": "low"}),
            encoding="utf-8")
        update_agent(ws, "sara", cat, False)
        check("A-update — a unit the agent file dropped goes; launch values stay",
              not (home / ".claude/rules/law.md").exists()
              and (home / ".claude/skills/alpha/SKILL.md").is_file()
              and json.loads((home / "launch.json").read_text(encoding="utf-8"))
              ["effort"] == "low", str(sorted(p.name for p in home.rglob("*"))))

        (home / "notes.md").write_text("the agent's own\n", encoding="utf-8")
        gone = remove_agent(ws, "sara", cat, False)
        check("A-remove — the installer's files go; the agent's own stay",
              sorted(p.name for p in home.iterdir())
              == ["agent.md", "notes.md", "settings.json"]
              and gone["kept"] == ["agent.md", "notes.md", "settings.json"],
              str(gone["kept"]))
        try:
            update_agent(ws, "nobody", cat, False)
            unknown = None
        except Refuse as exc:
            unknown = exc.code
        check("A-remove — an unknown agent refuses by name",
              unknown == "agent-unknown", str(unknown))

        for names, code in ((["shared"], "unit-ambiguous"),
                            (["nothing"], "unit-unknown"),
                            (["modb/comp/shared"], None)):
            _agent_file(tmp / "pick.md", skills=names)
            try:
                add_agent(tmp / "ws-pick", tmp / "pick.md", "claude", "m1",
                          "high", cat, True)
                got = None
            except Refuse as exc:
                got = exc.code
            check(f"A-units — {names[0]!r}: a name must resolve to exactly one "
                  "unit", got == code, str(got))

    check("A-launch — an effort number becomes the model's word; a model with "
          "no dial is inert; a bad value refuses",
          launch_values("claude", "m1", "1", CAST)["effort"] == "low"
          and launch_values("claude", "m1", "5", CAST)["effort"] == "high"
          and launch_values("claude", "plain", "high", CAST)["effort"] == "inert"
          and launch_values("codex", "m2", "medium", CAST)["effort"] == "medium",
          "")
    for args in (("kimi", "m1", "low"), ("claude", "nope", "low"),
                 ("claude", "m1", "turbo")):
        try:
            launch_values(*args, CAST)
            code = None
        except Refuse as exc:
            code = exc.code
        check(f"A-launch — {args} refuses", code == "launch-invalid", str(code))
    ctx.keep(locals())
