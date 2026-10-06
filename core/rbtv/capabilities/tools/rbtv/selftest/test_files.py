"""The 0.2.1 source format: checked schemas, marked sections of folder
instructions, the 0.2 names still read, hook and MCP server translation."""
from __future__ import annotations

import json

from discovery import Refuse, scan_all, scan_tree, file_rows

from lib import frontmatter, schema
from lib.claims import _block_del, _block_set
from lib.constants import HARNESSES, STATE_REL
from lib.content import _is_ours
from lib.operations import do_install, do_uninstall
from lib.state import read_state

from .fixture import _component, _file_md, _w


def _install(ws, root, cid, harnesses, tmp):
    cat, _ = scan_all(tmp / "no-mirror-u", root)
    return do_install(ws, cat, [cid], harnesses, dry_run=False), cat


def schema_and_frontmatter(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp

    print("\nU — frontmatter, schemas and the tool's bounds")
    crlf = frontmatter.split('---\r\nname: x\r\ndescription: "a: b"\r\n'
                             'skills: [p, q]\r\nrules:\r\n  - r\r\n---\r\nbody')
    check("U-frontmatter — CRLF, quoted scalars, inline and block lists",
          crlf == ({"name": "x", "description": "a: b", "skills": ["p", "q"],
                    "rules": ["r"]}, "body"), str(crlf))
    check("U-frontmatter — a file with none says so",
          frontmatter.split("# title\n") == (None, "# title\n"))

    skill = schema.load("skill")
    check("U-schema — a valid skill record passes",
          schema.errors({"name": "a-b", "description": "d"}, skill) == [])
    bad = schema.errors({"name": "A_B", "color": 1}, skill)
    check("U-schema — pattern, required and unknown fields are each named",
          any("does not match" in e for e in bad)
          and any("'description'" in e for e in bad)
          and any("color" in e for e in bad), str(bad))
    mcp = schema.load("mcp-server")
    base = {"name": "s", "description": "d"}
    check("U-schema — an MCP server needs exactly one of url and command",
          schema.errors({**base, "url": "u"}, mcp) == []
          and schema.errors({**base, "command": "c"}, mcp) == []
          and schema.errors({**base, "url": "u", "command": "c"}, mcp)
          and schema.errors(base, mcp),
          str(schema.errors(base, mcp)))
    hook = schema.load("hook")
    check("U-schema — a hook's timeout is a positive integer",
          schema.errors({**base, "event": "e", "command": "c", "timeout": 0},
                        hook)
          and schema.errors({**base, "event": "e", "command": "c",
                             "timeout": True}, hook)
          and schema.errors({**base, "event": "e", "command": "c",
                             "timeout": 5}, hook) == [])

    root = tmp / "tool-bounds"
    comp = _component(root, "tm", "tc")
    tool = comp / "capabilities/tools/t"
    _w(comp / "tools/prog.py", "#!/usr/bin/env python3\n")
    for entry, code in (("../../../tools/prog.py", None),
                        ("../../../../outside.py", "entry-point-escape"),
                        ("/abs/prog.py", "entry-point-escape"),
                        ("ws:tools/prog.py", None),
                        ("ws:../secret.py", "entry-point-escape")):
        _w(tool / "t.json", json.dumps(
            {"name": "t", "description": "d", "entry": entry}))
        try:
            file_rows(scan_tree(root, "repo")["tm/tc"])
            got = None
        except Refuse as exc:
            got = exc.code
        check(f"U-tool — entry {entry!r}: may climb, never leave the component",
              got == code, str(got))
    ctx.keep(locals())


def component_sections(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp

    print("\nU — a component's folder instructions are marked sections")
    root = tmp / "sections-src"
    for comp, target, text in (("alpha", ".", "alpha text"),
                               ("beta", "docs/notes", "beta text")):
        _component(root, "sm", comp)
        _w(root / "sm" / comp / "folder-instructions" / "f.md",
           f"---\ntarget: {target}\n---\n\n{text}\n")
    second = _component(root, "sm", "gamma")
    _w(second / "folder-instructions" / "g.md",
       "---\ntarget: .\n---\n\ngamma text\n")
    ws = tmp / "ws-sections"
    ws.mkdir()
    owner = "# Owner\n\nKeep this.\n"
    (ws / "CLAUDE.md").write_text(owner, encoding="utf-8")
    _install(ws, root, "sm/alpha", ["claude"], tmp)
    _install(ws, root, "sm/gamma", ["claude"], tmp)
    body = (ws / "CLAUDE.md").read_text(encoding="utf-8")
    check("U-sections — each component owns one labeled section, owner text kept",
          body.startswith(owner)
          and body.count("<!-- rbtv:start sm/alpha -->") == 1
          and body.count("<!-- rbtv:start sm/gamma -->") == 1
          and "alpha text" in body and "gamma text" in body
          and "<!-- rbtv:end sm/alpha --><!--" not in body, body)
    _, cat = _install(ws, root, "sm/beta", ["claude"], tmp)
    nested = ws / "docs/notes/CLAUDE.md"
    check("U-sections — a section lands in its target folder's file",
          nested.is_file() and "beta text" in nested.read_text(encoding="utf-8"))
    again = do_install(ws, cat, ["sm/alpha"], ["claude"], dry_run=False)
    check("U-sections — a re-install changes nothing",
          again["shared_written"] == [] and again["written"] == [])
    do_uninstall(ws, cat, ["sm/alpha"], dry_run=False)
    body = (ws / "CLAUDE.md").read_text(encoding="utf-8")
    check("U-sections — removing one takes only its section",
          "alpha text" not in body and "gamma text" in body
          and body.startswith(owner), body)
    do_uninstall(ws, cat, ["sm/gamma"], dry_run=False)
    do_uninstall(ws, cat, ["sm/beta"], dry_run=False)
    check("U-sections — the last removal restores the owner's exact bytes, "
          "and a file only we made is gone",
          (ws / "CLAUDE.md").read_text(encoding="utf-8") == owner
          and not nested.exists() and not (ws / "docs").exists()
          and not (ws / STATE_REL).exists())
    ctx.keep(locals())


def legacy_names(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp

    print("\nU — what the 0.2 installer wrote is still read")
    ws = tmp / "ws-legacy-book"
    (ws / STATE_REL).parent.mkdir(parents=True)
    (ws / STATE_REL).write_text(json.dumps({
        "schema": 2, "installer": "install.py",
        "components": {"m/c": {
            "module": "m", "component": "c", "harnesses": ["claude"],
            "parts": {"a": {"method": "sub-agent", "files": []},
                      "b": {"method": "config", "files": []},
                      "c": {"method": "path", "files": []},
                      "d": {"method": "agents.md", "files": []},
                      "e": {"method": "pool", "files": []},
                      "f": {"method": "skill", "files": []}}}}}),
        encoding="utf-8")
    files = read_state(ws)["components"]["m/c"]
    check("U-legacy — `parts` become `units`, methods take the new names, "
          "`pool` goes",
          "parts" not in files
          and {k: v["method"] for k, v in files["units"].items()}
          == {"a": "agent", "b": "mcp-server", "c": "tool",
              "d": "folder-instructions", "f": "skill"},
          str(files))

    renamed = tmp / "ws-renamed-install"
    (renamed / STATE_REL).parent.mkdir(parents=True)
    _w(renamed / STATE_REL, json.dumps({"components": {
        "core/installer": {"module": "core", "component": "installer",
                           "harnesses": ["claude"], "units": {
                               "rbtv-install": {"method": "tool", "files": [], "links": ["rbtv-install"]},
                               "manage-components": {"method": "skill", "files": []}}},
        "core/rbtv-cli": {"module": "core", "component": "rbtv-cli",
                          "harnesses": ["claude"], "units": {
                              "rbtv": {"method": "tool", "files": [], "links": ["rbtv"]}}}},
        "files": ["core/installer#rbtv-install", "core/rbtv-cli#rbtv"]}))
    migrated = read_state(renamed)
    check("U-legacy — renamed install component and shortcut file migrate together",
          set(migrated["components"]) == {"core/rbtv"}
          and set(migrated["components"]["core/rbtv"]["units"])
          == {"rbtv", "manage-components"}
          and migrated["files"] == ["core/rbtv#rbtv"], str(migrated))

    old = tmp / "old-marker.md"
    old.write_text("<!-- rbtv2-managed — generated by install.py -->\nx\n",
                   encoding="utf-8")
    check("U-legacy — a file with the rbtv2 marker is still ours",
          _is_ours(tmp, "old-marker.md"))
    fenced = "keep\n# rbtv2:start\nold\n# rbtv2:end\nafter\n"
    check("U-legacy — a block under the rbtv2 fence is replaced, then deleted, "
          "by its current name",
          _block_set(fenced, "new", "#")
          == "keep\n# rbtv:start\nnew\n# rbtv:end\nafter\n"
          and _block_del(fenced, "#") == "keep\nafter\n")
    ctx.keep(locals())


def translations(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp

    print("\nU — hooks and MCP servers are written in each harness's own form")
    root = tmp / "translate-src"
    comp = _component(root, "tm", "srv")
    _w(comp / "mcp-servers/local.json", json.dumps({
        "name": "local", "description": "A local server", "command": "npx",
        "args": ["pkg"], "env": {"TOKEN": "TOKEN_VAR"}}))
    _w(comp / "hooks/stop.json", json.dumps({
        "name": "stop", "description": "Runs at the end", "event": "Stop",
        "command": "true", "timeout": 5}))
    ws = tmp / "ws-translate"
    ws.mkdir()
    cat, _ = scan_all(tmp / "no-mirror-u", root)
    try:
        do_install(ws, cat, ["tm/srv"], list(HARNESSES), dry_run=False)
        refused = None
    except Refuse as exc:
        refused = exc.code
    check("U-mcp — Codex cannot rename a variable, so it refuses, writing nothing",
          refused == "mcp-env-unsupported"
          and not (ws / STATE_REL).exists()
          and not (ws / ".mcp.json").exists(), str(refused))
    do_install(ws, cat, ["tm/srv"], ["claude", "opencode"], dry_run=False)
    claude = json.loads((ws / ".mcp.json").read_text(encoding="utf-8"))
    opencode = json.loads((ws / "opencode.json").read_text(encoding="utf-8"))
    check("U-mcp — the variable's NAME becomes each harness's own reference",
          claude["mcpServers"]["local"]
          == {"command": "npx", "args": ["pkg"],
              "env": {"TOKEN": "${TOKEN_VAR}"}}
          and opencode["mcp"]["local"]["environment"]
          == {"TOKEN": "{env:TOKEN_VAR}"}, str((claude, opencode)))
    settings = json.loads((ws / ".claude/settings.json").read_text(encoding="utf-8"))
    check("U-hook — an rbtv hook becomes the harness's event entry",
          settings["hooks"]["Stop"]
          == [{"hooks": [{"type": "command", "command": "true",
                          "timeout": 5}]}]
          and "hooks" not in opencode, str(settings))
    ctx.keep(locals())
