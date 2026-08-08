#!/usr/bin/env python3
"""edge-runner-job — CMP-25's pass: verify a finished seat's done contract and mark it `done` or
`failed` (task 7.123 / M4-08), evaluate readiness of every row whose `after` names it (task 7.124 /
M4-09), enqueue each LAUNCH CANDIDATE as a daemon job seeded with its predecessors' declared
outputs (task 7.125 / M4-10), and exit (task C1 — see below: the exit is step 5 and it is the
DAEMON that reads it).

Fired by the ignite daemon as a `fire-tool` job. CMP-25 is ONE engine whose per-edge behaviour is
entirely DATA; this file is that engine.

⚠⚠ STEP 5 IS THE PROCESS EXIT, AND IT EXISTS ONLY ON THE DAEMON PATH (task C1, owner ruling
`d-owner-batch1` (1)). CMP-25's pass has five steps: (1) verify the finished seat's done contract,
(2) mark it done or failed loudly, (3) evaluate every downstream row whose `after` names it,
(4) enqueue each ready seat's launch job, (5) exit — "no long-lived driver survives this design".
Step 5 is not an arm this file could ever have carried alone: called IN-PROCESS from `coord.py`'s
check-out (STEP 4b) the pass RETURNS into a caller that keeps running, so there is no exit for
anybody to observe, and the interpreter's own `sys.exit` below reports to nothing. Fired as a
`fire-tool` job the pass IS a process and its exit is RECORDED: `ticker.recordToolCompletion` maps
exit 0 to a `done` completion and non-zero to `failed`, carrying this file's own output tail as the
corpus. Step 5 was therefore delivered by REGISTERING this file, not by adding an arm to it — the
return code below is the pass's report, and the daemon is the reader that makes it one.

⚠ STEP 4 IS THIS WAVE'S ONE ENQUEUE INTERFACE. `enqueue()` is called by the check-out fast path
(M4-11), the created goal's first workflow (M4-20) and the C1 rehearsal (M4-22). None of the three
writes its own: two enqueue implementations are G-301 rebuilt at the queue, and the expensive half
of that shape is that one of the two keeps reporting success. Its signature is a DECLARED OUTPUT of
task 7.125 and is recorded in `probe-record-edge-runner-enqueue-builder.md`; `--signature` prints
the live one, and a check binds the two together so it cannot move under its consumers silently.

**A CATALOGUE ENTRY NOW REGISTERS THIS FILE** — `tools: edge-runner` in
`ignite/config/spawn-profiles.yaml` (owner ruling `d-owner-batch1` (1): the edge-runner registers
as a REAL daemon job per CMP-25, superseding the interim in-process arm-file-gated call — which
stays intact and is not retired here). TWO BOUNDS SURVIVE THAT ENTRY, and both are still
`r-cutover-gated` (m4 criterion C4):

  LANDED IS NOT LIVE. `spawn-profiles.yaml` is BOOT-READ, so the entry reaches a daemon only
  through a restart, and firing it additionally needs a catalogue row in that machine's `heart.db`
  (`ignite register-job`) and a queue row (`ignite add-job`). Neither is in this repo — per-machine
  runtime state never is. Landing this entry arms nothing by itself.

  A FIRE STANDS DOWN ON AN UNARMED RUN. The entry names a GOAL and never a run: the live run is
  resolved at FIRE TIME (`--goal`), and STEP 4's `job-id`/`profile` are read from THAT run's own
  `coordination/edge-fastpath.json` — the same arm file, in the same single home, that the check-out
  fast path reads. An unarmed run is marked and reported and enqueues NOTHING, loud on stderr. The
  two triggers cannot disagree about what is armed, because there is exactly one file to disagree
  about.

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
  python3 edge-runner-job.py --goal <GOAL> --enqueue [--ignite-bin PATH]   # the catalogue entry
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
# 7.425 (W2): the guard's field is read INSIDE a declared output — the artifact, not the seat.md
# that names it. Declared as its own site rather than folded into `SEAT_MD_OUTPUTS`, because the
# two are read at different DEPTHS: the outputs section answers "does it exist" (PRIN-5's third
# grade), this one answers "what does it say". Both resolve to the SAME audited row — audit row 14
# names the site as "`{RUN}/seats/*/seat.md` `<io-spec>` Outputs + THE ARTIFACT PATHS IT NAMES",
# field `null`, so a guard field has no column to be audited under and is covered where its paths
# are. AUDIT ROW 15 WAS STALE for exactly the reason 7.425's seat recorded here: it still read
# "`skipped` — resolves to NO column … M4-09 builds no guard evaluator, and nothing can produce it"
# after 7.425 had built one. That seat reported it to the `leader` rather than editing another
# seat's surface, and it then sat. RECONCILED 2026-08-06 by task 7.454, which gave
# `run-state-job.py` the arm that EMITS the state and corrected both of the audit's sites under a
# claim-shaped grant (run-3 `decisions.md#p-mc12-granted-the-audit-row-claim-not-the-folder`).
# Row 15 now reads the state as DERIVED from this file's third verdict list; its `null` field
# verdict never moved. Nothing in THIS file's behaviour changed with that correction — only this
# comment, which had itself become the last carrier of the retired claim.
DECLARED_ARTIFACTS = "{RUN}/seats/*/seat.md <io-spec> Outputs -> the artifact paths it names"

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
    # STEP 3b (7.425 / W2) adds exactly this one, and it is audited at row 14 — see the constant.
    # The FIELD is `None` because the guard NAMES its own field (`ref[field=value]`), so no fixed
    # column resolves the site; that is the same reason row 14 carries `field: null`.
    (DECLARED_ARTIFACTS, None),  # the guard's field, read off the predecessor's VALIDATED OUTPUT
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
# ⚠⚠ THE SCOPE BOUND MOVED (7.425 / W2): THE THIRD VERDICT NOW EXISTS AND IS REACHED.
# Until 7.425 `VERDICTS` was closed at two values and the registry's state for a row excluded by a
# conditional edge was DEFINED AND UNREACHABLE — nothing could produce it, because nothing
# evaluated a guard. 7.424 (W1) collapsed the two `after`-member parsers so a consumer receives a
# member's DECOMPOSITION, and this task builds the evaluator on top of it. The third verdict is
# therefore produced, not merely named, and `check_skipped_is_produced_not_merely_named` asserts it
# FIRES on the fixture rather than asserting it is absent — the inverse of the check it replaces,
# for the inverse reason: a state that appears in a vocabulary but never in an output is the claim
# this file used to refuse, and the fix for it is to make it reachable, not to keep it out.
# ⚠ WHAT DID NOT MOVE: `issues.md` G-301/G-308 (the lint and the runtime reading one `after` cell
# differently) is NOT closed by this task — it is a GOAL-LINT defect, W3's surface, not this file's.
#
# WHY THE CELL PARSE IS STILL `coord.taskforce_after` AND NEVER A LOCAL SPLIT. The `after` cell has
# exactly one producer (`materialize-seats.py`) and one runtime parse (`coord.taskforce_after`,
# `raw.split(",")`, comma ONLY). A second parse here is G-301 rebuilt at a new seam: today
# `goal_cli.check_acyclic` DOES split those forms and reports NO finding while the runtime blocks
# the seat forever, and one of the two disagreeing readers says everything is fine. This stage
# reads what the RUNTIME reads, by calling it — and since 7.424 that call also carries the MEMBER
# grammar's decomposition, which this file consumes through `coord.after_member_parts` and
# decomposes NOWHERE of its own (`check_no_second_grammar_decomposition`).
#
# A bracketed token that does NOT decompose (`name[nokey]`, a second bracket group) is still ONE
# predecessor name taken verbatim, resolving to nothing and holding its seat blocked — that is
# `parse_after_member`'s own fail-safe direction, and `unresolvable_shape_note` makes it visible in
# the reason instead of leaving it as a silent forever-block.
#
# ⚠ READINESS IS NOT LAUNCH CANDIDACY, AND STEP 4 MUST NOT TREAT IT AS SUCH. This predicate has
# NO term for the seat's OWN state. `coord.ready_seat_rows` carries three more terms before it
# says READY — terminal(self) is None, no ACTIVE roster row, a descriptor on disk — and a seat
# that is already finished or already sitting satisfies this predicate while being the wrong
# thing to launch. The `self-marks` key and the `caveats` list below carry that bound in the
# output itself so the enqueue stage cannot miss it.

VERDICTS = ("ready", "blocked", "skipped")   # closed, spelled out, and compared against literally

NO_MARK = None                           # a predecessor nothing has marked. NEVER read as `done`.

_UNRESOLVABLE_SHAPE = re.compile(r"[\[\]|]")


def unresolvable_shape_note(name):
    """A note for an unmet predecessor whose token carries guard or alternate characters and yet
    did NOT decompose — `parse_after_member` handed it back as a bare name with those characters
    still in it (`name[nokey]`, a second bracket group, an unbalanced bracket).

    The note changes NO verdict and evaluates nothing. It reports that the whole token is one
    uninterpreted predecessor NAME, which is why it can never resolve: the MALFORMED-REF arm.
    Called only where the decomposition came back bare — a well-formed `ref[field=value]` and a
    well-formed alternate are EVALUATED (7.425), and neither reaches here."""
    if not _UNRESOLVABLE_SHAPE.search(name):
        return None
    return ("this token carries guard/alternate characters but did NOT decompose — the one member "
            "parse (`coord.parse_after_member`, reached through `after_member_parts`) handed it "
            "back as a BARE name with the brackets still in it, which is its fail-safe direction: "
            "an unparseable guard must never become a satisfied one. It therefore resolves to no "
            "seat and holds this row blocked. Fix the cell, not this stage.")


# ---- STEP 3b (task 7.425 / W2): THE GUARD EVALUATOR ------------------------------------------
#
# WHAT A GUARD IS HERE, AND WHAT IT IS NOT. `ref[field=value]` on an `after` member is evaluated
# DETERMINISTICALLY against `ref`'s VALIDATED OUTPUT — the artifacts its own `<io-spec> Outputs`
# declares, which STEP 1-2 already resolved on disk before marking it `done`. No judgment routes
# here and none may: a guard whose satisfaction needs a reading of prose is a DESIGN DEFECT
# upstream (Rule 10), reported to the `leader`, never built into this file.
#
# ⚠⚠ THIS IS NOT `coord`'s GUARD, AND THE TWO ANSWER DIFFERENT QUESTIONS. `coord.ready_seat_rows`
# discharges the SAME syntax against `coordination/guard-values.csv` — a LEADER'S RULING, the
# execution-strategy's B-2 lane. This stage reads the predecessor's OUTPUT FIELD, which B-2 itself
# routes here: "REFUSE [the ruled lane] when the condition IS machine-derivable from a
# predecessor's validated output field — then it is a plain deterministic guard on that field".
# So one grammar now has two evaluators consuming two different surfaces, and on an UNRULED but
# field-satisfied guard this stage READIES a row `coord` blocks. That direction is the one
# `p-edge-runner-strictness-is-ONE-DIRECTIONAL` forbids — a ruling that predates any guard
# evaluator and whose stated subject is the declared-artifact STRICTNESS ordering. It is NOT
# reconciled here (conforming down would delete this task) and it is NOT waved at:
# `check_agrees_with_coord_ready_seats` now compares the BARE-member rows, where the ordering still
# binds and is still measured, and NAMES the guarded rows it excluded with their count and cause.
# The amendment is the `leader`'s; the divergence is reported, not settled, by this file.
#
# THE FIELD SURFACE IS JSON, AND THE REASON IS DETERMINISM, NOT TASTE. A guard must resolve to one
# value or to none, off disk, with no interpretation. A declared `.json` output whose top level is
# an object gives exactly that; a markdown record does not. Every other declared artifact
# contributes NO field, so a guard over a run that declares no JSON is UNEVALUABLE — blocked and
# named — never satisfied and never excluded. The three verdicts are kept apart deliberately:
#   satisfied    the field is there and equals the guard's value          -> the edge admits
#   excluded     the field is there and DIFFERS                           -> the edge is SKIPPED
#   unevaluable  no field, unreadable, ambiguous, or a non-scalar value    -> the row stays BLOCKED
# Collapsing `unevaluable` into `excluded` would mark a row SKIPPED because nobody could read its
# guard, which is a silent branch death; collapsing it into `satisfied` admits an unruled edge.
GUARD_VERDICTS = ("satisfied", "excluded", "unevaluable")

# The join separator. The ALTERNATE grammar is the CELL's, one level ABOVE the member grammar —
# the same layering `coord.taskforce_after` already uses when it splits the cell on comma and
# hands each member to the one member parse. Splitting here is therefore not a second member
# decomposition, and every limb is re-made through `coord.AfterMember` so its guard is read by
# the ONE parse and never by this file (`check_no_second_grammar_decomposition`).
ALTERNATE_SEP = "|"


def _canonical_field(value):
    """The guard-comparable TEXT of a JSON value, or None when it is not comparable to one.

    A guard's right-hand side is text from a csv cell, so the comparison is text-to-text and the
    JSON side is rendered ONCE, here, in JSON's own spelling (`true`, `null`, `1.5`). An object or
    an array renders None — a guard cannot mean "equals this whole structure", and pretending it
    could would compare two arbitrary reprs and call the result a routing decision."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    if isinstance(value, str):
        return value
    return None


def validated_output_fields(pkg, pred):
    """({field: text}, [sources], [notes]) — the FIELD SURFACE of `pred`'s validated output.

    The artifacts are exactly the ones `declared_outputs` resolved: a seat's own `<io-spec>
    Outputs` paths, present on disk. `.json` artifacts whose top level is an object contribute
    their scalar fields; everything else contributes none and says so in `notes`.

    TWO ARTIFACTS DECLARING THE SAME FIELD WITH DIFFERENT VALUES DROP IT rather than picking one:
    an ambiguous field is not a routing input, and 'first file wins' makes the routing depend on
    the ORDER of a prose section. The dropped field then reads UNEVALUABLE at the guard, which is
    the fail-safe direction."""
    declared, resolvable, _missing, why = declared_outputs(pkg, pred)
    if declared is None:
        return {}, [], ["no declared-output site for `%s`: %s" % (pred, why)]
    fields, sources, notes, seen_at = {}, [], [], {}
    for tok in resolvable:
        path = resolve_declared_path(pkg, tok)
        if path is None or path.suffix.lower() != ".json":
            notes.append("`%s` contributes no field (not a `.json` declared output)" % tok)
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            notes.append("`%s` did not read as JSON (%s: %s) — it contributes NO field rather "
                         "than a guessed one" % (tok, type(exc).__name__, exc))
            continue
        if not isinstance(doc, dict):
            notes.append("`%s` parsed as %s, not an object — no top-level fields"
                         % (tok, type(doc).__name__))
            continue
        sources.append(str(path))
        for key, raw in doc.items():
            text = _canonical_field(raw)
            if text is None:
                notes.append("`%s`.%s is a %s — not comparable to a guard's text value"
                             % (tok, key, type(raw).__name__))
                continue
            if key in fields and fields[key] != text:
                notes.append("field `%s` is declared twice with different values (%r in %s, %r in "
                             "%s) — DROPPED, because an ambiguous field is not a routing input"
                             % (key, fields[key], seen_at[key], text, tok))
                fields.pop(key)
                seen_at[key] = None
                continue
            if seen_at.get(key, "") is None:      # already dropped as ambiguous; stay dropped
                continue
            fields[key], seen_at[key] = text, tok
    return fields, sources, notes


def evaluate_guard(pkg, pred, key, required, cache=None):
    """(verdict, detail) for ONE guard, where `pred` is ALREADY marked `done`.

    The `done` precondition is the caller's and it is the ordering CMP-25 states: a guarded edge
    whose predecessor never finished must read as an unfinished predecessor, not as a failed
    guard, or the reason names the wrong thing to fix. It is also what makes the output VALIDATED —
    STEP 1-2 marks `done` only once every declared path resolved on disk.

    `cache` is `{pred: (fields, sources, notes)}`, so N guards over one predecessor cost one read
    of its artifacts. Omit it and the read happens per call."""
    if cache is None:
        cache = {}
    if pred not in cache:
        cache[pred] = validated_output_fields(pkg, pred)
    fields, sources, notes = cache[pred]
    if key not in fields:
        return "unevaluable", {
            "guard": {"key": key, "required": required}, "found": None, "sources": sources,
            "notes": notes,
            "reason": "`%s`'s validated output declares NO field `%s` (%d field(s) readable from "
                      "%d source(s)). The guard is UNEVALUABLE, so this edge stays BLOCKED — it is "
                      "neither satisfied nor excluded, because nobody could read it."
                      % (pred, key, len(fields), len(sources))}
    found = fields[key]
    if found == required:
        return "satisfied", {
            "guard": {"key": key, "required": required}, "found": found, "sources": sources,
            "notes": notes,
            "reason": "`%s`.%s == %r in its validated output — the guard admits this edge."
                      % (pred, key, required)}
    return "excluded", {
        "guard": {"key": key, "required": required}, "found": found, "sources": sources,
        "notes": notes,
        "reason": "`%s`.%s is %r, and this edge requires %r — the guard EXCLUDES it, so the edge "
                  "is SKIPPED and no join waits on it." % (pred, key, found, required)}


def member_limbs(coord, member):
    """([limb], None) for an alternate member, ([member], None) for an ordinary one, or
    (None, reason) when the token cannot be split into well-formed limbs.

    WHAT DECIDES THAT A MEMBER IS AN ALTERNATE IS NOT THIS FUNCTION. `coord.parse_after_member`
    answers it — it strips bracketed content BEFORE testing for the separator, so a separator
    inside a guard VALUE is never read as a join — and this function splits only what it already
    called an alternate. Each limb is then re-made through `coord.AfterMember`, so the guard inside
    a limb is decomposed by the one parse site and never here.

    THE BALANCE TEST IS THE ONE CASE THE SPLIT CANNOT GET RIGHT: a token carrying a separator
    INSIDE a guard value AND one between limbs (`a[x=y|z]|b`) is cut in the wrong place by a text
    split, which leaves the fragment `a[x=y`. That is detected by bracket balance and REFUSED
    whole rather than evaluated on the fragments — a fragment parses as an ordinary bare name, so
    guessing here would silently route on a predecessor nobody named."""
    _name, _key, _value, unsupported = coord.after_member_parts(member)
    if not unsupported:
        return [member], None
    limbs = []
    for token in str(member).split(ALTERNATE_SEP):
        token = token.strip()
        if not token:
            continue
        if token.count("[") != token.count("]"):
            return None, ("this alternate carries `%s` both inside a guard value and between "
                          "limbs, so splitting it produces the unbalanced fragment %r. REFUSED "
                          "whole: a fragment parses as an ordinary seat name, and routing on one "
                          "would advance an edge nobody authored." % (ALTERNATE_SEP, token))
        limb = coord.AfterMember(token)
        if coord.after_member_parts(limb)[3]:
            return None, ("limb %r is itself unsupported after the split — the token is not a "
                          "flat alternate and this stage refuses to interpret it." % token)
        limbs.append(limb)
    if len(limbs) < 2:
        return None, ("the token reads as an alternate but yields %d limb(s) — refusing to "
                      "evaluate a join with nothing to join." % len(limbs))
    return limbs, None


def _simple_member_state(coord, pkg, member, marks, skipped, cache):
    """(state, detail) for ONE non-alternate member. state is `met`, `excluded` or `unmet`.

    `excluded` is the guard-false answer AND the transitive one: a predecessor whose OWN row this
    pass marked SKIPPED took no branch, so an edge out of it is dead too. Without that, the row
    after an untaken branch blocks forever and the join CMP-25 says must not wait, waits."""
    name, key, value, _unsupported = coord.after_member_parts(member)
    if name in skipped:
        return "excluded", {"seat": name, "state": "predecessor-skipped",
                            "reason": "`%s` is itself SKIPPED — its branch was not taken, so this "
                                      "edge out of it is dead. Exclusion propagates along the "
                                      "branch; it does not stop at the guarded edge." % name}
    mark = marks.get(name, NO_MARK)
    if mark != ADVANCES_EDGE:
        entry = {"seat": name, "state": mark if mark is not None else "no-mark",
                 "mark": mark, "raw": str(member)}
        note = unresolvable_shape_note(str(member))
        if key is None and note:
            entry["shape-note"] = note
        if key is not None:
            entry["guard"] = {"key": key, "required": value}
            entry["reason"] = ("`%s` is not marked `%s` (mark: %s). The guard `%s` was NOT "
                               "evaluated: the dependency half comes first, so an unfinished "
                               "predecessor reads as unfinished and not as a failed guard."
                               % (name, ADVANCES_EDGE, mark, key))
        return "unmet", entry
    if key is None:
        return "met", None
    verdict, detail = evaluate_guard(pkg, name, key, value, cache)
    detail = dict(detail, seat=name, state="guard-" + verdict, raw=str(member))
    if verdict == "satisfied":
        return "met", detail
    if verdict == "excluded":
        return "excluded", detail
    return "unmet", detail


def member_state(coord, pkg, member, marks, skipped, cache):
    """(state, detail) for ONE `after` member, alternates included. `met` | `excluded` | `unmet`.

    THE JOIN IS `whichever ran`: an alternate is MET as soon as ONE limb is met, which is what
    lets a fork's join complete over the branch that was taken while the other is SKIPPED. It is
    EXCLUDED only when EVERY limb is excluded — no branch was taken at all — and UNMET while any
    limb is still merely unfinished, because that limb may yet run."""
    limbs, why = member_limbs(coord, member)
    if limbs is None:
        return "unmet", {"seat": str(member), "state": "malformed-alternate", "raw": str(member),
                         "shape-note": why, "reason": why}
    if len(limbs) == 1:
        return _simple_member_state(coord, pkg, limbs[0], marks, skipped, cache)
    states = [_simple_member_state(coord, pkg, limb, marks, skipped, cache) for limb in limbs]
    limb_detail = [{"limb": str(limb), "state": st, "detail": d}
                   for limb, (st, d) in zip(limbs, states)]
    kinds = [st for st, _ in states]
    if "met" in kinds:
        return "met", {"seat": str(member), "state": "alternate-join-met", "limbs": limb_detail,
                       "reason": "%d of %d alternates is MET — the join completes on whichever "
                                 "ran." % (kinds.count("met"), len(kinds))}
    if all(k == "excluded" for k in kinds):
        return "excluded", {"seat": str(member), "state": "alternate-join-excluded",
                            "limbs": limb_detail, "raw": str(member),
                            "reason": "every one of the %d alternates is excluded — no branch was "
                                      "taken, so this join is dead too." % len(kinds)}
    return "unmet", {"seat": str(member), "state": "alternate-join-unmet", "limbs": limb_detail,
                     "raw": str(member),
                     "reason": "no alternate is met yet and %d is still unfinished — the join "
                               "waits on a limb that may still run." % kinds.count("unmet")}


def _row_state(coord, pkg, seat, preds, marks, skipped, cache):
    """One row's verdict over its own `after` members. PRECEDENCE, and the order is the design:
    BLOCKED before SKIPPED. A row with one unmet member and one excluded member is not settled —
    calling it SKIPPED would kill a branch on an edge nobody has finished evaluating."""
    unmet, unmet_marks, notes, excluded, render = [], {}, {}, [], {}
    for p in preds:
        state, detail = member_state(coord, pkg, p, marks, skipped, cache)
        render[str(p)] = {"state": state, "detail": detail}
        if state == "unmet":
            unmet.append(str(p))
            unmet_marks[str(p)] = detail.get("mark", detail.get("state"))
            for key in ("shape-note", "reason"):
                if detail.get(key):
                    notes[str(p)] = detail[key]
                    break
        elif state == "excluded":
            excluded.append({"member": str(p), "detail": detail})
    if unmet:
        return {"verdict": "blocked", "seat": seat, "unmet": unmet, "unmet-marks": unmet_marks,
                "after": [str(p) for p in preds], "notes": notes, "after-render": render,
                "reason": "after: " + " ".join(
                    "%s=%s" % (p, unmet_marks[p] if unmet_marks[p] is not None else "<no mark>")
                    for p in unmet)}
    if excluded:
        return {"verdict": "skipped", "seat": seat, "excluded-by": excluded,
                "after": [str(p) for p in preds], "after-render": render,
                "reason": "guard-excluded: " + " ".join(
                    "%s — %s" % (e["member"], e["detail"].get("reason", "")) for e in excluded)}
    return {"verdict": "ready", "seat": seat, "after": [str(p) for p in preds],
            "after-render": render}


def readiness(coord, pkg, marks=None):
    """`{ready: [seat], blocked: [{seat, unmet: [pred], ...}], skipped: [{seat, excluded-by, ...}],
    ...}` for every `taskforce.csv` row.

    `marks` is `{seat: disposition}` as STEP 1-2 emits it (`done` | `failed` | None). Omit it and
    it is computed by running that stage — the same code path, never a second reading of the
    trace. Rows are returned in `taskforce.csv` FILE ORDER, which is `taskforce_after`'s order.

    Only the literal mark `done` satisfies an edge. `failed` does NOT, and neither does an absent
    mark: `failed` is terminal, and reading terminal as "finished, therefore satisfied" is the
    plausible wrong reading that would advance a workflow past work that did not pass.

    7.425: guards are EVALUATED and `skipped` is a third verdict. It is computed to a FIXPOINT
    because exclusion propagates along a branch — the row after a skipped row is skipped too — and
    `taskforce.csv` file order is not guaranteed to be topological. The iteration is monotone (the
    skipped set only grows: a member's exclusion is never withdrawn by another row becoming
    skipped), so it settles in at most one round per row; the bound is spelled out rather than
    trusted, and the final round is the one that changed nothing."""
    if marks is None:
        marks = {r["seat"]: r["disposition"] for r in run_stage(coord, pkg)}
    after = coord.taskforce_after(pkg)

    cache, skipped_seats, rows = {}, set(), []
    for _round in range(len(after) + 1):
        rows = [_row_state(coord, pkg, seat, preds, marks, skipped_seats, cache)
                for seat, preds in after.items()]
        now = {r["seat"] for r in rows if r["verdict"] == "skipped"}
        if now == skipped_seats:
            break
        skipped_seats = now

    ready = [r["seat"] for r in rows if r["verdict"] == "ready"]
    blocked = [{k: v for k, v in r.items() if k != "verdict"}
               for r in rows if r["verdict"] == "blocked"]
    skipped = [{k: v for k, v in r.items() if k != "verdict"}
               for r in rows if r["verdict"] == "skipped"]

    return {
        "ready": ready,
        "blocked": blocked,
        # 7.425: the guard-excluded rows, in DERIVED state ONLY — nothing is written anywhere, and
        # `check_no_status_column_written` runs this pass too. Present even when EMPTY: an empty
        # list says "no edge was excluded", an absent key says nothing at all.
        "skipped": skipped,
        # The seat's OWN mark, for every seat this predicate calls ready. Carried because the
        # predicate has no self-state term and a consumer that launched on `ready` alone would
        # relaunch a finished seat.
        "self-marks": {s: marks.get(s, NO_MARK) for s in ready},
        "caveats": [
            "readiness is the `after`-set term ONLY. Launch candidacy additionally requires "
            "terminal(self) is None, no ACTIVE roster row, and a descriptor on disk — the three "
            "terms coord.ready_seat_rows carries and this predicate does not.",
            "the verdict vocabulary is closed at %s. `skipped` is a GUARD-EXCLUDED row — its "
            "guard was read off a predecessor's validated output and did not match, or its whole "
            "branch was excluded upstream. It is DERIVED state: no column, anywhere (Rule 14)."
            % (list(VERDICTS),),
            "a guard whose field could not be READ is UNEVALUABLE and leaves its row BLOCKED — "
            "never skipped and never satisfied. `skipped` therefore means an edge was evaluated "
            "and excluded, and never means an edge nobody could evaluate.",
            "this stage's guard reads the predecessor's validated OUTPUT FIELD; "
            "coord.ready_seat_rows discharges the same syntax against a LEADER'S RULING in "
            "coordination/guard-values.csv. Two evaluators, two surfaces, one grammar — on an "
            "unruled but field-satisfied guard the two DISAGREE, and this one readies. Reported "
            "to the leader against `p-edge-runner-strictness-is-ONE-DIRECTIONAL`, not settled "
            "here.",
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
#
# ⚠ THE DEFAULT IS A BARE NAME AND A FIRED JOB MUST NOT RELY ON IT (task C1). A `fire-tool` exec
# inherits the systemd --user MANAGER's PATH — `runToolLikeExec` passes `envFile: null` — and that
# PATH does not carry `~/.local/bin`, where this binary is installed. The bare name resolves for
# every INTERACTIVE caller and for the in-process fast path, and resolves for NOBODY under the
# daemon; `--ignite-bin` rebinds it to an absolute path, which is what the catalogue entry passes.
# Same reasoning, one field over, as the `restart-daemon` entry's absolute-interpreter note.
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


def _enqueue_argv(job_id, profile, pkg, seat, seed, at, dry_run, prompt):
    """THE ONLY PLACE AN ENQUEUE COMMAND IS BUILT IN THIS TREE.

    `check_single_enqueue_call_site` asserts by source inspection that the door's verb appears in
    exactly this one function and nowhere else in the file. `profile` is the one argument the
    daemon REQUIRES of a launch-agent job, so it is a required parameter here rather than a
    default this stage invents.

    THE ARGS OBJECT CARRIES EXACTLY THE THREE REGISTERED KEYS `{profile, prompt, workdir}` (M4-38,
    extended by 7.445). It once carried `{profile, seat, package, seed}`; `seat`, `package` and
    `seed` are in no registered `args_schema`, and the door refuses the object by NAME on the first
    of them (`E_BAD_ARGS`), which masked a second refusal on a placeholder profile behind it. THE
    SEED NO LONGER RIDES IN ARGV AND MUST NOT BE PUT BACK: a seat is driven by its DESCRIPTOR and
    by the room, never by argv text, so predecessor-output addresses reach a seat through its own
    `seat.md` (milestone-spine part iii). `seed` stays a parameter here and stays in the RESULT
    rows — it is what the failure and exclusion arms report on — it simply is not submitted.

    ⚠ `prompt` IS A REGISTERED KEY AND IS NOT THE SEED RETURNING. It is the seat's BOOT PROMPT —
    the message `ticker.launchAgent` reads off `args.prompt` and `spawn.ensurePromptFile` writes to
    the 0600 file the harness receives as stdin. Absent, that file is written `''` and a harness
    that requires a message dies promptless (finding D). It is declared `optional: {prompt:
    'string'}` in every launch-agent `args_schema` this tree registers (`engine/attached-run.js`,
    the ticker and chat probes) and is a KNOWN request key at the spawn door (`spawn.js`
    `validateRequestKeys`). It carries no free text: batch-08 item 4 half A collapsed the headless
    vocabulary to `{stdin}`, and this value never becomes argv of the harness — only of the door.

    ⚠⚠ SCOPE, NAMED: a catalogue row registered OUT OF BAND whose `args_schema` omits `prompt`
    refuses this object with `unknown argument: prompt`, and registration is create-only. This
    stage cannot read that schema, so the refusal is reported as a `failed` row carrying the door's
    own text — never swallowed."""
    args_obj = {"profile": profile, "prompt": prompt,
                "workdir": str((Path(pkg) / "seats" / seat).resolve())}
    argv = [IGNITE_BIN, _ENQUEUE_VERB,
            "--fn", job_id,
            "--args-json", json.dumps(args_obj, sort_keys=True),
            "--trigger", "scheduled",
            "--at", at]
    if dry_run:
        argv.append("--dry-run")
    return argv


def seat_prompts(coord, pkg):
    """{seat -> descriptor dict} for every seat the kit can DISCOVER under this package.

    One read of the roster surface per enqueue pass, through `coord.discover_workers` — the kit's
    own descriptor reader. A private frontmatter parse here would be a second reading of the same
    surface, and the two would drift the day a descriptor key moves (7.445 exists because a value
    the launch path composes never reached the queue).

    `launch_candidates` admits a seat on its descriptor's EXISTENCE; discovery additionally needs
    the identity key (`seat:`/`agent:`). The two are deliberately not the same test, so a seat can
    be a candidate and still be absent here — `seat_boot_prompt` turns that into a refusal."""
    return {w["agent"]: w for w in coord.discover_workers(coord.workers_dir(_coord_args(pkg)))}


def _coord_args(pkg):
    """The namespace coord's resolvers read a package out of. Every one of them uses `getattr`
    with a default, so naming `package` is enough and no other key is invented here."""
    return argparse.Namespace(package=str(pkg))


def seat_boot_prompt(coord, pkg, seats, seat):
    """(prompt, error) — the seat's boot prompt from THE KIT'S ONE COMPOSER, `coord.boot_prompt`.

    ⚠ THIS FUNCTION COMPOSES NOTHING. It calls the composer the live launch path calls
    (`coord.launch_seat` -> `prompt_file(args, w["agent"], prompt or boot_prompt(w, args))`) so a
    daemon-launched seat and a hand-launched one boot from the SAME bytes. Copying the composition
    here would make this file a second source of a seat's first instruction, and the two would
    disagree silently — the seat that read the stale one would look launched and be wrong.

    Returns the error instead of raising: a composition that fails must REFUSE ITS OWN enqueue and
    leave every other candidate of the pass untouched. An empty prompt is a failure, not a value:
    it is exactly what the defect produced, and queueing it would reproduce the defect through the
    fix."""
    w = seats.get(seat)
    if w is None:
        return None, ("no DISCOVERABLE descriptor: {RUN}/seats/%s/seat.md exists (that is why this "
                      "seat is a candidate) but carries no `seat:`/`agent:` frontmatter key, so "
                      "the kit's own reader cannot name it and no prompt can be composed for it. "
                      "Enqueuing it would queue a launch with an empty stdin." % seat)
    try:
        prompt = coord.boot_prompt(w, _coord_args(pkg))
    except Exception as exc:                                    # noqa: BLE001 — reported as data
        return None, ("composing the boot prompt raised %s: %s. A launch is not queued on a prompt "
                      "that could not be built." % (type(exc).__name__, exc))
    if not (prompt or "").strip():
        return None, ("the composer returned an EMPTY prompt. An empty prompt is what this stage "
                      "exists to stop reaching the queue, not a value to submit.")
    return prompt, ""


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
    for member in after.get(seat, []):
        # 7.425: THE SEED RESOLVES THE CLEAN PREDECESSOR NAME, NEVER THE RAW MEMBER TOKEN. Before
        # the guard evaluator existed, no guarded row could become ready, so this loop only ever
        # saw bare tokens and `{RUN}/seats/<token>/seat.md` happened to resolve. A guarded row now
        # reaches it, and `seats/fx-route[risk=high]/seat.md` is a directory that cannot exist —
        # the seat would be launched with a SILENTLY EMPTY seed, which is the same name-lookup
        # defect 7.383 closed at the readiness loop, one stage downstream. The clean name comes off
        # the member itself (W1's decomposition), never from a second parse here. For a BARE member
        # the clean name IS the token, so no plain row's seed changes.
        for pred, alternate in _seed_predecessors(coord, member):
            declared, resolvable, absent, err = declared_outputs(pkg, pred)
            if alternate:
                # AN UNTAKEN ALTERNATE PRODUCED NOTHING, AND THAT IS NOT A FAILURE. A join is
                # seeded from the limbs that RAN; a limb whose declared artifact is absent is the
                # branch that did not run, so it contributes nothing instead of failing the
                # enqueue. ⚠ SCOPE, NAMED: which limb ran is the readiness pass's knowledge and is
                # NOT threaded here — this stage seeds the UNION of what the limbs left on disk.
                # Two limbs that both ran therefore seed both artifacts. Sharpening that is
                # M4-10's, not this arm's, and it is reported rather than assumed correct.
                absent = []
            _seed_member(pkg, seed, missing, seen, pred, resolvable, absent)
    return seed, missing


def _seed_predecessors(coord, member):
    """[(clean predecessor name, is-an-alternate-limb)] for ONE `after` member.

    A bare or guarded member yields exactly one name — its own. An alternate yields one per limb.
    A member that does not decompose at all yields its RAW token, which resolves to no seat and is
    reported as such rather than dropped."""
    limbs, _why = member_limbs(coord, member)
    if limbs is None:
        return [(str(member), False)]
    if len(limbs) == 1:
        name = coord.after_member_parts(limbs[0])[0]
        return [(name or str(member), False)]
    return [(coord.after_member_parts(limb)[0] or str(limb), True) for limb in limbs]


def _seed_member(pkg, seed, missing, seen, pred, resolvable, absent):
    """Fold ONE predecessor's declared outputs into `seed`/`missing` IN PLACE. Split out of
    `seed_for` only so the per-member loop above stays readable; the behaviour is unchanged from
    the inline form it replaced."""
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


# ---- STEP 4a (task 7.469 / CW5): THE DECLARED-OUTPUT ADMISSION CHECK --------------------------
#
# WHAT IT REFUSES, AND WHY THE REFUSAL BELONGS AT THE QUEUE. A seat that launches CAGED writes
# inside bwrap walls composed from `cage.SeatBinds`; everything outside them is read-only or simply
# absent. A row whose `<io-spec> ## Outputs` declares a token in such a place is a row that WILL
# fail on its own first write — and today it fails at the FAR end, after a launch, as a missing
# artifact that STEP 1-2 marks `failed`. That reads as "the seat did not do its work" when the
# truth is "the declaration named a place the seat was never able to write". This check moves the
# failure to the one door every queued caged launch passes (task 7.468 computed that `enqueue` is
# that door), where it costs one refusal instead of one wasted seat and one misattributed mark.
#
# ⚠ IT IS SCOPED TO CAGED LAUNCHES, AND THAT SCOPE IS THE DESIGN, NOT A SHORTCUT. Task 7.470
# converts 11 tokens now and the remaining 228 as each component is next materialized
# (milestone-task-dag §2.4, arm 2). Those 228 belong to seats that launch into tmux UNCAGED, where
# nothing is broken. Refusing them here would silently convert a ruled deferral into a forced
# 251-token migration. So an UNCAGED row is NOT refused — and this check is precisely the mechanism
# that makes that deferral honest rather than a promise (`r-gate-ships-with-its-own-key`, K1).
#
# ⚠⚠ THE CAGE CLASSIFICATION IS A MEASURED SNAPSHOT, NOT A LIVE COMPOSITION, and every refusal says
# so on its own face rather than in this comment. No Python frame on this path holds a composed
# cage spec and none can: composing one here would be a SECOND cage composer in a second language,
# against `r-seats-only-architecture (1)`. So the wall was measured ONCE, from INSIDE real composed
# cages with real writes and real reads, by task 7.466 — and the table below is that measurement,
# transcribed. If `cage.SeatBinds` changes, this table goes stale WHILE STILL REFUSING
# CONFIDENTLY. That is the one failure mode a reader cannot see from a refusal alone, which is why
# the provenance travels IN the refusal text: a refusal that cannot be dated cannot be trusted.
#
# ⚠⚠ AND THE TABLE IS INCOMPLETE, WHICH IS A DIFFERENT DEFECT FROM STALE. It carries no row for
# `branches/<b>/coordination/`. An unmapped subtree is `undecided`, and `undecided` REFUSES — it is
# NEVER admitted and never passed through (leader bar, 2026-08-07). A branch-relative token that
# reads admissible on paper may be unwritable in fact: `composeCageFor` passes `runDir` straight
# through, and the one construction site found builds a PARENT-run path. Fail-closed here is
# load-bearing, not defensive tidiness.

_ADMISSIBLE = "admissible"
_INADMISSIBLE = "inadmissible"
_UNDECIDED = "undecided"

# THE RULE, verbatim from its ONE home — the docstring and refusal texts of task 7.467's
# `token_admissible` (sha256:f89c6b7abece83e9). There is no separate convention document, so this
# text is not a summary of the rule: it IS the rule, and it is carried into every refusal so a
# reader who hits one needs no second document.
_ADMISSION_RULE = (
    "A declared-output token is ADMISSIBLE iff its subtree is WRITABLE in the producing seat's "
    "composed cage AND -- where any successor reads it -- READABLE in that successor's composed "
    "cage. The discriminator is per ROW (\"does a successor read it\"), never per subtree.")

_ADMISSION_HOMES = (
    "WHERE AN ADMISSIBLE TOKEN LIVES: no successor reads it -> `seats/<self>/...`; a successor "
    "reads it -> `coordination/<producer>-<artifact>`; `outputs/` and `branches/.../outputs/` are "
    "INADMISSIBLE for a caged producer. The `coordination/` home is an INTERIM and retires at task "
    "7.57, when the gateway path supersedes it.")

_CAGE_MAP_PROVENANCE = (
    "PROVENANCE OF THE CAGE CLASSIFICATION (task 7.466 / CW2, 2026-08-07, VANTAGE: DISK): composed "
    "and executed OUT-OF-PROCESS against `server/spawn/cage.js` and `config/spawn-profiles.yaml` "
    "as they sat on disk -- `composeSeatCage` + `specToBwrapFlags` DRIVEN (never the YAML read in "
    "place of the emitter), the flags handed to `bwrap.buildBwrapArgv`, and a REAL write from a "
    "producer cage plus a REAL read from a DISTINCT successor cage attempted per row; `os.access` "
    "never consulted; grants NONE (the ordinary-seat case). Record `cage-subtree-map.csv` "
    "sha256:c36a11b409238eb7, asserting composed-flag digests producer 1c8ef7c433259527, successor "
    "0507cfef2345526e, templates 21. THIS IS A SNAPSHOT, NOT A LIVE SPEC: if `cage.SeatBinds` has "
    "changed since, this refusal is STALE and not current -- re-run 7.466's driver before trusting "
    "it. It is also INCOMPLETE: there is no `branches/<b>/coordination/` row, so a token there is "
    "`undecided` and refused rather than admitted.")

# subtree -> (writable-by-producer, readable-by-peer, deciding-entry), transcribed from CW2's
# record. Keys are patterns over a RUN-PACKAGE-RELATIVE token; `<x>` matches one path segment. The
# record's sixth row is its NEGATIVE CONTROL (`{goalDir}/runs/run-decoy/`) and is deliberately not
# transcribed: it is a control on the instrument, not a subtree any package token can name.
_CAGE_SUBTREES = {
    "outputs/":              (False, True,  "W ro-bind:{runDir} | R ro-bind:{runDir}"),
    "branches/<b>/outputs/": (False, True,  "W ro-bind:{runDir} | R ro-bind:{runDir}"),
    "seats/<self>/":         (True,  False, "W bind:{seatDir} | R tmpfs:{runDir}/seats"),
    "coordination/":         (True,  True,  "W bind:{runDir}/coordination | "
                                            "R bind:{runDir}/coordination"),
    "{runDir} root":         (False, True,  "W ro-bind:{runDir} | R ro-bind:{runDir}"),
}


def _cage_key_pattern(key):
    """A cage-map key as a regex over a token. `<x>` matches exactly one path segment."""
    if key == "{runDir} root":
        return re.compile(r"[^/]+\Z")
    parts = [r"[^/]+" if re.fullmatch(r"<[^>]+>", p) else re.escape(p)
             for p in key.rstrip("/").split("/")]
    return re.compile("/".join(parts) + "/")


def cage_subtree_of(token):
    """The cage-map subtree covering `token`, longest key wins; None when NO row covers it.

    None is not "no restriction" — it is the F1 shape, and its caller refuses on it."""
    hits = [k for k in _CAGE_SUBTREES if _cage_key_pattern(k).match(token)]
    return max(hits, key=len) if hits else None


def token_admissible(token, successor_reads_verdict):
    """(verdict, reason) for ONE declared-output token. THE RULE, as code.

    `token` is run-package-relative; `successor_reads_verdict` is that row's discriminator — `yes`,
    `no`, or anything else, which is treated as undecided. An undecided operand is CARRIED THROUGH,
    never past: this function never picks a side on an upstream absence, because an unmapped
    subtree that defaulted to admissible would admit exactly the write the cage will refuse.

    ⚠ THE DISCRIMINATOR IS CONSULTED ONLY WHERE IT DECIDES, AND THAT ORDER IS THE RULING, NOT AN
    OPTIMISATION (run `decisions.md`
    `#p-take-b-evaluate-the-discriminator-only-where-it-DECIDES-and-MOVE-CW3s-function-so-ONE-reading-survives`).
    The formula is `writable AND (no successor reads it OR readable)`. Where `readable` is true the
    parenthesis is true for EVERY discriminator value, unknown included — so testing the
    discriminator's VALIDITY first computes an artifact of statement order rather than the rule,
    and it refused 2 of the 11 tokens task 7.470 migrates TO. The 8-row yes/no truth table is
    UNCHANGED by this order; only undecided inputs move, and only where the subtree already
    decides. `undecided` still refuses wherever the discriminator genuinely decides — an own-seat
    token with an undecidable discriminator is refused, exactly as before."""
    subtree = cage_subtree_of(token)
    if subtree is None:
        return (_UNDECIDED,
                "undecided: no cage-map row covers `%s`, and an unmapped subtree NEVER defaults to "
                "admissible -- the missing row is task 7.466's to measure from inside a composed "
                "cage" % token)
    writable, readable, entry = _CAGE_SUBTREES[subtree]
    if not writable:
        return (_INADMISSIBLE,
                "producer-cannot-write: subtree `%s` is not writable in the producing seat's "
                "composed cage (deciding entry: %s)" % (subtree, entry))
    if readable:
        return (_ADMISSIBLE,
                "admissible: subtree `%s` is writable in the producer's cage AND readable from a "
                "successor's, so no value of the successor-read discriminator can change this "
                "(deciding entry: %s)" % (subtree, entry))
    sr = str(successor_reads_verdict).strip().lower()
    if sr not in ("yes", "no"):
        return (_UNDECIDED,
                "undecided: subtree `%s` is writable by the producer but NOT readable from a "
                "successor's cage, so the verdict turns on whether a successor reads `%s` -- and "
                "that discriminator is `%s`, not yes/no. Here it genuinely decides, so it is "
                "carried through rather than resolved (deciding entry: %s)"
                % (subtree, token, successor_reads_verdict, entry))
    if sr == "yes":
        return (_INADMISSIBLE,
                "successor-cannot-read: subtree `%s` is writable by the producer but not readable "
                "from a successor's composed cage, and this row IS read by a successor (deciding "
                "entry: %s)" % (subtree, entry))
    return (_ADMISSIBLE,
            "admissible: subtree `%s` is writable in the producer's cage and no successor reads "
            "this row (deciding entry: %s)" % (subtree, entry))


def successor_reads(coord, seat, after):
    """`yes` / `no` / `undecided` — does any row of this package read `seat`'s declared output?

    Computed from `after` alone, which is what makes it answerable BEFORE the row runs. A row
    declares its inputs indirectly, as "the validated output of every predecessor its `after` cell
    names", so a successor naming this seat IS a read of this seat's declared output.

    ⚠ THE ALTERNATE ARM RETURNS `undecided`, AND THAT DIVERGES FROM TASK 7.465's CENSUS ON TWO
    FIXTURE ROWS — deliberately, in the fail-closed direction, and the leader ruled the divergence
    correct rather than in need of reconciliation (run `decisions.md`
    `#p-the-after-parser-divergence-needs-NO-settlement-because-each-consumers-SAFE-DIRECTION-is-set-by-its-ROLE`).
    An OR-alternate member (`a|b`) is `unsupported` to `parse_after_member`, which yields
    `name=None`: this reader cannot see whose name is inside it. Splitting it here to find out
    would be a SECOND decomposition of the after-member grammar — the exact defect task 7.424
    collapsed into one site. A CENSUS' safe direction is to keep the row in scope (`yes`, a
    redundant check); a REFUSAL's safe direction is the opposite, because undecided can only
    OVER-refuse. The two consumers therefore disagree BY ROLE, and neither is waiting on the open
    question of which `after` parser is authoritative.

    ⚠ THE UNDECIDABILITY IS BOUNDED BY A CONTAINMENT TEST, AND THE BOUND IS SOUND WITHOUT PARSING
    ANYTHING. An alternate poisons only the seats whose NAME OCCURS IN ITS RAW TEXT. This is not a
    reading of the grammar and makes no claim about it: it rests only on the fact that a member
    which names `seat` must contain `seat`'s characters, whatever the grammar turns out to be. So
    a false NEGATIVE is impossible (a member that truly names the seat always contains it), and a
    false POSITIVE — a name that occurs without being named, e.g. `x-terminal-2|y` for `terminal`
    — resolves to `undecided`, which refuses. Both error directions therefore stay on the safe
    side. Without this bound a single unrelated alternate anywhere in the package makes EVERY
    unnamed seat undecided, which refused 3 of the 11 tokens task 7.470 migrates TO — a check
    refusing the migration it exists to enable.

    `undecided` is returned only where it could still CHANGE the answer: a supported member naming
    this seat settles it `yes` regardless of any alternate elsewhere."""
    undecidable = False
    for members in after.values():
        for member in members:
            name, _key, _value, unsupported = coord.after_member_parts(member)
            if unsupported:
                if seat in str(member):
                    undecidable = True
            elif name == seat:
                return "yes"
    return "undecided" if undecidable else "no"


# The caged-ness predicate is the DAEMON'S OWN, asked of the daemon's own config loader rather
# than reproduced here. `spawn.js#composeCageFor` returns null — no cage — for exactly
# `!template || template.length === 0`, where `template` is the RESOLVED profile's
# `sandbox.SeatBinds`. Two facts make a Python re-read of the YAML wrong rather than merely
# redundant: the top-level `cage:` block is merged into every profile's sandbox by
# `launch-profiles/profiles.js`, so the answer is not visible in a profile's own stanza at all;
# and a second parse would be free to disagree with the emitter about whether a seat is caged,
# which is the two-readers shape this file is bounded against. `node` is not a new dependency on
# this path — the enqueue door (`IGNITE_BIN`) is itself a node program.
_CAGE_PROBE_JS = (
    "const {loadConfig} = require(process.argv[1]);\n"
    "const prof = (loadConfig(process.argv[2]).profiles || {})[process.argv[3]];\n"
    "if (!prof) { console.log('unknown'); process.exit(0); }\n"
    "const t = prof.sandbox && prof.sandbox.SeatBinds;\n"
    "console.log(Array.isArray(t) && t.length ? 'caged' : 'uncaged');\n")

_IGNITE_ROOT = Path(__file__).resolve().parent.parent
_CAGE_LOADER_JS = _IGNITE_ROOT / "server" / "spawn" / "config.js"
_CAGE_CONFIG_YAML = _IGNITE_ROOT / "config" / "spawn-profiles.yaml"
_CAGED_CACHE = {}


def profile_launches_caged(profile, config=None):
    """True / False / None — would a row launched under `profile` be CAGED? None = UNDECIDABLE.

    None is returned for an unknown profile, an unreadable config, an absent `node`, or a probe
    that does not answer in time. **None NEVER refuses and never admits by default**: task 7.469's
    F1 arm forbids defaulting an undecidable caged-ness in either direction, so the caller records
    it as a NAMED caveat and leaves the row alone. A silent skip here would disarm the whole check
    on one typo'd profile name, so the caveat names the profile it could not resolve.

    `config` overrides the config file, and exists for ONE reason: every profile in the committed
    config carries the shared `cage:` block, so the UNCAGED verdict is unreachable against it. A
    check that could never observe `False` would leave this predicate's scoping arm — the arm the
    whole §2.4 deferral rests on — asserted rather than driven. The override drives the SAME
    loader against a fixture config; it never substitutes a second reading."""
    key = (profile, str(config or _CAGE_CONFIG_YAML))
    if key in _CAGED_CACHE:
        return _CAGED_CACHE[key]
    verdict = None
    try:
        p = subprocess.run(["node", "-e", _CAGE_PROBE_JS, str(_CAGE_LOADER_JS),
                            str(config or _CAGE_CONFIG_YAML), str(profile)],
                           capture_output=True, text=True, timeout=30)
        answer = ((p.stdout or "").strip().splitlines() or [""])[-1]
        if p.returncode == 0 and answer in ("caged", "uncaged"):
            verdict = answer == "caged"
    except (OSError, subprocess.SubprocessError):
        verdict = None
    _CAGED_CACHE[key] = verdict
    return verdict


def admission_scope_caveat(profile, caged):
    """The one line STEP 4a says about ITSELF on every pass, whichever way it went.

    A check whose absence is silent is indistinguishable from a check that ran and found nothing —
    and this one is absent on two of its three verdicts by design. So the scope is reported, never
    inferred from an empty `failed` list."""
    if caged is True:
        return ("STEP 4a RAN: profile `%s` resolves to a composed seat cage, so every candidate "
                "above had its OWN declared-output tokens admitted against task 7.466's MEASURED "
                "cage map (`cage-subtree-map.csv` sha256:c36a11b409238eb7, VANTAGE: DISK). That "
                "map is a SNAPSHOT: a `cage.SeatBinds` change since 2026-08-07 makes these "
                "verdicts stale while they still read confidently." % profile)
    if caged is False:
        return ("STEP 4a DID NOT RUN: profile `%s` resolves to NO seat cage, and an uncaged row is "
                "deliberately not refused (milestone-task-dag §2.4, arm 2 — refusing it would "
                "convert a ruled deferral into a forced 251-token migration). Nothing above was "
                "checked for declared-output admissibility." % profile)
    return ("⚠ STEP 4a COULD NOT RUN: caged-ness is UNDECIDABLE for profile `%s` — an unknown "
            "profile, an unreadable `config/spawn-profiles.yaml`, or no `node`. It defaulted "
            "NEITHER way (task 7.469 F1): nothing was refused and nothing was cleared. Every row "
            "above is UNCHECKED for declared-output admissibility." % profile)


def declared_output_admission(coord, pkg, seat, after, caged):
    """`(bad, reason)` refusing `seat`'s OWN declared-output tokens, or None to admit.

    `caged` is `profile_launches_caged`'s verdict: **only True refuses.** False is the ruled §2.4
    scope (an uncaged row is not refused) and None is undecidable, which defaults neither way.

    The tokens come from `declared_outputs` — the ONE existing reader of the `<io-spec> ## Outputs`
    grammar, of which this is the third caller. A reader authored here instead would be free to
    disagree with the artifact GRADE about what a token means, at a new column, which is `G-301`'s
    shape. Every non-admissible verdict refuses, `undecided` included."""
    if caged is not True:
        return None
    declared, resolvable, missing, _why = declared_outputs(pkg, seat)
    if not declared:
        return None                      # no seat.md, no <io-spec>, or no path-shaped token
    sr = successor_reads(coord, seat, after)
    bad = []
    for tok in list(resolvable) + list(missing):
        verdict, why = token_admissible(tok, sr)
        if verdict != _ADMISSIBLE:
            bad.append({"token": tok, "verdict": verdict, "why": why,
                        "subtree": cage_subtree_of(tok), "successor-reads": sr})
    if not bad:
        return None
    return bad, (
        "DECLARED-OUTPUT TOKEN NOT ADMISSIBLE FOR A CAGED LAUNCH: %s. THE RULE: %s %s %s This "
        "launch was refused BEFORE it was queued, because the seat could not have written the "
        "token once caged: the failure would otherwise have surfaced at the far end as an absent "
        "artifact and been marked against the seat's work rather than against its declaration. An "
        "UNCAGED row is NOT refused; this row's profile resolves to a composed seat cage." % (
            "; ".join("`%s` -- %s" % (b["token"], b["why"]) for b in bad),
            _ADMISSION_RULE, _ADMISSION_HOMES, _CAGE_MAP_PROVENANCE))


def enqueue(coord, pkg, job_id, profile, readiness_result=None, at=None, submit=None,
            dry_run=False):
    """THE enqueue interface. Turn every LAUNCH CANDIDATE into a daemon job seeded with its
    predecessors' declared outputs AND with its own boot prompt.

    7.445: the queue row carries `prompt`, composed by CALLING `coord.boot_prompt` — the one
    composer the hand-launch path already calls. `ticker.launchAgent` reads that key and
    `spawn.ensurePromptFile` writes it to the file the harness gets as stdin; before this it read
    nothing, wrote `''`, and the seat booted with an empty message. A candidate whose prompt cannot
    be composed is REFUSED into `failed` rather than queued promptless.

    Returns `{enqueued: [{seat, job-id, seed}], validated, excluded, failed, caveats}`.

      enqueued   one row per seat that reached the queue, each carrying the job id the door
                 returned. A row is here ONLY with a real id.
      validated  the same rows under `dry_run=True`, where the door validates and writes nothing,
                 so no id exists. A separate key rather than an `enqueued` row with a null id:
                 "validated" and "enqueued" are two different claims about the queue.
      excluded    every ready seat the self-state intersection excluded, with the term and value.
                 Present even when empty.
      failed     every candidate whose enqueue did not happen, with the cause named — a prompt
                 that could not be composed, a missing seed path, or a non-zero return from the
                 door.

    `readiness_result` is STEP 3's output; omit it and it is computed by running STEP 3, which is
    the same code path rather than a second reading. `submit` is `(argv) -> (rc, stdout, stderr)`
    and defaults to running the daemon's door; injecting it is how a caller exercises the interface
    without a daemon. `at` defaults to now."""
    res = readiness_result if readiness_result is not None else readiness(coord, pkg)
    submit = submit or default_submitter
    at = at or iso_utc_now()
    after = coord.taskforce_after(pkg)

    candidates, excluded = launch_candidates(coord, pkg, res["ready"], res["self-marks"])
    seats = seat_prompts(coord, pkg)
    # STEP 4a: ONE resolution per pass — the whole call shares one `profile`, so caged-ness is one
    # boolean for every candidate below, not a per-seat question.
    caged = profile_launches_caged(profile)

    enqueued, validated, failed = [], [], []
    for seat in candidates:
        prompt, perr = seat_boot_prompt(coord, pkg, seats, seat)
        if perr:
            failed.append({"seat": seat, "missing-seed-paths": [], "detail": [],
                           "reason": "PROMPT COMPOSITION FAILED: %s" % perr})
            continue
        seed, missing = seed_for(coord, pkg, seat, after)
        if missing:
            failed.append({"seat": seat, "missing-seed-paths": [m["path"] for m in missing],
                           "detail": missing,
                           "reason": "SEED PATH ABSENT AT ENQUEUE TIME: %s. Enqueuing this launch "
                                     "would schedule a seat that fails on its first read."
                                     % ", ".join(m["path"] for m in missing)})
            continue
        # STEP 4a (7.469): LAST of the pre-queue refusals, deliberately. Every existing refusal
        # reason still fires first, so no candidate that failed before this change fails for a new
        # reason now — only a candidate that WOULD have been queued can be refused here.
        admission = declared_output_admission(coord, pkg, seat, after, caged)
        if admission:
            bad, why = admission
            failed.append({"seat": seat, "missing-seed-paths": [], "detail": bad,
                           "reason": why})
            continue
        argv = _enqueue_argv(job_id, profile, pkg, seat, seed, at, dry_run, prompt)
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
            admission_scope_caveat(profile, caged),
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

# 7.445: A FIXTURE SEAT'S DESCRIPTOR MUST BE DISCOVERABLE, NOT MERELY PRESENT. Two fastpath
# fixtures wrote a bare `fixture seat\n` and relied on `launch_candidates`, which admits a seat on
# its descriptor's EXISTENCE. The enqueue interface now also COMPOSES that seat's boot prompt
# through `coord.discover_workers`, which needs the identity key — so a keyless descriptor is
# refused before the door and those fixtures stopped reaching it.
#
# ⚠ THIS IS WHY IT IS A CONSTANT AND NOT TWO INLINE STRINGS: when it was two, ONE of the two checks
# caught the drift (`check_fastpath_never_raises`, whose `must_reach_guard` arm asserts the door was
# reached) and the OTHER went silently vacuous — `check_fastpath_refuses_traceless_pkg` kept
# printing "reached the door 0 time(s)" in a PASSING line, because it printed the discriminating
# number without asserting it. Both arms then reached the door 0 times and the control measured
# nothing. One constant means the next precondition added to the enqueue path breaks both fixtures
# at once, where at least one check is guaranteed to say so.
FIXTURE_SEAT_MD = "---\nseat: %s\n---\nfixture seat\n"

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


# ---- STEP 5 (MC11 / task 7.453): THE BRANCH ARM ----------------------------------------------
#
# WHAT A NESTED-WORKFLOW ROW IS. A manifest row's reference names a seat-id "or, instead of a
# seat, a nested workflow" (registry `workflow manifest`; workflows call workflows). Both are the
# same SHAPE — a lowercase-kebab id — so nothing in the cell separates them; the two NAMESPACES
# do, and MC9's `classify_manifest_reference` is the one reading of that. THIS FILE CLASSIFIES
# NOTHING: it calls that function, and `check_branch_arm_reaches_the_classifier` asserts at source
# that no second resolution rule exists here.
#
# WHAT WAS BROKEN, MEASURED BEFORE THE FIX. A ready nested row fell straight through STEP 4's
# third self-state term as `no-descriptor` — correctly, there IS no `seats/<workflow>/seat.md` —
# and nothing else looked at it. Its successor then blocked on `<no mark>` forever, because a row
# nobody launches is a row nobody ever marks. `branches/` appeared nowhere in this file.
#
# THE TWO HALVES, AND WHY THEY ARE SEPARATE. Launching (`branch_stage`) and advancing
# (`branch_marks`) are two different acts on two different surfaces, and the parent's advance must
# survive a process that never ran the launch: `branch_marks` derives its answer from the branch's
# OWN trace on disk, so a parent driven by one process and a branch driven by another still agree.
#
# ⚠ RULE 14 HOLDS THROUGH BOTH. No status column, no state file, no marker: the parent row's mark
# is COMPUTED from the branch's terminal rows every pass, exactly as every other mark in this file
# is computed from a check-out record. `check_no_status_column_written` runs the branch arm inside
# its before/after window and hashes BOTH packages' csv headers.
#
# ⚠ WHICH BRANCH BELONGS TO WHICH ROW IS DERIVED, NOT RECORDED. A branch home is `branch-M` by the
# settled numbering rule (MC8) — the name cannot carry the row. Rather than write a provenance
# file (a new artifact in a run-folder shape, which is not this task's to introduce), the mapping
# is derived from what materialization already guarantees: the branch's taskforce rows ARE the
# nested manifest's rows (Rule 13's frozen copy, MC10 criterion 2). So a branch belongs to the row
# whose workflow manifest has that seat set. TWO ROWS NAMING THE SAME WORKFLOW under one parent
# are therefore INDISTINGUISHABLE, and both are REFUSED with the reason named rather than one of
# them guessed — the fail-safe direction, and a stated limit of this arm.
#
# THE CATALOG IS NOT A TRACE SURFACE, so it is deliberately absent from `READS`: that inventory is
# the trace-field audit's subject, and the catalog carries no trace field. The same is already
# true of `coordination/edge-fastpath.json`, which STEP 4b reads and READS does not list.

MATERIALIZE_PATH = HERE.parent / "team-kit" / "materialize-seats.py"

# The settled folder name (`concepts/branch.md`, d-branch-family). Spelled here as the literal this
# file's paths use, and asserted equal to goal_cli's own `BRANCHES_DIR_NAME` by
# `check_branch_dir_matches_the_registry` — so drift makes a check red rather than silent.
BRANCHES_DIR = "branches"

BRANCH_MARKS = ("done", "failed", None)   # the SAME vocabulary `verify` emits. No fourth value.

BRANCH_STAGE_KEYS = ("launched", "existing", "refused", "caveats")


def load_materialize():
    """Import the kit's `materialize-seats.py` as a module. LAZY — called inside the arm, never at
    module import — because it pulls `yaml` and `goal_cli`, and a job that does not use the branch
    arm must not acquire those dependencies to run at all.

    importlib rather than `import`: the filename carries a hyphen."""
    import importlib.util                                        # noqa: PLC0415 — lazy on purpose
    spec = importlib.util.spec_from_file_location("materialize_seats", MATERIALIZE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("materialize_seats", mod)
    spec.loader.exec_module(mod)
    return mod


def nested_rows(coord, pkg, catalog_root, ms=None):
    """`({seat: ManifestReference}, [refused])` — every `taskforce.csv` row whose reference
    classifies as a NESTED WORKFLOW, decided by CALLING MC9's classifier.

    A row that classifies as a `seat`, and a row the classifier REFUSES, are both simply not
    nested rows here — but the refusals are CARRIED rather than dropped: an unresolvable reference
    is exactly the input a launch must never be guessed from, and reporting it is how a reader
    sees the difference between "no nested rows" and "one nobody could read"."""
    ms = ms or load_materialize()
    catalog_root = Path(catalog_root)
    seats_catalog = ms.load_catalogs(catalog_root)[0]
    nested, refused = {}, []
    for seat in coord.taskforce_after(pkg):
        try:
            ref = ms.classify_manifest_reference(seat, catalog_root, seats_catalog)
        except ms.Refuse as r:
            # `reference-unresolvable` is the ORDINARY case for a live run whose seats are not in
            # the catalog, so it is reported and never raised: this arm's question is "is this row
            # a nested workflow", and "it resolves to nothing" answers NO.
            refused.append({"seat": seat, "code": r.code, "message": r.message})
            continue
        if ref.kind == "nested_workflow":
            nested[seat] = ref
    return nested, refused


def manifest_seat_set(ms, manifest_path):
    """The seat ids a workflow manifest declares, as a set. A MEMBERSHIP view over one column —
    the command's own `MANIFEST_SEAT_COLUMN` — and not a second reading of any grammar."""
    with Path(manifest_path).open(encoding="utf-8", newline="") as fh:
        return {(r.get(ms.MANIFEST_SEAT_COLUMN) or "").strip()
                for r in csv.DictReader(fh)
                if (r.get(ms.MANIFEST_SEAT_COLUMN) or "").strip()}


def branch_home_for(coord, ms, pkg, ref):
    """`(home, note)` — the EXISTING branch home under `pkg` that materialized `ref`'s workflow,
    or `(None, note)` when there is none.

    Matched on the frozen copy: the branch's taskforce seat set IS the manifest's (Rule 13). Two
    homes matching is refused with both named, never resolved by picking one."""
    want = manifest_seat_set(ms, ref.source)
    hits = []
    for home in sorted((pkg / BRANCHES_DIR).glob("branch-*")):
        tf = home / "taskforce.csv"
        if not tf.is_file():
            continue
        if set(coord.taskforce_after(home)) == want:
            hits.append(home)
    if not hits:
        return None, "no branch under %s/ carries this workflow's seat set" % BRANCHES_DIR
    if len(hits) > 1:
        return None, ("AMBIGUOUS: %d branch homes carry this workflow's seat set (%s). Nothing is "
                      "launched and nothing is advanced from an ambiguous home."
                      % (len(hits), ", ".join(h.name for h in hits)))
    return hits[0], "branch %s carries this workflow's seat set" % hits[0].name


def terminal_seats(coord, pkg):
    """The rows no other row depends on — the ones whose completion IS the package's completion.

    Predecessor names come off `_seed_predecessors`, which routes through the ONE member parse
    (`coord.after_member_parts`) and handles alternates; this function decomposes nothing."""
    after = coord.taskforce_after(pkg)
    named = {name
             for members in after.values()
             for member in members
             for name, _alt in _seed_predecessors(coord, member)}
    return [seat for seat in after if seat not in named]


def branch_terminal_mark(coord, home):
    """`(mark, detail)` — the branch's completion, DERIVED from its own trace on disk.

    `done` only when every TERMINAL row is `done`, or `skipped` with at least one terminal `done`:
    a guard-excluded terminal took no branch, and waiting on a row that can never run is the
    forever-block `_simple_member_state` already refuses one level down. `failed` as soon as ANY
    row of the branch is `failed` — its successors can never complete, so the branch is dead and
    saying so beats leaving the parent undecided forever. Otherwise `None`: still running.

    ⚠ NO VALUE HERE IS READ FROM A COLUMN. The marks come from `run_stage` over the branch — the
    same check-out-record + declared-outputs pass every other mark in this file comes from."""
    marks = {r["seat"]: r["disposition"] for r in run_stage(coord, home)}
    res = readiness(coord, home, marks=marks)
    skipped = {s["seat"] for s in res["skipped"]}
    terminals = terminal_seats(coord, home)
    detail = {"home": str(home), "terminal-rows": terminals,
              "marks": {s: marks.get(s, NO_MARK) for s in terminals},
              "skipped": sorted(skipped)}
    failed = sorted(s for s, m in marks.items() if m == "failed")
    if failed:
        detail["reason"] = ("%d row(s) of the branch are `failed` (%s) — every row after them can "
                            "never complete, so the branch is dead. The parent does NOT advance."
                            % (len(failed), ", ".join(failed)))
        return "failed", detail
    if not terminals:
        detail["reason"] = ("the branch has NO terminal row — every row is named as somebody's "
                            "predecessor, which is a cycle or an empty taskforce. Nothing is "
                            "derived from it.")
        return None, detail
    unfinished = [s for s in terminals if marks.get(s) != ADVANCES_EDGE and s not in skipped]
    if unfinished:
        detail["reason"] = ("%d terminal row(s) are not `%s`: %s. The parent row does NOT advance."
                            % (len(unfinished), ADVANCES_EDGE,
                               ", ".join("%s=%s" % (s, marks.get(s) or "<no mark>")
                                         for s in unfinished)))
        return None, detail
    if not [s for s in terminals if marks.get(s) == ADVANCES_EDGE]:
        detail["reason"] = ("every terminal row is SKIPPED — the branch took no terminal path at "
                            "all, so there is no completion to derive an advance from. Reported, "
                            "never defaulted to done.")
        return None, detail
    detail["reason"] = ("every terminal row is `%s` or guard-skipped, with at least one `%s` — the "
                        "branch completed." % (ADVANCES_EDGE, ADVANCES_EDGE))
    return ADVANCES_EDGE, detail


def branch_marks(coord, pkg, catalog_root, ms=None):
    """`{nested row: {mark, detail}}` — one entry per nested-workflow row of `pkg`, its mark
    derived from its branch's terminal state. A row with no branch yet gets `None` and says so."""
    ms = ms or load_materialize()
    nested, _refused = nested_rows(coord, pkg, catalog_root, ms)
    out = {}
    for seat, ref in nested.items():
        home, note = branch_home_for(coord, ms, pkg, ref)
        if home is None:
            out[seat] = {"mark": None, "detail": {"home": None, "reason":
                         "no branch to derive an advance from — %s" % note}}
            continue
        mark, detail = branch_terminal_mark(coord, home)
        out[seat] = {"mark": mark, "detail": detail}
    return out


def marks_with_branches(coord, pkg, catalog_root, ms=None):
    """STEP 1-2's marks, with every nested-workflow row's mark REPLACED by its branch's derived
    one. This is what `readiness` must be handed on a package carrying nested rows: without it a
    nested row has no check-out record of its own and reads `<no mark>` forever."""
    marks = {r["seat"]: r["disposition"] for r in run_stage(coord, pkg)}
    for seat, entry in branch_marks(coord, pkg, catalog_root, ms).items():
        marks[seat] = entry["mark"]
    return marks


def _materialize_argv(pkg, ref, catalog_root, bindings, creation_inputs, milestone_id):
    """The materialize command's OWN argv for one branch. Built as an argv list and parsed by that
    command's `build_parser`, so the Namespace `materialize_branch` receives is the command's and
    not a shape this file invented."""
    argv = ["--branch-of", str(pkg), "--workflow", ref.name,
            "--catalog-root", str(catalog_root), "--bindings", str(bindings), "--root"]
    for opt, key in (("--conduct", "conduct"), ("--claude-md", "claude_md"),
                     ("--budget-json", "budget_json")):
        value = (creation_inputs or {}).get(key)
        if value:
            argv += [opt, str(value)]
    if milestone_id:
        argv += ["--milestone-id", milestone_id]
    return argv


def branch_stage(coord, pkg, catalog_root, job_id, profile, bindings, submit=None, at=None,
                 dry_run=False, creation_inputs=None, milestone_id=None, readiness_result=None):
    """Launch every READY nested-workflow row as a branch, and enqueue that branch's ROOTS.

    `{launched, existing, refused, caveats}`:
      launched   one row per branch materialized THIS pass, with its home and the enqueue result
                 for the branch's own ready roots
      existing   a ready nested row that ALREADY has a branch — the idempotence arm. Nothing is
                 materialized twice, and the row says which home it found
      refused    a nested row that was not launched, with the cause named: an ambiguous home, a
                 materialize refusal, or a classifier refusal. NEVER a silent skip
      caveats    the standing bounds a reader needs to not over-read the result

    The branch's roots reach the queue through `enqueue` — THIS wave's one enqueue interface,
    called on the branch package. No second enqueue is written here (G-301's shape)."""
    ms = load_materialize()
    res = readiness_result if readiness_result is not None else readiness(
        coord, pkg, marks=marks_with_branches(coord, pkg, catalog_root, ms))
    nested, classifier_refusals = nested_rows(coord, pkg, catalog_root, ms)

    launched, existing, refused = [], [], []
    for r in classifier_refusals:
        # Carried, never launched — the K1 arm: a row whose reference does not resolve is refused
        # with its code, and a refusal is not an absence.
        #
        # ⚠ `ready` IS ON THE ROW BECAUSE MOST REFUSALS ARE ORDINARY. A live run's seats are not in
        # the catalog the branch arm is pointed at, so nearly every row refuses `reference-
        # unresolvable` and that says nothing. The ones that MATTER are the READY rows: there a
        # refusal is the difference between a launch and no launch. Every refusal stays in the
        # data; the flag is what lets a caller shout about the consequential ones only.
        # A READY row with a descriptor on disk is an ORDINARY SEAT — STEP 4's own third
        # self-state term already tells the two apart, and it is reused here rather than a second
        # rule invented. So the consequential population is: ready, and NOT a seat anybody could
        # launch. Everything else stays in the data and out of the shouting.
        pending = (r["seat"] in res["ready"]
                   and not (pkg / "seats" / r["seat"] / "seat.md").exists())
        refused.append({"seat": r["seat"], "ready": pending,
                        "reason": "classifier refused (%s): %s" % (r["code"], r["message"])})
    # Two ready rows naming ONE workflow cannot be told apart by the derived mapping, so neither
    # is launched. Detected before any materialize runs, so the first one does not win by order.
    by_workflow = {}
    for seat, ref in nested.items():
        by_workflow.setdefault(ref.name, []).append(seat)

    for seat in res["ready"]:
        ref = nested.get(seat)
        if ref is None:
            continue
        siblings = by_workflow[ref.name]
        if len(siblings) > 1:
            refused.append({"seat": seat, "ready": True, "reason":
                            "%d rows of this parent name the SAME workflow `%s` (%s). A branch is "
                            "matched to its row by the manifest's seat set, which cannot tell them "
                            "apart, so NEITHER is launched." % (len(siblings), ref.name,
                                                                ", ".join(siblings))})
            continue
        home, note = branch_home_for(coord, ms, pkg, ref)
        if home is not None:
            existing.append({"seat": seat, "home": str(home), "reason":
                             "already materialized — %s. Nothing was materialized twice." % note})
            continue
        if "AMBIGUOUS" in note:
            refused.append({"seat": seat, "ready": True, "reason": note})
            continue
        argv = _materialize_argv(pkg, ref, catalog_root, bindings, creation_inputs, milestone_id)
        try:
            result = ms.materialize_branch(ms.build_parser().parse_args(argv))
        except (ms.Refuse, ms.CatalogRefusal) as exc:
            code = getattr(exc, "code", "catalog")
            refused.append({"seat": seat, "ready": True, "argv": argv,
                            "reason": "materialize refused (%s): %s" % (code, exc)})
            continue
        home = Path(result["branch"]["home"])
        launched.append({"seat": seat, "workflow": ref.name, "home": str(home),
                         "warnings": result.get("warnings", []),
                         "enqueue": enqueue(coord, home, job_id, profile, at=at, submit=submit,
                                            dry_run=dry_run)})

    return {
        "launched": launched,
        "existing": existing,
        "refused": refused,
        "caveats": [
            "a branch is matched to its row by the frozen-copy property (the branch's taskforce "
            "seat set IS the nested manifest's, Rule 13). Nothing records the mapping, and two "
            "rows naming one workflow are refused rather than guessed.",
            "the parent row's advance is NOT written here. It is derived every pass by "
            "`branch_marks` from the branch's own terminal rows — no status column, anywhere "
            "(Rule 14).",
            "the branch's roots reach the queue through `enqueue`, this wave's ONE enqueue "
            "interface, applied to the branch package. Its own three self-state terms still hold "
            "there: readiness is not launch candidacy.",
            "the check-out fast path (STEP 4b) does NOT fire this arm: its arm file carries a "
            "job-id and a profile and no catalog root or bindings, and extending the arming "
            "mechanism is not this stage's. The arm is reached by `--branch-arm` and by calling "
            "`branch_stage`.",
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
    # 7.425: the guarded rows' predecessor. It checks out `done` and its ONE declared output is a
    # `.json` object — the VALIDATED OUTPUT every guard below is evaluated against.
    "fx-route": "done",
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
    # 7.425 (W2) — one row per shape the GUARD evaluator must get right. The predecessor
    # `fx-route` declares `outputs/route.json` = {"risk": "high", "count": 2, "ok": true}, so every
    # expectation below is computed from THAT object and from the guard's own text, by hand.
    "fx-r-guard-hit":       "fx-route[risk=high]",
    "fx-r-guard-miss":      "fx-route[risk=low]",
    "fx-r-guard-bool":      "fx-route[ok=true]",
    "fx-r-guard-number":    "fx-route[count=2]",
    "fx-r-guard-nofield":   "fx-route[colour=blue]",
    "fx-r-guard-unfinished": "fx-renew[risk=high]",
    "fx-r-malformed-guard": "fx-route[nokey]",
    "fx-r-join-one-taken":  "fx-route[risk=high]|fx-route[risk=low]",
    "fx-r-join-none-taken": "fx-route[risk=mid]|fx-route[risk=low]",
    "fx-r-join-malformed":  "fx-route[risk=a|b]|fx-route",
    "fx-r-skip-propagates": "fx-r-guard-miss",
    "fx-r-block-beats-skip": "fx-route[risk=low],fx-open-sitting",
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
    # 7.425 — WAS blocked-as-one-uninterpreted-name; the guard is now EVALUATED. Its predecessor
    # is `done` and declares `outputs/present.md`, which is not a field surface, so the guard is
    # UNEVALUABLE: blocked, and deliberately NOT skipped.
    "fx-r-conditional":     ("blocked", ["fx-done-outputs-present[state=ok]"]),
    # 7.425 — WAS blocked; both alternates are `done`, so the join is met on whichever ran.
    "fx-r-alternate":       ("ready",   []),
    "fx-r-artifact-strict": ("blocked", ["fx-done-output-missing"]),
    # 7.425 — the guard shapes. For a `skipped` row the second element is its EXCLUDED members.
    "fx-r-guard-hit":       ("ready",   []),
    "fx-r-guard-miss":      ("skipped", ["fx-route[risk=low]"]),
    "fx-r-guard-bool":      ("ready",   []),
    "fx-r-guard-number":    ("ready",   []),
    "fx-r-guard-nofield":   ("blocked", ["fx-route[colour=blue]"]),
    "fx-r-guard-unfinished": ("blocked", ["fx-renew[risk=high]"]),
    "fx-r-malformed-guard": ("blocked", ["fx-route[nokey]"]),
    "fx-r-join-one-taken":  ("ready",   []),
    "fx-r-join-none-taken": ("skipped", ["fx-route[risk=mid]|fx-route[risk=low]"]),
    "fx-r-join-malformed":  ("blocked", ["fx-route[risk=a|b]|fx-route"]),
    "fx-r-skip-propagates": ("skipped", ["fx-r-guard-miss"]),
    "fx-r-block-beats-skip": ("blocked", ["fx-open-sitting"]),
    "fx-route":                ("ready", []),
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
    # 7.425: the guard pass runs inside the window too, so the third verdict is proven DERIVED —
    # a `skipped` mark that reached disk would show up here as a changed header.
    readiness(coord, pkg)
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

READINESS_KEYS = ("ready", "blocked", "skipped", "self-marks", "caveats")  # literal, not derived


def _readiness_verdicts(res):
    """{seat: verdict} from a readiness result, for comparison against the literal table."""
    out = {s: "ready" for s in res["ready"]}
    for b in res["blocked"]:
        out[b["seat"]] = "blocked"
    for s in res["skipped"]:
        out[s["seat"]] = "skipped"
    return out


def _readiness_members(res):
    """{seat: [the members its verdict NAMES]} — the unmet set for a blocked row, the EXCLUDING
    members for a skipped one. One accessor, so the expectation table can carry one column."""
    out = {b["seat"]: list(b["unmet"]) for b in res["blocked"]}
    out.update({s["seat"]: [e["member"] for e in s["excluded-by"]] for s in res["skipped"]})
    return out


def check_readiness_verdicts(coord, pkg):
    """CRITERION 1 + 4 — every fixture row gets the verdict and the UNMET SET the literal
    EXPECT_READY table names. Covers the empty-`after` root (ready) and, as the discriminating
    control, a predecessor marked `failed` (BLOCKED, never ready): treating a terminal mark as
    "finished, therefore satisfied" is the plausible wrong reading and it is checked explicitly."""
    res = readiness(coord, pkg)
    got = _readiness_verdicts(res)
    members = _readiness_members(res)
    bad = []
    for seat, (want_verdict, want_members) in EXPECT_READY.items():
        if seat not in got:
            bad.append("%s: no verdict at all" % seat)
            continue
        if got[seat] != want_verdict:
            bad.append("%s: expected %s, got %s" % (seat, want_verdict, got[seat]))
        elif want_verdict != "ready" and members.get(seat) != want_members:
            bad.append("%s: expected members %s, got %s" % (seat, want_members,
                                                            members.get(seat)))
    extra = sorted(set(got) - set(EXPECT_READY))
    if extra:
        bad.append("rows with no expectation in the table: %s" % extra)
    if bad:
        return False, "criterion 1/4: %d wrong readiness row(s): %s" % (len(bad), "; ".join(bad))
    return True, ("criterion 1/4: all %d rows correct (ready=%d, blocked=%d, skipped=%d), every "
                  "blocked row's unmet set and every skipped row's excluding member(s) match by "
                  "name" % (
                      len(EXPECT_READY),
                      sum(1 for v, _ in EXPECT_READY.values() if v == "ready"),
                      sum(1 for v, _ in EXPECT_READY.values() if v == "blocked"),
                      sum(1 for v, _ in EXPECT_READY.values() if v == "skipped")))


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
    # 7.425: the guarded and alternate tokens are now EVALUATED, so the row that must still survive
    # whole as ONE uninterpreted name is the MALFORMED one — the shape `parse_after_member` hands
    # back bare. It is asserted here in place of the two that used to be, because it is the case
    # the fail-safe direction still owns.
    want = "fx-route[nokey]"
    b = blocked.get("fx-r-malformed-guard")
    if b is None:
        return False, ("criterion 2: fx-r-malformed-guard is NOT blocked — a token that did not "
                       "decompose was resolved to something, which is how a row is readied off a "
                       "predecessor nobody named")
    if b["unmet"] != [want]:
        return False, ("criterion 2: fx-r-malformed-guard unmet is %r, expected exactly [%r]"
                       % (b["unmet"], want))
    if not b["notes"].get(want):
        return False, ("criterion 2: fx-r-malformed-guard carries no note explaining that the "
                       "token is one uninterpreted name — a permanent block with no stated cause")
    return True, ("criterion 2: comma-only split confirmed on 5 cells; the guarded and alternate "
                  "tokens survive the CELL split whole and are then evaluated (7.425), and the "
                  "malformed token blocks its row with a stated cause")


def check_skipped_is_produced_not_merely_named():
    """7.425 CRITERION 1 — the third verdict is PRODUCED, not merely present in a vocabulary.

    ⚠ THIS CHECK IS THE INVERSE OF THE ONE IT REPLACES, ON PURPOSE. Until 7.425,
    `check_no_conditional_evaluator_or_third_verdict` asserted the excluded state's name occurred
    NOWHERE in this file, because nothing could produce it and a named-but-unreachable state reads
    as "this case did not arise" when the truth is "this case cannot arise". The evaluator makes it
    reachable, so the guard against that same confusion inverts: the state must now appear in the
    OUTPUT, on the fixture, and not only in the vocabulary. An empty `skipped` list with the word
    in `VERDICTS` is exactly the shape the old check refused.

    The shape-note helper is still asserted to have ONE call site — it annotates a reason and
    decides nothing — because the malformed-ref arm is the one place a token is still uninterpreted.
    """
    if VERDICTS != ("ready", "blocked", EXCLUDED_STATE):
        return False, ("7.425 criterion 1: VERDICTS is %r, expected exactly ('ready', 'blocked', "
                       "'%s')" % (VERDICTS, EXCLUDED_STATE))
    coord = load_coord()
    tmp = Path(tempfile.mkdtemp(prefix="edge-runner-skipped-"))
    try:
        res = readiness(coord, build_fixture(tmp))
        produced = [r["seat"] for r in res[EXCLUDED_STATE]]
        if not produced:
            return False, ("7.425 criterion 1: the vocabulary carries `%s` but the fixture "
                           "produced ZERO such rows — a verdict that never appears in an output "
                           "is the state this check exists to refuse" % EXCLUDED_STATE)
        for row in res[EXCLUDED_STATE]:
            if not row.get("excluded-by"):
                return False, ("7.425 criterion 1: %s is %s but NAMES no excluding member — an "
                               "unexplained exclusion is a silent branch death"
                               % (row["seat"], EXCLUDED_STATE))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    calls = inspect.getsource(_simple_member_state).count("unresolvable_shape_note(")
    if calls != 1:
        return False, ("7.425 criterion 1: the shape-note helper is called %d time(s) from "
                       "`_simple_member_state`, expected exactly 1" % calls)
    return True, ("7.425 criterion 1: VERDICTS == %r and the fixture PRODUCES %d %s row(s) (%s), "
                  "each naming its excluding member(s)"
                  % (list(VERDICTS), len(produced), EXCLUDED_STATE, ", ".join(sorted(produced))))


# The member-grammar idioms this file must NOT contain, each assembled from fragments so that this
# check's own source is not a hit for the search it performs. They are the CONCRETE idioms of
# `coord.parse_after_member` — its key character class and its bracket strip — plus the two ways a
# hand-rolled decomposition is written. A needle naming the ABSTRACT idea ("guard", "parse") would
# fire on every comment in this file and on the sentence forbidding it.
_GRAMMAR_NEEDLES = {
    "the guarded-member key class": "[^\\" + "[\\]=]",
    "a bracket strip": "sub(r\"\\" + "[[^\\]]*\\]\"",
    "a direct call to the member parser": "parse_after_" + "member(",
}

# The bracket used as a SEPARATOR argument to any string method — `.split("[")`, `.partition("[")`,
# `.rsplit("[")` — which is how a hand-rolled decomposition is written without a regex. `.count(`
# is excluded BY NAME: `member_limbs` counts brackets to REFUSE a bad split, which is the opposite
# act. ⚠ MEASURED, NOT ANTICIPATED: this pattern exists because the first needle set listed
# `.split("[")` alone, and a planted mutant that used `.partition("[")` walked straight past it —
# a blind spot found by mutating the check rather than by reading it.
_BRACKET_SEPARATOR = re.compile(r"\.(?!count\b)\w+\(\"\\?\[\"\)")


def check_no_second_grammar_decomposition():
    """7.425 CRITERION 3 — the member grammar is decomposed by W1's ONE parse site and NOWHERE
    here (C-4 / A-3, import-not-copy).

    Two arms, and both are needed. NEGATIVE: none of `parse_after_member`'s own idioms appears in
    this file, so no second decomposition was written. POSITIVE: the evaluator actually reaches
    coord's reader — an absent needle set would also be satisfied by a file that evaluates no guard
    at all, which is the vacuous pass this arm exists to close.

    ⚠ ITS STATED BOUND, inherited from W1-3's: it detects a decomposition written with these
    idioms. One avoiding all of them — a hand-rolled scanner over the characters — is invisible to
    it. Named here rather than left for a reader to discover."""
    src_lines = Path(__file__).read_text(encoding="utf-8").splitlines()
    mine = set(inspect.getsource(check_no_second_grammar_decomposition).splitlines())
    mine |= set(inspect.getsource(load_coord).splitlines())
    found = []
    for i, line in enumerate(src_lines, 1):
        # PURE COMMENT LINES ARE SKIPPED, and the reason is measured: the comment that DOCUMENTS
        # the separator pattern spells the idiom out, so the check fired on the sentence forbidding
        # it — the search must match the binding VALUE, never its own statement. A comment
        # decomposes nothing, so skipping it removes no coverage.
        if line.lstrip().startswith("#"):
            continue
        if line in mine or "_GRAMMAR_NEEDLES" in line or "_BRACKET_SEPARATOR" in line:
            continue
        for what, needle in _GRAMMAR_NEEDLES.items():
            if needle in line:
                found.append("line %d: %s (%r)" % (i, what, line.strip()[:70]))
        if _BRACKET_SEPARATOR.search(line):
            found.append("line %d: a bracket used as a separator (%r)" % (i, line.strip()[:70]))
    if found:
        return False, ("7.425 criterion 3: a SECOND decomposition of the member grammar is "
                       "present — %s. Route it through W1's site (coord.after_member_parts) "
                       "instead." % "; ".join(found))
    reader = "after_member" + "_parts("
    sites = [name for name, obj in sorted(globals().items())
             if callable(obj) and getattr(obj, "__module__", None) == __name__
             and name != "check_no_second_grammar_decomposition"
             and reader in _safe_source(obj)]
    if not sites:
        return False, ("7.425 criterion 3: NO function in this file reads a member through coord's "
                       "one reader — the needle set would pass vacuously over a file that "
                       "decomposes nothing because it evaluates nothing")
    if "member_limbs" not in sites or "_simple_member_state" not in sites:
        return False, ("7.425 criterion 3: the reader is called from %s, but the two functions "
                       "that MUST read a member through it (`member_limbs`, "
                       "`_simple_member_state`) are not both there" % sites)
    return True, ("7.425 criterion 3: none of the %d member-grammar idioms (nor a bracket used as "
                  "a separator) occurs in this file's %d lines, and the decomposition is read "
                  "through coord's one reader at %d site(s) (%s)"
                  % (len(_GRAMMAR_NEEDLES), len(src_lines), len(sites), ", ".join(sites)))


def _safe_source(obj):
    try:
        return inspect.getsource(obj)
    except (OSError, TypeError):
        return ""


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
    for s in res[EXCLUDED_STATE]:
        if not {"seat", "excluded-by"} <= set(s):
            return False, "schema: a %s row lacks `seat`/`excluded-by`: %r" % (EXCLUDED_STATE,
                                                                                sorted(s))
        for e in s["excluded-by"]:
            if not e.get("member") or not e.get("detail", {}).get("reason"):
                return False, ("schema: %s's exclusion %r names no member or carries no reason — "
                               "an exclusion is auditable or it is folklore" % (s["seat"], e))
    if set(res["self-marks"]) != set(res["ready"]):
        return False, "schema: `self-marks` must cover exactly the ready set"
    return True, ("schema: keys %r; %d ready, %d blocked, %d %s; every blocked row names >=1 unmet "
                  "predecessor and every excluded row names its member and reason"
                  % (list(READINESS_KEYS), len(res["ready"]), len(res["blocked"]),
                     len(res[EXCLUDED_STATE]), EXCLUDED_STATE))


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
    readying a row coord blocks — is red even if it were listed.

    ⚠⚠ 7.425 NARROWED THE COMPARED SET TO BARE-MEMBER ROWS, and the narrowing is the finding, not
    a convenience. A GUARDED row's two answers are computed from two different surfaces by design:
    coord discharges `ref[field=value]` against a LEADER'S RULING in `guard-values.csv`, this stage
    against the predecessor's VALIDATED OUTPUT FIELD (execution-strategy B-2's own refusal clause
    routes a machine-derivable condition here rather than through a ruling). On a guard that is
    unruled but field-satisfied, this stage READIES what coord blocks — the direction
    `p-edge-runner-strictness-is-ONE-DIRECTIONAL` forbids, in a ruling that predates any guard
    evaluator and whose stated subject is the declared-artifact strictness ordering. Comparing
    those rows here would report a defect this task was ordered to create; SILENTLY dropping them
    would hide it. So they are excluded BY THE ROW'S SHAPE, COUNTED, and NAMED in the return, and
    the amendment is asked of the `leader` rather than taken by this file."""
    theirs_rows = coord.ready_seat_rows(_fixture_args(pkg))
    theirs_disp = {r["seat"]: r["disposition"] for r in theirs_rows}
    after = coord.taskforce_after(pkg)
    mine = _readiness_verdicts(readiness(coord, pkg))
    marks = {r["seat"]: r["disposition"] for r in run_stage(coord, pkg)}

    if not theirs_rows:
        return False, ("criterion 7: coord.ready_seat_rows returned ZERO rows for the fixture — "
                       "an empty comparison would agree vacuously")

    def _bare(preds):
        """True when every member is a plain seat name — no guard, no alternate. The one class on
        which the two stages consume the SAME inputs and the ordering ruling still binds."""
        for p in preds:
            _n, key, _v, unsupported = coord.after_member_parts(p)
            if key is not None or unsupported:
                return False
        return True

    guarded_rows = [s for s, preds in after.items() if not _bare(preds)]
    diverged, unsound = [], []
    for seat, preds in after.items():
        if seat in guarded_rows:
            continue
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
    compared = len(after) - len(guarded_rows)
    if compared < 2:
        return False, ("criterion 7: only %d bare-member row(s) remained to compare — a "
                       "comparison this narrow agrees vacuously" % compared)
    return True, ("criterion 7: %d BARE-member rows compared term-by-term against "
                  "coord.ready_seat_rows; agreement on %d, and the %d named divergence %s is "
                  "one-directional and explained by the declared-artifact grade. %d GUARDED row(s) "
                  "were EXCLUDED from the comparison and are named: %s — the two stages evaluate a "
                  "guard against different surfaces (coord: guard-values.csv rulings; this stage: "
                  "the predecessor's validated output), which is reported to the leader against "
                  "`p-edge-runner-strictness-is-ONE-DIRECTIONAL`, not settled here"
                  % (compared, compared - len(diverged), len(diverged),
                     sorted(EXPECTED_DIVERGENCES), len(guarded_rows), sorted(guarded_rows)))


# ---- STEP 3b's checks (task 7.425 / W2) -------------------------------------------------------
#
# Every expectation is PRE-COMPUTED from the fixture's own JSON object and from the guard's text,
# written out by hand below. Not one is read from `evaluate_guard`, from `READY_AFTER`, or from
# `EXPECT_READY` — a check whose expectation comes from the value under test moves with it.

# `fx-route`'s validated output, restated as the literal the checks compare against. It is written
# by `build_fixture` from the same three pairs; stating it twice is deliberate, and the pair is
# asserted equal at the top of `check_guard_admits_and_excludes` so a drift reds instead of
# silently re-basing every guard expectation on whatever the fixture happens to contain.
FX_ROUTE_OUTPUT = {"risk": "high", "count": 2, "ok": True}
FX_ROUTE_ARTIFACT = "outputs/route.json"

# The guarded rows, their guard, and the verdict each MUST reach — computed by hand from the object
# above: `risk` is the string "high"; `ok` is JSON true, which renders `true`; `count` is 2, which
# renders `2`; `colour` is not there at all.
EXPECT_GUARD = {
    "fx-r-guard-hit":        ("satisfied",   "risk",   "high",  "ready"),
    "fx-r-guard-miss":       ("excluded",    "risk",   "low",   EXCLUDED_STATE),
    "fx-r-guard-bool":       ("satisfied",   "ok",     "true",  "ready"),
    "fx-r-guard-number":     ("satisfied",   "count",  "2",     "ready"),
    "fx-r-guard-nofield":    ("unevaluable", "colour", "blue",  "blocked"),
}


def _fixture_readiness(coord, mutate=None):
    """(readiness result, pkg) over a FRESH fixture in its own temp tree, optionally mutated first.

    Every red arm below runs here — on a scratch copy built for that arm — so no arm ever mutates
    the fixture another check is reading (C-3: the red is planted on a copy, never on the artifact
    under test)."""
    tmp = Path(tempfile.mkdtemp(prefix="edge-runner-guard-"))
    try:
        pkg = build_fixture(tmp)
        if mutate is not None:
            mutate(pkg)
        return readiness(coord, pkg), pkg
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_guard_admits_and_excludes(coord, pkg):
    """7.425 CRITERION 1 — a satisfied guard ADMITS and an unsatisfied one yields the excluded
    state; a guard whose field cannot be read is UNEVALUABLE and blocks.

    The three are asserted apart on purpose: collapsing `unevaluable` into the excluded state kills
    a branch because nobody could read its guard, and collapsing it into `satisfied` admits an edge
    nothing evaluated."""
    on_disk = json.loads((pkg / FX_ROUTE_ARTIFACT).read_text(encoding="utf-8"))
    if on_disk != FX_ROUTE_OUTPUT:
        return False, ("7.425 criterion 1: the fixture's validated output is %r but every "
                       "expectation here was computed from %r — re-base the expectations by hand, "
                       "never by reading the artifact" % (on_disk, FX_ROUTE_OUTPUT))
    verdicts = _readiness_verdicts(readiness(coord, pkg))
    bad = []
    cache = {}
    for seat, (want_guard, key, required, want_row) in EXPECT_GUARD.items():
        got_guard, detail = evaluate_guard(pkg, "fx-route", key, required, cache)
        if got_guard != want_guard:
            bad.append("%s: guard %s=%r expected %s, got %s (%s)"
                       % (seat, key, required, want_guard, got_guard, detail["reason"]))
        if verdicts.get(seat) != want_row:
            bad.append("%s: row verdict expected %s, got %s" % (seat, want_row,
                                                                verdicts.get(seat)))
        if want_guard != "unevaluable" and detail["found"] is None:
            bad.append("%s: the guard decided without naming the value it FOUND" % seat)
    if bad:
        return False, "7.425 criterion 1: %d wrong guard outcome(s): %s" % (len(bad),
                                                                             "; ".join(bad))
    return True, ("7.425 criterion 1: %d guards evaluated against `%s` on disk — %d satisfied "
                  "(row ready), %d excluded (row %s), %d unevaluable (row blocked); each names the "
                  "value it found"
                  % (len(EXPECT_GUARD), FX_ROUTE_ARTIFACT,
                     sum(1 for v in EXPECT_GUARD.values() if v[0] == "satisfied"),
                     sum(1 for v in EXPECT_GUARD.values() if v[0] == "excluded"), EXCLUDED_STATE,
                     sum(1 for v in EXPECT_GUARD.values() if v[0] == "unevaluable")))


def check_guard_reads_the_validated_output(coord, pkg):
    """7.425 — F-W2a's arm: the guard is evaluated against THE PREDECESSOR'S VALIDATED OUTPUT and
    against nothing else.

    ⚠ A CHECK THAT ONLY ASSERTED THE RIGHT VERDICTS WOULD BE CONFOUNDED — the fixture's guard
    values and its artifact agree, so a stage that read the guard's own text and ignored the
    artifact entirely would pass it. This one MEASURES AT THE DECISION: it plants the OPPOSITE
    value in a scratch copy of the artifact, changing nothing else, and requires both rows to
    SWAP. A verdict that tracks the artifact's content is read from the artifact's content.

    The second arm removes the artifact instead: with the declared output gone, the predecessor's
    own mark falls to `failed` (STEP 1-2's declared-artifact grade) and the guarded row blocks —
    never admits. Two mutations, one variable each."""
    live = _readiness_verdicts(readiness(coord, pkg))
    if (live.get("fx-r-guard-hit"), live.get("fx-r-guard-miss")) != ("ready", EXCLUDED_STATE):
        return False, ("F-W2a: the unmutated control is already wrong (hit=%s, miss=%s) — a "
                       "mutation result would mean nothing"
                       % (live.get("fx-r-guard-hit"), live.get("fx-r-guard-miss")))

    def flip(scratch):
        doc = json.loads((scratch / FX_ROUTE_ARTIFACT).read_text(encoding="utf-8"))
        doc["risk"] = "low"
        (scratch / FX_ROUTE_ARTIFACT).write_text(json.dumps(doc, indent=2) + "\n")

    flipped, _ = _fixture_readiness(coord, flip)
    got = _readiness_verdicts(flipped)
    if (got.get("fx-r-guard-hit"), got.get("fx-r-guard-miss")) != (EXCLUDED_STATE, "ready"):
        return False, ("F-W2a: the artifact's `risk` was flipped high->low on a scratch copy and "
                       "the rows did NOT swap (hit=%s, miss=%s, expected %s/ready). The verdict is "
                       "not being read from the predecessor's validated output — redesign the read "
                       "point and re-run." % (got.get("fx-r-guard-hit"), got.get("fx-r-guard-miss"),
                                              EXCLUDED_STATE))

    def remove(scratch):
        (scratch / FX_ROUTE_ARTIFACT).unlink()

    gone, _ = _fixture_readiness(coord, remove)
    got2 = _readiness_verdicts(gone)
    if got2.get("fx-r-guard-hit") != "blocked":
        return False, ("F-W2a: with the declared output DELETED on a scratch copy, fx-r-guard-hit "
                       "is %s — expected blocked. A guard must never be satisfied by an output "
                       "that is not there." % got2.get("fx-r-guard-hit"))
    return True, ("F-W2a: flipping `risk` high->low inside %s on a scratch copy SWAPS the two rows "
                  "(ready<->%s), and deleting the artifact blocks the admitting row. The read "
                  "point is the predecessor's validated output"
                  % (FX_ROUTE_ARTIFACT, EXCLUDED_STATE))


def check_alternate_join_whichever_ran(coord, pkg):
    """7.425 CRITERION 2 — a join over `a|b` completes when exactly one alternate ran, and does not
    complete when none did.

    The second half is the DISCRIMINATING CONTROL: a join that completed on any input at all would
    pass the first half alone, and "the join fired" would then say nothing about which branch was
    taken."""
    res = readiness(coord, pkg)
    verdicts = _readiness_verdicts(res)
    if verdicts.get("fx-r-join-one-taken") != "ready":
        return False, ("7.425 criterion 2: a join whose first alternate is satisfied and whose "
                       "second is excluded is %s, expected ready — the join is waiting on the "
                       "branch that was NOT taken" % verdicts.get("fx-r-join-one-taken"))
    if verdicts.get("fx-r-join-none-taken") != EXCLUDED_STATE:
        return False, ("7.425 criterion 2 control: a join whose alternates are BOTH excluded is "
                       "%s, expected %s — a join that completes with no branch taken completes on "
                       "anything" % (verdicts.get("fx-r-join-none-taken"), EXCLUDED_STATE))
    # THE ROW VERDICT IS NOT ENOUGH: a join met because BOTH limbs were met would pass the two
    # assertions above while proving nothing about "whichever ran". The limb states are therefore
    # read at the decision itself.
    marks = {r["seat"]: r["disposition"] for r in run_stage(coord, pkg)}
    member = coord.taskforce_after(pkg)["fx-r-join-one-taken"][0]
    state, detail = member_state(coord, pkg, member,
                                 marks, {r["seat"] for r in res[EXCLUDED_STATE]}, {})
    kinds = [limb["state"] for limb in detail.get("limbs", [])]
    if (state, kinds) != ("met", ["met", "excluded"]):
        return False, ("7.425 criterion 2: the join member is %s with limbs %r, expected met with "
                       "exactly one met limb and one excluded one" % (state, kinds))
    return True, ("7.425 criterion 2: the join over one taken branch is READY, its limbs are %r "
                  "(exactly one ran), and the control join with NO branch taken is %s"
                  % (kinds, EXCLUDED_STATE))


def check_guard_red_arms_fire(coord, pkg):
    """7.425 CRITERION 4 — the three red arms the contract names FIRE, each on the fixture, each
    with the wrong outcome named as what it would have been.

      guard mismatch    the excluded state is reached, and the row is NOT readied
      malformed ref     a bracketed token that did not decompose blocks and is NAMED
      join over one taken branch   the join completes on the taken limb while the other is excluded

    A fourth arm rides here because it is the one a reader assumes rather than checks: BLOCKED
    BEATS the excluded state. A row with one excluded member AND one unfinished member is blocked —
    calling it excluded would kill a branch over an edge nobody has finished evaluating."""
    verdicts = _readiness_verdicts(readiness(coord, pkg))
    arms = [
        ("guard mismatch", "fx-r-guard-miss", EXCLUDED_STATE,
         "an unsatisfied guard would have ADMITTED its row"),
        ("malformed ref", "fx-r-malformed-guard", "blocked",
         "an unparseable guard would have become a satisfied one"),
        ("malformed alternate", "fx-r-join-malformed", "blocked",
         "a join split in the wrong place would have routed on a fragment"),
        ("join over one taken branch", "fx-r-join-one-taken", "ready",
         "the join would have waited on the branch that was not taken"),
        ("blocked beats %s" % EXCLUDED_STATE, "fx-r-block-beats-skip", "blocked",
         "a half-evaluated row would have been declared a dead branch"),
        ("exclusion propagates", "fx-r-skip-propagates", EXCLUDED_STATE,
         "the row after an untaken branch would have blocked forever"),
    ]
    bad = [("%s: %s is %s, expected %s — %s" % (name, seat, verdicts.get(seat), want, harm))
           for name, seat, want, harm in arms if verdicts.get(seat) != want]
    if bad:
        return False, "7.425 criterion 4: %d red arm(s) did NOT fire: %s" % (len(bad),
                                                                             "; ".join(bad))
    return True, ("7.425 criterion 4: all %d red arms fired — %s"
                  % (len(arms), "; ".join("%s -> %s" % (n, verdicts[s]) for n, s, _w, _h in arms)))


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
# nine are `ready` on the `after` term — their `after` cells are empty — and all nine are the
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
    "fx-route":                "done",      # 7.425's guard predecessor — finished, never relaunched
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
    # 7.425: the rows the guard evaluator makes ready. Their `after` member is a GUARDED token, so
    # the seed is the CLEAN predecessor's artifact — the same de-duplication, over a name the raw
    # token does not carry. `fx-r-alternate`'s two limbs declare the same artifact; the join's two
    # limbs name the same predecessor twice.
    "fx-r-guard-hit":      ["outputs/route.json"],
    "fx-r-guard-bool":     ["outputs/route.json"],
    "fx-r-guard-number":   ["outputs/route.json"],
    "fx-r-join-one-taken": ["outputs/route.json"],
    "fx-r-alternate":      ["outputs/present.md"],
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


# ---- STEP 4a's checks (task 7.469 / CW5) ------------------------------------------------------
#
# ⚠ THE ACCEPT ARM IS NOT DECORATION. A refusal that refuses everything is not a refusal, it is an
# outage, and it passes a "does it refuse?" check perfectly. So every arm below moves ONE variable
# against the same fixture and asserts BOTH outcomes: refuse and admit, caged and uncaged.

_FX_CAGED_PROFILE = "claude-opus"     # a REAL profile of the committed config, resolved by the
                                      # daemon's own loader — not a name this file invents


def _fx_declare(pkg, seat, token):
    """Rewrite `seat`'s descriptor so its `<io-spec> ## Outputs` declares exactly `token`.

    The token is NOT created on disk: admissibility is a question about a token's LOCATION, which
    is answerable before the seat has written anything — that is the whole point of refusing at the
    queue instead of grading at the far end."""
    (pkg / "seats" / seat).mkdir(parents=True, exist_ok=True)
    (pkg / "seats" / seat / "seat.md").write_text(
        "---\nseat: %s\n---\n<io-spec id=\"fx-io\" version=\"latest\">\n## Inputs\n\n- nothing.\n\n"
        "## Outputs\n\n- `%s` — the declared artifact.\n</io-spec>\n" % (seat, token),
        encoding="utf-8")


def _fx_own_package(prefix):
    """A FRESH fixture package these checks own outright, plus its temp root to remove.

    Every check below REWRITES a seat's declared output, and the selftest's shared package is read
    by every later check — including ones that seed from this seat as a predecessor. Mutating the
    shared fixture and restoring it afterwards would make each check's green depend on the
    restoration of the one before it. A package of one's own removes the coupling instead of
    managing it."""
    tmp = Path(tempfile.mkdtemp(prefix=prefix))
    return build_fixture(tmp), tmp


def _fx_uncaged_config(tmp):
    """The committed config with its `cage:` block REMOVED, and nothing else changed.

    Every profile in the committed config carries the shared `cage:` block, so `uncaged` is
    unreachable against it and the scoping arm could only ever be asserted. This copy moves exactly
    ONE variable, and the SAME loader reads it — a hand-written stand-in profile would test a
    config this daemon never has."""
    src = _CAGE_CONFIG_YAML.read_text(encoding="utf-8")
    out, skip = [], False
    for line in src.splitlines(True):
        if re.match(r"^cage:", line):
            skip = True
            continue
        if skip and re.match(r"^[A-Za-z_]", line):
            skip = False
        if not skip:
            out.append(line)
    path = Path(tmp) / "no-cage-spawn-profiles.yaml"
    path.write_text("".join(out), encoding="utf-8")
    return path


def check_caged_predicate_is_the_daemons(_coord, _pkg):
    """The caged-ness predicate is DRIVEN through the daemon's own config loader, both ways.

    Inputs are not hand-supplied: one arm reads the committed config, the other the same config
    with only `cage:` removed. A predicate that answered from a fixture dict would prove that the
    fixture dict was read."""
    tmp = Path(tempfile.mkdtemp(prefix="edge-runner-cage-probe-"))
    try:
        live = profile_launches_caged(_FX_CAGED_PROFILE)
        none_cage = profile_launches_caged(_FX_CAGED_PROFILE, _fx_uncaged_config(tmp))
        unknown = profile_launches_caged("fx-no-such-profile-exists")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if live is not True:
        return False, ("the committed config resolves `%s` to %r, not True — either every profile "
                       "lost its cage or the probe is not reaching the loader"
                       % (_FX_CAGED_PROFILE, live))
    if none_cage is not False:
        return False, ("with `cage:` removed the loader still answers %r for `%s` — the UNCAGED "
                       "verdict is unreachable, so the §2.4 scoping arm is asserted, not driven"
                       % (none_cage, _FX_CAGED_PROFILE))
    if unknown is not None:
        return False, ("an unknown profile answered %r, not None — an undecidable caged-ness must "
                       "default NEITHER way (7.469 F1)" % (unknown,))
    return True, ("7.469 scope: the daemon's own loader answers caged=True on the committed config "
                  "and caged=False on the same config with only `cage:` removed (one variable, "
                  "both arms); an unknown profile answers None and defaults neither way")


def check_admission_refuses_and_admits(coord, _pkg):
    """The REFUSE arm and the ACCEPT arm, one variable apart, on one caged fixture seat.

    `outputs/…` is inadmissible (CW2 measured `{runDir}` ro-bind for the producer);
    `coordination/…` is admissible (measured writable by the producer AND readable by a peer).
    Same seat, same profile, same package — only the declared token moves."""
    seat = "fx-r-root"
    pkg, tmp = _fx_own_package("edge-runner-admission-")
    try:
        _fx_declare(pkg, seat, "outputs/refused-by-7469.json")
        submit, _calls = _stub_door()
        bad = enqueue(coord, pkg, FX_JOB_ID, _FX_CAGED_PROFILE, submit=submit)
        refused = [f for f in bad["failed"] if f["seat"] == seat]
        if not refused:
            return False, ("the REFUSE arm did not fire: `%s` declaring `outputs/…` reached the "
                           "queue under caged profile `%s`" % (seat, _FX_CAGED_PROFILE))
        if any(r["seat"] == seat for r in bad["enqueued"]):
            return False, "`%s` was BOTH refused and enqueued" % seat

        _fx_declare(pkg, seat, "coordination/%s-admitted.json" % seat)
        submit, _calls = _stub_door()
        good = enqueue(coord, pkg, FX_JOB_ID, _FX_CAGED_PROFILE, submit=submit)
        if any(f["seat"] == seat for f in good["failed"]):
            why = [f["reason"] for f in good["failed"] if f["seat"] == seat][0]
            return False, ("the ACCEPT arm did not fire: `%s` declaring `coordination/…` was "
                           "REFUSED under the same profile — a check that refuses everything is an "
                           "outage, not a refusal. Reason given: %s" % (seat, why[:200]))
        if not any(r["seat"] == seat for r in good["enqueued"]):
            return False, "`%s` neither refused nor enqueued on the accept arm" % seat
        return True, ("both arms on one seat, one variable: `outputs/refused-by-7469.json` REFUSED "
                      "(%s) and `coordination/%s-admitted.json` ENQUEUED, under the same caged "
                      "profile `%s`" % (refused[0]["detail"][0]["verdict"], seat,
                                        _FX_CAGED_PROFILE))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_admission_carries_the_rule(coord, _pkg):
    """The refusal states the rule WORD FOR WORD, plus the provenance of the map it consulted.

    A refusal that names a violation without stating the rule sends its reader looking for a
    second document; a refusal that cites a MEASURED snapshot without dating it cannot be told
    from a current one."""
    seat = "fx-r-root"
    pkg, tmp = _fx_own_package("edge-runner-rule-text-")
    try:
        _fx_declare(pkg, seat, "outputs/rule-text-probe.json")
        submit, _calls = _stub_door()
        res = enqueue(coord, pkg, FX_JOB_ID, _FX_CAGED_PROFILE, submit=submit)
        hit = [f for f in res["failed"] if f["seat"] == seat]
        if not hit:
            return False, "no refusal to inspect — the refuse arm did not fire"
        text = hit[0]["reason"]
        for needle, what in ((_ADMISSION_RULE, "the rule verbatim"),
                             (_ADMISSION_HOMES, "the admissible-home table"),
                             ("sha256:c36a11b409238eb7", "the cage map's digest"),
                             ("SNAPSHOT, NOT A LIVE SPEC", "the staleness disclosure"),
                             ("`branches/<b>/coordination/` row", "the incompleteness disclosure")):
            if needle not in text:
                return False, "the refusal omits %s" % what
        return True, ("the refusal carries the rule verbatim, the home table, the cage map's "
                      "digest sha256:c36a11b409238eb7, and BOTH disclosures (snapshot + "
                      "incomplete) — %d chars, no second document needed" % len(text))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_admission_is_scoped_to_caged(coord, _pkg):
    """An UNCAGED row is NOT refused, and an UNDECIDABLE one is not refused either.

    This is the arm that makes task 7.470's deferral of 228 tokens a deferral rather than a forced
    251-token migration, so it is driven, never assumed. The caged arm in the same body is the
    control that keeps this from passing because nothing ever refuses."""
    seat = "fx-r-root"
    pkg, tmp = _fx_own_package("edge-runner-scope-")
    try:
        _fx_declare(pkg, seat, "outputs/uncaged-must-pass.json")
        after = coord.taskforce_after(pkg)
        uncaged = profile_launches_caged(_FX_CAGED_PROFILE, _fx_uncaged_config(tmp))
        if uncaged is not False:
            return False, "could not obtain an UNCAGED verdict to test with (%r)" % (uncaged,)
        if declared_output_admission(coord, pkg, seat, after, False):
            return False, ("an UNCAGED row declaring `outputs/…` was REFUSED — that converts a "
                           "ruled deferral into a forced 251-token migration")
        if declared_output_admission(coord, pkg, seat, after, None):
            return False, ("an UNDECIDABLE caged-ness REFUSED — 7.469's F1 arm forbids defaulting "
                           "in either direction")
        if not declared_output_admission(coord, pkg, seat, after, True):
            return False, ("the same seat and token was ADMITTED when caged — the two arms above "
                           "would then pass for the wrong reason")
        submit, _calls = _stub_door()
        res = enqueue(coord, pkg, FX_JOB_ID, "fx-no-such-profile-exists", submit=submit)
        if any(f["seat"] == seat for f in res["failed"]):
            return False, "an unresolvable profile refused a row rather than defaulting neither way"
        if "COULD NOT RUN" not in res["caveats"][-1]:
            return False, ("the undecidable pass did not SAY it could not run — a check whose "
                           "absence is silent reads exactly like one that ran and found nothing")
        return True, ("one token, three caged-ness verdicts: caged=True REFUSES, caged=False does "
                      "NOT (§2.4 arm 2), caged=None does NOT and says so in its caveat")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_admission_undecided_refuses(_coord, _pkg):
    """An UNMAPPED subtree is `undecided`, and `undecided` REFUSES — it is never admitted.

    The cage map carries no `branches/<b>/coordination/` row. A branch-relative token may be
    unwritable in fact, so admitting it on the strength of a missing measurement is the one
    direction that turns a gap into a green (leader bar, 2026-08-07)."""
    unmapped = "branches/branch-1/coordination/nested.json"
    if cage_subtree_of(unmapped) is not None:
        return False, ("`%s` is now MAPPED — this check's premise is gone and its green would be "
                       "vacuous" % unmapped)
    for sr in ("yes", "no", "undecided"):
        verdict, why = token_admissible(unmapped, sr)
        if verdict != _UNDECIDED:
            return False, "unmapped subtree returned %s (%s) at successor-reads=%s" % (verdict,
                                                                                       why, sr)
    if token_admissible("coordination/mapped.json", "no")[0] != _ADMISSIBLE:
        return False, ("the MAPPED sibling `coordination/…` is not admissible either — this check "
                       "would then pass because everything is refused")
    if token_admissible("seats/self/x.json", "undecided")[0] != _UNDECIDED:
        return False, ("an undecided discriminator did not carry through on `seats/<self>/`, where "
                       "it GENUINELY decides — that is the half of the leader bar option (b) does "
                       "not touch")
    return True, ("`branches/branch-1/coordination/nested.json` is unmapped and refuses at all "
                  "three discriminator values, while its MAPPED sibling `coordination/…` is "
                  "admitted — the refusal is a decision, not a stuck red")


def check_admission_truth_table(_coord, _pkg):
    """The rule's 8-row truth table, SPELLED OUT here rather than read back from the code.

    A check whose expectation is computed by the thing under test moves with it and passes any
    change to it. These verdicts are literals. The last three rows are option (b)'s whole subject:
    an undecided discriminator is carried through ONLY where it decides."""
    cases = [
        # (subtree key, discriminator, expected verdict, why this row exists)
        ("coordination/",         "yes",       _ADMISSIBLE,   "writable+readable"),
        ("coordination/",         "no",        _ADMISSIBLE,   "writable+readable"),
        ("seats/<self>/",         "yes",       _INADMISSIBLE, "writable, unreadable, read"),
        ("seats/<self>/",         "no",        _ADMISSIBLE,   "writable, unreadable, unread"),
        ("outputs/",              "yes",       _INADMISSIBLE, "unwritable"),
        ("outputs/",              "no",        _INADMISSIBLE, "unwritable"),
        ("branches/<b>/outputs/", "yes",       _INADMISSIBLE, "unwritable"),
        ("branches/<b>/outputs/", "no",        _INADMISSIBLE, "unwritable"),
        # option (b): the discriminator is consulted only where it can change the answer
        ("coordination/",         "undecided", _ADMISSIBLE,   "(b): readable, so unknown cannot "
                                                              "change the answer"),
        ("outputs/",              "undecided", _INADMISSIBLE, "(b): unwritable decides alone"),
        ("seats/<self>/",         "undecided", _UNDECIDED,    "(b): here it GENUINELY decides"),
    ]
    tokens = {"coordination/": "coordination/p-a.json", "seats/<self>/": "seats/s/a.json",
              "outputs/": "outputs/a.json",
              "branches/<b>/outputs/": "branches/b1/outputs/a.json"}
    for key, sr, want, why in cases:
        tok = tokens[key]
        if cage_subtree_of(tok) != key:
            return False, "`%s` no longer classifies as `%s` — the row is testing nothing" % (tok,
                                                                                              key)
        got, reason = token_admissible(tok, sr)
        if got != want:
            return False, "%s at successor-reads=%s: got %s, want %s (%s) -- %s" % (key, sr, got,
                                                                                    want, why,
                                                                                    reason)
    return True, ("all %d rows of the rule hold as literals: the 8 yes/no rows UNCHANGED by the "
                  "(b) ordering, and the 3 undecided rows carrying through only where the "
                  "discriminator decides" % len(cases))


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
        (pkg / "seats" / "fx-a" / "seat.md").write_text(FIXTURE_SEAT_MD % "fx-a", encoding="utf-8")
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
        # 7.445: ASSERTED, not merely printed. The closing line has always reported this count, and
        # a passing line reading "reached the door 0 time(s)" is what it looked like when the arm
        # went vacuous — both arms at 0, one variable controlling nothing, still green. `fired` is
        # NOT this claim: the hook fires when it RUNS the enqueue, whether or not any candidate
        # survived to the door. Measured on this file, not anticipated.
        if not gcalls:
            return False, ("the trace-carrying arm FIRED but reached the door 0 times, so both "
                           "arms now reach it 0 times and the trace is no longer the variable "
                           "under control. This check would be green while measuring nothing. "
                           "enqueue result: %r" % (green["enqueue"],))
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
        (armed / "seats" / "fx-a" / "seat.md").write_text(FIXTURE_SEAT_MD % "fx-a",
                                                          encoding="utf-8")
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


# ---- STEP 5's checks (MC11 / task 7.453) ------------------------------------------------------
#
# THE FIXTURE IS THE MATERIALIZE COMMAND'S OWN. Building a second catalog here would be a second
# statement of what a catalog is, and the two would drift the day a column moves. `build_fixture`
# from `materialize-seats.py` already ships a catalog carrying the `demo-flow` workflow manifest
# and a run package to home a branch under — so this section BUILDS a parent taskforce over that
# package and nothing else.

FX_BRANCH_JOB_ID = "fx-branch-job"
FX_BRANCH_PROFILE = "fx-branch-profile"

# The parent's three rows, spelled out literally: a real seat, the NESTED-WORKFLOW row, and a row
# that depends on it — the one whose verdict answers "did the parent advance?".
FX_PARENT_ROWS = (("parent-root", ""), ("demo-flow", "parent-root"), ("post-nested", "demo-flow"))
FX_NESTED_ROW = "demo-flow"
FX_PARENT_SUCCESSOR = "post-nested"

# The branch this fixture's `demo-flow` manifest materializes: `beta` is its ONE terminal row.
FX_BRANCH_TERMINAL = "beta"


class _RecordingDoor:
    """The enqueue door as a recorder: every argv kept, a real queue id returned. `enqueue` only
    writes an `enqueued` row when the door names an id, so a launch that reached 'the queue' here
    is a launch this object was actually handed."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv):
        self.calls.append(argv)
        return 0, "accepted: queue id fxq-%d\n" % (len(self.calls),), ""


def _branch_fixture(ms, root):
    """(pkg, fx) — materialize-seats' own catalog + run package, with a parent taskforce carrying a
    nested-workflow row. `parent-root` has checked out clean, so the nested row is READY."""
    fx = ms.build_fixture(Path(root))
    pkg = Path(fx["pkg"])
    with (pkg / "taskforce.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(list(ms.TASKFORCE_HEADER))
        for seat, after in FX_PARENT_ROWS:
            w.writerow(["tf-1", seat, after, "claude", "claude-opus-5", "high", "65", "m1"])
    for seat, _after in FX_PARENT_ROWS:
        if seat == FX_NESTED_ROW:
            continue          # a nested row has NO descriptor — that is the whole point of it
        d = pkg / "seats" / seat
        d.mkdir(parents=True, exist_ok=True)
        d.joinpath("seat.md").write_text(
            "---\nseat: %s\n---\n<io-spec id=\"fx-io\" version=\"latest\">\n## Outputs\n\n- none "
            "declared.\n</io-spec>\n" % seat, encoding="utf-8")
    (pkg / "sessions.csv").write_text(
        "started,ended,seat,session-id,disposition,note\n"
        "2026-01-01 00:00,2026-01-01 01:00,parent-root,s-1,done,\n", encoding="utf-8")
    (pkg / "coordination").mkdir(exist_ok=True)
    return pkg, fx


def _branch_creation_inputs(fx):
    return {"conduct": fx["src_conduct"], "claude_md": fx["src_claude"],
            "budget_json": fx["src_budget"]}


def _finish_branch(home, seats):
    """Write a branch trace where each named seat checked out `done`. Nothing else is touched — the
    parent's own trace stays exactly as the fixture wrote it, so an advance can only come from
    HERE."""
    lines = ["started,ended,seat,session-id,disposition,note"]
    for i, seat in enumerate(seats):
        lines.append("2026-01-02 00:00,2026-01-02 01:00,%s,b-%d,done," % (seat, i))
    (home / "sessions.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_branch_dir_matches_the_registry():
    """`BRANCHES_DIR` is the registry's own folder name, not a second spelling of it."""
    ms = load_materialize()
    if BRANCHES_DIR != ms.BRANCHES_DIR_NAME:
        return False, ("this file spells the branch folder %r while goal_cli spells it %r — one of "
                       "the two writes somewhere nothing reads" % (BRANCHES_DIR,
                                                                   ms.BRANCHES_DIR_NAME))
    return True, "BRANCHES_DIR == goal_cli.BRANCHES_DIR_NAME == %r" % BRANCHES_DIR


def check_branch_arm_launches_a_ready_nested_row(coord):
    """CRITERION 1 — a ready nested row produces a branch under `branches/` and its ROOTS reach the
    queue, read back FROM THE QUEUE (the door's own recorded argv), never from the result dict."""
    ms = load_materialize()
    tmp = Path(tempfile.mkdtemp(prefix="edge-runner-mc11-c1-"))
    try:
        pkg, fx = _branch_fixture(ms, tmp)
        door = _RecordingDoor()
        res = branch_stage(coord, pkg, Path(fx["catalog"]), FX_BRANCH_JOB_ID, FX_BRANCH_PROFILE,
                           fx["b_both"], submit=door,
                           creation_inputs=_branch_creation_inputs(fx))
        if len(res["launched"]) != 1 or res["launched"][0]["seat"] != FX_NESTED_ROW:
            return False, ("criterion 1: the ready nested row did not launch — launched=%s "
                           "refused=%s" % (res["launched"], res["refused"]))
        home = Path(res["launched"][0]["home"])
        if home.parent.name != BRANCHES_DIR or not (home / "taskforce.csv").is_file():
            return False, "criterion 1: %s is not a branch home under %s/" % (home, BRANCHES_DIR)
        # READ BACK FROM THE QUEUE: the branch's root seat is the workdir of a submitted argv.
        roots = [s for s, preds in coord.taskforce_after(home).items() if not preds]
        queued = set()
        for argv in door.calls:
            payload = json.loads(argv[argv.index("--args-json") + 1])
            queued.add(Path(payload["workdir"]).name)
            if not str(payload["workdir"]).startswith(str(home)):
                return False, ("criterion 1: a submitted job's workdir %s is OUTSIDE the branch "
                               "home %s" % (payload["workdir"], home))
        if not roots or set(roots) - queued:
            return False, ("criterion 1: branch roots %s did not all reach the queue (queued: %s)"
                           % (roots, sorted(queued)))
        return True, ("criterion 1: %s -> %s/%s; %d root(s) %s read back off the door's own argv"
                      % (FX_NESTED_ROW, BRANCHES_DIR, home.name, len(roots), sorted(roots)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_branch_advance_is_derived_from_the_branch(coord):
    """CRITERION 2 — the parent row advances ONLY when the branch's terminal rows are done, and the
    verdict is derived from the branch's disk.

    BOTH ARMS, on two fixtures built identically and differing in ONE fact: whether the branch's
    terminal row checked out. If the parent advanced in both, the advance was never derived from
    the branch — which is F-11a, the silent auto-advance this criterion exists to catch."""
    ms = load_materialize()
    verdicts = {}
    for arm, finish in (("complete", True), ("incomplete", False)):
        tmp = Path(tempfile.mkdtemp(prefix="edge-runner-mc11-c2-%s-" % arm))
        try:
            pkg, fx = _branch_fixture(ms, tmp)
            res = branch_stage(coord, pkg, Path(fx["catalog"]), FX_BRANCH_JOB_ID,
                               FX_BRANCH_PROFILE, fx["b_both"], submit=_RecordingDoor(),
                               creation_inputs=_branch_creation_inputs(fx))
            if not res["launched"]:
                return False, "criterion 2: no branch launched for the %s arm (%s)" % (arm, res)
            home = Path(res["launched"][0]["home"])
            branch_seats = list(coord.taskforce_after(home))
            if FX_BRANCH_TERMINAL not in branch_seats:
                return False, ("criterion 2: the fixture branch's terminal row %r is absent from "
                               "%s — the two arms would differ in nothing"
                               % (FX_BRANCH_TERMINAL, branch_seats))
            _finish_branch(home, branch_seats if finish
                           else [s for s in branch_seats if s != FX_BRANCH_TERMINAL])
            marks = marks_with_branches(coord, pkg, Path(fx["catalog"]), ms)
            after = readiness(coord, pkg, marks=marks)
            verdicts[arm] = {
                "mark": marks.get(FX_NESTED_ROW),
                "successor-ready": FX_PARENT_SUCCESSOR in after["ready"],
                "detail": branch_marks(coord, pkg, Path(fx["catalog"]), ms)[FX_NESTED_ROW],
            }
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    ok = (verdicts["complete"]["mark"] == ADVANCES_EDGE
          and verdicts["complete"]["successor-ready"]
          and verdicts["incomplete"]["mark"] is None
          and not verdicts["incomplete"]["successor-ready"])
    if not ok:
        return False, ("criterion 2: the advance is NOT derived from the branch — %s"
                       % json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "detail"}
                                     for k, v in verdicts.items()}))
    return True, ("criterion 2: complete branch -> parent `%s`, %s READY; incomplete branch -> "
                  "parent <no mark>, %s BLOCKED. The control fired."
                  % (ADVANCES_EDGE, FX_PARENT_SUCCESSOR, FX_PARENT_SUCCESSOR))


def check_branch_arm_is_idempotent(coord):
    """A SECOND pass over a package whose nested row already has a branch materializes NOTHING.

    Without this the arm mints `branch-2`, `branch-3`, … on every sweep — and each new branch is
    EMPTY of check-outs, so the parent would never advance again either."""
    ms = load_materialize()
    tmp = Path(tempfile.mkdtemp(prefix="edge-runner-mc11-idem-"))
    try:
        pkg, fx = _branch_fixture(ms, tmp)
        kw = dict(submit=_RecordingDoor(), creation_inputs=_branch_creation_inputs(fx))
        first = branch_stage(coord, pkg, Path(fx["catalog"]), FX_BRANCH_JOB_ID, FX_BRANCH_PROFILE,
                             fx["b_both"], **kw)
        second = branch_stage(coord, pkg, Path(fx["catalog"]), FX_BRANCH_JOB_ID, FX_BRANCH_PROFILE,
                              fx["b_both"], **kw)
        homes = sorted(p.name for p in (pkg / BRANCHES_DIR).glob("branch-*"))
        if len(first["launched"]) != 1 or second["launched"] or len(homes) != 1:
            return False, ("the second pass was not a no-op: launched=%s homes=%s"
                           % (second["launched"], homes))
        if not second["existing"] or second["existing"][0]["seat"] != FX_NESTED_ROW:
            return False, "the second pass did not REPORT the existing branch: %s" % second
        return True, ("a second pass materialized nothing and reported the existing home; %s/ "
                      "holds exactly %s" % (BRANCHES_DIR, homes))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_branch_arm_writes_no_status_column(coord):
    """CRITERION 3 — Rule 14 over BOTH csv sets: the parent's and the branch's. Every csv header
    under both packages is read before and after a full branch pass INCLUDING the advance."""
    ms = load_materialize()
    tmp = Path(tempfile.mkdtemp(prefix="edge-runner-mc11-rule14-"))
    try:
        pkg, fx = _branch_fixture(ms, tmp)
        res = branch_stage(coord, pkg, Path(fx["catalog"]), FX_BRANCH_JOB_ID, FX_BRANCH_PROFILE,
                           fx["b_both"], submit=_RecordingDoor(),
                           creation_inputs=_branch_creation_inputs(fx))
        home = Path(res["launched"][0]["home"])
        _finish_branch(home, list(coord.taskforce_after(home)))

        def headers():
            out = {}
            for p in sorted(pkg.rglob("*.csv")):
                with p.open(encoding="utf-8", errors="replace") as fh:
                    out[str(p.relative_to(pkg))] = fh.readline().rstrip("\n")
            return out

        before = headers()
        marks = marks_with_branches(coord, pkg, Path(fx["catalog"]), ms)
        readiness(coord, pkg, marks=marks)
        branch_marks(coord, pkg, Path(fx["catalog"]), ms)
        after = headers()
        if before != after:
            return False, ("criterion 3: a branch pass CHANGED csv header(s): %s"
                           % [k for k in set(before) | set(after) if before.get(k) != after.get(k)])
        # THE NAME TEST IS SCOPED TO THE REGISTRY Rule 14 GOVERNS — `taskforce.csv`, the file
        # whose run-state must stay derived. `milestones.csv` legitimately carries a milestone
        # `status` column and always has; flagging it would make this check fail on a fixture
        # nobody changed, which is how a real assertion gets deleted for being noisy. The
        # byte-identical header comparison above still covers EVERY csv under both packages, so a
        # column added to any of them anywhere is caught there.
        registries = [n for n in after if Path(n).name == "taskforce.csv"]
        for name in registries:
            for col in after[name].split(","):
                if col.strip().lower() in ("status", "state", "branch-state", "disposition-cache"):
                    return False, "criterion 3: %s carries a status-like column %r" % (name, col)
        both = [k for k in registries if k.startswith(BRANCHES_DIR + "/")]
        if len(registries) < 2 or not both:
            return False, ("criterion 3: no branch csv was in the window at all — the assertion "
                           "would hold vacuously over the parent alone")
        if marks.get(FX_NESTED_ROW) != ADVANCES_EDGE:
            return False, ("criterion 3: the window did not contain an ADVANCE (%s=%s), so a "
                           "column written on advance would not have been seen"
                           % (FX_NESTED_ROW, marks.get(FX_NESTED_ROW)))
        return True, ("criterion 3: %d csv header(s) across BOTH packages byte-identical across a "
                      "pass that DID advance the parent, and neither taskforce.csv (%s) carries a "
                      "status-like column" % (len(after), ", ".join(sorted(registries))))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Assembled from fragments so this check's own source is never a hit for the search it performs.
_CLASSIFIER = "classify_manifest" + "_reference"
_WORKFLOW_GLOB = "/work" + "flows/"
_SEAT_CATALOG = "seats" + ".csv"


def check_branch_arm_reaches_the_classifier():
    """CRITERION 4 — the arm REACHES MC9's classifier rather than re-classifying. Proven at source,
    both directions:

      (a) `nested_rows` CALLS the classifier — its own source carries the call;
      (b) this file contains NO second resolution of what a reference names: neither the workflow-
          manifest glob nor the seat-catalog filename appears anywhere in it.

    (b) alone would pass on a file that never classifies at all, and (a) alone would pass on a file
    that calls the classifier and then overrides it — so both are asserted. The needles are
    positively controlled against `materialize-seats.py`, where they ARE present: a search that
    finds nothing because it was looking for the wrong string reports the same clean 'absent'."""
    here = Path(__file__).read_text(encoding="utf-8")
    if _CLASSIFIER not in _safe_source(nested_rows):
        return False, "criterion 4: `nested_rows` does not call %s" % _CLASSIFIER
    local = [n for n in (_WORKFLOW_GLOB, _SEAT_CATALOG) if n in here]
    if local:
        return False, ("criterion 4: this file resolves a reference ITSELF — %s appears in its "
                       "source, which is a second reading of what MC9's classifier owns" % local)
    control = MATERIALIZE_PATH.read_text(encoding="utf-8")
    missing = [n for n in (_WORKFLOW_GLOB, _SEAT_CATALOG) if n not in control]
    if missing:
        return False, ("criterion 4 CONTROL FAILED: %s is absent from %s too, so the clean result "
                       "above is not evidence of absence" % (missing, MATERIALIZE_PATH.name))
    return True, ("criterion 4: `nested_rows` calls %s and this file carries no second resolution "
                  "rule (both needles positively controlled in %s)"
                  % (_CLASSIFIER, MATERIALIZE_PATH.name))


def check_branch_arm_refuses_an_unresolvable_reference(coord):
    """THE GATE KEY (K1, self) — a nested-workflow row whose reference does not resolve is REFUSED
    with its cause named, never launched and never defaulted to a seat. Driven, not asserted from
    the source: a row naming a workflow that is not in the catalog is added to the parent."""
    ms = load_materialize()
    tmp = Path(tempfile.mkdtemp(prefix="edge-runner-mc11-k1-"))
    try:
        pkg, fx = _branch_fixture(ms, tmp)
        with (pkg / "taskforce.csv").open("a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(["tf-1", "no-such-flow", "parent-root", "claude",
                                     "claude-opus-5", "high", "65", "m1"])
        res = branch_stage(coord, pkg, Path(fx["catalog"]), FX_BRANCH_JOB_ID, FX_BRANCH_PROFILE,
                           fx["b_both"], submit=_RecordingDoor(),
                           creation_inputs=_branch_creation_inputs(fx))
        row = [r for r in res["refused"] if r["seat"] == "no-such-flow"]
        launched = [r["seat"] for r in res["launched"]]
        if not row or "reference-unresolvable" not in row[0]["reason"]:
            return False, "K1: the unresolvable row was not refused with its cause: %s" % res
        if "no-such-flow" in launched:
            return False, "K1: the unresolvable row was LAUNCHED: %s" % launched
        if FX_NESTED_ROW not in launched:
            return False, ("K1: the resolvable row did NOT launch alongside it (%s) — the refusal "
                           "arm would be indistinguishable from a stage that launches nothing"
                           % launched)
        return True, ("K1: `no-such-flow` refused (reference-unresolvable) while `%s` launched in "
                      "the same pass — the accept arm proves the refusal is a decision"
                      % FX_NESTED_ROW)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def build_fixture(root):
    """Write the fixture tree. Identical in content to the on-disk fixture the probe record drives,
    so `--selftest --fixture <DIR>` runs the same assertions against real disk."""
    pkg = root / "run-fx"
    (pkg / "outputs").mkdir(parents=True, exist_ok=True)
    (pkg / "outputs" / "present.md").write_text("fixture artifact — exists on disk\n")
    # 7.425: `fx-route`'s VALIDATED OUTPUT — the object every guard in READY_AFTER is evaluated
    # against. Three scalar kinds on purpose: a string, a number and a bool, because the guard's
    # right-hand side is always TEXT and `_canonical_field` is what makes the comparison decidable.
    (pkg / "outputs" / "route.json").write_text(
        json.dumps({"risk": "high", "count": 2, "ok": True}, indent=2) + "\n")
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
        "s-10,fx-no-iospec,claude,n-10,/fx,,2026-07-30 06:00,2026-07-30 06:10,110,1000,/dev/pts/10,done\n"
        "s-11,fx-route,claude,n-11,/fx,,2026-07-30 06:00,2026-07-30 06:10,111,1000,/dev/pts/11,done\n")
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
    iospec = {"fx-done-output-missing": "outputs/absent.md",
              "fx-route": "outputs/route.json"}
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
        ("readiness-schema", lambda: check_readiness_schema(coord, pkg)),
        ("agrees-with-coord-ready-seats", lambda: check_agrees_with_coord_ready_seats(coord, pkg)),
        # STEP 3b (7.425 / W2) — the guard evaluator and the third verdict
        ("skipped-is-produced", lambda: check_skipped_is_produced_not_merely_named()),
        ("no-second-grammar-decomposition", lambda: check_no_second_grammar_decomposition()),
        ("guard-admits-and-excludes", lambda: check_guard_admits_and_excludes(coord, pkg)),
        ("guard-reads-validated-output", lambda: check_guard_reads_the_validated_output(coord,
                                                                                        pkg)),
        ("alternate-join-whichever-ran", lambda: check_alternate_join_whichever_ran(coord, pkg)),
        ("guard-red-arms-fire", lambda: check_guard_red_arms_fire(coord, pkg)),
        # STEP 4 (M4-10)
        ("enqueue-schema", lambda: check_enqueue_schema(coord, pkg)),
        ("enqueue-excludes-self-marked", lambda: check_enqueue_excludes_self_marked(coord, pkg)),
        ("seed-carries-pred-outputs", lambda: check_seed_carries_predecessor_outputs(coord, pkg)),
        ("root-seat-empty-seed", lambda: check_root_seat_empty_seed(coord, pkg)),
        ("missing-seed-path-fails", lambda: check_missing_seed_path_fails_loudly(coord, pkg)),
        ("single-enqueue-call-site", lambda: check_single_enqueue_call_site()),
        ("enqueue-signature-recorded", lambda: check_enqueue_signature_is_recorded()),
        # STEP 4a (7.469) — the declared-output admission check
        ("admission-truth-table", lambda: check_admission_truth_table(coord, pkg)),
        ("admission-undecided-refuses", lambda: check_admission_undecided_refuses(coord, pkg)),
        ("admission-caged-predicate", lambda: check_caged_predicate_is_the_daemons(coord, pkg)),
        ("admission-refuses-and-admits", lambda: check_admission_refuses_and_admits(coord, pkg)),
        ("admission-carries-the-rule", lambda: check_admission_carries_the_rule(coord, pkg)),
        ("admission-scoped-to-caged", lambda: check_admission_is_scoped_to_caged(coord, pkg)),
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
        # STEP 5 (MC11 / 7.453) — the branch arm. These build their OWN fixture (the materialize
        # command's catalog + package), so they do not read `pkg` and are unaffected by --fixture.
        ("branch-dir-matches-registry", lambda: check_branch_dir_matches_the_registry()),
        ("branch-arm-launches-nested-row",
         lambda: check_branch_arm_launches_a_ready_nested_row(coord)),
        ("branch-advance-is-derived",
         lambda: check_branch_advance_is_derived_from_the_branch(coord)),
        ("branch-arm-is-idempotent", lambda: check_branch_arm_is_idempotent(coord)),
        ("branch-arm-no-status-column", lambda: check_branch_arm_writes_no_status_column(coord)),
        ("branch-arm-reaches-classifier", lambda: check_branch_arm_reaches_the_classifier()),
        ("branch-arm-refuses-unresolvable",
         lambda: check_branch_arm_refuses_an_unresolvable_reference(coord)),
        # STEP 5 / the daemon entry (task C1, owner ruling d-owner-batch1 (1))
        ("goal-resolves-the-live-run", lambda: check_goal_resolves_the_live_run()),
        ("arming-has-one-home", lambda: check_arming_has_exactly_one_home(coord, pkg)),
        ("catalogue-entry-drives-parser", lambda: check_catalogue_entry_drives_this_interface()),
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


# ---- STEP 5 / the daemon entry (task C1) — checks -----------------------------------------------

CATALOGUE = HERE.parent / "config" / "spawn-profiles.yaml"
CATALOGUE_TOOL = "edge-runner"


def _fake_args(**kw):
    """An argparse-Namespace stand-in carrying only the fields `resolve_package` reads. Written
    rather than driving `main()` because these two checks are about the RESOLVERS; the check that
    the real parser accepts the shipped argv drives the real parser, in its own subprocess."""
    ns = argparse.Namespace(package=None, goal=None)
    for k, v in kw.items():
        setattr(ns, k, v)
    return ns


def _goal_fixture(root, states):
    """A goal folder whose runs.csv carries one row per `states` entry — the minimum
    `coord.resolve_live_run` reads. Its run folders exist so a resolved path is a real directory."""
    goal = Path(root)
    goal.mkdir(parents=True, exist_ok=True)
    lines = ["run-id,state"]
    for i, st in enumerate(states, start=1):
        lines.append("run-%d,%s" % (i, st))
        (goal / "runs" / ("run-%d" % i)).mkdir(parents=True, exist_ok=True)
    (goal / "runs.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return goal


def check_goal_resolves_the_live_run():
    """C1 criterion 1: a catalogue argv names a GOAL and the run is resolved at fire time — and the
    resolver REFUSES rather than picks when the register is ambiguous. Both arms, one variable."""
    tmp = Path(tempfile.mkdtemp(prefix="edge-runner-goal-"))
    try:
        one = _goal_fixture(tmp / "g-one", ["closed", "open", "closed"])
        pkg, prov = resolve_package(_fake_args(goal=str(one)))
        if pkg != (one / "runs" / "run-2").resolve():
            return False, "one open row resolved to %s, expected run-2 (%s)" % (pkg, prov)

        two = _goal_fixture(tmp / "g-two", ["open", "open"])
        bad, why = resolve_package(_fake_args(goal=str(two)))
        if bad is not None:
            return False, "TWO open rows resolved to %s instead of refusing" % bad
        if "R9" not in why:
            return False, "the two-open-row refusal does not name R9: %s" % why

        none, why0 = resolve_package(_fake_args(goal=str(_goal_fixture(tmp / "g-none", ["closed"]))))
        if none is not None:
            return False, "a register with no open row resolved to %s instead of refusing" % none

        # The override still wins, and it consults no register: this package has no runs.csv above
        # it at all, which is the shape every check and every on-disk fixture run passes.
        over, oprov = resolve_package(_fake_args(package=str(tmp), goal=str(two)))
        if over != tmp.resolve() or "override" not in oprov:
            return False, "--package did not override --goal (got %s / %s)" % (over, oprov)
        return True, ("one open row -> run-2; TWO open rows REFUSED naming R9; zero open rows "
                      "REFUSED; --package overrode a resolvable --goal. Four arms, one variable.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_arming_has_exactly_one_home(_coord, pkg):
    """C1 criterion 2: STEP 4's `job-id`/`profile` come from the package's OWN arm file — the same
    file the check-out fast path reads — so the two CMP-25 triggers cannot be armed differently.
    The control is the SAME package with the arm removed: it must yield no values at all."""
    p = arm_path(pkg)
    had = p.read_bytes() if p.exists() else None
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"job-id": "fx-armed-job", "profile": "fx-armed-profile",
                                 "dry-run": True}), encoding="utf-8")
        jid, prof, dry, scope = enqueue_arming(pkg, None, None)
        if (jid, prof, dry) != ("fx-armed-job", "fx-armed-profile", True):
            return False, "armed package yielded %r/%r/%r" % (jid, prof, dry)
        if str(p) not in scope:
            return False, "the provenance does not name the arm file: %s" % scope
        # The SAME two values, read by the OTHER trigger, off the same file — this is the property,
        # not the values: if the fast path ever read a different home this comparison goes red.
        other, _ = fastpath_arm(pkg)
        if (other["job-id"], other["profile"]) != (jid, prof):
            return False, "the fast path reads %r but the daemon path reads %r" % (other, (jid, prof))

        p.unlink()
        njid, nprof, ndry, nscope = enqueue_arming(pkg, None, None)
        if (njid, nprof, ndry) != (None, None, None):
            return False, "an UNARMED package still yielded %r/%r/%r" % (njid, nprof, ndry)
        if ARM_FILENAME not in nscope:
            return False, "the unarmed refusal does not name %s: %s" % (ARM_FILENAME, nscope)

        ojid, oprof, _, oprov = enqueue_arming(pkg, "cli-job", "cli-profile")
        if (ojid, oprof) != ("cli-job", "cli-profile") or "override" not in oprov:
            return False, "explicit --job-id/--profile did not override (%r/%r)" % (ojid, oprof)
        return True, ("armed -> %s/%s (dry-run honoured) and BOTH triggers read the one file; the "
                      "same package unarmed -> nothing, naming %s; explicit flags overrode. The "
                      "control fired." % (jid, prof, ARM_FILENAME))
    finally:
        if had is None:
            if p.exists():
                p.unlink()
        else:
            p.write_bytes(had)


def check_catalogue_entry_drives_this_interface():
    """C1 criterion 3: the SHIPPED catalogue entry and this file's own argument surface are bound
    together, so the argv cannot drift under the program it execs.

    The binding is EXERCISED, not read: the entry's own argv is handed to this file's real parser
    in a subprocess, with `--arming-scope` appended so the pass reports and acts on nothing. The
    control is the same argv plus a flag that does not exist — it must exit 2. Without that arm a
    parser that accepted everything would pass this check."""
    if not CATALOGUE.exists():
        return False, "no catalogue at %s" % CATALOGUE
    import yaml                                            # noqa: E402 — checks only, not the job
    entry = (yaml.safe_load(CATALOGUE.read_text(encoding="utf-8")).get("tools") or {}).get(
        CATALOGUE_TOOL)
    if not entry or not isinstance(entry.get("argv"), list):
        return False, "`tools: %s` carries no argv in %s" % (CATALOGUE_TOOL, CATALOGUE)
    argv = [str(a) for a in entry["argv"]]
    if str(Path(__file__).resolve()) not in argv:
        return False, "the entry's argv does not name this file (%s)" % Path(__file__).resolve()
    if "--package" in argv:
        return False, ("the entry pins a RUN via --package. A run number in a catalogue argv is a "
                       "home in waiting — it goes stale at the next run close (7.117/7.188).")
    if "--goal" not in argv:
        return False, "the entry passes no --goal, so it can resolve no run at fire time"
    for flag in ("--job-id", "--profile"):
        if flag in argv:
            return False, ("the entry pins %s, minting a SECOND home for a value whose one home is "
                           "the run's own %s" % (flag, ARM_FILENAME))
    if "--ignite-bin" not in argv:
        return False, ("the entry passes no --ignite-bin. A fire-tool exec inherits the systemd "
                       "--user manager's PATH, which does not carry the ignite binary.")
    bin_path = argv[argv.index("--ignite-bin") + 1]
    if not bin_path.startswith("/"):
        return False, "--ignite-bin is %r, not an absolute path" % bin_path
    accepted = subprocess.run([sys.executable] + argv[1:] + ["--arming-scope"],
                              capture_output=True, text=True)
    if accepted.returncode == 2 or "unrecognized arguments" in accepted.stderr:
        return False, ("this file's parser REFUSED the shipped argv (rc=%d): %s"
                       % (accepted.returncode, accepted.stderr.strip()[:400]))
    refused = subprocess.run([sys.executable] + argv[1:] + ["--arming-scope", "--no-such-flag"],
                             capture_output=True, text=True)
    if refused.returncode != 2:
        return False, ("the control did NOT fire: a bogus flag exited %d, so 'the parser accepted "
                       "the shipped argv' measures nothing" % refused.returncode)
    return True, ("the shipped `tools: %s` argv names this file, pins no run, pins neither job-id "
                  "nor profile, carries an absolute --ignite-bin (%s), and this file's real parser "
                  "accepted it (rc=%d) while rejecting a bogus flag (rc=2)"
                  % (CATALOGUE_TOOL, bin_path, accepted.returncode))


# ---- THE DAEMON ENTRY (task C1) ---------------------------------------------------------------
#
# A `fire-tool` catalogue entry's argv is FIXED at boot and carries no per-fire arguments
# (`ticker.launchFireTool` execs `tool.argv` verbatim). Everything run-specific must therefore be
# RESOLVED by this file at fire time rather than written into that argv — the two functions below
# are the whole of that resolution, and neither invents a value.


def door_at(binary):
    """A submitter for `enqueue` that runs the door from an explicitly named binary — or `None`,
    meaning "use the default door unchanged".

    ⚠ THIS IS AN INJECTION, NOT A SECOND BUILDER, and the distinction is
    `check_single_enqueue_call_site`'s whole subject. `_enqueue_argv` stays the only place an
    enqueue command is BUILT; this substitutes element 0 of the command it built and touches
    nothing else of it. The first draft rebound the module's door-binary constant from `main()`
    instead, and that check went red the same minute: the constant being named outside the one
    builder IS the drift it watches for. The injection seam already existed for the checks; a fired
    job needs it for the same reason, so nothing new was invented here.

    ⚠ AND ITS INNER FUNCTION IS NOT CALLED `submit`, deliberately. That check's third needle is the
    literal submitter call, and a second function whose source carries that text reads to it as a
    second call site. The name here is prose the check cannot mistake for the thing it guards."""
    if not binary:
        return None

    def run_door(argv):
        return default_submitter([binary] + list(argv[1:]))
    return run_door


def resolve_package(args):
    """(Path, provenance) or (None, refusal) — the run package this pass runs against.

    THE TARGET IS RESOLVED, NEVER PINNED. A run number written into a catalogue argv is a HOME IN
    WAITING: it goes stale the moment that run closes, and the entry then fires against a closed
    run's package while the job's own status keeps reading healthy. That is not hypothetical on
    this tree — it is the defect task 7.117 fixed in the `selfheal-watch` entry and task 7.188
    fixed in `selfheal-room`, and swapping in the currently-live run reproduces it at the very next
    close. So the entry names a GOAL and this asks the register which run is open.

    THE REGISTER HAS EXACTLY ONE READER AND IT IS NOT THIS FILE. `coord.resolve_live_run` already
    answers this and already REFUSES rather than guesses on zero or two `state=open` rows (R9's
    one-live-run guarantee, whose enforcement — task 7.77 — is NOT BUILT). A second CSV reader here
    would be a second answer to "which run is live", which is the two-readers shape (G-301) this
    whole file is bounded against. Unlike `selfheal-watch.resolve_package` this takes no `--coord`
    flag: `COORD_PATH` is already a module-level constant here and `load_coord()` is already the
    single import site, so a flag would be a second home for a path this file cannot run without.

    `--package` SURVIVES AS THE EXPLICIT OVERRIDE and wins whenever present — every interactive
    caller, every check, and the on-disk fixture runs pass it, and none of them has a run register.

    Refusal is FAIL-CLOSED and returns no package: a pass that guessed its target on an ambiguous
    register would mark and advance seats in a run nobody named."""
    if args.package:
        return Path(args.package).resolve(), "--package (explicit override; the register is not consulted)"
    if not args.goal:
        return None, ("neither --package nor --goal: this pass has no target and will not choose "
                      "one. A catalogue entry passes --goal, and the live run is resolved from that "
                      "goal's runs.csv at FIRE TIME.")
    goal = Path(args.goal).resolve()
    run_id, detail = load_coord().resolve_live_run(goal)
    if not run_id:
        return None, ("register at %s did not resolve ONE live run: %s" % (goal / "runs.csv", detail))
    return (goal / "runs" / run_id).resolve(), (
        "%s state=open -> %s (resolved live via coord.resolve_live_run, R10)"
        % (goal / "runs.csv", run_id))


def enqueue_arming(pkg, job_id, profile):
    """(job-id, profile, dry-run, provenance) — the values STEP 4 enqueues with, or `(None, None,
    None, why-not)` when this package is not armed.

    ONE HOME FOR THESE TWO VALUES, AND IT IS THE PACKAGE'S OWN ARM FILE. `job-id` and `profile`
    have no defaults anywhere in this file — the catalogue id belongs to whoever armed the queue
    and the daemon requires a profile of every launch-agent job — so a fixed catalogue argv cannot
    carry them without minting a SECOND home beside `coordination/edge-fastpath.json`. A second
    home is a disagreement waiting to happen about the one question C4 cares about: what is this
    armed FOR. Reading the same file the check-out fast path reads means the two triggers of CMP-25
    are armed by one act and can never diverge.

    It also keeps `r-cutover-gated` intact through the registration: a run that carries no arm file
    is not advanced by a daemon fire any more than by a check-out. AN UNARMED PACKAGE IS A NO-OP,
    NOT A FAILURE — the same verdict `check_fastpath_unarmed_is_a_no_op` already pins on the other
    trigger — so the caller reports the scope loudly and exits 0. Exiting non-zero would record a
    `failed` completion on every fire of every unarmed goal, and a job whose normal state is red is
    a job whose red nobody reads.

    Explicit `--job-id`/`--profile` still win, both together: they are how every check and every
    interactive run drives the interface, and neither half alone is a usable arming."""
    if job_id and profile:
        return job_id, profile, None, "--job-id/--profile (explicit override; the arm file is not consulted)"
    arm, scope = fastpath_arm(pkg)
    if arm is None:
        return None, None, None, scope
    return arm["job-id"], arm["profile"], bool(arm.get("dry-run")), scope


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--package", help="the run folder to verify seats in")
    p.add_argument("--goal", default=None,
                   help="goal folder whose runs.csv resolves the live run when --package is "
                        "absent. Names a GOAL, never a run — there is no run number to go stale")
    p.add_argument("--ignite-bin", default=None, dest="ignite_bin",
                   help="absolute path to the `ignite` binary STEP 4's door runs. Omitted, the "
                        "door resolves the bare name on PATH — which works for an interactive "
                        "caller and for NOBODY under a fire-tool exec, since that inherits the "
                        "systemd --user manager's PATH")
    p.add_argument("--seat", action="append", default=[],
                   help="verify only this seat (repeatable); default is every seat on the trace "
                        "or the roster")
    p.add_argument("--json", action="store_true", help="emit the marks as JSON")
    p.add_argument("--readiness", action="store_true",
                   help="STEP 3: after marking, print which seats are ready, which are blocked "
                        "(each naming its unmet predecessors) and which are SKIPPED (each naming "
                        "the guard that excluded it). Readiness is the `after`-set term ONLY — it "
                        "is not launch candidacy. A guard is evaluated against its predecessor's "
                        "VALIDATED OUTPUT; a guard nobody can read leaves its row BLOCKED, never "
                        "skipped")
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
    p.add_argument("--branch-arm", action="store_true", dest="branch_arm",
                   help="STEP 5: launch every READY nested-workflow row as a BRANCH under "
                        "branches/, enqueue that branch's own roots, and report each nested row's "
                        "mark as DERIVED from its branch's terminal rows. Requires --job-id, "
                        "--profile, --catalog-root and --bindings — the classifier needs a catalog "
                        "and the materialize command needs an executor binding, and this stage "
                        "invents neither")
    p.add_argument("--catalog-root", default=None, dest="catalog_root",
                   help="with --branch-arm: the component catalog root a manifest reference is "
                        "classified against (MC9) and materialized from (MC10)")
    p.add_argument("--bindings", default=None,
                   help="with --branch-arm: the JSON bindings file the branch's seats are "
                        "materialized with")
    p.add_argument("--milestone-id", default=None, dest="milestone_id",
                   help="with --branch-arm: passed through to the materialize command")
    p.add_argument("--conduct", default=None,
                   help="with --branch-arm: conduct.md base text for the created branch package; "
                        "omitted, the parent's own is inherited")
    p.add_argument("--claude-md", default=None, dest="claude_md",
                   help="with --branch-arm: run CLAUDE.md base text for the created branch "
                        "package; omitted, the parent's own is inherited")
    p.add_argument("--budget-json", default=None, dest="budget_json",
                   help="with --branch-arm: budget.json for the created branch package; omitted, "
                        "the parent's own is inherited. A PATH, never a value (R-10)")
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
              "(M4-20), the C1 rehearsal (M4-22), and STEP 5's branch arm (MC11 / 7.453), which "
              "applies it to a BRANCH package.")
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
        if args.package or args.goal:
            target, prov = resolve_package(args)
            if target is None:
                print("\nno target resolved: %s" % prov)
            else:
                _, scope = fastpath_arm(target)
                print("\ntarget %s\n  resolved by: %s\n  %s" % (target, prov, scope))
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

    # The door, bound to the binary this invocation names — `None` when the flag is omitted, which
    # leaves every existing caller on today's exact default behaviour.
    door = door_at(args.ignite_bin)

    pkg, provenance = resolve_package(args)
    if pkg is None:
        p.error(provenance)
    # PRINTED, NEVER ONLY DECIDED. A fired pass leaves its stdout as the daemon's completion corpus,
    # and "which run did this act on" is the first question anyone reads that corpus to answer.
    print("target %s\n  resolved by: %s" % (pkg, provenance))

    coord = load_coord()
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
            # 7.425: printed, never only in the JSON. A guard-excluded row that appears in no
            # human-readable output is a branch that died where nobody was told.
            for s in res["skipped"]:
                print("SKIPPED  %-28s %s" % (s["seat"], s["reason"]))
            for c in res["caveats"]:
                print("\ncaveat: %s" % c)
        return 0

    if args.branch_arm:
        missing = [o for o, v in (("--job-id", args.job_id), ("--profile", args.profile),
                                  ("--catalog-root", args.catalog_root),
                                  ("--bindings", args.bindings)) if not v]
        if missing:
            p.error("--branch-arm requires %s: the catalogue id and profile belong to whoever "
                    "armed the queue, and the classifier and the materialize command need a "
                    "catalog root and a bindings file. This stage invents none of them."
                    % ", ".join(missing))
        # The marks a nested row carries are its BRANCH's, so readiness is computed over
        # `marks_with_branches` — the whole point of the stage. A plain `run_stage` here would
        # read every nested row as `<no mark>` and block its successors forever.
        res3 = readiness(coord, pkg, marks=marks_with_branches(coord, pkg, args.catalog_root))
        res = branch_stage(coord, pkg, args.catalog_root, args.job_id, args.profile,
                           args.bindings, submit=door, at=args.at, dry_run=args.dry_run,
                           milestone_id=args.milestone_id, readiness_result=res3,
                           creation_inputs={"conduct": args.conduct,
                                            "claude_md": args.claude_md,
                                            "budget_json": args.budget_json})
        derived = branch_marks(coord, pkg, args.catalog_root)
        if args.json:
            print(json.dumps({"branch-stage": res, "derived-marks": derived}, indent=2))
        else:
            for r in res["launched"]:
                print("BRANCHED  %-28s -> %s" % (r["seat"], r["home"]))
                for q in r["enqueue"]["enqueued"]:
                    print("  QUEUED    %-26s job %s" % (q["seat"], q["job-id"]))
                for q in r["enqueue"]["validated"]:
                    print("  VALIDATED %-26s (dry run — the door wrote nothing)" % q["seat"])
            for r in res["existing"]:
                print("existing   %-28s %s" % (r["seat"], r["reason"]))
            for seat, entry in derived.items():
                print("DERIVED   %-28s mark: %-8s %s"
                      % (seat, entry["mark"] or "<none>", entry["detail"].get("reason", "")))
            for c in res["caveats"]:
                print("\ncaveat: %s" % c)
        # FAIL LOUD: a refusal and a candidate that did not reach the queue both go to stderr.
        failed = [f for r in res["launched"] for f in r["enqueue"]["failed"]]
        loud = [r for r in res["refused"] if r.get("ready")]
        for r in loud:
            print("NOT BRANCHED  %s — %s" % (r["seat"], r["reason"]), file=sys.stderr)
        quiet = len(res["refused"]) - len(loud)
        if quiet:
            # Counted, never listed: a run's own seats are not in this catalog and refuse by the
            # dozen. The count is here so the silence is a MEASURED silence, not an omission.
            print("(%d further row(s) did not classify as a nested workflow and were not ready — "
                  "see `refused` in --json)" % quiet, file=sys.stderr)
        for f in failed:
            print("NOT ENQUEUED  %s — %s" % (f["seat"], f["reason"]), file=sys.stderr)
        return 1 if failed else 0

    if args.enqueue:
        job_id, profile, arm_dry, arming = enqueue_arming(pkg, args.job_id, args.profile)
        print("arming: %s" % arming)
        if job_id is None:
            # STOOD DOWN — not failed, and the exit code says so. `enqueue_arming`'s docstring
            # carries why: a fire against an unarmed run is the no-op `r-cutover-gated` asks for,
            # and recording it as `failed` would make every such fire red.
            print("NOT ENQUEUED (whole pass stood down) — %s" % arming, file=sys.stderr)
            return 0
        full = marks if not args.seat else run_stage(coord, pkg)
        res3 = readiness(coord, pkg, {r["seat"]: r["disposition"] for r in full})
        res = enqueue(coord, pkg, job_id, profile, readiness_result=res3, submit=door,
                      at=args.at, dry_run=args.dry_run or bool(arm_dry))
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
