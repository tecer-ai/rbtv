#!/usr/bin/env python3
"""probe-goal-root-escape.py — `goal_cli.py`'s `--root` sandbox holds for `lint` and `materialize`.

THE DEFECT IT SCORES (found by adversarial verification of task 7.63, run-2 seat `G2-goaltree-ver`,
Finding 1): `goal_dir = root / args.goal_name`. `Path.__truediv__` DISCARDS the left operand when
the right one is absolute, so an absolute `goal_name` escaped `--root` entirely — `materialize`
wrote a `seat.md` outside the declared root and still reported `"ok": true`, exit 0. `..` segments
walk out of the root the same way. Only `scaffold` validated its name (`GOAL_NAME_RE`); `lint` and
`materialize` validated nothing. `--root` is the ONLY thing that aims a write verb at a test tree
instead of a live goals package, so an escape defeats the one sandbox this tool has.

⚠ THE GREEN ARMS ALONE PROVE NOTHING, AND THAT IS WHY THE MUTANT EXISTS. "The tool refused" is also
what a tool that refuses everything, or that never found the goal, would produce. So every green
arm has a control:

  - the MUTANT arm (row 3) runs a copy of `goal_cli.py` with EVERY `resolve_goal_dir` call site
    textually reverted to the pre-fix `root / <name>` and REQUIRES the escape to succeed there — a
    write landing outside the root, exit 0. If the mutant does NOT escape, this probe is vacuous
    and exits 2 (INOPERATIVE), never 0: an assertion that cannot go red has scored nothing. Row 3
    also counts CALL SITES against MUTATED sites and refuses to proceed unless they match, so a
    call site written in a textual form the mutation cannot reach cannot silently shrink the
    guard (see `CALL_SITE_RE` / `MUTATE_RE`).
  - the POSITIVE arm (row 4) requires an ordinary in-root goal name to still lint and materialize,
    so the refusal is discriminating rather than a blanket ban.

Every path below is a throwaway tree under `tempfile`. The live `.rbtv/goals` package is never read
and never written, by either the fixed tool or the mutant.

Run it through the suite — `node deploy/probe-suite.js --only goal-root-escape` — never by hand
(`G-163`). Exit 0 = the sandbox holds and the mutant proved the check can fail · 1 = a property is
broken · 2 = INOPERATIVE (could not run, or the red control did not go red).

⚠ 1 WINS OVER 2 WHEN BOTH APPLY (task 7.592, from the §2 review of 7.576). A genuinely broken
G-115 guard produces BOTH: real assertion failures in rows 1-2d AND an inoperative row 3, because
row 1 has already escaped and the mutant's own materialize then refuses as "already materialized".
The old mapping returned 2 first, so the WORST case this probe can report — a live escape out of
`--root` — read as "broken probe" to anything grading on the exit code alone. Real failures
therefore win: `failures` → 1, else `INOPERATIVE` → 2, else 0. Nothing is hidden either way — the
summary prints every INOPERATIVE row and every FAILED row regardless of which code is returned.
The vacuity signal is untouched where it is the ONLY signal: a census that reaches no call site
while the guard still holds has no real failures, so it still exits 2.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "tool" / "goal_cli.py"
OUT = HERE / "probe-goal-root-escape.out"

# The mutation, as a FORM rather than as literals. `CALL_SITE_RE` counts every `resolve_goal_dir`
# CALL in the landed source (its definition excluded); `MUTATE_RE` is the subset the mutant can
# actually revert to the pre-fix `root / <name>`. Row 3 requires those two counts to be EQUAL and
# nonzero.
#
# WHY IT COUNTS CALL SITES AND NOT PATTERNS (task 7.576): the earlier form held two literal
# strings and asserted `applied == 2` — but `goal_cli.py` carries FIVE call sites in THREE textual
# forms (`resolve_goal_dir(root, name)` · `(root, args.goal_name)` · `(root, goal_name)`), so
# `applied == 2` was satisfied while a whole form went unmutated. A future call site in that
# unmutated form, inside a verb rows 1–2b score, would have shrunk this guard with no signal —
# the same failure class this probe itself recovered from, one level down. Counting the calls in
# the source makes the shortfall unmissable.
#
# The census is WHOLE-FILE on purpose: which verbs this probe scores is a judgement, and gating
# the count on that judgement re-introduces the silence. If this ever fires on a call site that
# genuinely must not be mutated, widen `MUTATE_RE` or record the exclusion HERE, on the probe,
# with its reason — never let it pass silent.
#
# ⚠ WHAT THE CENSUS CANNOT SEE — the residual, MEASURED and RECORDED rather than guarded (§2
# review of 7.576). Both regexes key on the literal text `resolve_goal_dir(`, so an INDIRECT
# callee is invisible to BOTH of them: the two counts stay EQUAL and the shortfall passes
# SILENTLY, exit 0. Measured on scratch copies: an alias binding (`_rgd = resolve_goal_dir` …
# `_rgd(root, name)`) and a lookup callee (`globals()["resolve_goal_dir"](root, name)`) each
# moved sites 5→4 AND applied 5→4 — 20/20 green, nothing reported. Every DIRECT form does trip
# INOPERATIVE (each measured `4 of 5`, exit 2): a multiline call, keyword arguments
# (`root=root`), a first argument that is not literally `root`, and a nested argument expression
# (`str(name)`). It is stated instead of widened because a bare-name regex would fire on the
# comment in `goal_cli.py` that merely NAMES this function, and every call in that file is
# direct. IF AN INDIRECT CALLEE IS EVER INTRODUCED, add its form to both regexes by hand — this
# census cannot warn you about it.
CALL_SITE_RE = re.compile(r"(?<!def )resolve_goal_dir\(")
MUTATE_RE = re.compile(r"resolve_goal_dir\(root, ([A-Za-z_][A-Za-z0-9_.]*)\)")
MUTATE_SUB = r"root / \1"

RESULTS = []
INOPERATIVE = []
_lines = []


def out(line):
    _lines.append(line)
    print(line)


def check(label, cond, detail=""):
    RESULTS.append((bool(cond), label))
    out(("PASS  " if cond else "FAIL  ") + label + (f"\n        {detail}" if detail else ""))


def inoperative(label, why):
    INOPERATIVE.append((label, why))
    out(f"SKIP  {label}\n        INOPERATIVE: {why}")


def run(tool: Path, args: list[str]):
    r = subprocess.run([sys.executable, str(tool), *args], capture_output=True, text=True,
                       timeout=120)
    return r.returncode, (r.stdout or ""), (r.stderr or "")


def build_tree(td: Path) -> tuple[Path, Path, Path]:
    """A sandbox root, a DECOY goal outside it, and a catalog. Returns (root, decoy_goal, catalog).

    The decoy is a fully materializable goal so that an escape has somewhere real to land: if the
    outside goal were unbuildable, `materialize` would refuse for the WRONG reason and the green
    arm would be an accident.
    """
    root = td / "sandbox" / ".rbtv" / "goals"
    root.mkdir(parents=True)
    decoy_root = td / "decoy"
    decoy_root.mkdir()
    contract = td / "contract.md"
    contract.write_text("Ship the thing.\n", encoding="utf-8")

    rc, _, err = run(TOOL, ["--root", str(decoy_root), "scaffold", "outside-goal",
                            "--contract", str(contract), "--lane", "console"])
    if rc != 0:
        raise RuntimeError(f"could not scaffold the decoy goal: {err.strip()}")
    goal = decoy_root / "outside-goal"

    # 7.607 E2a — GOAL-DIRECT: the plan and the pass folder sit directly under the goal.
    run_dir = goal
    # The decoy's pass folder — the write-safe fixture row 2d needs. `write_gate_key_override`
    # does NOT mkdir its parent: without this folder an escaped `--override` record cannot land
    # even when the guard is gone, so row 2d's "nothing was written outside" arm would pass for
    # the wrong reason — and NOT hypothetically: MEASURED (7.602, trial D3) that with this one
    # `mkdir` removed, the SAME live escape reds only 2 of row 2d's 6 arms — the record cannot
    # land, so "nothing written outside" passes, and the failed write makes the verb exit
    # nonzero so "exits nonzero" passes too. With the folder present the escape lands
    # `planning/pass-1/gate-key-override.md` outside the root and all 6 arms red.
    (run_dir / "planning" / "pass-1").mkdir(parents=True)
    (run_dir / "taskforce.csv").write_text(
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
        "tf-1,w-demo,,claude,claude-opus-5,medium,50,m1\n", encoding="utf-8", newline="\n")
    (run_dir / "milestones.csv").write_text(
        "milestone-id,name,status\nm1,prove it,pending\n", encoding="utf-8", newline="\n")

    comp = td / "catalog" / "mod" / "comp"
    for sub in ("prompts/cognitive-units/persona", "prompts/cognitive-units/permissions",
                "tasks/cognitive-units/task-goal", "capabilities/grep-it"):
        (comp / sub).mkdir(parents=True)
    (comp / "prompts/cognitive-units/persona/p.md").write_text(
        "---\nid: cu-persona-demo\ndescription: demo persona\n---\n\n"
        "<persona>\nYou are the demo seat.\n</persona>\n", encoding="utf-8")
    (comp / "prompts/cognitive-units/permissions/perm.md").write_text(
        "---\nid: cu-permissions-demo\ndescription: demo permissions\n---\n\n"
        "<permissions>\nRead the tree. Write nothing.\n</permissions>\n", encoding="utf-8")
    (comp / "tasks/cognitive-units/task-goal/g.md").write_text(
        "---\nid: cu-task-goal-demo\ndescription: demo goal\n---\n\n"
        "<task-goal>\nProve the assembly.\n</task-goal>\n", encoding="utf-8")
    (comp / "capabilities/grep-it/grep-it.md").write_text(
        "---\nid: cu-capability-grep-it\ndescription: find things\n---\n\n"
        "<capability>\nNot inlined.\n</capability>\n", encoding="utf-8")
    (comp / "prompts.csv").write_text(
        "prompt-id,persona,permissions,description\n"
        "prompt-demo,cu-persona-demo@latest,cu-permissions-demo@latest,demo prompt\n",
        encoding="utf-8")
    (comp / "tasks.csv").write_text(
        "task-id,task-goal,capabilities,description\n"
        "task-demo,cu-task-goal-demo@latest,cu-capability-grep-it,demo task\n", encoding="utf-8")
    (comp / "seats.csv").write_text(
        "seat-id,prompt-id,task-id,description\nw-demo,prompt-demo,task-demo,the demo seat\n",
        encoding="utf-8")
    return root, goal, td / "catalog"


def seats_under(goal: Path) -> list[str]:
    return sorted(str(p) for p in goal.rglob("seat.md"))


def overrides_under(goal: Path) -> list[str]:
    """Row 2d's damage detector — `gate-key-check --override`'s § 6b record."""
    return sorted(str(p) for p in goal.rglob("gate-key-override.md"))


def main() -> int:
    OUT.write_text("", encoding="utf-8")   # truncate BEFORE any work — no evidence husk

    if not TOOL.is_file():
        inoperative("goal_cli.py is present", f"{TOOL} does not exist")
        OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
        return 2

    with tempfile.TemporaryDirectory(prefix="probe-goal-root-escape-") as _td:
        td = Path(_td)
        try:
            root, decoy, catalog = build_tree(td)
        except Exception as exc:                                  # noqa: BLE001
            inoperative("throwaway fixture builds", str(exc))
            OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
            return 2

        abs_name = str(decoy)
        # `..` from `<td>/sandbox/.rbtv/goals` back down into `<td>/decoy/outside-goal`
        dots_name = "../../../decoy/outside-goal"

        # ── 1. materialize (the WRITE verb) refuses both escape forms, and writes nothing ──────
        for label, name in (("absolute path", abs_name), ("`..` traversal", dots_name)):
            rc, so, se = run(TOOL, ["--root", str(root), "materialize", name,
                                    "--catalog-root", str(catalog), "--json"])
            check(f"1.{label} — materialize exits nonzero", rc != 0, f"exit={rc} stdout={so[:200]}")
            check(f"1.{label} — the refusal names the root escape",
                  "escapes --root" in se, f"stderr={se.strip()[:300]}")
            check(f"1.{label} — nothing was written outside --root",
                  seats_under(decoy) == [], str(seats_under(decoy)))
            check(f"1.{label} — nothing was written inside --root either",
                  seats_under(root) == [], str(seats_under(root)))

        # ── 2. lint (the READ verb) refuses both forms rather than reading outside the root ────
        for label, name in (("absolute path", abs_name), ("`..` traversal", dots_name)):
            rc, so, se = run(TOOL, ["--root", str(root), "lint", name])
            check(f"2.{label} — lint exits nonzero", rc != 0, f"exit={rc}")
            check(f"2.{label} — lint refuses instead of reporting findings from outside the root",
                  "escapes --root" in se and "finding(s)" not in so,
                  f"stdout={so.strip()[:200]} stderr={se.strip()[:200]}")

        # ── 2b. gate-key-check (the OTHER read verb) — SCORED, not assumed ─────────────────────
        #
        # `gate_key_check(root, goal_name, …)` is the third textual form, and until task 7.576 it
        # was a guarded call site with no arm at all: nothing here distinguished "guarded" from
        # "unguarded", and silence reads exactly like the defect. It is scored rather than
        # excluded. It writes nothing without `--override`, which is never passed here.
        #
        # WHICH CALL SITE EACH ARM ACTUALLY SCORES, measured by reverting ONE site at a time to
        # the pre-fix `root / <name>` (§2 review of 7.576, re-measured by task 7.592):
        # `lint_goal` → rows 2 (2 arms red) · `gate_key_check` → rows 2b (2 arms red) ·
        # `cmd_materialize` → rows 1 (5 arms red). (`cmd_branch_home` → rows 2c, 4 arms, DELETED
        # WITH ITS VERB by 7.607 E2a — see the note where 2c used to stand.)
        # The fifth site — `cmd_gate_key_check`'s `--override` branch — turns nothing red under
        # that ONE-SITE technique and never will, because it is SHADOWED; rows 2d below score it
        # through a two-site revert instead, and carry the measurement.
        # THERE IS NO LONGER AN UNSCORED CENSUSED SITE (task 7.602). The last one — the
        # `--override` branch of `cmd_gate_key_check` — is scored by rows 2d below. Its former
        # exclusion ("that branch WRITES") is retired: every path here already runs inside a
        # `tempfile` throwaway tree, so the write is safe by construction; what the arm needed
        # was the decoy's `planning/pass-1/` folder (see `build_tree`), because
        # `write_gate_key_override` does not create its parent.
        for label, name in (("absolute path", abs_name), ("`..` traversal", dots_name)):
            rc, so, se = run(TOOL, ["--root", str(root), "gate-key-check", name,
                                    "--pass-folder", "pass-1"])
            check(f"2b.{label} — gate-key-check exits nonzero", rc != 0, f"exit={rc}")
            check(f"2b.{label} — gate-key-check refuses instead of checking outside the root",
                  "escapes --root" in se and "gate-key-check pass-1" not in so,
                  f"stdout={so.strip()[:200]} stderr={se.strip()[:200]}")

        # ── 2c. branch-home — DELETED WITH ITS VERB (7.607 E2a) ───────────────────────────────
        #
        # `cmd_branch_home` and the whole branch-compartment machinery are abolished: the registry
        # deleted the branch folder (`r-branch-folder-deleted-nested-seats-are-ordinary-run-seats`
        # — a branch is a ROLE with no file home) and design-lock item 9 deleted the code with it.
        # Its four arms are removed rather than pointed at a surviving verb: the CENSUS of
        # resolve_goal_dir call sites lost a member, it did not lose coverage of one. The remaining
        # rows still score every site that exists (1, 2, 2b, 2d).

        # ── 2d. gate-key-check --override (the SECOND WRITE path) — SCORED (task 7.602) ────────
        #
        # ⚠ THIS SITE IS SHADOWED, AND THAT CHANGES WHAT ITS RED CONTROL LOOKS LIKE. Reverting
        # this call site ALONE reds nothing here and NEVER CAN: `cmd_gate_key_check`
        # (goal_cli.py) calls `gate_key_check(root, goal_name, …)` FIRST, and that function's own
        # `resolve_goal_dir` refuses an escaping name before the `--override` branch is reached.
        # So a single-site attribution census — the technique that scored rows 2/2b/2c — reports
        # "turns nothing red" for this site whether it is guarded or not, which is precisely why
        # it read as unscorable until 7.602.
        #
        # The red control is therefore a TWO-SITE revert, with the one-site revert as its GREEN
        # discriminator (both MEASURED, task 7.602, scratch copies):
        #   revert `gate_key_check`'s site ONLY   -> rows 2b red, rows 2d GREEN (this site
        #                                            refuses the escape, nothing lands outside)
        #   revert BOTH that site AND this one    -> rows 2d RED: exit 0, no escape refusal, and
        #                                            `gate-key-override.md` written outside --root
        # The green half is what attributes rows 2d to THIS site rather than to the shadowing
        # one — without it the arms would merely re-measure rows 2b.
        #
        # ⚠ IF YOU EVER REMOVE `gate_key_check`'s OWN `resolve_goal_dir` CALL, OR MAKE IT
        # CONDITIONAL, BOTH HALVES ABOVE CHANGE MEANING — silently, with every arm still green.
        # The shadow is what makes the one-site revert a discriminator: unshadowed, reverting
        # `gate_key_check`'s site alone would red rows 2d TOO, and a reader following the recipe
        # would read that as "this site is unguarded" when the site under test was never touched.
        # Rows 2d would also become the ONLY guard left on this path, so what is defense in depth
        # today is a single point of failure then. If that call goes: re-derive the controls here
        # (the one-site revert of THIS site becomes the red control directly) and rewrite this
        # block — do not carry these two trials forward unexamined.
        #
        # The third arm is the one nothing else in this probe covers: an escaping `--override`
        # WRITES. Row 1 asserts `materialize` writes nothing outside; nothing asserted it of the
        # § 6b override record until now.
        for label, name in (("absolute path", abs_name), ("`..` traversal", dots_name)):
            rc, so, se = run(TOOL, ["--root", str(root), "gate-key-check", name,
                                    "--pass-folder", "pass-1", "--override", "d-probe-anchor"])
            check(f"2d.{label} — gate-key-check --override exits nonzero", rc != 0,
                  f"exit={rc} stdout={so.strip()[:200]}")
            check(f"2d.{label} — the refusal names the root escape",
                  "escapes --root" in se, f"stderr={se.strip()[:300]}")
            check(f"2d.{label} — no override record was written outside --root",
                  overrides_under(decoy) == [], str(overrides_under(decoy)))

        # ── 3. THE RED CONTROL — the pre-fix code MUST escape, or rows 1-2 score nothing ───────
        #
        # THE MUTANT MUST SIT AT THE TOOL'S OWN DEPTH. `goal_cli.py` resolves the `after`-member
        # grammar through `coord_source_path()`, which is `Path(__file__).resolve().parents[3] /
        # "team-kit" / "coord.py"`. A mutant dropped in a FLAT temp dir has no such ancestor, so
        # the grammar import failed and `materialize` died inside `after_pred_names` with a
        # traceback — before it ever reached the escape this arm exists to reproduce. The arm
        # then reported `mutant exit=1, wrote nothing` and declared itself INOPERATIVE, which is
        # exactly right and exactly useless: the red control for a CRITICAL defect could not
        # fire, so rows 1-2 had been scoring nothing since the day it was written.
        #
        # So the temp tree MIRRORS the real depth (`<mut>/capabilities/goals-tree/tool/`) and
        # `team-kit` is symlinked to the real one, putting `coord.py` exactly where
        # `parents[3]` looks. The link is READ-ONLY by construction — nothing here writes
        # through it, and `coord.py` is certified and never edited by a probe.
        mut_root = td / "mut"
        mutant = mut_root / "capabilities" / "goals-tree" / "tool" / TOOL.name
        mutant.parent.mkdir(parents=True)
        (mut_root / "team-kit").symlink_to(TOOL.resolve().parents[3] / "team-kit")
        src = TOOL.read_text(encoding="utf-8")
        sites = len(CALL_SITE_RE.findall(src))
        mutated, applied = MUTATE_RE.subn(MUTATE_SUB, src)
        # NAME the offending lines: "4 of 5" alone sends the next agent hunting through the file
        # for the one call the mutation could not reach.
        unreached = [f"{TOOL.name}:{i}: {ln.strip()}"
                     for i, ln in enumerate(src.splitlines(), 1)
                     if CALL_SITE_RE.search(ln) and not MUTATE_RE.search(ln)]
        if sites == 0 or applied != sites:
            inoperative(
                "3. the mutation reaches EVERY resolve_goal_dir call site",
                f"{applied} of {sites} `resolve_goal_dir` call sites in {TOOL.name} were reverted "
                "to the pre-fix form (the counts must MATCH and be nonzero) — a call site the "
                "mutation cannot reach, or a source carrying none at all, means this probe's red "
                "control no longer bites every guarded path; rows 1-2d are therefore unproven, "
                "not green. Widen MUTATE_RE to the new call form, or record the exclusion and its "
                "reason on this probe. UNREACHED: "
                + ("; ".join(unreached) if unreached
                   else "no line matched CALL_SITE_RE at all — the source carries no direct "
                        "`resolve_goal_dir(` call, so there is nothing left to mutate"),
            )
        else:
            mutant.write_text(mutated, encoding="utf-8")
            rc, so, se = run(mutant, ["--root", str(root), "materialize", abs_name,
                                      "--catalog-root", str(catalog), "--json"])
            escaped = seats_under(decoy)
            ok_json = False
            try:
                ok_json = json.loads(so).get("ok") is True
            except Exception:                                     # noqa: BLE001
                ok_json = False
            if rc == 0 and escaped:
                check("3. RED CONTROL — the pre-fix code DOES escape --root (so rows 1-2 can fail)",
                      True, f"mutant wrote {escaped[0]} and reported ok={ok_json}")
            else:
                inoperative(
                    "3. RED CONTROL — the pre-fix code DOES escape --root",
                    f"mutant exit={rc}, wrote {escaped or 'nothing'} outside the root — the "
                    "escape could not be reproduced, so the green rows above discriminate nothing",
                )
            # the mutant's damage is confined to the throwaway tree; clean it so row 4 starts fresh
            shutil.rmtree(decoy / "seats", ignore_errors=True)

        # ── 4. THE POSITIVE CONTROL — an ordinary in-root name is NOT refused ──────────────────
        contract = td / "contract.md"
        rc, _, se = run(TOOL, ["--root", str(root), "scaffold", "inside-goal",
                               "--contract", str(contract), "--lane", "console"])
        check("4. an in-root goal still scaffolds", rc == 0, se.strip()[:200])
        rc, so, se = run(TOOL, ["--root", str(root), "lint", "inside-goal"])
        check("4. an in-root goal is LINTED, not refused as an escape",
              "escapes --root" not in se and "goal-lint inside-goal" in so,
              f"exit={rc} stdout={so.strip()[:200]} stderr={se.strip()[:200]}")
        # gate-key-check's own positive control: it refuses row 2b's names for the ESCAPE, not
        # because it refuses every name. (It still exits nonzero here — no run compartment — so
        # the discriminating property is the absence of the escape refusal, not the exit code.)
        rc, so, se = run(TOOL, ["--root", str(root), "gate-key-check", "inside-goal",
                                "--pass-folder", "pass-1"])
        check("4. an in-root goal is not refused by gate-key-check as an escape",
              "escapes --root" not in se and "escapes --root" not in so,
              f"exit={rc} stdout={so.strip()[:200]} stderr={se.strip()[:200]}")
        # gate-key-check --override's own positive control — an in-root name reaches the
        # override branch instead of being refused as an escape. (`inside-goal` has no run
        # compartment, so the record still cannot be written and the verb exits nonzero; the
        # discriminating property is the ABSENCE of the escape refusal.)
        rc, so, se = run(TOOL, ["--root", str(root), "gate-key-check", "inside-goal",
                                "--pass-folder", "pass-1", "--override", "d-probe-anchor"])
        check("4. an in-root goal is not refused by gate-key-check --override as an escape",
              "escapes --root" not in se and "escapes --root" not in so,
              f"exit={rc} stdout={so.strip()[:200]} stderr={se.strip()[:200]}")

    failures = [lbl for ok, lbl in RESULTS if not ok]
    out("")
    out(f"checks: {len(RESULTS)}  failures: {len(failures)}  inoperative: {len(INOPERATIVE)}")
    for lbl, why in INOPERATIVE:
        out(f"  INOPERATIVE  {lbl}: {why}")
    for lbl in failures:
        out(f"  FAILED  {lbl}")
    OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")

    # A REAL failure outranks INOPERATIVE (see the module docstring): a broken guard reds rows
    # 1-2d (measured: 19 arms — 5+2+2+4+6) AND strands row 3, and reporting that as "could not run"
    # buries a live root escape.
    if failures:
        return 1
    return 2 if INOPERATIVE else 0


if __name__ == "__main__":
    sys.exit(main())
