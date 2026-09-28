#!/usr/bin/env python3
"""work_liveness — is the ignite system actually DOING work, or only ticking?

The one question no other watchdog row asks. Every other row grades a PROCESS: is the daemon
answering the gateway, is the Slack socket alive, did the probe suite fire recently. All three
can read `up` while the system schedules nothing at all — which is exactly the state that ran
from 2026-08-31T19:00Z to 2026-09-03T22:43Z: a healthy daemon, zero restarts, ticking every 11
seconds, no seat run for 46 hours, and an owner who found out by asking.

WHY THIS LIVES OUTSIDE THE DAEMON. Every signal that normally reaches the owner — an ask, an
alarm row, a digest — is minted by the machinery being watched, so a wedge anywhere upstream of
those producers is invisible by construction. This reads GROUND TRUTH off disk instead: the
sitting ledgers the daemon appends as it runs, the ask store, and the goal folders. It calls
nothing, and it trusts no component's report about itself.

THE PREDICATE — all three must hold before this says a word:

  1. There IS live work      — at least one goal holds a taskforce, is not dormant, is not a
                                fixture, and still has a seat that has not reached a terminal
                                outcome (see `_live_goals`).
  2. NOTHING awaits the owner — zero asks are open (the store's own §2.1 predicate: `state='open'
                                AND posted=1`, `state-store/predicates.js:48-55`). An open ask
                                means the silence is the system correctly waiting on a human. That
                                is legitimate and must never page: it is the designed state, not a
                                fault.
  3. SOME live goal has not run — evaluated PER GOAL, never as one fleet-wide maximum: each live
                                goal's OWN `executions.csv` is checked for a sitting that started
                                or ended within `stall_seconds`. A goal that never recorded a
                                sitting counts as stalled unconditionally — there is no sitting to
                                start a clock from, and treating "never ran" as healthy is exactly
                                the absence-reads-as-health failure this component exists to
                                remove. Clause 3 is satisfied (the row may alarm) when AT LEAST ONE
                                live goal is stalled — one busy goal can no longer mask a wedged
                                one (see `per_goal_sitting`, `assess`).

Only the CONJUNCTION is a fault. Each part alone is an ordinary state: an idle box with no live
goals, a system politely blocked on a question, a quiet hour between sittings. That is what keeps
this from becoming the always-on alarm an owner learns to ignore — the failure mode that kills a
real signal.

WHY CLAUSE 1 IS NOT `goal_states.stored = 'running'`. `goal_states` is written by the OWNER-RESUME
PATH ALONE (verified against the live store: every row's `who_stamped` is `owner`) — a goal the
daemon creates and drives itself never gets a row there. Requiring `stored = 'running'` would make
this row blind to exactly the goals it exists to watch, and the blindness would be silent: the row
would just go quiet forever and read as healthy. So clause 1 is read off ground truth the daemon
DOES write for every goal it runs — `taskforce.csv` (who is on the roster) and `seat_endings` (who
has finished) — never off a register only a human action populates. `goal_states` is still
consulted, but only to EXCLUDE a goal a human has explicitly stamped `paused`/`finished`/`closed`;
its absence is never treated as dormancy.

TIME COMPARISON IS LEXICAL, ON PURPOSE. Every stamp read here is ISO-8601 UTC with a `Z` suffix,
and so is the cutoff this builds, so string ordering IS chronological ordering. That is why this
module parses no dates and therefore does not carry a second copy of the watchdog's `utc_epoch`.
A fractional-second stamp sorts a hair before its whole-second twin; against a multi-hour
threshold that is not a difference that exists.
"""

import csv
import glob
import os
import sqlite3
import time

STORE_REL = os.path.join(".rbtv", "runtime", "ignite", "heart.db")
GOALS_REL = os.path.join(".rbtv", "goals")

# Goal words that mean "nobody expects this goal to advance right now" — every stored word except
# `running` (`state-store/vocabulary.js:8` GOAL_WORDS = ['running','paused','finished','closed'];
# `tables.sql:63` CHECK). `abandoned` is deliberately absent: it is not a goal word, the CHECK
# rejects it, and it can never be stored — keeping it here would be a second, wrong copy of a
# vocabulary this module does not own.
DORMANT_GOAL_WORDS = ("paused", "finished", "closed")

# A goal folder that exists only to be probed or exercised, and that nobody expects to keep
# producing real work — the probe suite's and the acceptance tests' throwaway runs (`test-*`) and
# scratch plan runs (`scratch-*`). Identified by NAME PREFIX because that is the one signal every
# fixture goal observed on this box already carries, and because this vault's own naming
# convention (kebab-case, evocative names — vault-root CLAUDE.md) never produces a real goal titled
# starting with a reserved probe prefix. The accepted cost: a real goal someone deliberately named
# `test-…` would be silently excluded from this one extra alarm. That failure is SAFE — the goal
# loses nothing but this row's paging, it does not vanish, misreport, or block — which is why a
# name prefix is an acceptable filter here where it would not be for anything destructive.
FIXTURE_PREFIXES = ("test-", "scratch-")

# The sitting ledger's two time columns. A sitting that STARTED counts as work happening just as
# much as one that ended — a seat running right now has no `ended` yet, and reading only `ended`
# would call a long live sitting a stall.
SITTING_TIME_COLUMNS = ("ended", "started")


def _cutoff(stall_seconds, now=None):
    """The ISO-8601 UTC instant before which a sitting is 'too long ago'."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ",
                         time.gmtime((now if now is not None else time.time()) - stall_seconds))


def _is_fixture(goal):
    return goal.startswith(FIXTURE_PREFIXES)


def per_goal_sitting(workspace, goals):
    """`{goal: (newest, ok)}` — EACH `goal`'s own latest sitting stamp, read from its OWN
    `executions.csv` only, never maxed across goals. `newest` is None when that goal has never
    recorded a sitting. `ok` is False when that goal's ledger EXISTS but could not be read
    (`OSError`/`csv.Error` — a mid-write or corrupt file), as opposed to a ledger that was simply
    never created. An unreadable ledger can only ever make `newest` OLDER than the truth, and an
    older answer is the ONE thing that can satisfy clause 3 and page — so the caller must treat
    `ok=False` as UNMEASURED (`skip`) for that goal, never fold it into an older-but-confident
    answer.

    Restricted to `goals` (defect 2): reading every goal's ledger let a sitting on a paused goal or
    a `test-*`/`scratch-*` fixture reset another goal's stall clock, which is exactly how the
    incident this row exists to catch stayed quiet. Only a sitting in the SAME population clause 1
    already decided is live work can testify that ITS OWN goal is doing something — one goal's
    recent sitting says nothing about a sibling goal's (defect: one busy goal masking a wedged one,
    `V3-final.md` row 2 of "V1's defects: fixed or not")."""
    result = {}
    for goal in goals:
        path = os.path.join(workspace, GOALS_REL, goal, "executions.csv")
        newest = None
        ok = True
        if os.path.exists(path):
            try:
                with open(path, newline="") as f:
                    for row in csv.DictReader(f):
                        for column in SITTING_TIME_COLUMNS:
                            stamp = (row.get(column) or "").strip()
                            if stamp and (newest is None or stamp > newest):
                                newest = stamp
            except (OSError, csv.Error):
                ok = False
        result[goal] = (newest, ok)
    return result


def _taskforce_seats(path):
    """The seat names on a goal's roster, or None when the file could not be read (missing means
    empty, not unreadable — `csv.DictReader` over zero data rows already yields an empty set)."""
    seats = set()
    try:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                seat = (row.get("seat") or "").strip()
                if seat:
                    seats.add(seat)
    except (OSError, csv.Error):
        return None
    return seats


def _live_goals(workspace, dormant, finished_seats):
    """Goal ids that hold a taskforce, are not dormant, are not a fixture, and still have at least
    one seat that has not reached a terminal outcome — clause 1's population, and (defect 2) the
    exact population `per_goal_sitting` is later restricted to.

    A seat counts as FINISHED only when `finished_seats` says so — built in `_store_facts` from
    `seat_endings.ending = 'done'` (clean success) or a row in `seat_abandonments` (the store's own
    SECOND terminal outcome, `tables.sql:174`, a lane the owner dropped for good). `incomplete` and
    `failed` do NOT count as finished: `isLaunchable` (`state-store/predicates.js`) allows a
    relaunch on both, and the live incident behind this row — `goal-master` stuck on `failed` while
    its goal still reads `running`, with nothing ever picking the lane back up — is precisely a
    `failed` seat that never becomes `done`. A seat with NO `seat_endings` row at all (never run,
    or run before this store existed) is unfinished for the same reason: absence is not
    completion, it is the un-measured case, and this predicate is never allowed to read absence as
    health."""
    live = []
    for path in glob.glob(os.path.join(workspace, GOALS_REL, "*", "taskforce.csv")):
        goal = os.path.basename(os.path.dirname(path))
        if goal.startswith("_") or goal in dormant or _is_fixture(goal):
            continue
        seats = _taskforce_seats(path)
        if seats and (seats - finished_seats.get(goal, set())):
            live.append(goal)
    return sorted(live)


def _store_facts(workspace):
    """(open_ask_count, dormant_goal_ids, finished_seats) read from the ending store, or
    (None, None, None) when the store cannot be read. None is NOT zero: an unreadable store means
    clause 2 (and clause 1's dormancy/finish facts) are UNMEASURED, and an unmeasured clause can
    never be counted as satisfied.

    `finished_seats` maps goal -> the set of seat names that have reached a terminal outcome
    (`seat_endings.ending = 'done'`, or a row in `seat_abandonments`) — clause 1's completion
    ground truth, read once here rather than re-derived per goal."""
    store = os.path.join(workspace, STORE_REL)
    if not os.path.exists(store):
        return None, None, None
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % store, uri=True)
        try:
            # §2.1's own predicate (`state-store/predicates.js:48-55` `listAllOpenAsks`):
            # `state = 'open' AND posted = 1`. `state` is `NOT NULL` (`tables.sql:86`), so there is
            # no `state is null` arm to carry.
            open_asks = conn.execute(
                "select count(*) from open_asks where state = 'open' and posted = 1"
            ).fetchone()[0]
            dormant = {row[0] for row in conn.execute(
                "select goal from goal_states where stored in (%s)"
                % ",".join("?" * len(DORMANT_GOAL_WORDS)), DORMANT_GOAL_WORDS)}
            finished_seats = {}
            for goal, seat in conn.execute(
                    "select goal, seat from seat_endings where ending = 'done'"):
                finished_seats.setdefault(goal, set()).add(seat)
            for goal, seat in conn.execute("select goal, seat from seat_abandonments"):
                finished_seats.setdefault(goal, set()).add(seat)
            return int(open_asks), dormant, finished_seats
        finally:
            conn.close()
    except sqlite3.Error:
        return None, None, None


def assess(workspace, stall_seconds, now=None):
    """Grade work-liveness. Returns the watchdog's (state, detail) pair.

    `up`    — every live goal ran recently, or somebody is waiting on the owner, or there is
              nothing to run.
    `alarm` — clauses 1 and 2 hold fleet-wide (live work exists, nobody is waiting on the owner)
              AND clause 3 finds AT LEAST ONE live goal individually stalled — that goal's own
              ledger recorded no sitting within `stall_seconds`, or none at all. One goal's recent
              sitting never covers for a sibling goal's silence (defect: one busy goal masking a
              wedged one — see `per_goal_sitting`). No restart fixes this, so this row never
              returns `down`.
    `skip`  — a clause could not be measured. NOT graded, and deliberately not `up`: closing a
              standing condition because nobody looked is the absence-reads-as-health failure this
              whole component exists to remove.

    The alarm detail names the WORST-stalled goal (a never-run goal outranks any timestamped one;
    among timestamped goals, the oldest sitting is worst) plus a count of the rest, never every
    stalled goal by name — a fleet with several live goals would otherwise blow past a one-line
    phone message. Clause 2 (open asks) stays fleet-wide, unchanged: an open ask anywhere is the
    system legitimately waiting on the owner, regardless of which goal it belongs to.
    """
    open_asks, dormant, finished_seats = _store_facts(workspace)
    if open_asks is None:
        return "skip", "cannot read the ending store at %s" % os.path.join(workspace, STORE_REL)

    live = _live_goals(workspace, dormant, finished_seats)
    if not live:
        return "up", "no live goal holds a taskforce — nothing is expected to run"
    if open_asks > 0:
        return "up", ("%d goal(s) live, %d ask(s) open — the silence is the system waiting on "
                      "the owner" % (len(live), open_asks))

    sittings = per_goal_sitting(workspace, live)
    unreadable = sorted(goal for goal, (_, ok) in sittings.items() if not ok)
    if unreadable:
        return "skip", ("cannot read a sitting ledger for a live goal (%s) — clause 3 is "
                        "unmeasured" % (", ".join(unreadable[:4]) +
                                        ("…" if len(unreadable) > 4 else "")))

    cutoff = _cutoff(stall_seconds, now)
    hours = stall_seconds / 3600.0
    stalled = sorted(
        (goal for goal, (newest, _ok) in sittings.items() if newest is None or newest < cutoff),
        key=lambda goal: (sittings[goal][0] is not None, sittings[goal][0] or ""))

    if not stalled:
        newest_overall = max((n for n, _ok in sittings.values() if n), default=None)
        return "up", ("%d goal(s) live, %d ask(s) open, last sitting %s"
                      % (len(live), open_asks, newest_overall))

    worst = stalled[0]
    worst_newest = sittings[worst][0]
    worst_desc = ("%s (no sitting ever recorded)" % worst if worst_newest is None
                 else "%s (silent since %s)" % (worst, worst_newest))
    more = ", +%d more" % (len(stalled) - 1) if len(stalled) > 1 else ""
    return "alarm", ("%d of %d live goal(s) stalled — worst: %s%s — no ask is waiting on the "
                     "owner, over the %.1fh limit" % (len(stalled), len(live), worst_desc, more,
                                                       hours))
