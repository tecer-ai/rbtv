"""The portable two-file agent record and its shared-operation lifecycle."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from discovery import Refuse, scan_all
from lib.agents import (IGNORE_TEXT, add_agent, agent_home, cast_agent_list, cast_catalog,
                        cast_effort_word, cast_model_id, configure_agent, is_path, launch_values, remove_agent,
                        update_agent)
from lib.constants import MATRIX, REPO_ROOT
from lib.doctor import do_doctor
from lib.planning import plan_files
from lib.state import read_state
from lib.target import resolve_target

from .fixture import _component, _file_md, _w


def _agent(home, *, name="scout", files=None, packs=None):
    home.mkdir(parents=True, exist_ok=True)
    _w(home / "prompt.md", f"---\nname: {name}\n---\n\nScout.\n")
    _w(home / "agent.json", json.dumps({"name": name, "description": "Scout.",
        "harness": "claude", "model": "haiku-4-5", "effort": "high",
        "files": files or [], "packs": packs or []}) + "\n")


def _git_status(repo: Path) -> set[str]:
    done = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                          cwd=repo, check=True, capture_output=True, text=True,
                          encoding="utf-8")
    return {line[3:] for line in done.stdout.splitlines()}


def _ignored_agent(home: Path, harness: str) -> None:
    model, effort = {
        "claude": ("haiku-4-5", "high"),
        "codex": ("c1", "high"),
        "opencode": ("glm-5.3", "high"),
    }[harness]
    name = home.name
    _w(home / "prompt.md", f"---\nname: {name}\n---\n\nAgent.\n")
    _w(home / "agent.json", json.dumps({
        "name": name, "description": "Agent.", "harness": harness,
        "model": model, "effort": effort, "files": [], "packs": []}) + "\n")
    _w(home / "prompt.pre-split.md", "Author file.\n")
    _w(home / "notes/own.md", "Author note.\n")


def _refused(call) -> tuple[str | None, str | None]:
    """The code and the next command of the refusal a call raises."""
    try:
        call()
    except Refuse as exc:
        return exc.code, getattr(exc, "next", None)
    return None, None


def agent_ignore_file(ctx) -> None:
    check, skip, tmp, catalog = ctx.check, ctx.skip, ctx.tmp, ctx.frame()[0]
    if shutil.which("git") is None:
        skip("A-ignore — git status preserves authored files", "git is unavailable")
        return
    known = {"claude": {"haiku-4-5": {"rungs": ["low", "high"], "selected": True}},
             "codex": {"c1": {"rungs": ["low", "medium", "high"], "selected": True}},
             "opencode": {"glm-5.3": {"rungs": ["low", "high"], "selected": True}}}
    every_destination = ["fixskill", "fixrule", "fixcmd", "fixhook", "fixmcp"]

    check = ctx.check

    def add(repo: Path, agent: Path, harness: str) -> tuple[set[str], set[str]]:
        _ignored_agent(agent, harness)
        state = json.loads((agent / "agent.json").read_text(encoding="utf-8"))
        state["files"] = every_destination
        _w(agent / "agent.json", json.dumps(state) + "\n")
        # The fixture agent is added by name as a harness-native sub-agent, so the
        # plan holds that harness's sub-agent file too.
        with patch("lib.agents.cast_catalog", return_value=known), \
                patch("lib.agents.cast_model_id", return_value="native-id"):
            add_agent(repo, str(agent), ["fixagent"], set(), catalog, False,
                      on=(f"{harness}:{state['model']}:{state['effort']}",))
        _w(agent / "state.sqlite", "machine data\n")
        _w(agent / "turns/t1/x", "machine data\n")
        _w(agent / "conversations/c1/session.json", "{}\n")
        prefix = agent.relative_to(repo).as_posix() + "/"
        status = {path for path in _git_status(repo) if path.startswith(prefix)}
        state = read_state(agent)
        files, _owners, claims, _report = plan_files(state["components"], catalog,
                                                     agent)
        planned = set(files) | {claim["path"] for claim in claims}
        sub_agent_file = MATRIX["agent"][harness].format(name="fixagent")
        check(f"SA-agent-target — {harness} agent gets the sub-agent file of its own harness",
              sub_agent_file in files and "native-id" in files[sub_agent_file],
              repr(sorted(files)))
        ignored = {
            rel for rel in planned
            if subprocess.run(["git", "check-ignore", "--quiet", "--no-index",
                               "--", str(agent / rel)],
                              cwd=repo, check=False).returncode == 0
        }
        return status, planned - ignored

    expected_a = {
        ".rbtv/agents/a1/prompt.md", ".rbtv/agents/a1/agent.json",
        ".rbtv/agents/a1/settings.json", ".rbtv/agents/a1/prompt.pre-split.md",
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
        _w(repo / ".gitignore", ".rbtv/agents/*/*\n!.rbtv/agents/*/prompt.md\n"
                              "!.rbtv/agents/*/agent.json\n")
        prefix = agent.relative_to(repo).as_posix() + "/"
        status_b = {path for path in _git_status(repo) if path.startswith(prefix)}
        check(f"A-ignore — {harness} agent folder keeps root ignore rules",
              status_b == {".rbtv/agents/a1/prompt.md", ".rbtv/agents/a1/agent.json"},
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
    check, skip, tmp = ctx.check, ctx.skip, ctx.tmp
    root = tmp / "agent-source"
    comp = _component(root, "moda", "comp")
    _file_md(comp / "rules/kiss.md", "kiss", "Kiss", "body\n")
    _file_md(comp / "rules/other.md", "other", "Other", "body\n")
    _w(comp / "agents/research/prompt.md", "---\nname: research\n---\n\nResearch.\n")
    _w(comp / "agents/research/agent.json", json.dumps({
        "name": "research", "description": "Research.", "files": ["kiss"], "packs": []}) + "\n")
    catalog, _ = scan_all(tmp / "agent-mirror", root)
    ws = tmp / "agent-installation"; ws.mkdir()
    home = ws / ".rbtv/agents/scout"
    _agent(home, files=["kiss"])
    known = {"claude": {"haiku-4-5": {"rungs": ["low", "high"], "selected": True}},
             "codex": {"c1": {"rungs": ["low", "medium", "high"], "selected": True}}}
    # The word cast gives for an effort number on these made-up models.
    words = {("claude", "haiku-4-5", "2"): "high", ("codex", "c1", "3"): "high"}

    def cast_words():
        return patch("lib.agents.cast_effort_word", side_effect=lambda *asked: words.get(asked[:3]))

    with patch("lib.agents.cast_catalog", return_value=known), cast_words():
        before = (home / "agent.json").read_bytes()
        planned = add_agent(ws, "scout", [], set(), catalog, True)
        check("A-add — dry run writes no agent file", (home / "agent.json").read_bytes() == before and planned["dry_run"], str(planned))
        add_agent(ws, "scout", [], set(), catalog, False)
        launch = {"harness": "claude", "model": "haiku-4-5", "effort": "2"}
        research = ws / ".rbtv/agents/research"
        check("A-add-flags — a shipped agent without the three flags is refused and not placed",
              _refused(lambda: add_agent(ws, "research", [], set(), catalog, False))
              == ("launch-required", "cast models list")
              and _refused(lambda: add_agent(ws, "research", [], set(), catalog, False,
                                             {"harness": "claude", "model": None,
                                              "effort": None}))[0] == "launch-required"
              and not research.exists(), "")
        check("A-add-flags — a model cast does not list is refused before placing",
              _refused(lambda: add_agent(ws, "research", [], set(), catalog, False,
                                         {**launch, "model": "nosuch"}))[0] == "launch-invalid"
              and not research.exists(), "")
        preview = add_agent(ws, "research", [], set(), catalog, True, launch)
        check("A-add-flags — a preview of placing a shipped agent writes nothing",
              preview["dry_run"] and preview["placed"]["id"] == "moda/comp#research"
              and preview["launch"]["effort"] == "high" and not research.exists(),
              str(preview))
        placed = add_agent(ws, "research", [], set(), catalog, False, launch)
        placed_record = json.loads((research / "agent.json").read_text(encoding="utf-8"))
        check("A-add-flags — the three flags are checked as configure checks them and "
              "written into the placed agent.json",
              (placed_record["harness"], placed_record["model"], placed_record["effort"])
              == ("claude", "haiku-4-5", "high") and placed["launch"]["model"] == "haiku-4-5",
              str(placed_record))
        check("A-add-flags — a flag for an agent that has the values is refused and "
              "names rbtv agent configure",
              _refused(lambda: add_agent(ws, "research", [], set(), catalog, False,
                                         {"harness": None, "model": "haiku-4-5", "effort": None}))
              == ("launch-already-set", "rbtv agent configure research --model haiku-4-5")
              and _refused(lambda: add_agent(ws, "scout", [], set(), catalog, False, launch))[0]
              == "launch-already-set", "")
        bare = ws / ".rbtv/agents/bare"
        _w(bare / "prompt.md", "---\nname: bare\n---\n\nBare.\n")
        _w(bare / "agent.json", json.dumps({"name": "bare", "description": "Bare."}) + "\n")
        check("A-add-flags — a hand-written agent without the values needs the flags too",
              _refused(lambda: add_agent(ws, "bare", [], set(), catalog, False))[0]
              == "launch-required", "")
        add_agent(ws, "bare", [], set(), catalog, False, launch)
        check("A-add-flags — and the flags are written into its agent.json",
              read_state(bare)["model"] == "haiku-4-5" and read_state(bare)["effort"] == "high",
              str(read_state(bare)))
        shutil.rmtree(bare)
    state = read_state(home)
    check("A-add — agent.json is the sole record and normalizes files", state["files"] == ["moda/comp#kiss"] and not (home / "launch.json").exists() and not (home / ".rbtv/config/install.json").exists(), str(state))
    check("A-add — harness files, settings and ignore file are present", (home / ".claude/rules/kiss.md").is_file() and (home / "settings.json").is_file() and (home / ".gitignore").is_file(), "")
    check("A-add — a shipped agent is placed then applied",
          placed["placed"]["id"] == "moda/comp#research"
          and (research / "prompt.md").is_file() and (research / "agent.json").is_file()
          and (research / ".claude/rules/kiss.md").is_file(), str(placed))
    update_agent(ws, "scout", "all", catalog, False)
    check("A-update — shared update keeps the authored record", (home / "agent.json").is_file() and (home / ".claude/rules/kiss.md").is_file(), "")
    with patch("lib.agents.cast_catalog", return_value=known), cast_words():
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
    with patch("lib.agents.cast_catalog", return_value=known), cast_words():
        updated = update_agent(ws, "scout", "all", catalog, False)
        added = add_agent(ws, "scout", ["other"], set(), catalog, False)
        removed = remove_agent(ws, "scout", ["other"], set(), False, False,
                               catalog, False)
        lifecycle_state = read_state(home)
        lifecycle_health = do_doctor(home, "fixture", catalog, [], root,
                                     home / ".rbtv/mirror")["ok"]
        restored = configure_agent(ws, "scout", "claude", "haiku-4-5", "2", None,
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
    # The list of agents is cast's own. The checks run the cast of this source tree, and the rbtv
    # that cast asks, on PATH through launchers the suite writes; node is what this machine must supply.
    with patch("lib.agents.shutil.which", return_value=None):
        check("A-list — without cast on PATH the list is refused, not rebuilt here",
              _refused(lambda: cast_agent_list(ws, None, False, False, 100)) == ("cast-missing", "rbtv doctor"), "")
        check("A-effort — without cast on PATH an effort number is refused, not worked out here",
              _refused(lambda: cast_effort_word("claude", "haiku-4-5", "2", ws)) == ("cast-missing", "rbtv doctor"), "")
    with patch("lib.agents.shutil.which", return_value="cast"), \
            patch("lib.agents.subprocess.run",
                  return_value=subprocess.CompletedProcess([], 0, "not JSON", "")):
        check("A-effort — an answer from cast that is not its launch value is refused",
              _refused(lambda: cast_effort_word("claude", "haiku-4-5", "2", ws))[0] == "cast-unreadable", "")
    with patch("lib.agents.cast_effort_word", return_value=None):
        check("A-effort — a number cast refuses is refused, and no word is made up for it",
              _refused(lambda: launch_values("claude", "haiku-4-5", "2", known, ws))
              == ("launch-invalid", "cast models list"), "")
    check("A-model — a model cast does not support is refused with the list of those it does",
          _refused(lambda: launch_values("claude", "nosuch", "high", known, ws))
          == ("launch-invalid", "cast models list --supported"), "")
    unselected = {"claude": {"haiku-4-5": {"rungs": ["low", "high"], "selected": False}}}
    check("A-model — a model the installation has not selected is refused with the command that selects it",
          _refused(lambda: launch_values("claude", "haiku-4-5", "high", unselected, ws))
          == ("launch-invalid", "cast models add claude haiku-4-5"), "")
    with patch("lib.agents.shutil.which", return_value="cast"), \
            patch("lib.agents.subprocess.run", return_value=subprocess.CompletedProcess(
                [], 2, '{"error":"catalog-unreadable","message":"refused: cannot read the model catalog"}\n', "")):
        try:
            cast_catalog(ws)
            said = "no refusal"
        except Refuse as exc:
            said = f"{exc.code}: {exc.message}"
        check("A-model — a refusal from cast models list is passed on, not read as an empty list",
              said == "cast-refused: `cast models list` refused: refused: cannot read the model catalog", said)
    node = shutil.which("node")
    if node is None:
        for name in ("A-list — the list is the one cast prints",
                     "A-effort — an effort number becomes the word cast gives for it",
                     "A-rules — rbtv and cast agree on what a path is and where an agent's folder is"):
            skip(name, "node is not on this machine, and cast runs on node")
    else:
        # What makes a value a path, and where an agent's folder is, are cast's rules, which rbtv
        # states in one line each. cast's own code answers here, so the two cannot differ unnoticed.
        values = ["scout", "a-b", "plans/x", "plans\\x", "C:\\agents\\x", ".", "..", "./x", "x/", "a.b", "~", ""]
        asked = subprocess.run(
            [node, "-e",
             "const [lib, root, values] = process.argv.slice(1); const cast = require(lib);"
             "console.log(JSON.stringify({ paths: JSON.parse(values).map((value) => cast.isPath(value)),"
             " home: cast.agentHomeIn(root, 'scout') }));",
             str(REPO_ROOT / "core/cast/capabilities/tools/cast/lib/agent.js"), str(ws), json.dumps(values)],
            capture_output=True, text=True, encoding="utf-8")
        cast_says = json.loads(asked.stdout) if asked.returncode == 0 else {"paths": asked.stderr, "home": ""}
        ours = [is_path(value) for value in values]
        check("A-rules — rbtv and cast agree on what makes a value a path: a slash, a backslash, or a dot name",
              ours == cast_says["paths"] and ours == [False, False, True, True, True, True, True, True, True, False, False, False],
              f"rbtv {ours}, cast {cast_says['paths']}")
        check("A-rules — rbtv and cast agree on where an agent's folder is",
              cast_says["home"] != "" and agent_home(ws, "scout") == Path(cast_says["home"]),
              f"rbtv {agent_home(ws, 'scout')}, cast {cast_says['home']}")
        cast_js = REPO_ROOT / "core/cast/capabilities/tools/cast/cast.js"
        cast_bin = tmp / "cast-bin"; cast_bin.mkdir()
        _w(cast_bin / "cast", f'#!/bin/sh\nexec "{node}" "{cast_js}" "$@"\n')
        (cast_bin / "cast").chmod(0o755)
        _w(cast_bin / "cast.cmd", f'@"{node}" "{cast_js}" %*\r\n')
        rbtv_py = REPO_ROOT / "core/rbtv/capabilities/tools/rbtv/install.py"
        _w(cast_bin / "rbtv", f'#!/bin/sh\nexec "{sys.executable}" "{rbtv_py}" "$@"\n')
        (cast_bin / "rbtv").chmod(0o755)
        _w(cast_bin / "rbtv.cmd", f'@"{sys.executable}" "{rbtv_py}" %*\r\n')
        with patch.dict(os.environ, {"PATH": f"{cast_bin}{os.pathsep}{os.environ['PATH']}"}):
            listed = cast_agent_list(ws, None, False, False, 100).splitlines()
            check("A-list — the list is the one cast prints: the installation's agents, by name",
                  listed[:2] == ["rbtv agents: 3", f"Folder: {ws / '.rbtv' / 'agents'}"]
                  and [line.split()[0] for line in listed[3:7]] == ["Name", "research", "scout", "second"], str(listed))
            check("A-list — the columns are cast's: Ignite and description, no packs, files or folder",
                  listed[3].split() == ["Name", "Harness", "Model", "Effort", "Ignite", "Description"], listed[3])
            whole = cast_agent_list(ws, None, False, True, 200)
            check("A-list — --full reaches cast: every agent is a labeled block with its whole description",
                  "Name: second\nHarness: " in whole and "…" not in whole, whole)
            narrow = cast_agent_list(ws, None, False, False, 40)
            check("A-list — the width this command sees reaches cast: a narrow terminal gets labeled blocks",
                  "Name: second\nHarness: " in narrow, narrow)
            one = cast_agent_list(ws, "second", False, False, 100)
            check("A-list — an agent named is shown in full, with its folder",
                  one.startswith("Name: second\n") and f"Folder: {ws / '.rbtv' / 'agents' / 'second'}\n" in one, one)
            by_path = json.loads(cast_agent_list(ws, str(ws / ".rbtv/agents/second"), True, False, 100))
            check("A-list — a path names the agent, and --json is cast's value",
                  by_path["name"] == "second" and by_path["ignite"] is False, str(by_path))
            check("A-list — an agent that is not there is refused as for the other agent verbs",
                  _refused(lambda: cast_agent_list(ws, "nosuch", False, False, 100))[0] == "agent-unknown", "")
            bare = tmp / "agent-list-empty"; bare.mkdir()
            check("A-list — an installation with no agent folder is successful",
                  cast_agent_list(bare, None, False, False, 100).startswith("rbtv agents: 0\n"), "")
            plan = tmp / "plan-agents"
            _agent(plan / "drafter", name="drafter")
            (tmp / "elsewhere").mkdir()
            outside = cast_agent_list(ws, None, True, False, 100, str(plan))
            check("A-list — --target reaches cast: the agents of a folder outside .rbtv/agents/",
                  json.loads(outside)["folder"] == str(plan)
                  and [row["name"] for row in json.loads(outside)["agents"]] == ["drafter"], outside)
            check("A-list — with --target, AGENT is a name among that folder's agents",
                  json.loads(cast_agent_list(ws, "drafter", True, False, 100, str(plan)))["home"] == str(plan / "drafter"), "")
            check("A-list — a --target that holds no agent is cast's refusal",
                  _refused(lambda: cast_agent_list(ws, None, False, False, 100, str(tmp / "elsewhere")))
                  == ("cast-refused", "rbtv agent list -h"), "")
            try:
                cast_agent_list(ws, None, False, False, 100, str(tmp / "elsewhere"))
                said = ""
            except Refuse as exc:
                said = exc.message
            check("A-list — that refusal carries cast's first line only",
                  said.endswith("names no rbtv agents") and "Nothing was listed" not in said
                  and "cast list -h" not in said, said)
            # What cast supports and what an effort number means are cast's own. The expected
            # words are read from the list cast prints (for each word, the number that selects
            # it), on the first model that has effort words. cast answers from a folder outside
            # any installation, where every supported model is selected.
            away = tmp / "no-installation"; away.mkdir()
            listed_models = json.loads(subprocess.run(
                [shutil.which("cast", path=str(cast_bin)), "models", "list", "--supported", "--json"], cwd=away,
                capture_output=True, text=True, encoding="utf-8").stdout)["models"]
            table = cast_catalog(away)
            row = next(row for row in listed_models if row["effort_numbers"] and row["mode"] == "cli")
            harness, model, numbers = row["harness"], row["model"], row["effort_numbers"]
            check("A-model — the models rbtv checks against are the ones cast models list --supported prints",
                  {(h, m) for h in table for m in table[h]} == {(r["harness"], r["model"]) for r in listed_models}
                  and table[harness][model] == {"rungs": row["rungs"], "selected": True}, str(table.get(harness)))
            got = {word: cast_effort_word(harness, model, str(n), away) for word, n in numbers.items()}
            check("A-effort — an effort number becomes the word cast gives for it",
                  got == {word: word for word in numbers}, f"{harness} {model}: {got}")
            check("A-effort — the word reaches the agent's values, and a number cast refuses is refused",
                  launch_values(harness, model, "1", table, away)["effort"] == min(numbers, key=numbers.get)
                  and cast_effort_word(harness, model, "0", away) is None
                  and _refused(lambda: launch_values(harness, model, "0", table, away))[0] == "launch-invalid",
                  f"{harness} {model}")
            # The installation of the folder cast is asked from decides what is selected: here
            # one whose model catalog holds a single model.
            pruned = tmp / "pruned"
            _w(pruned / ".rbtv/config/install.json", "{}\n")
            _w(pruned / ".rbtv/config/cast/models.csv", "mode,harness,model\ncli,claude,sonnet-5-5\n")
            _agent(pruned / ".rbtv/agents/scout")
            chosen = cast_catalog(pruned / ".rbtv/agents/scout")
            check("A-model — cast is asked from the agent's folder, so its installation's selection answers",
                  chosen["claude"]["sonnet-5-5"]["selected"] and not chosen["claude"]["haiku-4-5"]["selected"]
                  and table["claude"]["haiku-4-5"]["selected"], str(chosen["claude"]))
            check("A-model — agent configure refuses a model the agent's installation has not selected",
                  _refused(lambda: configure_agent(pruned, "scout", None, None, "low", None, catalog, True))
                  == ("launch-invalid", "cast models add claude haiku-4-5"), "")
            check("A-effort — a number is asked of cast from the agent's folder: an unselected model gives no word",
                  cast_effort_word("claude", "opus-5-5", "1", pruned / ".rbtv/agents/scout") is None
                  and cast_effort_word("claude", "opus-5-5", "1", away) == "low"
                  and cast_effort_word("claude", "sonnet-5-5", "1", pruned / ".rbtv/agents/scout") == "low", "")
            check("A-model — the harness's own id is asked of cast from the same folder",
                  cast_model_id("claude", "sonnet-5-5", pruned / ".rbtv/agents/scout") == "claude-sonnet-5-5"
                  and _refused(lambda: cast_model_id("claude", "opus-5-5", pruned / ".rbtv/agents/scout"))[0]
                  == "cast-unreadable", "")
    selected, source = resolve_target(None, ws, {"RBTV_AGENT_HOME": str(home)})
    retired_name = "IGNITE" + "_AGENT_HOME"
    legacy, legacy_source = resolve_target(None, ws, {retired_name: str(home)})
    check("A-agent-home — RBTV_AGENT_HOME selects an agent and the retired name does not",
          selected == home and source == "RBTV_AGENT_HOME" and legacy == ws
          and legacy_source != retired_name, f"{selected} / {legacy}")
    remove_agent(ws, "scout", ["kiss"], set(), False, False, catalog, False)
    check("A-remove — removes harness files but preserves authored files",
          (home / "prompt.md").is_file() and (home / "agent.json").is_file()
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

    refused = _refused

    no_record = ws / ".rbtv/agents/norecord"
    _w(no_record / "prompt.md", "---\nname: norecord\n---\n\nNo record.\n")
    check("A-refusal — a folder without agent.json is agent-json-missing",
          refused(lambda: add_agent(ws, "norecord", [], set(), catalog, True))
          == ("agent-json-missing", "rbtv agent add -h"), "")
    broken = ws / ".rbtv/agents/brokenjson"
    _w(broken / "prompt.md", "---\nname: brokenjson\n---\n\nBroken.\n")
    _w(broken / "agent.json", '{"name": "brokenjson",\n}\n')
    code, nxt = refused(lambda: add_agent(ws, "brokenjson", [], set(), catalog, True))
    check("A-refusal — invalid agent.json is agent-json-invalid with its line",
          code == "agent-json-invalid" and nxt == "rbtv agent add -h", str((code, nxt)))
    old_named = ws / ".rbtv/agents/oldname"
    _agent(old_named, name="oldname")
    (old_named / "prompt.md").rename(old_named / "agent.md")
    try:
        add_agent(ws, "oldname", [], set(), catalog, True)
        got = None
    except Refuse as exc:
        got = (exc.code, exc.message)
    check("A-refusal — a folder still holding agent.md is prompt-missing with the rename command",
          got == ("prompt-missing", f"{old_named / 'prompt.md'} is missing. This folder still has "
                  "agent.md, the old name of the prompt file. If another machine already renamed "
                  "it, pull first; otherwise rename it with: git mv agent.md prompt.md (inside "
                  f"{old_named}), and change any .gitignore line that names agent.md."), str(got))
    check("A-refusal — a run inside that folder targets the folder, never the installation above",
          resolve_target(None, old_named, {})[0] == old_named.resolve(), "")
    cli = subprocess.run([sys.executable, str(REPO_ROOT / "core/rbtv/capabilities/tools/rbtv/install.py"),
                          "status", "--json"], cwd=old_named, capture_output=True, text=True,
                         encoding="utf-8", env={k: v for k, v in os.environ.items() if k != "RBTV_AGENT_HOME"})
    check("A-refusal — rbtv status inside that folder refuses with prompt-missing",
          cli.returncode != 0 and '"prompt-missing"' in cli.stdout + cli.stderr,
          (cli.stdout + cli.stderr)[:300])
    shutil.rmtree(old_named)
    check("A-refusal — an unknown pack is pack-unknown",
          refused(lambda: add_agent(ws, "scout", [], {"nosuchpack"}, catalog, True))
          == ("pack-unknown", "rbtv list --type pack"), "")
