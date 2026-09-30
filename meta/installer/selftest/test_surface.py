"""What `ls`, `li` and `doctor` print, plain, pretty and as JSON."""
from __future__ import annotations

import contextlib
import io
import json
import re

from discovery import SKILLS_DIR

from lib.constants import STATE_REL
from lib.target import DISCOVER_CWD, DISCOVER_FLAG
from lib.state import _unit_in, read_state, write_state
from lib.operations import do_install
from lib.listing import build_ls, do_list
from lib.doctor import do_doctor, doctor_exit
from lib.parser import build_parser
from lib.commands import _print_doctor, cmd_doctor, cmd_li, cmd_ls, main
from lib.report import print_result



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
    check("SURF-ls-reports — scanner retains shadowed source detail",
          ls_data["shadowed"][0]["id"] == "fixmod/goodcomp"
          and "no_manifest" not in ls_data)
    check("SURF-ls-parts-are-rows — vendored parts is 1, not file count",
          vend_e["units"] == 1
          and len(vend_e["items"]) == 1
          and vend_files > 1
          and good_e["units"] == len(good_e["items"]) == 9
          and f"{vend_files}" not in
          [str(e["units"]) for e in ls_data["components"]
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
    inn = {i["unit_id"]: i["in"] for i in good["items"]}
    check("SURF-ls-in-column — booked True, sibling False",
          inn.get("fixskill") is True and inn.get("fixrule") is True
          and inn.get("fixcmd") is False,
          str(inn))
    raw_sk = {"components": {
        "_skills/vendored": {"units": {"vendored": {"method": "skill"}}}}}
    check("ls-in-legacy-skills-key — leftover _skills/ counts as in",
          _unit_in(raw_sk, "_hub/skills/vendored", "vendored") is True)
    raw_v1 = {"components": {
        "fixmod/goodcomp": {"files": [".claude/rules/fixrule.md"]}}}
    check("ls-in-schema1-whole — missing parts map means every pid is in",
          _unit_in(raw_v1, "fixmod/goodcomp", "fixrule") is True
          and _unit_in(raw_v1, "fixmod/goodcomp", "fixcmd") is True)
    ls_nc = build_ls(catalog, [], {}, exclude_components=["fixmod/goodcomp"])
    check("SURF-ls-exclude-component",
          all(e["id"] != "fixmod/goodcomp" for e in ls_nc["components"]),
          str([e["id"] for e in ls_nc["components"]][:8]))
    ls_nx = build_ls(catalog, [], {}, exclude_methods=["skill"])
    check("SURF-ls-exclude-method",
          all(i["method"] != "skill"
              for e in ls_nx["components"] for i in e["items"]))
    li_data = do_list(pws, catalog)
    part_rec = li_data["components"]["fixmod/goodcomp"]
    full_rec = li_data["components"]["fixmod/codexcomp"]
    check("SURF-li-full-vs-part — structured inventory identifies missing items",
          part_rec["status"] == "part"
          and full_rec["status"] == "full"
          and "fixcmd" in part_rec["missing"]
          and not full_rec["missing"],
          f"part={part_rec['status']} miss={part_rec['missing']} "
          f"full={full_rec['status']}")

    doctor_data = do_doctor(pws, DISCOVER_CWD, catalog, [], tree,
                            pws / ".rbtv" / "mirror")
    by_name = {c["name"]: c for c in doctor_data["checks"]}
    check("SURF-doctor-workspace-scope — current selection is explicit",
          {"Saved selection", "Selected files", "Maintained guidance",
           "Source catalog"} <= set(by_name)
          and all(c["scope"] for c in doctor_data["checks"])
          and "fixmod" not in by_name["Source catalog"]["detail"],
          str(doctor_data["checks"]))

    notdir = tmp / "ws-doc-notdir"
    notdir.write_text("x\n", encoding="utf-8")
    tfail = do_doctor(notdir, DISCOVER_FLAG, {}, [], tree,
                      notdir / ".rbtv" / "mirror")
    named_tfail = {c["name"]: c for c in tfail["checks"]}
    check("SURF-doctor-target-fail — selected path is named",
          named_tfail["Saved selection"]["level"] == "fail"
          and str(notdir) in named_tfail["Saved selection"]["detail"]
          and doctor_exit(tfail["checks"]) == 1,
          named_tfail["Saved selection"]["detail"])

    bws = tmp / "ws-doc-badbook"
    bws.mkdir()
    (bws / STATE_REL).parent.mkdir(parents=True)
    (bws / STATE_REL).write_text("{not-json", encoding="utf-8")
    bfail = do_doctor(bws, DISCOVER_CWD, catalog, [], tree,
                      bws / ".rbtv" / "mirror")
    named_bfail = {c["name"]: c for c in bfail["checks"]}
    check("SURF-doctor-book-fail — unreadable selection is named",
          named_bfail["Saved selection"]["level"] == "fail"
          and "unreadable" in named_bfail["Saved selection"]["detail"]
          and doctor_exit(bfail["checks"]) == 1,
          named_bfail["Saved selection"]["detail"])

    gws = tmp / "ws-doc-basis"
    gws.mkdir()
    write_state(gws, {"components": {}, "guidance_basis": "WAT.md",
                      "shared_claims": []})
    dbas = do_doctor(gws, DISCOVER_CWD, {}, [], tree,
                     gws / ".rbtv" / "mirror")
    named_dbas = {c["name"]: c for c in dbas["checks"]}
    check("SURF-doctor-guidance-basis — invalid saved basis is named",
          named_dbas["Maintained guidance"]["level"] == "fail"
          and "WAT.md" in named_dbas["Maintained guidance"]["detail"],
          named_dbas["Maintained guidance"]["detail"])
    buf_p, buf_j = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf_p), \
         contextlib.redirect_stderr(io.StringIO()):
        cmd_ls(build_parser().parse_args(["ls"]), pws, catalog, [])
    with contextlib.redirect_stdout(buf_j), \
         contextlib.redirect_stderr(io.StringIO()):
        cmd_ls(build_parser().parse_args(["ls", "--pretty"]),
               pws, catalog, [])
    plain_ls, pretty_ls = buf_p.getvalue(), buf_j.getvalue()
    check("SURF-pretty-off-is-plain — default and optional pretty are readable",
          "\033[" not in plain_ls
          and "Target:" in plain_ls and "Target:" in pretty_ls,
          f"plain_esc={'\\033[' in plain_ls} "
          f"pretty_esc={'\\033[' in pretty_ls}")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), \
         contextlib.redirect_stderr(io.StringIO()):
        cmd_ls(build_parser().parse_args(["ls", "--json"]),
               pws, catalog, [])
    lsj = json.loads(buf.getvalue())
    check("SURF-json-ls-keys — list envelope and stable item identity",
          set(lsj) >= {"ok", "target", "source", "items", "total", "returned",
                       "limit", "offset", "next"}
          and all(set(row) >= {"id", "installed_items", "source_items",
                                   "description"}
                  for row in lsj["items"])
          and lsj["ok"] is True,
          str(sorted(lsj)))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), \
         contextlib.redirect_stderr(io.StringIO()):
        cmd_li(build_parser().parse_args(["li", "--json"]),
               pws, catalog, [])
    lij = json.loads(buf.getvalue())
    check("SURF-json-li-keys — installed list has same envelope",
          set(lij) == set(lsj)
          and all(row["installed_items"] > 0 for row in lij["items"]),
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
    check("SURF-json-refuse-keys — actionable error envelope",
          rc_ref == 1 and env.get("ok") is False
          and "error" in env and "code" in env["error"]
          and "message" in env["error"],
          str(env))

    root_help = build_parser().format_help()
    group_body = root_help.split("Shared options:", 1)[0]
    check("SURF-root-help-grouped-no-argparse-leakage",
          root_help.startswith("RBTV install — help")
          and "Discover" in root_help and "Change this workspace" in root_help
          and "Check and guided use" in root_help
          and "==SUPPRESS==" not in root_help
          # The two retired verbs get no row of their own in the grouped
          # command listing — only a mention later, in "Renamed:".
          and not any(line.strip().startswith(("set ", "dupe-artifacts "))
                      for line in group_body.splitlines())
          and "Renamed: set -> configure" in root_help,
          root_help)

    fail_data = {"ok": False, "target": str(pws), "why": DISCOVER_CWD,
                 "checks": [
                     {"name": "Saved selection", "ok": True, "level": "ok",
                      "scope": "Workspace", "detail": "2 components; record readable"},
                     {"name": "Selected shortcut: cast", "ok": False, "level": "fail",
                      "scope": "Shared commands",
                      "detail": "Managed cast shortcut missing; preview: "
                                "rbtv install update scaffolding --dry-run "
                                "--target 'X'; apply: rbtv install update "
                                "scaffolding --target 'X'"},
                     {"name": "Command lookup: cast", "ok": False, "level": "fail",
                      "scope": "Current PATH",
                      "detail": "no cast on PATH; run update scaffolding, "
                                "open a new terminal, then rerun doctor"},
                 ]}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _print_doctor(fail_data, color=False)
    doctor_plain = buf.getvalue()
    check("SURF-doctor-detail-not-truncated-at-width100 — full recovery text survives",
          fail_data["checks"][1]["detail"] in doctor_plain,
          doctor_plain)
    check("SURF-doctor-truthful-discovery-claim — FAIL never reads 'verified'",
          "Selected command discovery verified" not in doctor_plain
          and "FAILED for at least one shortcut" in doctor_plain,
          doctor_plain)

    ok_data = {"ok": True, "target": str(pws), "why": DISCOVER_CWD,
               "checks": [{"name": "Saved selection", "ok": True, "level": "ok",
                          "scope": "Workspace", "detail": "fine"}]}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        _print_doctor(ok_data, color=False)
    check("SURF-doctor-truthful-discovery-claim-no-path-checks",
          "No selected command shortcut needed a PATH lookup" in buf.getvalue(),
          buf.getvalue())

    buf_color = io.StringIO()
    with contextlib.redirect_stdout(buf_color):
        _print_doctor(fail_data, color=True)
    ansi_re = re.compile(r"\033\[[0-9;]*m")
    colored_lines = [ln for ln in buf_color.getvalue().splitlines()
                     if ln.startswith("Saved selection") or ln.startswith("Selected shortcut")]
    plain_lines = [ln for ln in doctor_plain.splitlines()
                   if ln.startswith("Saved selection") or ln.startswith("Selected shortcut")]
    check("SURF-doctor-color-does-not-shift-alignment — ANSI bytes excluded from column width",
          len(colored_lines) == len(plain_lines) == 2
          and [ansi_re.sub("", ln) for ln in colored_lines] == plain_lines
          and any("\033[" in ln for ln in colored_lines),
          f"colored={colored_lines!r} plain={plain_lines!r}")

    # report.py's `planned_changes`/`shared_*` contract (report-contract.md):
    # the renderer must show REAL planned changes on a fresh preview, REAL
    # zero-change counts on an identical reinstall preview, and the
    # automatically-managed guidance-section report — never the retired
    # manual-paste instructions.
    fresh_preview = {"_verb": "add", "dry_run": True, "target": str(pws),
                     "source": DISCOVER_CWD, "selected_items": ["fixmod/goodcomp#fixskill"],
                     "harnesses": ["codex"], "adopted": [], "adopted_sections": [],
                     "released": [], "shared_removed": [],
                     "planned_changes": {
                         "write_files": [".agents/skills/fixskill/SKILL.md"],
                         "delete_files": [], "unchanged_files": [],
                         "write_shared_files": ["AGENTS.md"],
                         "delete_shared_files": [], "unchanged_shared_files": []},
                     "report": {"guidance_sections": ["AGENTS.md"],
                               "guidance_mirror": {"basis": None, "targets": []}},
                     "next": "rbtv install doctor --target " + str(pws)}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_result(fresh_preview)
    fresh_text = buf.getvalue()
    check("SURF-fresh-add-preview-shows-real-planned-changes-in-text",
          "would write 1 file(s)" in fresh_text
          and "would write 1 shared file(s)" in fresh_text
          and "  + .agents/skills/fixskill/SKILL.md" in fresh_text
          and "  ~ AGENTS.md" in fresh_text,
          fresh_text)
    check("SURF-preview-reports-automatic-owned-section-no-manual-paste",
          "will regenerate the automatically managed instruction section "
          "in: AGENTS.md" in fresh_text
          and "D8" not in fresh_text and "Add this block to" not in fresh_text
          and "paste" not in fresh_text.lower(),
          fresh_text)

    reinstall_preview = {**fresh_preview,
                         "planned_changes": {
                             "write_files": [], "delete_files": [],
                             "unchanged_files": [".agents/skills/fixskill/SKILL.md"],
                             "write_shared_files": [], "delete_shared_files": [],
                             "unchanged_shared_files": ["AGENTS.md"]}}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_result(reinstall_preview)
    reinstall_text = buf.getvalue()
    check("SURF-identical-reinstall-preview-shows-zero-changes-in-text",
          "would write 0 file(s), would delete 0 file(s)" in reinstall_text
          and "would write 0 shared file(s), would delete 0 shared file(s)"
          in reinstall_text
          and "2 file(s) already match and stay untouched" in reinstall_text
          and "  + " not in reinstall_text and "  ~ " not in reinstall_text,
          reinstall_text)

    # Preview adoption wording MUST be prospective — a dry run adopts
    # nothing, so it must never claim a takeover already happened.
    adoption_data = {"_verb": "add", "target": str(pws), "source": DISCOVER_CWD,
                     "adopted": ["AGENTS.md"], "adopted_sections": ["CLAUDE.md"],
                     "released": [], "shared_removed": [],
                     "planned_changes": {"write_files": [], "delete_files": [],
                                        "unchanged_files": [],
                                        "write_shared_files": [],
                                        "delete_shared_files": [],
                                        "unchanged_shared_files": []},
                     "report": {}, "next": "rbtv install status"}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_result({**adoption_data, "dry_run": True})
    adoption_preview = buf.getvalue()
    check("SURF-preview-adoption-wording-is-prospective-not-a-completed-claim",
          "would become managed here" in adoption_preview
          and "would adopt its existing owned section only" in adoption_preview
          and "now managed here" not in adoption_preview
          and "\n  ^ CLAUDE.md: adopted its existing owned section only"
          not in adoption_preview,
          adoption_preview)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_result({**adoption_data, "dry_run": False,
                      "written": [], "deleted": [], "skipped": [],
                      "shared_written": [], "shared_deleted": [],
                      "shared_skipped": []})
    adoption_real = buf.getvalue()
    check("SURF-real-adoption-wording-claims-the-completed-takeover",
          "now managed here" in adoption_real
          and "adopted its existing owned section only" in adoption_real
          and "would become managed" not in adoption_real
          and "would adopt" not in adoption_real,
          adoption_real)

    # Every public command's `-h` and every `update` scope's `-h` carries the
    # shared title, argparse's own usage text survives untouched, and root's
    # OWN title string never appears a second time inside a subcommand's help.
    root_text = build_parser().format_help()
    for argv, label in (
        (["list", "-h"], "list"), (["search", "-h"], "search"),
        (["show", "-h"], "show"), (["status", "-h"], "status"),
        (["add", "-h"], "add"), (["remove", "-h"], "remove"),
        (["configure", "-h"], "configure"),
        (["update", "-h"], "update"),
        (["update", "guidance", "-h"], "update guidance"),
        (["update", "scaffolding", "-h"], "update scaffolding"),
        (["update", "all", "-h"], "update all"),
        (["doctor", "-h"], "doctor"),
        (["interactive", "-h"], "interactive"),
        (["selftest", "-h"], "selftest"),
    ):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                main(argv)
            except SystemExit:
                pass
        text = buf.getvalue()
        expected_title = f"RBTV install — {label} help"
        check(f"SURF-help-title-{'-'.join(argv)}",
              text.startswith(expected_title + "\n\n")
              and text.split("\n\n", 1)[1].startswith("usage:")
              and text.count("RBTV install —") == 1
              and root_text.strip() != text.strip(),
              text[:120])

    # Configure's FIRST example must be a complete, copyable first-setup
    # command — first setup requires BOTH --harness and --guidance.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            main(["configure", "-h"])
        except SystemExit:
            pass
    configure_help = buf.getvalue()
    first_example = configure_help.split("Examples:\n", 1)[1].splitlines()[0]
    check("SURF-configure-help-first-example-is-a-complete-first-setup-command",
          "--harness" in first_example and "--guidance" in first_example,
          first_example)

    # The shared refusal title at every plain-text stderr boundary: parser
    # validation, a retired form, a target/command Refuse, and an io-error —
    # JSON stays a single undecorated value throughout.
    for argv in (["set", "--guidance", "none"], ["list", "--limit", "abc"],
                ["show", "no-such-thing-zzz"]):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            main(argv)
        check(f"SURF-refusal-has-shared-title-{'-'.join(argv)}",
              err.getvalue().startswith("RBTV install — refused\n\nREFUSED [")
              and not out.getvalue(),
              err.getvalue())
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            main([*argv, "--json"])
        check(f"SURF-refusal-json-stays-undecorated-{'-'.join(argv)}",
              not err.getvalue() and out.getvalue().strip().startswith("{")
              and "RBTV install" not in out.getvalue(),
              out.getvalue())

    # Owner ruling (content split): guidance copies maintained HUMAN text
    # only, preserving each destination's own generated section unrebuilt;
    # scaffolding regenerates the generated section in EVERY configured
    # file, including a received copy like AGENTS.md; both may write the
    # SAME file. Help text for every scope must say so explicitly, and
    # never make the superseded whole-counterpart-file claim.
    for argv, must_contain in (
        (["update", "-h"], ("CONTENT OWNERSHIP", "SAME instruction file")),
        (["update", "guidance", "-h"],
         ("HUMAN text", "does NOT rebuild that section")),
        (["update", "scaffolding", "-h"],
         ("generated instruction section in EVERY configured",
          "does not copy or synchronize that text from the basis")),
        (["update", "all", "-h"],
         ("the two parts of the SAME file",)),
    ):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                main(argv)
            except SystemExit:
                pass
        text = buf.getvalue()
        check(f"SURF-update-help-states-content-ownership-{'-'.join(argv)}",
              all(phrase in text for phrase in must_contain),
              text)
    for argv in (["update", "-h"], ["update", "guidance", "-h"],
                ["update", "scaffolding", "-h"], ["update", "all", "-h"]):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                main(argv)
            except SystemExit:
                pass
        text = buf.getvalue()
        check(f"SURF-update-help-never-claims-whole-file-untouched-or-copied-"
              f"{'-'.join(argv)}",
              "left untouched" not in text
              and "copies the generated" not in text
              and "copies its generated" not in text,
              text)

    # `_print_guidance`/`_print_guidance_sections` wording: never claim a
    # whole counterpart is untouched, and never claim a destination's own
    # generated section "is preserved as-is" for a scope where that is not
    # actually guaranteed — `_add_mirror` (operations.py) only skips
    # rewriting it when scope == "guidance"; `all`/`add` rebuild it via
    # their own planned claims in the SAME run. `guidance_sections` reads as
    # "regenerated", not "kept"/"preserved".
    #
    # scope="all" fixture (also stands in for `add`'s default scope): the
    # mirror copies maintained text; the destination's own generated
    # section is REBUILT elsewhere in this same run (guidance_sections),
    # never claimed "preserved" here.
    all_scope_data = {"_verb": "update", "scope": "all", "dry_run": True,
                      "target": str(pws), "source": DISCOVER_CWD,
                      "adopted": [], "adopted_sections": [], "released": [],
                      "shared_removed": [],
                      "planned_changes": {"write_files": [], "delete_files": [],
                                         "unchanged_files": [],
                                         "write_shared_files": ["AGENTS.md"],
                                         "delete_shared_files": [],
                                         "unchanged_shared_files": []},
                      "report": {"guidance_sections": ["AGENTS.md"],
                                "guidance_mirror": {"basis": "CLAUDE.md",
                                                    "targets": ["AGENTS.md"],
                                                    "count": 1, "excludes": []}},
                      "next": "rbtv install doctor"}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_result(all_scope_data)
    all_scope_text = buf.getvalue()
    check("SURF-all-scope-guidance-mirror-never-claims-whole-file-copy-or-preserved",
          "maintained text" in all_scope_text
          and "generated sections are not copied from the basis" in all_scope_text
          and "preserved as-is" not in all_scope_text
          and "left untouched" not in all_scope_text,
          all_scope_text)
    check("SURF-all-scope-guidance-sections-wording-says-regenerated-not-preserved",
          "will regenerate the automatically managed instruction section "
          "in: AGENTS.md" in all_scope_text
          and "kept" not in all_scope_text.lower(),
          all_scope_text)

    # scope="guidance" fixture: preservation of the destination's own
    # generated section IS actually guaranteed here, so the message may
    # (and does) say so — and real `update guidance` never regenerates a
    # section (`operations.py` sets `guidance_sections = []` for this
    # scope), so no regeneration claim should print at all.
    guidance_only_data = {**all_scope_data, "scope": "guidance",
                          "report": {"guidance_sections": [],
                                    "guidance_mirror": all_scope_data["report"]
                                    ["guidance_mirror"]}}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_result(guidance_only_data)
    guidance_only_text = buf.getvalue()
    check("SURF-guidance-only-scope-states-destination-section-is-preserved",
          "generated sections are not copied from the basis" in guidance_only_text
          and "each destination's own existing generated instruction "
          "section is preserved as-is by this copy" in guidance_only_text,
          guidance_only_text)
    check("SURF-guidance-only-scope-has-no-sections-and-no-regeneration-claim",
          "regenerate" not in guidance_only_text.lower()
          and "instruction section in:" not in guidance_only_text,
          guidance_only_text)
    ctx.keep(locals())
