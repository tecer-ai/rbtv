#!/usr/bin/env python3
"""probe-watchdog-work-liveness — the `work-liveness` row alarms ONLY on the conjunction it was
built for, and never mistakes "nobody looked", "the owner is being asked", or "one goal is busy"
for health.

THE INCIDENT THIS PINS. 2026-08-31T19:00Z → 2026-09-03T22:43Z: the ignite daemon was healthy,
zero restarts, ticking every 11s, ran ZERO seats for 46 hours, and the owner found out by asking.
Every existing row (`daemon`, `bridge`, `probe-suite`) read `up` throughout — none of them asks
whether WORK is happening, only whether a process answers. `work_liveness.assess()`
(`tool/work_liveness.py`) is the new predicate; this probe is what keeps it honest.

THE FAILURE MODE THIS GUARDS AGAINST. A panel review of this same suite found 19 probes
quarantined KNOWN_RED so the suite "stays green", the probe-suite service configured
`SuccessExitStatus=0 1` so a RED verdict is recorded as a successful systemd run, and a PASSING
probe that asserts minting an owner ask while POSTING ZERO is acceptable — i.e. probes here have
proven the arm was built, not the outcome the owner needs. Two adversarial verifiers then
mutation-tested an earlier version of THIS probe and found it caught the obvious "always up" /
"always alarm" mutants while passing every mutant that reintroduced the real production defects:
fixture goals counted as live, a closed or unposted ask suppressing the alarm, a goal whose seats
were all finished still counted as live, an unreadable sitting ledger reading as healthy, and one
busy goal masking a wedged sibling. This version closes each of those gaps with a fixture case and
an assertion that a mutant reintroducing the bug actually fails. It also fixes a check that could
be satisfied by the WRONG state's text (2b matched both the `up` copy and the `alarm` copy).

WHAT IS SIMULATED. A scratch workspace per case: `.rbtv/goals/<goal>/taskforce.csv` +
`executions.csv` for goal/sitting/seat facts, and a real sqlite `heart.db` shaped like the live
store's `open_asks` (state, posted), `goal_states` (goal, stored), `seat_endings` (goal, seat,
ending) and `seat_abandonments` (goal, seat) tables — the exact columns `work_liveness.py` reads,
confirmed against the live schema at `.rbtv/runtime/ignite/heart.db`. `work_liveness.assess()` is
called directly against these fixtures with a fixed `now`, so no wall-clock sleep is needed and the
cutoff math is exact. Two cases are also driven through the REAL watchdog `main()` (`--dry-run` and
a real pass), to prove the row is actually wired into `ROWS` and that `skip` does not clear a
standing alarm the way `up` does — not only that the standalone predicate is correct. Nothing on
this box is probed, started, stopped or restarted; no real gateway or Slack call is reachable from
a scratch workspace with no install record and the notify file armed.

Exit 0 = every assertion held. Exit 1 = at least one failed.
"""
import csv
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL_DIR = os.path.join(os.path.dirname(HERE), "tool")
TOOL = os.path.join(TOOL_DIR, "rbtv-ignite-watchdog")
OUT = os.path.join(HERE, "probe-watchdog-work-liveness.out")

STALL_SECONDS = 3600  # 1h, so the probe does not have to sleep for real hours
NOW = 1_800_000_000.0  # fixed instant; every stamp below is computed relative to it

# A needle that appears in the `up` copy (`work_liveness.py` clause-2 branch: "the silence is the
# system waiting on the owner") and NOWHERE in the `alarm` copy ("no ask is waiting on the owner").
# Both copies contain the bare words "waiting on" — asserting that alone lets an ignore-asks mutant
# fail check 2 (state) and then PASS a state-blind text check on its own alarm string. Every check
# below that inspects `detail` for a specific state asserts `state` first.
UP_ASK_NEEDLE = "the silence is the system waiting"


def load_watchdog():
    spec = importlib.util.spec_from_loader(
        "rbtv_ignite_watchdog_under_probe",
        importlib.machinery.SourceFileLoader("rbtv_ignite_watchdog_under_probe", TOOL))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def stamp(delta_seconds):
    """ISO-8601 UTC with Z, `delta_seconds` before NOW — the exact shape `work_liveness` reads."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(NOW - delta_seconds))


def build_fixture(root, live_goals=(), taskforce=None, dormant_goal=None, dormant_word="paused",
                  sittings=None, broken_ledger_goals=(), seat_endings=None,
                  seat_abandonments=None, open_asks=0, ask_rows=None, broken_store=False):
    """A scratch `.rbtv/` tree with just enough of the ground truth `work_liveness.assess()`
    reads.

    `live_goals` — goal ids to give a `taskforce.csv`. Each gets one seat named `worker` unless
    `taskforce` (a `{goal: [seat, ...]}` map) names its own roster.
    `sittings` — `{goal: [(started, ended), ...]}`; a goal named here with an empty list, or not
    named at all, gets an `executions.csv` with a header row and zero data rows (never sat).
    `broken_ledger_goals` — goal ids whose `executions.csv` is a DIRECTORY, not a file — the shape
    of a ledger that exists but cannot be read (`IsADirectoryError`, an `OSError`), as opposed to
    one that was simply never created.
    `dormant_goal` / `dormant_word` — one goal stamped `stored=<dormant_word>` in `goal_states`
    (`paused`, `finished` or `closed` — the store's own dormancy vocabulary).
    `seat_endings` — `{goal: [(seat, ending), ...]}`, inserted into `seat_endings`.
    `seat_abandonments` — `{goal: [seat, ...]}`, inserted into `seat_abandonments`.
    `open_asks` — sugar for N rows of `('open', 1)` in `open_asks`. `ask_rows` — `[(state,
    posted), ...]`, for exact control over the population; when given it REPLACES the `open_asks`
    sugar rather than adding to it, so a case is never accidentally testing two ask populations at
    once.
    `broken_store` — `heart.db` exists but is not a readable sqlite file (mid-rewrite / corrupt),
    distinct from a store that was never created at all.
    """
    goals_dir = os.path.join(root, ".rbtv", "goals")
    for goal in live_goals:
        gdir = os.path.join(goals_dir, goal)
        os.makedirs(gdir, exist_ok=True)
        seats = (taskforce or {}).get(goal, ["worker"])
        with open(os.path.join(gdir, "taskforce.csv"), "w") as f:
            f.write("seat\n" + "\n".join(seats) + "\n")
        exec_path = os.path.join(gdir, "executions.csv")
        if goal in broken_ledger_goals:
            os.makedirs(exec_path, exist_ok=True)  # a directory where a file is expected
            continue
        rows = (sittings or {}).get(goal, [])
        with open(exec_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["started", "ended"])
            for started, ended in rows:
                w.writerow([started, ended])
    if dormant_goal:
        gdir = os.path.join(goals_dir, dormant_goal)
        os.makedirs(gdir, exist_ok=True)
        with open(os.path.join(gdir, "taskforce.csv"), "w") as f:
            f.write("seat\nworker\n")

    store_dir = os.path.join(root, ".rbtv", "runtime", "ignite")
    os.makedirs(store_dir, exist_ok=True)
    store = os.path.join(store_dir, "heart.db")
    if broken_store:
        # A file that EXISTS but is not a readable sqlite database — the shape of a store mid
        # rewrite or corrupted, not a store that was never created.
        with open(store, "wb") as f:
            f.write(b"not a sqlite database\x00\x01\x02")
        return
    conn = sqlite3.connect(store)
    try:
        # Columns match the live schema's names exactly (`open_asks.state`, `.posted`;
        # `goal_states.goal`, `.stored`; `seat_endings.goal/seat/ending`;
        # `seat_abandonments.goal/seat`) — confirmed against `.rbtv/runtime/ignite/heart.db`. Only
        # the columns `work_liveness.py` actually queries are declared; the live table's CHECK
        # constraints and bookkeeping columns (label, evidence_pointer, who_stamped, ...) are not
        # this predicate's concern.
        conn.execute("create table open_asks (id integer primary key, state text, posted integer)")
        conn.execute("create table goal_states (goal text, stored text)")
        conn.execute("create table seat_endings (goal text, seat text, ending text)")
        conn.execute("create table seat_abandonments (goal text, seat text)")
        rows = ask_rows if ask_rows is not None else [("open", 1)] * open_asks
        for state, posted in rows:
            conn.execute("insert into open_asks (state, posted) values (?, ?)", (state, posted))
        if dormant_goal:
            conn.execute("insert into goal_states (goal, stored) values (?, ?)",
                        (dormant_goal, dormant_word))
        for goal, endings in (seat_endings or {}).items():
            for seat, ending in endings:
                conn.execute("insert into seat_endings (goal, seat, ending) values (?, ?, ?)",
                            (goal, seat, ending))
        for goal, seats in (seat_abandonments or {}).items():
            for seat in seats:
                conn.execute("insert into seat_abandonments (goal, seat) values (?, ?)",
                            (goal, seat))
        conn.commit()
    finally:
        conn.close()


def main():
    log, fails = [], []

    def say(s):
        log.append(s)

    def check(name, ok, detail=""):
        say("%-4s %s%s" % ("PASS" if ok else "FAIL", name, ("  — " + detail) if detail else ""))
        if not ok:
            fails.append(name)

    sys.path.insert(0, TOOL_DIR)
    import work_liveness  # noqa: E402 — the module under test, loaded after the fixture path is set

    scratch = tempfile.mkdtemp(prefix="rbtv-watchdog-work-liveness-")
    try:
        # --- 1. ALL THREE CLAUSES HOLD -> alarm, naming the stalled goal -----------------------
        w1 = os.path.join(scratch, "case1")
        build_fixture(w1, live_goals=["goal-a"],
                      sittings={"goal-a": [(stamp(STALL_SECONDS + 7200), stamp(STALL_SECONDS + 7100))]},
                      open_asks=0)
        state, detail = work_liveness.assess(w1, STALL_SECONDS, now=NOW)
        check("1. live work + no open ask + stale sitting -> alarm", state == "alarm",
              "%s: %s" % (state, detail))
        check("1b. alarm names the stalled goal", state == "alarm" and "goal-a" in detail, detail)

        # --- 1c. ONE BUSY GOAL DOES NOT MASK A WEDGED SIBLING (per-goal clock) -----------------
        # Defect fixed by seat `stall-clock-per-goal`: `newest_sitting` used to take the MAX
        # timestamp across every live goal, so a recent sitting on goal-busy reset the clock for
        # goal-wedged too. Each goal's own ledger must now testify only for itself.
        w1c = os.path.join(scratch, "case1masking")
        build_fixture(w1c, live_goals=["goal-busy", "goal-wedged"],
                      sittings={"goal-busy": [(stamp(30), "")]},  # 30s ago, well inside the window
                      open_asks=0)  # goal-wedged: no sittings entry -> never recorded one
        state, detail = work_liveness.assess(w1c, STALL_SECONDS, now=NOW)
        check("1c. a busy goal does not mask a wedged sibling -> alarm naming goal-wedged",
              state == "alarm" and "goal-wedged" in detail, "%s: %s" % (state, detail))

        # --- 2. AN ASK IS OPEN -> up, EVEN THOUGH THE OTHER TWO CLAUSES STILL HOLD ------------
        # The false-positive guard: this is the state that must NEVER page, because the silence
        # is the system correctly waiting on a human, not the system being wedged.
        w2 = os.path.join(scratch, "case2")
        build_fixture(w2, live_goals=["goal-a"],
                      sittings={"goal-a": [(stamp(STALL_SECONDS + 7200), stamp(STALL_SECONDS + 7100))]},
                      ask_rows=[("open", 1)])
        state, detail = work_liveness.assess(w2, STALL_SECONDS, now=NOW)
        check("2. live work + stale sitting BUT an open, posted ask -> up (never alarm)",
              state == "up", "%s: %s" % (state, detail))
        check("2b. detail carries the up-only ask needle (not the alarm copy's)",
              state == "up" and UP_ASK_NEEDLE in detail, detail)

        # --- 2c. A CLOSED ASK MUST NOT SUPPRESS THE ALARM --------------------------------------
        w2c = os.path.join(scratch, "case2closed")
        build_fixture(w2c, live_goals=["goal-a"],
                      sittings={"goal-a": [(stamp(STALL_SECONDS + 7200), stamp(STALL_SECONDS + 7100))]},
                      ask_rows=[("closed", 1)])
        state, detail = work_liveness.assess(w2c, STALL_SECONDS, now=NOW)
        check("2c. a closed ask does not suppress -> alarm", state == "alarm",
              "%s: %s" % (state, detail))

        # --- 2d. AN UNPOSTED ASK MUST NOT SUPPRESS THE ALARM -----------------------------------
        w2d = os.path.join(scratch, "case2unposted")
        build_fixture(w2d, live_goals=["goal-a"],
                      sittings={"goal-a": [(stamp(STALL_SECONDS + 7200), stamp(STALL_SECONDS + 7100))]},
                      ask_rows=[("open", 0)])
        state, detail = work_liveness.assess(w2d, STALL_SECONDS, now=NOW)
        check("2d. an open-but-unposted (posted=0) ask does not suppress -> alarm",
              state == "alarm", "%s: %s" % (state, detail))

        # --- 3. A SITTING IS RECENT -> up -------------------------------------------------------
        w3 = os.path.join(scratch, "case3")
        build_fixture(w3, live_goals=["goal-a"],
                      sittings={"goal-a": [(stamp(30), "")]},  # started 30s ago, still running
                      open_asks=0)
        state, detail = work_liveness.assess(w3, STALL_SECONDS, now=NOW)
        check("3. live work + no open ask + recent sitting -> up", state == "up",
              "%s: %s" % (state, detail))

        # --- 4. NO LIVE GOAL -> up ---------------------------------------------------------------
        w4 = os.path.join(scratch, "case4")
        build_fixture(w4, live_goals=[], open_asks=0)
        state, detail = work_liveness.assess(w4, STALL_SECONDS, now=NOW)
        check("4. no live goal -> up (nothing is expected to run)", state == "up",
              "%s: %s" % (state, detail))

        # a goal that is dormant must not count as live, for EACH dormancy word the store allows.
        for suffix, word in (("b", "paused"), ("c", "finished"), ("d", "closed")):
            wd = os.path.join(scratch, "case4" + suffix)
            build_fixture(wd, live_goals=[], dormant_goal="goal-dormant", dormant_word=word,
                         open_asks=0)
            state, detail = work_liveness.assess(wd, STALL_SECONDS, now=NOW)
            check("4%s. a %s goal -> up, not counted as live" % (suffix, word), state == "up",
                  "%s: %s" % (state, detail))

        # --- 4e. A FIXTURE GOAL (test-*/scratch-*) MUST NOT COUNT AS LIVE ----------------------
        # This is the exact "cry-wolf population" a live re-run found: the probe suite's and
        # acceptance tests' own throwaway goals. Given a stale sitting and no other live goal, a
        # fixture goal that wrongly counted as live would alarm; correctly excluded, there is
        # nothing to run. `FIXTURE_PREFIXES` names TWO prefixes (`test-`, `scratch-`) — a probe
        # that only ever constructs a `test-*` goal would ship green on a mutant that drops the
        # `scratch-` prefix alone (judge finding XA), so both prefixes get their own case here.
        w4e = os.path.join(scratch, "case4e")
        build_fixture(w4e, live_goals=["test-probe-run"],
                      sittings={},  # never sat — the worst case, so a wrong inclusion alarms loudly
                      open_asks=0)
        state, detail = work_liveness.assess(w4e, STALL_SECONDS, now=NOW)
        check("4e. a test-* fixture goal -> up, not counted as live", state == "up",
              "%s: %s" % (state, detail))

        w4e2 = os.path.join(scratch, "case4e2")
        build_fixture(w4e2, live_goals=["scratch-plan-run"],
                      sittings={},  # never sat — the worst case, so a wrong inclusion alarms loudly
                      open_asks=0)
        state, detail = work_liveness.assess(w4e2, STALL_SECONDS, now=NOW)
        check("4e2. a scratch-* fixture goal -> up, not counted as live", state == "up",
              "%s: %s" % (state, detail))

        # --- 4f. A GOAL WHOSE SEATS ARE ALL FINISHED MUST NOT COUNT AS LIVE --------------------
        w4f = os.path.join(scratch, "case4f")
        build_fixture(w4f, live_goals=["goal-done"], sittings={},
                      seat_endings={"goal-done": [("worker", "done")]}, open_asks=0)
        state, detail = work_liveness.assess(w4f, STALL_SECONDS, now=NOW)
        check("4f. a goal whose only seat ended 'done' -> up, not counted as live",
              state == "up", "%s: %s" % (state, detail))

        # a goal with one abandoned seat and no other seat is equally finished (the store's SECOND
        # terminal outcome — `seat_abandonments`, not just `seat_endings`).
        w4g = os.path.join(scratch, "case4g")
        build_fixture(w4g, live_goals=["goal-abandoned"], sittings={},
                      seat_abandonments={"goal-abandoned": ["worker"]}, open_asks=0)
        state, detail = work_liveness.assess(w4g, STALL_SECONDS, now=NOW)
        check("4g. a goal whose only seat was abandoned -> up, not counted as live",
              state == "up", "%s: %s" % (state, detail))

        # --- 4h. A GOAL WITH ONE FINISHED SEAT AND ONE STILL OPEN STAYS LIVE -------------------
        # The counterpart to 4f/4g: "all seats finished" excludes the goal; "some seat unfinished"
        # must NOT, or a mutant that drops the `finished_seats` check entirely would slip past 4f.
        w4h = os.path.join(scratch, "case4h")
        build_fixture(w4h, live_goals=["goal-partial"], taskforce={"goal-partial": ["helper", "worker"]},
                      sittings={},  # never sat -> if correctly live, this must alarm
                      seat_endings={"goal-partial": [("helper", "done")]}, open_asks=0)
        state, detail = work_liveness.assess(w4h, STALL_SECONDS, now=NOW)
        check("4h. a goal with one finished seat and one open seat -> still live -> alarm",
              state == "alarm" and "goal-partial" in detail, "%s: %s" % (state, detail))

        # --- 5. THE STORE IS UNREADABLE -> skip, NEVER up ---------------------------------------
        # The absence-reads-as-health guard: "nobody looked" must never be reported as "healthy".
        w5 = os.path.join(scratch, "case5")
        build_fixture(w5, live_goals=["goal-a"], broken_store=True)
        state, detail = work_liveness.assess(w5, STALL_SECONDS, now=NOW)
        check("5. unreadable store -> skip (NOT up)", state == "skip", "%s: %s" % (state, detail))

        w5b = os.path.join(scratch, "case5b")
        # store never created at all — same guard, the other way a store can be "unreadable"
        os.makedirs(os.path.join(w5b, ".rbtv", "goals", "goal-a"), exist_ok=True)
        with open(os.path.join(w5b, ".rbtv", "goals", "goal-a", "taskforce.csv"), "w") as f:
            f.write("seat\n")
        state, detail = work_liveness.assess(w5b, STALL_SECONDS, now=NOW)
        check("5b. store never created -> skip (NOT up)", state == "skip", "%s: %s" % (state, detail))

        # --- 5c. A LIVE GOAL'S SITTING LEDGER IS UNREADABLE -> skip, NEVER up ------------------
        # Exercises `assess()` itself (not a monkey-patch of the row function) with a live goal
        # whose OWN `executions.csv` cannot be read — the ledger half of the unmeasured-input
        # guard, distinct from case 5/5b's store half.
        w5c = os.path.join(scratch, "case5c")
        build_fixture(w5c, live_goals=["goal-wedged"], broken_ledger_goals=["goal-wedged"],
                     open_asks=0)
        state, detail = work_liveness.assess(w5c, STALL_SECONDS, now=NOW)
        check("5c. unreadable sitting ledger for a live goal -> skip (NOT up)", state == "skip",
              "%s: %s" % (state, detail))

        # --- 6. INTEGRATION: the row is actually wired into the real watchdog -------------------
        w6 = os.path.join(scratch, "case6")
        build_fixture(w6, live_goals=["goal-a"],
                      sittings={"goal-a": [(stamp(STALL_SECONDS + 7200), stamp(STALL_SECONDS + 7100))]},
                      open_asks=0)
        # `work_liveness.assess()` takes `now=None` inside the tool (real wall clock) — real time
        # must actually exceed STALL_SECONDS for the alarm path to fire through main(), so this
        # leg uses a genuinely old sitting (10x the stall window) instead of a fixed `now`.
        really_old = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                   time.gmtime(time.time() - STALL_SECONDS * 10))
        with open(os.path.join(w6, ".rbtv", "goals", "goal-a", "executions.csv"), "w", newline="") as f:
            w_ = csv.writer(f)
            w_.writerow(["started", "ended"])
            w_.writerow([really_old, really_old])
        os.environ.update({
            "RBTV_WATCHDOG_WORKSPACE": w6,
            "RBTV_WATCHDOG_TARGETS": "work-liveness",
            "RBTV_WATCHDOG_WORK_STALL_SECONDS": str(STALL_SECONDS),
            "RBTV_WATCHDOG_LEDGER": os.path.join(w6, "ledger.jsonl"),
            "RBTV_WATCHDOG_NOTIFY_FILE": os.path.join(w6, "notify.jsonl"),
            "RBTV_SYSTEM_CHANNEL_ID": "C-PROBE-SYSTEM",
        })
        os.environ.pop("RBTV_WATCHDOG_ROW_ALARMS", None)
        os.environ.pop("RBTV_WATCHDOG_STATE", None)
        wd = load_watchdog()  # module-level WORKSPACE is resolved at load time — env must be set first
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = wd.main(["--dry-run"])
        out = buf.getvalue()
        check("6. --dry-run through the real ROWS table reads alarm for work-liveness",
              rc == 0 and "work-liveness alarm" in out, out.strip()[:200])
        check("6b. dry-run raises nothing", "would raise watchdog-work-liveness-alarm" in out,
              out.strip()[:200])

        # a REAL (non-dry) pass opens the registry row …
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = wd.main([])
        row_alarms = read_json(os.path.join(w6, ".rbtv", "runtime", "watchdog", "row-alarms.json"), {})
        check("6c. a real pass opens the work-liveness row in row-alarms",
              "work-liveness" in row_alarms, json.dumps(row_alarms))

        # … and a `skip` pass right after must NOT clear it — the absence-reads-as-health guard,
        # proven at the integration level: `main()` only clears an alarm on `up`, never on `skip`.
        wd2 = load_watchdog()
        wd2.probe_work_liveness = lambda: ("skip", "simulated: store unreadable this pass")
        wd2.ROWS = dict(wd2.ROWS)
        wd2.ROWS["work-liveness"] = (wd2.probe_work_liveness, wd2._work_liveness_has_no_restart,
                                     wd2.ROWS["work-liveness"][2])
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = wd2.main([])
        row_alarms_after = read_json(os.path.join(w6, ".rbtv", "runtime", "watchdog", "row-alarms.json"), {})
        check("6d. a skip pass leaves the standing alarm OPEN (skip never clears)",
              "work-liveness" in row_alarms_after, json.dumps(row_alarms_after))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
        for k in ("RBTV_WATCHDOG_WORKSPACE", "RBTV_WATCHDOG_TARGETS", "RBTV_WATCHDOG_WORK_STALL_SECONDS",
                 "RBTV_WATCHDOG_LEDGER", "RBTV_WATCHDOG_NOTIFY_FILE", "RBTV_SYSTEM_CHANNEL_ID"):
            os.environ.pop(k, None)

    say("")
    say("%d checks, %d failed" % (len([l for l in log if l[:4] in ("PASS", "FAIL")]), len(fails)))
    text = "\n".join(log)
    print(text)
    with open(OUT, "w") as f:
        f.write(text + "\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
