"""What `ls`, `li` and `doctor` print, plain, pretty and as JSON."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from pathlib import Path

from discovery import EXPOSURE_COLS, EXPOSURE_NAME, SKILLS_DIR, scan_tree

from lib.constants import BASIS_NONE, MANAGED_MARK, SCHEMA, STATE_REL, _RUNTIME
from lib.pathlinks import local_bin
from lib.target import DISCOVER_CWD, DISCOVER_FLAG
from lib.state import _part_in, read_state, write_state
from lib.operations import do_install
from lib.listing import _settings_view, build_ls, do_list, print_li, print_ls
from lib.doctor import do_doctor, doctor_exit
from lib.parser import build_parser
from lib.commands import _li_filter, cmd_doctor, cmd_li, cmd_ls, main

from .fixture import _fixture


def ls_li_doctor(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nSURF — ls / li / doctor / --pretty / --json")

    vend_files = sum(1 for q in (tree / SKILLS_DIR / "vendored").rglob("*")
                     if q.is_file())
    ls_data = build_ls(catalog, [
        {"id": "fixmod/goodcomp",
         "winner_path": "/mirror/fixmod/goodcomp",
         "shadowed_path": "/repo/fixmod/goodcomp"}],
        read_state(target))
    vend_e = next(e for e in ls_data["components"]
                  if e["id"] == "_hub/skills/vendored")
    good_e = next(e for e in ls_data["components"]
                  if e["id"] == "fixmod/goodcomp")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_ls(ls_data)
    ls_txt = buf.getvalue()
    check("SURF-ls-reports — SHADOWED prints; no no-manifest section",
          "SHADOWED: fixmod/goodcomp exists on both trees" in ls_txt
          and "no exposure manifest" not in ls_txt
          and "no_manifest" not in ls_data,
          ls_txt[-400:])
    check("SURF-ls-parts-are-rows — vendored parts is 1, not file count",
          vend_e["parts"] == 1
          and len(vend_e["items"]) == 1
          and vend_files > 1
          and good_e["parts"] == len(good_e["items"]) == 9
          and f"{vend_files}" not in
          [str(e["parts"]) for e in ls_data["components"]
           if e["id"] == "_hub/skills/vendored"],
          f"parts={vend_e['parts']} files={vend_files} "
          f"good={good_e['parts']}")

    pws = tmp / "ws-surf-li"
    pws.mkdir()
    do_install(pws, catalog, ["fixmod/goodcomp"], ["claude"],
               dry_run=False,
               parts=["fixmod/goodcomp#fixskill",
                      "fixmod/goodcomp#fixrule"])
    do_install(pws, catalog, ["fixmod/codexcomp"], ["claude"],
               dry_run=False)
    ls_in = build_ls(catalog, [], read_state(pws))
    good = next(e for e in ls_in["components"] if e["id"] == "fixmod/goodcomp")
    inn = {i["part_id"]: i["in"] for i in good["items"]}
    check("SURF-ls-in-column — booked True, sibling False",
          inn.get("fixskill") is True and inn.get("fixrule") is True
          and inn.get("fixcmd") is False,
          str(inn))
    raw_sk = {"components": {
        "_skills/vendored": {"parts": {"vendored": {"method": "skill"}}}}}
    check("ls-in-legacy-skills-key — leftover _skills/ counts as in",
          _part_in(raw_sk, "_hub/skills/vendored", "vendored") is True)
    raw_v1 = {"components": {
        "fixmod/goodcomp": {"files": [".claude/rules/fixrule.md"]}}}
    check("ls-in-schema1-whole — missing parts map means every pid is in",
          _part_in(raw_v1, "fixmod/goodcomp", "fixrule") is True
          and _part_in(raw_v1, "fixmod/goodcomp", "fixcmd") is True)
    ls_nc = build_ls(catalog, [], {}, exclude_components=["fixmod/goodcomp"])
    check("SURF-ls-exclude-component",
          all(e["id"] != "fixmod/goodcomp" for e in ls_nc["components"]),
          str([e["id"] for e in ls_nc["components"]][:8]))
    ls_nx = build_ls(catalog, [], {}, exclude_methods=["skill"])
    check("SURF-ls-exclude-method",
          all(i["method"] != "skill"
              for e in ls_nx["components"] for i in e["items"]))
    li0 = do_list(pws, catalog)
    args_nc = argparse.Namespace(
        module=[], component=[], method=[],
        exclude_module=[], exclude_component=["fixmod/goodcomp"],
        exclude_method=[])
    check("SURF-li-exclude-component",
          "fixmod/goodcomp" not in _li_filter(li0, catalog, args_nc)["components"])
    li_data = do_list(pws, catalog)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_li(li_data)
    li_txt = buf.getvalue()
    part_rec = li_data["components"]["fixmod/goodcomp"]
    full_rec = li_data["components"]["fixmod/codexcomp"]
    check("SURF-li-full-vs-part — partial has out:, full does not",
          part_rec["status"] == "part"
          and full_rec["status"] == "full"
          and "out:" in li_txt
          and any(line.startswith("1") or "part" in line
                  for line in li_txt.splitlines())
          and any("full" in line and "fixmod/codexcomp" in line
                  for line in li_txt.splitlines())
          and any("part" in line and "fixmod/goodcomp" in line
                  for line in li_txt.splitlines())
          and "out: " in li_txt
          and "fixcmd" in part_rec["missing"]
          and not full_rec["missing"],
          f"part={part_rec['status']} miss={part_rec['missing']} "
          f"full={full_rec['status']}")
    # Retargeted TWICE on 2026-08-22. The original was
    # `endswith("@  (none)") or "@  " in li_txt` — an OR whose right arm
    # matched any line containing "@  ". The first retarget asserted the
    # real payload was listed, but THIS FIXTURE OWNS NOTHING (claims,
    # guidance and links are all empty), so every `all(... for x in [])`
    # was vacuously true and a mutant that stopped printing items entirely
    # still passed. The renderer is now driven with a payload that HAS one
    # of each, which is the only way the listing behaviour can be observed.
    _labels = ("guidance files written",
               "keys held in shared config files",
               "commands linked onto PATH")
    _probe = {"guidance_files": ["AGENTS.md"],
              "shared_claims": ['.mcp.json::["mcpServers", "probe"]'],
              "path_links": [{"name": "probe-cli"}],
              "components": {}, "target": str(pws),
              "state_file": str(pws / STATE_REL),
              "marker": MANAGED_MARK, "guidance_basis": BASIS_NONE,
              "schema": SCHEMA,
              "settings": _settings_view({})}
    _pbuf = io.StringIO()
    with contextlib.redirect_stdout(_pbuf):
        print_li(_probe)
    _ptxt = _pbuf.getvalue()
    _plisted = [ln[2:] for ln in _ptxt.splitlines()
                if ln.startswith("  ") and ln.strip()]
    check("SURF-li-ownership-footer — every owned thing is listed under a "
          "named section",
          all(f"\n{lab}:" in _ptxt for lab in _labels)
          and "AGENTS.md" in _plisted
          and '.mcp.json::["mcpServers", "probe"]' in _plisted
          and "probe-cli" in _plisted
          # and the real render still labels all three, empty or not
          and all(f"\n{lab}:" in li_txt for lab in _labels),
          f"listed={_plisted} "
          f"labels_missing={[l for l in _labels if chr(10) + l + ':' not in _ptxt]}")

    by_name = {c["name"]: c for c in do_doctor(
        pws, DISCOVER_CWD, catalog, [], tree,
        pws / ".rbtv" / "mirror")["checks"]}
    check("SURF-doctor-names — every check has a stable name",
          set(by_name) == {
              "target", "book", "tree-repo", "tree-mirror", "bin-dir",
              "bin-on-path", "local-bin-shadow", "path-unbooked",
              "path-collision", "path-not-executable", "add-collisions",
              "guidance-basis"},
          str(sorted(by_name)))

    notdir = tmp / "ws-doc-notdir"
    notdir.write_text("x\n", encoding="utf-8")
    tfail = {c["name"]: c for c in do_doctor(
        notdir, DISCOVER_FLAG, {}, [], tree,
        notdir / ".rbtv" / "mirror")["checks"]}
    check("SURF-doctor-target-fail — names the path",
          tfail["target"]["level"] == "fail"
          and str(notdir) in tfail["target"]["detail"]
          and "not a directory" in tfail["target"]["detail"]
          and doctor_exit(list(tfail.values())) == 1,
          tfail["target"]["detail"])

    bws = tmp / "ws-doc-badbook"
    bws.mkdir()
    (bws / STATE_REL).parent.mkdir(parents=True)
    (bws / STATE_REL).write_text("{not-json", encoding="utf-8")
    bfail = {c["name"]: c for c in do_doctor(
        bws, DISCOVER_CWD, catalog, [], tree,
        bws / ".rbtv" / "mirror")["checks"]}
    check("SURF-doctor-book-fail — unreadable book is named",
          bfail["book"]["level"] == "fail"
          and "unreadable" in bfail["book"]["detail"]
          and doctor_exit(list(bfail.values())) == 1,
          bfail["book"]["detail"])

    rtree = tmp / "doc-repo-tree"
    rtree.mkdir()
    _fixture(rtree)
    mtree = tmp / "doc-mirror-tree"
    mtree.mkdir()
    (mtree / "fixmod" / "goodcomp").mkdir(parents=True)
    (mtree / "fixmod" / "goodcomp" / EXPOSURE_NAME).write_text(
        ",".join(EXPOSURE_COLS) + "\n", encoding="utf-8")
    tws = tmp / "ws-doc-trees"
    tws.mkdir()
    tchecks = {c["name"]: c for c in do_doctor(
        tws, DISCOVER_CWD, {}, [], rtree, mtree)["checks"]}
    repo_n = len(scan_tree(rtree, "repo"))
    mir_n = len(scan_tree(mtree, "mirror"))
    check("SURF-doctor-trees — counts come from the trees given",
          tchecks["tree-repo"]["level"] == "ok"
          and tchecks["tree-mirror"]["level"] == "ok"
          and f"{repo_n} components" in tchecks["tree-repo"]["detail"]
          and str(rtree) in tchecks["tree-repo"]["detail"]
          and f"{mir_n} components" in tchecks["tree-mirror"]["detail"]
          and str(mtree) in tchecks["tree-mirror"]["detail"]
          and repo_n != mir_n,
          f"repo={tchecks['tree-repo']['detail']} "
          f"mir={tchecks['tree-mirror']['detail']}")

    saved_bin, saved_path = _RUNTIME["bin"], os.environ.get("PATH")
    ghost = tmp / "ghost-bin"
    _RUNTIME["bin"] = ghost
    os.environ["PATH"] = "/usr/bin"
    dmiss = {c["name"]: c for c in do_doctor(
        tws, DISCOVER_CWD, {}, [], rtree, mtree)["checks"]}
    check("SURF-doctor-bin-missing — names the bindir",
          dmiss["bin-dir"]["level"] == "warn"
          and str(ghost) in dmiss["bin-dir"]["detail"]
          and "missing" in dmiss["bin-dir"]["detail"]
          and dmiss["path-unbooked"]["detail"] == "no directory"
          and doctor_exit(list(dmiss.values())) == 0,
          dmiss["bin-dir"]["detail"])
    check("SURF-doctor-bin-on-path — says not on PATH",
          dmiss["bin-on-path"]["level"] == "warn"
          and "not on PATH" in dmiss["bin-on-path"]["detail"],
          dmiss["bin-on-path"]["detail"])

    ghost.mkdir()
    os.environ["PATH"] = str(ghost) + os.pathsep + str(local_bin())
    (local_bin()).mkdir(parents=True, exist_ok=True)
    (local_bin() / "shadowme").write_text("x\n", encoding="utf-8")
    (ghost / "shadowme").symlink_to(tmp / "fake-bashrc")
    Path(_RUNTIME["rc"]).write_text("x\n", encoding="utf-8")
    dsh = {c["name"]: c for c in do_doctor(
        tws, DISCOVER_CWD, {}, [], rtree, mtree)["checks"]}
    check("SURF-doctor-local-shadow — names the shadowed command",
          dsh["local-bin-shadow"]["level"] == "warn"
          and "shadowme" in dsh["local-bin-shadow"]["detail"]
          and "shadows" in dsh["local-bin-shadow"]["detail"],
          dsh["local-bin-shadow"]["detail"])
    (ghost / "stranger").symlink_to(tmp / "fake-bashrc")
    dun = {c["name"]: c for c in do_doctor(
        tws, DISCOVER_CWD, {}, [], rtree, mtree)["checks"]}
    check("SURF-doctor-unbooked — names the leftover link",
          dun["path-unbooked"]["level"] == "warn"
          and "stranger" in dun["path-unbooked"]["detail"],
          dun["path-unbooked"]["detail"])
    (ghost / "hitfile").write_text("not a link\n", encoding="utf-8")
    coll_cat = {
        "amod/acomp": {
            "id": "amod/acomp", "module": "amod",
            "component": "acomp", "kind": "component",
            "manifest": True, "tree": "repo",
            "path": str(tmp),
            "rows": [{"part-id": "hitfile", "method": "path"}]}}
    dcol = {c["name"]: c for c in do_doctor(
        tws, DISCOVER_CWD, coll_cat, [], rtree, mtree)["checks"]}
    check("SURF-doctor-path-collision — names the regular file",
          dcol["path-collision"]["level"] == "warn"
          and "hitfile" in dcol["path-collision"]["detail"]
          and "not a symlink" in dcol["path-collision"]["detail"],
          dcol["path-collision"]["detail"])
    nox = tmp / "not-exec.py"
    nox.write_text("print(1)\n", encoding="utf-8")
    nox.chmod(0o644)
    (ghost / "noexec").symlink_to(nox)
    nexec_cat = {
        "amod/acomp": {
            "id": "amod/acomp", "module": "amod",
            "component": "acomp", "kind": "component",
            "manifest": True, "tree": "repo",
            "path": str(tmp),
            "rows": [{"part-id": "noexec", "method": "path"}]}}
    dnx = {c["name"]: c for c in do_doctor(
        tws, DISCOVER_CWD, nexec_cat, [], rtree, mtree)["checks"]}
    check("SURF-doctor-not-exec — names the non-executable dest",
          dnx["path-not-executable"]["level"] == "warn"
          and "noexec" in dnx["path-not-executable"]["detail"]
          and "not executable" in dnx["path-not-executable"]["detail"],
          dnx["path-not-executable"]["detail"])
    _RUNTIME["bin"] = saved_bin
    if saved_path is None:
        os.environ.pop("PATH", None)
    else:
        os.environ["PATH"] = saved_path

    cws = tmp / "ws-doc-addcoll"
    cws.mkdir()
    (cws / ".claude/skills/fixskill").mkdir(parents=True)
    (cws / ".claude/skills/fixskill/SKILL.md").write_text(
        "hand authored, no marker\n", encoding="utf-8")
    dadd = {c["name"]: c for c in do_doctor(
        cws, DISCOVER_CWD, {"fixmod/goodcomp": catalog["fixmod/goodcomp"]},
        [], tree, cws / ".rbtv" / "mirror")["checks"]}
    check("SURF-doctor-add-collisions — names the unbooked file",
          dadd["add-collisions"]["level"] == "warn"
          and "fixskill" in dadd["add-collisions"]["detail"]
          and "collision" in dadd["add-collisions"]["detail"]
          and doctor_exit(list(dadd.values())) == 0,
          dadd["add-collisions"]["detail"])

    gws = tmp / "ws-doc-basis"
    gws.mkdir()
    write_state(gws, {"components": {}, "guidance_basis": "WAT.md",
                      "shared_claims": []})
    dbas = {c["name"]: c for c in do_doctor(
        gws, DISCOVER_CWD, {}, [], tree,
        gws / ".rbtv" / "mirror")["checks"]}
    check("SURF-doctor-guidance-basis — names the bad value",
          dbas["guidance-basis"]["level"] == "warn"
          and "WAT.md" in dbas["guidance-basis"]["detail"]
          and "guidance-basis-invalid" in dbas["guidance-basis"]["detail"],
          dbas["guidance-basis"]["detail"])

    buf_p, buf_j = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf_p), \
         contextlib.redirect_stderr(io.StringIO()):
        cmd_ls(build_parser().parse_args(["ls"]), pws, catalog, [])
    with contextlib.redirect_stdout(buf_j), \
         contextlib.redirect_stderr(io.StringIO()):
        cmd_ls(build_parser().parse_args(["ls", "--pretty"]),
               pws, catalog, [])
    plain_ls, pretty_ls = buf_p.getvalue(), buf_j.getvalue()
    check("SURF-pretty-off-is-plain — default has no ANSI",
          "\033[" not in plain_ls
          and "\033[" in pretty_ls,
          f"plain_esc={'\\033[' in plain_ls} "
          f"pretty_esc={'\\033[' in pretty_ls}")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), \
         contextlib.redirect_stderr(io.StringIO()):
        cmd_ls(build_parser().parse_args(["ls", "--json"]),
               pws, catalog, [])
    lsj = json.loads(buf.getvalue())
    check("SURF-json-ls-keys — today's keys plus items/index",
          set(lsj) >= {"ok", "components", "shadowed",
                       "hub_refusals", "index"}
          and "no_manifest" not in lsj
          and set(lsj["components"][0]) >= {
              "id", "tree", "module", "kind", "manifest", "methods",
              "parts", "note", "items"}
          and lsj["ok"] is True,
          str(sorted(lsj)))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), \
         contextlib.redirect_stderr(io.StringIO()):
        cmd_li(build_parser().parse_args(["li", "--json"]),
               pws, catalog, [])
    lij = json.loads(buf.getvalue())
    check("SURF-json-li-keys — today's keys plus path_links/status",
          set(lij) >= {"ok", "target", "schema", "state_file", "marker",
                       "guidance_basis", "components", "guidance_files",
                       "shared_claims", "path_links", "settings"}
          and lij["components"]["fixmod/goodcomp"]["status"] == "part"
          and "missing" in lij["components"]["fixmod/goodcomp"],
          str(sorted(lij)))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), \
         contextlib.redirect_stderr(io.StringIO()):
        cmd_doctor(build_parser().parse_args(["doctor", "--json"]),
                   pws, catalog, [])
    dj = json.loads(buf.getvalue())
    check("SURF-json-doctor-keys — envelope + named checks",
          set(dj) >= {"ok", "version", "target", "why", "checks"}
          and {c["name"] for c in dj["checks"]}
          == set(by_name)
          and all("level" in c and "detail" in c and "ok" in c
                  for c in dj["checks"]),
          str(sorted(dj)))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), \
         contextlib.redirect_stderr(io.StringIO()):
        rc_ref = main(["add", "--target", str(pws), "-c", "no/comp",
                       "--json"])
    env = json.loads(buf.getvalue())
    check("SURF-json-refuse-keys — refusal envelope kept",
          rc_ref == 1 and env.get("ok") is False
          and "refusal" in env and "code" in env["refusal"]
          and "message" in env["refusal"],
          str(env))
    ctx.keep(locals())
