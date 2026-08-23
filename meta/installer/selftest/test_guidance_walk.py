"""The guidance mirror across the whole tree: recursion, adoption, harness
keying, forced reads."""
from __future__ import annotations

import contextlib
import hashlib
import io

from discovery import Refuse

from lib.constants import FENCE_ID, HARNESSES, LEGACY_PREFIX
from lib.guidance import strip_generated_banner
from lib.state import read_state, write_state
from lib.operations import do_install, do_uninstall
from lib.report import print_result


def r1_recursive_walk(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nR1 — the mirror is RECURSIVE, and the walk skips what it must")
    mtr = tmp / "workspace11"
    bodies = {
        "CLAUDE.md": "# root\n\nRoot guidance.\n",
        "sub/CLAUDE.md": "# sub\n\nSub guidance.\n",
        "sub/deep/CLAUDE.md": "# deep\n\nDeep guidance.\n",
        "vendor/CLAUDE.md": "# a nested repo's own guidance\n",
        ".rbtv/goals/g1/CLAUDE.md": "# a scaffold-owned goal router\n",
        "node_modules/pkg/CLAUDE.md": "# vendored junk\n",
        "skipme/CLAUDE.md": "# excluded by flag\n",
        "sub/notes.md": "# not guidance\n",
    }
    for rel, body in bodies.items():
        (mtr / rel).parent.mkdir(parents=True, exist_ok=True)
        (mtr / rel).write_text(body, encoding="utf-8")
    (mtr / "vendor" / ".git").mkdir()      # nested git repo
    base_hashes = {rel: hashlib.sha256((mtr / rel).read_bytes()).hexdigest()
                   for rel in bodies}
    resr = do_install(mtr, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                      dry_run=False, guidance_basis="CLAUDE.md",
                      guidance_excludes=["skipme"])
    mirrors_on_disk = sorted(p.relative_to(mtr).as_posix()
                             for p in mtr.rglob("AGENTS.md"))
    check("one mirror beside every eligible CLAUDE.md, and only those",
          mirrors_on_disk == ["AGENTS.md", "sub/AGENTS.md",
                              "sub/deep/AGENTS.md"], str(mirrors_on_disk))
    check("a nested git repo's guidance is NEVER touched",
          not (mtr / "vendor/AGENTS.md").exists())
    check(".rbtv/goals is carved out (both routers are scaffold-owned)",
          not (mtr / ".rbtv/goals/g1/AGENTS.md").exists())
    check("node_modules is never walked",
          not (mtr / "node_modules/pkg/AGENTS.md").exists())
    check("--guidance-exclude skips its subtree and is persisted",
          not (mtr / "skipme/AGENTS.md").exists()
          and read_state(mtr)["guidance_excludes"] == ["skipme"],
          str(read_state(mtr).get("guidance_excludes")))
    check("each mirror is generated from ITS OWN directory's basis",
          (mtr / "sub/deep/AGENTS.md").read_text().endswith(
              bodies["sub/deep/CLAUDE.md"])
          and "mirrors sub/deep/CLAUDE.md"
          in (mtr / "sub/deep/AGENTS.md").read_text()
          and (mtr / "sub/AGENTS.md").read_text().endswith(
              bodies["sub/CLAUDE.md"]))
    check("EVERY basis file is byte-identical after the run",
          all(hashlib.sha256((mtr / rel).read_bytes()).hexdigest() == h
              for rel, h in base_hashes.items()))
    check("every nested mirror is booked",
          read_state(mtr)["guidance_files"] == sorted(
              ["AGENTS.md", "sub/AGENTS.md", "sub/deep/AGENTS.md"]),
          str(read_state(mtr)["guidance_files"]))
    check("the report counts the mirrors it rendered",
          resr["report"]["guidance_mirror"]["count"] == 3,
          str(resr["report"]["guidance_mirror"]))
    resr2 = do_install(mtr, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                       dry_run=False)
    check("a recursive re-run is idempotent, flags and all",
          resr2["written"] == [] and resr2["deleted"] == []
          and resr2["report"]["guidance_mirror"]["count"] == 3,
          str(resr2["written"] + resr2["deleted"]))
    ctx.keep(locals())


def r2_flip_protects_every_dir(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nR2 — the basis flip protects EVERY directory's basis, not the "
          "root's alone")
    for rel in ("CLAUDE.md", "sub/CLAUDE.md", "sub/deep/CLAUDE.md"):
        (mtr / rel).unlink()              # the user now authors AGENTS.md
    (mtr / "sub/AGENTS.md").write_text(
        (mtr / "sub/AGENTS.md").read_text() + "\nHand-edited after the flip.\n",
        encoding="utf-8")
    flipped = {rel: hashlib.sha256((mtr / rel).read_bytes()).hexdigest()
               for rel in mirrors_on_disk}
    resr3 = do_install(mtr, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                       dry_run=False, guidance_basis="AGENTS.md")
    check("NO basis is deleted by the flip, at any depth",
          resr3["deleted"] == [], str(resr3["deleted"]))
    check("every flipped-to basis survives byte-for-byte",
          all(hashlib.sha256((mtr / rel).read_bytes()).hexdigest() == h
              for rel, h in flipped.items()))
    check("the flip renders the other name at every depth",
          sorted(resr3["written"]) == ["CLAUDE.md", "sub/CLAUDE.md",
                                       "sub/deep/CLAUDE.md"],
          str(resr3["written"]))
    check("a generated banner is STRIPPED, never stacked (7.623a)",
          (mtr / "sub/CLAUDE.md").read_text().count(
              "GENERATED by install.py") == 1
          and "Hand-edited after the flip."
          in (mtr / "sub/CLAUDE.md").read_text()
          and resr3["report"]["guidance_mirror"]["banner_stripped"]
          == ["AGENTS.md", "sub/AGENTS.md", "sub/deep/AGENTS.md"],
          str(resr3["report"]["guidance_mirror"].get("banner_stripped")))
    resr4 = do_install(mtr, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                       dry_run=False)
    check("re-mirroring a mirror is stable — no banner growth per run",
          resr4["written"] == [], str(resr4["written"]))
    check("full uninstall takes every nested mirror and no basis",
          do_uninstall(mtr, catalog, ["fixmod/goodcomp"], dry_run=False)
          and sorted(p.relative_to(mtr).as_posix()
                     for p in mtr.rglob("CLAUDE.md"))
          == [".rbtv/goals/g1/CLAUDE.md", "node_modules/pkg/CLAUDE.md",
              "skipme/CLAUDE.md", "vendor/CLAUDE.md"]
          and sorted(p.relative_to(mtr).as_posix()
                     for p in mtr.rglob("AGENTS.md"))
          == ["AGENTS.md", "sub/AGENTS.md", "sub/deep/AGENTS.md"],
          str(sorted(p.relative_to(mtr).as_posix()
                     for p in mtr.rglob("*.md"))))
    ctx.keep(locals())


def r3_deep_foreign_mirror(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nR3 — a foreign mirror DEEP in the tree refuses too")
    mtd = tmp / "workspace12"
    (mtd / "a" / "b").mkdir(parents=True)
    (mtd / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
    (mtd / "a/b/CLAUDE.md").write_text("# deep\n", encoding="utf-8")
    (mtd / "a/b/AGENTS.md").write_text("rendered by the OLD installer\n",
                                       encoding="utf-8")
    try:
        do_install(mtd, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                   dry_run=False, guidance_basis="CLAUDE.md")
        check("a foreign nested AGENTS.md refuses", False, "no refusal")
    except Refuse as exc:
        check("a foreign nested AGENTS.md refuses",
              exc.code == "guidance-mirror-collision"
              and "a/b/AGENTS.md" in exc.message, f"{exc.code}: {exc.message}")
        check("the deep refusal wrote nothing, anywhere",
              not (mtd / "AGENTS.md").exists()
              and (mtd / "a/b/AGENTS.md").read_text()
              == "rendered by the OLD installer\n"
              and not (mtd / ".claude").exists())
    ctx.keep(locals())


def r4_adoption(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nR4 — ADOPTION: a PROVABLY-generated foreign mirror is taken "
          "over; an unproven one is still refused")
    mta = tmp / "workspace13"
    (mta / "deep").mkdir(parents=True)
    (mta / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
    (mta / "deep/CLAUDE.md").write_text("# deep\n\nDeep guidance.\n",
                                        encoding="utf-8")
    # Byte-for-byte the shape install.py's model_mirror renders.
    old_mirror = (
        "<!-- AUTO-GENERATED MIRROR — DO NOT EDIT. Generated by rbtv "
        "mirror.py from CLAUDE.md. -->\n\n"
        "> [!danger] GENERATED FILE — DO NOT EDIT\n"
        "> This `AGENTS.md` is an auto-generated mirror of `CLAUDE.md`.\n"
        "\n---\n\n# Stale body from a month ago\n")
    (mta / "AGENTS.md").write_text(old_mirror, encoding="utf-8")
    (mta / "deep/AGENTS.md").write_text(
        old_mirror.replace("CLAUDE.md", "deep/CLAUDE.md"), encoding="utf-8")
    basis_hashes = {rel: hashlib.sha256((mta / rel).read_bytes()).hexdigest()
                    for rel in ("CLAUDE.md", "deep/CLAUDE.md")}
    resa = do_install(mta, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                      dry_run=False, guidance_basis="CLAUDE.md")
    check("the old installer's mirror is ADOPTED, not refused, at any depth",
          resa["adopted"] == ["AGENTS.md", "deep/AGENTS.md"],
          str(resa.get("adopted")))
    check("an adopted mirror is regenerated fresh from its own basis",
          {"AGENTS.md", "deep/AGENTS.md"} <= set(resa["written"])
          and (mta / "AGENTS.md").read_text().endswith(basis_body)
          and "Stale body from a month ago"
          not in (mta / "AGENTS.md").read_text(),
          str(resa["written"]))
    check("the adopted file carries exactly ONE banner — ours",
          (mta / "AGENTS.md").read_text().count("DO NOT EDIT") == 1
          and "AUTO-GENERATED MIRROR" not in (mta / "AGENTS.md").read_text())
    check("adopted mirrors are booked, so uninstall can take them back",
          {"AGENTS.md", "deep/AGENTS.md"}
          <= set(read_state(mta)["guidance_files"]),
          str(read_state(mta)["guidance_files"]))
    check("adoption never touches a basis, at any depth",
          all(hashlib.sha256((mta / rel).read_bytes()).hexdigest() == h
              for rel, h in basis_hashes.items()))
    check("the run AFTER an adoption is idempotent",
          do_install(mta, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                     dry_run=False)["written"] == [])
    # The other side of the boundary: no banner → no proof → still refused.
    mtb = tmp / "workspace14"
    (mtb / "deep").mkdir(parents=True)
    (mtb / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
    (mtb / "deep/CLAUDE.md").write_text("# deep\n", encoding="utf-8")
    hand = "# AGENTS.md I wrote by hand\n\nDo not clobber this.\n"
    (mtb / "deep/AGENTS.md").write_text(hand, encoding="utf-8")
    try:
        do_install(mtb, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                   dry_run=False, guidance_basis="CLAUDE.md")
        check("a HAND-AUTHORED mirror-named file is never adopted", False,
              "no refusal raised — it was adopted")
    except Refuse as exc:
        check("a HAND-AUTHORED mirror-named file is never adopted",
              exc.code == "guidance-mirror-collision"
              and "deep/AGENTS.md" in exc.message, f"{exc.code}")
        check("the hand-authored file is byte-identical after the refusal",
              (mtb / "deep/AGENTS.md").read_text() == hand
              and not (mtb / "AGENTS.md").exists())

    # The banner carries the installer's filename, and that filename changed on
    # 2026-08-23. Files minted before then sit in every workspace installed
    # until that day, so GENERATED_MARKERS keeps the OLD spelling too — this
    # arm is what stops that retained marker rotting into an untested branch.
    legacy_banner = ("<!-- GENERATED by install2.py — DO NOT EDIT.\n"
                     "     AGENTS.md mirrors CLAUDE.md. -->\n\n# body\n")
    stripped_legacy, was_banner = strip_generated_banner(legacy_banner)
    check("a PRE-RENAME generated banner is still recognized and stripped",
          was_banner and stripped_legacy.strip() == "# body",
          repr(stripped_legacy))
    ctx.keep(locals())


def h_harness_keyed(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nH — the mirror is HARNESS-KEYED (CMP-12 agents.md row)")
    def _mk(name: str, harnesses: list[str], basis: str,
            extra: dict | None = None):
        """A fresh workspace with a root + nested basis, installed for
        *harnesses* only. Returns (path, result)."""
        ws = tmp / name
        (ws / "sub").mkdir(parents=True)
        (ws / basis).write_text(basis_body, encoding="utf-8")
        (ws / "sub" / basis).write_text("# sub\n\nSub guidance.\n",
                                        encoding="utf-8")
        for rel, body in (extra or {}).items():
            (ws / rel).parent.mkdir(parents=True, exist_ok=True)
            (ws / rel).write_text(body, encoding="utf-8")
        return ws, do_install(ws, catalog, ["fixmod/goodcomp"], harnesses,
                              dry_run=False, guidance_basis=basis)

    h1, r1 = _mk("ws-claude-only", ["claude"], "CLAUDE.md")
    h1_hash = hashlib.sha256((h1 / "CLAUDE.md").read_bytes()).hexdigest()
    check("H1 — claude-only + basis CLAUDE.md writes NO mirror, anywhere",
          not list(h1.rglob("AGENTS.md"))
          and r1["report"]["guidance_mirror"]["targets"] == []
          and r1["report"]["guidance_mirror"]["count"] == 0
          and read_state(h1)["guidance_files"] == [],
          str(r1["report"]["guidance_mirror"]))
    check("H1 — and the basis is untouched, at every depth",
          hashlib.sha256((h1 / "CLAUDE.md").read_bytes()).hexdigest()
          == h1_hash
          and (h1 / "sub/CLAUDE.md").read_text() == "# sub\n\nSub "
          "guidance.\n")
    check("H1 — the block claude needs is REPORTED for the basis, "
          "never written",
          sorted(r1["report"]["guidance_manual"]) == ["CLAUDE.md"]
          and "Step 0" not in r1["report"]["guidance_manual"]["CLAUDE.md"],
          str(sorted(r1["report"]["guidance_manual"])))
    check("H1 — a claude-only re-run stays a no-op",
          do_install(h1, catalog, ["fixmod/goodcomp"], ["claude"],
                     dry_run=False)["written"] == [])

    h2, r2 = _mk("ws-codex-only", ["codex"], "CLAUDE.md")
    check("H2 — selecting codex renders AGENTS.md, recursively",
          sorted(q.relative_to(h2).as_posix()
                 for q in h2.rglob("AGENTS.md"))
          == ["AGENTS.md", "sub/AGENTS.md"]
          and r2["report"]["guidance_mirror"]["targets"] == ["AGENTS.md"],
          str(r2["report"]["guidance_mirror"]))
    check("H2 — the forced Step-0 read is IN the generated guidance file, "
          "at the ROOT only (F4)",
          "Step 0" in (h2 / "AGENTS.md").read_text()
          and "`.agents/behavior-rules/fixrule.md`"
          in (h2 / "AGENTS.md").read_text()
          and "fixguide" in (h2 / "AGENTS.md").read_text()
          and "Step 0" not in (h2 / "sub/AGENTS.md").read_text(),
          (h2 / "AGENTS.md").read_text()[:400])
    check("H2 — the generated body still ends with the basis body",
          (h2 / "AGENTS.md").read_text().endswith(basis_body))

    h3, r3 = _mk("ws-agents-share", ["codex", "opencode"],
                 "CLAUDE.md")
    check("H3 — remaining AGENTS.md harnesses get ONE file per folder",
          r3["report"]["guidance_mirror"]["targets"] == ["AGENTS.md"]
          and r3["report"]["guidance_mirror"]["count"] == 2,
          str(r3["report"]["guidance_mirror"]))

    h4, r4 = _mk("ws-no-forced", ["claude", "opencode"], "CLAUDE.md")
    check("H4 — opencode takes NO forced read (CMP-12 gives it no separate "
          "rule type; it reads .claude/)",
          (h4 / "AGENTS.md").is_file()
          and "Step 0" not in (h4 / "AGENTS.md").read_text()
          and not (h4 / ".agents/behavior-rules").exists()
          and (h4 / ".claude/rules/fixrule.md").is_file(),
          str(sorted(q.relative_to(h4).as_posix()
                     for q in h4.rglob("*") if q.is_file())))

    h5, r5 = _mk("ws-basis-agents", ["claude", "codex"], "AGENTS.md")
    check("H5 — basis AGENTS.md + claude installed renders CLAUDE.md",
          r5["report"]["guidance_mirror"]["targets"] == ["CLAUDE.md"]
          and (h5 / "CLAUDE.md").is_file()
          and "Step 0" not in (h5 / "CLAUDE.md").read_text()
          and "Step 0" in r5["report"]["guidance_manual"]["AGENTS.md"],
          str(r5["report"]["guidance_mirror"]))
    ctx.keep(locals())


def h6_retired_index_cleaned(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nH6 — the retired exposure index is cleaned by the machinery")
    h6, _ = _mk("ws-retire", ["claude", "codex"], "CLAUDE.md")
    stale_rel = f".agents/{LEGACY_PREFIX}exposure.md"
    (h6 / stale_rel).parent.mkdir(parents=True, exist_ok=True)
    (h6 / stale_rel).write_text("# the old invented index\n",
                                encoding="utf-8")
    st = read_state(h6)                    # book it, as the old code did
    st["guidance_files"] = sorted(st["guidance_files"] + [stale_rel])
    write_state(h6, st)
    r6 = do_install(h6, catalog, ["fixmod/goodcomp"], ["claude", "codex"],
                    dry_run=False)
    check("H6 — an existing rbtv2-exposure.md is DELETED by the next run",
          stale_rel in r6["deleted"] and not (h6 / stale_rel).exists()
          and stale_rel not in read_state(h6)["guidance_files"],
          str(r6["deleted"]))
    ctx.keep(locals())


def h7_block_never_stacks(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nH7 — the exposure block never stacks across a basis flip")
    h7, _ = _mk("ws-flip-block", ["claude", "codex"], "CLAUDE.md")
    (h7 / "CLAUDE.md").unlink()
    (h7 / "sub/CLAUDE.md").unlink()
    r7 = do_install(h7, catalog, ["fixmod/goodcomp"], ["claude", "codex"],
                    dry_run=False, guidance_basis="AGENTS.md")
    # The flipped-to basis carried OUR AGENTS.md block (codex's, with the
    # Step-0). Mirroring it back must strip that one and render CLAUDE.md's
    # own block instead — exactly one fence, and no forced read, because
    # claude auto-injects `.claude/rules/`.
    check("H7 — the flipped file's fenced block is stripped, not stacked",
          (h7 / "CLAUDE.md").read_text().count(f"{FENCE_ID}:start") == 1
          and (h7 / "CLAUDE.md").read_text().count("Step 0") == 0
          and "Step 0" in r7["report"]["guidance_manual"]["AGENTS.md"],
          (h7 / "CLAUDE.md").read_text()[:400])
    check("H7 — and the flipped run is idempotent",
          do_install(h7, catalog, ["fixmod/goodcomp"], ["claude", "codex"],
                     dry_run=False)["written"] == [])
    ctx.keep(locals())


def rf1_forced_read_step_zero(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nRF1 — Step-0 names ONLY the rule files that harness reads")
    rf = tmp / "ws-mixed-harness"
    rf.mkdir()
    (rf / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
    # goodcomp's rule lands under `.claude/rules/` ONLY (claude-only);
    # codexcomp then arrives for codex, whose forced read must enumerate
    # its OWN `.agents/behavior-rules/` file and nothing else.
    do_install(rf, catalog, ["fixmod/goodcomp"], ["claude"],
               dry_run=False, guidance_basis="CLAUDE.md")
    rrf = do_install(rf, catalog, ["fixmod/codexcomp"], ["codex"],
                     dry_run=False)
    agents_md = (rf / "AGENTS.md").read_text()
    check("RF1 — the claude-only rule is NOT enumerated to codex",
          "fixrule" not in agents_md
          and ".claude/rules" not in agents_md,
          agents_md[:600])
    check("RF1 — codex's own rule IS enumerated, at the path written",
          "Step 0" in agents_md
          and "`.agents/behavior-rules/codexrule.md`" in agents_md
          and (rf / ".agents/behavior-rules/codexrule.md").is_file(),
          agents_md[:600])
    check("RF1 — every path the Step-0 names EXISTS on disk",
          all((rf / line.split("`")[1]).is_file()
              for line in agents_md.splitlines()
              if line[:2] in ("1.", "2.", "3.") and "`" in line),
          agents_md[:600])
    check("RF1 — and the unrealized path was never created",
          not (rf / ".agents/behavior-rules/fixrule.md").exists()
          and (rf / ".claude/rules/fixrule.md").is_file())
    ctx.keep(locals())


def rf2_dry_run_reports_the_block(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nRF2 — a DRY RUN still reports the block the human must place")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_result(do_install(rf, catalog, ["fixmod/codexcomp"],
                                ["codex"], dry_run=True))
    out = buf.getvalue()
    check("RF2 — the dry run prints the guidance-mirror summary",
          "guidance mirror:" in out and "would generate" in out, out[-600:])
    check("RF2 — and the manual block, flush (never a 4-space code block)",
          "Add this block to CLAUDE.md" in out
          and "\n# rbtv exposure" in out
          and "\n    # rbtv exposure" not in out, out[-600:])
    ctx.keep(locals())


def rf3_flip_debanners_the_basis(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nRF3 — a flip into an empty-target config de-banners the basis")
    fb = tmp / "ws-flip-empty"
    fb.mkdir()
    (fb / "AGENTS.md").write_text(basis_body, encoding="utf-8")
    do_install(fb, catalog, ["fixmod/goodcomp"], ["claude"],
               dry_run=False, guidance_basis="AGENTS.md")
    check("RF3 — setup: claude's CLAUDE.md was generated from AGENTS.md",
          "GENERATED by install.py" in (fb / "CLAUDE.md").read_text())
    rfb = do_install(fb, catalog, ["fixmod/goodcomp"], ["claude"],
                     dry_run=False, guidance_basis="CLAUDE.md")
    cleaned = (fb / "CLAUDE.md").read_text()
    check("RF3 — the file the human now authors carries NO stale banner",
          "GENERATED by install.py" not in cleaned
          and "DO NOT EDIT" not in cleaned
          and f"{FENCE_ID}:start" not in cleaned
          and rfb["report"]["guidance_debannered"] == ["CLAUDE.md"],
          cleaned[:400])
    check("RF3 — the guidance BODY survives the cleaning",
          cleaned.rstrip() == basis_body.rstrip(), repr(cleaned[:200]))
    check("RF3 — a hand-authored basis is never rewritten by the cleaner",
          do_install(fb, catalog, ["fixmod/goodcomp"], ["claude"],
                     dry_run=False)["report"]["guidance_debannered"] == []
          and (fb / "CLAUDE.md").read_text() == cleaned)
    ctx.keep(locals())
