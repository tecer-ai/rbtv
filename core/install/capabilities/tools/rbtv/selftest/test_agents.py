"""The portable two-file agent record and its shared-operation lifecycle."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

from discovery import Refuse, scan_all
from lib.agents import (IGNORE_TEXT, add_agent, configure_agent, list_agents,
                        remove_agent, update_agent)
from lib.doctor import do_doctor
from lib.planning import plan_files
from lib.state import read_state
from lib.target import resolve_target

from .fixture import _component, _unit_md, _w


def _agent(home, *, name="scout", units=None, packs=None):
    home.mkdir(parents=True, exist_ok=True)
    _w(home / "agent.md", f"---\nname: {name}\n---\n\nScout.\n")
    _w(home / "agent.json", json.dumps({"name": name, "description": "Scout.",
        "harness": "claude", "model": "m1", "effort": "high",
        "units": units or [], "packs": packs or []}) + "\n")


def _git_status(repo: Path) -> set[str]:
    done = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                          cwd=repo, check=True, capture_output=True, text=True,
                          encoding="utf-8")
    return {line[3:] for line in done.stdout.splitlines()}


def _ignored_agent(home: Path, harness: str) -> None:
    model, effort = {
        "claude": ("m1", "high"),
        "codex": ("c1", "high"),
        "opencode": ("glm-5.3", "high"),
    }[harness]
    name = home.name
    _w(home / "agent.md", f"---\nname: {name}\n---\n\nAgent.\n")
    _w(home / "agent.json", json.dumps({
        "name": name, "description": "Agent.", "harness": harness,
        "model": model, "effort": effort, "units": [], "packs": []}) + "\n")
    _w(home / "agent.pre-split.md", "Author file.\n")
    _w(home / "notes/own.md", "Author note.\n")


def agent_ignore_file(ctx) -> None:
    check, skip, tmp, catalog = ctx.check, ctx.skip, ctx.tmp, ctx.frame()[0]
    if shutil.which("git") is None:
        skip("A-ignore — git status preserves authored files", "git is unavailable")
        return
    known = {"claude": {"m1": ["low", "high"]},
             "codex": {"c1": ["low", "medium", "high"]},
             "opencode": {"glm-5.3": ["low", "high"]}}
    every_destination = [
        "fixskill", "fixrule", "fixcmd", "fixagent", "fixhook", "fixmcp",
    ]

    def add(repo: Path, agent: Path, harness: str) -> tuple[set[str], set[str]]:
        _ignored_agent(agent, harness)
        state = json.loads((agent / "agent.json").read_text(encoding="utf-8"))
        state["units"] = every_destination
        _w(agent / "agent.json", json.dumps(state) + "\n")
        with patch("lib.agents.cast_catalog", return_value=known):
            add_agent(repo, str(agent), [], set(), catalog, False)
        _w(agent / "state.sqlite", "machine data\n")
        _w(agent / "turns/t1/x", "machine data\n")
        _w(agent / "conversations/c1/session.json", "{}\n")
        prefix = agent.relative_to(repo).as_posix() + "/"
        status = {path for path in _git_status(repo) if path.startswith(prefix)}
        state = read_state(agent)
        files, _owners, claims, _report = plan_files(state["components"], catalog,
                                                     agent)
        planned = set(files) | {claim["path"] for claim in claims}
        ignored = {
            rel for rel in planned
            if subprocess.run(["git", "check-ignore", "--quiet", "--no-index",
                               "--", str(agent / rel)],
                              cwd=repo, check=False).returncode == 0
        }
        return status, planned - ignored

    expected_a = {
        ".rbtv/agents/a1/agent.md", ".rbtv/agents/a1/agent.json",
        ".rbtv/agents/a1/settings.json", ".rbtv/agents/a1/agent.pre-split.md",
        ".rbtv/agents/a1/notes/own.md",
    }
    for harness in ("codex", "claude", "opencode"):
        repo = tmp / f"agent-ignore-{harness}"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        agent = repo / ".rbtv/agents/a1"
        status_a, uncovered = add(repo, agent, harness)
        check(f"A-ignore — {harness} agent folder preserves authored files",
              status_a == expected_a, repr(sorted(status_a)))
        check(f"A-ignore — {harness} ignores every destination in its plan",
              not uncovered, repr(sorted(uncovered)))
        _w(repo / ".gitignore", ".rbtv/agents/*/*\n!.rbtv/agents/*/agent.md\n"
                              "!.rbtv/agents/*/agent.json\n")
        prefix = agent.relative_to(repo).as_posix() + "/"
        status_b = {path for path in _git_status(repo) if path.startswith(prefix)}
        check(f"A-ignore — {harness} agent folder keeps root ignore rules",
              status_b == {".rbtv/agents/a1/agent.md", ".rbtv/agents/a1/agent.json"},
              repr(sorted(status_b)))

    repo = tmp / "agent-ignore-outside"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    outside = repo / "plans/launch/agents/launch-drafter"
    status_c, uncovered_c = add(repo, outside, "codex")
    expected_c = {path.replace(".rbtv/agents/a1", "plans/launch/agents/launch-drafter")
                  for path in expected_a}
    check("A-ignore — an agent outside .rbtv preserves authored files",
          status_c == expected_c, repr(sorted(status_c)))
    check("A-ignore — an outside agent ignores every destination in its plan",
          not uncovered_c, repr(sorted(uncovered_c)))


def installed_agents(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    root = tmp / "agent-source"
    comp = _component(root, "moda", "comp")
    _unit_md(comp / "rules/kiss.md", "kiss", "Kiss", "body\n")
    _unit_md(comp / "rules/other.md", "other", "Other", "body\n")
    _w(comp / "agents/research/agent.md", "---\nname: research\n---\n\nResearch.\n")
    _w(comp / "agents/research/agent.json", json.dumps({
        "name": "research", "description": "Research.", "harness": "claude",
        "model": "m1", "effort": "high", "units": ["kiss"], "packs": []}) + "\n")
    catalog, _ = scan_all(tmp / "agent-mirror", root)
    ws = tmp / "agent-installation"; ws.mkdir()
    home = ws / ".rbtv/agents/scout"
    _agent(home, units=["kiss"])
    known = {"claude": {"m1": ["low", "high"]},
             "codex": {"c1": ["low", "medium", "high"]}}
    with patch("lib.agents.cast_catalog", return_value=known):
        before = (home / "agent.json").read_bytes()
        planned = add_agent(ws, "scout", [], set(), catalog, True)
        check("A-add — dry run writes no agent file", (home / "agent.json").read_bytes() == before and planned["dry_run"], str(planned))
        add_agent(ws, "scout", [], set(), catalog, False)
        placed = add_agent(ws, "research", [], set(), catalog, False)
    state = read_state(home)
    check("A-add — agent.json is the sole record and normalizes units", state["units"] == ["moda/comp#kiss"] and not (home / "launch.json").exists() and not (home / ".rbtv/config/install.json").exists(), str(state))
    check("A-add — generated files, settings and ignore file are present", (home / ".claude/rules/kiss.md").is_file() and (home / "settings.json").is_file() and (home / ".gitignore").is_file(), "")
    research = ws / ".rbtv/agents/research"
    check("A-add — a shipped agent is placed then applied",
          placed["placed"]["id"] == "moda/comp#research"
          and (research / "agent.md").is_file() and (research / "agent.json").is_file()
          and (research / ".claude/rules/kiss.md").is_file(), str(placed))
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
    with patch("lib.agents.cast_catalog", return_value=known):
        updated = update_agent(ws, "scout", "all", catalog, False)
        added = add_agent(ws, "scout", ["other"], set(), catalog, False)
        removed = remove_agent(ws, "scout", ["other"], set(), False, False,
                               catalog, False)
        lifecycle_state = read_state(home)
        lifecycle_health = do_doctor(home, "fixture", catalog, [], root,
                                     home / ".rbtv/mirror")["ok"]
        restored = configure_agent(ws, "scout", "claude", "m1", "2", None,
                                   catalog, False)
        restored_update = update_agent(ws, "scout", "all", catalog, False)
    state = read_state(home)
    check("A-configure — a harness flip keeps ownership through update, add, remove and doctor",
          updated["ok"] and added["ok"] and removed["ok"]
          and lifecycle_health and lifecycle_state["shared_claims"]
          and lifecycle_state.get("shared_files"), str(lifecycle_state))
    check("A-configure — changing back removes Codex files and remains updateable",
          restored["ok"] and restored_update["ok"]
          and state["harness"] == "claude" and not (home / "AGENTS.md").exists(),
          str(restored))
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
          [row["name"] for row in listed["agents"]] == ["research", "scout", "second"]
          and [row["name"] for row in listed_folder["agents"]] == ["research", "scout", "second"], str(listed))
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
    check("A-remove — removes generated files but preserves authored files",
          (home / "agent.md").is_file() and (home / "agent.json").is_file()
          and (home / ".gitignore").read_text(encoding="utf-8") == IGNORE_TEXT
          and not (home / ".agents/behavior-rules/kiss.md").exists(), "")
    _w(home / ".gitignore", "# author edited\n")
    remove_agent(ws, "scout", [], set(), True, True, catalog, False)
    check("A-remove — leaves an edited agent ignore file",
          (home / ".gitignore").read_text(encoding="utf-8") == "# author edited\n", "")
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
    check("A-refusal — --all requires --yes", got == "confirm-required", str(got))

    def refused(call) -> tuple[str | None, str | None]:
        try:
            call()
        except Refuse as exc:
            return exc.code, getattr(exc, "next", None)
        return None, None

    no_record = ws / ".rbtv/agents/norecord"
    _w(no_record / "agent.md", "---\nname: norecord\n---\n\nNo record.\n")
    check("A-refusal — a folder without agent.json is agent-json-missing",
          refused(lambda: add_agent(ws, "norecord", [], set(), catalog, True))
          == ("agent-json-missing", "rbtv agent add -h"), "")
    broken = ws / ".rbtv/agents/brokenjson"
    _w(broken / "agent.md", "---\nname: brokenjson\n---\n\nBroken.\n")
    _w(broken / "agent.json", '{"name": "brokenjson",\n}\n')
    code, nxt = refused(lambda: add_agent(ws, "brokenjson", [], set(), catalog, True))
    check("A-refusal — invalid agent.json is agent-json-invalid with its line",
          code == "agent-json-invalid" and nxt == "rbtv agent add -h", str((code, nxt)))
    check("A-refusal — an unknown pack is pack-unknown",
          refused(lambda: add_agent(ws, "scout", [], {"nosuchpack"}, catalog, True))
          == ("pack-unknown", "rbtv list --type pack"), "")
    check("A-refusal — listing a missing folder is not-a-folder",
          refused(lambda: list_agents(ws, ws / "missing"))[0] == "not-a-folder", "")
