"""An agent a component ships, added with `rbtv add`: the harness-native sub-agent
files, the `--on` values, the record that keeps them, and the one source format."""
from __future__ import annotations

import contextlib
import io
import json
from unittest.mock import patch

from discovery import Refuse, scan_all, file_rows
from lib import commands, constants, schema
from lib.constants import SCHEMA, STATE_REL
from lib.help_pages import PAGES
from lib.recovery import shell_quote
from lib.state import read_state

from .fixture import FIXAGENT, _component, _file_md, _w

KNOWN = {"claude": {"m1": ["low", "medium", "high"], "nodial": []},
         "codex": {"c1": ["low", "medium", "high"]},
         "opencode": {"o1": ["high", "max"]}}
# The word cast gives for an effort number on these made-up models.
WORDS = {("claude", "m1", "1"): "low", ("claude", "m1", "2"): "medium",
         ("claude", "m1", "3"): "high", ("opencode", "o1", "1"): "high"}


def sub_agents(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    catalog = ctx.frame()[0]
    ws = tmp / "sa-installation"
    ws.mkdir()
    claude = ws / ".claude/agents/fixagent.md"
    codex = ws / ".codex/agents/fixagent.toml"
    opencode = ws / ".opencode/agents/fixagent.md"

    def run(*argv, cat=None, columns="100"):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(commands, "scan_all", return_value=(cat or catalog, [])), \
                patch("lib.agents.cast_catalog", return_value=KNOWN), \
                patch("lib.agents.cast_effort_word", side_effect=lambda *asked: WORDS.get(asked)), \
                patch("lib.agents.cast_model_id",
                      side_effect=lambda harness, model, _folder: f"id/{model}"), \
                patch.dict("os.environ", {"COLUMNS": columns}), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = commands.main([*argv, "--target", str(ws)])
        return code, out.getvalue(), err.getvalue()

    def flat(text: str) -> str:
        """Text with its line wrapping removed: the wrap depends on the path length."""
        return " ".join(text.split())

    def agent_record() -> dict:
        return read_state(ws)["components"]["fixmod/goodcomp"]["units"]["fixagent"]

    print("\nSA — an agent a component ships, added as a harness-native sub-agent")
    code, _out, err = run("add", "fixagent", "--harness", "claude,codex", "--guidance", "none")
    check("SA-on-required — naming an agent without --on is refused, naming --on and rbtv agent add",
          code == 1 and err.startswith(
              "rbtv — refused\n\nREFUSED [on-required] fixagent: an agent a component ships. "
              "Added with `rbtv add` it is written as a\n  harness-native sub-agent, which needs a "
              "model and an effort for each harness: give --on\n  HARNESS:MODEL:EFFORT, once "
              "per harness. To place it as an rbtv agent instead, run\n  `rbtv agent add "
              "fixagent --harness HARNESS --model MODEL --effort EFFORT`. Nothing was changed.\n"
              "next: cast list\n") and not (ws / STATE_REL).exists(), err)

    code, preview, _err = run("add", "fixagent", "--on", "claude:m1:3", "--dry-run",
                              "--harness", "claude,codex", "--guidance", "none")
    check("SA-preview — a preview names the harness and writes nothing",
          code == 0 and "rbtv — add preview" in preview
          and "  claude:         m1, effort high\n  codex:          not written\n" in preview
          and "Files:            would write 1," in preview and not claude.exists()
          and not (ws / STATE_REL).exists(), preview)

    code, one, _err = run("add", "fixagent", "--on", "claude:m1:3",
                          "--harness", "claude,codex", "--guidance", "none")
    check("SA-one-harness — the file is written only for the harness given, with its "
          "model and effort",
          code == 0 and claude.is_file() and not codex.exists() and not opencode.exists()
          and 'model: "id/m1"\n' in claude.read_text(encoding="utf-8")
          and 'effort: "high"\n' in claude.read_text(encoding="utf-8"), one)
    check("SA-one-harness-result — the result names the harness written and the one left out",
          "Installed:        fixmod/goodcomp#fixagent\n" in one
          and "Sub-agent:        fixagent (harness-native sub-agent)\n"
              "  claude:         m1, effort high\n"
              "  codex:          not written\n" in one
          and "· fixagent is a harness-native sub-agent for claude, not for codex. rbtv "
              "cannot add it by itself: a model and an effort are needed. Add it with: "
              "rbtv add fixagent --on codex:MODEL:EFFORT --target "
              f"{shell_quote(ws)} " in flat(one), one)
    check("SA-record — the agent's record holds the model, the harness's own model id and "
          "the effort, per harness, and nothing tied to this machine",
          agent_record()["sub_agent"] == {"claude": {"model": "m1", "model_id": "id/m1",
                                             "effort": "high"}}
          and read_state(ws)["schema"] == SCHEMA == 9
          and str(tmp) not in json.dumps(agent_record()["sub_agent"]), str(agent_record()))
    saved = json.loads((ws / STATE_REL).read_text(encoding="utf-8"))
    booked = saved["components"]["fixmod/goodcomp"]["units"]["fixagent"]
    described = schema.load("install-json")
    broken = []
    for change in (lambda entry: entry["claude"].pop("model_id"),
                   lambda entry: entry["claude"].update(effort=3),
                   lambda entry: entry.update(kimi=dict(entry["claude"]))):
        booked["sub_agent"] = {"claude": {"model": "m1", "model_id": "id/m1",
                                          "effort": "high"}}
        valid = not schema.errors(saved, described)
        change(booked["sub_agent"])
        broken.append(valid and bool(schema.errors(saved, described)))
    check("SA-record-schema — the record the program wrote, with its sub_agent entry, "
          "matches the install record schema; an entry missing a key, with a value "
          "that is not text, or under an unknown harness does not",
          "sub_agent" in json.loads((ws / STATE_REL).read_text(encoding="utf-8"))
          ["components"]["fixmod/goodcomp"]["units"]["fixagent"]
          and not schema.errors(json.loads((ws / STATE_REL).read_text(encoding="utf-8")),
                                described)
          and broken == [True, True, True], str(broken))

    code, two, _err = run("add", "fixagent", "--on", "codex:c1:medium", "--on", "claude:m1:1")
    check("SA-second-harness — a second harness is added and a new value replaces the old, "
          "which the result shows",
          code == 0 and codex.is_file()
          and 'model = "id/c1"\n' in codex.read_text(encoding="utf-8")
          and 'model_reasoning_effort = "medium"\n' in codex.read_text(encoding="utf-8")
          and 'effort: "low"\n' in claude.read_text(encoding="utf-8")
          and "  claude:         m1, effort low (was m1, effort high)\n"
              "  codex:          c1, effort medium\n" in two
          and "Installed files:  1 (unchanged)" in two and "not for codex" not in two, two)

    code, out, _err = run("add", "fixagent", "--on", "claude:m1:1", "--json")
    payload = json.loads(out)
    check("SA-json — the structured result carries the values, the harnesses left out "
          "and what was not applied",
          code == 0 and payload["sub_agents"][0]["id"] == FIXAGENT
          and payload["sub_agents"][0]["harnesses"]["claude"]
          == {"model": "m1", "model_id": "id/m1", "effort": "low", "was": None,
              "not_applied": []}
          and payload["sub_agents"][0]["not_written_for"] == []
          and payload["sub_agents"][0]["files_not_applied"] == []
          and run("add", "fixskill", "--json")[1].count('"sub_agents": []') == 1, out)

    code, _out, err = run("add", "fixagent", "--on", "opencode:o1:high")
    check("SA-not-received — a harness the target does not receive is refused, naming "
          "what it receives and configure",
          code == 1 and "[on-harness-not-received] --on names opencode, which this target "
          "does not receive. It\n  receives: claude, codex." in err
          and "next: rbtv configure --harness claude,codex,opencode --target " in err
          and not opencode.exists(), err)
    code, _out, err = run("add", "fixskill", "--on", "claude:m1:high")
    check("SA-on-without-agent — --on with no agent among the names is refused",
          code == 1 and "[on-without-agent] --on gives a model and an effort to an agent a "
          "component ships, and no\n  such agent is among the names." in err
          and "next: rbtv list --type agent --target " in err, err)
    usage = [run("add", "fixagent", "--on", value) for value in
             ("claude:m1", "nosuch:m1:high", "claude::high")]
    code, _out, twice = run("add", "fixagent", "--on", "claude:m1:1", "--on", "claude:m1:2")
    check("SA-on-usage — a value that is not HARNESS:MODEL:EFFORT, or a harness given "
          "twice, is invalid arguments",
          all(code == 2 and "REFUSED [usage] --on " in err and "next: rbtv add -h" in err
              for code, _out, err in usage)
          and "is not HARNESS:MODEL:EFFORT" in usage[0][2]
          and code == 2 and "names claude more than once" in twice, str(usage))
    code, _out, err = run("add", "fixagent", "--on", "claude:nosuch:high")
    check("SA-on-checked — model and effort get the check an rbtv agent's values get",
          code == 1 and "[launch-invalid] claude has no model 'nosuch'" in err
          and run("add", "fixagent", "--on", "claude:m1:max")[0] == 1, err)

    _code, status, _err = run("status")
    _code, status_json, _err = run("status", "--json")
    line = f"Sub-agent {FIXAGENT}: claude (m1, effort low); codex (c1, effort medium)\n"
    check("SA-status — status says for which harnesses and with what",
          "Packs on: none\n" + line in status
          and json.loads(status_json)["installation"]["sub_agents"]
          == {FIXAGENT: agent_record()["sub_agent"]}, status)
    _code, listed, _err = run("list", "--type", "agent")
    _code, listed_json, _err = run("list", "--type", "agent", "--json")
    rows = {row["id"]: row for row in json.loads(listed_json)["files"]}
    check("SA-list — the catalog lists each agent once, type agent, and an installed one "
          "with its harnesses",
          f"{FIXAGENT}  agent  installed " in listed and line in listed
          and "fixmod/goodcomp#research  agent  not installed" in listed
          and rows[FIXAGENT]["sub_agent"] == agent_record()["sub_agent"]
          and rows["fixmod/goodcomp#research"]["sub_agent"] == {}, listed)
    _code, shown, _err = run("show", "fixagent")
    check("SA-show — show names the sub-agent's harnesses, the rbtv agent folder and "
          "the command of each form",
          "  Harness-native sub-agent: claude (m1, effort low); codex (c1, effort medium)\n"
          f"  rbtv agent: no folder at {ws / '.rbtv/agents/fixagent'}\n" in shown
          and "  As a harness-native sub-agent: rbtv add fixagent --on HARNESS:MODEL:EFFORT\n"
              "  As an rbtv agent: rbtv agent add fixagent --harness HARNESS --model MODEL "
              "--effort EFFORT\n" in shown
          and shown.rstrip().endswith("Next: cast list")
          and "  Harness:" not in shown and "  Packs: none\n" in shown, shown)
    code, _out, err = run("list", "--type", "sub-agent")
    check("SA-type-retired — sub-agent is an unknown type, refused as any unknown type is",
          code == 2 and "--type 'sub-agent' is unknown. Did you mean agent?" in err
          and "sub-agent" not in constants.CATALOG_TYPES, err)

    claude.unlink()
    codex.unlink()
    code, _out, _err = run("update", "all")
    check("SA-update — update regenerates the sub-agent files from the record alone",
          code == 0 and 'effort: "low"\n' in claude.read_text(encoding="utf-8")
          and 'model = "id/c1"\n' in codex.read_text(encoding="utf-8"), _err)

    code, grown, _err = run("configure", "--harness", "claude,codex,opencode")
    check("SA-harness-added — a harness added later gets no file; the result names the "
          "agent and the command, and says why rbtv cannot do it",
          code == 0 and not opencode.exists() and "opencode" not in agent_record()["sub_agent"]
          and "· fixagent is a harness-native sub-agent for claude and codex, not for "
              "opencode. rbtv cannot add it by itself: a model and an effort are "
              "needed. Add it with: "
              "rbtv add fixagent --on opencode:MODEL:EFFORT --target "
              f"{shell_quote(ws)} " in flat(grown),
          grown)
    code, _out, _err = run("add", "fixagent", "--on", "opencode:o1:1")
    check("SA-opencode — OpenCode's file names the model and the effort as its variant",
          code == 0 and 'model: "id/o1"\n' in opencode.read_text(encoding="utf-8")
          and 'variant: "high"\n' in opencode.read_text(encoding="utf-8"), _err)
    code, _out, _err = run("configure", "--harness", "claude,codex")
    check("SA-harness-dropped — a dropped harness loses its file and its values",
          code == 0 and not opencode.exists() and sorted(agent_record()["sub_agent"]) == ["claude", "codex"],
          str(agent_record()))

    with patch.dict(constants.SUB_AGENT_SETTINGS["codex"], {"effort": None}):
        code, gap, _err = run("add", "fixagent", "--on", "codex:c1:high")
        toml = codex.read_text(encoding="utf-8")
    check("SA-not-applied — a value the harness's file has no setting for is recorded, "
          "left out of the file, and reported",
          code == 0 and "model_reasoning_effort" not in toml and 'model = "id/c1"' in toml
          and agent_record()["sub_agent"]["codex"]["effort"] == "high"
          and "fixagent for codex: effort high was recorded and not applied (a codex "
              "sub-agent file has no" in gap, gap)
    code, inert, _err = run("add", "fixagent", "--on", "claude:nodial:2")
    check("SA-no-dial — a model with no effort dial records the effort and writes no "
          "effort setting",
          code == 0 and agent_record()["sub_agent"]["claude"]["effort"] == "inert"
          and "effort:" not in claude.read_text(encoding="utf-8")
          and "effort inert was recorded and not applied (nodial has no effort setting)"
          in " ".join(inert.split()), inert)

    code, _out, _err = run("add", "research", "--on", "claude:m1:high")
    _code, own, _err = run("add", "research", "--on", "claude:m1:high")
    check("SA-own-files — the agent's own files and packs are named as not applied",
          code == 0 and "research's own files and packs were not applied: file fixskill. "
          "A harness-native sub-agent sees what its target has; add them with "
          "`rbtv add`." in flat(own), own)
    code, removed, _err = run("remove", "fixagent")
    check("SA-remove — remove deletes the sub-agent for every harness and its values",
          code == 0 and not claude.exists() and not codex.exists()
          and "fixagent" not in read_state(ws)["components"]["fixmod/goodcomp"]["units"]
          and (ws / ".claude/agents/research.md").is_file(), removed)

    pages = {"add": ("--on HARNESS:MODEL:EFFORT",),
             "agent add": ("--harness {claude,codex,opencode}", "--model MODEL",
                           "--effort EFFORT", "--on HARNESS:MODEL:EFFORT"),
             "configure": ("rbtv add NAME --on HARNESS:MODEL:EFFORT",),
             "interactive": ("rbtv add NAME --on HARNESS:MODEL:EFFORT",)}
    check("SA-help — the pages of the changed commands name the new flags, and no page "
          "names the retired type",
          all(word in PAGES[page] for page, words in pages.items() for word in words)
          and not any("\n  sub-agent " in text for text in PAGES.values()),
          str([(page, word) for page, words in pages.items() for word in words
               if word not in PAGES[page]]))

    print("\nSA — one source format")
    src = tmp / "sa-source"
    comp = _component(src, "moda", "comp")
    _file_md(comp / "skills/plain.md", "plain", "Plain", "body\n")
    _w(comp / "agents/named/agent.md", "---\nname: named\n---\n\nNamed.\n")
    _w(comp / "agents/named/agent.json", json.dumps({
        "name": "named", "description": "Named.", "harness": "claude", "model": "m1"}) + "\n")
    bad, _ = scan_all(tmp / "sa-mirror", src)
    try:
        file_rows(bad["moda/comp"])
        refusal = None
    except Refuse as exc:
        refusal = exc
    code, _out, err = run("show", "moda/comp", cat=bad)
    check("SA-source-launch — a shipped agent that names a harness or a model is refused, "
          "naming the fields to remove",
          refusal is not None and refusal.code == "agent-source-launch"
          and refusal.message.endswith("an agent a component ships names no harness, model "
                                       "or effort; they exist only in an installation. "
                                       "Remove: harness, model")
          and code == 1 and "[agent-source-launch]" in err, str(refusal and refusal.message))
    _w(comp / "packs/both.json", json.dumps({"description": "Both",
                                             "files": ["moda/comp#plain"]}))
    try:
        scan_all(tmp / "sa-mirror", src)
        with_pack = "no refusal"
    except Refuse as exc:
        with_pack = exc.code
    check("SA-source-launch-pack — a pack of that component fails for the same reason, "
          "not as an unknown file",
          with_pack == "agent-source-launch", with_pack)
    (comp / "agents/named/agent.json").write_text(
        json.dumps({"name": "named", "description": "Named."}) + "\n", encoding="utf-8")
    _file_md(comp / "sub-agents/old.md", "old", "Old format", "body\n")
    try:
        scan_all(tmp / "sa-mirror", src)
        refusal = None
    except Refuse as exc:
        refusal = exc
    check("SA-source-retired — a file in the old folder is refused, naming agents/<name>/",
          refusal is not None and refusal.code == "agent-source-retired"
          and refusal.message.endswith("an agent is no longer shipped as one file in "
                                       "sub-agents/. Ship it as the folder agents/old/ "
                                       "with agent.md and agent.json"),
          str(refusal and refusal.message))

    print("\nSA — a record written before this schema")
    legacy = tmp / "sa-legacy"
    (legacy / STATE_REL).parent.mkdir(parents=True)
    _w(legacy / ".claude/agents/fixagent.md",
       "---\nname: fixagent\n---\n<!-- rbtv-managed -->\nold loader\n")
    (legacy / STATE_REL).write_text(json.dumps({
        "schema": 7, "version": "0.2.1", "marker": "rbtv-managed",
        "harnesses": ["claude"], "files": [FIXAGENT, "fixmod/goodcomp#fixskill"],
        "packs": [], "guidance_basis": "none", "shared_claims": [], "shared_files": [],
        "components": {"fixmod/goodcomp": {
            "module": "fixmod", "component": "goodcomp", "tree": "repo",
            "harnesses": ["claude"], "units": {
                "fixagent": {"method": "sub-agent",
                             "files": [".claude/agents/fixagent.md"]},
                "fixskill": {"method": "skill", "files": []}}}}}), encoding="utf-8")
    before = read_state(legacy)
    out, err = io.StringIO(), io.StringIO()
    with patch.object(commands, "scan_all", return_value=(catalog, [])), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = commands.main(["update", "all", "--target", str(legacy)])
    after = json.loads((legacy / STATE_REL).read_text(encoding="utf-8"))
    check("SA-migrate — a schema 7 record is read, its sub-agent file becomes the agent "
          "file, and the record written is valid",
          before["components"]["fixmod/goodcomp"]["units"]["fixagent"]["method"] == "agent"
          and code == 0 and after["schema"] == 9
          and after["components"]["fixmod/goodcomp"]["units"]["fixagent"]
          == {"method": "agent", "files": []}
          and not schema.errors(after, schema.load("install-json"))
          and (legacy / ".claude/skills/fixskill/SKILL.md").is_file(), out.getvalue() + err.getvalue())
    check("SA-migrate-unset — the migrated agent has no model and effort: its old file "
          "goes and the result names the command that gives them",
          not (legacy / ".claude/agents/fixagent.md").exists()
          and f"{FIXAGENT} is chosen and has no model and effort for a receiving harness"
          in " ".join(out.getvalue().split())
          and "rbtv add fixagent --on HARNESS:MODEL:EFFORT --target "
          + shell_quote(legacy) in out.getvalue(),
          out.getvalue())
