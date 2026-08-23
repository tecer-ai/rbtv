"""How the installer tells its own files apart from everyone else's."""
from __future__ import annotations

import contextlib
import io

from discovery import Refuse

from lib.constants import FENCE_ID, LEGACY_PREFIX, MANAGED_BANNER, STATE_REL
from lib.claims import _claim_id
from lib.state import read_state, rec_files, write_state
from lib.operations import do_install, do_uninstall
from lib.report import print_result


def the_marker_is_ownership(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nM — D12: the marker is what says `this file is mine`")
    mk = tmp / "ws-marker"
    mk.mkdir()
    rule_rel = ".claude/rules/fixrule.md"
    (mk / rule_rel).parent.mkdir(parents=True)
    # An UNBOOKED file at a planned path, carrying OUR marker: provably a
    # run of ours (a lost book, a copied workspace) — adopted, not refused.
    (mk / rule_rel).write_text(MANAGED_BANNER + "# a stale body\n",
                               encoding="utf-8")
    resm = do_install(mk, catalog, ["fixmod/goodcomp"], ["claude"],
                      dry_run=False)
    check("M1 — a marked file outside the book is ADOPTED and regenerated",
          resm["adopted"] == [rule_rel]
          and "a stale body" not in (mk / rule_rel).read_text()
          and rule_rel in rec_files(read_state(mk)["components"][
              "fixmod/goodcomp"]),
          str(resm.get("adopted")))

    # The other side: the same path, hand-authored, no marker → refused.
    mk2 = tmp / "ws-marker-hand"
    (mk2 / ".claude/rules").mkdir(parents=True)
    hand_rule = "# my own rule\n"
    (mk2 / rule_rel).write_text(hand_rule, encoding="utf-8")
    try:
        do_install(mk2, catalog, ["fixmod/goodcomp"], ["claude"],
                   dry_run=False)
        check("M2 — an UNMARKED file at a planned path refuses", False,
              "no refusal raised — it was overwritten")
    except Refuse as exc:
        check("M2 — an UNMARKED file at a planned path refuses",
              exc.code == "collision"
              and (mk2 / rule_rel).read_text() == hand_rule, exc.code)

    # RELEASE — a booked file a human took over (marker gone) is dropped
    # from the book, never deleted.
    (mk / rule_rel).write_text("# I own this now\n", encoding="utf-8")
    resm2 = do_uninstall(mk, catalog, ["fixmod/goodcomp"], dry_run=False)
    check("M3 — a booked file whose marker is gone is RELEASED, not deleted",
          resm2["released"] == [rule_rel]
          and (mk / rule_rel).read_text() == "# I own this now\n"
          and rule_rel not in resm2["deleted"], str(resm2["released"]))

    # MIGRATION — files a pre-marker run minted under the `rbtv2-` prefix
    # carry no marker at all; the legacy-name clause keeps them ours, so
    # the first unprefixed run cleans them up instead of orphaning them.
    mk3 = tmp / "ws-legacy"
    mk3.mkdir()
    do_install(mk3, catalog, ["fixmod/goodcomp"], ["claude"], dry_run=False)
    legacy_rel = f".claude/rules/{LEGACY_PREFIX}fixrule.md"
    (mk3 / legacy_rel).write_text("# THE RULE\n\nAlways do the thing.\n",
                                  encoding="utf-8")
    st3 = read_state(mk3)
    st3["components"]["fixmod/goodcomp"]["files"] = (
        sorted(rec_files(st3["components"]["fixmod/goodcomp"]))
        + [legacy_rel])
    write_state(mk3, st3)
    resm3 = do_install(mk3, catalog, ["fixmod/goodcomp"], ["claude"],
                       dry_run=False)
    check("M4 — yesterday's rbtv2- file is deleted as stale, not orphaned",
          resm3["deleted"] == [legacy_rel]
          and not (mk3 / legacy_rel).exists()
          and resm3["released"] == [], str(resm3["deleted"]))
    ctx.keep(locals())


def gitignore_block(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nG — D14: the .gitignore block keeps our artifacts out of git")
    gi = tmp / "ws-gitignore"
    gi.mkdir()
    (gi / ".git").mkdir()
    (gi / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
    (gi / ".gitignore").write_text("# theirs\nnode_modules/\n",
                                   encoding="utf-8")
    rgi = do_install(gi, catalog, ["fixmod/goodcomp"], ["claude", "codex"],
                     dry_run=False, guidance_basis="CLAUDE.md")
    body = (gi / ".gitignore").read_text()
    booked = sorted(rec_files(read_state(gi)["components"]["fixmod/goodcomp"]))
    check("G1 — every per-component artifact and the book are listed",
          all(rel in body for rel in booked)
          and STATE_REL.as_posix() in body
          and rgi["report"]["gitignore"]["count"] == len(booked) + 1,
          str(rgi["report"]["gitignore"]))
    check("G1 — the guidance mirror is NOT listed (workspace content)",
          "\nAGENTS.md" not in body, body)
    check("G1 — the foreign lines survive, and the block is fenced",
          "node_modules/" in body and f"# {FENCE_ID}:start" in body
          and f"# {FENCE_ID}:end" in body, body)
    check("G1 — the claim is booked like any other shared-file claim",
          _claim_id(".gitignore", None)
          in read_state(gi)["shared_claims"],
          str(read_state(gi)["shared_claims"]))
    check("G2 — a re-run is idempotent, block and all",
          do_install(gi, catalog, ["fixmod/goodcomp"],
                     ["claude", "codex"], dry_run=False)["written"] == []
          and (gi / ".gitignore").read_text() == body)
    # A shrinking set shrinks the block — the whole point of D14, and
    # since D16 a narrower harness set really is a narrowing.
    rgi2 = do_install(gi, catalog, ["fixmod/goodcomp"], ["claude"],
                      dry_run=False)
    gi_body = (gi / ".gitignore").read_text()
    check("G3 — a narrowed harness set drops the dropped harness's files "
          "from disk AND from the block",
          ".claude/rules/fixrule.md" in gi_body
          and ".agents/behavior-rules/fixrule.md" not in gi_body
          and ".agents/behavior-rules/fixrule.md" in rgi2["deleted"]
          and not (gi / ".agents/behavior-rules/fixrule.md").exists(),
          str(rgi2["deleted"]))
    # …and widening it back restores them.
    rgi3 = do_install(gi, catalog, ["fixmod/goodcomp"], ["claude", "codex"],
                      dry_run=False)
    check("G3b — widening it back re-writes them",
          ".agents/behavior-rules/fixrule.md"
          in (gi / ".gitignore").read_text()
          and (gi / ".agents/behavior-rules/fixrule.md").exists()
          and rgi3["deleted"] == [], str(rgi3["deleted"]))
    do_uninstall(gi, catalog, ["fixmod/goodcomp"], dry_run=False)
    check("G4 — the last uninstall takes the block, leaves their lines",
          (gi / ".gitignore").read_text() == "# theirs\nnode_modules/\n",
          (gi / ".gitignore").read_text())

    ng = tmp / "ws-not-a-repo"
    ng.mkdir()
    rng = do_install(ng, catalog, ["fixmod/goodcomp"], ["claude"],
                     dry_run=False)
    check("G5 — off a git repo, no .gitignore is ever minted",
          not (ng / ".gitignore").exists()
          and rng["report"]["gitignore"] == {"claimed": False,
                                             "reason": "not a git repo"},
          str(rng["report"]["gitignore"]))

    gf = tmp / "ws-foreign-fence"
    gf.mkdir()
    (gf / ".git").mkdir()
    foreign = f"# {FENCE_ID}:start\nsomething-else\n# {FENCE_ID}:end\n"
    (gf / ".gitignore").write_text(foreign, encoding="utf-8")
    try:
        do_install(gf, catalog, ["fixmod/goodcomp"], ["claude"],
                   dry_run=False)
        check("G6 — a foreign rbtv2 fence refuses", False, "no refusal")
    except Refuse as exc:
        check("G6 — a foreign rbtv2 fence refuses",
              exc.code == "collision"
              and ".gitignore" in exc.message
              and (gf / ".gitignore").read_text() == foreign, exc.code)

    gt = tmp / "ws-tracked"
    gt.mkdir()
    import subprocess
    if subprocess.run(["git", "-C", str(gt), "init", "-q"],
                      capture_output=True).returncode == 0:
        (gt / ".claude" / "rules").mkdir(parents=True)
        (gt / ".claude/rules/fixrule.md").write_text("theirs\n",
                                                     encoding="utf-8")
        subprocess.run(["git", "-C", str(gt), "add",
                        ".claude/rules/fixrule.md"], capture_output=True)
        (gt / ".claude/rules/fixrule.md").unlink()
        rgt = do_install(gt, catalog, ["fixmod/goodcomp"], ["claude"],
                         dry_run=False)
        check("G7 — a path git ALREADY TRACKS is reported, not silently "
              "ignored",
              rgt["report"]["gitignore"]["tracked"]
              == [".claude/rules/fixrule.md"],
              str(rgt["report"]["gitignore"]))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_result(rgt)
        check("G7 — and the human is told, with the fix",
              "ALREADY TRACKED" in buf.getvalue()
              and "git rm --cached" in buf.getvalue(), buf.getvalue()[-400:])
    ctx.keep(locals())
