"""Component pack discovery, selection, reconciliation, and catalog views."""
from __future__ import annotations

import contextlib
import io
import json

from discovery import Refuse, scan_all
from lib.catalog import catalog_packs
from lib.commands import cmd_add, cmd_list, cmd_rm, cmd_show, cmd_update
from lib.parser import build_parser
from lib.state import read_state


def packs(ctx) -> None:
    check, tmp, tree, mirror = ctx.check, ctx.tmp, ctx.tree, ctx.mirror
    catalog = ctx.frame()[0]
    print("\nPK — component packs")
    starter = catalog_packs(catalog).get("starter")
    check("PK-discover — schema-checked pack names its component and files",
          starter is not None and starter["component"] == "fixmod/goodcomp"
          and len(starter["files"]) == 2, str(starter))

    duplicate = tree / "fixmod" / "codexcomp" / "packs" / "starter.json"
    duplicate.parent.mkdir(parents=True, exist_ok=True)
    duplicate.write_text(json.dumps({"description": "duplicate", "files":
                                     ["fixmod/codexcomp#codexrule"]}), encoding="utf-8")
    try:
        scan_all(mirror, tree)
        duplicate_result = "no refusal"
    except Refuse as exc:
        duplicate_result = exc.code
    duplicate.unlink()
    check("PK-duplicate — duplicate pack name refuses", duplicate_result == "pack-duplicate",
          duplicate_result)

    invalid = tree / "fixmod" / "codexcomp" / "packs" / "bad.json"
    invalid.write_text(json.dumps({"description": "bad", "files": ["no/such#file"]}),
                            encoding="utf-8")
    try:
        scan_all(mirror, tree)
        invalid_result = "no refusal"
    except Refuse as exc:
        invalid_result = exc.code
    invalid.unlink()
    check("PK-file — unknown pack file refuses", invalid_result == "pack-file-unknown",
          invalid_result)

    malformed = tree / "fixmod" / "codexcomp" / "packs" / "malformed.json"
    malformed.write_text(json.dumps({"files": ["fixmod/codexcomp#codexrule"]}),
                         encoding="utf-8")
    try:
        scan_all(mirror, tree)
        malformed_result = "no refusal"
    except Refuse as exc:
        malformed_result = exc.code
    malformed.unlink()
    check("PK-schema — malformed pack refuses its schema", malformed_result == "pack-invalid",
          malformed_result)

    target = tmp / "ws-packs"
    target.mkdir()

    def args(tokens):
        parsed = build_parser().parse_args(tokens)
        parsed._why = "selftest"
        return parsed

    with contextlib.redirect_stdout(io.StringIO()):
        cmd_add(args(["add", "--pack", "starter", "--harness", "claude",
                      "--guidance", "none"]), target, catalog, [])
    state = read_state(target)
    check("PK-add — pack generates each file but records only the pack",
          state["packs"] == ["starter"] and state["files"] == []
          and set(state["components"]["fixmod/goodcomp"]["selected"])
          == {"fixskill", "fixrule"}, str(state))

    combined = tmp / "ws-pack-combined"
    combined.mkdir()
    with contextlib.redirect_stdout(io.StringIO()):
        cmd_add(args(["add", "fixcmd", "--pack", "starter", "--harness", "claude",
                      "--guidance", "none"]), combined, catalog, [])
    combined_state = read_state(combined)
    check("PK-add-combined — one command keeps explicit and pack selections distinct",
          combined_state["packs"] == ["starter"]
          and combined_state["files"] == ["fixmod/goodcomp#fixcmd"]
          and set(combined_state["components"]["fixmod/goodcomp"]["selected"])
          == {"fixcmd", "fixskill", "fixrule"}, str(combined_state))

    with contextlib.redirect_stdout(io.StringIO()):
        cmd_add(args(["add", "fixskill"]), target, catalog, [])
        cmd_rm(args(["remove", "--pack", "starter"]), target, catalog, [])
    state = read_state(target)
    check("PK-remove — explicit file survives a removed pack",
          state["packs"] == [] and state["files"] == ["fixmod/goodcomp#fixskill"]
          and set(state["components"]["fixmod/goodcomp"]["selected"]) == {"fixskill"},
          str(state))

    with contextlib.redirect_stdout(io.StringIO()):
        cmd_add(args(["add", "--pack", "starter", "--pack", "second"]),
                target, catalog, [])
        cmd_rm(args(["remove", "--pack", "starter"]), target, catalog, [])
    overlapping = read_state(target)
    check("PK-overlap — file shared by an enabled pack stays once",
          overlapping["packs"] == ["second"]
          and set(overlapping["components"]["fixmod/goodcomp"]["selected"])
          == {"fixskill", "fixrule"}, str(overlapping))
    with contextlib.redirect_stdout(io.StringIO()):
        cmd_rm(args(["remove", "--pack", "second"]), target, catalog, [])

    with contextlib.redirect_stdout(io.StringIO()):
        cmd_add(args(["add", "--pack", "starter"]), target, catalog, [])
    pack_path = tree / "fixmod" / "goodcomp" / "packs" / "starter.json"
    original = pack_path.read_text(encoding="utf-8")
    pack_path.write_text(json.dumps({"description": "The fixture starter pack",
                                     "files": ["fixmod/goodcomp#fixskill"]}), encoding="utf-8")
    catalog, _ = scan_all(mirror, tree)
    with contextlib.redirect_stdout(io.StringIO()):
        cmd_update(args(["update", "all"]), target, catalog, [])
    dropped = read_state(target)
    pack_path.write_text(original, encoding="utf-8")
    catalog, _ = scan_all(mirror, tree)
    with contextlib.redirect_stdout(io.StringIO()):
        cmd_update(args(["update", "all"]), target, catalog, [])
    restored = read_state(target)
    check("PK-update — changed pack drops then restores its generated file",
          set(dropped["components"]["fixmod/goodcomp"]["selected"]) == {"fixskill"}
          and set(restored["components"]["fixmod/goodcomp"]["selected"])
          == {"fixskill", "fixrule"}, str(restored))

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cmd_add(args(["add", "--pack", "nosuchpack"]), target, catalog, [])
        unknown = "no refusal"
    except Refuse as exc:
        unknown = exc.message
    check("PK-unknown — names list --type pack", "list --type pack" in unknown, unknown)

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            cmd_add(args(["add", "starter"]), target, catalog, [])
        bare = "no refusal"
    except Refuse as exc:
        bare = exc.code
    check("PK-namespace — a bare pack name never enables it", bare == "name-unknown", bare)

    rendered = io.StringIO()
    with contextlib.redirect_stdout(rendered):
        cmd_list(args(["list", "--type", "pack"]), target, catalog, [])
        cmd_show(args(["show", "--pack", "starter"]), target, catalog, [])
    text = rendered.getvalue()
    words = ("starter", "fixmod/goodcomp", "2", "Pack: on for this target", "Declaration:",
             "fixskill", "fixrule")
    check("PK-discover-views — list and show expose component, count, state, path and files",
          all(word in text for word in words), text)
    ctx.keep(locals())
