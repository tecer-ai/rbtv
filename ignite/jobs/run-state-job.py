#!/usr/bin/env python3
"""run-state-job — recompute every seat's RUN STATE from disk, on demand, per seat (task 7.127 /
M4-12, from 7.56 item (b)).

One computation shared by human, agent and daemon. Registered as a `fire-tool` job so the daemon
runs the SAME code an operator runs by hand — a second implementation for the daemon's benefit is
the defect this file is bounded against.

⚠⚠ IT COMPUTES; IT NEVER READS A STORED STATE, BECAUSE THERE IS NONE TO READ. There is no status
column anywhere in this system and none is ever added (Rule 14). A cached answer is a second source
that will disagree with the graph the moment either moves, and the disagreement is silent — the
cache keeps answering. Every state below is derived at the instant of the call from check-out
records, declared outputs, the `after` sets and the roster.

WHAT THIS FILE DOES NOT DO
--------------------------
It does not decide anything and it launches nothing. It is a pure read whose output another actor
acts on. It writes NO file — not a log, not a cache, not a status column (`--selftest` proves the
csv headers are byte-identical across a full pass).

**NOTHING ARMS FROM THIS FILE.** Registering a job DEFINITION in the catalogue is create-only and
fires nothing: `add-job` schedules a run, and that is the arming instrument
(`cli/commands/register-job.js` § REGISTER vs ADD; the queue's own foreign key
`queue.job_id REFERENCES jobs.job_id`). So this file does not touch `r-cutover-gated` (m4 criterion
C4), and the live run's control loop stays untouched. **The registration is NOT PERFORMED here and
is not claimed** — see THE REGISTRATION, below.

THE READER PROBLEM — WHY EVERY ANSWER HERE IS *CALLED*, NEVER RE-DERIVED
-----------------------------------------------------------------------
Two readers of one graph that disagree is `issues.md` G-301, where `taskforce_after()` and
`goal_cli.check_acyclic` read one `after` cell differently and the lint reports nothing wrong. This
task exists partly to not repeat that, so it owns NO predicate of its own:

| The answer | The one reader it is taken from |
|---|---|
| is a seat's check-out `done` / `failed` | `edge-runner-job.verify` → coord's ONE disposition reader |
| are its declared outputs on disk | `edge-runner-job.declared_outputs` |
| are its `after` predecessors satisfied | `edge-runner-job.readiness` → `coord.taskforce_after` |
| is it OCCUPIED right now | `coord.ready_seat_rows`' own `active` term |

This file performs no comma split of its own, holds no second disposition scan, and states no
second readiness rule.
`--selftest`'s `uses-existing-predicate` check proves that by identity and by source search, not by
intent — a re-implementation that agreed today would still fail it.

⚠ `running` COMES FROM THE ROSTER, AND THAT IS A RULING, NOT A PREFERENCE
------------------------------------------------------------------------
`decisions.md#p-recompute-cli-reads-RUNNING-from-the-ROSTER` (leader PROVISIONAL, 2026-07-30): this
CLI derives `running` from an ACTIVE roster row via `ready_seat_rows()`, **not** from the trace's
empty `ended` cell. Two reasons, the first dispositive: (a) this CLI must AGREE with the kit's
predicate, which uses the roster, so a trace-derived answer fails by construction; (b) measured the
same night — two DAG roots sat with LIVE harnesses that had never checked in. The trace reading
calls those `running`, which is true of the PROCESS and false of the WORK; the roster reading calls
them not-running, which is what the operator needed.

`trace-field-audit.md` §2.4 had recorded the trace reading as taken. That record stands as the
documented alternative and is not rewritten; the ruling overrode it.

**Required rider of that same ruling, and the reason `divergences` exists below:** where the two
readings disagree — the CRASHED-SEAT shape, an open session row with an inactive roster row — this
CLI **REPORTS** the row instead of silently normalizing it. Both fields are present, so no reader is
blind either way. Every divergence is printed to STDERR as well as carried in the JSON, so it cannot
be missed by a reader who did not opt in.

⚠⚠ `skipped` IS REACHABLE — THE UNREACHABILITY CLAIM IS RETIRED (task 7.454 / MC12)
------------------------------------------------------------------------------------
`skipped` is the DAG-authoring Rule 10 marking for a row excluded by a guard, so that a join never
waits on an un-taken branch. It was carried in the vocabulary and reported unreachable for exactly
as long as no guard evaluator existed. **Task 7.425 built one.** `edge-runner-job.readiness` now
returns the guard-excluded rows as a THIRD verdict list beside `ready` and `blocked`, and this CLI
routes that list into the state, so a guard-excluded row is reported `skipped`.

The claim was retired in the SAME change that made the state emittable, because a file that prints
*"skipping cannot happen"* while emitting the state is worse than a file that says nothing: a
reader who believes the note reads every emitted row as a bug in the CLI. What the OUTPUT says now
is the honest successor claim — an absence of `skipped` rows means NO ROW WAS GUARD-EXCLUDED on
this package, which is a measurement about this graph, where the retired claim was about the
machinery. See `GUARD_EXCLUDED_NOTE`.

⚠ ONE WORD, TWO MEANINGS IN THIS WAVE — DO NOT CONFLATE THEM. `edge-runner-job.py`'s enqueue stage
(M4-10) also has a `skipped`, and it means *"a ready seat the self-state intersection excluded from
enqueueing"*. **This file's `skipped` is the guard-excluded RUN STATE.** Same word, two surfaces,
and both fire on real rows now — which makes the collision matter MORE than when it was reported to
the `leader` (message #275), not less. M4-10 owns that surface; this file names the collision and
does not resolve it.

THE REGISTRATION — DECLARED, AUTHORED VERBATIM, AND *NOT* PERFORMED
------------------------------------------------------------------
`REGISTER_INVOCATION` below is the exact command that registers this file as a job. **It has not
been run.** Three independent obstacles, all measured rather than assumed:

  1. NO CREDENTIAL. `ignite inspect jobs` and `ignite register-job … --dry-run` BOTH return
     `ERROR [AUTH_REFUSED] authentication required` — even the validate-only path — and
     `IGNITE_SENDER_TOKEN` is unset. The only owner-token grant on record covers exactly two
     unrelated calls of task 7.53 (`decisions.md#r-owner-token-reseed`).
  2. NOT THIS SEAT'S VERB. `register-job` belongs to another seat's grant; this seat's floor is
     `ignite inspect` only.
  3. NO `run-state` TOOL ENTRY (task 7.587). `config/spawn-profiles.yaml` carries no `run-state`
     key, so the `add-job` that schedules the registered row is refused `E_UNKNOWN_TOOL` at the
     enqueue door. `--registration` prints this obstacle in full; this list is the SAME three, and
     the two must not drift apart.

Ruled by the `leader` (#271, answering #270): author the invocation verbatim-and-unrun, land
everything else, and disclose the criterion as UNMET-FOR-CREDENTIAL. **It is disclosed, never
claimed.** `--registration` prints the command and this status.
"""

import argparse
import csv
import importlib.util
import inspect as _inspect
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDGE_RUNNER_PATH = HERE / "edge-runner-job.py"

# ---- THE STATE VOCABULARY — closed, spelled out, and compared against literally ---------------
#
# `blocked` is the SIXTH state, and it is a leader ruling rather than this seat's improvisation
# (#271, answering ask #270). The five originally declared for 7.127 carry no state for a seat whose
# predecessor is unfinished, and that is not an edge case: measured by the leader on the live graph,
# 44 seats split DONE=29 / BLOCKED=11 / READY=2 / RUNNING=2 — `blocked` is 11 of the 15 rows NOT YET
# DONE, i.e. roughly three quarters of all work that still has anywhere to go.
#
# It COINS NOTHING (PRIN-10): `blocked` is already the settled term in BOTH readers over this graph
# — `edge-runner-job.VERDICTS == ("ready", "blocked")` and `coord.ready_seat_rows`' `BLOCKED`.
#
# The two REJECTED alternatives are recorded so neither is re-tried as an improvement:
#   * `state: null` + a reason — REFUSED by the leader. A null a reader may default is the exact
#     defect ruled on the same night: a seat's EMPTY disposition cell defaulted to `done` advances
#     the DAG past a seat that never worked (G-leader-0730-0647). The wave had just been bitten by
#     one nullable field; it does not get a second.
#   * omitting blocked rows — the silent omission this whole task exists to prevent. A reader would
#     conclude "no rows are blocked" when the truth is "blocked rows were not printed".
STATES = ("done", "ready", "running", "skipped", "failed", "blocked")

# The guard-excluded state, held as its own constant so the check over it cannot be satisfied by a
# coincidence of wording elsewhere. It was `UNREACHABLE_STATE` until task 7.454: the NAME asserted a
# property the code no longer has, and the next agent reads a constant's name long before it reads
# any comment under it.
GUARD_EXCLUDED_STATE = "skipped"

# Printed on EVERY run and in `--help`. The claim is checkable by RUNNING the CLI, so this text must
# never retreat into a comment. Spelled out literally here and asserted literally by the check — a
# check that read its expectation from this constant would move with it and prove nothing.
#
# SUPERSEDES the retired `UNREACHABLE_NOTE` (task 7.454). What it said, kept so the change is
# legible and nobody re-derives the old claim from its absence: "`skipped` is DEFINED AND CURRENTLY
# UNREACHABLE … NO guard evaluator exists to produce it — so no seat can ever be reported skipped.
# Read an absence of `skipped` rows as \"skipping CANNOT happen\" …". That was true of M4-09's
# world and is FALSE of this one: task 7.425 built the evaluator. Its two cited causes, issues.md
# G-301 and G-308, are NOT thereby closed — whether either is closed is the leader's call on those
# rows, not this CLI's; they simply stopped being the reason this state could not be produced.
GUARD_EXCLUDED_NOTE = (
    "`skipped` is the GUARD-EXCLUDED verdict, and it is REACHABLE. It is DAG-authoring Rule 10's "
    "marking for a row whose guard was EVALUATED and did not match — the row is excluded so a join "
    "never waits on an un-taken branch — and it is produced by readiness()'s third verdict list, "
    "which task 7.425 built. Read an absence of `skipped` rows as \"NO ROW WAS GUARD-EXCLUDED on "
    "this package\": that is a measurement about THIS graph. It is no longer a statement about the "
    "machinery — the earlier claim of unreachability was RETIRED by task 7.454, in the same change "
    "that made the state emittable. A guard that could not be READ is a third answer again: such a "
    "row is UNEVALUABLE and stays `blocked`, never `skipped`. So `skipped` always means an edge was "
    "evaluated and excluded, and never means an edge nobody could evaluate."
)

# ---- THE DECLARED READ INVENTORY — closed, and asserted against the audit off disk ------------
#
# `field=None` marks a read SITE that resolves to no column, carried visibly rather than dropped.
# Every row below is already in `trace-field-audit.md`'s `reads[]` for task 7.56 item (b) — THIS
# CLI — and the check proves that by set arithmetic against the audit file, not against a copy.
SESSIONS = "{RUN}/sessions.csv"
SEAT_MD_OUTPUTS = "{RUN}/seats/*/seat.md"
TASKFORCE = "{RUN}/taskforce.csv"
WORKERS = "{RUN}/coordination/workers.md"

READS = [
    (SESSIONS, "seat"),          # audit row 1  — which rows belong to which seat
    (SESSIONS, "ended"),         # audit row 2  — did it finish; and row 6, the open-row divergence
    (SESSIONS, "disposition"),   # audit row 3  — the durable check-out value
    (TASKFORCE, "after"),        # audit row 4  — the predecessor set
    (TASKFORCE, "seat"),         # audit row 5  — which row each `after` cell belongs to
    (WORKERS, "agent"),          # audit row 7  — the roster half of `running` (RULED reading)
    (WORKERS, "active"),         # audit row 8  — ditto
    (SEAT_MD_OUTPUTS, None),     # audit row 14 — declared outputs; no column resolves this site
]

# Audit row 15 is the `skipped` site. It audits to NO COLUMN — the state is DERIVED, computed from
# `readiness()`'s third verdict list (task 7.425), so there is no column anywhere to read (Rule 14)
# — but it is NOT a no-surface site any more, and the audit's own reason clause said it was.
# Carried here as a declared NON-read so the absence of a column is a recorded fact rather than an
# omission, and the check below asserts BOTH halves: that row 15 still resolves to no column, and
# that it no longer claims the state is unreachable. The second half is what makes the audit
# correction load-bearing instead of cosmetic (leader ruling, run-3 decisions.md
# #p-mc12-granted-the-audit-row-claim-not-the-folder, rider 2).
SKIPPED_SITE_AUDIT_ROW = 15

# The literal the retired claim is recognised by, at the audit. Spelled out here so the check keys
# on the CLAIM and not on the word "unreachable", which the audit's own SUPERSEDED-by note has to
# use in order to say what it retired — a check that matched the abstract word would fire on the
# sentence retiring it.
RETIRED_AUDIT_CLAIM = "no guard evaluator is built"

# The state precedence, spelled out as data so the check can assert the ORDER and not merely the
# outcomes. Its first three terms match `coord.ready_seat_rows`' own order (terminal before occupied
# before the `after` term), which is what keeps the two surfaces from disagreeing on a
# finished-but-still-rostered seat. The last THREE are not competitors at all: `ready`, `blocked`
# and `skipped` are the three disjoint outcomes of the one `after` term, and they appear here in
# the order the branch chain writes them, which is `readiness()`'s own return order. `skipped`
# joined this tuple with the arm, in the same change (task 7.454).
PRECEDENCE = ("done", "failed", "running", "ready", "blocked", "skipped")


def load_module(path, name):
    """Import a sibling script whose filename is not a Python identifier (hyphens)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_edge_runner():
    """The M4-09 stage, imported as a module. Its `readiness` is THE predicate this CLI uses."""
    if not EDGE_RUNNER_PATH.exists():
        print("error: the readiness predicate is absent at %s — this CLI owns no predicate of its "
              "own and cannot answer without it." % EDGE_RUNNER_PATH, file=sys.stderr)
        sys.exit(2)
    return load_module(EDGE_RUNNER_PATH, "edge_runner_job")


def _args_for(pkg):
    """An args-shaped object for `coord.ready_seat_rows`.

    `workers_dir` is supplied EXPLICITLY. Left unset, `coord.workers_dir` resolves the package with
    `register=True`, which WRITES the package into this machine's runs index — a read-only command
    must never register a run, and a temp fixture must never become one."""
    class _A:
        package = str(pkg)
        base = str(pkg / "coordination")
        workers_dir = str(pkg / "seats")
        run = None
    return _A()


def open_session_seats(coord, pkg):
    """{seat} with at least one session row whose `ended` cell is EMPTY — an OPEN sitting.

    Read with coord's OWN csv primitives, never a private parser. This is the trace half of the
    divergence rider only: it decides NO state. The `running` verdict comes from the roster
    (`p-recompute-cli-reads-RUNNING-from-the-ROSTER`), and this set exists purely so a crashed seat
    — open trace row, inactive roster row — is REPORTED rather than normalized away."""
    path = coord.sessions_csv(pkg)
    if not path.exists():
        return set()
    header, rows = coord.read_csv_table(path, coord.SESSIONS_COLS)
    idx = {c: i for i, c in enumerate(header)}
    if not {"seat", "ended"} <= set(idx):
        return set()
    out = set()
    for r in rows:
        coord.pad_row(r, header)
        seat = r[idx["seat"]].strip()
        if seat and not r[idx["ended"]].strip():
            out.add(seat)
    return out


def run_state(coord, er, pkg):
    """`{rows: [{seat, state, reason, ...}], divergences, not-in-graph, caveats, unreachable}`.

    Every state is DERIVED at the instant of this call. Nothing is cached, nothing is stored, and no
    status column is read — there is none.

    The graph is `taskforce.csv`'s rows, which is what BOTH existing readers iterate. A seat with a
    trace row and no roster row is NOT given a graph state (it has no `after` set to have one) — it
    is reported under `not-in-graph` with its mark, so it is never silently dropped."""
    marks = {r["seat"]: r for r in er.run_stage(coord, pkg)}
    ready_res = er.readiness(coord, pkg, {s: m["disposition"] for s, m in marks.items()})
    ready_set = set(ready_res["ready"])
    blocked_by_seat = {b["seat"]: b for b in ready_res["blocked"]}
    # 7.454: the THIRD verdict list, taken from the producer's own return exactly like the other
    # two. This CLI decides no exclusion for itself — the guard evaluator is `readiness()`'s
    # (task 7.425), and a second one here would be issues.md G-301 rebuilt at a new seam.
    skipped_by_seat = {s["seat"]: s for s in ready_res["skipped"]}

    # The ROSTER term, taken from the kit's own predicate rather than by re-reading workers.md.
    coord_rows = {r["seat"]: r for r in coord.ready_seat_rows(_args_for(pkg))}
    open_sessions = open_session_seats(coord, pkg)

    graph = coord.taskforce_after(pkg)
    rows, divergences = [], []

    for seat, preds in graph.items():
        mark = marks.get(seat, {}).get("disposition")
        mark_reason = (marks.get(seat, {}).get("reason")
                       or marks.get(seat, {}).get("undecided-reason"))
        active = bool(coord_rows.get(seat, {}).get("active"))

        # PRECEDENCE — terminal, then occupied, then the `after` term. Never a default: every
        # branch below is entered on a positive reading, and the final branch is `blocked`, which
        # is itself a positive reading (readiness NAMED at least one unmet predecessor).
        if mark == "done":
            state, why = "done", mark_reason
        elif mark == "failed":
            state, why = "failed", mark_reason
        elif active:
            state, why = "running", "roster: ACTIVE row — the seat is occupied now"
        elif seat in ready_set:
            state, why = "ready", (ready_res["self-marks"].get(seat) and
                                   "every `after` predecessor is `done`") or \
                                  "every `after` predecessor is `done`"
        elif seat in blocked_by_seat:
            state, why = "blocked", blocked_by_seat[seat]["reason"]
        elif seat in skipped_by_seat:
            # 7.454 — THE GUARD-EXCLUDED ARM. Before it, a row in `readiness()`'s third list matched
            # no branch and fell to the refusal below, so the CLI printed `NO-STATE` for a row the
            # producer had answered perfectly well. The reason is the producer's own, not a sentence
            # composed here: it names the excluded member and the field values that excluded it.
            state, why = "skipped", skipped_by_seat[seat]["reason"]
        else:
            # Unreachable by construction: `readiness` returns every graph row in exactly one of
            # its THREE lists. Carried as a LOUD refusal rather than a silent fallthrough, because a
            # quiet else-branch here would be indistinguishable from a real state.
            state, why = None, ("NO STATE COMPUTED — this seat is in `taskforce.csv` but in "
                                "neither list `readiness` returned. That is impossible by "
                                "construction, so treat it as a defect in this CLI, never as a "
                                "state.")

        row = {"seat": seat, "state": state, "reason": why, "after": list(preds),
               "evidence-read": list(marks.get(seat, {}).get("evidence-read") or [])}
        if state == "running" or seat in open_sessions:
            row["evidence-read"].append("%s::active" % WORKERS)
        rows.append(row)

        # THE RIDER — report, never normalize. Both divergence directions are named.
        if seat in open_sessions and not active:
            divergences.append({
                "seat": seat, "class": "crashed-seat",
                "trace": "an OPEN session row (`ended` empty)", "roster": "NOT active",
                "state-reported": state,
                "note": ("the two readings disagree. The TRACE reading would call this seat "
                         "`running`, which is true of the PROCESS and false of the WORK; the "
                         "ROSTER reading is the ruled one and is what this row reports "
                         "(p-recompute-cli-reads-RUNNING-from-the-ROSTER). Reported, never "
                         "normalized: a harness may still be alive with nobody working.")})
        elif active and mark is not None:
            divergences.append({
                "seat": seat, "class": "terminal-but-roster-active",
                "trace": "a terminal check-out `%s`" % mark, "roster": "still ACTIVE",
                "state-reported": state,
                "note": ("the seat declared an ending but its roster row was never closed. The "
                         "terminal mark WINS here, matching coord.ready_seat_rows' own precedence "
                         "— but the stale roster row is real and is reported.")})

    not_in_graph = [{"seat": s, "mark": m["disposition"],
                     "reason": m["reason"] or m["undecided-reason"]}
                    for s, m in marks.items() if s not in graph]

    return {
        "rows": rows,
        "divergences": divergences,
        "not-in-graph": not_in_graph,
        # Renamed from `unreachable` with the arm (task 7.454) — the key asserted the property the
        # change removed. No consumer outside this file read it (swept at HEAD 3e9493d9).
        "skipped-state": {"state": GUARD_EXCLUDED_STATE, "statement": GUARD_EXCLUDED_NOTE},
        "caveats": [
            "every state here is COMPUTED from disk at the instant of this call. No status column "
            "is read and none exists; there is no cache to go stale.",
            "`running` is the ROSTER reading, ruled: an ACTIVE roster row via ready_seat_rows(), "
            "not the trace's empty `ended` cell "
            "(decisions.md#p-recompute-cli-reads-RUNNING-from-the-ROSTER).",
            "the `after` term is `readiness()`'s, CALLED. This CLI owns no predicate: two readers "
            "of one graph that disagree is issues.md G-301, which this task exists to not repeat.",
            "a `not-in-graph` seat has a trace row and no `taskforce.csv` row, so it has no `after` "
            "set and is given NO graph state — it is listed, never dropped.",
            "`skipped` is the GUARD-EXCLUDED verdict, routed from readiness()'s third list "
            "(task 7.425). An absence of `skipped` rows means no row was guard-excluded on THIS "
            "package; the machinery-level claim that the state could not be produced at all was "
            "retired by task 7.454, in the change that made it emittable.",
        ],
    }


# =================================================================================================
# CHECKS — the probe set. Every expectation is spelled out LITERALLY; not one is read from the
# value under test. A check whose expected value is computed by the code it guards moves with that
# code and passes any change to it.
# =================================================================================================

AUDIT = (HERE.parents[4] / ".rbtv" / "goals" / "build-core-daemon-mvp" / "runs" / "run-3"
         / "planning" / "m4-workflow-engine-runs-DAG-edged-jobs" / "trace-field-audit.md")

# The fixture's expected states, written out BY HAND. Not one is computed from the predicate, from
# the fixture's own tables, or from the mark table.
EXPECT_STATE = {
    # terminal marks — `done` requires a clean check-out AND its declared outputs on disk
    "fx-done-outputs-present": "done",
    "fx-done-output-missing": "failed",   # clean `done`, declared artifact absent
    "fx-renew": "failed",
    "fx-revive": "failed",
    "fx-exited": "failed",
    "fx-empty-disposition": "failed",     # ended with an EMPTY cell — unknown, never done
    "fx-renewed-then-done": "done",
    "fx-no-iospec": "done",
    "fx-open-sitting": "running",         # roster ACTIVE — the ruled reading, and it OUTRANKS the
                                          # empty `after` cell that would otherwise read `ready`
    # No trace row and no roster row, but its `after` cell is EMPTY — so the `after` term is
    # satisfied vacuously and `ready` is correct. This entry first read `blocked`, which was this
    # seat INFERRING an unmet predecessor it never looked up; the check caught it. A root with no
    # predecessors is ready whether or not anything has ever sat in it.
    "fx-no-row": "ready",
    # the `after`-set rows
    "fx-r-root": "ready",
    "fx-r-one-done": "ready",
    "fx-r-two-done": "ready",
    "fx-r-spaces": "ready",
    "fx-r-failed-pred": "blocked",
    "fx-r-exited-pred": "blocked",
    "fx-r-undecided-pred": "blocked",
    "fx-r-mixed": "blocked",
    "fx-r-dangling": "blocked",
    "fx-r-conditional": "blocked",
    # AMENDED by 7.454, and it is the one entry in this table that MOVED rather than being added.
    # Its cell is `fx-done-outputs-present|fx-renewed-then-done` and both alternates mark `done`.
    # This entry read `blocked` because it was written against M4-09's reader, which treated the
    # whole cell as ONE uninterpreted predecessor name that no seat answered to. 7.425 evaluates
    # `|`, so the join is met on whichever alternate ran. Derived from the cell and the mark table,
    # not from a run: the corroboration is that edge-runner-job.EXPECT_READY — a hand table in
    # another file — records the same move with the same rationale at its own line.
    "fx-r-alternate": "ready",
    "fx-r-artifact-strict": "blocked",
    # 7.425's guard rows, given expectations by 7.454. Every one is derived from the fixture's own
    # shape: the `after` cell's text, `fx-route`'s validated output `{"risk": "high", "count": 2,
    # "ok": true}`, and the mark table. None has a roster row and only `fx-route` has a session row,
    # so each falls to the `after` term. The rule that separates the two non-ready outcomes is
    # `readiness()`'s own and is stated in its caveats: a guard EVALUATED and not matched excludes
    # the row (`skipped`); a guard that could not be READ leaves it UNEVALUABLE (`blocked`).
    "fx-route": "done",                    # checked out `done`; declares route.json, and it exists
    "fx-r-guard-hit": "ready",             # [risk=high] — risk IS high
    "fx-r-guard-miss": "skipped",          # [risk=low] — risk is high; evaluated and EXCLUDED
    "fx-r-guard-bool": "ready",            # [ok=true] — ok is true; the RHS is always text
    "fx-r-guard-number": "ready",          # [count=2] — count is 2
    "fx-r-guard-nofield": "blocked",       # [colour=blue] — no such field: UNEVALUABLE
    "fx-r-guard-unfinished": "blocked",    # fx-renew marks `failed` — no validated output to read
    "fx-r-malformed-guard": "blocked",     # [nokey] — no `=`: UNEVALUABLE
    "fx-r-join-one-taken": "ready",        # one alternate admitted — the join is met
    "fx-r-join-none-taken": "skipped",     # both evaluated, neither matched — the join is excluded
    "fx-r-join-malformed": "blocked",      # [risk=a|b] — malformed guard text: UNEVALUABLE
    "fx-r-skip-propagates": "skipped",     # its predecessor is skipped — exclusion propagates
    "fx-r-block-beats-skip": "blocked",    # conjunction: one member excluded, one still UNDECIDED —
                                           # a live unmet predecessor outranks an excluded one
    # roster-driven rows this fixture adds on top of M4-09's graph
    "fx-active-clean": "running",          # active roster row, no terminal mark
    "fx-crashed": "blocked",               # OPEN trace row + INACTIVE roster -> the rider's shape
    "fx-done-but-active": "done",          # terminal mark WINS over an active roster row
}

EXPECT_DIVERGENCE = {
    "fx-crashed": "crashed-seat",
    "fx-done-but-active": "terminal-but-roster-active",
}


def check_states_are_the_declared_vocabulary(coord, er, pkg):
    """CRITERION 1 — every emitted state is one of the six declared values, and the vocabulary
    itself is exactly the six spelled out. A seventh value appearing in output, or the tuple
    quietly growing, is red."""
    if STATES != ("done", "ready", "running", "skipped", "failed", "blocked"):
        return False, ("criterion 1: STATES is %r, expected exactly the five declared for 7.127 "
                       "plus `blocked` (leader #271)" % (STATES,))
    res = run_state(coord, er, pkg)
    if not res["rows"]:
        return False, ("criterion 1: ZERO rows emitted — an empty result would satisfy every "
                       "vocabulary assertion vacuously")
    bad = [(r["seat"], r["state"]) for r in res["rows"] if r["state"] not in STATES]
    if bad:
        return False, ("criterion 1: %d row(s) carry a state outside the declared vocabulary: %s"
                       % (len(bad), bad))
    nostate = [r["seat"] for r in res["rows"] if r["state"] is None]
    if nostate:
        return False, ("criterion 1: %d row(s) got NO state at all: %s — every graph row must "
                       "carry one" % (len(nostate), nostate))
    return True, ("criterion 1: all %d rows carry a state drawn from the declared %d "
                  "(%s)" % (len(res["rows"]), len(STATES), ", ".join(sorted(
                      {r["state"] for r in res["rows"]}))))


def check_states_match_expected_table(coord, er, pkg):
    """CRITERION 1 + the discriminating controls — every fixture row gets the state the LITERAL
    table names.

    Three controls carry the design and would each pass under a plausible wrong reading:
      * `fx-done-output-missing` checked out a clean `done` and its declared artifact is ABSENT.
        Reading the check-out alone gives `done`; the correct answer is `failed`.
      * `fx-done-but-active` has a terminal mark AND an active roster row. Reading the roster
        first gives `running`; the correct answer is `done`.
      * `fx-crashed` has an OPEN trace row and an INACTIVE roster row. The trace reading gives
        `running`; the RULED roster reading gives its `after`-term state."""
    res = run_state(coord, er, pkg)
    got = {r["seat"]: r["state"] for r in res["rows"]}
    bad = []
    for seat, want in EXPECT_STATE.items():
        if seat not in got:
            bad.append("%s: no row at all" % seat)
        elif got[seat] != want:
            bad.append("%s: expected %s, got %s" % (seat, want, got[seat]))
    extra = sorted(set(got) - set(EXPECT_STATE))
    if extra:
        bad.append("rows with no expectation in the table: %s" % extra)
    if bad:
        return False, "criterion 1/controls: %d wrong state(s): %s" % (len(bad), "; ".join(bad))
    counts = {}
    for v in EXPECT_STATE.values():
        counts[v] = counts.get(v, 0) + 1
    return True, ("criterion 1/controls: all %d fixture states correct (%s); the three "
                  "discriminating controls hold"
                  % (len(EXPECT_STATE),
                     ", ".join("%s=%d" % kv for kv in sorted(counts.items()))))


def check_no_stored_state_is_read(coord, er, pkg):
    """CRITERION 2 — the state is DERIVED, never read from a stored column, and this CLI writes
    nothing.

    Three assertions, because "derives" has three failure modes:
      (a) no csv on the package carries a status-like column;
      (b) this file's own source contains no read of one;
      (c) a FULL pass leaves every csv header AND every csv byte unchanged — a CLI that cached its
          answer would have to write somewhere."""
    forbidden = ("status", "state", "verdict", "run-state", "runstate")
    csvs = sorted(pkg.glob("*.csv"))
    if not csvs:
        return False, "criterion 2: no csv found under %s — nothing to check" % pkg
    before = {p: p.read_bytes() for p in csvs}
    for p in csvs:
        with p.open(newline="", encoding="utf-8") as fh:
            header = next(csv.reader(fh), [])
        for col in header:
            if col.strip().lower() in forbidden:
                return False, ("criterion 2: %s carries a stored-state column %r — the CLI must "
                               "compute, and no status column may exist" % (p.name, col))
    src = Path(__file__).read_text(encoding="utf-8")
    # Assembled from fragments ON PURPOSE, so this check's own source is not a hit for the search
    # it performs. Spelling the markers out inline made the check fail on its own text — observed,
    # not theorised.
    q1, q2 = '"', "'"
    for marker in ("idx[%sstatus%s]" % (q1, q1), "row[%sstatus%s]" % (q2, q2),
                   "row[%sstatus%s]" % (q1, q1), "[%srun-state%s]" % (q1, q1)):
        if marker in src:
            return False, ("criterion 2: this file reads a stored-state column (%r found in its "
                           "own source)" % marker)
    run_state(coord, er, pkg)
    changed = [p.name for p in csvs if p.read_bytes() != before[p]]
    if changed:
        return False, ("criterion 2: a full pass CHANGED %s — this CLI must write nothing at all"
                       % changed)
    return True, ("criterion 2: %d csv(s) carry no stored-state column, this file reads none, and "
                  "a full pass left every byte of all %d unchanged" % (len(csvs), len(csvs)))


def check_uses_existing_predicate(coord, er, pkg):
    """CRITERION 3 — the readiness answer comes from M4-09's predicate BY CALL, and this file
    contains no second predicate.

    Proven three ways, none of them by intent:
      (a) IDENTITY — the function this CLI calls is the very object defined in edge-runner-job.py,
          asserted by module of origin. A copied-and-pasted equivalent fails this.
      (b) CALL SITE — `run_state`'s own source calls `er.readiness(`, and this file's source
          defines no predicate of that name (the search string is assembled from fragments below,
          so this docstring is not itself a hit — spelling it out here made the check red on its
          own text, twice).
      (c) NO PRIVATE PARSE — the `after` cell has exactly one runtime parse
          (`coord.taskforce_after`, comma-only). A comma split anywhere in this file would be
          G-301 rebuilt at a new seam. The needle is assembled from fragments so that neither this
          docstring nor the search line is a hit for the search itself."""
    if er.readiness.__module__ != "edge_runner_job":
        return False, ("criterion 3: the readiness function's module is %r, not the imported "
                       "edge-runner stage — this CLI is not using M4-09's predicate"
                       % er.readiness.__module__)
    src = Path(__file__).read_text(encoding="utf-8")
    # Assembled from two fragments so this check's own text is not a hit for its own search.
    if ("def " + "readiness") in src:
        return False, ("criterion 3: this file DEFINES a readiness function — a second predicate "
                       "over one graph is exactly G-301's shape")
    body = _inspect.getsource(run_state)
    if "er.readiness(" not in body:
        return False, ("criterion 3: `run_state` does not call the imported predicate — its "
                       "readiness answer is coming from somewhere else")
    needle = "split(" + '"' + "," + '"'
    lines = [i + 1 for i, ln in enumerate(src.splitlines())
             if needle in ln.replace(" ", "")]
    if lines:
        return False, ("criterion 3: this file splits a cell on comma at line(s) %s — the `after` "
                       "parse has ONE reader (coord.taskforce_after) and this is a second" % lines)
    # The disposition VALUE must likewise come from coord's one reader, via the edge-runner stage.
    # Needle assembled, same reason as the two above: the check must not be a hit for itself.
    if ("session" + "_disposition") in src:
        return False, ("criterion 3: this file names coord's disposition reader directly — the "
                       "disposition is the edge-runner stage's to read, and a second call site "
                       "here is a second grader")
    return True, ("criterion 3: readiness is the imported edge_runner_job.readiness (called in "
                  "`run_state`), this file defines no predicate, splits no cell on comma, and "
                  "reads no disposition itself")


def check_agrees_with_readiness_surface(coord, er, pkg):
    """CRITERION 4 — the CLI and the existing readiness surface give the SAME per-seat answer.

    THE IDENTITY, stated as `readiness()`'s OWN schema declares it — over THREE lists, not two.
    That predicate returns a TOTAL PARTITION of the graph across its closed verdict vocabulary
    `edge-runner-job.VERDICTS`: every `taskforce.csv` row lands in exactly one of its verdict
    lists. So for a seat with no terminal mark and no active roster row, this CLI's `state` must
    equal THE NAME OF THE LIST THAT HOLDS IT. Seats excluded by a terminal mark or an active roster
    row are excluded from the comparison rather than silently swallowed — those are this CLI's
    extra terms, not disagreements — and both exclusion sets are counted and named below.

    Task 7.455 / MC13 rewrote this arm. It built its expectation from `ready` + `blocked` ONLY,
    enumerated by hand. A guard-excluded seat is in neither, so the surface side read `None`; and
    before task 7.454's `skipped` arm this CLI also said `None` for those rows, so `None == None`
    and the arm passed VACUOUSLY ON EXACTLY THE ROWS IT EXISTS TO COMPARE — it reported "26
    comparable seat(s), agree on every one" in a run whose sibling arm found three guard-excluded
    rows. The defect was the hand enumeration itself, so the fix is SHAPED against its recurrence:

      (a) the expectation is driven off `er.VERDICTS` and read out of `readiness()`'s own return,
          so a verdict added to the producer extends this comparison instead of escaping it;
      (b) a verdict declared with no list, or a per-seat list the vocabulary does not declare, is
          REPORTED (MC13 F-13b) — never compared around;
      (c) the lists are asserted to be a PARTITION: a seat in two of them is red, because the
          identity above presupposes exactly one verdict per row;
      (d) ⚠ AN UNCLASSIFIED ROW IS RED, NEVER AGREEMENT. A compared seat in NO verdict list makes
          both sides `None`, and `None == None` is the vacuity this rewrite exists to end — in the
          general form, not only for `skipped`.

    The expectation is built from the PRODUCER (`edge-runner-job`), never from this file, which is
    the code under test: a guard that reads its own constant moves with the code and proves nothing.

    The comparison is COMPUTED here, per seat, and the count is reported WITH its per-verdict
    breakdown — so a run that compares many rows while exercising a verdict zero times is visible
    rather than hidden inside a healthy-looking total. A vacuous comparison (zero comparable
    seats) is RED."""
    res = run_state(coord, er, pkg)
    marks = {r["seat"]: r["disposition"] for r in er.run_stage(coord, pkg)}
    ready_res = er.readiness(coord, pkg, marks)

    # (a) + (c) — the expectation, off the producer's own vocabulary and its own return. Nothing is
    # enumerated by hand: `ready` is a list of seat names, `blocked`/`skipped` lists of rows keyed
    # `seat`, and both shapes are read the same way.
    theirs, double = {}, []
    for verdict in er.VERDICTS:
        if verdict not in ready_res:
            return False, ("criterion 4: `readiness()` declares the verdict `%s` in VERDICTS %r "
                           "but its return carries NO SUCH LIST — the producer and its own closed "
                           "vocabulary disagree, so no expectation can be built over it (MC13 "
                           "F-13b)" % (verdict, list(er.VERDICTS)))
        for row in ready_res[verdict]:
            seat = row if isinstance(row, str) else row["seat"]
            if seat in theirs:
                double.append("%s: %s and %s" % (seat, theirs[seat], verdict))
            theirs[seat] = verdict
    if double:
        return False, ("criterion 4: `readiness()`'s verdict lists are NOT a partition — %d seat(s) "
                       "appear in two of them: %s. The identity this arm asserts presupposes "
                       "exactly one verdict per row." % (len(double), "; ".join(double)))
    # (b) — a per-seat list outside the declared vocabulary would be compared against nothing at
    # all, which is the hand-enumeration defect returning under a new name.
    strays = sorted(k for k, v in ready_res.items()
                    if k not in er.VERDICTS and isinstance(v, list) and v
                    and all(isinstance(e, dict) and "seat" in e for e in v))
    if strays:
        return False, ("criterion 4: `readiness()` returns per-seat list(s) %s that VERDICTS %r "
                       "does not declare — an undeclared verdict list is exactly the drift this "
                       "arm was rewritten to catch (MC13 F-13b). Report it to the leader; do not "
                       "compare around it." % (strays, list(er.VERDICTS)))

    coord_rows = {r["seat"]: r for r in coord.ready_seat_rows(_args_for(pkg))}
    per_verdict = dict.fromkeys(er.VERDICTS, 0)
    by_terminal, by_roster, unclassified, disagree = [], [], [], []
    compared = 0
    for r in res["rows"]:
        seat = r["seat"]
        if marks.get(seat) is not None:
            by_terminal.append(seat)      # terminal mark — this CLI's own extra term
            continue
        if coord_rows.get(seat, {}).get("active"):
            by_roster.append(seat)        # occupied — likewise
            continue
        compared += 1
        expected = theirs.get(seat)
        if expected is None:              # (d) — never let `None == None` read as agreement
            unclassified.append("%s: cli=%s" % (seat, r["state"]))
            continue
        per_verdict[expected] += 1
        if r["state"] != expected:
            disagree.append("%s: cli=%s surface=%s" % (seat, r["state"], expected))
    if not compared:
        return False, ("criterion 4: ZERO comparable seats — every row was excluded, so agreement "
                       "would be vacuous")
    if unclassified:
        return False, ("criterion 4: %d comparable seat(s) are in the graph but in NONE of "
                       "`readiness()`'s %d verdict lists: %s. Both sides are then `None` and the "
                       "comparison would PASS on rows nobody classified — that vacuity is red "
                       "here, never agreement." % (len(unclassified), len(er.VERDICTS),
                                                   "; ".join(unclassified)))
    if disagree:
        return False, ("criterion 4: %d seat(s) DISAGREE with the readiness surface: %s. STOP — do "
                       "not adjust either reader to match; a disagreement between two readers of "
                       "one graph is a finding for the leader."
                       % (len(disagree), "; ".join(disagree)))
    # The exclusion sets are NAMED, and where naming them all would bury the counts they are named
    # up to a cap WITH THE ELISION STATED. The COUNT is never elided and never approximate: on the
    # live run-3 package the terminal-mark term excludes 363 seats, and one line of 363 names is
    # how a reported number becomes unreadable — which is the same failure as swallowing it.
    def named(seats, cap=12):
        s = sorted(seats)
        if not s:
            return "none"
        if len(s) <= cap:
            return ", ".join(s)
        return "%s, … +%d more NOT LISTED (count above is exact)" % (", ".join(s[:cap]), len(s) - cap)
    return True, ("criterion 4: %d comparable seat(s) compared against readiness() over ALL %d of "
                  "its verdict lists %r, broken down %s — the CLI and the surface agree on every "
                  "one. EXCLUDED AND NAMED, not swallowed: %d by this CLI's terminal-mark term "
                  "(%s), %d by its active-roster term (%s); %d compared + %d excluded = %d "
                  "taskforce row(s)."
                  % (compared, len(er.VERDICTS), list(er.VERDICTS),
                     ", ".join("%s=%d" % (v, per_verdict[v]) for v in er.VERDICTS),
                     len(by_terminal), named(by_terminal),
                     len(by_roster), named(by_roster),
                     compared, len(by_terminal) + len(by_roster), len(res["rows"])))


def check_skipped_is_emitted_and_explained(coord, er, pkg):
    """CRITERION 5, SUCCEEDING the retired unreachability check (task 7.454) — the CLI EMITS the
    guard-excluded state, emits exactly the rows `readiness()` excluded, explains the state in its
    own OUTPUT, and no longer prints the retired claim anywhere.

    The predecessor asserted that no row is ever reported `skipped`. The arm makes that false, so
    the check is REPLACED rather than deleted: the state's vocabulary keeps a check over it, and
    the successor is strictly stronger — the old one passed on a CLI that could not produce the
    state at all, this one fails on exactly that CLI.

    Five assertions, because "emits the third state" has five failure modes:
      (a) the emitted `skipped` set is EXACTLY `readiness()`'s third verdict list, read off the
          producer's own return. This CLI owns no predicate, so agreement with the producer is
          what correct MEANS here — an emitted set of this CLI's own devising would be G-301;
      (b) that list is NON-EMPTY on this fixture, or the set equality in (a) holds vacuously;
      (c) each excluded seat is printed as `SKIPPED` in the PLAIN run's stdout, not only inside a
          JSON a reader has to opt into;
      (d) a normal run and `--help` both explain what the state means, on literal phrases, so
          rewording the note red-flags here instead of silently dropping the claim;
      (e) neither prints the RETIRED claim. A file that emits `skipped` while telling its reader
          that skipping cannot happen is worse than one that says nothing, so the retirement is
          CHECKED and not merely intended."""
    must_appear = ("the GUARD-EXCLUDED verdict",
                   "readiness()'s third verdict list",
                   "NO ROW WAS GUARD-EXCLUDED")
    # The retired claim's own literal sentences. Matched on the CLAIM, never on the word
    # "unreachability" — which the retirement note itself must use to say what it retired, so a
    # check keyed on the abstract word would fire on the sentence that does the retiring.
    must_not_appear = ("DEFINED AND CURRENTLY UNREACHABLE",
                       "no seat can ever be reported",
                       "skipping CANNOT happen")
    for flags, label in ((["--package", str(pkg)], "a normal run's output"),
                         (["--help"], "--help")):
        proc = subprocess.run([sys.executable, str(Path(__file__).resolve())] + flags,
                              capture_output=True, text=True)
        blob = proc.stdout + proc.stderr
        missing = [p for p in must_appear if p not in blob]
        if missing:
            return False, ("criterion 5: %s does not explain `%s` — missing %s. A vocabulary entry "
                           "a reader cannot interpret is one they will misread."
                           % (label, GUARD_EXCLUDED_STATE, missing))
        retired = [p for p in must_not_appear if p in blob]
        if retired:
            return False, ("criterion 5: %s still prints the RETIRED unreachability claim %s while "
                           "this CLI emits the state — a file that does is worse than silent"
                           % (label, retired))
    res = run_state(coord, er, pkg)
    emitted = {r["seat"] for r in res["rows"] if r["state"] == GUARD_EXCLUDED_STATE}
    theirs = {s["seat"] for s in er.readiness(
        coord, pkg, {r["seat"]: r["disposition"] for r in er.run_stage(coord, pkg)})["skipped"]}
    if not theirs:
        return False, ("criterion 5: `readiness()` excluded ZERO rows on this fixture, so the set "
                       "comparison below would hold vacuously — the fixture must carry at least "
                       "one guard-excluded row for this check to mean anything")
    if emitted != theirs:
        return False, ("criterion 5: the emitted `%s` set is not `readiness()`'s third list — "
                       "only in the CLI: %s; only in the surface: %s"
                       % (GUARD_EXCLUDED_STATE, sorted(emitted - theirs), sorted(theirs - emitted)))
    proc = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                           "--package", str(pkg)], capture_output=True, text=True)
    lines = [ln.split()[:2] for ln in proc.stdout.splitlines() if ln.split()]
    unseen = [s for s in sorted(theirs) if [GUARD_EXCLUDED_STATE.upper(), s] not in lines]
    if unseen:
        return False, ("criterion 5: %d excluded seat(s) never appear as `%s` in the plain run's "
                       "stdout: %s — a state only in a data structure is one nobody sees"
                       % (len(unseen), GUARD_EXCLUDED_STATE.upper(), unseen))
    return True, ("criterion 5: %d row(s) emitted `%s` and the set is EXACTLY readiness()'s third "
                  "list (%s); each is printed as %s in the plain run; both a normal run and --help "
                  "explain the state, and neither carries the retired unreachability claim"
                  % (len(emitted), GUARD_EXCLUDED_STATE, ", ".join(sorted(emitted)),
                     GUARD_EXCLUDED_STATE.upper()))


def check_reads_subset_of_audit():
    """CRITERION 2 (reads) — every field this CLI reads was audited, by set arithmetic against the
    audit file ON DISK. A field added to READS but never audited fails here rather than being read
    silently in production.

    Row 15 (`skipped`) carries TWO assertions since task 7.454, and the second is the point:
      * it must still audit to NO column — `skipped` is derived state and no column resolves it
        (Rule 14), which the guard evaluator did not change;
      * it must NOT still say the state is unreachable. That clause was measured false the moment
        7.425 built the evaluator, and this check ASSERTED it, so the green outlived the fact it
        stood for. Retired here in the same change that corrects the audit itself (leader ruling,
        run-3 decisions.md #p-mc12-granted-the-audit-row-claim-not-the-folder, rider 2), and proven
        able to go RED against an audit copy carrying the old clause."""
    if not AUDIT.exists():
        return False, "reads: the audit file is absent at %s — cannot verify" % AUDIT
    er = load_edge_runner()
    pairs, nulls = er.audited_pairs(AUDIT)
    if not pairs:
        return False, ("reads: parsed ZERO audited field rows from %s — the parse is broken, and "
                       "an empty audited set would let every read pass vacuously" % AUDIT)
    unaudited = []
    for surface, field in READS:
        if field is None:
            if not any("seat.md" in s and "io-spec" in s for s in nulls):
                unaudited.append("%s::<io-spec> Outputs" % surface)
        elif (surface, field) not in pairs:
            unaudited.append("%s::%s" % (surface, field))
    if unaudited:
        return False, ("reads: %d read site(s) are NOT in the audit's reads[]: %s. Report the "
                       "field to the leader; do not read it." % (len(unaudited), ", ".join(unaudited)))
    # Row 15 — the guard-excluded state's site. It resolves to no column, and (7.454) it must no
    # longer carry the retired claim.
    row15 = [ln for ln in AUDIT.read_text(encoding="utf-8").splitlines()
             if ln.startswith("| %d " % SKIPPED_SITE_AUDIT_ROW)]
    if not row15:
        return False, ("reads: audit row %d (the `%s` site) is absent — this declared NON-read has "
                       "no audited record" % (SKIPPED_SITE_AUDIT_ROW, GUARD_EXCLUDED_STATE))
    if GUARD_EXCLUDED_STATE not in row15[0] or "no column resolves this site" not in row15[0]:
        return False, ("reads: audit row %d no longer records `%s` as a site no column resolves — "
                       "it now reads: %s"
                       % (SKIPPED_SITE_AUDIT_ROW, GUARD_EXCLUDED_STATE, row15[0][:200]))
    if RETIRED_AUDIT_CLAIM in row15[0]:
        return False, ("reads: audit row %d still asserts %r, which task 7.425 made false when it "
                       "built the guard evaluator. This CLI now EMITS `%s`, so an audit saying the "
                       "state cannot be produced disagrees with the code it audits. Row reads: %s"
                       % (SKIPPED_SITE_AUDIT_ROW, RETIRED_AUDIT_CLAIM, GUARD_EXCLUDED_STATE,
                          row15[0][:200]))
    return True, ("reads: all %d declared read sites appear in the audit's reads[] (%d audited "
                  "field rows, %d null-field rows); row %d still records `%s` as a site no column "
                  "resolves, and no longer claims the state is unproducible"
                  % (len(READS), len(pairs), len(nulls), SKIPPED_SITE_AUDIT_ROW,
                     GUARD_EXCLUDED_STATE))


def check_divergences_are_reported(coord, er, pkg):
    """THE RULED RIDER — divergent rows are REPORTED, not normalized.

    `p-recompute-cli-reads-RUNNING-from-the-ROSTER` requires the crashed-seat shape (open session
    row, inactive roster row) to be surfaced rather than silently taking the roster answer. Both
    divergence classes are asserted by the literal table, and the note must be non-empty: a
    divergence with no explanation is a row a reader cannot act on."""
    res = run_state(coord, er, pkg)
    got = {d["seat"]: d["class"] for d in res["divergences"]}
    if got != EXPECT_DIVERGENCE:
        only_got = sorted(set(got) - set(EXPECT_DIVERGENCE))
        only_exp = sorted(set(EXPECT_DIVERGENCE) - set(got))
        wrong = sorted("%s: got %s want %s" % (s, got[s], EXPECT_DIVERGENCE[s])
                       for s in set(got) & set(EXPECT_DIVERGENCE)
                       if got[s] != EXPECT_DIVERGENCE[s])
        return False, ("rider: divergence set wrong — unexpected %s, missing %s, misclassified %s"
                       % (only_got, only_exp, wrong))
    for d in res["divergences"]:
        if not d.get("note") or not d.get("trace") or not d.get("roster"):
            return False, ("rider: divergence for %s carries no note/trace/roster — a divergence "
                           "a reader cannot act on is not reported, it is merely counted"
                           % d["seat"])
    # And it must reach STDERR, not only the JSON a reader has to opt into.
    proc = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                           "--package", str(pkg)], capture_output=True, text=True)
    for seat in EXPECT_DIVERGENCE:
        if seat not in proc.stderr:
            return False, ("rider: %s's divergence is absent from STDERR — a divergence only in "
                           "a data structure is one nobody sees" % seat)
    return True, ("rider: both divergence classes reported with a stated cause (%s), and both "
                  "reach STDERR"
                  % ", ".join("%s=%s" % kv for kv in sorted(EXPECT_DIVERGENCE.items())))


def check_precedence_is_ordered(coord, er, pkg):
    """The precedence is the design, so it is asserted as ORDER and not merely as outcomes.

    `fx-done-but-active` satisfies the terminal term AND the roster term; `fx-crashed` satisfies
    neither and falls to the `after` term. If the order were roster-first, the first would read
    `running` — which is what coord.ready_seat_rows would NOT say, so the two surfaces would then
    disagree on a finished seat."""
    if PRECEDENCE != ("done", "failed", "running", "ready", "blocked", "skipped"):
        return False, ("precedence: PRECEDENCE is %r, expected the six in order — the three "
                       "`after`-term outcomes included" % (PRECEDENCE,))
    res = run_state(coord, er, pkg)
    got = {r["seat"]: r["state"] for r in res["rows"]}
    if got.get("fx-done-but-active") != "done":
        return False, ("precedence: fx-done-but-active is %r — a terminal mark must OUTRANK an "
                       "active roster row, or this CLI disagrees with coord on every finished "
                       "seat whose roster row was never closed" % got.get("fx-done-but-active"))
    if got.get("fx-active-clean") != "running":
        return False, ("precedence: fx-active-clean is %r — an active roster row with no terminal "
                       "mark must outrank the `after` term" % got.get("fx-active-clean"))
    coord_rows = {r["seat"]: r for r in coord.ready_seat_rows(_args_for(pkg))}
    if coord_rows.get("fx-done-but-active", {}).get("verdict") != "DONE":
        return False, ("precedence: coord.ready_seat_rows calls fx-done-but-active %r, so the "
                       "expectation this check encodes is no longer coord's own order"
                       % coord_rows.get("fx-done-but-active", {}).get("verdict"))
    return True, ("precedence: terminal outranks roster (fx-done-but-active=done, and coord agrees "
                  "with DONE), roster outranks the after-term (fx-active-clean=running)")


CHECKS = [
    ("reads-subset-of-audit", lambda coord, er, pkg: check_reads_subset_of_audit()),
    ("states-are-declared-vocabulary", check_states_are_the_declared_vocabulary),
    ("states-match-expected-table", check_states_match_expected_table),
    ("no-stored-state-is-read", check_no_stored_state_is_read),
    ("uses-existing-predicate", check_uses_existing_predicate),
    ("agrees-with-readiness-surface", check_agrees_with_readiness_surface),
    ("skipped-is-emitted-and-explained", check_skipped_is_emitted_and_explained),
    ("divergences-are-reported", check_divergences_are_reported),
    ("precedence-is-ordered", check_precedence_is_ordered),
]


# ---- ARMS EXPECTED RED, and why this file's tally is not 9/9 ---------------------------------
#
# A check left red with no explanation is read by the next reader — a seat, a commit gate, a
# regression sweep — as "broken", and the plausible wrong response is to WEAKEN THE ARM until the
# number goes up. That is the failure this table exists to prevent, so each entry states three
# things at the arm itself: that the red is EXPECTED, what CAUSED it, and WHO consumes it.
#
# A red documented only in a message log shares the fate of any claim whose provenance nobody can
# resolve. Leader ruling, run-3 `decisions.md`
# `#p-mc12-completes-at-8-of-9-with-the-red-named-on-the-artifact` (task 7.454).
#
# SELF-RETIRING: an entry whose arm has gone GREEN says so on sight, every run, until it is
# deleted. The seat that fixes an arm deletes its entry in the SAME change.
# EMPTY, and that is a RESULT rather than an oversight: task 7.454 entered exactly one arm here —
# `agrees-with-readiness-surface` — and task 7.455 / MC13 fixed that arm and DELETED its entry in
# the same change, as both the entry and the ruling required. The table itself stays: it is the
# ruled medium for naming a red on the artifact, and the next seat that must leave one red adds a
# row rather than re-inventing the mechanism.
EXPECTED_RED = {}


def build_fixture(root):
    """The fixture tree: M4-09's graph, PLUS a roster and three roster-driven rows this CLI needs.

    Built by CALLING the edge-runner stage's own `build_fixture` and adding to it, rather than by
    writing a second copy — a divergent fixture would make the two stages' checks disagree about
    the same seat names for no reason."""
    er = load_edge_runner()
    pkg = er.build_fixture(root)

    # Three rows the M4-09 fixture has no reason to carry, because it has no roster term.
    extra_after = {
        "fx-active-clean": "",                          # active, no mark -> running
        "fx-crashed": "fx-open-sitting",                 # open trace row, inactive roster
        "fx-done-but-active": "",                        # terminal mark + active roster row
    }
    with (pkg / "taskforce.csv").open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        for seat, cell in extra_after.items():
            w.writerow(["tf-fx", seat, cell, "claude", "claude-opus-5", "medium", "50", "fx"])
    for seat in extra_after:
        d = pkg / "seats" / seat
        d.mkdir(parents=True, exist_ok=True)
        d.joinpath("seat.md").write_text(
            "---\nseat: %s\n---\n<io-spec id=\"fx-io\" version=\"latest\">\n## Inputs\n\n- none.\n"
            "\n## Outputs\n\n- `outputs/present.md` — the declared artifact.\n</io-spec>\n" % seat)

    # Session rows for the two that need a trace: one terminal-and-still-rostered, one CRASHED
    # (open row, and its roster row will be inactive).
    with (pkg / "sessions.csv").open("a", encoding="utf-8") as fh:
        fh.write("s-11,fx-done-but-active,claude,n-11,/fx,,2026-07-30 06:00,"
                 "2026-07-30 06:10,111,1000,/dev/pts/11,done\n")
        fh.write("s-12,fx-crashed,claude,n-12,/fx,,2026-07-30 06:00,,112,1000,/dev/pts/12,\n")

    # THE ROSTER. `fx-crashed` is deliberately ABSENT from it: no roster row at all is the
    # inactive reading, which with its open session row is exactly the crashed-seat shape.
    (pkg / "coordination").mkdir(parents=True, exist_ok=True)
    (pkg / "coordination" / "workers.md").write_text(
        "# workers — agent sessions (script-managed, do not edit by hand)\n\n"
        "| agent | active | tmux pane | working on | checked in | checked out | last-read |\n"
        "|-------|--------|-----------|------------|------------|-------------|-----------|\n"
        "| fx-active-clean | yes | %201 | a fixture seat sitting now | 2026-07-30 06:00 |  | 1 |\n"
        "| fx-open-sitting | yes | %202 | a fixture seat sitting now | 2026-07-30 06:00 |  | 1 |\n"
        "| fx-done-but-active | yes | %203 | checked out but never closed | 2026-07-30 06:00 |  | 1 |\n"
        "| fx-done-outputs-present | no | %204 | finished | 2026-07-30 05:00 | 2026-07-30 06:10 | 1 |\n",
        encoding="utf-8")
    return pkg


def cmd_selftest(fixture, only):
    coord = load_edge_runner().load_coord()
    er = load_edge_runner()
    tmp = None
    if fixture:
        pkg = Path(fixture).resolve()
        print("run-state-job --selftest against on-disk fixture %s" % pkg)
    else:
        tmp = tempfile.mkdtemp(prefix="run-state-selftest-")
        pkg = build_fixture(Path(tmp))
        print("run-state-job --selftest against hermetic temp fixture %s" % pkg)
    try:
        selected = [(n, f) for n, f in CHECKS if not only or n == only]
        if only and not selected:
            print("error: no check named %r — known: %s"
                  % (only, ", ".join(n for n, _ in CHECKS)), file=sys.stderr)
            return 2
        passed, failed_names = 0, []
        for name, fn in selected:
            try:
                ok, msg = fn(coord, er, pkg)
            except Exception as exc:                       # a raising check is a FAILING check
                ok, msg = False, "raised %s: %s" % (type(exc).__name__, exc)
            print("  %-34s %s  %s" % (name, "PASS" if ok else "FAIL", msg))
            # The red is named AT THE ARM, where a reader who stops at the first FAIL still meets
            # it — never only in the tally, and never only in a message log.
            if name in EXPECTED_RED:
                print("      %s" % (EXPECTED_RED[name] if not ok else
                                    "⚠ STALE `EXPECTED_RED` ENTRY: this arm is GREEN now, so its "
                                    "entry no longer describes anything. Delete it."))
            passed += 1 if ok else 0
            if not ok:
                failed_names.append(name)
        print("%d/%d checks passed" % (passed, len(selected)))
        expected = [n for n in failed_names if n in EXPECTED_RED]
        if expected:
            print("NOT a clean run BY DESIGN: %d of the %d failing arm(s) are EXPECTED RED and "
                  "documented at the arm above — %s. Each names its cause and the task that owns "
                  "it. Do NOT weaken an arm to raise this tally."
                  % (len(expected), len(failed_names), ", ".join(expected)))
        return 0 if passed == len(selected) else 1
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


REGISTER_INVOCATION = (
    "ignite register-job run-state-recompute "
    "--action-type fire-tool "
    "--description 'Recompute every seat run state from disk (task 7.127 / M4-12)' "
    # ⚠ THE SCHEMA SHAPE IS THE STORE'S, NOT A SKETCH (task 7.587). It read
    # `'{"package": "string"}'` until 2026-08-09 — three defects in one string, all of which
    # `heart-store.js` refuses AT REGISTRATION, before the INSERT, so no id was ever burnt:
    # `package` is an unknown TOP-LEVEL key (`validateSchemaTypes` accepts only `required` and
    # `optional`); a `fire-tool` schema must declare `tool` in `required`
    # (`REQUIRED_ARGS_BY_ACTION['fire-tool'] === ['tool']`, enforced by the S-2(a) guard in
    # `registerJob`); and `package` — this file's one real operand — was declared where nothing
    # reads it. The shape below is what those two checks accept.
    "--args-schema '{\"required\":{\"tool\":\"string\",\"package\":\"string\"}}'"
)


def cmd_registration():
    """Print the registration command and its HONEST status. It has not been run."""
    print("THE REGISTRATION — DECLARED AND *NOT* PERFORMED\n")
    print("command, verbatim and unrun:\n")
    print("  %s\n" % REGISTER_INVOCATION)
    print("STATUS: NOT REGISTERED. Criterion 6 of task 7.127 is UNMET-FOR-CREDENTIAL, disclosed\n"
          "and never claimed (leader ruling, message #271 answering ask #270).\n")
    print("Three independent obstacles, all measured rather than assumed:\n"
          "  1. NO CREDENTIAL. `ignite inspect jobs` and the command above with --dry-run BOTH\n"
          "     return `ERROR [AUTH_REFUSED] authentication required` — the validate-only path\n"
          "     included, so the payload could not even be proven well-formed. IGNITE_SENDER_TOKEN\n"
          "     is unset; the only owner-token grant on record covers exactly two unrelated calls\n"
          "     of task 7.53 (decisions.md#r-owner-token-reseed).\n"
          "  2. NOT THIS SEAT'S VERB. `register-job` sits in another seat's grant; this seat's\n"
          "     floor is `ignite inspect` only.\n"
          "  3. NO `run-state` TOOL ENTRY (task 7.587). The command above would REGISTER, but the\n"
          "     `add-job` that schedules it would then be refused `E_UNKNOWN_TOOL` — the enqueue\n"
          "     door checks the row's `tool` against the boot-read `tools:` catalogue\n"
          "     (`heart-store.js` enqueue, `Object.hasOwn(this.config.tools, args.tool)`), and\n"
          "     `config/spawn-profiles.yaml` carries no `run-state` key. Registering first costs\n"
          "     nothing (create-only, and the id is not burnt by a MISSING catalogue entry — only\n"
          "     by a wrong SCHEMA), but the entry must land before any row can fire.\n")
    print("VERIFY IT, DO NOT TRUST THIS: `ignite inspect jobs` and look for `run-state-recompute`.\n"
          "The register command's own success line is NOT evidence — the job list is.\n")
    print("NOTE, so nobody re-decides this as an arming question: `register-job` is CREATE-ONLY and\n"
          "arms nothing. It installs a job DEFINITION; `add-job` schedules a run, and that is the\n"
          "arming instrument. So this is not cutover-class and does not touch r-cutover-gated.")
    return 0


def main():
    p = argparse.ArgumentParser(
        prog="run-state-job",
        description=("Recompute every seat's run state from disk, on demand (task 7.127 / M4-12). "
                     "It COMPUTES; it never reads a stored state, because there is none."),
        epilog=("THE STATE VOCABULARY: " + ", ".join("`%s`" % s for s in STATES) + ".\n\n"
                + GUARD_EXCLUDED_NOTE + "\n\n"
                "`running` is the ROSTER reading — an ACTIVE roster row via ready_seat_rows() — "
                "ruled at decisions.md#p-recompute-cli-reads-RUNNING-from-the-ROSTER, not the "
                "trace's empty `ended` cell. Rows where the two readings disagree (the "
                "crashed-seat shape) are REPORTED, never normalized.\n\n"
                "NOT REGISTERED as a job: see --registration for the verbatim command and why it "
                "was not run."),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--package", help="the run folder to recompute states in")
    p.add_argument("--json", action="store_true", help="emit the full result as JSON")
    p.add_argument("--registration", action="store_true",
                   help="print the register-job invocation and its honest status")
    p.add_argument("--selftest", action="store_true", help="run the probe set")
    p.add_argument("--only", default=None,
                   help="with --selftest: run ONE named check, so each criterion has its own "
                        "command line")
    p.add_argument("--fixture", default=None,
                   help="with --selftest: run against this on-disk package instead of a temp tree")
    args = p.parse_args()

    if args.registration:
        return cmd_registration()
    if args.selftest:
        return cmd_selftest(args.fixture, args.only)
    if not args.package:
        p.error("--package is required (or --selftest, or --registration)")

    er = load_edge_runner()
    coord = er.load_coord()
    pkg = Path(args.package).resolve()
    res = run_state(coord, er, pkg)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        for r in res["rows"]:
            print("%-10s %-30s %s" % (r["state"].upper() if r["state"] else "NO-STATE",
                                      r["seat"], r["reason"] or ""))
        if res["not-in-graph"]:
            print("\nnot in the graph (a trace row, no `taskforce.csv` row — listed, never "
                  "dropped; no `after` set, so NO graph state):")
            for n in res["not-in-graph"]:
                print("  %-30s mark=%s" % (n["seat"], n["mark"] or "REFUSED-TO-DECIDE"))
        for c in res["caveats"]:
            print("\ncaveat: %s" % c)
        # Criterion 5 — stated on EVERY run, not only in --help.
        print("\n⚠ %s" % GUARD_EXCLUDED_NOTE)

    # FAIL LOUD: divergences go to stderr too, so a reader who did not ask for JSON still sees
    # them. The rider's whole point is that these rows are never silently normalized.
    for d in res["divergences"]:
        print("DIVERGENCE  %s [%s] — trace says %s, roster says %s; reported as `%s`. %s"
              % (d["seat"], d["class"], d["trace"], d["roster"], d["state-reported"], d["note"]),
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
