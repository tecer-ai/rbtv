"""Workspace settings and local update scopes."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from discovery import Refuse

from lib.constants import FENCE_ID, STATE_REL
from lib.state import read_state
from lib.operations import do_install, do_uninstall
from lib.parser import build_parser
from lib.commands import _HANDLERS, main


def workspace_settings(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    catalog, _, _, _, basis_body, *_ = ctx.frame()
    print("\nW — workspace setup and scoped local updates")

    def workspace(name: str) -> Path:
        target = tmp / name
        target.mkdir()
        (target / "CLAUDE.md").write_text(basis_body, encoding="utf-8")
        return target

    def run(target: Path, *argv: str,
            source: dict | None = None) -> tuple[int | str, str]:
        args = build_parser().parse_args(list(argv))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                rc = _HANDLERS[args.verb](args, target,
                                          catalog if source is None else source, [])
                return rc, output.getvalue()
            except Refuse as exc:
                return exc.code, exc.message

    fresh = workspace("ws-configure-fresh")
    check("W1 — first configure requires both settings",
          run(fresh, "configure", "--harness", "codex")[0] == "setup-required"
          and not (fresh / STATE_REL).exists())
    check("W2 — configure initializes an empty selection",
          run(fresh, "configure", "--harness", "claude,codex",
              "--guidance", "CLAUDE.md")[0] == 0
          and read_state(fresh)["components"] == {}
          and read_state(fresh)["harnesses"] == ["claude", "codex"])
    check("W3 — add inherits configured settings",
          run(fresh, "add", "fixmod/goodcomp#fixskill")[0] == 0
          and set(read_state(fresh)["components"]["fixmod/goodcomp"]["parts"])
          == {"fixskill"})
    code, message = run(fresh, "add", "fixmod/goodcomp#fixskill",
                        "--harness", "claude")
    check("W4 — changed add setting teaches configure",
          code == "setting-locked" and "configure --harness" in message)

    skill = fresh / ".claude/skills/fixskill/SKILL.md"
    mirror = fresh / "AGENTS.md"
    check("W5 — all update preserves partial selection",
          run(fresh, "update", "all")[0] == 0
          and set(read_state(fresh)["components"]["fixmod/goodcomp"]["parts"])
          == {"fixskill"})
    correct_skill = skill.read_bytes()
    correct_mirror = mirror.read_bytes()
    mirror.write_text("stale mirror\n", encoding="utf-8")
    check("W6 — guidance update leaves scaffolding alone",
          run(fresh, "update", "guidance")[0] == 0
          and mirror.read_bytes() == correct_mirror
          and skill.read_bytes() == correct_skill)
    skill.write_text("stale skill\n", encoding="utf-8")
    check("W7 — scaffolding update leaves guidance alone",
          run(fresh, "update", "scaffolding")[0] == 0
          and skill.read_bytes() == correct_skill
          and mirror.read_bytes() == correct_mirror)
    skill.write_text("stale skill\n", encoding="utf-8")
    mirror.write_text("stale mirror\n", encoding="utf-8")
    book_before = (fresh / STATE_REL).read_bytes()
    check("W8 — all update previews are write-free",
          all(run(fresh, "update", scope, "--dry-run")[0] == 0
              for scope in ("guidance", "scaffolding", "all"))
          and skill.read_text(encoding="utf-8") == "stale skill\n"
          and mirror.read_text(encoding="utf-8") == "stale mirror\n"
          and (fresh / STATE_REL).read_bytes() == book_before)
    check("W9 — all update repairs both scopes",
          run(fresh, "update", "all")[0] == 0
          and skill.read_bytes() == correct_skill
          and mirror.read_bytes() == correct_mirror)

    missing = workspace("ws-update-missing-basis")
    check("W10 — direct first add accepts setup flags",
          run(missing, "add", "fixmod/goodcomp#fixskill", "--harness", "codex",
              "--guidance", "CLAUDE.md")[0] == 0)
    (missing / "CLAUDE.md").unlink()
    target_skill = missing / ".agents/skills/fixskill/SKILL.md"
    target_skill.write_text("stale skill\n", encoding="utf-8")
    check("W11 — all validates guidance before scaffolding writes",
          run(missing, "update", "all")[0] == "guidance-basis-missing"
          and target_skill.read_text(encoding="utf-8") == "stale skill\n")

    (fresh / "skipme").mkdir()
    (fresh / "skipme/CLAUDE.md").write_text("nested\n", encoding="utf-8")
    check("W12 — guidance exclusion uses public noun",
          run(fresh, "add", "guidance", "exclude", "skipme")[0] == 0
          and read_state(fresh)["guidance_excludes"] == ["skipme"]
          and not (fresh / "skipme/AGENTS.md").exists())
    check("W13 — removing exclusion restores mirror",
          run(fresh, "rm", "guidance", "exclude", "skipme")[0] == 0
          and read_state(fresh)["guidance_excludes"] == []
          and (fresh / "skipme/AGENTS.md").exists())

    virgin = workspace("ws-configure-virgin")
    check("W14 — update requires configuration",
          run(virgin, "update", "all")[0] == "workspace-unrecorded")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        retired = [main([name, "--target", str(fresh)])
                   for name in ("set", "dupe-artifacts")]
    check("W15 — retired commands refuse", retired == [2, 2])
    check("W16 — saved book keeps internal method schema",
          read_state(fresh)["components"]["fixmod/goodcomp"]["parts"]
          ["fixskill"]["method"] == "skill")

    codex_skill = fresh / ".agents/skills/fixskill/SKILL.md"
    check("W17 — removing one harness removes only its generated files",
          codex_skill.exists()
          and run(fresh, "rm", "harness", "codex")[0] == 0
          and not codex_skill.exists()
          and not (fresh / "AGENTS.md").exists()
          and read_state(fresh)["harnesses"] == ["claude"])
    check("W18 — the last harness cannot be removed as a setting",
          run(fresh, "rm", "harness", "claude")[0] == "harness-list-empty"
          and read_state(fresh)["harnesses"] == ["claude"])
    check("W19 — adding the harness restores files and counterpart",
          run(fresh, "add", "harness", "codex")[0] == 0
          and codex_skill.exists()
          and (fresh / "AGENTS.md").exists())
    stable_book = (fresh / STATE_REL).read_bytes()
    check("W20 — no-op and dry-run settings preserve book bytes",
          run(fresh, "add", "harness", "codex")[0] == 0
          and run(fresh, "rm", "harness", "codex", "--dry-run")[0] == 0
          and (fresh / STATE_REL).read_bytes() == stable_book)
    check("W21 — setting noun with component selector refuses before writes",
          run(fresh, "add", "harness", "codex", "-c", "fixmod/goodcomp")[0]
          == "noun-with-selectors"
          and (fresh / STATE_REL).read_bytes() == stable_book)

    flip = workspace("ws-configure-flip")
    (flip / "AGENTS.md").write_text("hand-authored\n", encoding="utf-8")
    check("W22 — basis flip cannot overwrite an owner-authored counterpart",
          run(flip, "configure", "--harness", "claude,codex",
              "--guidance", "CLAUDE.md")[0] == "guidance-mirror-collision"
          and (flip / "AGENTS.md").read_text(encoding="utf-8")
          == "hand-authored\n"
          and not (flip / STATE_REL).exists())

    exclude = workspace("ws-configure-exclusions")
    run(exclude, "configure", "--harness", "claude,codex",
        "--guidance", "CLAUDE.md")
    for name in ("first", "second"):
        (exclude / name).mkdir()
        (exclude / name / "CLAUDE.md").write_text("nested\n", encoding="utf-8")
        run(exclude, "add", "guidance", "exclude", name)
    check("W23 — a second exclusion joins rather than replaces the first",
          read_state(exclude)["guidance_excludes"] == ["first", "second"]
          and not (exclude / "first/AGENTS.md").exists()
          and not (exclude / "second/AGENTS.md").exists())
    check("W24 — removing one exclusion retains the other",
          run(exclude, "rm", "guidance", "exclude", "first")[0] == 0
          and read_state(exclude)["guidance_excludes"] == ["second"]
          and (exclude / "first/AGENTS.md").exists()
          and not (exclude / "second/AGENTS.md").exists())

    legacy = workspace("ws-configure-legacy")
    do_install(legacy, catalog, ["fixmod/goodcomp", "fixmod/codexcomp"],
               ["claude", "codex"], dry_run=False, guidance_basis="CLAUDE.md")
    old = json.loads((legacy / STATE_REL).read_text(encoding="utf-8"))
    old.pop("harnesses")
    old["components"]["fixmod/goodcomp"]["harnesses"] = ["claude"]
    old["components"]["fixmod/codexcomp"]["harnesses"] = ["codex"]
    (legacy / STATE_REL).write_text(json.dumps(old), encoding="utf-8")
    check("W25 — old per-component settings migrate by union",
          read_state(legacy)["harnesses"] == ["claude", "codex"])

    gone = workspace("ws-guidance-source-missing")
    run(gone, "add", "fixmod/goodcomp#fixskill", "--harness", "claude,codex",
        "--guidance", "CLAUDE.md")
    (gone / "CLAUDE.md").write_text("New owner guidance\n", encoding="utf-8")
    absent_source = {cid: comp for cid, comp in catalog.items()
                     if cid != "fixmod/goodcomp"}
    code, _ = run(gone, "update", "guidance", source=absent_source)
    check("W26 — vanished source selection does not block guidance copy",
          code == 0 and "New owner guidance" in
          (gone / "AGENTS.md").read_text(encoding="utf-8")
          and "fixmod/goodcomp" in read_state(gone)["components"])
    check("W27 — vanished source blocks scaffolding regeneration",
          run(gone, "update", "scaffolding", source=absent_source)[0]
          == "component-vanished")

    no_copy = workspace("ws-guidance-none-rule")
    (no_copy / "AGENTS.md").write_text("Owner instructions\n", encoding="utf-8")
    check("W28 — no guidance copying still installs the Codex rule section",
          run(no_copy, "add", "fixmod/codexcomp#codexrule",
              "--harness", "codex", "--guidance", "none")[0] == 0
          and "Owner instructions" in
          (no_copy / "AGENTS.md").read_text(encoding="utf-8")
          and "Step 0" in (no_copy / "AGENTS.md").read_text(encoding="utf-8")
          and (no_copy / ".agents/behavior-rules/codexrule.md").exists())
    check("W29 — removing the last rule keeps owner instructions",
          run(no_copy, "remove", "fixmod/codexcomp#codexrule")[0] == 0
          and (no_copy / "AGENTS.md").read_text(encoding="utf-8")
          == "Owner instructions\n")

    legacy_section = workspace("ws-legacy-owner-section")
    start, end = (f"<!-- {FENCE_ID}:start -->",
                  f"<!-- {FENCE_ID}:end -->")
    owner_prefix = b"# Owner start\r\n\r\n"
    owner_suffix = b"\r\n\r\nOwner end\r\n"
    (legacy_section / "CLAUDE.md").write_bytes(
        owner_prefix + f"{start}\r\nold block\r\n{end}".encode("utf-8")
        + owner_suffix)
    adopted = do_install(legacy_section, catalog, ["fixmod/goodcomp"],
                         ["claude"], dry_run=False, guidance_basis="none",
                         parts=["fixmod/goodcomp#fixguide"])
    updated = (legacy_section / "CLAUDE.md").read_bytes()
    check("W30 — valid legacy section is adopted without owning the whole file",
          adopted["adopted_sections"] == ["CLAUDE.md"]
          and "CLAUDE.md" not in adopted["adopted"]
          and updated.startswith(owner_prefix)
          and updated.endswith(owner_suffix)
          and updated.count(start.encode("utf-8")) == 1
          and b"fixguide" in updated,
          str(adopted["adopted_sections"]))
    check("W31 — adopted section is idempotent",
          do_install(legacy_section, catalog, ["fixmod/goodcomp"],
                     ["claude"], dry_run=False)["shared_written"] == []
          and (legacy_section / "CLAUDE.md").read_bytes() == updated)

    for label, body in (
            ("incomplete", f"Owner\n{start}\nunfinished\n"),
            ("duplicate", f"Owner\n{start}\na\n{end}\n{start}\nb\n{end}\n"),
            ("reversed", f"Owner\n{end}\n{start}\n")):
        malformed = workspace("ws-legacy-" + label)
        (malformed / "CLAUDE.md").write_text(body, encoding="utf-8")
        try:
            do_install(malformed, catalog, ["fixmod/goodcomp"], ["claude"],
                       dry_run=False, guidance_basis="none",
                       parts=["fixmod/goodcomp#fixguide"])
        except Refuse as exc:
            code = exc.code
        else:
            code = None
        check(f"W32-{label} — malformed section refuses before writes",
              code == "guidance-section-malformed"
              and (malformed / "CLAUDE.md").read_text(encoding="utf-8") == body
              and not (malformed / STATE_REL).exists()
              and not (malformed / ".claude").exists())

    whitespace = workspace("ws-owner-whitespace")
    owner_bytes = b"# Owner\r\nKeep two spaces  \r\n\r\n"
    (whitespace / "AGENTS.md").write_bytes(owner_bytes)
    do_install(whitespace, catalog, ["fixmod/codexcomp"], ["codex"],
               dry_run=False, guidance_basis="none",
               parts=["fixmod/codexcomp#codexrule"])
    inserted = (whitespace / "AGENTS.md").read_bytes()
    check("W33 — first managed section retains outside CRLF and trailing blanks",
          inserted.startswith(owner_bytes)
          and inserted.count(start.encode("utf-8")) == 1,
          repr(inserted))
    do_uninstall(whitespace, catalog, ["fixmod/codexcomp"], dry_run=False,
                 parts=["fixmod/codexcomp#codexrule"])
    check("W34 — final section removal restores exact owner bytes",
          (whitespace / "AGENTS.md").read_bytes() == owner_bytes,
          repr((whitespace / "AGENTS.md").read_bytes()))

    stale_fence = workspace("ws-malformed-booked-section")
    do_install(stale_fence, catalog, ["fixmod/codexcomp"], ["codex"],
               dry_run=False, guidance_basis="none",
               parts=["fixmod/codexcomp#codexrule"])
    booked_bytes = (stale_fence / STATE_REL).read_bytes()
    (stale_fence / "AGENTS.md").write_text(
        f"Owner\n{start}\nfirst\n{end}\n{start}\nsecond\n{end}\n",
        encoding="utf-8")
    try:
        do_uninstall(stale_fence, catalog, ["fixmod/codexcomp"], dry_run=False,
                     parts=["fixmod/codexcomp#codexrule"])
    except Refuse as exc:
        stale_code = exc.code
    else:
        stale_code = None
    check("W35 — malformed booked section refuses removal before writes",
          stale_code == "guidance-section-malformed"
          and (stale_fence / STATE_REL).read_bytes() == booked_bytes
          and (stale_fence / ".agents/behavior-rules/codexrule.md").exists())

    only_space = workspace("ws-whitespace-only-owner")
    whitespace_bytes = b"\r\n  \r\n"
    (only_space / "AGENTS.md").write_bytes(whitespace_bytes)
    do_install(only_space, catalog, ["fixmod/codexcomp"], ["codex"],
               dry_run=False, guidance_basis="none",
               parts=["fixmod/codexcomp#codexrule"])
    do_uninstall(only_space, catalog, ["fixmod/codexcomp"], dry_run=False,
                 parts=["fixmod/codexcomp#codexrule"])
    check("W36 — whitespace-only owner file survives final section removal",
          (only_space / "AGENTS.md").read_bytes() == whitespace_bytes)

    split = workspace("ws-content-split")
    (split / "nested").mkdir()
    (split / "nested/CLAUDE.md").write_text("Nested source v1\n", encoding="utf-8")
    check("W37 — fresh add creates the counterpart's own generated section",
          run(split, "add", "fixmod/codexcomp#codexrule", "--harness",
              "claude,codex", "--guidance", "CLAUDE.md")[0] == 0
          and "Step 0" in (split / "AGENTS.md").read_text(encoding="utf-8")
          and "Step 0" not in (split / "CLAUDE.md").read_text(encoding="utf-8"))

    def replace_section(text: str, body: str) -> str:
        return text.split(start, 1)[0] + start + "\n" + body + "\n" + end \
            + text.split(end, 1)[1]

    (split / "CLAUDE.md").write_text("Source human v2\n", encoding="utf-8")
    (split / "AGENTS.md").write_text(
        replace_section((split / "AGENTS.md").read_text(encoding="utf-8"),
                        "Stale destination section"), encoding="utf-8")
    (split / "nested/CLAUDE.md").write_text(
        "Nested source v2\n" + start + "\nWrong source section\n" + end + "\n",
        encoding="utf-8")
    (split / "nested/AGENTS.md").write_text(
        replace_section((split / "nested/AGENTS.md").read_text(encoding="utf-8")
                        + "\n" + start + "\nOld nested section\n" + end + "\n",
                        "Old nested section"), encoding="utf-8")
    rule_before = (split / ".agents/behavior-rules/codexrule.md").read_bytes()
    guide_preview = (split / "AGENTS.md").read_bytes()
    book_preview = (split / STATE_REL).read_bytes()
    check("W38 — guidance preview is write-free even with stale sections",
          run(split, "update", "guidance", "--dry-run")[0] == 0
          and (split / "AGENTS.md").read_bytes() == guide_preview
          and (split / STATE_REL).read_bytes() == book_preview)
    check("W39 — guidance copies human text and retains destination sections",
          run(split, "update", "guidance")[0] == 0
          and "Source human v2" in (split / "AGENTS.md").read_text(encoding="utf-8")
          and "Stale destination section" in
          (split / "AGENTS.md").read_text(encoding="utf-8")
          and "Step 0" not in (split / "AGENTS.md").read_text(encoding="utf-8")
          and "Nested source v2" in
          (split / "nested/AGENTS.md").read_text(encoding="utf-8")
          and "Old nested section" in
          (split / "nested/AGENTS.md").read_text(encoding="utf-8")
          and "Wrong source section" not in
          (split / "nested/AGENTS.md").read_text(encoding="utf-8")
          and (split / ".agents/behavior-rules/codexrule.md").read_bytes()
          == rule_before)

    (split / "AGENTS.md").write_text(
        replace_section("Destination human only\n" + start
                        + "\nStale destination section\n" + end + "\n",
                        "Stale destination section"), encoding="utf-8")
    check("W40 — scaffolding refreshes counterpart section, keeps its human text",
          run(split, "update", "scaffolding")[0] == 0
          and (split / "AGENTS.md").read_text(encoding="utf-8")
          .startswith("Destination human only\n")
          and "Step 0" in (split / "AGENTS.md").read_text(encoding="utf-8")
          and "Stale destination section" not in
          (split / "AGENTS.md").read_text(encoding="utf-8")
          and (split / "CLAUDE.md").read_text(encoding="utf-8")
          == "Source human v2\n")
    (split / "CLAUDE.md").write_text("Source human v3\n", encoding="utf-8")
    (split / "AGENTS.md").write_text(
        replace_section((split / "AGENTS.md").read_text(encoding="utf-8"),
                        "Stale again"), encoding="utf-8")
    check("W41 — all copies human text and regenerates counterpart section",
          run(split, "update", "all")[0] == 0
          and "Source human v3" in (split / "AGENTS.md").read_text(encoding="utf-8")
          and "Step 0" in (split / "AGENTS.md").read_text(encoding="utf-8")
          and "Stale again" not in (split / "AGENTS.md").read_text(encoding="utf-8")
          and "Old nested section" in
          (split / "nested/AGENTS.md").read_text(encoding="utf-8")
          and "Wrong source section" not in
          (split / "nested/AGENTS.md").read_text(encoding="utf-8"))
    same = do_install(split, catalog, ["fixmod/codexcomp"], ["claude", "codex"],
                      dry_run=True, scope="all")
    check("W42 — identical all preview plans no file changes",
          not any(same["planned_changes"][key] for key in
                  ("write_files", "delete_files", "write_shared_files",
                   "delete_shared_files")), str(same["planned_changes"]))

    (split / "AGENTS.md").write_text("Owner\n" + start + "\nBroken\n",
                                       encoding="utf-8")
    malformed_before = (split / STATE_REL).read_bytes()
    check("W43 — malformed counterpart section blocks guidance without writes",
          run(split, "update", "guidance")[0] == "guidance-section-malformed"
          and (split / STATE_REL).read_bytes() == malformed_before
          and (split / "AGENTS.md").read_text(encoding="utf-8")
          == "Owner\n" + start + "\nBroken\n")
