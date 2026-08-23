"""The root guidance basis: choosing it, refusing a bad one, and flipping
it.
"""
from __future__ import annotations

import hashlib
import json

from discovery import Refuse

from lib.constants import BASIS_NONE, HARNESSES, STATE_REL
from lib.state import read_state
from lib.operations import do_install, do_uninstall


def the_guidance_mirror(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nD13 — the guidance mirror")
    check("mirror OFF by default: nothing written, nothing recorded",
          not (target / "AGENTS.md").exists()
          and "guidance_basis" not in read_state(target))

    mt = tmp / "workspace4"
    mt.mkdir()
    basis_body = "# The workspace\n\nHand-authored guidance.\n"
    (mt / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
    basis_hash = hashlib.sha256((mt / "CLAUDE.md").read_bytes()).hexdigest()
    do_install(mt, catalog, ["fixmod/goodcomp"], list(HARNESSES),
               dry_run=False, guidance_basis="CLAUDE.md")
    mirrored = (mt / "AGENTS.md").read_text()
    check("mirror generated from the basis",
          mirrored.endswith(basis_body) and "DO NOT EDIT" in mirrored
          and "mirrors CLAUDE.md" in mirrored, mirrored[:120])
    check("the user-authored basis file was NEVER modified",
          hashlib.sha256((mt / "CLAUDE.md").read_bytes()).hexdigest()
          == basis_hash)
    check("the basis choice is persisted",
          read_state(mt).get("guidance_basis") == "CLAUDE.md")
    check("the mirror is booked as an installer-owned file",
          "AGENTS.md" in read_state(mt).get("guidance_files", []))
    # A later run must NOT re-ask and must NOT need the flag again.
    res4 = do_install(mt, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                      dry_run=False)
    check("re-run without the flag still mirrors, and is idempotent",
          res4["written"] == []
          and res4["report"]["guidance_mirror"]["basis"] == "CLAUDE.md",
          str(res4["written"]))
    (mt / "CLAUDE.md").write_text(basis_body + "\nA new line.\n",
                                  encoding="utf-8")
    res4 = do_install(mt, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                      dry_run=False)
    check("an edited basis re-renders the mirror on the next run",
          res4["written"] == ["AGENTS.md"]
          and "A new line." in (mt / "AGENTS.md").read_text(),
          str(res4["written"]))
    check("full uninstall takes the mirror, leaves the basis",
          do_uninstall(mt, catalog, ["fixmod/goodcomp"], dry_run=False)
          and not (mt / "AGENTS.md").exists()
          and (mt / "CLAUDE.md").is_file())
    ctx.keep(locals())


def red_garbage_basis(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nred arm — a garbage basis value refuses")
    for bad_value, where in (("QWEN.md", "flag"), ("../etc", "book")):
        mt2 = tmp / f"workspace5-{where}"
        mt2.mkdir()
        (mt2 / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        kwargs = {"guidance_basis": bad_value} if where == "flag" else {}
        if where == "book":
            (mt2 / STATE_REL).parent.mkdir(parents=True)
            (mt2 / STATE_REL).write_text(
                json.dumps({"schema": 1, "components": {},
                            "shared_claims": [],
                            "guidance_basis": bad_value}),
                encoding="utf-8")
        try:
            do_install(mt2, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                       dry_run=False, **kwargs)
            check(f"garbage basis from the {where} refuses", False,
                  "no refusal raised")
        except Refuse as exc:
            check(f"garbage basis from the {where} refuses",
                  exc.code == "guidance-basis-invalid", exc.code)
            check(f"the {where} refusal wrote nothing",
                  not (mt2 / "AGENTS.md").exists()
                  and not (mt2 / ".claude").exists())
    ctx.keep(locals())


def red_foreign_mirror(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nred arm — a foreign mirror file (old installer's) refuses")
    mt3 = tmp / "workspace6"
    mt3.mkdir()
    (mt3 / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
    (mt3 / "AGENTS.md").write_text("rendered by the OLD installer\n",
                                   encoding="utf-8")
    try:
        do_install(mt3, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                   dry_run=False, guidance_basis="CLAUDE.md")
        check("a foreign AGENTS.md refuses", False, "no refusal raised")
    except Refuse as exc:
        check("a foreign AGENTS.md refuses",
              exc.code == "guidance-mirror-collision"
              and "AGENTS.md" in exc.message,
              f"{exc.code}: {exc.message}")
        # F4 — the generic advice ("move or remove it") would tell the user
        # to delete hand-authored guidance. The mirror message must not.
        check("the mirror collision names the real situation, never "
              "'remove it'",
              "DO NOT delete it" in exc.message
              and "move or remove it" not in exc.message, exc.message)
        check("the foreign mirror is byte-identical after the refusal",
              (mt3 / "AGENTS.md").read_text()
              == "rendered by the OLD installer\n")
    ctx.keep(locals())


def f1_flip_keeps_the_users_file(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nF1 — the basis FLIP never deletes the user's file")
    mt5 = tmp / "workspace7"
    mt5.mkdir()
    (mt5 / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
    do_install(mt5, catalog, ["fixmod/goodcomp"], list(HARNESSES),
               dry_run=False, guidance_basis="CLAUDE.md")
    # The user switches: AGENTS.md becomes the file they author by hand
    # (same NAME the book still carries as our generated mirror), CLAUDE.md
    # goes away.
    authored = "# Authored by hand, under the old mirror's name\n"
    (mt5 / "AGENTS.md").write_text(authored, encoding="utf-8")
    (mt5 / "CLAUDE.md").unlink()
    authored_hash = hashlib.sha256((mt5 / "AGENTS.md").read_bytes()).hexdigest()
    res5 = do_install(mt5, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                      dry_run=False, guidance_basis="AGENTS.md")
    check("the flipped-to basis is NOT in the delete set",
          res5["deleted"] == [], str(res5["deleted"]))
    check("the hand-authored file survives the flip byte-for-byte",
          (mt5 / "AGENTS.md").is_file()
          and hashlib.sha256((mt5 / "AGENTS.md").read_bytes()).hexdigest()
          == authored_hash)
    check("the flip renders the other name from the new basis",
          res5["written"] == ["CLAUDE.md"]
          and authored in (mt5 / "CLAUDE.md").read_text(),
          str(res5["written"]))
    check("the book no longer claims the basis as a generated file",
          "AGENTS.md" not in read_state(mt5)["guidance_files"]
          and "CLAUDE.md" in read_state(mt5)["guidance_files"],
          str(read_state(mt5)["guidance_files"]))
    ctx.keep(locals())


def f2_missing_basis_names_recovery(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nF2 — a missing basis names its recovery, and a flag recovers")
    mt6 = tmp / "workspace8"
    mt6.mkdir()
    (mt6 / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
    do_install(mt6, catalog, ["fixmod/goodcomp"], list(HARNESSES),
               dry_run=False, guidance_basis="CLAUDE.md")
    (mt6 / "CLAUDE.md").unlink()          # basis gone; AGENTS.md remains
    try:
        do_install(mt6, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                   dry_run=False)
        check("a missing basis refuses", False, "no refusal raised")
    except Refuse as exc:
        check("a missing basis refuses",
              exc.code == "guidance-basis-missing", exc.code)
        check("the refusal names BOTH recoveries, in verbs that EXIST",
              "rbtv install set artifact AGENTS.md" in exc.message
              and f"rbtv install set artifact {BASIS_NONE}" in exc.message,
              exc.message)
    res6 = do_install(mt6, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                      dry_run=False, guidance_basis="AGENTS.md")
    check("repointing the basis at the surviving file recovers the run",
          res6["written"] == ["CLAUDE.md"]
          and read_state(mt6)["guidance_basis"] == "AGENTS.md",
          str(res6["written"]))
    ctx.keep(locals())


def f3_uninstall_never_blocked(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nF3 — an uninstall is never blocked by a mirror problem")
    mt7 = tmp / "workspace9"
    mt7.mkdir()
    (mt7 / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
    do_install(mt7, catalog, ["fixmod/goodcomp", "fixmod/codexcomp"],
               list(HARNESSES), dry_run=False, guidance_basis="CLAUDE.md")
    (mt7 / "CLAUDE.md").unlink()          # basis gone AFTER the install
    res7 = do_uninstall(mt7, catalog, ["fixmod/codexcomp"], dry_run=False)
    check("the partial uninstall succeeds with a missing basis",
          res7["ok"] and read_state(mt7)["components"].keys()
          == {"fixmod/goodcomp"}, str(res7))
    check("it reports the skip instead of pretending it mirrored",
          res7["report"]["guidance_mirror"]["skipped"]
          == "guidance-basis-missing",
          str(res7["report"]["guidance_mirror"]))
    check("neither root guidance file was deleted by the skip",
          (mt7 / "AGENTS.md").is_file() and "AGENTS.md" not in res7["deleted"],
          str(res7["deleted"]))
    ctx.keep(locals())


def f6_non_utf8_basis(ctx) -> None:
    check, skip, tmp, tree, target, shadowed = (
        ctx.check, ctx.skip, ctx.tmp, ctx.tree, ctx.target, ctx.shadowed)
    (catalog, data, legacy, expect, basis_body, mirrors_on_disk, mtr,
     _mk, rf, pws) = ctx.frame()

    print("\nF6 — a non-UTF-8 basis refuses cleanly")
    mt8 = tmp / "workspace10"
    mt8.mkdir()
    (mt8 / "CLAUDE.md").write_bytes(b"\xff\xfe not text at all\x00")
    try:
        do_install(mt8, catalog, ["fixmod/goodcomp"], list(HARNESSES),
                   dry_run=False, guidance_basis="CLAUDE.md")
        check("a non-UTF-8 basis refuses", False, "no refusal raised")
    except Refuse as exc:
        check("a non-UTF-8 basis refuses",
              exc.code == "guidance-basis-unreadable", exc.code)
        check("the unreadable-basis refusal wrote nothing",
              not (mt8 / "AGENTS.md").exists()
              and not (mt8 / ".claude").exists())
    ctx.keep(locals())
