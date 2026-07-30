#!/usr/bin/env python3
"""edge-runner-job — CMP-25's pass, STAGE 1 ONLY: verify a finished seat's done contract and
mark it `done` or `failed` (task 7.123 / M4-08).

Fired by the ignite daemon as a `fire-tool` job, one job per finished seat. CMP-25 is ONE engine
whose per-edge behaviour is entirely DATA; this file is that engine, and today it carries only the
first of its five steps.

⚠⚠ WHAT THIS FILE IS NOT, YET. CMP-25's pass has five steps: (1) verify the finished seat's done
contract, (2) mark it done or failed loudly, (3) evaluate every downstream row whose `after` names
it, (4) enqueue each ready seat's launch job, (5) exit. **Steps 1 and 2 are here. Steps 3 and 4 are
NOT, and their absence is a build state, not a design.** They are tasks 7.124 (M4-09, readiness over
plain `after` sets) and 7.125 (M4-10, enqueue). A reader who finds no readiness arm here has found
an unbuilt stage, not a missing feature.

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

READS = [
    (SESSIONS, "seat"),          # which rows belong to the seat under verification
    (SESSIONS, "ended"),         # whether it FINISHED — CMP-25's precondition
    (SESSIONS, "disposition"),   # the durable check-out value; `done` alone advances an edge
    (SEAT_MD_OUTPUTS, None),     # its declared outputs, and the artifact paths they name
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
    (pkg / "taskforce.csv").write_text(
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
        + "".join("tf-fx,%s,,claude,claude-opus-5,medium,50,fx\n" % s for s in EXPECT))
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
