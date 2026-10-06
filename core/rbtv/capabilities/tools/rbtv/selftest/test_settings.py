"""Installation settings and local update scopes."""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
from pathlib import Path

from discovery import Refuse

from lib.constants import FENCE_ID, STATE_REL
from lib.state import read_state, write_state
from lib.operations import do_install, do_uninstall
from lib.parser import build_parser
from lib.commands import _HANDLERS, main
from lib.doctor import do_doctor
from lib.agents import update_agent


def installation_settings(ctx) -> None:
    check, tmp = ctx.check, ctx.tmp
    catalog, _, _, _, basis_body, *_ = ctx.frame()
    print("\nW — installation setup and scoped local updates")

    def installation(name: str) -> Path:
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

    fresh = installation("ws-configure-fresh")
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
          and set(read_state(fresh)["components"]["fixmod/goodcomp"]["units"])
          == {"fixskill"})
    code, message = run(fresh, "add", "fixmod/goodcomp#fixskill",
                        "--harness", "claude")
    check("W4 — changed add setting teaches configure",
          code == "setting-locked" and "configure --harness" in message)

    skill = fresh / ".claude/skills/fixskill/SKILL.md"
    mirror = fresh / "AGENTS.md"
    check("W5 — all update preserves partial selection",
          run(fresh, "update", "all")[0] == 0
          and set(read_state(fresh)["components"]["fixmod/goodcomp"]["units"])
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

    missing = installation("ws-update-missing-basis")
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

    virgin = installation("ws-configure-virgin")
    check("W14 — update requires configuration",
          run(virgin, "update", "all")[0] == "installation-unrecorded")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        retired = [main([name, "--target", str(fresh)])
                   for name in ("set", "dupe-artifacts")]
    check("W15 — retired commands refuse", retired == [2, 2])
    check("W16 — saved book keeps internal method schema",
          read_state(fresh)["components"]["fixmod/goodcomp"]["units"]
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

    lifecycle = installation("ws-configure-lifecycle")
    check("W21a — root harness changes retain ownership through update, add, remove and doctor",
          run(lifecycle, "add", "fixmod/goodcomp#fixskill", "--harness", "claude",
              "--guidance", "none")[0] == 0
          and run(lifecycle, "configure", "--harness", "codex")[0] == 0
          and run(lifecycle, "update", "all")[0] == 0
          and run(lifecycle, "add", "fixmod/goodcomp#fixrule")[0] == 0
          and run(lifecycle, "remove", "fixmod/goodcomp#fixrule")[0] == 0
          and bool(read_state(lifecycle)["shared_claims"])
          and do_doctor(lifecycle, "fixture", catalog, [], ctx.tree,
                        lifecycle / ".rbtv/mirror")["ok"],
          str(read_state(lifecycle)))

    flip = installation("ws-configure-flip")
    (flip / "AGENTS.md").write_text("hand-authored\n", encoding="utf-8")
    check("W22 — basis flip cannot overwrite an owner-authored counterpart",
          run(flip, "configure", "--harness", "claude,codex",
              "--guidance", "CLAUDE.md")[0] == "guidance-mirror-collision"
          and (flip / "AGENTS.md").read_text(encoding="utf-8")
          == "hand-authored\n"
          and not (flip / STATE_REL).exists())

    exclude = installation("ws-configure-exclusions")
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

    legacy = installation("ws-configure-legacy")
    do_install(legacy, catalog, ["fixmod/goodcomp", "fixmod/codexcomp"],
               ["claude", "codex"], dry_run=False, guidance_basis="CLAUDE.md")
    old = json.loads((legacy / STATE_REL).read_text(encoding="utf-8"))
    old.pop("harnesses")
    old["components"]["fixmod/goodcomp"]["harnesses"] = ["claude"]
    old["components"]["fixmod/codexcomp"]["harnesses"] = ["codex"]
    (legacy / STATE_REL).write_text(json.dumps(old), encoding="utf-8")
    check("W25 — old per-component settings migrate by union",
          read_state(legacy)["harnesses"] == ["claude", "codex"])

    gone = installation("ws-guidance-source-missing")
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
    code, _ = run(gone, "update", "scaffolding", source=absent_source)
    check("W27 — scaffolding removes a vanished source selection",
          code == 0 and "fixmod/goodcomp" not in read_state(gone)["components"]
          and not (gone / ".claude/skills/fixskill/SKILL.md").exists())

    rule_start = f"<!-- {FENCE_ID}:start rule fixmod/codexcomp#codexrule -->"
    rule_end = f"<!-- {FENCE_ID}:end rule fixmod/codexcomp#codexrule -->"

    no_copy = installation("ws-guidance-none-rule")
    (no_copy / "AGENTS.md").write_text("Owner instructions\n", encoding="utf-8")
    check("W28 — no guidance copying still installs the Codex rule section",
          run(no_copy, "add", "fixmod/codexcomp#codexrule",
              "--harness", "codex", "--guidance", "none")[0] == 0
          and "Owner instructions" in
          (no_copy / "AGENTS.md").read_text(encoding="utf-8")
          and rule_start in (no_copy / "AGENTS.md").read_text(encoding="utf-8")
          and "# CODEX RULE" in (no_copy / "AGENTS.md").read_text(encoding="utf-8")
          and not (no_copy / ".agents/behavior-rules").exists())
    check("W29 — removing the last rule keeps owner instructions",
          run(no_copy, "remove", "fixmod/codexcomp#codexrule")[0] == 0
          and (no_copy / "AGENTS.md").read_text(encoding="utf-8")
          == "Owner instructions\n")

    start, end = (f"<!-- {FENCE_ID}:start -->",
                  f"<!-- {FENCE_ID}:end -->")
    # A 0.2 install booked an unlabeled section (the Codex "Step 0" rule list).
    # Nothing writes it any more, so the next install takes it back.
    legacy_section = installation("ws-legacy-step0")
    owner_prefix = b"# Owner start\r\n\r\n"
    owner_suffix = b"\r\n\r\nOwner end\r\n"
    do_install(legacy_section, catalog, ["fixmod/codexcomp"], ["codex"],
               dry_run=False, guidance_basis="none",
               parts=["fixmod/codexcomp#codexrule"])
    (legacy_section / "AGENTS.md").write_bytes(
        owner_prefix + f"{start}\r\nStep 0 list\r\n{end}".encode("utf-8")
        + owner_suffix)
    book = json.loads((legacy_section / STATE_REL).read_text(encoding="utf-8"))
    book["shared_claims"] = sorted(set(book["shared_claims"]) | {"AGENTS.md::#block"})
    (legacy_section / STATE_REL).write_text(json.dumps(book), encoding="utf-8")
    do_install(legacy_section, catalog, ["fixmod/codexcomp"], ["codex"],
               dry_run=False, parts=["fixmod/codexcomp#codexrule"])
    updated = (legacy_section / "AGENTS.md").read_bytes()
    check("W30 — a booked 0.2 Step 0 section is taken back on the next install",
          updated.startswith(owner_prefix)
          and b"Step 0 list" not in updated
          and updated.count(start.encode("utf-8")) == 0
          and rule_start.encode("utf-8") in updated
          and "AGENTS.md::#block" not in read_state(legacy_section)["shared_claims"],
          repr(updated))
    check("W31 — and the run after it is idempotent",
          do_install(legacy_section, catalog, ["fixmod/codexcomp"],
                     ["codex"], dry_run=False)["shared_written"] == []
          and (legacy_section / "AGENTS.md").read_bytes() == updated)

    whitespace = installation("ws-owner-whitespace")
    owner_bytes = b"# Owner\r\nKeep two spaces  \r\n\r\n"
    (whitespace / "AGENTS.md").write_bytes(owner_bytes)
    do_install(whitespace, catalog, ["fixmod/codexcomp"], ["codex"],
               dry_run=False, guidance_basis="none",
               parts=["fixmod/codexcomp#codexrule"])
    inserted = (whitespace / "AGENTS.md").read_bytes()
    check("W33 — first managed section retains outside CRLF and trailing blanks",
          inserted.startswith(owner_bytes)
          and inserted.count(rule_start.encode("utf-8")) == 1,
          repr(inserted))
    do_uninstall(whitespace, catalog, ["fixmod/codexcomp"], dry_run=False,
                 parts=["fixmod/codexcomp#codexrule"])
    check("W34 — final section removal restores exact owner bytes",
          (whitespace / "AGENTS.md").read_bytes() == owner_bytes,
          repr((whitespace / "AGENTS.md").read_bytes()))

    only_space = installation("ws-whitespace-only-owner")
    whitespace_bytes = b"\r\n  \r\n"
    (only_space / "AGENTS.md").write_bytes(whitespace_bytes)
    do_install(only_space, catalog, ["fixmod/codexcomp"], ["codex"],
               dry_run=False, guidance_basis="none",
               parts=["fixmod/codexcomp#codexrule"])
    do_uninstall(only_space, catalog, ["fixmod/codexcomp"], dry_run=False,
                 parts=["fixmod/codexcomp#codexrule"])
    check("W36 — whitespace-only owner file survives final section removal",
          (only_space / "AGENTS.md").read_bytes() == whitespace_bytes)

    split = installation("ws-content-split")
    (split / "nested").mkdir()
    (split / "nested/CLAUDE.md").write_text("Nested source v1\n", encoding="utf-8")
    check("W37 — fresh add puts the rule section in AGENTS.md only",
          run(split, "add", "fixmod/codexcomp#codexrule", "--harness",
              "claude,codex", "--guidance", "CLAUDE.md")[0] == 0
          and rule_start in (split / "AGENTS.md").read_text(encoding="utf-8")
          and rule_start not in (split / "CLAUDE.md").read_text(encoding="utf-8"))

    def replace_section(text: str, body: str) -> str:
        return text.split(start, 1)[0] + start + "\n" + body + "\n" + end \
            + text.split(end, 1)[1]

    def replace_rule(text: str, body: str) -> str:
        return text.split(rule_start, 1)[0] + rule_start + "\n" + body + "\n" \
            + rule_end + text.split(rule_end, 1)[1]

    (split / "CLAUDE.md").write_text("Source human v2\n", encoding="utf-8")
    (split / "AGENTS.md").write_text(
        replace_rule((split / "AGENTS.md").read_text(encoding="utf-8"),
                     "Stale destination section"), encoding="utf-8")
    (split / "nested/CLAUDE.md").write_text(
        "Nested source v2\n" + start + "\nWrong source section\n" + end + "\n",
        encoding="utf-8")
    (split / "nested/AGENTS.md").write_text(
        replace_section((split / "nested/AGENTS.md").read_text(encoding="utf-8")
                        + "\n" + start + "\nOld nested section\n" + end + "\n",
                        "Old nested section"), encoding="utf-8")
    rule_before = (split / ".claude/rules/codexrule.md").read_bytes()
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
          and "# CODEX RULE" not in (split / "AGENTS.md").read_text(encoding="utf-8")
          and "Nested source v2" in
          (split / "nested/AGENTS.md").read_text(encoding="utf-8")
          and "Old nested section" in
          (split / "nested/AGENTS.md").read_text(encoding="utf-8")
          and "Wrong source section" not in
          (split / "nested/AGENTS.md").read_text(encoding="utf-8")
          and (split / ".claude/rules/codexrule.md").read_bytes()
          == rule_before,
          (split / "AGENTS.md").read_text(encoding="utf-8")
          + "|NESTED|" + (split / "nested/AGENTS.md").read_text(encoding="utf-8"))

    (split / "AGENTS.md").write_text(
        "Destination human only\n" + rule_start
        + "\nStale destination section\n" + rule_end + "\n", encoding="utf-8")
    check("W40 — scaffolding refreshes the rule section, keeps its human text",
          run(split, "update", "scaffolding")[0] == 0
          and (split / "AGENTS.md").read_text(encoding="utf-8")
          .startswith("Destination human only\n")
          and "# CODEX RULE" in (split / "AGENTS.md").read_text(encoding="utf-8")
          and "Stale destination section" not in
          (split / "AGENTS.md").read_text(encoding="utf-8")
          and (split / "CLAUDE.md").read_text(encoding="utf-8")
          == "Source human v2\n")
    (split / "CLAUDE.md").write_text("Source human v3\n", encoding="utf-8")
    (split / "AGENTS.md").write_text(
        replace_rule((split / "AGENTS.md").read_text(encoding="utf-8"),
                     "Stale again"), encoding="utf-8")
    check("W41 — all copies human text and regenerates the rule section",
          run(split, "update", "all")[0] == 0
          and "Source human v3" in (split / "AGENTS.md").read_text(encoding="utf-8")
          and "# CODEX RULE" in (split / "AGENTS.md").read_text(encoding="utf-8")
          and "Stale again" not in (split / "AGENTS.md").read_text(encoding="utf-8")
          and "Old nested section" in
          (split / "nested/AGENTS.md").read_text(encoding="utf-8")
          and "Wrong source section" not in
          (split / "nested/AGENTS.md").read_text(encoding="utf-8"),
          (split / "AGENTS.md").read_text(encoding="utf-8"))

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


def file_selection_sync(ctx) -> None:
    """A portable selected-file list reconciles root folders, not agents."""
    check, tmp, tree = ctx.check, ctx.tmp, ctx.tree
    catalog = ctx.frame()[0]
    print("\nW44 — selected files reconcile copied and hand-edited records")

    def home(name: str) -> Path:
        path = tmp / name
        path.mkdir()
        return path

    def run(target: Path, *argv: str) -> tuple[int | str, str]:
        args = build_parser().parse_args(list(argv))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                return _HANDLERS[args.verb](args, target, catalog, []), output.getvalue()
            except Refuse as exc:
                return exc.code, exc.message

    a, b, c = home("ws-files-a"), home("ws-files-b"), home("ws-files-c")
    for target in (a, b):
        run(target, "add", "fixskill", "fixrule", "--harness", "claude",
            "--guidance", "none")
    check("W44 — add and remove maintain full selected ids",
          run(a, "remove", "fixrule")[0] == 0
          and read_state(a)["files"] == ["fixmod/goodcomp#fixskill"])
    book = (a / STATE_REL).read_bytes()
    (b / STATE_REL).write_bytes(book)
    preview = run(b, "update", "all", "--dry-run", "--details")
    check("W44 — copied record previews and removes a stray marked file",
          preview[0] == 0 and ".claude/rules/fixrule.md" in preview[1]
          and run(b, "update", "all")[0] == 0
          and not (b / ".claude/rules/fixrule.md").exists()
          and do_doctor(b, "fixture", catalog, [], tree, b / ".rbtv/mirror")["ok"])
    (c / STATE_REL).parent.mkdir(parents=True)
    (c / STATE_REL).write_bytes(book)
    check("W45 — copied record generates into an empty folder",
          run(c, "update", "all")[0] == 0
          and (c / ".claude/skills/fixskill/SKILL.md").is_file()
          and do_doctor(c, "fixture", catalog, [], tree, c / ".rbtv/mirror")["ok"])

    hand = home("ws-files-hand")
    run(hand, "add", "fixskill", "fixrule", "--harness", "claude", "--guidance", "none")
    state = read_state(hand)
    state["files"] = ["fixmod/goodcomp#fixskill"]
    write_state(hand, state)
    check("W46 — a hand deletion from files removes its generated files",
          run(hand, "update", "all")[0] == 0
          and not (hand / ".claude/rules/fixrule.md").exists())
    state = read_state(hand)
    state["files"].append("fixmod/goodcomp#fixrule")
    write_state(hand, state)
    check("W46 — a valid hand-added file is generated",
          run(hand, "update", "all")[0] == 0
          and (hand / ".claude/rules/fixrule.md").is_file())
    user_file = hand / ".claude/rules/user.md"
    user_file.write_text("author text\n", encoding="utf-8")
    run(hand, "remove", "fixrule")
    check("W47 — an unmarked neighbouring file is never removed",
          run(hand, "update", "all")[0] == 0
          and user_file.read_text(encoding="utf-8") == "author text\n")

    guidance = home("ws-files-guidance")
    run(guidance, "add", "fixskill", "fixrule", "--harness", "claude", "--guidance", "none")
    state = read_state(guidance)
    state["files"] = ["fixmod/goodcomp#fixskill"]
    write_state(guidance, state)
    check("W48 — update guidance does not reconcile generated files",
          run(guidance, "update", "guidance")[0] == 0
          and (guidance / ".claude/rules/fixrule.md").is_file())

    fence_a, fence_b = home("ws-files-fence-a"), home("ws-files-fence-b")
    for target in (fence_a, fence_b):
        do_install(target, catalog, ["fixmod/codexcomp"], ["codex"],
                   dry_run=False, guidance_basis="none", parts=["codexrule"])
        state = read_state(target)
        state["files"] = ["fixmod/codexcomp#codexrule"]
        write_state(target, state)
    state = read_state(fence_a)
    state["files"] = []
    write_state(fence_a, state)
    (fence_b / STATE_REL).write_bytes((fence_a / STATE_REL).read_bytes())
    check("W49 — copied record removes an unbooked fenced shared section",
          run(fence_b, "update", "all")[0] == 0
          and (not (fence_b / "AGENTS.md").exists() or
               "rule fixmod/codexcomp#codexrule" not in
               (fence_b / "AGENTS.md").read_text(encoding="utf-8")))

    def foreign_fences(home: Path) -> dict[Path, bytes]:
        label = "rule fixmod/codexcomp#codexrule"
        quoted = (f"quoted text\n<!-- rbtv:start {label} -->\nquoted\n"
                  f"<!-- rbtv:end {label} -->\nmore text\n")
        docs = home / "docs/deep/transcript.md"
        nested = home / "tools/repo/template.md"
        docs.parent.mkdir(parents=True)
        nested.parent.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(nested.parent)], check=True,
                       capture_output=True)
        docs.write_text(quoted, encoding="utf-8")
        nested.write_text(quoted, encoding="utf-8")
        backup = home / "backup/AGENTS.md"
        backup.parent.mkdir(parents=True)
        backup.write_bytes((home / "AGENTS.md").read_bytes())
        return {path: path.read_bytes() for path in (docs, backup, nested)}

    bounded = home("ws-files-fence-bounded")
    do_install(bounded, catalog, ["fixmod/codexcomp"], ["codex"],
               dry_run=False, guidance_basis="none", parts=["codexrule"])
    root_foreign = foreign_fences(bounded)
    state = read_state(bounded)
    state["files"] = []
    write_state(bounded, state)
    root_preview = run(bounded, "update", "all", "--dry-run", "--details")
    root_real = run(bounded, "update", "all")
    root_stale_released = not (bounded / "AGENTS.md").exists()

    agent_root = home("ws-files-fence-agent-root")
    agent = agent_root / ".rbtv/agents/scout"
    agent.mkdir(parents=True)
    (agent / "agent.md").write_text("---\nname: scout\n---\n\nScout.\n",
                                     encoding="utf-8")
    (agent / "agent.json").write_text(json.dumps({
        "name": "scout", "description": "Scout.", "harness": "codex",
        "model": "c1", "effort": "high",
        "files": ["fixmod/codexcomp#codexrule"], "packs": []}) + "\n",
                                     encoding="utf-8")
    update_agent(agent_root, "scout", "all", catalog, False)
    agent_foreign = foreign_fences(agent)
    state = read_state(agent)
    state["files"] = []
    write_state(agent, state)
    agent_preview = update_agent(agent_root, "scout", "all", catalog, True)
    agent_real = update_agent(agent_root, "scout", "all", catalog, False)
    agent_stale_released = ("rule fixmod/codexcomp#codexrule" not in
                            (agent / "AGENTS.md").read_text(encoding="utf-8"))
    foreign_names = [path.relative_to(bounded).as_posix() for path in root_foreign]
    check("W50 — update releases only stale shared sections, never quoted or copied documents",
          all(path.read_bytes() == before for path, before in root_foreign.items())
          and all(path.read_bytes() == before for path, before in agent_foreign.items())
          and all(name not in root_preview[1] and name not in root_real[1]
                  for name in foreign_names)
          and root_stale_released and agent_stale_released
          and "AGENTS.md::#block:rule fixmod/codexcomp#codexrule" in
          agent_preview["generated"]["shared_removed"]
          and "AGENTS.md::#block:rule fixmod/codexcomp#codexrule" in
          agent_real["generated"]["shared_removed"],
          str((root_preview, root_real,
               agent_preview["generated"].get("shared_removed"),
               agent_real["generated"].get("shared_removed"))))
