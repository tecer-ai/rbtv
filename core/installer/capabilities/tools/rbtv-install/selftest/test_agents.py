"""The portable two-file agent record and its shared-operation lifecycle."""
from __future__ import annotations

import json
from unittest.mock import patch

from discovery import Refuse, scan_all
from lib.agents import (add_agent, configure_agent, list_agents, remove_agent,
                        update_agent)
from lib.state import read_state
from lib.target import resolve_target

from .fixture import _component, _unit_md, _w


def _agent(home, *, name="scout", units=None, packs=None):
    home.mkdir(parents=True, exist_ok=True)
    _w(home / "agent.md", f"---\nname: {name}\n---\n\nScout.\n")
    _w(home / "agent.json", json.dumps({"name": name, "description": "Scout.",
        "harness": "claude", "model": "m1", "effort": "high",
        "units": units or [], "packs": packs or []}) + "\n")


def installed_agents(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    root = tmp / "agent-source"
    comp = _component(root, "moda", "comp")
    _unit_md(comp / "rules/kiss.md", "kiss", "Kiss", "body\n")
    catalog, _ = scan_all(tmp / "agent-mirror", root)
    ws = tmp / "agent-workspace"; ws.mkdir()
    home = ws / ".rbtv/agents/scout"
    _agent(home, units=["kiss"])
    known = {"claude": {"m1": ["low", "high"]},
             "codex": {"c1": ["low", "medium", "high"]}}
    with patch("lib.agents.cast_catalog", return_value=known):
        before = (home / "agent.json").read_bytes()
        planned = add_agent(ws, "scout", [], set(), catalog, True)
        check("A-add — dry run writes no agent file", (home / "agent.json").read_bytes() == before and planned["dry_run"], str(planned))
        add_agent(ws, "scout", [], set(), catalog, False)
    state = read_state(home)
    check("A-add — agent.json is the sole record and normalizes units", state["units"] == ["moda/comp#kiss"] and not (home / "launch.json").exists() and not (home / ".rbtv/config/install.json").exists(), str(state))
    check("A-add — generated files, settings and ignore file are present", (home / ".claude/rules/kiss.md").is_file() and (home / "settings.json").is_file() and (home / ".gitignore").is_file(), "")
    update_agent(ws, "scout", "all", catalog, False)
    check("A-update — shared update keeps the authored record", (home / "agent.json").is_file() and (home / ".claude/rules/kiss.md").is_file(), "")
    with patch("lib.agents.cast_catalog", return_value=known):
        files_before = {path.relative_to(home) for path in home.rglob("*") if path.is_file()}
        configured = configure_agent(ws, "scout", None, None, "2", None, catalog, False)
        files_after = {path.relative_to(home) for path in home.rglob("*") if path.is_file()}
        check("A-configure — numeric effort changes only agent.json when harness stays",
              configured["launch"]["effort"] == "high" and files_before == files_after,
              str(configured))
        switched = configure_agent(ws, "scout", "codex", "c1", "3", None, catalog, False)
    state = read_state(home)
    check("A-configure — harness flip replaces generated harness files",
          state["harness"] == "codex" and state["model"] == "c1"
          and state["effort"] == "high" and not (home / ".claude/rules/kiss.md").exists()
          and not (home / "CLAUDE.md").exists() and (home / "AGENTS.md").is_file()
          and switched["harness_changed"], str(switched))
    before_bad = (home / "agent.json").read_bytes()
    with patch("lib.agents.cast_catalog", return_value=known):
        try:
            configure_agent(ws, "scout", None, "nosuchmodel", None, None, catalog, False)
            got = None
        except Refuse as exc:
            got = exc.code
    check("A-configure — unknown model refuses before writing",
          got == "launch-invalid" and (home / "agent.json").read_bytes() == before_bad, str(got))
    try:
        configure_agent(ws, "scout", None, None, None, None, catalog, False)
        got = None
    except Refuse as exc:
        got = exc.code
    check("A-configure — no option is usage", got == "usage", str(got))
    _agent(ws / ".rbtv/agents/second", name="second")
    listed = list_agents(ws, None)
    listed_folder = list_agents(ws, ws / ".rbtv")
    check("A-list — reads two agents below the default folder and a supplied folder",
          [row["name"] for row in listed["agents"]] == ["scout", "second"]
          and [row["name"] for row in listed_folder["agents"]] == ["scout", "second"], str(listed))
    empty = ws / "empty"; empty.mkdir()
    check("A-list — no agent is successful", not list_agents(ws, empty)["agents"], "")
    _w(empty / "broken" / "agent.json", "{not json\n")
    unreadable = list_agents(ws, empty)["agents"]
    check("A-list — an unreadable record is reported without stopping the list",
          len(unreadable) == 1 and "unreadable" in unreadable[0], str(unreadable))
    bare = tmp / "agent-list-empty"; bare.mkdir()
    check("A-list — a missing default agent folder is successful",
          not list_agents(bare, None)["agents"], "")
    selected, source = resolve_target(None, ws, {"RBTV_AGENT_HOME": str(home)})
    retired_name = "IGNITE" + "_AGENT_HOME"
    legacy, legacy_source = resolve_target(None, ws, {retired_name: str(home)})
    check("A-agent-home — RBTV_AGENT_HOME selects an agent and the retired name does not",
          selected == home and source == "RBTV_AGENT_HOME" and legacy == ws
          and legacy_source != retired_name, f"{selected} / {legacy}")
    remove_agent(ws, "scout", ["kiss"], set(), False, False, catalog, False)
    check("A-remove — removes generated files but preserves the two authored files", (home / "agent.md").is_file() and (home / "agent.json").is_file() and not (home / ".agents/behavior-rules/kiss.md").exists(), "")
    for mutate, code in ((lambda: _agent(ws / ".rbtv/agents/bad", name="wrong"), "agent-name-mismatch"),):
        try:
            mutate(); add_agent(ws, "bad", [], set(), catalog, True)
            got = None
        except Refuse as exc:
            got = exc.code
        check("A-refusal — names must agree", got == code, str(got))
    try:
        remove_agent(ws, "scout", [], set(), True, False, catalog, True)
        got = None
    except Refuse as exc:
        got = exc.code
    check("A-refusal — --all requires --yes", got == "confirmation-required", str(got))
