#!/usr/bin/env python3
"""probe-goal-splice.py — growing a LIVE goal's seat roster holds end to end (issue S-33).

WHAT IT SCORES, and why it is not the selftest again. `goal_cli.py selftest` calls `cmd_pause`,
`splice_new_seat` and `cmd_add_seat` IN PROCESS, with hand-built `argparse.Namespace` objects. That
proves the logic and proves nothing about the COMMAND: a verb that is never registered on the
parser, a flag whose `dest` does not match what the function reads, a required argument the
namespace supplies but a caller cannot, and a refusal that never reaches exit 1 are all invisible
to it. Every arm here runs the real `goal_cli.py` as a SUBPROCESS, over a throwaway goals tree,
and reads exit codes and `--json` refusal codes off stdout/stderr.

THE PROPERTY: a goal whose roster is grown must come out with (1) exactly the rewired rows
changed and every other byte identical, (2) the pause stash returned byte-for-byte by `resume`,
and (3) every gate refusing by CODE — never by prose, which is edited freely.

⚠ THE GREEN AND RED ARMS DISCRIMINATE EACH OTHER, which is what makes this probe non-vacuous
without a source mutant. "The tool refused" is also what a tool that refuses everything produces —
so rows 3 and 6 require a splice to SUCCEED and to change exactly one line. "The tool accepted" is
what a tool with no gates produces — so rows 4-5 require six named refusals over the same fixture
the green rows use. Neither set can be satisfied by a degenerate tool.

Run it through the suite — `node deploy/probe-suite.js --only goal-splice` — never by hand
(`G-163`). Exit 0 = the property holds · 1 = a property is broken · 2 = INOPERATIVE (could not run).
"""

import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
TOOL = HERE.parent / "tool" / "goal_cli.py"
OUT = HERE / "probe-goal-splice.out"

TF_HEAD = ["taskforce-id", "seat", "after", "harness", "model", "effort",
           "ctx-refresh", "milestone-id"]
# The fixture graph. `d` carries a GUARD and `c` carries a MULTI-MEMBER cell on purpose — those
# are the two cell shapes a naive splice damages, and the two the gates key on.
FIXTURE_ROWS = [("a", ""), ("b", "a"), ("c", "a,b"), ("d", "a[gate=b]"), ("new", "a")]

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


def refusal_code(stdout):
    """The machine-readable code off a `--json` refusal envelope, or None."""
    try:
        return json.loads(stdout).get("refusal", {}).get("code")
    except Exception:                                             # noqa: BLE001
        return None


def render(values):
    import io
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(values)
    return buf.getvalue()[:-1]


def taskforce_text():
    return "\n".join([render(TF_HEAD)]
                     + [render(["tf-1", s, a, "claude", "claude-opus-5", "medium", "50", "m1"])
                        for s, a in FIXTURE_ROWS]) + "\n"


def build_tree(td: Path):
    """A throwaway goals root carrying one goal with a hand-built registry.

    Scaffolded through the tool itself, so the goal is the shape the tool creates rather than a
    shape this probe invented — a fixture that diverges from the real one scores the fixture.
    """
    root = td / ".rbtv" / "goals"
    root.mkdir(parents=True)
    contract = td / "contract.md"
    contract.write_text("Grow the roster, verified at the edge.\n", encoding="utf-8")
    rc, _, err = run(["--root", str(root), "scaffold", "live-goal", "--contract", str(contract)])
    if rc != 0:
        raise RuntimeError(f"could not scaffold the fixture goal: {err.strip()}")
    goal = root / "live-goal"
    (goal / "taskforce.csv").write_text(taskforce_text(), encoding="utf-8", newline="")
    (goal / "executions.csv").write_text(
        "seat,session-id,lane,started,ended,outcome\na,s1,attached,t0,t1,done\n",
        encoding="utf-8", newline="")
    sheet = td / "bindings.json"
    # The SHARED sheet names every seat of the goal — which is exactly why `add-seat` writes a
    # one-seat SCOPED copy for the mint: the materializer refuses `bindings-extra-seat` for any
    # key outside the set being materialized. A one-seat sheet here would make row 7 pass for
    # the wrong reason.
    sheet.write_text(json.dumps({
        "defaults": {"harness": "claude", "model": "claude-opus-5", "effort": "medium",
                     "ctx-refresh": "50", "agent_type": "worker", "cwd-mode": "seat-folder"},
        "seats": {s: {} for s, _ in FIXTURE_ROWS}}, indent=2), encoding="utf-8")
    return root, goal, sheet, build_catalog(td)


def build_catalog(td: Path) -> Path:
    """The minimum CMP-5 component database `materialize-seats.py` can assemble a seat from."""
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
        "seat-id,prompt-id,task-id,description\n"
        + "".join(f"{s},prompt-demo,task-demo,seat {s}\n" for s, _ in FIXTURE_ROWS),
        encoding="utf-8")
    return td / "catalog"


def main() -> int:
    OUT.write_text("", encoding="utf-8")   # truncate BEFORE any work — no evidence husk

    if not TOOL.is_file():
        inoperative("goal_cli.py is present", f"{TOOL} does not exist")
        OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
        return 2

    with tempfile.TemporaryDirectory(prefix="probe-goal-splice-") as _td:
        td = Path(_td)
        try:
            root, goal, sheet, catalog = build_tree(td)
        except Exception as exc:                                  # noqa: BLE001
            inoperative("throwaway fixture builds", str(exc))
            OUT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
            return 2

        lane = goal / "execution-lane"
        R = ["--root", str(root)]

        def add_seat(*extra, before="b", after="a", seat="new", splice_only=True):
            return run([*R, "--json", "add-seat", "live-goal", "--seat", seat,
                        "--after", after, "--before", before,
                        "--bindings", str(sheet), "--catalog-root", str(catalog),
                        *(["--splice-only"] if splice_only else []), *extra])

        def reset_registry():
            (goal / "taskforce.csv").write_text(taskforce_text(), encoding="utf-8", newline="")

        def refuses_without_damage(label, code, *args, **kw):
            """A refusal that left `taskforce.csv` byte-identical — snapshotted immediately
            BEFORE the call and compared immediately after, with NOTHING in between.

            ⚠ THE ORDER IS THE WHOLE ARM. The first version of this probe called
            `reset_registry()` between the refusals and the comparison, so it compared the reset
            text to itself: it passed for a tool that wrote garbage on every refusal. A damage
            check whose snapshot is taken after a restore is not a damage check.
            """
            snapshot = (goal / "taskforce.csv").read_text(encoding="utf-8")
            rc, so, _ = add_seat(*args, **kw)
            check(label, rc == 1 and refusal_code(so) == code, f"exit={rc} {so.strip()[:200]}")
            check(f"{label.split('.')[0]}. …and it left taskforce.csv byte-identical",
                  (goal / "taskforce.csv").read_text(encoding="utf-8") == snapshot)

        # ── 1. the PAUSE stash round-trips byte-exactly through the real CLI ──────────────────
        lane.write_text("daemon claude-sonnet\n", encoding="utf-8", newline="")
        rc, so, se = run([*R, "pause", "live-goal"])
        check("1. `pause` exits 0", rc == 0, f"exit={rc} {se.strip()[:200]}")
        check("1. the marker is stashed behind `paused `",
              lane.read_text(encoding="utf-8") == "paused daemon claude-sonnet\n",
              repr(lane.read_text(encoding="utf-8")))
        rc, so, _ = run([*R, "--json", "lane", "live-goal"])
        payload = json.loads(so) if so.strip().startswith("{") else {}
        check("1. `lane --json` reports paused + paused_from",
              payload.get("paused") is True
              and payload.get("paused_from") == "daemon claude-sonnet"
              and payload.get("lane") == "console",
              so.strip()[:300])
        rc, _, se = run([*R, "--json", "lane", "live-goal", "--set", "console"])
        check("1. `lane --set` refuses `lane-paused` while the stash is held",
              rc == 1 and "lane-paused" in se, f"exit={rc} {se.strip()[:200]}")
        rc, _, se = run([*R, "resume", "live-goal"])
        check("1. `resume` returns the marker BYTE-EXACTLY",
              rc == 0 and lane.read_text(encoding="utf-8") == "daemon claude-sonnet\n",
              repr(lane.read_text(encoding="utf-8")))
        rc, so, se = run([*R, "--json", "resume", "live-goal"])
        check("1. a second `resume` refuses `not-paused`",
              rc == 1 and refusal_code(so) == "not-paused", f"exit={rc} {so.strip()[:200]}")

        # ── 2. `dag` reads the graph without opening a file ───────────────────────────────────
        rc, so, se = run([*R, "--json", "dag", "live-goal"])
        try:
            dag = json.loads(so)
        except Exception:                                         # noqa: BLE001
            dag = {}
        seats_seen = [n["seat"] for n in dag.get("nodes", [])]
        check("2. `dag --json` lists every registry row in dependency order",
              rc == 0 and seats_seen and seats_seen.index("a") < seats_seen.index("b"),
              f"exit={rc} {seats_seen}")
        states = {n["seat"]: n["state"] for n in dag.get("nodes", [])}
        check("2. `dag` derives each seat's state from executions.csv",
              states.get("a") == "done" and states.get("c") == "never-ran", str(states))

        # ── 3. THE GREEN ARM — a splice succeeds and changes EXACTLY the rewired line ─────────
        #
        # CONSOLE, then pause: rows 4's cells are multi-member/guarded, which the
        # daemon-complex-cell gate refuses on a stashed DAEMON lane (row 5 scores that on
        # purpose). The green rows must not be measuring that gate by accident.
        lane.write_text("console\n", encoding="utf-8", newline="")
        run([*R, "pause", "live-goal"])
        before_text = (goal / "taskforce.csv").read_text(encoding="utf-8")
        rc, so, se = add_seat()
        check("3. add-seat --splice-only exits 0", rc == 0, f"exit={rc} {se.strip()[:300]}")
        after_text = (goal / "taskforce.csv").read_text(encoding="utf-8")
        changed = [(x, y) for x, y in zip(before_text.split("\n"), after_text.split("\n"))
                   if x != y]
        check("3. exactly ONE line changed", len(changed) == 1, str(changed))
        check("3. …and it is b's `after` cell, re-parented onto the new seat",
              changed and changed[0][1].startswith("tf-1,b,new,"), str(changed))

        # ── 4. THE GUARD AND THE DEDUPE survive the real command ──────────────────────────────
        reset_registry()
        rc, so, se = add_seat(before="d", after="a,b", seat="new")
        # `d`'s cell is `a[gate=b]`: the member OUTSIDE the brackets is substituted, the `b`
        # INSIDE the guard is a condition and must not be.
        row_d = [ln for ln in (goal / "taskforce.csv").read_text(encoding="utf-8").split("\n")
                 if ln.startswith("tf-1,d,")]
        check("4. a `[key=value]` guard span survives the splice untouched",
              rc == 0 and row_d and row_d[0] == 'tf-1,d,new[gate=b],claude,claude-opus-5,'
                                                'medium,50,m1',
              f"exit={rc} {row_d} {se.strip()[:200]}")
        reset_registry()
        rc, so, se = add_seat(before="c", after="a,b")
        row_c = [ln for ln in (goal / "taskforce.csv").read_text(encoding="utf-8").split("\n")
                 if ln.startswith("tf-1,c,")]
        check("4. two replaced members collapse to ONE (no `new,new`)",
              rc == 0 and row_c and row_c[0].startswith("tf-1,c,new,"),
              f"exit={rc} {row_c} {se.strip()[:200]}")

        # ── 5. THE RED ARMS — every gate refuses BY CODE, exit 1, registry untouched ──────────
        reset_registry()
        pristine = (goal / "taskforce.csv").read_text(encoding="utf-8")

        lane.write_text("console\n", encoding="utf-8", newline="")
        refuses_without_damage("5. an UNPAUSED goal refuses `goal-not-paused`", "goal-not-paused")

        lane.write_text("paused console\n", encoding="utf-8", newline="")
        (goal / "executions.csv").write_text(
            "seat,session-id,lane,started,ended,outcome\na,s1,attached,t0,,\n",
            encoding="utf-8", newline="")
        refuses_without_damage("5. an OPEN execution row refuses `goal-not-quiescent`",
                               "goal-not-quiescent")
        # THE DEADLOCK ESCAPE. A killed run's row is never closed by anything, so the gate above
        # is permanent without a way past it. The refusal must also NAME the row it is about.
        _, so, _ = add_seat()
        msg = json.loads(so).get("refusal", {}).get("message", "") if so.strip().startswith("{") \
            else so
        check("5. …and the refusal NAMES the offending row (seat, session, started)",
              "seat a" in msg and "session s1" in msg and "started t0" in msg, msg[:250])
        rc, so, _ = add_seat("--allow-open-execution")
        check("5. …and --allow-open-execution is the escape for a row nothing will ever close",
              rc == 0, f"exit={rc} {so.strip()[:200]}")
        reset_registry()
        # A SUPERSEDED open row is NOT live — the seat's LAST row decides, exactly as the engine
        # reads the record (`engine/seeding.js#recordView`).
        (goal / "executions.csv").write_text(
            "seat,session-id,lane,started,ended,outcome\n"
            "a,s1,attached,t0,,\na,s2,attached,t1,t2,done\n", encoding="utf-8", newline="")
        rc, so, _ = add_seat()
        check("5. a seat whose LAST row is stamped is quiescent despite an earlier OPEN row",
              rc == 0, f"exit={rc} {so.strip()[:200]}")
        reset_registry()

        (goal / "executions.csv").write_text(
            "seat,session-id,lane,started,ended,outcome\nb,s1,attached,t0,t1,done\n",
            encoding="utf-8", newline="")
        refuses_without_damage(
            "5. a --before seat that has already RUN refuses `splice-target-has-run`",
            "splice-target-has-run")

        (goal / "executions.csv").write_text(
            "seat,session-id,lane,started,ended,outcome\na,s1,attached,t0,t1,done\n",
            encoding="utf-8", newline="")
        (goal / ".attached-run.lock").write_text("held\n", encoding="utf-8")
        refuses_without_damage("5. a live attached run refuses `attached-run-live`",
                               "attached-run-live")
        (goal / ".attached-run.lock").unlink()

        refuses_without_damage(
            "5. a seat absent from the shared sheet refuses `bindings-missing-seat`",
            "bindings-missing-seat", seat="absent")

        lane.write_text("paused daemon claude-sonnet\n", encoding="utf-8", newline="")
        refuses_without_damage(
            "5. a multi-member cell + a stashed DAEMON lane refuses `daemon-complex-cell`",
            "daemon-complex-cell", before="c", after="a,b")
        rc, so, _ = add_seat("--allow-daemon-complex-cell", before="c", after="a,b")
        check("5. …and --allow-daemon-complex-cell is the deliberate escape", rc == 0,
              f"exit={rc} {so.strip()[:200]}")
        reset_registry()

        lane.write_text("paused console\n", encoding="utf-8", newline="")
        refuses_without_damage("5. --before naming no row refuses `splice-before-unknown`",
                               "splice-before-unknown", before="nope")
        refuses_without_damage(
            "5. a --before row sharing no member with --after refuses "
            "`splice-not-an-insertion`", "splice-not-an-insertion", before="b", after="b")

        (goal / "taskforce.csv").write_text(pristine.replace('tf-1,a,', 'tf-1,"a",', 1),
                                            encoding="utf-8", newline="")
        refuses_without_damage("5. a non-canonical registry refuses `taskforce-noncanonical`",
                               "taskforce-noncanonical")
        # CRLF: the same code, but the message must NAME line endings — the un-named version sent
        # the operator to "repair the registry" with nothing to act on.
        (goal / "taskforce.csv").write_text(pristine.replace("\n", "\r\n"),
                                            encoding="utf-8", newline="")
        rc, so, _ = add_seat()
        msg = json.loads(so).get("refusal", {}).get("message", "") if so.strip().startswith("{") \
            else so
        check("5. a CRLF registry refuses `taskforce-noncanonical` NAMING the line endings",
              rc == 1 and refusal_code(so) == "taskforce-noncanonical"
              and "CRLF" in msg and "LF-only" in msg, f"exit={rc} {msg[:250]}")
        reset_registry()

        # ── 6. DRY RUN reviews without touching, and runs the gates ───────────────────────────
        before_dry = (goal / "taskforce.csv").read_text(encoding="utf-8")
        rc, so, se = add_seat("--dry-run")
        check("6. --dry-run exits 0 and writes nothing",
              rc == 0 and (goal / "taskforce.csv").read_text(encoding="utf-8") == before_dry,
              f"exit={rc} {se.strip()[:200]}")
        try:
            plan = json.loads(so)
        except Exception:                                         # noqa: BLE001
            plan = {}
        check("6. --dry-run prints the local graph around the new seat",
              plan.get("dry_run") is True
              and [r["seat"] for r in plan.get("rewrites", [])] == ["b"],
              so.strip()[:300])
        lane.write_text("console\n", encoding="utf-8", newline="")
        rc, so, _ = add_seat("--dry-run")
        check("6. --dry-run fires the gates too (an unpaused goal still refuses)",
              rc == 1 and refusal_code(so) == "goal-not-paused", f"exit={rc} {so.strip()[:200]}")

        # ── 7. THE MINT PATH — the half `--splice-only` skips ────────────────────────────────
        #
        # ⚠ THIS ROW EXISTS BECAUSE THE BUG IT SCORES SHIPPED PAST EVERY ARM ABOVE. `add-seat`
        # read `taskforce.csv` ONCE, before dispatching the mint — so the snapshot it spliced
        # did not contain the row the mint had just appended, and a run that minted PERFECTLY
        # then refused `splice-no-row`, leaving the goal in exactly the half-done state
        # `--splice-only` exists to resume. Every `--splice-only` arm above stayed green
        # throughout: they hand-build the row, so they never exercise the read ordering. A
        # mint arm is therefore not redundant coverage of the splice — it is the ONLY arm that
        # sees the two halves in sequence.
        import shutil
        lane.write_text("paused console\n", encoding="utf-8", newline="")
        (goal / "executions.csv").write_text(
            "seat,session-id,lane,started,ended,outcome\na,s1,attached,t0,t1,done\n",
            encoding="utf-8", newline="")
        shutil.rmtree(goal / "seats", ignore_errors=True)
        # A registry WITHOUT the new seat — the mint is what puts it there.
        (goal / "taskforce.csv").write_text(
            "\n".join([render(TF_HEAD)]
                      + [render(["tf-1", s, a, "claude", "claude-opus-5", "medium", "50", "m1"])
                         for s, a in FIXTURE_ROWS if s != "new"]) + "\n",
            encoding="utf-8", newline="")
        rc, so, se = add_seat(splice_only=False)
        registry = (goal / "taskforce.csv").read_text(encoding="utf-8")
        check("7. add-seat MINTS and splices in one act", rc == 0,
              f"exit={rc} {(se or so).strip()[:400]}")
        check("7. the minted row carries the goal's EXISTING taskforce-id (not max+1)",
              "tf-1,new,a," in registry, registry)
        check("7. …and the successor is re-parented onto it in the same act",
              "tf-1,b,new," in registry, registry)
        check("7. the seat's descriptor was assembled",
              (goal / "seats" / "new" / "seat.md").is_file(),
              str(sorted(p.name for p in (goal / "seats").iterdir())
                  if (goal / "seats").is_dir() else "no seats/"))
        # The scoped one-seat bindings copy is a TEMP FILE outside the goal folder, removed in a
        # `finally`. A stray copy inside the goal is a real leak: it lands under the tree the
        # operator is auditing, and survives a crash between mint and splice.
        check("7. no scoped-bindings temp file was left in the goal folder",
              not [p.name for p in goal.iterdir() if p.name.startswith("add-seat-")],
              str([p.name for p in goal.iterdir()]))

        # ── 8. THE MINT-PATH DAMAGE ARM — a refusable splice must never MINT ─────────────────
        #
        # ⚠ EVERY ARM IN ROW 5 RUNS `--splice-only`, so none of them can see this. The splice
        # validations used to run only AFTER the mint: a bad `--before` refused with the row
        # already appended and `seats/<seat>/` already assembled — a half-grown goal produced by
        # a gate, on the one path where the gate has something to lose.
        shutil.rmtree(goal / "seats", ignore_errors=True)
        premint_registry = "\n".join(
            [render(TF_HEAD)]
            + [render(["tf-1", s, a, "claude", "claude-opus-5", "medium", "50", "m1"])
               for s, a in FIXTURE_ROWS if s != "new"]) + "\n"
        (goal / "taskforce.csv").write_text(premint_registry, encoding="utf-8", newline="")
        rc, so, _ = add_seat(before="nope", splice_only=False)
        check("8. a mint-path run with an unknown --before refuses `splice-before-unknown` "
              "BEFORE minting", rc == 1 and refusal_code(so) == "splice-before-unknown",
              f"exit={rc} {so.strip()[:250]}")
        check("8. …and NO row was appended to taskforce.csv",
              (goal / "taskforce.csv").read_text(encoding="utf-8") == premint_registry,
              (goal / "taskforce.csv").read_text(encoding="utf-8"))
        check("8. …and NO seats/new/ folder was assembled",
              not (goal / "seats" / "new").exists(),
              str(sorted(p.name for p in (goal / "seats").iterdir())
                  if (goal / "seats").is_dir() else "no seats/"))

        # ── 9. THE CROSS-LANGUAGE PIN on the attached-run lock filename ──────────────────────
        #
        # ⚠ THE PYTHON CONSTANT WAS PINNED TO ITSELF. `goal_cli.ATTACHED_RUN_LOCK` names a file
        # `engine/attached-execution.js` creates, and the "pin" was a Python arm comparing the
        # literal to a copy of the literal — it could not go red on a JS rename, which is the
        # only event it exists to catch. This asks NODE for its own export.
        # HERE = …/ignite/capabilities/goals-tree/probes → parents[2] is …/ignite
        engine = (HERE.parents[2] / "engine" / "attached-execution.js").resolve()
        if not engine.is_file():
            inoperative("9. the JS side of the lock-name pin", f"{engine} does not exist")
        else:
            js = subprocess.run(
                ["node", "-e",
                 f"process.stdout.write(require({str(engine).replace(chr(92), '/')!r}).RUN_LOCK)"],
                capture_output=True, text=True, timeout=60)
            py = subprocess.run(
                [sys.executable, "-c",
                 "import importlib.util,sys;"
                 f"spec=importlib.util.spec_from_file_location('g', {str(TOOL)!r});"
                 "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);"
                 "sys.stdout.write(m.ATTACHED_RUN_LOCK)"],
                capture_output=True, text=True, timeout=60)
            if js.returncode != 0 or py.returncode != 0:
                inoperative("9. the lock-name pin evaluates on both sides",
                            f"node rc={js.returncode} {js.stderr.strip()[:200]} | "
                            f"python rc={py.returncode} {py.stderr.strip()[:200]}")
            else:
                check("9. `goal_cli.ATTACHED_RUN_LOCK` equals the value NODE exports as "
                      "`attached-execution.js#RUN_LOCK` — a rename on either side goes red here",
                      js.stdout == py.stdout and js.stdout.strip() != "",
                      f"js={js.stdout!r} py={py.stdout!r}")

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
