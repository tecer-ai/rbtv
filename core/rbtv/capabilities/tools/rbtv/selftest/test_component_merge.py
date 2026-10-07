"""Schema 9: the components `core/build` and `core/install` are read as the
one component `core/rbtv`, in a root record and in an agent's record, and the
next update brings the folder in line."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from discovery import scan_all
from lib import commands
from lib.commands import cmd_agent
from lib.constants import _RUNTIME, AGENT_RECORD, STATE_REL
from lib.parser import build_parser
from lib.pathlinks import link_one
from lib.shared_links import owner_file
from lib.state import migrate_rbtv_component_ids, read_state

from .fixture import _component, _file_md, _w

KNOWN = {"claude": {"m1": {"rungs": ["low", "high"], "selected": True}}}


def _schema_8() -> dict:
    """What a schema 8 record holds when both old components are installed."""
    return {"schema": 8, "harnesses": ["claude"], "packs": [], "components": {
        "core/build": {"module": "core", "component": "build", "tree": "repo",
                       "harnesses": ["claude"], "selected": {
                           "build": {"method": "skill", "files": [
                               ".claude/skills/build/SKILL.md"]}}},
        "core/install": {"module": "core", "component": "install", "tree": "repo",
                         "harnesses": ["claude", "codex"], "path_links": ["rbtv"],
                         "selected": {
                             "rbtv": {"method": "tool", "files": [], "links": ["rbtv"]},
                             "manage-components": {"method": "skill", "files": [
                                 ".claude/skills/manage-components/SKILL.md"]}}},
        "moda/comp": {"module": "moda", "component": "comp", "harnesses": ["claude"],
                      "selected": {"kiss": {"method": "rule", "files": []}}}},
        "files": ["core/build#build", "core/install#manage-components",
                  "core/install#rbtv", "moda/comp#kiss"]}


def _tool(comp: Path) -> Path:
    tool = comp / "capabilities/tools/rbtv"
    _w(tool / "rbtv.json", json.dumps({
        "name": "rbtv", "description": "The fixture rbtv command",
        "entry": "install.py"}))
    _w(tool / "install.py", "#!/usr/bin/env python3\nprint('fixture')\n")
    (tool / "install.py").chmod(0o755)
    return tool / "install.py"


def record_rewrite(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp

    print("\nU-merge — schema 9 reads core/build and core/install as core/rbtv")
    ws = tmp / "ws-merge-record"
    (ws / STATE_REL).parent.mkdir(parents=True)
    _w(ws / STATE_REL, json.dumps(_schema_8()))
    raw = (ws / STATE_REL).read_bytes()
    got = read_state(ws)
    rec = got["components"].get("core/rbtv") or {}
    check("U-merge-one-entry — a record holding both old components ends with one "
          "core/rbtv entry, and other components stay",
          set(got["components"]) == {"core/rbtv", "moda/comp"}
          and rec.get("component") == "rbtv" and rec.get("module") == "core",
          str(sorted(got["components"])))
    check("U-merge-carries-both — the one entry carries what both held",
          rec.get("harnesses") == ["claude", "codex"]
          and rec.get("path_links") == ["rbtv"]
          and rec["selected"]["rbtv"] == {"method": "tool", "files": [], "links": ["rbtv"]}
          and rec["selected"]["framework"]
          == {"method": "skill", "files": [".claude/skills/build/SKILL.md"]},
          str(rec))
    check("U-merge-file-ids — build is framework and rbtv keeps its name, "
          "in the selection and in the booking",
          got["files"] == ["core/rbtv#framework", "core/rbtv#rbtv", "moda/comp#kiss"]
          and "build" not in rec["selected"], str(got["files"]))
    check("U-merge-no-successor — manage-components leaves the selection and keeps "
          "its booking, so the next update can delete its files",
          not any("manage-components" in key for key in got["files"])
          and rec["selected"]["manage-components"]["files"]
          == [".claude/skills/manage-components/SKILL.md"], str(rec["selected"]))
    check("U-merge-read-only — reading a schema 8 record leaves its file as it was",
          (ws / STATE_REL).read_bytes() == raw)
    again = copy.deepcopy(got)
    migrate_rbtv_component_ids(again)
    check("U-merge-idempotent — the step changes nothing on a rewritten record",
          again == got)

    for old, files, expect_files, expect_selected in (
            ("core/build", {"build": {"method": "skill", "files": []}},
             {"framework"}, ["core/rbtv#framework"]),
            ("core/install", {"rbtv": {"method": "tool", "files": [], "links": ["rbtv"]}},
             {"rbtv"}, ["core/rbtv#rbtv"])):
        state = {"components": {old: {"module": "core", "component": old.split("/")[1],
                                      "harnesses": ["claude"], "selected": files}},
                 "files": [f"{old}#{name}" for name in files]}
        migrate_rbtv_component_ids(state)
        check(f"U-merge-single — a record holding only {old} becomes core/rbtv",
              set(state["components"]) == {"core/rbtv"}
              and set(state["components"]["core/rbtv"]["selected"]) == expect_files
              and state["files"] == expect_selected, str(state))

    half = {"components": {
        "core/rbtv": {"module": "core", "component": "rbtv", "harnesses": ["claude"],
                      "selected": {"rbtv": {"method": "tool", "files": [], "links": ["rbtv"]}}},
        "core/build": {"module": "core", "component": "build", "harnesses": ["claude"],
                       "selected": {"build": {"method": "skill", "files": ["a"]}}}},
        "files": ["core/rbtv#rbtv", "core/build#build", "core/rbtv#framework"]}
    migrate_rbtv_component_ids(half)
    check("U-merge-into-existing — an old component folds into a core/rbtv entry "
          "the record already holds, and no id repeats",
          set(half["components"]) == {"core/rbtv"}
          and set(half["components"]["core/rbtv"]["selected"]) == {"rbtv", "framework"}
          and half["files"] == ["core/rbtv#rbtv", "core/rbtv#framework"], str(half))

    home = tmp / "ws-merge-agent"
    _w(home / "agent.md", "---\nname: scout\n---\n\nScout.\n")
    record = _schema_8()
    record.pop("harnesses")
    record.update(name="scout", description="A scout", harness="claude",
                  model="m1", effort="high")
    _w(home / AGENT_RECORD, json.dumps(record))
    agent = read_state(home)
    check("U-merge-agent — an agent's agent.json is rewritten by the same reader",
          set(agent["components"]) == {"core/rbtv", "moda/comp"}
          and agent["files"] == got["files"] and agent["name"] == "scout",
          str(agent.get("files")))
    ctx.keep(locals())


def update_after_rewrite(ctx) -> None:
    """A schema 8 installation written by the program itself, then updated
    against a source tree that holds core/rbtv only."""
    check, tmp = ctx.check, ctx.tmp

    print("\nU-merge — the update after the rewrite brings the folder in line")
    # Resolved, as the program stores a source path: the temporary folder may
    # sit behind a link.
    old_src = (tmp / "merge-old-src").resolve()
    new_src = (tmp / "merge-new-src").resolve()
    install = _component(old_src, "core", "install")
    _file_md(install / "skills/manage-components.md", "manage-components",
             "The retired skill", "# manage\n")
    old_entry = _tool(install)
    _file_md(_component(old_src, "core", "build") / "skills/build.md", "build",
             "The building skill", "# build\n")
    merged = _component(new_src, "core", "rbtv")
    _file_md(merged / "skills/framework.md", "framework",
             "The building skill", "# rbtv framework\n")
    new_entry = _tool(merged)
    old_catalog, _ = scan_all(tmp / "merge-no-mirror", old_src)
    new_catalog, _ = scan_all(tmp / "merge-no-mirror", new_src)
    ws = tmp / "ws-merge-update"
    ws.mkdir()
    home = ws / ".rbtv/agents/scout"
    _w(home / "agent.md", "---\nname: scout\n---\n\nScout.\n")
    _w(home / AGENT_RECORD, json.dumps({
        "name": "scout", "description": "A scout", "packs": [],
        "files": ["core/build#build", "core/install#manage-components",
                  "core/install#rbtv"]}) + "\n")
    copies = [ws / ".claude/skills/manage-components/SKILL.md",
               home / ".claude/skills/manage-components/SKILL.md"]
    old_skill = [ws / ".claude/skills/build/SKILL.md",
                 home / ".claude/skills/build/SKILL.md"]
    new_skill = [ws / ".claude/skills/framework/SKILL.md",
                 home / ".claude/skills/framework/SKILL.md"]

    def run(catalog, *argv):
        out, err = io.StringIO(), io.StringIO()
        with patch.object(commands, "scan_all", return_value=(catalog, [])), \
                patch("lib.agents.cast_catalog", return_value=KNOWN), \
                patch("lib.agents.cast_model_id",
                      side_effect=lambda harness, model, _folder: f"id/{model}"), \
                patch.dict("os.environ", {"COLUMNS": "100"}), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            if argv[0] == "agent":
                code = cmd_agent(build_parser().parse_args(list(argv)), ws, catalog, [])
            else:
                code = commands.main([*argv, "--target", str(ws)])
        return code, " ".join(out.getvalue().split()), err.getvalue()

    def saved(path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    bindir = tmp / "merge-home" / "bin"
    saved_bin = _RUNTIME["bin"]
    _RUNTIME["bin"] = bindir
    try:
        # The installation as the program wrote it before this schema: the same
        # code, with the new step switched off, and the number it wrote then.
        with patch("lib.state.migrate_rbtv_component_ids", lambda state: None):
            run(old_catalog, "add", "core/build", "core/install", "--harness", "claude",
                "--guidance", "none")
            run(old_catalog, "agent", "add", str(home), "--harness", "claude",
                "--model", "m1", "--effort", "high")
        for path in (ws / STATE_REL, home / AGENT_RECORD):
            record = saved(path)
            record["schema"] = 8
            _w(path, json.dumps(record, indent=2, sort_keys=True) + "\n")
        owners = json.loads(owner_file(bindir).read_text(encoding="utf-8"))
        check("U-merge-fixture — the schema 8 installation holds both old components, "
              "the old skills' files, and a shortcut to the old program",
              set(saved(ws / STATE_REL)["components"]) == {"core/build", "core/install"}
              and set(saved(home / AGENT_RECORD)["components"])
              == {"core/build", "core/install"}
              and all(path.is_file() for path in copies + old_skill)
              and owners["links"]["rbtv"]["target"] == str(old_entry), str(owners))

        # The move: the old program's file is gone, so the shortcut points nowhere.
        shutil.rmtree(old_src)
        code, text, err = run(new_catalog, "update", "all", "--dry-run")
        check("U-merge-preview — a preview names the file that would leave and "
              "writes nothing",
              code == 0 and "Would remove: core/rbtv#manage-components" in text
              and copies[0].is_file()
              and set(saved(ws / STATE_REL)["components"])
              == {"core/build", "core/install"}, text + err)
        code, text, err = run(new_catalog, "update", "all")
        record = saved(ws / STATE_REL)
        check("U-merge-update-says — `update all` says the file left the record",
              code == 0 and "Removed: core/rbtv#manage-components" in text, text + err)
        check("U-merge-update-files — the harness files of manage-components and of "
              "the old build skill are deleted, and those of framework are written",
              not copies[0].exists() and not copies[0].parent.exists()
              and not old_skill[0].exists() and not old_skill[0].parent.exists()
              and new_skill[0].is_file()
              and "# rbtv framework\n" in new_skill[0].read_text(encoding="utf-8"))
        check("U-merge-update-record — the record is written as schema 9 with the "
              "one core/rbtv entry",
              record["schema"] == 9 and set(record["components"]) == {"core/rbtv"}
              and set(record["components"]["core/rbtv"]["selected"])
              == {"rbtv", "framework"}
              and record["components"]["core/rbtv"]["selected"]["framework"]["files"]
              == [".claude/skills/framework/SKILL.md"]
              and record["files"] == ["core/rbtv#framework", "core/rbtv#rbtv"],
              str(record))
        owners = json.loads(owner_file(bindir).read_text(encoding="utf-8"))
        check("U-merge-shortcut — the rbtv shortcut that pointed at the missing old "
              "program is repaired and says so",
              "relinked PATH shortcut(s): rbtv" in text
              and owners["links"]["rbtv"]["target"] == str(new_entry)
              and link_one(bindir, "rbtv", new_entry, dry=True) == "ok", text)
        code, text, err = run(new_catalog, "update", "all")
        check("U-merge-update-settled — a second update adds and removes nothing",
              code == 0 and "Added: none Removed: none" in text
              and saved(ws / STATE_REL) == record, text + err)

        code, text, err = run(new_catalog, "agent", "update", str(home), "all")
        record = saved(home / AGENT_RECORD)
        check("U-merge-agent-update — `agent update AGENT all` says the file left, "
              "deletes its files, and writes the record with core/rbtv",
              code == 0 and "Removed: core/rbtv#manage-components" in text
              and not copies[1].exists() and not old_skill[1].exists()
              and new_skill[1].is_file()
              and record["schema"] == 9 and set(record["components"]) == {"core/rbtv"}
              and sorted(record["files"])
              == ["core/rbtv#framework", "core/rbtv#rbtv"],
              text + err + str(record))
    finally:
        _RUNTIME["bin"] = saved_bin
    ctx.keep(locals())
