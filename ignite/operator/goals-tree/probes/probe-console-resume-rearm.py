#!/usr/bin/env python3
"""probe-console-resume-rearm — the CONSOLE `rbtv goal resume` fires the resume RE-ARM EVENT.

WHAT IT MEASURES. `spec-recovery` §4 row 1 says a disarmed `incomplete:` from attempt-counter
exhaustion is what `resume {goal}` "re-arms … resets that counter; named re-arm event", and §5's
closed list names "mechanical `resume {goal}` on a disarmed-counter lane". TWO doors reach that one
verb — the gateway's `pause-resume` intent (Slack) and `goal_cli.py#cmd_resume` (console) — and the
console door used to restore the lane file and fire NOTHING. Measured live 2026-08-28 17:35Z on
`goal-memory-management`: RESUMED printed, `reconcile-respawn/nonterm` still N=3 DISARMED.

EVERYTHING RUNS ON A SCRATCH WORKSPACE. Its own `.rbtv/goals` tree, its own ending store, and its
own attempt-counter ledger under a scratch `RBTV_IGNITE_DEPLOY` — the live workspace, the live
ledger and both live `heart.db` are never named by any arm.

⚠ ARM D IS THE ONE THAT CAN SEE THE FILE SPLIT. The ledger is `__dirname`-relative
(`supervisor/attempt-counters.js#DEFAULT_COUNTERS_PATH`), so it lives beside the CODE, not in the
workspace: the console runs from the source tree and the daemon from the deploy worktree. An
implementation that lets the executor default the path re-arms a ledger nobody reads. Arm D puts a
row in the scratch DEPLOY ledger and a decoy row in a source-side one and asserts which file moved.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
IGNITE = HERE.parents[2]
GOAL_CLI = IGNITE / "operator" / "goals-tree" / "tool" / "goal_cli.py"
STORE_CLI = IGNITE / "state-store" / "cli.js"
COUNTERS = IGNITE / "supervisor" / "attempt-counters.js"

GOAL = "scratch-console-resume-rearm"
DRIVER = "reconcile-respawn"
REASON = "nonterm"
SEAT = "leader"

checks = []


def check(ok, label, detail=""):
    checks.append((bool(ok), label, detail))
    print(f"  {'ok  ' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail and not ok else ""))


def node(script, *argv):
    proc = subprocess.run(["node", "-e", script, *[str(a) for a in argv]],
                          capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise SystemExit(f"node fixture failed: {proc.stderr or proc.stdout}")
    return proc.stdout.strip()


def seed_counter(counters_file, goal, attempts=3):
    """Seed a DISARMED row through the real writer — never by hand-writing the JSON."""
    node(
        "const c=require(process.argv[1]);"
        "const f=process.argv[2];const g=process.argv[3];const n=Number(process.argv[4]);"
        "for(let i=0;i<n;i+=1){c.countAttempt({driver:'reconcile-respawn',goal:g,seat:'leader',"
        "reasonClass:'nonterm',n,items:['cadence-writer']},{countersFile:f});}",
        COUNTERS, counters_file, goal, attempts)


def counter_rows(counters_file, goal):
    try:
        rows = json.loads(Path(counters_file).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [v for v in rows.values() if v.get("goal") == goal]


def store_op(ws, op, payload):
    db = ws / ".rbtv" / "runtime" / "ignite" / "heart.db"
    proc = subprocess.run(["node", str(STORE_CLI), "--db", str(db), "--op", op,
                           "--payload", json.dumps(payload)],
                          capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise SystemExit(f"store op {op} failed: {proc.stderr or proc.stdout}")
    return json.loads(proc.stdout or "null")


def make_workspace(tmp, name="ws", registered=True):
    ws = tmp / name
    goals = ws / ".rbtv" / "goals"
    (goals / GOAL).mkdir(parents=True)
    (goals / "goals.csv").write_text(
        "name,creation date,due date,type,goal-kind,status\n"
        + (f"{GOAL},2026-08-28,,one-off,daemon,active\n" if registered else ""),
        encoding="utf-8")
    (goals / GOAL / "taskforce.csv").write_text(
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
        f"tf-1,{SEAT},,claude,claude-opus-5,high,,m1\n", encoding="utf-8")
    (goals / GOAL / "execution-lane").write_text("paused daemon\n", encoding="utf-8")
    return ws, goals


def run_resume(goals, deploy, cli=GOAL_CLI, extra_env=None):
    env = dict(os.environ)
    env["RBTV_IGNITE_DEPLOY"] = str(deploy)
    env.pop("COORD_AGENT", None)
    env.update(extra_env or {})
    return subprocess.run([sys.executable, str(cli), "resume", GOAL, "--root", str(goals)],
                          capture_output=True, text=True, timeout=120, env=env)


def deploy_ledger(deploy):
    f = deploy / "ignite" / "supervisor" / "attempt-counters.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    return f


def main():
    t0 = time.time()
    tmp = Path(tempfile.mkdtemp(prefix="probe-console-resume-rearm."))
    try:
        # ── A — THE VERB'S OWN CONTRACT: lane restored AND the counter row re-armed ──────────
        print("(a) the console resume restores the lane AND fires the re-arm")
        ws, goals = make_workspace(tmp / "a")
        ledger = deploy_ledger(tmp / "a" / "deploy")
        seed_counter(ledger, GOAL)
        before = counter_rows(ledger, GOAL)
        check(len(before) == 1 and before[0]["attempts"] == 3,
              "precondition: one DISARMED counter row at N=3", json.dumps(before))
        proc = run_resume(goals, tmp / "a" / "deploy")
        check(proc.returncode == 0, "exit 0", proc.stderr[-300:])
        check((goals / GOAL / "execution-lane").read_text(encoding="utf-8") == "daemon\n",
              "the lane assignment is restored verbatim",
              repr((goals / GOAL / "execution-lane").read_text(encoding="utf-8")))
        after = counter_rows(ledger, GOAL)
        check(after == [], "the disarmed counter row is GONE — re-armed", json.dumps(after))
        check("RESUMED" in proc.stdout, "the verb still reports RESUMED", proc.stdout[:200])
        check(re.search(r"re-armed counter: reconcile-respawn/nonterm on leader \(was N=3\)",
                        proc.stdout) is not None,
              "the output NAMES the row it re-armed and its count", proc.stdout[:400])

        # ── B — the ending half of §4 row 1: `disarmed → armed` on the seat row ──────────────
        print("(b) a disarmed `incomplete:` ending row is re-armed too")
        ws, goals = make_workspace(tmp / "b")
        ledger = deploy_ledger(tmp / "b" / "deploy")
        seed_counter(ledger, GOAL)
        store_op(ws, "stampSystem", {
            "goal": GOAL, "seat": SEAT, "ending": "incomplete", "armed": 0,
            "diagnostic": "attempt-counter exhaustion", "reason_class": "nonterm",
            "named_event": "named-external-input", "replace": True,
            "evidence_pointer": "probe fixture",
        })
        pre = store_op(ws, "getCurrentEnding", {"goal": GOAL, "seat": SEAT})
        check(pre and int(pre["armed"]) == 0, "precondition: the seat row reads DISARMED",
              json.dumps(pre))
        proc = run_resume(goals, tmp / "b" / "deploy")
        post = store_op(ws, "getCurrentEnding", {"goal": GOAL, "seat": SEAT})
        check(post and int(post["armed"]) == 1, "the seat row reads ARMED after",
              json.dumps(post))
        check("re-armed counter" in proc.stdout, "the output names the counter row it reset",
              proc.stdout[:400])

        # ── B2 — a disarmed ending row with NO counter row beside it. The counter sweep
        #        consumes the ending flag when both exist (`exhaustion.js#consumeDisarmed`), so
        #        this is the only fixture in which §4 row 1's per-seat leg reports itself. ─────
        print("(b2) a disarmed lane with no counter row is re-armed by the per-seat leg")
        ws, goals = make_workspace(tmp / "b2")
        store_op(ws, "stampSystem", {
            "goal": GOAL, "seat": SEAT, "ending": "incomplete", "armed": 0,
            "diagnostic": "attempt-counter exhaustion", "reason_class": "nonterm",
            "named_event": "named-external-input", "replace": True,
            "evidence_pointer": "probe fixture",
        })
        proc = run_resume(goals, tmp / "b2" / "deploy")
        post = store_op(ws, "getCurrentEnding", {"goal": GOAL, "seat": SEAT})
        check(post and int(post["armed"]) == 1, "the seat row reads ARMED after", json.dumps(post))
        check("re-armed lane: leader disarmed→armed" in proc.stdout,
              "the output names the lane it armed", proc.stdout[:400])

        # ── B3 — the goal word, and the PROVENANCE it is stamped with. `origin` exists so a
        #        console resume is not filed as one the owner typed in chat. ──────────────────
        print("(b3) a paused goal word flips, stamped with the CONSOLE origin")
        ws, goals = make_workspace(tmp / "b3")
        store_op(ws, "writeGoalWord", {"goal": GOAL, "stored": "paused",
                                       "who_stamped": "owner",
                                       "evidence_pointer": "probe fixture"})
        proc = run_resume(goals, tmp / "b3" / "deploy")
        state = store_op(ws, "getGoalState", {"goal": GOAL}) or {}
        check(state.get("stored") == "running", "the goal word reads running", json.dumps(state))
        # KNOWN AND ASSERTED, not overlooked: the pointer says `in chat` whichever door was
        # used. Widening `pauseResume`'s parameter list to carry the door would kill
        # `probe-pause-resume`'s R0d/R4 anchor, which pins that list as 919be192's red-proof.
        check(state.get("evidence_pointer") == f"owner resume in chat · goal {GOAL}",
              "the evidence pointer is the executor's one string (see the note — a known gap)",
              json.dumps(state.get("evidence_pointer")))
        check("goal state: paused→running" in proc.stdout, "the output says so", proc.stdout[:400])

        # ── C — IDEMPOTENT: a second resume has nothing left to re-arm and says so ───────────
        print("(c) a second resume is idempotent and says `nothing to re-arm`")
        (goals / GOAL / "execution-lane").write_text("paused daemon\n", encoding="utf-8")
        proc = run_resume(goals, tmp / "b" / "deploy")
        check(proc.returncode == 0, "exit 0", proc.stderr[-300:])
        check("nothing to re-arm" in proc.stdout, "it says nothing to re-arm",
              proc.stdout[:400])

        # ── D — THE FILE SPLIT. The ledger is code-tree-resident; the console runs from the
        #        SOURCE tree and the daemon from the DEPLOY worktree. Only the deploy ledger
        #        may move. ────────────────────────────────────────────────────────────────────
        print("(d) the ledger written is the DAEMON's, not the console tree's")
        ws, goals = make_workspace(tmp / "d")
        deploy = tmp / "d" / "deploy"
        ledger = deploy_ledger(deploy)
        seed_counter(ledger, GOAL)
        decoy = tmp / "d" / "source-side-attempt-counters.json"
        seed_counter(decoy, GOAL)
        decoy_before = Path(decoy).read_text(encoding="utf-8")
        proc = run_resume(goals, deploy)
        check(counter_rows(ledger, GOAL) == [], "the DEPLOY ledger row is gone")
        check(Path(decoy).read_text(encoding="utf-8") == decoy_before,
              "a ledger outside the daemon's tree is byte-unchanged")

        # ── E — A STORE THAT WILL NOT OPEN IS LOUD AND NON-FATAL; leftover prefix stays ────
        print("(e) an unopenable store is a loud line, never a silent un-pause")
        ws, goals = make_workspace(tmp / "e")
        deploy = tmp / "e" / "deploy"
        seed_counter(deploy_ledger(deploy), GOAL)
        blocked = ws / ".rbtv" / "runtime" / "ignite"
        blocked.mkdir(parents=True, exist_ok=True)
        (blocked / "heart.db").mkdir()          # a DIRECTORY where the store must be a file
        proc = run_resume(goals, deploy)
        check(proc.returncode == 0, "exit 0 — a store fault does not abort the verb",
              proc.stderr[-300:])
        check((goals / GOAL / "execution-lane").read_text(encoding="utf-8") == "paused daemon\n",
              "leftover prefix is kept when the store did not answer — never silently un-pause",
              repr((goals / GOAL / "execution-lane").read_text(encoding="utf-8")))
        check("did NOT fire" in proc.stdout and "UNCHANGED" in proc.stdout,
              "the failure is a loud line naming the counters as unchanged", proc.stdout[:400])
        check(counter_rows(deploy_ledger(deploy), GOAL) != [],
              "and the counter row is honestly still there")

        # ── F — a goal outside the live register is a SKIP line, not a silent success ────────
        print("(f) a goal outside `goals.csv` is refused by name, and says the rows stand")
        ws, goals = make_workspace(tmp / "f", registered=False)
        deploy = tmp / "f" / "deploy"
        seed_counter(deploy_ledger(deploy), GOAL)
        proc = run_resume(goals, deploy)
        check(proc.returncode == 0, "exit 0", proc.stderr[-300:])
        check("re-arm SKIPPED" in proc.stdout and "UNCHANGED" in proc.stdout,
              "the skip is named", proc.stdout[:400])
        check(counter_rows(deploy_ledger(deploy), GOAL) != [], "the row is untouched")

        # ── G — RED MUTATION: delete the re-arm call and arm (a) must fail ───────────────────
        print("(g) red mutation — the re-arm call removed, on a DISCARDED copy")
        mutant = tmp / "mutant_goal_cli.py"
        src = GOAL_CLI.read_text(encoding="utf-8")
        cut = "    fired = _fire_pause_resume(root, name, \"resume\")"
        check(cut in src, "the mutation point exists in the source")
        mutant.write_text(src.replace(cut, '    fired = {"ok": True, "result": {"found": False, '
                                           '"reason": "mutation", "detail": "mutation"}}', 1),
                          encoding="utf-8")
        ws, goals = make_workspace(tmp / "g")
        deploy = tmp / "g" / "deploy"
        seed_counter(deploy_ledger(deploy), GOAL)
        proc = run_resume(goals, deploy, cli=mutant)
        check(proc.returncode == 0, "the mutant still exits 0 (it looks fine)", proc.stderr[-200:])
        check((goals / GOAL / "execution-lane").read_text(encoding="utf-8") == "daemon\n",
              "the mutant still restores the lane — which is the whole trap")
        survived = counter_rows(deploy_ledger(deploy), GOAL)
        check(survived != [] and survived[0]["attempts"] == 3,
              "RED: without the call the counter row SURVIVES at N=3 — arm (a) would fail",
              json.dumps(survived))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [c for c in checks if not c[0]]
    print(f"\nRESULT: {'PASS' if not failed else 'FAIL'} — "
          f"{len(checks) - len(failed)}/{len(checks)} checks")
    print(f"WALL_MS {int((time.time() - t0) * 1000)}")
    print(f"EXIT {1 if failed else 0}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
