#!/usr/bin/env python3
"""edge-runner-job — CMP-25's pass, STEPS 1-4: verify a finished seat's done contract and mark it
`done` or `failed` (task 7.123 / M4-08), evaluate readiness of every row whose `after` names it
(task 7.124 / M4-09), and enqueue each LAUNCH CANDIDATE as a daemon job seeded with its
predecessors' declared outputs (task 7.125 / M4-10).

Fired by the ignite daemon as a `fire-tool` job, one job per finished seat. CMP-25 is ONE engine
whose per-edge behaviour is entirely DATA; this file is that engine, and today it carries the
first four of its five steps.

⚠⚠ WHAT THIS FILE IS NOT, YET. CMP-25's pass has five steps: (1) verify the finished seat's done
contract, (2) mark it done or failed loudly, (3) evaluate every downstream row whose `after` names
it, (4) enqueue each ready seat's launch job, (5) exit. **Steps 1 through 4 are here. Step 5 is
NOT, and its absence is a build state, not a design.** A reader who finds no exit arm here has
found an unbuilt stage, not a missing feature.

⚠ STEP 4 IS THIS WAVE'S ONE ENQUEUE INTERFACE. `enqueue()` is called by the check-out fast path
(M4-11), the created goal's first workflow (M4-20) and the C1 rehearsal (M4-22). None of the three
writes its own: two enqueue implementations are G-301 rebuilt at the queue, and the expensive half
of that shape is that one of the two keeps reporting success. Its signature is a DECLARED OUTPUT of
task 7.125 and is recorded in `probe-record-edge-runner-enqueue-builder.md`; `--signature` prints
the live one, and a check binds the two together so it cannot move under its consumers silently.

**NOTHING REGISTERS THIS FILE.** It is in no job catalogue and no queue row, so it fires for
nothing and arms nothing. That is deliberate and it is the `r-cutover-gated` bound (m4 criterion
C4): the live run's own control loop stays untouched, and this engine is exercised against the
THROWAWAY goal `throwaway-m4-fixture` and against the fixture tree its own `--selftest` builds.
Arming it against a real run is a separate, gated act that this file does not perform.

THE READER PROBLEM, AND WHY THIS FILE CALLS RATHER THAN REIMPLEMENTS
-------------------------------------------------------------------
The durable check-out disposition already has exactly one reader: `coord.session_disposition`
(coord.py, `dag-09`), whose docstring states it "must be callable by anything that can name a run
package". This file CALLS it. It does not re-derive the last-ended-row rule, and it does not modify
coord.py.

That is not politeness, it is the defect this wave is bounded against: two readers of one graph
that disagree is the shape of `issues.md` G-301, where `taskforce_after()` and
`goal_cli.check_acyclic` read one `after` cell differently and one of them reports nothing wrong.
A second disposition reader here would reproduce that at the disposition column.

ONE read this file DOES perform itself, and the invariant that keeps it honest: whether the seat
has an ENDED row at all. `session_disposition` returns `None` for four different causes — no
`sessions.csv`, no `disposition` column, no ended row, or an empty cell — and two of those must be
marked differently (an empty cell on an ended row is a seat that FINISHED without declaring, which
is `failed`; no ended row at all is a seat that has not finished, which is not this stage's to
decide). Answering the precondition therefore needs a row scan, and it uses coord's OWN parsing
primitives (`read_csv_table`, `pad_row`, `SESSIONS_COLS`) rather than a private csv reader.
**The duplication hazard that creates is converted into a measured invariant, not waved at:**
`check_scan_agrees_with_coord_reader` asserts, per seat and off disk, that whenever the scan finds
an ended row with a non-empty cell, `session_disposition` returns exactly that cell. If the two
ever drift apart, that check goes red instead of a workflow advancing on a disagreement.

STATE IS DERIVED. NO STATUS COLUMN, ANYWHERE (Rule 14)
------------------------------------------------------
This stage READS `sessions.csv` and WRITES NOTHING to it, nor to `taskforce.csv`, nor to any new
ledger. Its marks are its stdout — a value recomputed from disk on every pass. A stored status
would be a second source that disagrees with the computation, which is the same two-readers defect
in a different column. `check_no_status_column_written` asserts the fixture's csv headers are
byte-identical before and after a full pass.

`done` IS THE ONLY VALUE THAT ADVANCES AN EDGE
----------------------------------------------
The enum is closed and it is coord's, not this file's: `RECORD_DISPOSITION_WRITER =
{done, renew, revive, exited}` (coord.py, validated at write time by `validate_disposition`, which
raises and never normalizes). `renew`, `revive` and `exited` each mark NOT-done here, and so does
an empty cell — coord.py's own comment on the column reads "AN EMPTY CELL IS `unknown`, NEVER
`done`". An implementation that read `exited` as "probably done" would reintroduce the silent stall
that value exists to make visible.

**`revive` and `exited` cannot be evidenced from the live build run's trace at all** — its observed
value set is `{done, renew}` (trace-field-audit.md §5, P-2). They are exercised on the fixture, and
that is why the fixture exists rather than the live trace being reused.

VERIFICATION IS GRADED, AND THE GRADE IT CANNOT AFFORD IS NAMED (PRIN-5)
-----------------------------------------------------------------------
PRIN-5: "existence -> shape -> content — apply the deepest grade the artifact affords at the edge's
cost budget." Applied here as:

  existence  the check-out record exists (the seat has an ended session row)
  shape      its disposition validates against coord's closed enum, and is `done`
  content    every resolvable path the seat's own `<io-spec> Outputs` declares exists on disk

The fourth grade a reader might expect — whether each artifact's CONTENT is correct — is **not
afforded** and every result says so in `grades-not-afforded`. It is per-contract, not derivable
from the trace, and a stage that silently omitted it would be read as having checked it.

THE ONE VALUE THIS STAGE REFUSES TO INVENT
------------------------------------------
Where the stage cannot decide, `disposition` is JSON `null` and `undecided-reason` says why, LOUD
on stderr. It never defaults to either value. A silent default here becomes a false `done`, and a
false `done` is the one error that advances a workflow past work nobody did.

FIELDS READ ARE AUDITED, NOT ASSUMED
------------------------------------
Every read site is declared in `READS` below, and `check_reads_subset_of_audit` proves by set
arithmetic — against `trace-field-audit.md` parsed off disk, not against a copy — that every one of
them was audited. A field this stage needs that the audit does not list is REPORTED, never read
silently; the audit is the contract and extending it is the auditor's act.

Usage:
  python3 edge-runner-job.py --package <RUN> [--seat NAME ...] [--json]
  python3 edge-runner-job.py --selftest                    # hermetic temp-dir fixture
  python3 edge-runner-job.py --selftest --fixture <DIR>     # the same assertions, off real disk
"""

import argparse
import ast
import csv
import inspect
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
COORD_PATH = HERE.parent / "team-kit" / "coord.py"

# ---- THE DECLARED READ INVENTORY — closed, and asserted against the audit off disk ------------
#
# `field=None` marks a read SITE that resolves to no column, carried visibly rather than dropped:
# a seat's declared outputs are a section of its own seat.md plus the paths that section names.
# trace-field-audit.md row 14 carries the same site with `field: null` for the same reason.
SESSIONS = "{RUN}/sessions.csv"
SEAT_MD_OUTPUTS = "{RUN}/seats/*/seat.md"
TASKFORCE = "{RUN}/taskforce.csv"
ROSTER = "{RUN}/coordination/workers.md"

READS = [
    (SESSIONS, "seat"),          # which rows belong to the seat under verification
    (SESSIONS, "ended"),         # whether it FINISHED — CMP-25's precondition
    (SESSIONS, "disposition"),   # the durable check-out value; `done` alone advances an edge
    (SEAT_MD_OUTPUTS, None),     # its declared outputs, and the artifact paths they name
    # STEP 3 (M4-09) adds exactly these two, and both were already audited: trace-field-audit.md
    # rows 4 and 5 carry `{RUN}/taskforce.csv` `after` and `seat` for the `ready` state. Read
    # through `coord.taskforce_after`, never with a private parser.
    (TASKFORCE, "seat"),         # which row each `after` cell belongs to
    (TASKFORCE, "after"),        # the predecessor set, COMMA-separated names and nothing else
    # STEP 4 (M4-10) adds exactly these two, and both were already audited: trace-field-audit.md
    # rows 7 and 8 carry `{RUN}/coordination/workers.md` `agent` and `active` as the roster reading
    # of `running`. They are STEP 4's ACTIVE-roster self-state term, read through coord's OWN
    # roster readers (`load_workers` / `current_row`), never with a private parser.
    (ROSTER, "agent"),           # which roster row belongs to the seat
    (ROSTER, "active"),          # whether it is occupying a pane right now — a double-launch guard
]

# coord's closed enum, restated here ONLY as the literal this file's checks compare against, so a
# check's expectation is never read from the value under test. `check_enum_matches_coord` asserts
# it equals coord's own `RECORD_DISPOSITION_WRITER` keys — drift makes that check red, not silent.
EXPECTED_ENUM = {"done", "renew", "revive", "exited"}

ADVANCES_EDGE = "done"   # the ONE value. Not a default, not a fallback, not a prefix match.

GRADES_NOT_AFFORDED = [
    {"grade": "content-of-artifact",
     "why": "whether a declared artifact's CONTENT satisfies the contract is per-contract and is "
            "not derivable from the trace. Named rather than silently omitted (PRIN-5)."}
]


def load_coord():
    """Import the kit's coord.py as a module. READ-ONLY use: this file calls its reader and its
    csv primitives and modifies nothing in it (m4 criterion C4)."""
    sys.path.insert(0, str(COORD_PATH.parent))
    import coord  # noqa: E402
    return coord


# ---- declared outputs -------------------------------------------------------------------------

_PATHISH = re.compile(r"`([^`\s]*/[^`\s]*\.[A-Za-z0-9]{1,6})`")


def resolve_declared_path(pkg, tok):
    """The absolute path a declared-output token resolves to, or None when it resolves nowhere.

    ONE resolver, called by both consumers of a declared output: the artifact GRADE below (which
    asks only "is it there?") and STEP 4's seed (which needs the path itself). A second resolution
    written for the seed would be free to disagree with the grade about what a token means — the
    two-readers shape this whole file is bounded against, at the smallest possible seam. The bases
    are the run package and the goal root, in that order, and a token that resolves against neither
    is returned as None rather than silently assumed present."""
    cand = Path(tok)
    if cand.is_absolute():
        return cand if cand.exists() else None
    for base in (pkg, pkg.parent.parent):
        p = base / tok
        if p.exists():
            return p
    return None


def declared_outputs(pkg, seat):
    """(declared, resolvable, missing) for `seat`'s own declared outputs.

    Reads the `<io-spec>` block of `{RUN}/seats/<seat>/seat.md` and, inside it, the `## Outputs`
    section — the read site trace-field-audit.md row 14 names. From that section it takes every
    backticked token that looks like a path (contains `/` and carries an extension).

    THREE ABSENCES ARE DISTINGUISHED, and none of them is a pass:
      * no seat.md               -> declared=None (the site does not resolve)
      * a seat.md with NO <io-spec> block -> declared=None. **This is the shape every seat.md in
        the throwaway fixture goal has on disk**, so this branch is the live case, not a defensive
        one.
      * an Outputs section whose declarations are all PROSE -> declared=0, resolvable=0

    A declared=0 result NEVER counts as "outputs verified": the caller reports the count, so a
    zero-path check cannot read as a green. A path is resolved against the run package and then
    against the goal root; one that resolves against neither is returned as unresolvable rather
    than silently treated as present."""
    seat_md = pkg / "seats" / seat / "seat.md"
    if not seat_md.exists():
        return None, [], [], "no seat.md at {RUN}/seats/%s/seat.md" % seat
    text = seat_md.read_text(encoding="utf-8", errors="replace")
    block = re.search(r"<io-spec\b.*?</io-spec>", text, re.S)
    if not block:
        return None, [], [], "seat.md carries no <io-spec> block"
    body = block.group(0)
    sec = re.search(r"##\s*Outputs\s*(.*?)(?=\n##\s|\Z)", body, re.S)
    if not sec:
        return None, [], [], "<io-spec> carries no `## Outputs` section"
    tokens = _PATHISH.findall(sec.group(1))
    resolvable, missing, unresolvable = [], [], []
    for tok in tokens:
        # ONE resolver, shared with STEP 4's seed. Behaviour is unchanged from the inline form this
        # replaced; what changes is that the artifact GRADE and the SEED can no longer disagree
        # about what a declared token means.
        if resolve_declared_path(pkg, tok) is not None:
            resolvable.append(tok)
        else:
            # declared, resolves against no known base -> MISSING, named. Never assumed present.
            missing.append(tok)
    return len(tokens), resolvable, missing, None


# ---- the stage --------------------------------------------------------------------------------

def ended_rows(coord, pkg, seat):
    """The seat's ENDED session rows, in file order, using coord's OWN csv primitives.

    Answers CMP-25's precondition only ("has S finished?"). The disposition VALUE is never taken
    from here — `session_disposition` owns it, and `check_scan_agrees_with_coord_reader` asserts
    the two never disagree on a non-empty cell."""
    path = coord.sessions_csv(pkg)
    if not path.exists():
        return None
    header, rows = coord.read_csv_table(path, coord.SESSIONS_COLS)
    idx = {c: i for i, c in enumerate(header)}
    if not {"seat", "ended"} <= set(idx):
        return None
    out = []
    for r in rows:
        coord.pad_row(r, header)
        if r[idx["seat"]].strip() == seat and r[idx["ended"]].strip():
            out.append(r[idx["disposition"]].strip() if "disposition" in idx else "")
    return out


def verify(coord, pkg, seat):
    """`{seat, disposition, evidence-read, ...}` for one seat. disposition is `done`, `failed`, or
    None — and None is always accompanied by `undecided-reason`.

    `evidence-read` names the fields THIS seat's decision actually consulted, never the full
    possible set: a seat with no ended row never reaches the disposition cell or its declared
    outputs, and its evidence list is correspondingly shorter."""
    result = {"seat": seat, "disposition": None, "undecided-reason": None,
              "evidence-read": [], "grades-applied": [],
              "grades-not-afforded": GRADES_NOT_AFFORDED, "reason": None, "outputs": None}

    if not coord.sessions_csv(pkg).exists():
        result["undecided-reason"] = (
            "the trace surface %s does not exist, so no check-out record can be read. This stage "
            "refuses to decide rather than defaulting: an absent trace is not a failed seat."
            % SESSIONS)
        return result

    # GRADE 1 — existence: did the seat FINISH? (CMP-25 fires "on S finished".)
    result["evidence-read"] = ["%s::seat" % SESSIONS, "%s::ended" % SESSIONS]
    rows = ended_rows(coord, pkg, seat)
    result["grades-applied"].append("existence")
    if not rows:
        result["undecided-reason"] = (
            "no ENDED session row for this seat, so it has not finished. CMP-25's pass fires on a "
            "FINISHED seat; a seat that never sat, or is sitting now, is not this stage's to mark. "
            "Refusing to decide rather than defaulting either way.")
        return result

    # GRADE 2 — shape: the durable value, read by coord's ONE reader.
    result["evidence-read"].append("%s::disposition" % SESSIONS)
    value = coord.session_disposition(pkg, seat)
    if value is None:
        # An ended row exists and the cell is empty: the seat finished WITHOUT declaring. coord's
        # own column comment: "AN EMPTY CELL IS `unknown`, NEVER `done`". It is somebody else
        # ending the row (`close-seat`/`depart`), and neither witnessed what the occupant meant.
        result["disposition"] = "failed"
        result["reason"] = ("the seat ENDED with an EMPTY disposition cell — unknown, never done. "
                           "No check-out was made, so no edge advances.")
        result["grades-applied"].append("shape")
        return result
    if value not in EXPECTED_ENUM:
        result["undecided-reason"] = (
            "disposition %r is outside coord's closed enum %s. `validate_disposition` raises rather "
            "than normalizing, so this value cannot have been written through the kit — refusing to "
            "interpret it." % (value, sorted(EXPECTED_ENUM)))
        return result
    result["grades-applied"].append("shape")
    if value != ADVANCES_EDGE:
        result["disposition"] = "failed"
        result["reason"] = ("disposition %r is NOT `%s`. It is the only value that advances an "
                            "edge; %r marks the seat NOT-done." % (value, ADVANCES_EDGE, value))
        return result

    # GRADE 3 — content(existence-of-declared-artifacts): the seat's own declared outputs.
    result["evidence-read"].append("%s::<io-spec> Outputs" % SEAT_MD_OUTPUTS)
    declared, resolvable, missing, why = declared_outputs(pkg, seat)
    result["outputs"] = {"declared": declared, "resolvable": resolvable, "missing": missing,
                         "site-unresolved": why}
    if declared is None:
        result["disposition"] = "done"
        result["reason"] = ("clean `%s` check-out. The declared-outputs grade was NOT APPLIED: %s. "
                            "The mark rests on the check-out record alone."
                            % (ADVANCES_EDGE, why))
        return result
    result["grades-applied"].append("content(existence-of-declared-artifacts)")
    if missing:
        result["disposition"] = "failed"
        result["reason"] = ("clean `%s` check-out, but %d declared output(s) are NOT on disk: %s. "
                            "A check-out is a claim about a file, not the file."
                            % (ADVANCES_EDGE, len(missing), ", ".join(missing)))
        return result
    result["disposition"] = "done"
    result["reason"] = ("clean `%s` check-out and all %d declared output(s) present on disk."
                        % (ADVANCES_EDGE, declared)) if declared else (
        "clean `%s` check-out. Its `## Outputs` section declares NO resolvable path (0 of 0), so "
        "the artifact grade had nothing to check — stated so it does not read as a green."
        % ADVANCES_EDGE)
    return result


def seats_of(coord, pkg, explicit):
    """The seats to verify: those named on argv, else every seat with a session row plus every
    `taskforce.csv` row. The union is deliberate — a seat with a trace row and no roster row is
    exactly the case a roster-only sweep would miss."""
    if explicit:
        return list(explicit)
    names = []
    sess = coord.sessions_csv(pkg)
    if sess.exists():
        header, rows = coord.read_csv_table(sess, coord.SESSIONS_COLS)
        idx = {c: i for i, c in enumerate(header)}
        for r in rows:
            coord.pad_row(r, header)
            if "seat" in idx and r[idx["seat"]].strip():
                names.append(r[idx["seat"]].strip())
    tf = pkg / "taskforce.csv"
    if tf.exists():
        with tf.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if (row.get("seat") or "").strip():
                    names.append(row["seat"].strip())
    seen, out = set(), []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def run_stage(coord, pkg, explicit=()):
    return [verify(coord, pkg, s) for s in seats_of(coord, pkg, explicit)]


# ---- STEP 3: readiness over PLAIN `after` sets (task 7.124 / M4-09) ---------------------------
#
# A seat is READY when every predecessor named in its `after` cell carries the mark `done`, and
# BLOCKED otherwise with each unmet predecessor NAMED. That is the whole predicate.
#
# ⚠⚠ SCOPE BOUND, DELIBERATE AND NAMED — NO CONDITIONAL-EDGE EVALUATOR, AND NO THIRD VERDICT.
# `VERDICTS` below is closed at two values. The state a reader might expect as a third — the one
# the registry defines for a row excluded by a conditional edge — IS DEFINED AND UNREACHABLE
# (trace-field-audit.md row 15: "resolves to NO column"; DAG §M4-12; issues.md G-301, G-308).
# Saying so here is required rather than tidy: a value that silently never appears reads as "this
# case did not arise", when the truth is "this case cannot arise", and those are different claims.
# Whether the conditional mechanism should be BUILT is the `leader`'s call on those two ledger
# rows, not this stage's.
#
# WHY THE PARSE IS `coord.taskforce_after` AND NOT A LOCAL SPLIT. The `after` cell has exactly one
# producer (`materialize-seats.py`) and one runtime parse (`coord.taskforce_after`, coord.py:8667,
# `raw.split(",")`, comma ONLY — it strips no conditional token and splits no alternate). A second
# parse here is G-301 rebuilt at a new seam: today `goal_cli.check_acyclic` DOES split those forms
# and reports NO finding while the runtime blocks the seat forever, and one of the two disagreeing
# readers says everything is fine. This stage therefore reads what the RUNTIME reads, by calling
# it. A conditional-shaped or alternate-shaped token is consequently ONE predecessor name, taken
# verbatim, that resolves to nothing and holds its seat blocked — and `unresolvable_shape_note`
# makes that visible in the reason instead of leaving it as a silent forever-block.
#
# ⚠ READINESS IS NOT LAUNCH CANDIDACY, AND STEP 4 MUST NOT TREAT IT AS SUCH. This predicate has
# NO term for the seat's OWN state. `coord.ready_seat_rows` carries three more terms before it
# says READY — terminal(self) is None, no ACTIVE roster row, a descriptor on disk — and a seat
# that is already finished or already sitting satisfies this predicate while being the wrong
# thing to launch. The `self-marks` key and the `caveats` list below carry that bound in the
# output itself so the enqueue stage cannot miss it.

VERDICTS = ("ready", "blocked")          # closed, spelled out, and compared against literally

NO_MARK = None                           # a predecessor nothing has marked. NEVER read as `done`.

_UNRESOLVABLE_SHAPE = re.compile(r"[\[\]|]")


def unresolvable_shape_note(name):
    """A note for an unmet predecessor whose NAME carries a conditional-edge or alternate
    character. The note changes NO verdict and evaluates nothing — it reports that the whole
    token is one uninterpreted name, which is why it can never resolve."""
    if not _UNRESOLVABLE_SHAPE.search(name):
        return None
    return ("this whole token is ONE predecessor name — the runtime parse splits the cell on "
            "COMMA only, so it is neither reduced nor split. It resolves to no seat and holds "
            "this row blocked permanently. See issues.md G-301/G-308; this stage evaluates "
            "nothing and reports the shape instead.")


def readiness(coord, pkg, marks=None):
    """`{ready: [seat], blocked: [{seat, unmet: [pred], ...}], ...}` for every `taskforce.csv` row.

    `marks` is `{seat: disposition}` as STEP 1-2 emits it (`done` | `failed` | None). Omit it and
    it is computed by running that stage — the same code path, never a second reading of the
    trace. Rows are returned in `taskforce.csv` FILE ORDER, which is `taskforce_after`'s order.

    Only the literal mark `done` satisfies an edge. `failed` does NOT, and neither does an absent
    mark: `failed` is terminal, and reading terminal as "finished, therefore satisfied" is the
    plausible wrong reading that would advance a workflow past work that did not pass."""
    if marks is None:
        marks = {r["seat"]: r["disposition"] for r in run_stage(coord, pkg)}
    after = coord.taskforce_after(pkg)

    ready, blocked = [], []
    for seat, preds in after.items():
        unmet, unmet_marks, notes = [], {}, {}
        for p in preds:
            mark = marks.get(p, NO_MARK)
            if mark != ADVANCES_EDGE:
                unmet.append(p)
                unmet_marks[p] = mark
                note = unresolvable_shape_note(p)
                if note:
                    notes[p] = note
        if unmet:
            blocked.append({
                "seat": seat, "unmet": unmet, "unmet-marks": unmet_marks,
                "after": list(preds), "notes": notes,
                "reason": "after: " + " ".join(
                    "%s=%s" % (p, unmet_marks[p] if unmet_marks[p] is not None else "<no mark>")
                    for p in unmet),
            })
        else:
            ready.append(seat)

    return {
        "ready": ready,
        "blocked": blocked,
        # The seat's OWN mark, for every seat this predicate calls ready. Carried because the
        # predicate has no self-state term and a consumer that launched on `ready` alone would
        # relaunch a finished seat.
        "self-marks": {s: marks.get(s, NO_MARK) for s in ready},
        "caveats": [
            "readiness is the `after`-set term ONLY. Launch candidacy additionally requires "
            "terminal(self) is None, no ACTIVE roster row, and a descriptor on disk — the three "
            "terms coord.ready_seat_rows carries and this predicate does not.",
            "the verdict vocabulary is closed at %s. A row excluded by a conditional edge has no "
            "verdict here because no conditional edge can be authored: the cell is parsed on "
            "comma alone (issues.md G-301/G-308)." % (list(VERDICTS),),
        ],
    }


# ---- STEP 4: enqueue each LAUNCH CANDIDATE as a daemon job (task 7.125 / M4-10) ---------------
#
# `enqueue()` below is THE enqueue interface of this wave. Three later seats call it — the
# check-out fast path (M4-11), the created goal's first workflow (M4-20) and the C1 rehearsal
# (M4-22) — and NONE of them writes its own. That is the whole point of the stage: two enqueue
# implementations would be `issues.md` G-301 rebuilt at the queue, and the expensive half of that
# shape is not the duplication, it is that ONE OF THE TWO KEEPS REPORTING SUCCESS. The signature is
# a declared output for the same reason: a signature that moves after its consumers are built
# breaks them silently, so `check_enqueue_signature_is_recorded` binds it to the probe record.
#
# ⚠⚠ READINESS IS NOT LAUNCH CANDIDACY — LEADER BAR, run-3 `decisions.md`
# `#p-readiness-is-NOT-launch-candidacy`. STEP 3's predicate answers the `after`-SET TERM ONLY. It
# has no term for the seat's own state, so a seat that has already FINISHED satisfies it, and
# ENQUEUING THE READY LIST AS-IS RELAUNCHES FINISHED SEATS. Measured on run-3's own surfaces, not
# hypothesised: `queue-loss-detector-namer` is listed READY (its `after` set is empty) while its own
# mark is `failed`, and `master-path-wirer` carries `exited`. Both are genuine rows. This stage
# therefore INTERSECTS the ready list with three self-state terms before anything is enqueued, and
# NAMES every exclusion in `excluded` — the exclusion is the requirement, the naming is what makes it
# auditable. `excluded` is present even when EMPTY: an empty list says "nothing was excluded", an
# absent one says nothing at all.
#
# THE THREE SELF-STATE TERMS, AND WHY EACH IS COMPUTED BY CALLING coord RATHER THAN RE-READING:
#   terminal mark      STEP 1-2's own mark for the seat. `done` and `failed` are both terminal —
#                      neither is a thing to launch. Only an UNDECIDED seat (mark `None`) is a
#                      candidate. This is the term the leader's bar names.
#   no ACTIVE roster   `coord.load_workers` + `coord.current_row`, coord's OWN roster readers. A
#                      seat occupying a pane right now is double-launched if enqueued.
#   descriptor exists  `{RUN}/seats/<seat>/seat.md`, the same site `declared_outputs` already reads.
#                      A `taskforce.csv`-only row would be launched into nothing.
# These are the three terms `coord.ready_seat_rows` carries and STEP 3 deliberately does not. They
# are CALLED here, never reimplemented. The one place this stage and coord are DESIGNED to differ is
# STEP 3's declared-artifact strictness (`EXPECTED_DIVERGENCES`), and it is one-directional by the
# leader's ruling: this stage may BLOCK what coord readies and may NEVER ready what coord blocks —
# so nothing is ever enqueued on the strength of coord's readiness where STEP 3 blocks.
#
# THE SEED, AND THE ONE CASE THAT CANNOT ARISE FROM A SINGLE PASS. Each launch is seeded with the
# absolute artifact paths its predecessors DECLARED, so it arrives holding what it needs instead of
# rediscovering it. Every path is re-confirmed to exist AT ENQUEUE TIME, and a seed path that is not
# there fails that seat's enqueue LOUDLY with the path named rather than enqueuing a launch that
# cannot read its own input. Within ONE pass that failure is unreachable by construction — STEP 1-2
# marks a seat `failed` when a declared output is missing, and a `failed` predecessor never
# satisfies an edge, so no ready seat can have a done predecessor with a missing artifact. It is
# reachable exactly one way: the artifact is DELETED between the marking pass and the enqueue, which
# is why criterion 2 says "at enqueue time" and why `check_missing_seed_path_fails_loudly` drives it
# as that time-of-check/time-of-use gap rather than as a shape the fixture can hold statically.
# That is stated here, and in `--enqueue`'s own output, because a failure row that never appears
# reads as "this did not happen" when the truth is "this cannot happen from one pass".

# ⚠ THE KEY IS `excluded`, NOT the word a reader reaches for first — and the reason is a
# TERMINOLOGY COLLISION, not taste. That other word is already TAKEN in this system: it is the
# registry's name for a row excluded by a CONDITIONAL EDGE, and this file proves that name absent
# from its own source (`check_no_conditional_evaluator_or_third_verdict`), because a state named but
# unreachable reads as "this case did not arise" when the truth is "this case cannot arise". A
# self-state exclusion and a conditional-edge exclusion are two different claims; giving them one
# word in one file is how a later reader collapses them. The leader's bar is that every exclusion is
# NAMED and that the list is present even when empty — both hold under this key.
ENQUEUE_RESULT_KEYS = ("enqueued", "validated", "excluded", "failed", "caveats")
ENQUEUE_ROW_KEYS = ("seat", "job-id", "seed")

# The daemon's enqueue door. `ignite add-job` wraps the gateway's `enqueue-job` intent; this stage
# does not speak to the store, the queue or the gateway directly, and holds no credential of its
# own. `submit` is a parameter so the checks can drive the interface without a daemon and without
# arming anything (m4 criterion C4).
IGNITE_BIN = "ignite"
_ENQUEUE_VERB = "add" + "-job"          # assembled, so the single-call-site check never counts ITSELF
_QUEUE_ID = re.compile(r"queue id (\S+)")


def iso_utc_now():
    """Fixed-width ISO-8601 UTC, the exact shape the gateway's enqueue parse requires and the same
    formatting the daemon's own isoNow() emits."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_submitter(argv):
    """Run the daemon's enqueue door. (returncode, stdout, stderr) — no exception, no parsing: the
    caller decides what a non-zero return means, so a failure is data rather than a traceback."""
    res = subprocess.run(argv, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def _enqueue_argv(job_id, profile, pkg, seat, seed, at, dry_run):
    """THE ONLY PLACE AN ENQUEUE COMMAND IS BUILT IN THIS TREE.

    `check_single_enqueue_call_site` asserts by source inspection that the door's verb appears in
    exactly this one function and nowhere else in the file. The seed rides in the args object,
    which is where a launch-agent job reads its parameters from; `profile` is the one argument the
    daemon REQUIRES of a launch-agent job, so it is a required parameter here rather than a
    default this stage invents."""
    args_obj = {"profile": profile, "seat": seat, "package": str(pkg), "seed": list(seed)}
    argv = [IGNITE_BIN, _ENQUEUE_VERB,
            "--fn", job_id,
            "--args-json", json.dumps(args_obj, sort_keys=True),
            "--trigger", "scheduled",
            "--at", at]
    if dry_run:
        argv.append("--dry-run")
    return argv


def launch_candidates(coord, pkg, ready, self_marks):
    """(candidates, excluded) — the ready list INTERSECTED with the three self-state terms.

    `excluded` rows carry the seat, the term that excluded it and the value that term read, so an
    exclusion is auditable by a reader who did not watch this run."""
    _, _, roster = coord.load_workers(pkg / "coordination")
    candidates, excluded = [], []
    for seat in ready:
        mark = self_marks.get(seat, NO_MARK)
        if mark is not None:
            excluded.append({"seat": seat, "term": "terminal-mark", "value": mark,
                            "reason": "own mark is `%s` — terminal. Ready names the satisfaction "
                                      "of INCOMING EDGES, never the desirability of an action."
                                      % mark})
            continue
        row = coord.current_row(roster, seat)
        if row is not None and row.get("active") == "yes":
            excluded.append({"seat": seat, "term": "active-roster-row", "value": "yes",
                            "reason": "an ACTIVE roster row — the seat is occupied right now, and "
                                      "enqueuing it would double-launch it."})
            continue
        if not (pkg / "seats" / seat / "seat.md").exists():
            excluded.append({"seat": seat, "term": "no-descriptor", "value": None,
                            "reason": "no descriptor at {RUN}/seats/%s/seat.md — a taskforce.csv-"
                                      "only row would be launched into nothing." % seat})
            continue
        candidates.append(seat)
    return candidates, excluded


def _tried_paths(pkg, tok):
    """The ABSOLUTE candidates a declared-output token was looked for at. A failure that names only
    the token says what was declared; naming where it was looked for says what to fix."""
    cand = Path(tok)
    if cand.is_absolute():
        return [str(cand)]
    return [str(base / tok) for base in (pkg, pkg.parent.parent)]


def seed_for(coord, pkg, seat, after):
    """(seed, missing) — the absolute artifact paths of `seat`'s predecessors' declared outputs.

    A seat with NO predecessors gets `[]`, which is a correct and complete seed, not a failure: the
    root case is the one an implementation keyed on predecessors forgets. Paths are de-duplicated
    with order preserved (two predecessors may declare the same artifact).

    WHERE THE ENQUEUE-TIME EXISTENCE CHECK ACTUALLY IS, stated because a reader will look for it in
    the wrong place: it is `declared_outputs` being called HERE, in this loop, on this pass — it
    re-resolves every declared token against disk and returns the absent ones, so `missing` is
    computed from what is on disk NOW rather than from what STEP 1-2 saw. The `path is None` branch
    below is NOT that check; it is the residual race INSIDE this pass (the artifact vanishing between
    the two resolutions, microseconds apart) and it is deliberately unreachable in practice. It is
    kept because the alternative is seeding `str(None)`, and it is labelled because a branch that
    looks like the guard, but is not the guard, is how a mutation test passes green — measured: a
    mutation that removed it left every check green, which is what sent this comment here."""
    seed, missing, seen = [], [], set()
    for pred in after.get(seat, []):
        declared, resolvable, absent, err = declared_outputs(pkg, pred)
        for tok in absent:
            # THE enqueue-time guard: `declared_outputs` re-resolved this token a line ago and it
            # is not on disk. Its check is `check_missing_seed_path_fails_loudly`, proven red by
            # mutating THIS loop.
            missing.append({"predecessor": pred, "path": tok, "tried": _tried_paths(pkg, tok),
                            "reason": "declared by `%s`, absent at enqueue time — it resolves "
                                      "against neither the run package nor the goal root" % pred})
        for tok in resolvable:
            path = resolve_declared_path(pkg, tok)
            if path is None:                                   # the residual same-pass race; see above
                missing.append({"predecessor": pred, "path": tok, "tried": _tried_paths(pkg, tok),
                                "reason": "declared by `%s` and present two resolutions ago, ABSENT "
                                          "now — it vanished DURING this pass" % pred})
                continue
            key = str(path)
            if key not in seen:
                seen.add(key)
                seed.append(key)
    return seed, missing


def enqueue(coord, pkg, job_id, profile, readiness_result=None, at=None, submit=None,
            dry_run=False):
    """THE enqueue interface. Turn every LAUNCH CANDIDATE into a daemon job seeded with its
    predecessors' declared outputs.

    Returns `{enqueued: [{seat, job-id, seed}], validated, excluded, failed, caveats}`.

      enqueued   one row per seat that reached the queue, each carrying the job id the door
                 returned. A row is here ONLY with a real id.
      validated  the same rows under `dry_run=True`, where the door validates and writes nothing,
                 so no id exists. A separate key rather than an `enqueued` row with a null id:
                 "validated" and "enqueued" are two different claims about the queue.
      excluded    every ready seat the self-state intersection excluded, with the term and value.
                 Present even when empty.
      failed     every candidate whose enqueue did not happen, with the cause named — a missing
                 seed path or a non-zero return from the door.

    `readiness_result` is STEP 3's output; omit it and it is computed by running STEP 3, which is
    the same code path rather than a second reading. `submit` is `(argv) -> (rc, stdout, stderr)`
    and defaults to running the daemon's door; injecting it is how a caller exercises the interface
    without a daemon. `at` defaults to now."""
    res = readiness_result if readiness_result is not None else readiness(coord, pkg)
    submit = submit or default_submitter
    at = at or iso_utc_now()
    after = coord.taskforce_after(pkg)

    candidates, excluded = launch_candidates(coord, pkg, res["ready"], res["self-marks"])

    enqueued, validated, failed = [], [], []
    for seat in candidates:
        seed, missing = seed_for(coord, pkg, seat, after)
        if missing:
            failed.append({"seat": seat, "missing-seed-paths": [m["path"] for m in missing],
                           "detail": missing,
                           "reason": "SEED PATH ABSENT AT ENQUEUE TIME: %s. Enqueuing this launch "
                                     "would schedule a seat that fails on its first read."
                                     % ", ".join(m["path"] for m in missing)})
            continue
        argv = _enqueue_argv(job_id, profile, pkg, seat, seed, at, dry_run)
        rc, out, err = submit(argv)
        if rc != 0:
            failed.append({"seat": seat, "missing-seed-paths": [], "detail": [],
                           "reason": "the enqueue door returned %d: %s"
                                     % (rc, (err or out or "").strip())})
            continue
        if dry_run:
            validated.append({"seat": seat, "job-id": None, "seed": seed})
            continue
        m = _QUEUE_ID.search(out or "")
        if not m:
            failed.append({"seat": seat, "missing-seed-paths": [], "detail": [],
                           "reason": "the enqueue door returned 0 but named NO queue id: %r. A row "
                                     "with no id is not evidence of a queued job." % (out or "")})
            continue
        enqueued.append({"seat": seat, "job-id": m.group(1), "seed": seed})

    return {
        "enqueued": enqueued,
        "validated": validated,
        "excluded": excluded,
        "failed": failed,
        "caveats": [
            "every row here was intersected with three self-state terms (terminal mark, ACTIVE "
            "roster row, descriptor on disk) before enqueuing — `ready` alone is NOT launch "
            "candidacy (leader bar `p-readiness-is-NOT-launch-candidacy`).",
            "a seed path missing at enqueue time cannot arise from ONE pass: STEP 1-2 marks a seat "
            "`failed` when a declared output is absent, and a `failed` predecessor satisfies no "
            "edge. `failed` rows of that cause are therefore a time-of-check/time-of-use gap — the "
            "artifact was deleted between the marking pass and this one — never a routine outcome.",
            "the artifact GRADE this seeds from is existence, not content: `grades-not-afforded` "
            "still holds, so a seed path being present is not a claim that its content is right.",
        ],
    }


# ---- STEP 4b (M4-11 / task 7.126): THE CHECK-OUT FAST PATH ------------------------------------
#
# WHAT IT IS. A seat's clean check-out already MAKES its successors ready — STEP 3 computes that
# from disk on demand. Nothing ACTUATES it: today advancement happens only when an agent runs the
# cadence sweep, which is the chief-of-staff standing in for a deterministic edge-runner. This hook
# is what makes advancement PROMPT instead of sweep-paced: the check-out itself puts the newly
# ready work in the queue.
#
# IT IMPLEMENTS NO ENQUEUE. It calls `enqueue()` above and nothing else. A second enqueue path is
# G-301 rebuilt at the queue, and the expensive half of that shape is that ONE OF THE TWO KEEPS
# REPORTING SUCCESS. `check_fastpath_calls_the_one_interface` asserts that structurally, by source
# inspection, rather than trusting this paragraph.
#
# ⚠⚠ THE ARMING SCOPE IS THE WHOLE C4 QUESTION — it is the reason this is presence-keyed PER RUN
# PACKAGE and not a global switch. Armed for the throwaway fixture, m4's bound is honoured. Armed
# for the live build run, this is an ungated cutover on that run's OWN control loop, which
# `r-cutover-gated` forbids without an agreed shadow window and a filed probe trail. So:
#
#   * There is deliberately NO environment variable and NO command-line flag that can arm it.
#     Either would arm every package the process touches — the exact failure this scoping exists
#     to prevent — and neither can be read back off disk later to answer "what was armed, when?".
#     A file inside the package answers that months later, from the package itself.
#   * Both enqueue parameters are REQUIRED in the file and neither has a default, so an empty,
#     truncated or stray file arms NOTHING. Arming is an explicit, deliberate, auditable act.
#   * Every not-armed branch fails CLOSED — absent, unreadable, unparseable and incomplete all
#     return "not armed". An arming mechanism that arms on a file it could not read is the one
#     failure mode here that damages the run this code is running inside.
#
# THE CALL SITE IS coord.py's `cmd_checkout`, DONE BRANCH ONLY, and there is exactly one of it —
# `check_fastpath_call_site_in_coord` asserts both facts against coord.py's own source, by AST,
# because a hook that quietly gained a second call site would double-enqueue every advancement.

ARM_FILENAME = "edge-fastpath.json"

# REQUIRED, with no defaults, because M4-10's interface has none: the catalogue id belongs to
# whoever armed the queue, and the daemon requires a profile of every launch-agent job.
ARM_REQUIRED = ("job-id", "profile")

# ⚠ `why-not`, and NOT the word a reader reaches for first — the same collision M4-10 hit one key
# over, for the same reason. That other word is the registry's name for a row excluded by a
# CONDITIONAL EDGE, and `check_no_conditional_evaluator_or_third_verdict` asserts it occurs NOWHERE
# in this file's source: a verdict that is named but unreachable reads as "this case did not arise"
# when the truth is "this case cannot arise". A fast path that stood down and a row excluded by a
# guard are two different claims. Measured, not anticipated — this stage's first draft used that
# word and the inherited check went RED on 17 lines of it.
FASTPATH_RESULT_KEYS = ("seat", "armed", "arm-path", "scope", "disposition", "fired", "enqueue",
                        "why-not")


def arm_path(pkg):
    """THE one place the arming file's location is computed. ONE reader, deliberately: a second
    one — in coord.py, say, to save an import — would be free to disagree with this one about which
    packages are armed, and a disagreement about ARMING is the C4 failure itself."""
    return Path(pkg) / "coordination" / ARM_FILENAME


def fastpath_arm(pkg):
    """(arm, scope) — this package's arming declaration, or `None` plus the reason it is NOT armed.

    `scope` is a sentence, not a flag, and it is a DECLARED OUTPUT of this stage: the question a
    later verifier asks is not "did the hook work" but "what was it armed FOR", and that question
    is answered by printing this string for a package rather than by reading a diff."""
    p = arm_path(pkg)
    if not p.exists():
        return None, ("NOT ARMED: no %s. A package arms this hook by carrying that file and by no "
                      "other means — there is no environment variable and no flag that can arm "
                      "it — so a package with no such file cannot be armed by accident." % p)
    try:
        arm = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, ("NOT ARMED: %s exists but did not read as JSON (%s: %s). FAIL-CLOSED — an "
                      "arming file that could not be read arms nothing, because the alternative is "
                      "advancing a run on a file nobody could parse."
                      % (p, type(exc).__name__, exc))
    if not isinstance(arm, dict):
        return None, ("NOT ARMED: %s parsed as %s, not an object. FAIL-CLOSED."
                      % (p, type(arm).__name__))
    absent = [k for k in ARM_REQUIRED if not arm.get(k)]
    if absent:
        return None, ("NOT ARMED: %s carries no %s. Both are REQUIRED and neither has a default — "
                      "the catalogue id belongs to whoever armed the queue, and the daemon requires "
                      "a profile of every launch-agent job. An empty or stray file therefore arms "
                      "nothing." % (p, " and no ".join("`%s`" % k for k in absent)))
    return arm, ("ARMED by %s — job-id=%s profile=%s%s. THIS PACKAGE ONLY: the file lives inside "
                 "the package, so it scopes to the package that carries it and to no other."
                 % (p, arm["job-id"], arm["profile"],
                    " (dry-run: the door validates and writes nothing)"
                    if arm.get("dry-run") else ""))


def checkout_fastpath(coord, pkg, seat, disposition, submit=None, at=None):
    """THE HOOK. Called by coord.py's `cmd_checkout`, once, at the end of its DONE branch.

    Returns `{armed, arm-path, scope, disposition, fired, enqueue, why-not}` ALWAYS and RAISES
    NEVER. That is not defensiveness, it is the call site: by the time this runs, the check-out has
    already taken every irreversible act — the transcript is exported, the roster row is flipped,
    the awaiting-close record is written and the session row is closed. An exception here would
    report a failure for a session that is already over and cannot be un-ended, and it would do it
    to a seat that did nothing wrong. Every failure is DATA in the returned dict; the caller prints
    it. `check_fastpath_never_raises` proves it, and coord's own call site is wrapped as well —
    two independent guards, because this one rides on an act nobody can retry.

    THREE GATES, and all three are load-bearing:

      1. **`disposition` must be `done`.** `renew`, `revive` and `exited` each name a seat that has
         NOT finished its work. Enqueuing on one of them advances a dead seat silently, which is
         precisely the failure the closed disposition enum exists to make visible. The gate is an
         equality against ONE value — never a truthiness test, never a prefix match, never
         "not renew".
      2. **The package must be ARMED** — see `fastpath_arm`. C4.
      3. **The package must have a TRACE AT ALL** — `sessions.csv` must exist. WHOLESALE, at the
         PACKAGE, and NEVER a per-seat decision. `launch_candidates` excludes a seat whose own mark
         is terminal, and with no trace `session_disposition` returns `None` for EVERY seat — so
         every seat falls through into the candidate list, including the one that just checked out.
         The consumer would read *not-terminal ⇒ eligible*, which is the mirror image of the
         asymmetry `coord.session_disposition` documents for itself ("`None` means UNKNOWN and
         never `done`"). ⚠ AND "ALSO EXCLUDE ON `None`" IS THE WRONG FIX, which is why this gate is
         at the package: `None` is returned both for a seat that has NEVER run and for one that
         just checked out into a traceless package, so NO per-seat polarity is correct — excluding
         blocks every legitimate first launch, including relaunches finished seats. The information
         is not there, and the only correct answer to a question the inputs cannot answer is to
         refuse to answer it. `p-the-fastpath-must-REFUSE-a-package-with-no-trace-not-decide-per-
         seat` (leader ruling `0757`), sharpened by `p-the-trace-records-LAUNCHED-sessions-only`:
         the traceless package is not a corrupt one, it is the HAND-CHECKED-IN one — `sessions.csv`
         records LAUNCHED sessions, so a package whose seats were checked in by hand legitimately
         has no trace and genuinely cannot answer.

    THE THIRD GATE IS DELIBERATELY LAST, AFTER `armed` IS SET. A refusal nobody can read is a
    refusal that gets worked around: `fastpath_lines` prints nothing at all for an UNARMED package
    (by design — every check-out in the workspace takes that branch and must stay quiet), so a
    trace refusal raised before the arming flag would be silent. Armed-and-refused is a state a
    reader must SEE, and it is the state this gate exists to produce.

    The arm is resolved BEFORE the disposition gate so `scope` is populated on every path: a
    `renew` check-out's result still reports what the package is armed for, which is what makes the
    arming scope auditable from ANY check-out rather than only from a firing one.

    `submit` is passed straight through to `enqueue()` and is how a check exercises the whole path
    without a daemon and without arming anything. It is never defaulted here — `enqueue()` owns
    that default, and a second one would be a second door."""
    pkg = Path(pkg)
    # `seat` is carried into the result rather than used to decide anything: this stage recomputes
    # readiness over the WHOLE package (STEP 3 does), so the checking-out seat's identity changes
    # no outcome. It is recorded because an advancement is only auditable if the check-out that
    # triggered it is named — "a queue row appeared" and "THIS check-out produced it" are two
    # different claims, and the second is the one M4-11 exists to make.
    res = {"seat": seat, "armed": False, "arm-path": str(arm_path(pkg)), "scope": "",
           "disposition": disposition, "fired": False, "enqueue": None, "why-not": None}
    try:
        arm, scope = fastpath_arm(pkg)
        res["scope"] = scope
        if disposition != ADVANCES_EDGE:
            res["why-not"] = ("disposition is `%s`, and only `%s` advances an edge. `renew`, "
                              "`revive` and `exited` each name a seat that has NOT finished; "
                              "enqueuing on one of them advances a dead seat."
                              % (disposition, ADVANCES_EDGE))
            return res
        if arm is None:
            res["why-not"] = scope
            return res
        res["armed"] = True
        # GATE 3 — the trace must EXIST. One condition, read at the package, decided for the whole
        # package: there is deliberately no per-seat branch here and no seat name in the reason.
        trace = coord.sessions_csv(pkg)
        if not trace.exists():
            res["why-not"] = (
                "REFUSING TO ADVANCE THIS PACKAGE: it carries no trace at %s, so no seat's "
                "check-out record can be read — and this refusal is WHOLESALE, at the package, "
                "not a decision about any one seat. With no trace, every seat's durable "
                "disposition reads as UNKNOWN, and UNKNOWN is returned both by a seat that has "
                "NEVER run and by one that JUST checked out: launching on it relaunches finished "
                "seats, refusing on it blocks every legitimate first launch. The information to "
                "tell those apart is not present, so this hook answers neither. TO ADVANCE THIS "
                "PACKAGE, give it a real trace: its seats must be LAUNCHED THROUGH THE KIT, which "
                "is what writes %s. ⚠ DO NOT HAND-WRITE THAT FILE — a hand-written trace "
                "fabricates rows for sessions nobody launched, which is the false-completion this "
                "gate exists to refuse." % (trace, trace.name))
            return res
        res["enqueue"] = enqueue(coord, pkg, arm["job-id"], arm["profile"], at=at, submit=submit,
                                 dry_run=bool(arm.get("dry-run")))
        res["fired"] = True
    except Exception as exc:                                          # noqa: BLE001
        res["why-not"] = ("the fast path raised %s: %s — CAUGHT HERE. The check-out it rides on "
                          "already completed and STANDS; only the advancement did not happen, and "
                          "it is reported rather than swallowed."
                          % (type(exc).__name__, exc))
    return res


def fastpath_lines(res):
    """The hook's result as lines the caller prints. Separated from the hook so coord.py renders it
    without knowing the result's shape, and so a check can assert the WORDING a seat actually sees:
    an advancement nobody was told about is indistinguishable from one that did not happen."""
    if not res.get("armed"):
        return []
    lines = []
    eq = res.get("enqueue") or {}
    for r in eq.get("enqueued", []):
        lines.append("edge fast path: QUEUED %s as job %s" % (r["seat"], r["job-id"]))
    for r in eq.get("validated", []):
        lines.append("edge fast path: VALIDATED %s (dry run — the door wrote nothing)" % r["seat"])
    for r in eq.get("failed", []):
        lines.append("edge fast path: NOT ENQUEUED %s — %s" % (r["seat"], r["reason"]))
    if res.get("why-not"):
        lines.append("edge fast path: %s" % res["why-not"])
    if not lines:
        # An armed package that enqueued nothing SAYS so. Silence here would be indistinguishable
        # from the hook never having run — the state this whole stage exists to leave behind.
        lines.append("edge fast path: armed, and this check-out made nothing ready — nothing "
                     "enqueued, which is a correct and complete outcome")
    return lines


# ---- checks -----------------------------------------------------------------------------------
#
# Every expectation below is spelled out LITERALLY. Not one is read from the value under test: a
# check whose expected value is computed by the code it guards moves with that code and passes any
# change to it.

# The workspace root is FIVE parents up (jobs -> ignite -> rbtv -> tools -> 3-resources -> root),
# and the depth is VERIFIED by looking for `.rbtv/` rather than counted and trusted: a promotion
# that moves this file changes the depth, and a silently-wrong path would make the audit check
# report "audit file absent" instead of failing on the real cause.
def _workspace_root(start):
    for cand in [start] + list(start.parents):
        if (cand / ".rbtv").is_dir():
            return cand
    return start


AUDIT = (_workspace_root(HERE) / ".rbtv" / "goals" / "build-core-daemon-mvp" / "runs"
         / "run-3" / "planning" / "m4-workflow-engine-runs-DAG-edged-jobs"
         / "trace-field-audit.md")

# The fixture verdicts, spelled out. `None` means "the stage must refuse to decide".
EXPECT = {
    "fx-done-outputs-present": "done",
    "fx-done-output-missing": "failed",
    "fx-renew": "failed",
    "fx-revive": "failed",
    "fx-exited": "failed",
    "fx-empty-disposition": "failed",
    "fx-open-sitting": None,
    "fx-no-row": None,
    "fx-renewed-then-done": "done",
    "fx-no-iospec": "done",
}


# ---- the STEP-3 fixture graph, and its expectations, spelled out literally --------------------
#
# One row per shape the predicate must get right. The `after` CELLS are written verbatim into the
# fixture's taskforce.csv, INCLUDING the two malformed-on-purpose ones, so the comma-only parse is
# exercised against real disk rather than against a hand-built dict.
READY_AFTER = {
    "fx-r-root":            "",
    "fx-r-one-done":        "fx-done-outputs-present",
    "fx-r-two-done":        "fx-done-outputs-present,fx-renewed-then-done",
    "fx-r-spaces":          "  fx-done-outputs-present ,  fx-renewed-then-done  ",
    "fx-r-failed-pred":     "fx-renew",
    "fx-r-exited-pred":     "fx-exited",
    "fx-r-undecided-pred":  "fx-open-sitting",
    "fx-r-mixed":           "fx-done-outputs-present,fx-exited",
    "fx-r-dangling":        "fx-nobody-by-that-name",
    "fx-r-conditional":     "fx-done-outputs-present[state=ok]",
    "fx-r-alternate":       "fx-done-outputs-present|fx-renewed-then-done",
    "fx-r-artifact-strict": "fx-done-output-missing",
}

# The expected verdict and the expected UNMET SET for every fixture row, written out by hand.
# Not one entry is computed from the predicate, from READY_AFTER, or from the mark table: a check
# whose expectation is derived from the value under test moves with the code and passes any change
# to it. The EXPECT seats of step 1-2 all carry an empty `after`, so every one of them is ready.
EXPECT_READY = {
    "fx-r-root":            ("ready",   []),
    "fx-r-one-done":        ("ready",   []),
    "fx-r-two-done":        ("ready",   []),
    "fx-r-spaces":          ("ready",   []),
    "fx-r-failed-pred":     ("blocked", ["fx-renew"]),
    "fx-r-exited-pred":     ("blocked", ["fx-exited"]),
    "fx-r-undecided-pred":  ("blocked", ["fx-open-sitting"]),
    "fx-r-mixed":           ("blocked", ["fx-exited"]),
    "fx-r-dangling":        ("blocked", ["fx-nobody-by-that-name"]),
    "fx-r-conditional":     ("blocked", ["fx-done-outputs-present[state=ok]"]),
    "fx-r-alternate":       ("blocked", ["fx-done-outputs-present|fx-renewed-then-done"]),
    "fx-r-artifact-strict": ("blocked", ["fx-done-output-missing"]),
    "fx-done-outputs-present": ("ready", []),
    "fx-done-output-missing":  ("ready", []),
    "fx-renew":                ("ready", []),
    "fx-revive":               ("ready", []),
    "fx-exited":               ("ready", []),
    "fx-empty-disposition":    ("ready", []),
    "fx-open-sitting":         ("ready", []),
    "fx-no-row":               ("ready", []),
    "fx-renewed-then-done":    ("ready", []),
    "fx-no-iospec":            ("ready", []),
}

# The ONE row on which this predicate and `coord.ready_seat_rows` are EXPECTED to differ, named
# rather than tolerated. coord satisfies an edge on the RAW check-out value; this stage satisfies
# it on step 1-2's MARK, which additionally requires the predecessor's declared outputs to exist.
# `fx-done-output-missing` checked out `done` and its declared artifact is NOT on disk, so coord
# reads that edge satisfied and this stage does not. A strictness ordering, not a parse
# disagreement — and `check_agrees_with_coord_ready_seats` proves the ordering is ONE-directional
# (this stage may block what coord readies; it may NEVER ready what coord blocks) and that every
# divergence is explained by exactly that grade. A divergence outside this set is RED.
EXPECTED_DIVERGENCES = {"fx-r-artifact-strict"}


def audited_pairs(path):
    """The audit's `reads` list, parsed off ITS OWN FILE — never a copy kept here.

    Returns (field_pairs, null_surfaces): the (surface, field) pairs of every row carrying a
    column, and the surface strings of the rows whose field is `null`."""
    pairs, nulls = set(), []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6 or not cells[0].isdigit():
            continue
        field = cells[3].strip("`").strip()
        surface = cells[4].replace("`", "").strip()
        if field == "null":
            nulls.append(surface)
        else:
            pairs.add((surface, field))
    return pairs, nulls


def check_reads_subset_of_audit():
    """CRITERION 2 — every field this stage reads was audited. Set arithmetic against the audit
    file on disk, so a field added to READS but never audited fails here rather than being read
    silently in production."""
    if not AUDIT.exists():
        return False, "criterion 2: the audit file is absent at %s — cannot verify" % AUDIT
    pairs, nulls = audited_pairs(AUDIT)
    if not pairs:
        return False, "criterion 2: parsed ZERO audited field rows from %s — the parse is broken, " \
                      "and an empty audited set would let every read pass vacuously" % AUDIT
    unaudited = []
    for surface, field in READS:
        if field is None:
            if not any("seat.md" in s and "io-spec" in s for s in nulls):
                unaudited.append("%s::<io-spec> Outputs" % surface)
        elif (surface, field) not in pairs:
            unaudited.append("%s::%s" % (surface, field))
    if unaudited:
        return False, ("criterion 2: %d read site(s) are NOT in the audit's reads[] list: %s. "
                       "Report the field to the leader; do not read it."
                       % (len(unaudited), ", ".join(unaudited)))
    return True, "criterion 2: all %d declared read sites appear in the audit's reads[] (%d " \
                 "audited field rows parsed, %d null-field rows)" % (len(READS), len(pairs), len(nulls))


def check_reads_match_coord_reader(coord):
    """The read inventory is asserted against `session_disposition`'s OWN BYTES, not against prose.

    If coord's durable reader ever starts indexing a fourth column, that column becomes a field
    this stage reads and the audit never enumerated — the exact latent gap criterion 2 exists to
    catch. This check makes that drift red here instead of invisible in production."""
    src = inspect.getsource(coord.session_disposition)
    cols = set(re.findall(r'idx\["([a-z-]+)"\]', src))
    expected = {"seat", "ended", "disposition"}          # spelled out literally
    if cols != expected:
        return False, ("criterion 2: coord.session_disposition indexes %s, but this stage's READS "
                       "were declared against %s. The disposition reader changed; re-audit before "
                       "trusting any mark." % (sorted(cols), sorted(expected)))
    declared = {f for s, f in READS if s == SESSIONS}
    if not expected <= declared:
        return False, ("criterion 2: %s is read by coord.session_disposition but missing from "
                       "READS" % sorted(expected - declared))
    return True, "criterion 2: coord.session_disposition indexes exactly %s, all declared in READS" \
                 % sorted(expected)


def check_enum_matches_coord(coord):
    """The enum this stage compares against is coord's, not a private copy that can drift."""
    actual = set(coord.RECORD_DISPOSITION_WRITER)
    if actual != EXPECTED_ENUM:
        return False, ("criterion 2: coord's RECORD_DISPOSITION_WRITER is %s but this file expects "
                       "%s — a new disposition value exists and its NOT-done handling is unruled"
                       % (sorted(actual), sorted(EXPECTED_ENUM)))
    return True, "criterion 2: enum matches coord's RECORD_DISPOSITION_WRITER %s" % sorted(actual)


def check_dispositions(coord, pkg):
    """CRITERION 1 + the DISCRIMINATING CONTROL — `renew`, `revive` and `exited` each mark
    NOT-done, and an empty cell does too. Expectations are the literal EXPECT table."""
    got = {r["seat"]: r["disposition"] for r in run_stage(coord, pkg)}
    bad = []
    for seat, want in EXPECT.items():
        if seat not in got:
            bad.append("%s: not verified at all" % seat)
        elif got[seat] != want:
            bad.append("%s: expected %r, got %r" % (seat, want, got[seat]))
    if bad:
        return False, "criterion 1/discriminating control: %d wrong verdict(s): %s" % (len(bad),
                                                                                       "; ".join(bad))
    return True, "criterion 1/discriminating control: all %d fixture verdicts correct (done=%d, " \
                 "failed=%d, refused=%d)" % (
                     len(EXPECT),
                     sum(1 for v in EXPECT.values() if v == "done"),
                     sum(1 for v in EXPECT.values() if v == "failed"),
                     sum(1 for v in EXPECT.values() if v is None))


def check_refusal_is_explicit(coord, pkg):
    """CRITERION 8 — where the stage cannot decide it SAYS SO and defaults to neither value."""
    rows = {r["seat"]: r for r in run_stage(coord, pkg)}
    for seat in ("fx-open-sitting", "fx-no-row"):
        r = rows.get(seat)
        if r is None:
            return False, "criterion 8: %s was not verified" % seat
        if r["disposition"] is not None:
            return False, ("criterion 8: %s got disposition %r — an undecidable case took a "
                           "default, which is how a false `done` is born" % (seat, r["disposition"]))
        if not r["undecided-reason"]:
            return False, "criterion 8: %s refused to decide but gave NO reason" % seat
    return True, "criterion 8: both undecidable seats carry disposition=None with a stated reason"


def check_evidence_is_per_seat(coord, pkg):
    """CRITERION 3 — `evidence-read` is what THIS seat's decision consulted, not the full set."""
    rows = {r["seat"]: r for r in run_stage(coord, pkg)}
    outputs_site = "%s::<io-spec> Outputs" % SEAT_MD_OUTPUTS
    disp_site = "%s::disposition" % SESSIONS
    unfinished = rows["fx-no-row"]["evidence-read"]
    if disp_site in unfinished or outputs_site in unfinished:
        return False, ("criterion 3: fx-no-row never reached the disposition cell, yet its "
                       "evidence-read claims %s" % unfinished)
    notdone = rows["fx-renew"]["evidence-read"]
    if outputs_site in notdone:
        return False, ("criterion 3: fx-renew never reached its declared outputs (it is not-done), "
                       "yet its evidence-read claims %s" % outputs_site)
    done = rows["fx-done-outputs-present"]["evidence-read"]
    if outputs_site not in done:
        return False, ("criterion 3: fx-done-outputs-present DID consult its declared outputs but "
                       "does not report the site")
    if len(unfinished) >= len(done):
        return False, ("criterion 3: evidence-read does not vary per seat — unfinished reports %d "
                       "sites, a fully-graded seat %d" % (len(unfinished), len(done)))
    return True, "criterion 3: evidence-read varies per seat (unfinished %d sites, not-done %d, " \
                 "fully graded %d)" % (len(unfinished), len(notdone), len(done))


def check_scan_agrees_with_coord_reader(coord, pkg):
    """The duplication invariant. This file answers "did it end?" with its own scan and "what did
    it declare?" with coord's reader. Where the scan finds an ended row with a NON-EMPTY cell,
    coord's reader must return exactly that cell. Two readers that disagree is G-301's shape."""
    for seat in EXPECT:
        rows = ended_rows(coord, pkg, seat)
        if not rows:
            continue
        last_nonempty = None
        for cell in rows:
            if cell:
                last_nonempty = cell
        if rows[-1]:
            if coord.session_disposition(pkg, seat) != rows[-1]:
                return False, ("reader agreement: %s — scan's last ended cell is %r but "
                               "coord.session_disposition returned %r"
                               % (seat, rows[-1], coord.session_disposition(pkg, seat)))
        elif last_nonempty is not None:
            pass
    return True, "reader agreement: the row scan and coord.session_disposition agree on every " \
                 "fixture seat with a non-empty last cell"


def check_no_status_column_written(coord, pkg):
    """CRITERION 6 — Rule 14. A full pass writes NO status column anywhere. Every csv header under
    the package is hashed before and after."""
    def headers():
        out = {}
        for p in sorted(pkg.rglob("*.csv")):
            with p.open(encoding="utf-8", errors="replace") as fh:
                out[str(p.relative_to(pkg))] = fh.readline().rstrip("\n")
        return out
    before = headers()
    run_stage(coord, pkg)
    after = headers()
    if before != after:
        changed = [k for k in set(before) | set(after) if before.get(k) != after.get(k)]
        return False, "criterion 6: a pass CHANGED csv header(s): %s" % changed
    for name, head in after.items():
        for col in head.split(","):
            if col.strip().lower() in ("status", "state", "disposition-cache"):
                if not (name.endswith("runs.csv") and col.strip().lower() == "state"):
                    return False, ("criterion 6: %s carries a status-like column %r"
                                   % (name, col.strip()))
    return True, "criterion 6: %d csv header(s) byte-identical across a full pass; no status " \
                 "column present" % len(after)


# ---- STEP 3's checks (task 7.124 / M4-09) -----------------------------------------------------

# Assembled from two fragments ON PURPOSE, so that this check's own source is not a hit for the
# search it performs. Spelling it out inline would make the check pass or fail on its own text.
EXCLUDED_STATE = "skip" + "ped"

READINESS_KEYS = ("ready", "blocked", "self-marks", "caveats")   # literal, not derived


def _readiness_verdicts(res):
    """{seat: verdict} from a readiness result, for comparison against the literal table."""
    out = {s: "ready" for s in res["ready"]}
    for b in res["blocked"]:
        out[b["seat"]] = "blocked"
    return out


def check_readiness_verdicts(coord, pkg):
    """CRITERION 1 + 4 — every fixture row gets the verdict and the UNMET SET the literal
    EXPECT_READY table names. Covers the empty-`after` root (ready) and, as the discriminating
    control, a predecessor marked `failed` (BLOCKED, never ready): treating a terminal mark as
    "finished, therefore satisfied" is the plausible wrong reading and it is checked explicitly."""
    res = readiness(coord, pkg)
    got = _readiness_verdicts(res)
    unmet = {b["seat"]: b["unmet"] for b in res["blocked"]}
    bad = []
    for seat, (want_verdict, want_unmet) in EXPECT_READY.items():
        if seat not in got:
            bad.append("%s: no verdict at all" % seat)
            continue
        if got[seat] != want_verdict:
            bad.append("%s: expected %s, got %s" % (seat, want_verdict, got[seat]))
        elif want_verdict == "blocked" and unmet.get(seat) != want_unmet:
            bad.append("%s: expected unmet %s, got %s" % (seat, want_unmet, unmet.get(seat)))
    extra = sorted(set(got) - set(EXPECT_READY))
    if extra:
        bad.append("rows with no expectation in the table: %s" % extra)
    if bad:
        return False, "criterion 1/4: %d wrong readiness row(s): %s" % (len(bad), "; ".join(bad))
    return True, ("criterion 1/4: all %d rows correct (ready=%d, blocked=%d), every blocked row's "
                  "unmet set matches by name" % (
                      len(EXPECT_READY),
                      sum(1 for v, _ in EXPECT_READY.values() if v == "ready"),
                      sum(1 for v, _ in EXPECT_READY.values() if v == "blocked")))


def check_after_split_is_comma_only(coord, pkg):
    """CRITERION 2 — the `after` cell is split on COMMA and nothing else.

    Fed two cells the parse must NOT interpret: a conditional-shaped token and an
    alternate-shaped one. Each must survive as ONE predecessor name, character for character, and
    must NOT be reduced to the seat name inside it — a reduction would mark the row ready off a
    predecessor nobody named. Whitespace around comma-separated names IS stripped, which is what
    `materialize-seats.py` writes and `coord.taskforce_after` reads."""
    after = coord.taskforce_after(pkg)
    cases = [
        ("fx-r-conditional", ["fx-done-outputs-present[state=ok]"]),
        ("fx-r-alternate",   ["fx-done-outputs-present|fx-renewed-then-done"]),
        ("fx-r-spaces",      ["fx-done-outputs-present", "fx-renewed-then-done"]),
        ("fx-r-two-done",    ["fx-done-outputs-present", "fx-renewed-then-done"]),
        ("fx-r-root",        []),
    ]
    for seat, want in cases:
        if after.get(seat) != want:
            return False, ("criterion 2: `after` for %s parsed to %r, expected %r — the cell was "
                           "split on something other than comma" % (seat, after.get(seat), want))
    res = readiness(coord, pkg)
    blocked = {b["seat"]: b for b in res["blocked"]}
    for seat, want in (("fx-r-conditional", "fx-done-outputs-present[state=ok]"),
                       ("fx-r-alternate", "fx-done-outputs-present|fx-renewed-then-done")):
        b = blocked.get(seat)
        if b is None:
            return False, ("criterion 2: %s is NOT blocked — the uninterpretable token was "
                           "resolved to something, which is how a row is readied off a "
                           "predecessor nobody named" % seat)
        if b["unmet"] != [want]:
            return False, ("criterion 2: %s unmet is %r, expected exactly [%r]"
                           % (seat, b["unmet"], want))
        if not b["notes"].get(want):
            return False, ("criterion 2: %s carries no note explaining that the token is one "
                           "uninterpreted name — a permanent block with no stated cause" % seat)
    return True, ("criterion 2: comma-only split confirmed on 5 cells; both uninterpretable "
                  "tokens survive whole, block their row, and carry a stated cause")


def check_no_conditional_evaluator_or_third_verdict():
    """CRITERION 3 — no conditional-edge evaluator and no third verdict exist in this file.

    A SEARCH, and it is recorded: the excluded state's name must not occur anywhere in the source,
    the verdict tuple must be exactly the two values spelled out, and the shape-note helper must
    have exactly one call site (its return value annotates a reason; it decides nothing)."""
    src = Path(__file__).read_text(encoding="utf-8")
    hits = [i + 1 for i, ln in enumerate(src.splitlines())
            if EXCLUDED_STATE in ln.lower()]
    if hits:
        return False, ("criterion 3: the excluded state's name occurs at line(s) %s — a third "
                       "verdict is being introduced" % hits)
    if VERDICTS != ("ready", "blocked"):
        return False, "criterion 3: VERDICTS is %r, expected exactly ('ready', 'blocked')" % (
            VERDICTS,)
    # The shape-note helper must be called from `readiness` ONCE and from nowhere else, so it
    # cannot be reaching a verdict decision. Counted over function SOURCES rather than over the
    # whole file: this check's own text names the helper, and a whole-file count would be
    # measuring itself. This function is excluded BY NAME for exactly that reason.
    inside = inspect.getsource(readiness).count("unresolvable_shape_note(")
    if inside != 1:
        return False, ("criterion 3: `readiness` calls the shape-note helper %d time(s), "
                       "expected exactly 1" % inside)
    me = "check_no_conditional_evaluator_or_third_verdict"
    elsewhere = []
    for name, obj in sorted(globals().items()):
        if not callable(obj) or name in ("readiness", me):
            continue
        if getattr(obj, "__module__", None) != __name__:
            continue
        try:
            body = inspect.getsource(obj)
        except (OSError, TypeError):
            continue
        if name != "unresolvable_shape_note" and "unresolvable_shape_note(" in body:
            elsewhere.append(name)
    if elsewhere:
        return False, ("criterion 3: the shape-note helper is also called from %s — it may be "
                       "reaching a verdict decision there" % elsewhere)
    return True, ("criterion 3: excluded state's name absent from all %d lines; VERDICTS == "
                  "('ready', 'blocked'); the shape-note helper has exactly ONE call site, in "
                  "`readiness`, and none elsewhere" % len(src.splitlines()))


def check_readiness_schema(coord, pkg):
    """The declared output shape, asserted literally: `{ready: [seat], blocked: [{seat, unmet}]}`
    with `unmet` a list of NAMES, plus the two keys that carry the not-launch-candidacy bound."""
    res = readiness(coord, pkg)
    if tuple(res) != READINESS_KEYS:
        return False, "schema: top-level keys are %r, expected %r" % (tuple(res), READINESS_KEYS)
    if not all(isinstance(s, str) for s in res["ready"]):
        return False, "schema: `ready` must be a list of seat names"
    for b in res["blocked"]:
        if not {"seat", "unmet"} <= set(b):
            return False, "schema: a blocked row lacks `seat`/`unmet`: %r" % sorted(b)
        if not b["unmet"] or not all(isinstance(p, str) for p in b["unmet"]):
            return False, ("schema: %s's `unmet` is %r — every blocked row must NAME at least one "
                           "unmet predecessor, so a stalled wave reports WHICH edge holds it"
                           % (b["seat"], b["unmet"]))
    if set(res["self-marks"]) != set(res["ready"]):
        return False, "schema: `self-marks` must cover exactly the ready set"
    return True, ("schema: keys %r; %d ready, %d blocked, every blocked row names >=1 unmet "
                  "predecessor" % (list(READINESS_KEYS), len(res["ready"]), len(res["blocked"])))


def _fixture_args(pkg):
    """An args-shaped object for `coord.ready_seat_rows` pointed at the fixture.

    `workers_dir` is supplied EXPLICITLY: left unset, `coord.workers_dir` resolves the package with
    `register=True`, which WRITES the fixture into the machine's runs index. A read-only check must
    not register a temp directory as a run."""
    class _A:
        package = str(pkg)
        base = str(pkg / "coordination")
        workers_dir = str(pkg / "seats")
        run = None
    return _A()


def check_agrees_with_coord_ready_seats(coord, pkg):
    """CRITERION 7 — this predicate and `coord.ready_seat_rows` agree on the fixture's graph, and
    the ONE place they are designed to differ is named in advance.

    Compared TERM BY TERM, which is the term `ready-seats --explain` prints: for each row, whether
    every `after` predecessor is satisfied. coord's other three terms (terminal(self), an ACTIVE
    roster row, a descriptor on disk) are NOT this predicate's and are excluded from the
    comparison rather than silently swallowed.

    Two readers of one graph that disagree is the defect class this wave is bounded against, so a
    divergence outside `EXPECTED_DIVERGENCES` is RED, and an UNSOUND divergence — this stage
    readying a row coord blocks — is red even if it were listed."""
    theirs_rows = coord.ready_seat_rows(_fixture_args(pkg))
    theirs_disp = {r["seat"]: r["disposition"] for r in theirs_rows}
    after = coord.taskforce_after(pkg)
    mine = _readiness_verdicts(readiness(coord, pkg))
    marks = {r["seat"]: r["disposition"] for r in run_stage(coord, pkg)}

    if not theirs_rows:
        return False, ("criterion 7: coord.ready_seat_rows returned ZERO rows for the fixture — "
                       "an empty comparison would agree vacuously")

    diverged, unsound = [], []
    for seat, preds in after.items():
        theirs_ready = all(theirs_disp.get(p) == "done" for p in preds)
        mine_ready = mine.get(seat) == "ready"
        if mine_ready == theirs_ready:
            continue
        diverged.append(seat)
        if mine_ready and not theirs_ready:
            unsound.append("%s: THIS STAGE readies a row coord blocks" % seat)
            continue
        # Sound direction. It must be explained by the artifact grade and by nothing else.
        cause = [p for p in preds
                 if theirs_disp.get(p) == "done" and marks.get(p) == "failed"]
        if not cause:
            unsound.append("%s: blocked here, satisfied by coord, and NOT explained by the "
                           "declared-artifact grade" % seat)

    if unsound:
        return False, ("criterion 7: %d unexplained disagreement(s): %s. Investigate WHICH is "
                       "right before changing either; report to the leader with both outputs."
                       % (len(unsound), "; ".join(unsound)))
    if set(diverged) != EXPECTED_DIVERGENCES:
        return False, ("criterion 7: divergence set is %s, expected exactly %s — a new row "
                       "started disagreeing, or the named one stopped"
                       % (sorted(diverged), sorted(EXPECTED_DIVERGENCES)))
    return True, ("criterion 7: %d rows compared term-by-term against coord.ready_seat_rows; "
                  "agreement on %d, and the %d named divergence %s is one-directional and "
                  "explained by the declared-artifact grade"
                  % (len(after), len(after) - len(diverged), len(diverged),
                     sorted(EXPECTED_DIVERGENCES)))


# ---- STEP 4's checks (task 7.125 / M4-10) -----------------------------------------------------
#
# The fixture graph STEP 3 already writes carries every shape STEP 4 needs, so none is added here:
# four ready rows with predecessors, two ready rows with none (the root case), and eight ready rows
# carrying terminal marks (the leader's bar). Every expectation below is written out by hand — not
# one is computed from `enqueue`, from the mark table, or from `READY_AFTER`.

# The run-3 job catalogue id and launch profile are the caller's, never this stage's to invent, so
# the checks pass their own fixture values and the interface has no defaults for either.
FX_JOB_ID = "fx-launch-seat"
FX_PROFILE = "fx-profile"

# Every ready seat the self-state intersection MUST exclude, with the mark that excludes it. All
# eight are `ready` on the `after` term — their `after` cells are empty — and all eight are the
# wrong thing to launch. This is the leader's bar, spelled out row by row.
EXPECT_ENQUEUE_EXCLUDED = {
    "fx-done-outputs-present": "done",
    "fx-done-output-missing":  "failed",
    "fx-renew":                "failed",
    "fx-revive":               "failed",
    "fx-exited":               "failed",
    "fx-empty-disposition":    "failed",
    "fx-renewed-then-done":    "done",
    "fx-no-iospec":            "done",
}

# The seat -> seed the stage must produce, as paths RELATIVE to the fixture package (the check
# resolves them against it). `fx-r-two-done` and `fx-r-spaces` each name TWO predecessors that
# declare the SAME artifact, and the expectation says ONE path: de-duplication, written out rather
# than inferred. The two empty seeds are the root case of criterion 6.
EXPECT_ENQUEUE_SEED = {
    "fx-r-root":       [],
    "fx-r-one-done":   ["outputs/present.md"],
    "fx-r-two-done":   ["outputs/present.md"],
    "fx-r-spaces":     ["outputs/present.md"],
    "fx-open-sitting": [],
    "fx-no-row":       [],
}

# The interface signature three later seats call. Spelled out as a literal, and asserted against
# BOTH the live signature and the probe record on disk: a signature that moves after its consumers
# are built breaks them silently, which is the whole reason it is a declared output.
EXPECT_ENQUEUE_SIGNATURE = ("(coord, pkg, job_id, profile, readiness_result=None, at=None, "
                            "submit=None, dry_run=False)")

PROBE_RECORD = (_workspace_root(HERE) / ".rbtv" / "goals" / "build-core-daemon-mvp" / "runs"
                / "run-3" / "planning" / "m4-workflow-engine-runs-DAG-edged-jobs"
                / "probe-record-edge-runner-enqueue-builder.md")


def _stub_door():
    """A submitter standing in for the daemon's door: it records each argv and answers with a
    deterministic queue id in the door's own success wording.

    It stands in because this seat holds NO credential for the live gateway and is granted no
    arming act — the extensions table gives `register-job` to `queue-rearmer` and the enqueue right
    to three other seats. Driving the interface through an injected submitter exercises the whole
    stage (intersection, seed, argv, id parse, failure paths) while arming nothing, which is m4
    criterion C4's bound and not a convenience."""
    calls = []

    # Named `_door`, not `submit`: `check_single_enqueue_call_site` counts the submitter's INVOCATION
    # sites by source needle, and a stub whose own body reads like the call site would be counted as
    # a second one — the check would then be measuring its own helper instead of the interface.
    def _door(argv):
        calls.append(argv)
        return 0, "queued: queue id fx-q-%d\n" % len(calls), ""
    return _door, calls


def check_enqueue_schema(coord, pkg):
    """The declared output shape, asserted literally: `{enqueued: [{seat, job-id, seed}], ...}`,
    with a row in `enqueued` ONLY when the door named a real id, and `excluded` always present."""
    submit, calls = _stub_door()
    res = enqueue(coord, pkg, FX_JOB_ID, FX_PROFILE, submit=submit)
    if tuple(res) != ENQUEUE_RESULT_KEYS:
        return False, "schema: top-level keys are %r, expected %r" % (tuple(res),
                                                                     ENQUEUE_RESULT_KEYS)
    if "excluded" not in res:
        return False, "schema: `excluded` must be present even when empty"
    if not res["enqueued"]:
        return False, ("schema: ZERO rows enqueued on a fixture with launch candidates — an empty "
                       "result would satisfy every row assertion vacuously")
    for row in res["enqueued"]:
        if tuple(row) != ENQUEUE_ROW_KEYS:
            return False, "schema: an enqueued row's keys are %r, expected %r" % (tuple(row),
                                                                                 ENQUEUE_ROW_KEYS)
        if not row["job-id"]:
            return False, ("schema: %s is in `enqueued` with job-id %r — a row with no id is not "
                           "evidence of a queued job" % (row["seat"], row["job-id"]))
        if not isinstance(row["seed"], list) or not all(isinstance(s, str) for s in row["seed"]):
            return False, "schema: %s's `seed` is not a list of paths: %r" % (row["seat"],
                                                                             row["seed"])
    if len(calls) != len(res["enqueued"]):
        return False, ("schema: the door was called %d time(s) for %d enqueued row(s) — a row "
                       "nothing submitted is a fabricated queue entry"
                       % (len(calls), len(res["enqueued"])))
    return True, ("criterion 1: keys %r; %d enqueued, each with a real job-id and a seed, one door "
                  "call apiece" % (list(ENQUEUE_RESULT_KEYS), len(res["enqueued"])))


def check_enqueue_excludes_self_marked(coord, pkg):
    """CRITERION 1 / LEADER BAR — readiness is NOT launch candidacy.

    Every ready seat carrying a terminal mark must be EXCLUDED and NAMED, with the mark that
    excluded it. The expectation is the eight-row table above, compared exactly: a seat that stops
    being excluded is red, and so is one that starts."""
    submit, _ = _stub_door()
    res = enqueue(coord, pkg, FX_JOB_ID, FX_PROFILE, submit=submit)
    got = {s["seat"]: s["value"] for s in res["excluded"] if s["term"] == "terminal-mark"}
    if got != EXPECT_ENQUEUE_EXCLUDED:
        only_got = sorted(set(got) - set(EXPECT_ENQUEUE_EXCLUDED))
        only_exp = sorted(set(EXPECT_ENQUEUE_EXCLUDED) - set(got))
        wrong = sorted(s for s in set(got) & set(EXPECT_ENQUEUE_EXCLUDED)
                       if got[s] != EXPECT_ENQUEUE_EXCLUDED[s])
        return False, ("leader bar: the terminal-mark exclusions are wrong — excluded but should "
                       "not be %s; NOT excluded but must be %s; wrong mark %s. A ready seat with a "
                       "terminal mark that reaches the queue is a RELAUNCH of finished work."
                       % (only_got, only_exp, wrong))
    landed = {r["seat"] for r in res["enqueued"]} | {r["seat"] for r in res["validated"]}
    leaked = sorted(landed & set(EXPECT_ENQUEUE_EXCLUDED))
    if leaked:
        return False, "leader bar: %s were both excluded AND enqueued" % leaked
    if not all(s.get("reason") for s in res["excluded"]):
        return False, "leader bar: an exclusion carries no reason — an unnamed exclusion is invisible"
    return True, ("leader bar: all %d ready-but-terminally-marked seats excluded and NAMED with "
                  "their mark (%d done, %d failed); none reached the queue"
                  % (len(got), sum(1 for v in got.values() if v == "done"),
                     sum(1 for v in got.values() if v == "failed")))


def check_seed_carries_predecessor_outputs(coord, pkg):
    """CRITERION 2 — each launch is seeded with the ABSOLUTE artifact paths its predecessors
    declared, de-duplicated, and every one of them exists on disk right now."""
    submit, calls = _stub_door()
    res = enqueue(coord, pkg, FX_JOB_ID, FX_PROFILE, submit=submit)
    want = {seat: [str(pkg / rel) for rel in rels]
            for seat, rels in EXPECT_ENQUEUE_SEED.items()}
    got = {r["seat"]: r["seed"] for r in res["enqueued"]}
    if got != want:
        diffs = [("%s: seed %r, expected %r" % (s, got.get(s), want.get(s)))
                 for s in sorted(set(got) | set(want)) if got.get(s) != want.get(s)]
        return False, "criterion 2: %d wrong seed(s): %s" % (len(diffs), "; ".join(diffs))
    absent = [p for seed in got.values() for p in seed if not Path(p).exists()]
    if absent:
        return False, ("criterion 2: %d seed path(s) do not exist: %s — a seed naming a path that "
                       "is not there is a launch that fails on its first read" % (len(absent), absent))
    for argv in calls:
        blob = argv[argv.index("--args-json") + 1]
        if "seed" not in json.loads(blob):
            return False, "criterion 2: an enqueue command carries no `seed` in its args"
    return True, ("criterion 2: all %d seeds match the predecessors' declared outputs by name "
                  "(%d absolute path(s), all confirmed on disk), and every command carries its seed"
                  % (len(got), sum(len(s) for s in got.values())))


def check_root_seat_empty_seed(coord, pkg):
    """CRITERION 6 — a ready seat with NO upstream outputs enqueues with an EMPTY seed rather than
    failing. Checked on its own because the root case is precisely the one an implementation keyed
    on predecessors forgets, and it would otherwise hide inside the seed table."""
    submit, _ = _stub_door()
    res = enqueue(coord, pkg, FX_JOB_ID, FX_PROFILE, submit=submit)
    roots = ["fx-r-root", "fx-open-sitting", "fx-no-row"]
    rows = {r["seat"]: r for r in res["enqueued"]}
    failed = {r["seat"] for r in res["failed"]}
    for seat in roots:
        if seat in failed:
            return False, ("criterion 6: %s FAILED to enqueue — a seat with no predecessors has an "
                           "empty seed, which is a complete seed and not a shortfall" % seat)
        if seat not in rows:
            return False, "criterion 6: %s did not enqueue at all" % seat
        if rows[seat]["seed"] != []:
            return False, "criterion 6: %s's seed is %r, expected []" % (seat, rows[seat]["seed"])
    return True, ("criterion 6: all %d no-predecessor seats %s enqueued with an empty seed and a "
                  "real job-id" % (len(roots), roots))


def check_missing_seed_path_fails_loudly(coord, pkg):
    """CRITERION 2, failure arm — a seed path absent AT ENQUEUE TIME fails that seat's enqueue with
    the path NAMED, and the seat does not reach the queue.

    Driven as the time-of-check/time-of-use gap it actually is. Within ONE pass the case cannot
    arise: STEP 1-2 marks a seat `failed` when a declared output is missing, and a `failed`
    predecessor satisfies no edge — so the readiness result is computed FIRST, the artifact is then
    deleted, and the enqueue runs against the marks that were true a moment ago. That is the only
    way this row can appear in production, and a check that could not produce it would be asserting
    on a branch nothing reaches. The artifact is restored before returning."""
    res3 = readiness(coord, pkg)
    artifact = pkg / "outputs" / "present.md"
    body = artifact.read_text()
    submit, _ = _stub_door()
    try:
        artifact.unlink()
        res = enqueue(coord, pkg, FX_JOB_ID, FX_PROFILE, readiness_result=res3, submit=submit)
    finally:
        artifact.write_text(body)
    failed = {r["seat"]: r for r in res["failed"]}
    landed = {r["seat"] for r in res["enqueued"]}
    for seat in ("fx-r-one-done", "fx-r-two-done", "fx-r-spaces"):
        if seat not in failed:
            return False, ("criterion 2: %s enqueued with a seed path that is NOT on disk — the "
                           "launch would fail on its first read" % seat)
        if "outputs/present.md" not in failed[seat]["missing-seed-paths"]:
            return False, ("criterion 2: %s failed without NAMING the absent path (got %r) — an "
                           "unnamed missing path cannot be fixed by whoever reads this"
                           % (seat, failed[seat]["missing-seed-paths"]))
        tried = [t for d in failed[seat]["detail"] for t in d["tried"]]
        if str(artifact) not in tried:
            return False, ("criterion 2: %s named the declared token but not the ABSOLUTE path it "
                           "was looked for at (tried %r) — the token says what was declared, the "
                           "path says where to fix it" % (seat, tried))
        if seat in landed:
            return False, "criterion 2: %s is in BOTH `failed` and `enqueued`" % seat
    if "fx-r-root" not in landed:
        return False, ("criterion 2: the no-predecessor seat stopped enqueuing when an unrelated "
                       "artifact vanished — the failure must be per-seat, not a whole-pass abort")
    return True, ("criterion 2 failure arm: 3 seat(s) refused with the absent path %s named, none "
                  "of them queued, and the unaffected root seat still enqueued; artifact restored"
                  % artifact.name)


def check_single_enqueue_call_site():
    """CRITERION 3 — ONE enqueue implementation, proven by source inspection.

    Three later seats call this interface. If any of them writes its own, the run has two enqueue
    paths that will diverge, and the expensive half of that shape is that ONE OF THEM KEEPS
    REPORTING SUCCESS. The guard here is structural: the door's name and its verb are referenced by
    exactly ONE function, and the submitter is invoked at exactly one place. Every needle is
    ASSEMBLED from fragments so this check never matches its own text — a source search whose
    subject appears in the searching function measures itself and passes vacuously."""
    verb = "_ENQUEUE" + "_VERB"
    binary = "IGNITE" + "_BIN"
    call = "submit" + "(argv)"
    fns = {name: obj for name, obj in globals().items() if inspect.isfunction(obj)}
    holders = {needle: sorted(n for n, f in fns.items() if needle in inspect.getsource(f))
               for needle in (verb, binary, call)}
    if holders[verb] != ["_enqueue_argv"] or holders[binary] != ["_enqueue_argv"]:
        return False, ("criterion 3: the enqueue command is built in %s (verb) / %s (binary), "
                       "expected exactly ['_enqueue_argv'] for both — a second builder is a second "
                       "enqueue path, and one of two paths always keeps reporting success"
                       % (holders[verb], holders[binary]))
    if holders[call] != ["enqueue"]:
        return False, ("criterion 3: the submitter is invoked in %s, expected exactly ['enqueue']"
                       % holders[call])
    return True, ("criterion 3: the enqueue command is built in exactly ONE function "
                  "(`_enqueue_argv`) and submitted at exactly ONE call site (`enqueue`), across "
                  "%d functions in this file" % len(fns))


def check_enqueue_signature_is_recorded():
    """CRITERION 4 — the interface's signature is what its three consumers were told it is.

    Both directions are asserted: the LIVE signature equals the literal spelled out above, and the
    probe record on disk carries that same literal. A signature that changes after M4-11, M4-20 and
    M4-22 are built breaks them silently, and the record going stale is exactly how that happens
    without anyone noticing."""
    live = str(inspect.signature(enqueue))
    if live != EXPECT_ENQUEUE_SIGNATURE:
        return False, ("criterion 4: the live signature is %s, but its three consumers were given "
                       "%s" % (live, EXPECT_ENQUEUE_SIGNATURE))
    if not PROBE_RECORD.exists():
        return False, ("criterion 4: the declared record is absent at %s — a signature recorded "
                       "nowhere is a signature its consumers must guess" % PROBE_RECORD)
    if EXPECT_ENQUEUE_SIGNATURE not in PROBE_RECORD.read_text(encoding="utf-8"):
        return False, ("criterion 4: %s does not carry the signature %s — the record is STALE, "
                       "which is how a moved signature breaks a consumer silently"
                       % (PROBE_RECORD.name, EXPECT_ENQUEUE_SIGNATURE))
    return True, ("criterion 4: live signature `enqueue%s` matches the literal and is recorded in "
                  "%s" % (live, PROBE_RECORD.name))


# ---- STEP 4b's checks (M4-11) -----------------------------------------------------------------

# The four values of coord's closed disposition enum, spelled out as LITERALS. Not one is read from
# `ADVANCES_EDGE` or `EXPECTED_ENUM`: a check whose expectation is read from the constant under test
# moves with that constant and passes any change to it. `check_enum_matches_coord` separately binds
# these words to coord's own enum, so a rename there goes RED here instead of going silent.
FASTPATH_ADVANCES = "done"
FASTPATH_DOES_NOT_ADVANCE = ("renew", "revive", "exited")

FASTPATH_FIXTURE_ARM = {"job-id": "fx-edge-runner", "profile": "fx-profile"}

# The LIVE BUILD RUN's own package — a literal path, the C4 subject, and the thing this stage must
# be able to prove it did NOT arm. Resolved the same way `AUDIT` is (by looking for `.rbtv/`, never
# by counting parents), so a promotion that moves this file fails loudly instead of silently
# checking the wrong directory and reporting "not armed" about a path that does not exist.
THIS_RUN_PACKAGE = (_workspace_root(HERE) / ".rbtv" / "goals" / "build-core-daemon-mvp"
                    / "runs" / "run-3")


def _write_arm(pkg, payload):
    """Write an arming file into `pkg` and return its path. A `str` payload is written verbatim, so
    a check can arm with deliberately unparseable bytes."""
    p = arm_path(pkg)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(payload if isinstance(payload, str) else json.dumps(payload), encoding="utf-8")
    return p


def check_fastpath_only_done_advances(coord, pkg):
    """CRITERION 1 — a clean `done` check-out enqueues; `renew`, `revive` and `exited` enqueue
    NOTHING.

    THE DISCRIMINATING ARM of this whole stage, and the one a wrong reading makes expensive: a hook
    that fired on every disposition would advance DEAD seats, and it would do it while the run
    looked like it was progressing normally. Both halves are asserted at the DOOR — the count of
    submissions, not merely the returned `fired` flag — because a hook could set the flag correctly
    and still have reached the queue."""
    submit, calls = _stub_door()
    try:
        _write_arm(pkg, FASTPATH_FIXTURE_ARM)
        res = checkout_fastpath(coord, pkg, "fx-done-outputs-present", FASTPATH_ADVANCES,
                                submit=submit)
        if not res["fired"]:
            return False, ("`%s` did NOT fire on an armed package — %s"
                           % (FASTPATH_ADVANCES, res["why-not"]))
        if not calls:
            return False, ("`%s` reported fired but reached the door 0 times: an advancement that "
                           "enqueued nothing is not an advancement" % FASTPATH_ADVANCES)
        advanced = len(calls)
        for disp in FASTPATH_DOES_NOT_ADVANCE:
            before = len(calls)
            other = checkout_fastpath(coord, pkg, "fx-done-outputs-present", disp, submit=submit)
            if other["fired"] or len(calls) != before:
                return False, ("`%s` FIRED and reached the door %d time(s). A seat that has not "
                               "finished must never advance an edge — this is the silent stall the "
                               "closed enum exists to prevent" % (disp, len(calls) - before))
            if disp not in (other["why-not"] or ""):
                return False, ("`%s` stood down but the reason does not name the disposition, so "
                               "a reader cannot tell WHICH gate stopped it: %r"
                               % (disp, other["why-not"]))
    finally:
        arm_path(pkg).unlink(missing_ok=True)
    return True, ("criterion 1: `%s` reached the door %d time(s); `%s` reached it 0 times each, "
                  "every refusal naming its own disposition"
                  % (FASTPATH_ADVANCES, advanced, "`, `".join(FASTPATH_DOES_NOT_ADVANCE)))


def check_fastpath_unarmed_is_a_no_op(coord, pkg):
    """C4's shape at the smallest scale — an UNARMED package does not advance, and says why.

    This is the branch every check-out on every un-armed package in the workspace takes, the live
    build run's included. It must reach the door ZERO times, report `armed: False`, print NOTHING,
    and name the absent file so a reader can tell "not armed" from "broken"."""
    submit, calls = _stub_door()
    p = arm_path(pkg)
    if p.exists():
        return False, ("the fixture is armed at %s before the check ran, so this check cannot "
                       "measure the unarmed branch — a previous check leaked its arming file" % p)
    res = checkout_fastpath(coord, pkg, "fx-done-outputs-present", FASTPATH_ADVANCES, submit=submit)
    if res["armed"] or res["fired"] or calls:
        return False, ("an UNARMED package advanced: armed=%s fired=%s door-calls=%d. This is the "
                       "C4 breach in miniature" % (res["armed"], res["fired"], len(calls)))
    if str(p) not in (res["why-not"] or ""):
        return False, ("the refusal does not name the absent arming file, so a reader cannot tell "
                       "an unarmed package from a broken one: %r" % res["why-not"])
    if fastpath_lines(res) != []:
        return False, ("an unarmed check-out printed %r — it must print nothing at all, or every "
                       "check-out in the workspace gains noise about a hook that did not run"
                       % fastpath_lines(res))
    return True, ("an unarmed package reached the door 0 times, reported armed=False, printed "
                  "nothing, and named %s as the absent arming file" % p.name)


def check_fastpath_fails_closed_on_bad_arm(coord, pkg):
    """Every malformed arming file arms NOTHING — unparseable, wrong type, and each required key
    absent in turn.

    Fail-CLOSED is asserted rather than assumed because the failure it prevents is asymmetric: an
    arming mechanism that arms on a file it could not parse advances a run nobody meant to arm,
    and the diff that did it looks like a typo."""
    cases = [
        ("unparseable bytes", "{not json at all"),
        ("a JSON array, not an object", "[]"),
        ("no `job-id`", json.dumps({"profile": "fx-profile"})),
        ("no `profile`", json.dumps({"job-id": "fx-edge-runner"})),
        ("both keys present but empty", json.dumps({"job-id": "", "profile": ""})),
    ]
    try:
        for label, payload in cases:
            submit, calls = _stub_door()
            _write_arm(pkg, payload)
            res = checkout_fastpath(coord, pkg, "fx-done-outputs-present", FASTPATH_ADVANCES,
                                    submit=submit)
            if res["armed"] or res["fired"] or calls:
                return False, ("%s ARMED the hook (armed=%s fired=%s door-calls=%d) — it must fail "
                               "CLOSED" % (label, res["armed"], res["fired"], len(calls)))
            if "NOT ARMED" not in (res["why-not"] or ""):
                return False, ("%s did not report NOT ARMED: %r" % (label, res["why-not"]))
    finally:
        arm_path(pkg).unlink(missing_ok=True)
    return True, ("%d malformed arming files each armed nothing and each said NOT ARMED: %s"
                  % (len(cases), "; ".join(label for label, _ in cases)))


def check_fastpath_nothing_ready_is_clean(coord):
    """CRITERION 6 — an ARMED check-out that makes nothing ready enqueues nothing and does NOT
    error.

    The empty case is the one an implementation keyed on "there will be work" gets wrong, and it is
    the common case in a run's tail. Driven against a package built HERE with an empty taskforce,
    so "nothing ready" is a property of the input rather than of an accident in the shared fixture."""
    tmp = Path(tempfile.mkdtemp(prefix="edge-runner-fastpath-empty-"))
    try:
        pkg = tmp / "run-empty"
        (pkg / "coordination").mkdir(parents=True)
        (pkg / "taskforce.csv").write_text("seat,after\n", encoding="utf-8")
        (pkg / "sessions.csv").write_text("session-id,seat,started,ended,disposition,writer\n",
                                          encoding="utf-8")
        (pkg / "coordination" / "workers.md").write_text("", encoding="utf-8")
        _write_arm(pkg, FASTPATH_FIXTURE_ARM)
        submit, calls = _stub_door()
        res = checkout_fastpath(coord, pkg, "nobody", FASTPATH_ADVANCES, submit=submit)
        if not res["armed"]:
            return False, "the package was armed but the hook read it as unarmed: %s" % res["scope"]
        if not res["fired"]:
            return False, ("an armed `%s` check-out did NOT fire, so criterion 6 measures nothing: "
                           "%s" % (FASTPATH_ADVANCES, res["why-not"]))
        eq = res["enqueue"] or {}
        if eq.get("enqueued") or eq.get("validated") or eq.get("failed"):
            return False, ("nothing was ready, yet the result carries enqueued=%r validated=%r "
                           "failed=%r" % (eq.get("enqueued"), eq.get("validated"),
                                          eq.get("failed")))
        if calls:
            return False, ("nothing was ready, yet the door was reached %d time(s)" % len(calls))
        lines = fastpath_lines(res)
        if len(lines) != 1 or "made nothing ready" not in lines[0]:
            return False, ("an armed no-op must SAY it was armed and enqueued nothing — silence is "
                           "indistinguishable from the hook never running. Printed: %r" % lines)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return True, ("criterion 6: an armed `%s` check-out over an empty taskforce enqueued nothing, "
                  "reached the door 0 times, raised nothing, and said so in one line"
                  % FASTPATH_ADVANCES)


def check_fastpath_refuses_a_traceless_package(coord):
    """GATE 3 — an ARMED package with NO `sessions.csv` is refused WHOLESALE, and the same package
    WITH a trace still fires.

    TWO ARMS DIFFERING IN EXACTLY ONE VARIABLE, and the variable is named: both packages are built
    here, in the same act, from the same literals; the second one additionally carries a header-only
    trace file. Anything that made only the traceless arm refuse for some OTHER reason would fail
    the second arm too, which is what makes this a control rather than an assertion.

    THE WHOLESALE HALF IS ASSERTED DIRECTLY, because it is the part of the ruling that a later
    "refinement" would quietly undo: the refusal is produced for TWO DIFFERENT seat names and the
    two reasons must be BYTE-IDENTICAL. A per-seat trace decision — the shape
    `p-the-fastpath-must-REFUSE-a-package-with-no-trace-not-decide-per-seat` forbids — could not
    produce the same string for two different seats, so this comparison is the bound made
    mechanical rather than remembered."""
    def _build(root, with_trace):
        pkg = root / ("run-trace" if with_trace else "run-notrace")
        (pkg / "coordination").mkdir(parents=True)
        (pkg / "taskforce.csv").write_text("seat,after\nfx-a,\n", encoding="utf-8")
        (pkg / "coordination" / "workers.md").write_text("", encoding="utf-8")
        (pkg / "seats" / "fx-a").mkdir(parents=True)
        (pkg / "seats" / "fx-a" / "seat.md").write_text("fixture seat\n", encoding="utf-8")
        if with_trace:
            # Header only: a well-formed trace surface asserting nothing about any session. Its
            # PRESENCE is the whole variable.
            coord.sessions_csv(pkg).write_text(",".join(coord.SESSIONS_COLS) + "\n",
                                               encoding="utf-8")
        _write_arm(pkg, FASTPATH_FIXTURE_ARM)
        return pkg

    tmp = Path(tempfile.mkdtemp(prefix="edge-runner-fastpath-trace-"))
    try:
        notrace = _build(tmp, False)
        trace_path = coord.sessions_csv(notrace)
        if trace_path.exists():
            return False, ("the traceless arm was built WITH a trace at %s, so it measures nothing"
                           % trace_path)
        submit, calls = _stub_door()
        red = checkout_fastpath(coord, notrace, "fx-a", FASTPATH_ADVANCES, submit=submit)
        if not red["armed"]:
            return False, ("the traceless package did not read as ARMED (%s) — this check measures "
                           "the trace gate, which only an armed package reaches" % red["scope"])
        if red["fired"] or calls:
            return False, ("⚠ AN ARMED TRACELESS PACKAGE ADVANCED: fired=%s door-calls=%d. With no "
                           "trace every seat's disposition reads UNKNOWN and every seat falls "
                           "through into the candidate list — including the one that just checked "
                           "out" % (red["fired"], len(calls)))
        if str(trace_path) not in (red["why-not"] or ""):
            return False, ("the refusal does not name the absent trace surface %s, so a reader "
                           "cannot act on it: %r" % (trace_path, red["why-not"]))
        lines = fastpath_lines(red)
        if not any(str(trace_path) in ln for ln in lines):
            return False, ("the refusal is not PRINTED — a refusal nobody can read is a refusal "
                           "that gets worked around. Printed: %r" % lines)

        # WHOLESALE: a second seat name, and the reason must not move by one byte.
        other = checkout_fastpath(coord, notrace, "fx-some-other-seat", FASTPATH_ADVANCES,
                                  submit=submit)
        if other["why-not"] != red["why-not"]:
            return False, ("the refusal DIFFERS between two seats of the same package, so it is a "
                           "PER-SEAT decision and not the wholesale one the ruling requires:\n"
                           "  fx-a: %r\n  fx-some-other-seat: %r" % (red["why-not"],
                                                                     other["why-not"]))
        if calls:
            return False, "the second traceless seat reached the door %d time(s)" % len(calls)

        # THE OTHER ARM — same build, one variable added.
        green_pkg = _build(tmp, True)
        gsubmit, gcalls = _stub_door()
        green = checkout_fastpath(coord, green_pkg, "fx-a", FASTPATH_ADVANCES, submit=gsubmit)
        if not green["fired"]:
            return False, ("the SAME package WITH a trace did not fire, so the two arms differ in "
                           "more than the trace and this check controls nothing: %r"
                           % green["why-not"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return True, ("gate 3: an armed TRACELESS package reached the door 0 times, named %s in a "
                  "PRINTED refusal, and returned a BYTE-IDENTICAL reason for two different seats "
                  "(wholesale, not per-seat); the same package WITH a header-only trace fired and "
                  "reached the door %d time(s). One variable, both arms."
                  % (trace_path.name, len(gcalls)))


def check_fastpath_never_raises(coord):
    """The hook returns a result for inputs that have no right to work, and RAISES on none of them.

    It rides on a check-out that has already completed every irreversible act, so a throw here
    would report failure for a session that cannot be un-ended. The wrap at coord's call site is a
    SECOND guard; this asserts the first one, so neither is the only thing standing between a seat
    and a traceback at the end of its last command."""
    def _explodes(argv):
        raise RuntimeError("the door exploded")

    # ⚠ THE FIRST TWO CASES ALONE MAKE THIS CHECK VACUOUS, and that is measured rather than
    # feared: with only those two, narrowing the hook's `except Exception` to `except
    # ZeroDivisionError` left this check GREEN. Neither input reaches the guard — an absent path
    # and a file both resolve to "not armed" through ordinary control flow, so the check was
    # asserting the return shape of a path that never throws. THE THIRD CASE IS THE CHECK: it
    # arms a real package and hands the interface a door that raises, which is the only one of
    # the three that travels through the `try`. Kept together because the shape assertion is
    # still worth making on all three.
    tmp = Path(tempfile.mkdtemp(prefix="edge-runner-fastpath-raise-"))
    try:
        armed = tmp / "run-armed"
        (armed / "coordination").mkdir(parents=True)
        (armed / "taskforce.csv").write_text("seat,after\nfx-a,\n", encoding="utf-8")
        (armed / "sessions.csv").write_text(
            "session-id,seat,started,ended,disposition,writer\n", encoding="utf-8")
        (armed / "coordination" / "workers.md").write_text("", encoding="utf-8")
        (armed / "seats" / "fx-a").mkdir(parents=True)
        (armed / "seats" / "fx-a" / "seat.md").write_text("fixture seat\n", encoding="utf-8")
        _write_arm(armed, FASTPATH_FIXTURE_ARM)
        cases = [
            ("a package that does not exist", Path("/nonexistent/edge-runner/m4-11/run-x"),
             None, False),
            ("a package that is a FILE, not a directory", Path(__file__), None, False),
            ("an ARMED package whose door RAISES — the case that reaches the guard",
             armed, _explodes, True),
        ]
        for label, pkg, submit, must_reach_guard in cases:
            try:
                res = checkout_fastpath(coord, pkg, "whoever", FASTPATH_ADVANCES, submit=submit)
            except BaseException as exc:                              # noqa: BLE001
                return False, ("%s RAISED %s: %s — at a call site where the check-out has already "
                               "completed and cannot be un-ended"
                               % (label, type(exc).__name__, exc))
            if tuple(res) != FASTPATH_RESULT_KEYS:
                return False, ("%s returned keys %r, expected %r"
                               % (label, tuple(res), FASTPATH_RESULT_KEYS))
            if res["fired"]:
                return False, "%s reported fired=True" % label
            if must_reach_guard and "the door exploded" not in (res["why-not"] or ""):
                return False, ("%s did NOT travel through the hook's guard — `why-not` is %r, "
                               "which does not carry the raised error. This check would then be "
                               "asserting a path that never throws" % (label, res["why-not"]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return True, ("%d inputs each returned the declared %d-key result and raised nothing, and the "
                  "one that REACHES the guard (an armed package whose door raises) reported the "
                  "error as data" % (len(cases), len(FASTPATH_RESULT_KEYS)))


def check_fastpath_calls_the_one_interface():
    """CRITERION 3 — the fast path CALLS the wave's one enqueue interface and implements no enqueue
    of its own.

    Asserted by source inspection, not by reading the docstring: the hook's body must contain a call
    to `enqueue`, and must contain neither the door's verb nor the binary — those belong to
    `_enqueue_argv` alone, which `check_single_enqueue_call_site` pins independently. Every needle is
    ASSEMBLED from fragments so this check never matches its own text."""
    verb = "_ENQUEUE" + "_VERB"
    binary = "IGNITE" + "_BIN"
    src = inspect.getsource(checkout_fastpath)
    # The CALL is found by AST, not by a source needle: a needle keyed on the argument form goes
    # red on a harmless refactor (`enqueue(coord=coord, ...)`) and green on a hostile one that
    # merely mentions the name in a comment. `ast.parse` needs the source dedented — a method-level
    # `def` would not parse standalone; this one is module-level, and the parse failing IS a
    # finding rather than something to work around.
    calls = [n.func.id for n in ast.walk(ast.parse(src))
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
    if "enqueue" not in calls:
        return False, ("criterion 3: the hook calls %r and NONE of them is the enqueue interface — "
                       "a fast path that does not enqueue is not a fast path" % sorted(set(calls)))
    for needle in (verb, binary):
        if needle in src:
            return False, ("criterion 3: the hook references `%s`, so it is BUILDING an enqueue "
                           "command of its own. Two enqueue paths diverge, and the expensive half "
                           "of that shape is that one of them keeps reporting success (G-301)"
                           % needle)
    return True, ("criterion 3: the hook CALLS `enqueue` (AST, among %d call(s)) and references "
                  "neither `%s` nor `%s` — it implements no enqueue of its own"
                  % (len(calls), verb, binary))


def check_fastpath_call_site_in_coord():
    """ONE call site, in `cmd_checkout`, in coord.py — asserted against coord's own source by AST.

    Counted structurally rather than by grep because the answer must be about CALLS, not about the
    name appearing in a comment. A hook that quietly gains a second call site double-enqueues every
    advancement, and a hook whose call site drifts out of `cmd_checkout` fires on something that is
    not a check-out."""
    if not COORD_PATH.exists():
        return False, "coord.py is absent at %s" % COORD_PATH
    try:
        tree = ast.parse(COORD_PATH.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return False, "coord.py does not parse: %s" % exc
    wanted = "edge_fastpath" + "_on_checkout"
    holders = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name)
                    and inner.func.id == wanted):
                holders.append(node.name)
    if holders != ["cmd_checkout"]:
        return False, ("the hook is CALLED in %r, expected exactly ['cmd_checkout']: a second call "
                       "site double-enqueues every advancement, and a call site outside "
                       "`cmd_checkout` fires on something that is not a check-out" % holders)
    return True, ("`%s` is called at exactly ONE site in coord.py, inside `cmd_checkout`"
                  % wanted)


def check_this_run_is_not_armed():
    """CRITERION 4 (C4) — the LIVE BUILD RUN's own package is not armed, verified POSITIVELY.

    Not by the absence of an intent to arm it, and not by reading this wave's diff: by resolving the
    scoping mechanism against that package's real path and reading back what it says. The package
    itself must exist, or this check would report "not armed" about a directory that is not there —
    a vacuous pass, and exactly the shape that makes a C4 assurance worthless."""
    if not THIS_RUN_PACKAGE.is_dir():
        return False, ("the live run package is absent at %s, so this check cannot distinguish "
                       "'not armed' from 'looking in the wrong place'" % THIS_RUN_PACKAGE)
    arm, scope = fastpath_arm(THIS_RUN_PACKAGE)
    if arm is not None:
        return False, ("⚠ C4 BREACH: the LIVE run package IS ARMED — %s. This is an ungated cutover "
                       "on the run's own control loop, which `r-cutover-gated` forbids without an "
                       "agreed shadow window and a filed probe trail" % scope)
    return True, ("criterion 4: %s is NOT armed — %s"
                  % (THIS_RUN_PACKAGE, scope.split(". A package arms")[0]))


def build_fixture(root):
    """Write the fixture tree. Identical in content to the on-disk fixture the probe record drives,
    so `--selftest --fixture <DIR>` runs the same assertions against real disk."""
    pkg = root / "run-fx"
    (pkg / "outputs").mkdir(parents=True, exist_ok=True)
    (pkg / "outputs" / "present.md").write_text("fixture artifact — exists on disk\n")
    (pkg / "sessions.csv").write_text(
        "session-id,seat,harness,native-session-id,workdir,recorded,started,ended,pid,"
        "pid-starttime,tty,disposition\n"
        "s-01,fx-done-outputs-present,claude,n-01,/fx,,2026-07-30 06:00,2026-07-30 06:10,101,1000,/dev/pts/1,done\n"
        "s-02,fx-done-output-missing,claude,n-02,/fx,,2026-07-30 06:00,2026-07-30 06:10,102,1000,/dev/pts/2,done\n"
        "s-03,fx-renew,claude,n-03,/fx,,2026-07-30 06:00,2026-07-30 06:10,103,1000,/dev/pts/3,renew\n"
        "s-04,fx-revive,claude,n-04,/fx,,2026-07-30 06:00,2026-07-30 06:10,104,1000,/dev/pts/4,revive\n"
        "s-05,fx-exited,claude,n-05,/fx,,2026-07-30 06:00,2026-07-30 06:10,105,1000,/dev/pts/5,exited\n"
        "s-06,fx-empty-disposition,claude,n-06,/fx,,2026-07-30 06:00,2026-07-30 06:10,106,1000,/dev/pts/6,\n"
        "s-07,fx-open-sitting,claude,n-07,/fx,,2026-07-30 06:00,,107,1000,/dev/pts/7,\n"
        "s-08,fx-renewed-then-done,claude,n-08,/fx,,2026-07-30 05:00,2026-07-30 05:30,108,1000,/dev/pts/8,renew\n"
        "s-09,fx-renewed-then-done,claude,n-09,/fx,,2026-07-30 05:31,2026-07-30 06:10,109,1000,/dev/pts/9,done\n"
        "s-10,fx-no-iospec,claude,n-10,/fx,,2026-07-30 06:00,2026-07-30 06:10,110,1000,/dev/pts/10,done\n")
    # The ROSTER half of `seats_of` is load-bearing, not decoration: `fx-no-row` has no session row
    # at all and is discoverable ONLY here. Without this file the stage silently never verifies it,
    # which is exactly how an un-launched seat becomes invisible instead of undecided — the first
    # version of this fixture omitted it and `check_dispositions` caught the omission.
    # The `after` cells of the step-3 rows are QUOTED, because two of them are deliberately
    # malformed and one carries surrounding whitespace. csv.writer is used rather than a format
    # string so the file on disk is exactly what a csv reader will hand back.
    with (pkg / "taskforce.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["taskforce-id", "seat", "after", "harness", "model", "effort",
                    "ctx-refresh", "milestone-id"])
        for s in EXPECT:
            w.writerow(["tf-fx", s, "", "claude", "claude-opus-5", "medium", "50", "fx"])
        for s, cell in READY_AFTER.items():
            w.writerow(["tf-fx", s, cell, "claude", "claude-opus-5", "medium", "50", "fx"])
    # The step-3 rows get a descriptor apiece and NO session row: their own state must not shadow
    # the `after` term when coord.ready_seat_rows is run over this same package for the agreement
    # check (a seat with no descriptor reads UNBUILT there, and the comparison would be vacuous).
    for seat in READY_AFTER:
        d = pkg / "seats" / seat
        d.mkdir(parents=True, exist_ok=True)
        d.joinpath("seat.md").write_text(
            "---\nseat: %s\nharness: claude\n---\n<role id=\"fx-role\" version=\"latest\">\n"
            "A step-3 fixture row: it exists to carry an `after` cell.\n</role>\n" % seat)
    iospec = {"fx-done-output-missing": "outputs/absent.md"}
    for seat in EXPECT:
        d = pkg / "seats" / seat
        d.mkdir(parents=True, exist_ok=True)
        if seat == "fx-no-iospec":
            d.joinpath("seat.md").write_text(
                "---\nseat: fx-no-iospec\n---\n<role id=\"fx-role\" version=\"latest\">\n"
                "A fixture seat carrying no io-spec block — the shape every {TG} seat.md has on "
                "disk.\n</role>\n")
            continue
        d.joinpath("seat.md").write_text(
            "---\nseat: %s\n---\n<io-spec id=\"fx-io\" version=\"latest\">\n## Inputs\n\n"
            "- nothing; this is a fixture seat.\n\n## Outputs\n\n- `%s` — the declared artifact "
            "this fixture seat's done contract names.\n</io-spec>\n"
            % (seat, iospec.get(seat, "outputs/present.md")))
    return pkg


def cmd_selftest(fixture):
    coord = load_coord()
    tmp = None
    if fixture:
        pkg = Path(fixture).resolve()
        origin = "ON-DISK fixture %s" % pkg
    else:
        tmp = Path(tempfile.mkdtemp(prefix="edge-runner-selftest-"))
        pkg = build_fixture(tmp)
        origin = "hermetic temp fixture %s" % pkg
    print("edge-runner-job --selftest against %s" % origin)
    checks = [
        ("reads-subset-of-audit", lambda: check_reads_subset_of_audit()),
        ("reads-match-coord-reader", lambda: check_reads_match_coord_reader(coord)),
        ("enum-matches-coord", lambda: check_enum_matches_coord(coord)),
        ("dispositions", lambda: check_dispositions(coord, pkg)),
        ("refusal-is-explicit", lambda: check_refusal_is_explicit(coord, pkg)),
        ("evidence-is-per-seat", lambda: check_evidence_is_per_seat(coord, pkg)),
        ("scan-agrees-with-coord-reader", lambda: check_scan_agrees_with_coord_reader(coord, pkg)),
        ("no-status-column-written", lambda: check_no_status_column_written(coord, pkg)),
        # STEP 3 (M4-09)
        ("readiness-verdicts", lambda: check_readiness_verdicts(coord, pkg)),
        ("after-split-comma-only", lambda: check_after_split_is_comma_only(coord, pkg)),
        ("no-conditional-evaluator", lambda: check_no_conditional_evaluator_or_third_verdict()),
        ("readiness-schema", lambda: check_readiness_schema(coord, pkg)),
        ("agrees-with-coord-ready-seats", lambda: check_agrees_with_coord_ready_seats(coord, pkg)),
        # STEP 4 (M4-10)
        ("enqueue-schema", lambda: check_enqueue_schema(coord, pkg)),
        ("enqueue-excludes-self-marked", lambda: check_enqueue_excludes_self_marked(coord, pkg)),
        ("seed-carries-pred-outputs", lambda: check_seed_carries_predecessor_outputs(coord, pkg)),
        ("root-seat-empty-seed", lambda: check_root_seat_empty_seed(coord, pkg)),
        ("missing-seed-path-fails", lambda: check_missing_seed_path_fails_loudly(coord, pkg)),
        ("single-enqueue-call-site", lambda: check_single_enqueue_call_site()),
        ("enqueue-signature-recorded", lambda: check_enqueue_signature_is_recorded()),
        # STEP 4b (M4-11) — the check-out fast path
        ("fastpath-only-done-advances", lambda: check_fastpath_only_done_advances(coord, pkg)),
        ("fastpath-unarmed-is-a-no-op", lambda: check_fastpath_unarmed_is_a_no_op(coord, pkg)),
        ("fastpath-fails-closed-on-bad-arm", lambda: check_fastpath_fails_closed_on_bad_arm(coord,
                                                                                            pkg)),
        ("fastpath-nothing-ready-is-clean", lambda: check_fastpath_nothing_ready_is_clean(coord)),
        ("fastpath-refuses-traceless-pkg",
         lambda: check_fastpath_refuses_a_traceless_package(coord)),
        ("fastpath-never-raises", lambda: check_fastpath_never_raises(coord)),
        ("fastpath-calls-the-one-interface", lambda: check_fastpath_calls_the_one_interface()),
        ("fastpath-call-site-in-coord", lambda: check_fastpath_call_site_in_coord()),
        ("this-run-is-NOT-armed", lambda: check_this_run_is_not_armed()),
    ]
    failed = 0
    for name, fn in checks:
        try:
            ok, detail = fn()
        except Exception as exc:                                   # noqa: BLE001
            ok, detail = False, "raised %s: %s" % (type(exc).__name__, exc)
        print("  %-32s %s  %s" % (name, "PASS" if ok else "FAIL", detail))
        if not ok:
            failed += 1
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d/%d checks passed" % (len(checks) - failed, len(checks)))
    return 1 if failed else 0


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--package", help="the run folder to verify seats in")
    p.add_argument("--seat", action="append", default=[],
                   help="verify only this seat (repeatable); default is every seat on the trace "
                        "or the roster")
    p.add_argument("--json", action="store_true", help="emit the marks as JSON")
    p.add_argument("--readiness", action="store_true",
                   help="STEP 3: after marking, print which seats are ready and which are "
                        "blocked, each blocked row naming its unmet predecessors. Readiness is "
                        "the `after`-set term ONLY — it is not launch candidacy, and the "
                        "verdict vocabulary is closed at ready/blocked because no conditional "
                        "edge can be authored (issues.md G-301/G-308)")
    p.add_argument("--enqueue", action="store_true",
                   help="STEP 4: after marking and readiness, enqueue every LAUNCH CANDIDATE as a "
                        "daemon job seeded with its predecessors' declared outputs. Requires "
                        "--job-id and --profile. Readiness alone is NOT launch candidacy: the "
                        "ready list is intersected with the seat's own mark, its roster row and "
                        "its descriptor first, and every exclusion is named")
    p.add_argument("--job-id", default=None,
                   help="with --enqueue: the REGISTERED catalogue job whose fire launches a seat. "
                        "No default — the catalogue id belongs to whoever armed the queue")
    p.add_argument("--profile", default=None,
                   help="with --enqueue: the launch profile name. No default — the daemon requires "
                        "it of every launch-agent job and this stage does not invent one")
    p.add_argument("--at", default=None,
                   help="with --enqueue: ISO-8601 UTC fire time; default is now")
    p.add_argument("--dry-run", action="store_true",
                   help="with --enqueue: validate at the door and write nothing. Rows land under "
                        "`validated`, never `enqueued` — the two are different claims")
    p.add_argument("--arming-scope", action="store_true",
                   help="M4-11 (C4): print whether --package is armed for the check-out fast path, "
                        "the mechanism that scopes it, and — always, whatever --package is — "
                        "whether the LIVE BUILD RUN's own package is armed. Then exit. This is the "
                        "surface that answers 'what was this armed for?' off disk rather than off "
                        "a diff")
    p.add_argument("--signature", action="store_true",
                   help="print this wave's ONE enqueue interface signature and its result schema, "
                        "for the three seats that call it, then exit")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--fixture", default=None,
                   help="with --selftest: run the assertions against this on-disk package instead "
                        "of a temp tree")
    args = p.parse_args()

    if args.signature:
        print("edge-runner-job STEP 4 — the ONE enqueue interface of the m4 wave (task 7.125).")
        print("Called by: the check-out fast path (M4-11), the created goal's first workflow "
              "(M4-20), the C1 rehearsal (M4-22).")
        print("\n  from edge_runner_job import enqueue")
        print("  enqueue%s" % (inspect.signature(enqueue),))
        print("\n  -> {%s}" % ", ".join(ENQUEUE_RESULT_KEYS))
        print("     enqueued  [{%s}] — a row ONLY when the door returned a real id"
              % ", ".join(ENQUEUE_ROW_KEYS))
        print("     validated the same rows under dry_run=True; the door wrote nothing, so no id")
        print("     excluded   every ready seat the self-state intersection excluded, with its "
              "term and value. Present even when empty")
        print("     failed    every candidate that did not reach the queue, with the cause named")
        print("\n  job_id/profile have NO defaults — the catalogue id belongs to whoever armed the")
        print("  queue and the daemon requires a profile of every launch-agent job.")
        print("  submit is (argv) -> (rc, stdout, stderr) and defaults to the daemon's own door;")
        print("  inject it to exercise the interface without a daemon and without arming anything.")
        print("\n  DO NOT WRITE A SECOND ENQUEUE. Two implementations diverge, and the expensive")
        print("  half of that shape is that one of the two keeps reporting success (G-301).")
        return 0

    if args.arming_scope:
        print("edge-runner-job STEP 4b — the check-out fast path's ARMING SCOPE (task 7.126, m4 "
              "criterion C4).")
        print("\nThe mechanism, and the ONLY one: a package is armed by carrying")
        print("  {RUN}/coordination/%s   with both `job-id` and `profile`" % ARM_FILENAME)
        print("No environment variable and no flag can arm it. Either would arm every package the")
        print("process touches, and neither can be read back off disk later to answer what was")
        print("armed. Absent, unreadable, unparseable and incomplete all fail CLOSED.")
        if args.package:
            _, scope = fastpath_arm(Path(args.package).resolve())
            print("\n--package %s\n  %s" % (Path(args.package).resolve(), scope))
        # Printed on EVERY invocation, with or without --package: the question C4 asks is about
        # the live run, and an answer a reader has to remember to ask for is an answer that goes
        # unasked. The path is a literal, so this cannot be pointed somewhere reassuring.
        live_arm, live_scope = fastpath_arm(THIS_RUN_PACKAGE)
        print("\nTHE LIVE BUILD RUN — %s\n  %s" % (THIS_RUN_PACKAGE, live_scope))
        print("  verdict: %s" % ("⚠ ARMED — an ungated cutover on the live run's own control loop"
                                 if live_arm is not None else
                                 "NOT ARMED — C4 holds, read positively off the mechanism above"))
        return 1 if live_arm is not None else 0

    if args.selftest:
        return cmd_selftest(args.fixture)
    if not args.package:
        p.error("--package is required (or --selftest)")

    coord = load_coord()
    pkg = Path(args.package).resolve()
    marks = run_stage(coord, pkg, args.seat)

    if args.readiness:
        # Readiness is evaluated over the marks of a FULL pass, never over the `--seat` subset:
        # a predecessor left out of the subset would carry no mark and read as unmet.
        full = marks if not args.seat else run_stage(coord, pkg)
        res = readiness(coord, pkg, {r["seat"]: r["disposition"] for r in full})
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            for s in res["ready"]:
                print("READY    %-28s (own mark: %s)" % (s, res["self-marks"][s] or "none"))
            for b in res["blocked"]:
                print("BLOCKED  %-28s %s" % (b["seat"], b["reason"]))
                for p, note in b["notes"].items():
                    print("%-37s ⚠ `%s` — %s" % ("", p, note))
            for c in res["caveats"]:
                print("\ncaveat: %s" % c)
        return 0

    if args.enqueue:
        if not args.job_id or not args.profile:
            p.error("--enqueue requires --job-id and --profile: the catalogue id belongs to "
                    "whoever armed the queue, and the daemon requires a profile of every "
                    "launch-agent job. This stage invents neither.")
        full = marks if not args.seat else run_stage(coord, pkg)
        res3 = readiness(coord, pkg, {r["seat"]: r["disposition"] for r in full})
        res = enqueue(coord, pkg, args.job_id, args.profile, readiness_result=res3,
                      at=args.at, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            for r in res["enqueued"]:
                print("QUEUED    %-28s job %-12s seed: %s"
                      % (r["seat"], r["job-id"], ", ".join(r["seed"]) or "(none — root seat)"))
            for r in res["validated"]:
                print("VALIDATED %-28s (dry run — nothing written) seed: %s"
                      % (r["seat"], ", ".join(r["seed"]) or "(none — root seat)"))
            for s in res["excluded"]:
                print("excluded   %-28s %s" % (s["seat"], s["reason"]))
            for c in res["caveats"]:
                print("\ncaveat: %s" % c)
        # FAIL LOUD: a candidate that did not reach the queue goes to stderr, so it is never only
        # in a data structure somebody has to opt into reading.
        for r in res["failed"]:
            print("NOT ENQUEUED  %s — %s" % (r["seat"], r["reason"]), file=sys.stderr)
        return 1 if res["failed"] else 0

    if args.json:
        print(json.dumps(marks, indent=2))
    else:
        for m in marks:
            disp = m["disposition"] or "REFUSED-TO-DECIDE"
            print("%-28s %-18s %s" % (m["seat"], disp, m["reason"] or m["undecided-reason"]))
            print("%-28s evidence-read: %s" % ("", ", ".join(m["evidence-read"]) or "(none)"))
    # FAIL LOUD: a failed mark and a refusal both go to stderr, so neither is only in a data
    # structure somebody has to opt into reading.
    for m in marks:
        if m["disposition"] == "failed":
            print("FAILED  %s — %s" % (m["seat"], m["reason"]), file=sys.stderr)
        elif m["disposition"] is None:
            print("REFUSED %s — %s" % (m["seat"], m["undecided-reason"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
