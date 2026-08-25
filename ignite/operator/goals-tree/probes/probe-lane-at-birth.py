#!/usr/bin/env python3
"""probe-lane-at-birth.py — a goal declares its LANE at birth, and one grammar writes it (7.777).

WHAT IT SCORES, and why it is not the selftest again. `goal_cli.py selftest` calls `cmd_scaffold`
IN PROCESS with a hand-built `argparse.Namespace`: it can prove the gate's logic and nothing about
the COMMAND — a flag never registered on the parser, a `dest` the function does not read, a
refusal that never reaches exit 1. Every arm here runs the real `goal_cli.py` as a SUBPROCESS over
a throwaway goals tree, and one of them hands the result to NODE.

THE THREE PROPERTIES:

  1. NO LANE, NO GOAL — and the refusal lands BEFORE the first write. Arm A asserts the exit code,
     the operator wording, AND `not goal_dir.exists()`. Those are three independent claims on
     purpose: a gate moved BELOW `goal_dir.mkdir()` still exits 1 with the same words, so an arm
     that only read the message would stay green over a tool that leaves a half-built goal behind
     — which then refuses its own re-creation as "already exists". The placement assertion is the
     one that can go red alone, and it is the point of the arm.
  2. THE WRITER AND THE READER AGREE. Arm C does not stop at "the marker says what I wrote": it
     feeds the scaffolded folder to `engine/lane-watch.js#readLane` — the function the daemon's
     watch pass actually uses — and asserts the lane it answers. A writer checked against itself
     proves the writer, never the grammar.
  3. ONE COMPOSER. Arm F scaffolds a goal `--lane daemon` and moves a second goal onto the same
     lane with `lane --set daemon`, then compares the two markers BYTE FOR BYTE. A second speller
     of the marker grammar is drift `readLane` would misparse in silence, and byte equality is the
     only assertion that catches a separator.

  ⚠ 7.787 (`#d-abolish-profile-names`): the marker is ONE WORD and `--profile` is gone from both
  doors. The arms that drove those two facts are re-pointed rather than deleted — B now plants the
  RETIRED flag and requires argparse to refuse it, and D plants it on the console lane for the same
  reason. A flag quietly coming back is exactly what nothing else would notice.

Arm G is DELETED (D12, 2026-08-20): `rbtv-goal relaunch` and the grant file it wrote are gone with
the rest of the grant machinery. A seat comes back through the goal watcher's owed-work launch
(`engine/reconcile.js`), which has no verb at this door.

⚠ THE GREEN AND RED ARMS DISCRIMINATE EACH OTHER. "It refused" is also what a tool that refuses
everything produces (arms C, E, F require creation and exact bytes); "it accepted" is what a
tool with no gates produces (arms A, B, D require refusals over the same fixture).

Run it through the suite — `node ignite/deploy/probe-suite.js --only lane-at-birth` — never by
hand (`G-163`). Exit 0 = the properties hold · 1 = one is broken · 2 = INOPERATIVE (could not run).
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "tool" / "goal_cli.py"
LANE_WATCH = HERE.parents[2] / "engine" / "lane-watch.js"
OUT = HERE / "probe-lane-at-birth.out"

# The RETIRED flag, planted at both doors below. It carried the fallback launch profile until
# `#d-abolish-profile-names` (2026-08-12) deleted the fallback; argparse must now refuse it outright
# rather than accept-and-ignore, which would leave an operator believing he had chosen something.
RETIRED_FLAG = ["--profile", "claude-fable"]

# The two operator phrases the refusal owes the person standing at the terminal (owner-ruled): it
# names WHAT each lane means, never the file it writes.
PHRASE_DAEMON = "the daemon runs it unattended"
PHRASE_CONSOLE = "you run it when you type `rbtv run`"
FORBIDDEN_IN_REFUSAL = "execution-lane"

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


def run(args):
    r = subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                       timeout=120)
    return r.returncode, (r.stdout or ""), (r.stderr or "")


def marker(goal_dir: Path):
    p = goal_dir / "execution-lane"
    return p.read_text(encoding="utf-8") if p.is_file() else None


def main():
    if not TOOL.is_file():
        inoperative("the tool under test exists", f"{TOOL} does not exist")
        OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
        return 2

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        root = tmp / ".rbtv" / "goals"
        root.mkdir(parents=True)
        contract = tmp / "contract.md"
        contract.write_text("Declare the lane at birth, verified at the edge.\n", encoding="utf-8")

        def scaffold(name, *extra):
            return run(["--root", str(root), "scaffold", name,
                        "--contract", str(contract), *extra])

        # ── A. NO LANE, NO GOAL ────────────────────────────────────────────────────────────────
        rc, so, se = scaffold("no-lane-goal")
        said = so + se
        check("A. scaffold with no --lane exits non-zero", rc != 0, f"exit={rc} {said.strip()[:200]}")
        check("A. …the refusal says what the DAEMON lane means to an operator",
              PHRASE_DAEMON in said, said.strip()[:300])
        check("A. …and what the CONSOLE lane means to an operator",
              PHRASE_CONSOLE in said, said.strip()[:300])
        check(f"A. …and never names the file ({FORBIDDEN_IN_REFUSAL!r}) — the operator is told "
              "about lanes, not about the tool's bookkeeping",
              FORBIDDEN_IN_REFUSAL not in said, said.strip()[:300])
        # THE PLACEMENT ARM. Independent of the three above: it is the only one that goes red when
        # the gate is moved below `goal_dir.mkdir()`.
        check("A. …and NO goal folder was left behind (the gate is ahead of the first write)",
              not (root / "no-lane-goal").exists(),
              str(sorted(p.name for p in (root / "no-lane-goal").iterdir())
                  if (root / "no-lane-goal").is_dir() else "absent"))

        # ── B. the RETIRED --profile flag (7.787) ──────────────────────────────────────────────
        rc, so, se = scaffold("bad-profile-goal", "--lane", "daemon", *RETIRED_FLAG)
        check("B. --lane daemon with the RETIRED --profile flag is refused by argparse — the "
              "abolished knob cannot be passed at all, not even to be ignored",
              rc != 0 and "unrecognized arguments" in (so + se),
              f"exit={rc} {(so + se).strip()[:200]}")
        check("B. …and nothing was created", not (root / "bad-profile-goal").exists())

        # ── C. the daemon lane, written and READ BACK BY THE DAEMON'S OWN READER ────────────────
        rc, so, se = scaffold("daemon-goal", "--lane", "daemon")
        dg = root / "daemon-goal"
        check("C. --lane daemon creates the goal", rc == 0 and dg.is_dir(),
              f"exit={rc} {(so + se).strip()[:200]}")
        check("C. …and the marker reads exactly 'daemon\\n' — ONE WORD, no second token",
              marker(dg) == "daemon\n", repr(marker(dg)))
        if not LANE_WATCH.is_file():
            inoperative("C. the daemon's own reader agrees", f"{LANE_WATCH} does not exist")
        else:
            js = subprocess.run(
                ["node", "-e",
                 "const r=require(process.argv[1]).readLane(process.argv[2]);"
                 "process.stdout.write(`${r.lane}|${r.legacy}`)",
                 str(LANE_WATCH), str(dg)],
                capture_output=True, text=True, timeout=60)
            if js.returncode != 0:
                inoperative("C. the daemon's own reader agrees",
                            f"node rc={js.returncode} {js.stderr.strip()[:200]}")
            else:
                check("C. …and `lane-watch.js#readLane` — the function the daemon's watch pass "
                      "runs — answers daemon and NOT legacy: WRITER AND READER AGREE",
                      js.stdout == "daemon|false", repr(js.stdout))

        # ── D/E. the console lane ──────────────────────────────────────────────────────────────
        rc, so, se = scaffold("console-profile-goal", "--lane", "console", *RETIRED_FLAG)
        check("D. --lane console with the RETIRED --profile flag is refused too — the flag is gone "
              "from the parser, so neither lane can be handed one",
              rc != 0 and "unrecognized arguments" in (so + se),
              f"exit={rc} {(so + se).strip()[:200]}")
        check("D. …and nothing was created", not (root / "console-profile-goal").exists())

        rc, so, se = scaffold("console-goal", "--lane", "console")
        cg = root / "console-goal"
        check("E. --lane console creates the goal", rc == 0 and cg.is_dir(),
              f"exit={rc} {(so + se).strip()[:200]}")
        check("E. …and the marker reads exactly 'console\\n'", marker(cg) == "console\n",
              repr(marker(cg)))

        # ── F. ONE COMPOSER — born-daemon and moved-to-daemon are the SAME BYTES ────────────────
        rc, so, se = scaffold("moved-goal", "--lane", "console")
        if rc != 0:
            inoperative("F. the one-composer comparison", f"fixture scaffold failed: {se.strip()[:200]}")
        else:
            # ⚠ MATERIALIZED FIRST (7.787). `--set daemon` now refuses a goal whose seats cannot be
            # read (`lane-cast-unknown`) and one whose seats are UNCAST (`lane-uncast-seats`) —
            # "unknown" is not "none". A bare scaffolded goal is the first of those, so the fixture
            # gives it the minimum a real materialized goal has: a taskforce row and a CAST seat.
            mg_dir = root / "moved-goal"
            (mg_dir / "seats" / "alpha").mkdir(parents=True, exist_ok=True)
            (mg_dir / "taskforce.csv").write_text(
                "taskforce-id,seat,after\ntf-moved,alpha,\n", encoding="utf-8")
            (mg_dir / "seats" / "alpha" / "seat.md").write_text(
                "---\nseat: alpha\nharness: claude\nmodel: claude-fable-5\n---\n\nbody\n",
                encoding="utf-8")
            rc, so, se = run(["--root", str(root), "lane", "moved-goal", "--set", "daemon"])
            mg = root / "moved-goal"
            check("F. `lane --set daemon` moves an existing goal", rc == 0,
                  f"exit={rc} {(so + se).strip()[:200]}")
            check("F. …and its marker is BYTE-IDENTICAL to the one `scaffold --lane daemon` "
                  "wrote — one composer, no second grammar",
                  marker(mg) is not None and marker(mg) == marker(dg),
                  f"scaffolded={marker(dg)!r} moved={marker(mg)!r}")

    failures = [lbl for ok, lbl in RESULTS if not ok]
    out("")
    out(f"checks: {len(RESULTS)}  failures: {len(failures)}  inoperative: {len(INOPERATIVE)}")
    for lbl, why in INOPERATIVE:
        out(f"  INOPERATIVE  {lbl}: {why}")
    for lbl in failures:
        out(f"  FAILED  {lbl}")
    OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")

    if failures:
        return 1
    return 2 if INOPERATIVE else 0


if __name__ == "__main__":
    sys.exit(main())
