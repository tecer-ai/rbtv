#!/usr/bin/env python3
"""edge-runner-job — CMP-25's pass, STEPS 1-3: verify a finished seat's done contract and mark it
`done` or `failed` (task 7.123 / M4-08), then evaluate readiness of every row whose `after` names
it (task 7.124 / M4-09).

Fired by the ignite daemon as a `fire-tool` job, one job per finished seat. CMP-25 is ONE engine
whose per-edge behaviour is entirely DATA; this file is that engine, and today it carries the
first three of its five steps.

⚠⚠ WHAT THIS FILE IS NOT, YET. CMP-25's pass has five steps: (1) verify the finished seat's done
contract, (2) mark it done or failed loudly, (3) evaluate every downstream row whose `after` names
it, (4) enqueue each ready seat's launch job, (5) exit. **Steps 1, 2 and 3 are here. Step 4 is
NOT, and its absence is a build state, not a design.** It is task 7.125 (M4-10, enqueue). A reader
who finds no enqueue arm here has found an unbuilt stage, not a missing feature.

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
import csv
import inspect
import json
import re
import shutil
import sys
import tempfile
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
        cand = Path(tok)
        bases = [Path("/")] if cand.is_absolute() else [pkg, pkg.parent.parent]
        for base in bases:
            p = (base / tok) if not cand.is_absolute() else cand
            if p.exists():
                resolvable.append(tok)
                break
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
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--fixture", default=None,
                   help="with --selftest: run the assertions against this on-disk package instead "
                        "of a temp tree")
    args = p.parse_args()

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
