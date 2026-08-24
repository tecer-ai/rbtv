import csv
import json
import os
import shlex
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX
    fcntl = None

def atomic_write(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# ---------- package lock (T5) ----------

_LOCK_NOTE = {"shown": False}


def _acquire_flock(fh):
    """Take an exclusive advisory lock on an open handle. Raises on ANY failure — the caller
    then proceeds lockless. Module-level so the self-test can force the fallback path."""
    if fcntl is None:
        raise OSError("fcntl unavailable on this platform")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)


@contextmanager
def coord_lock(base):
    """Serialize one read-modify-write of the package's state files across concurrent coord
    processes (message-ID allocation, roster/cursor/group writes). Two concurrent sends used to
    claim the SAME message number (run-obs §589) and two concurrent roster writes could lose one
    (cli #203) — reads stay lockless.

    Never fatal: a sandboxed seat whose package is read-only (codex EROFS) cannot take the lock,
    so it proceeds WITHOUT it after one note. Yields True when the lock was actually held."""
    fh = None
    try:
        Path(base).mkdir(parents=True, exist_ok=True)
        fh = open(Path(base) / ".lock", "a+", encoding="utf-8")
        _acquire_flock(fh)
    except Exception as exc:  # OSError, PermissionError, anything the platform raises
        if fh is not None:
            try:
                fh.close()
            except OSError:
                pass
            fh = None
        if not _LOCK_NOTE["shown"]:
            _LOCK_NOTE["shown"] = True
            print(f"note: coordination lock unavailable ({exc}) — proceeding lockless",
                  file=sys.stderr)
    try:
        yield fh is not None
    finally:
        if fh is not None:
            try:
                if fcntl is not None:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            fh.close()


# F1 (paneless checkin, owner-ruled 2026-08-17). A daemon-launched seat has NO tmux pane, so its
# roster row carries its OPEN `sessions.csv` session id in the pane cell instead, prefixed. One
# column, two identity kinds — no header change, and the prefix is what keeps them tellable apart.
# ⚠ A raw id handed to `tmux -t` is a silent wrong-target; every tmux wrapper below refuses a token
# this predicate rejects, which is why the guard lives at the wrappers and not at each caller.
SID_PANE_PREFIX = "sid:"


# ---------- run index + session trace (task 7.37; settle ledger R10/R11) ----------
#
# TWO FILES, DIFFERENT JOBS. The KG `run` record as AMENDED (R11, decisions.md#d-run-state-layout)
# — the record's older wording called the per-run trace `runs.csv` and now says so against itself:
#
#   {goal}/runs.csv                    the run INDEX — one row per run (start, finish/ongoing)
#   {goal}/runs/run-{n}/sessions.csv   that run's TRACE — one row per session, in order,
#                                      carrying the resume refs (harness, native session id,
#                                      workdir) task 7.32 resumes from
#
# ONE ROW PER SESSION, opened at launch and completed at close. 7.37's criteria say a launch and a
# close "each produce their own row"; read literally that is TWO rows per session, which would make
# the `ended` column meaningless and contradict the session shape the same task builds for (a
# session lives until CLOSED; the trace is ordered sessions, one per session). What that criterion
# actually defends is that NOBODY INVOKES THE WRITER — and nobody does: both acts below are hooks
# on paths the run already traverses, and neither has a command. Disclosed to leader (log #531).
#
# R10 RESIDUE, carried rather than softened: goal-level state surviving across runs is valid only
# because R9 guarantees one live run per goal, and R9 is now task 7.77 (m4) — NOT BUILT. Until it
# lands, one-live-run is a convention held by hand. So nothing here assumes exclusivity: the index
# is keyed by run-id, and a second concurrent run would add its own row rather than corrupt this.

# `pid`/`pid-starttime`/`tty` are the seat-identity gate's PRE-REGISTERED interface to this writer
# (ignite/server/seat-identity/identity.js: REQUIRED_IDENTITY_COLUMNS + CORROBORATING_COLUMNS).
# The PAIR is the identity — starttime is what defeats pid reuse, so the gate refuses a pid alone
# and explicitly does not accept a degraded mode. `tty` corroborates and never decides.
# `disposition` (dag-09) is APPENDED LAST, and it is the DURABLE home of the value the DAG reads.
# `awaiting-close.json` is the declaration at the moment of truth, but the lifecycle executor
# CLEARS that entry on success — so without a durable copy every successful renewal or completion
# erases the fact the ready arithmetic depends on, and the whole DAG advances exactly once and
# then goes blind. It lives on the SESSION ROW because a check-out IS a session end, and because
# the alternatives are worse: `taskforce.csv` may not carry run state (it is DERIVED), and a new
# coordination file re-imports the two-surfaces hazard this module already names.
# ⚠ AN EMPTY CELL IS `unknown`, NEVER `done` — see `session_disposition` below.
# `disposition-writer` (task 7.155) is APPENDED LAST, after `disposition`, and it holds the writer
# that was VALIDATED for the value beside it — never a second, independently-chosen name. It exists
# because `d-exited-row-closure` gave the `disposition` column a SECOND author: until 7.155 every
# value on this row came from the seat's own check-out or the kit's attest arm, and a reader could
# infer the author from the value. The leader's ruled `done` is indistinguishable from a seat's own
# `done` BY VALUE, and the two mean different things — one is a seat reporting its own work
# finished, the other is a third party's ruling after an investigation. A reader that cannot tell
# them apart cannot audit the ruled ones, so the author is RECORDED rather than inferred.
# ⚠ AN EMPTY CELL HERE MEANS `not recorded`, and it is the reading every row written before this
# column existed carries. It is NEVER read as `seat`: guessing an author is the same class of
# defect as guessing a disposition, one field over.
# `execution` (7.607 E2b, design-lock item 5) is APPENDED LAST, after `disposition-writer`, and it
# carries the DATED EXECUTION STAMP the row was opened under. It is the delimiter the run id used
# to be: with runs extinguished this file is goal-durable and accumulates every execution's
# sessions, so without it a reader cannot tell this boot's rows from the previous one's.
# ⚠ AN EMPTY CELL MEANS `written before the stamp existed`, and it is what every pre-cutover row
# carries (`widen_header` appends the column to a live file without touching a byte of its data).
# It is NEVER read as "the current execution": inheriting the current stamp onto a historical row
# is exactly the cross-execution confusion the stamp exists to end.
# `checkin` (task 7.96) is APPENDED LAST, after `execution`, and it completes the row's TIME
# TRUTH TABLE: `started` is the LAUNCH instant (written by `session_open`, before the seat has
# processed a single token), `checkin` is the seat's LATEST check-in, `ended` is the close. Until
# it existed the middle moment lived ONLY in `workers.md`, which is a PER-SESSION roster row that
# is OVERWRITTEN on every re-check-in — so a seat that checked in four times left one stamp, and
# `sessions.csv`, the durable trace, could not say when any session actually came alive.
# ⚠ IT IS THE LATEST CHECK-IN, NOT THE FIRST, and that is deliberate: a re-check-in (P1
# supersession) is the SAME session waking again, not a new one, so the cell moves rather than the
# row multiplying. The FIRST-boot instant is recoverable as `started`; nothing else is lost.
# ⚠ AN EMPTY CELL MEANS `this session never checked in, or the row predates the column`. It is
# NEVER read as `started` — a launch that opened a row for a seat whose harness then died before
# check-in is exactly the G-11 shape, and inheriting `started` here would erase it.
# ⚠ `model` IS APPENDED AT THE END, NOT PLACED BESIDE `harness` WHERE IT READS BETTER (ruling
# D19, 2026-08-11). `widen_header`'s whole safety argument is append-only, and a fresh file whose
# header ordered `model` mid-list would disagree in ORDER with every legacy file this kit widens —
# which is the run-1/run-2 disagreement that docstring exists to warn about. Column order in a CSV
# carries no meaning; agreement between a born file and a widened one does.
#
# ⚠ THE COLUMN IS NOT NEW ON DISK, ONLY NEW TO THIS CONTRACT. `model` was hand-added to run-2's
# header long ago and never populated (see `widen_header`), so this ADOPTS the spelling already
# there rather than minting a second one — a `model` and a `model-id` in two files would be the
# exact drift the one-schema-owner rule exists to prevent.
#
# WHAT WRITES IT: this kit's own `session_open` (from the roster row's cast), and the daemon's two
# launch doors — `server/spawn/spawn.js` and `engine/attached-execution.js` — which read it off
# the RESOLVED launch profile's own `--model` pin. Both write the model that ACTUALLY launched,
# never the one a seat was cast as: the point of the column is that a divergence between the two
# becomes visible in the seat's own trace instead of only in the system journal (design proposal
# §2 defect 9 — a seat cast `claude-fable-5` ran `claude-sonnet-5` for weeks and nothing said so).
# An EMPTY cell means `this writer did not know the model, or the row predates the column` — never
# "no model".
SESSIONS_COLS = ["session-id", "seat", "harness", "native-session-id", "workdir",
                 "recorded", "started", "ended", "pid", "pid-starttime", "tty", "disposition",
                 "disposition-writer", "execution", "checkin", "model",
                 # D42 (owner, 2026-08-20) — THE LEADER'S HOLD ANCHOR. APPENDED, NEVER INSERTED,
                 # for `widen_header`'s own reason: a freshly-born file and a widened legacy file
                 # must agree on column order.
                 #
                 # ⚠ IT IS NOT A GRANT AND NOT A LATCH, AND D12 IS INTACT. It authorizes nothing,
                 # expires on nothing, suppresses no gate and nothing spends it. It records ONE
                 # fact: that the `leader` INVESTIGATED this non-terminal row and ruled that it
                 # STAYS AS IT IS. Written by `rule-disposition --hold`, RELEASED by the next real
                 # ruling on the same row, and read by exactly one consumer — the goal watcher's
                 # class-A owed scan (`engine/reconcile.js#deriveOwed`), which stops re-waking the
                 # leader every cadence on a row that leader has already ruled on. `ready-seats`
                 # still reports the row's REAL class and it still blocks its successors.
                 "hold-anchor",
                 # D54/D72 (owner, 2026-08-22) — THE `--reopen` DOOR'S RECORDED REASON. APPENDED,
                 # NEVER INSERTED, the same `widen_header` reason `hold-anchor` was appended for.
                 #
                 # ⚠ WRITTEN ONLY ON THE NEW ROW A `--reopen` ADMISSION OPENS, NEVER ON THE `done`
                 # ROW IT RE-OPENS. D54: "the `done` row stands unrewritten" — this column's writer
                 # (the `--reopen` block in `cmd_launch`) finds the seat's freshly-opened OPEN row
                 # by `sessions_open_ids`, not by `sessions_last_ended_rows`, so there is no code
                 # path from this column back to the old ended row's cells.
                 #
                 # ⚠ NOT A GRANT, NOT A LATCH — same D12 shape as `hold-anchor`. It records ONE
                 # fact: the reason the leader gave for re-opening finished work. When D72's
                 # walk-forward finds downstream seats that already ran on the retracted `done`,
                 # this cell also carries a POINTER (" (downstream flagged in messages.md #N)") to
                 # the durable note — see `reopen_downstream_seats` and the `--reopen` block for
                 # why `messages.md` and not a second column is that flag's durable home.
                 "reopen-reason"]
# The one name for that column. Three readers spell it, and a fourth spelling is how a hold
# becomes invisible to the surface meant to show it.
HOLD_ANCHOR_COL = "hold-anchor"
REOPEN_REASON_COL = "reopen-reason"
NATIVE_ID_WAIT = 8.0   # seconds; a boot writes its transcript within ~1s, close re-resolves


# ---- dag-08: THE RECORD DISPOSITION ENUM — the value space the DAG reads --------------------
#
# ⚠⚠ THIS IS NOT `LIFECYCLE_DISPOSITIONS` (defined much further down, beside the executor), AND
# THE TWO SHARE NO VALUE. Two enums live in this file and conflating them is the readiest way to
# break it:
#
#   LIFECYCLE_DISPOSITIONS      `renew|close|revive` — executor ACTIONS, the argv vocabulary of
#                               `lifecycle-exec`. What the detached executor DOES.
#   RECORD_DISPOSITION_WRITER   `done|renew|revive|exited|incomplete|unverified` — the RECORDED
#   (here)                      disposition, the value stored on `awaiting-close.json` AND in the
#                               `disposition` column of `sessions.csv` above (dag-09). What the
#                               DAG READS.
#
# ⚠ IT SITS HERE, BESIDE `SESSIONS_COLS`, AND NOT DOWN IN THE AWAITING-CLOSE SECTION WHERE dag-08
# first put it. It stopped being one record's private enum the moment dag-09 gave it a second
# surface: it is now the value space BOTH writers validate against, and `session_close`'s
# signature reads it at `def` time, several hundred lines above the old home. One enum, one
# definition, above every consumer (PRIN-11).
#
# `LIFECYCLE_INTENT_OF` is the MAP between them: its keys are argv actions, its non-ABSENT values
# are members of THIS enum. The self-test asserts that containment, so widening one enum without
# the other cannot pass silently.
#
# WHAT EACH VALUE MEANS, AND WHO MAY WRITE IT — ONE mapping, because "is this a legal value" and
# "may THIS writer write it" are the same question asked twice. Two constants would be two things
# to widen, and the second one is the one somebody forgets (PRIN-11).
#
# ⚠ EACH VALUE IS A SET OF ADMITTED WRITERS, NOT A SINGLE OWNER (task 7.154). It was a single
# owner until the widening below, and the shape changed because the model had to express a value
# with TWO admitted writers without growing a second constant beside it — which is the exact thing
# the paragraph above bars. A set of one is still a bound of one: `renew`, `revive` and `exited`
# each admit exactly one writer and are no wider than they were.
#
#   done    the SEAT, at its own clean check-out    — the ONLY value that advances a DAG edge
#           ALSO the LEADER, and ONLY on the ruled act below.
#   renew   the SEAT, at a context refresh          — the same seat comes back; no advancement
#   revive  the KIT's revival path (stage 4)        — the same seat comes back; no advancement.
#           It never reaches `awaiting-close.json` at all: a crash had no check-out, which is
#           exactly what `LIFECYCLE_INTENT_OF["revive"] is LIFECYCLE_INTENT_ABSENT` says. Its
#           home is the durable session row (`dag-09`). Listed here because this constant is the
#           VALUE SPACE, not one file's column, and both writers validate against it.
#   exited  the KIT's attest-exit arm (`dag-11`) ONLY, NEVER a seat — and it means, in full:
#           THE HARNESS TERMINATED; WHETHER THE WORK IS DONE IS NOT ESTABLISHED HERE.
#   incomplete  the SEAT, at a check-out it is declaring UNFINISHED (7.676) — its done-contract is
#           UNMET and it is saying so. No advancement (only `done` advances an edge) and no
#           successor (only `renew`/`revive` bring one back): the seat ENDS, and the row it leaves
#           routes to the leader carrying the seat's own reason.
#           ⚠ D5 (2026-08-19) ONCE ALSO PARKED THE UNVERIFIABLE `done` HERE. D32 (2026-08-20)
#           TOOK IT BACK OUT: that state is `unverified` below, and `incomplete` is again the ONE
#           thing it says — the seat declared its own work unfinished.
#   unverified  the SEAT, at a check-out whose `done` the kit could NOT VERIFY (D32, 2026-08-20)
#           — in full: THE SEAT CLAIMED DONE; THE GATE LOOKED AT THE DECLARED `## Outputs`
#           SURFACE AND FOUND NOTHING GRADEABLE. D5's substance is unchanged (refuse the word
#           `done`, record an owed ending, route it, keep it rulable); only the WORD moved.
#           Writer stays `seat`: it is still the occupant's check-out path, and the kit witnessed
#           the undeclarable SURFACE, never the work — which is exactly why it may not say
#           `incomplete` on the seat's behalf.
#           ⚠⚠ WHY A SIXTH VALUE RATHER THAN A REUSE, MEASURED. D5 shipped this state AS
#           `incomplete` for ONE reason: the ruled word `exited` is kit-only-writable and a seat
#           cannot write it. Measured cost, 2026-08-20: `incomplete` then meant two OPPOSITE
#           things on one column — "the seat said unfinished" and "the seat claimed done and the
#           gate could not check" — and 7 rows of genuinely FINISHED work (files on disk,
#           md5-verified by the leader) carried the word for unfinished. THE WORD IS THE
#           DISCRIMINATOR: no reason column, no side file, nothing for a reader to parse. It is
#           the same argument 7.676 makes two paragraphs down — an ending nobody can express is
#           an ending nobody records, and an ending recorded in ANOTHER ending's word is worse,
#           because it reads as recorded.
#           ⚠ IT IS THE SEAT'S ALONE, like `incomplete`: the leader's instrument on such a row is
#           `rule-disposition` (D33(b)), which now admits it as a from-state.
#
# ⚠⚠ WHY A FIFTH VALUE EXISTS AT ALL, MEASURED: until 7.676 THIS ENUM HAD NO HONEST ENDING. A seat
# whose work was unfinished had exactly two words available — `done` (a lie that ADVANCES THE DAG)
# and `renew` (a lie that promises a successor nobody will boot) — so the tool's own vocabulary
# forced a false statement at the one moment the truth was known. Measured 2026-08-09: an
# `elicitator` session flipped to `done` having written no planning folder, no brief and no
# handoff, and NO SURFACE IN THIS SYSTEM COULD TELL IT FROM A SEAT THAT PRODUCED EVERYTHING. The
# fix is a WORD, not a flag: an ending nobody can express is an ending nobody records.
#
# ⚠ IT IS THE SEAT'S ALONE, AND NOT THE LEADER'S. `incomplete` is a seat reporting its OWN work
# unfinished — a fact only the occupant holds. A leader who believes a seat is unfinished has
# `exited`'s investigation path (`d-exited-row-closure`), not a word to put in the seat's mouth;
# admitting the leader here would be the R-6 misgrading the writer bound exists to bar, aimed at
# the one value whose whole purpose is that it was self-declared.
#
# ⚠⚠ WHY THE LEADER MAY WRITE `done`, AND WHAT AUTHORIZES IT: `d-exited-row-closure` (owner,
# ruling A-10, 2026-07-28) — "the leader's act on an `exited` row routed to it by the
# chief-of-staff's sweep: INVESTIGATE whether the row needs relaunching; if the work had in fact
# CONCLUDED, simply switch the row to `done`." `cmd_attest_exit` PRINTS that instruction to the
# leader in its own closing line. Until 7.154 the value space REFUSED it — `leader` was not a
# declared writer at all — so the tool directed the leader to do what its own validator forbade.
# The widening resolves that contradiction in the direction the ruling already settled.
#
# ⚠ THE WIDENING IS EXACTLY ONE PAIR, AND THE NARROWNESS IS THE POINT. `leader` is admitted for
# `done` and for NOTHING ELSE: it may not write `renew` (a seat's own refresh), `revive` (the
# kit's), or `exited` (the kit attesting to a termination it witnessed and the leader did not).
# A leader that could write `exited` would be attesting to a fact it did not witness — the same
# misgrading R-6 bars — and the ruling grants no such thing. Refusal matrix: task 7.154's captures
# under `planning/briefing-designed-work-with-no-seats/captures-7154-disposition-writer-model/`.
#
# ⚠ THIS IS NOT A BYPASS AND IT IS NOT ATTACHED TO A FLAG. It is a value-space change: the leader's
# write is validated by the same boundary as every other, and is refused by name everywhere the
# ruling does not reach. No gate is re-attached to `--force`.
#
# ⚠ NOTHING ANYWHERE MAPS `exited` TO `done`. An implementation that does it "because the work is
# probably fine" has reintroduced F1 — the measured one-shot (seat `oc2`, 2026-07-28) that
# finished its work, exited without checking out, and left every surface reading "still working,
# forever" — with extra steps, and it has done it by ATTESTING TO A FACT IT DID NOT WITNESS,
# which is the misgrading R-6 bars. An `exited` row is routed to a LEADER's judgment; it is never
# resolved by a default. THE WIDENING ABOVE DOES NOT WEAKEN THIS: no code maps one value to the
# other, and the leader's `done` is the OUTCOME OF AN INVESTIGATION it performed, never a
# translation of the `exited` value it started from.
DISPOSITION_WRITER_SEAT = "seat"
DISPOSITION_WRITER_KIT = "kit"
DISPOSITION_WRITER_LEADER = "leader"
RECORD_DISPOSITION_WRITER = {
    "done": frozenset({DISPOSITION_WRITER_SEAT, DISPOSITION_WRITER_LEADER}),
    "renew": frozenset({DISPOSITION_WRITER_SEAT}),
    "revive": frozenset({DISPOSITION_WRITER_KIT}),
    "exited": frozenset({DISPOSITION_WRITER_KIT}),
    "incomplete": frozenset({DISPOSITION_WRITER_SEAT}),
    "unverified": frozenset({DISPOSITION_WRITER_SEAT})}


def validate_disposition(disposition, writer):
    """Refuse a disposition AT THE MOMENT IT IS WRITTEN. RAISES ValueError; never normalizes.

    Three refusals out of one mapping: an unknown writer, a value outside the enum, and a legal
    value reached for by the side that does not own it.

    ⚠ IT RAISES, AND THAT IS THE POINT. Every other failure around this record is best-effort —
    a disk that will not take the write costs a debt nobody recorded, and `set_awaiting` answers
    False rather than taking the checkout down with it. This one is a different KIND of failure:
    a value outside the enum, or a writer reaching across the bound, can only be introduced by
    somebody EDITING THIS FILE, never by the environment. Answering False would leave the DAG
    reading a surface that silently stopped being written, and normalizing would leave it
    advancing on a fact nobody established. Loud, at the boundary, is the only safe direction
    (R-8).

    The writer set is derived from the mapping's own values rather than kept as a second
    constant, so a new writer cannot exist without a value that names it. Since 7.154 each value
    is a SET of admitted writers, so the derivation is a union rather than a collection of
    singletons — the property it exists for is unchanged: a writer nobody's value names does not
    exist here, and adding one is a single edit to the mapping."""
    # ⚠ D33(b) (owner, 2026-08-20) — THE ONE VALUE OUTSIDE THE ENUM, AND IT IS A DESTINATION,
    # NEVER A RECORDED ENDING. The leader's `rule-disposition` gained a second destination beside
    # `done`: the EMPTY cell, which CLEARS a row back to "nobody declared an ending". A CLEAR does
    # NOT re-seed the row — the daemon reads UNDECLARED as not-waitable — so the leader brings it
    # back itself with `launch --only <seat> --declare-only <anchor>`, a session that DECLARES the
    # ending (D39: two acts, by design). ⚠ D42: that is the CLEARED row's door and it is not a
    # re-run. A CRASHED (`exited`) row is re-run in ONE act with `launch --only <seat> --rerun
    # <anchor>` and is never cleared first — the CLEAR would destroy the `exited` word, which is
    # the run's only record of how that session ended.
    # It is admitted HERE, at the one boundary, and
    # for the LEADER ALONE — never by a caller bypassing this function, which is the edit the whole
    # boundary exists to prevent. It is deliberately NOT a key of `RECORD_DISPOSITION_WRITER`: that
    # mapping is the space of ENDINGS a row may CARRY, its key set is asserted equal to
    # `_DEFERRAL_BY_DISPOSITION`'s, and an empty cell is the ABSENCE of an ending — the state
    # `undeclared_endings` already reports and `RULED_FLIP_FROM_STATES` already admits as a
    # FROM-state. Adding it as a key would mint a deferral class for "no class".
    # The writer check below still runs FIRST: an unknown writer clearing a row is not a clear.
    writers = set().union(*RECORD_DISPOSITION_WRITER.values())
    if writer not in writers:
        raise ValueError(
            f"unknown disposition writer {writer!r} — the writers are "
            f"{', '.join(sorted(writers))}. A writer is DECLARED by its call site so this "
            f"boundary can tell a seat's own check-out from an act of the kit; an undeclared "
            f"one cannot be checked against anything.")
    if disposition == "" and writer == DISPOSITION_WRITER_LEADER:
        return                                   # D33(b): the leader's CLEAR. See the note above.
    if disposition not in RECORD_DISPOSITION_WRITER:
        raise ValueError(
            f"{disposition!r} is not a recorded disposition. The enum is exactly "
            f"{', '.join(sorted(RECORD_DISPOSITION_WRITER))}. The value is REFUSED here rather "
            f"than normalized to a neighbour: the DAG advances on this field, and a normalized "
            f"guess advances it on something nobody established.")
    owners = RECORD_DISPOSITION_WRITER[disposition]
    if writer not in owners:
        raise ValueError(
            f"the {writer} may not write disposition {disposition!r} — that value belongs to the "
            f"{', '.join(sorted(owners))}. The bound is not decoration: `exited` is the kit "
            f"attesting that a harness terminated, a fact a seat cannot witness about itself, and "
            f"`done` is a seat reporting its own work finished, a fact the kit never witnessed. "
            f"Each side writes only what it saw. The one act by which a THIRD side writes a value "
            f"it did not itself perform is the leader's `done` on an investigated `exited` row "
            f"(`d-exited-row-closure`), and it is admitted for that value ALONE — this refusal is "
            f"what keeps it there.")


def goal_dir(pkg):
    """The goal folder owning this package — which IS the package (7.607 E2b, design-lock item 8).

    KEPT AS A NAMED IDENTITY, not inlined at its ~dozen call sites. "Which goal owns this package"
    is a question a reader asks and a future layout could answer differently; the walk that used to
    answer it (`pkg.parent.parent if pkg.parent.name == "runs"`) is what died, not the question.

    ⚠ `runs_index_csv` WENT WITH IT. There is no run register: `<goal>/runs.csv` had exactly two
    writers in this file (`ensure_run_index`, `close_run_index`) and both are deleted with the
    layer — liveness is the DERIVED LEASE (item 1) and the goal's end is the FINISH EDGE (item 3).
    """
    return pkg


def sessions_csv(pkg):
    return pkg / "sessions.csv"


# ---- 7.96: THE PER-SESSION SCRATCHPAD — one folder name, two consumers ----------------------
#
# The KG rules a seat's per-session working files to `{seat folder}/sessions/{session-id}/`
# (`concepts/session-folder.md` + `seat-folder.md`, R31). Task 7.11 built it in the DAEMON's spawn
# path only; the kit's own launch path never created one and no seat-facing surface named it, so
# the convention existed on paper and nowhere on disk.
#
# ⚠ THE NAME IS A CONSTANT BECAUSE IT HAS A SECOND, NON-OBVIOUS CONSUMER: `boot_stale_findings`
# walks the WHOLE seat folder by mtime, so a scratchpad under it floods the G-61 staleness detector
# with the seat's own working files — every write the seat makes reads as "your instructions
# changed since you booted". The creator and the excluder MUST agree on the folder name or the
# detector goes to noise the day the scratchpad lands; two string literals is how they would come
# to disagree.
SEAT_SCRATCHPAD_DIR = "sessions"
# `transcripts/` is an EXPORT target written by the close ceremony and never read at boot; the
# scratchpad is the seat's own working output. Neither is a boot-read surface, and the walk that
# reports one as stale instructions is reporting a fact about nothing.
# ⚠ TRANSCRIPTS ARE NOT MOVED HERE (7.96 criterion 5). `transcripts/` stays exactly where the kit
# writes it — task 7.31 owns the KG's `sessions/{session-id}/` transcript home, and this line is
# the whole of 7.96's contact with that question.
BOOT_STALE_SKIP_DIRS = ("transcripts", SEAT_SCRATCHPAD_DIR)


def seat_scratchpad(folder, session_id):
    """`{seat folder}/sessions/{session-id}`, or None when either half is unknown.

    None rather than a partial path: a scratchpad under a blank session-id would be a shared
    folder every session of the seat writes into, which is the one property the convention exists
    to prevent."""
    if not folder or not session_id:
        return None
    return Path(folder) / SEAT_SCRATCHPAD_DIR / session_id

# ---- 7.31: THE PIPE-PANE TRANSCRIPT — where it lands, and how its name is minted ---------------
#
# R31 (`system-definition/decisions.md#d-transcript-placement`) rules the home as
# `{goal}/runs/run-{n}/seats/{seat}/sessions/{session-id}/`. THE `runs/run-{n}` LAYER NO LONGER
# EXISTS: 7.607 E2b extinguished it (design-lock item 8 — the package IS the goal folder, see
# `goal_dir` above, whose own walk `pkg.parent.parent if pkg.parent.name == "runs"` died with it).
# So the ruled path is followed MINUS the layer that was deleted under it — the per-session subtree
# of the seat folder holding the session it records. Everything R31 actually decides is intact:
# workspace-side under the goals tree (never the per-machine ignite root), and ONE transcript per
# session BY CONSTRUCTION, since a new session gets a new `sessions/<session-id>/` folder.
#
# The seats/workers fork mirrors `workers_dir`'s exactly — KG run-folder form wins when present,
# legacy `workers/` otherwise — and it is re-derived here rather than reached through `workers_dir`
# because that resolver takes `args` (and honours a `--workers-dir` override) while every caller
# here holds only the package.
def seat_sessions_dir(pkg, seat):
    seats = pkg / "seats"
    return (seats if seats.is_dir() else pkg / "workers") / seat / "sessions"


def session_transcript_path(pkg, seat, sid):
    """The one file `tmux pipe-pane` writes for this session, and the value of `recorded`."""
    return seat_sessions_dir(pkg, seat) / sid / "transcript.log"


def nonempty_file(p):
    """True when `p` names a file with bytes in it. A zero-byte record is not a record."""
    try:
        return bool(p) and Path(p).is_file() and Path(p).stat().st_size > 0
    except OSError:
        return False


def seat_recorded_log(pkg, seat):
    """`seat`'s pipe-pane log path from its LAST `sessions.csv` row (`recorded`), or `""`.

    THE LAST ROW, not the last OPEN one, and for `resume_ref`'s reason: a session that died with
    its tmux server never gets `ended` stamped, and that death is exactly the case its one caller —
    #259's kill gate — reaches this for. Selecting the open row would miss it.

    LAST-ROW selection is OWNER-RULED (`decisions.md#d-kill-gate-last-row-stands`) — do not "fix"
    it on sight. Accepted cost: on a seat that has since started a newer session, this can clear an
    older DEAD session's kill using the newer session's log. Re-open only on a real incident that
    destroys a record that mattered, or once the pending-close record carries its own session id.

    NEVER RAISES, and returns `""` on every surface that cannot answer (no `sessions.csv`, a header
    predating the `recorded` column, an unreadable trace): the caller is a gate that must FAIL
    CLOSED on a record it cannot read, never take the whole reap sweep down with it."""
    try:
        path = sessions_csv(pkg)
        if not path.exists():
            return ""
        header, rows = read_csv_table(path, SESSIONS_COLS)
        idx = {c: i for i, c in enumerate(header)}
        if not {"seat", "recorded"} <= set(idx):
            return ""
        found = ""
        for r in rows:
            pad_row(r, header)
            if r[idx["seat"]].strip() == seat:
                found = r[idx["recorded"]].strip()
        return found
    except (OSError, ValueError, csv.Error):
        return ""


def mint_session_id_from(taken, seat):
    stem = f"{seat}-{file_stamp()}"
    sid, n = stem, 2
    while sid in taken:          # two sessions of one seat inside one minute
        sid, n = f"{stem}-{n}", n + 1
    return sid


def mint_session_id(pkg, seat):
    """A session-id unique against the trace ON DISK — minted WITHOUT writing a row.

    Split out of `session_open` because 7.31 needs the id BEFORE the row exists: the transcript
    path carries the session-id, and capture must start at pane BIRTH, which is before the harness
    is verified up and therefore before the row may HONESTLY be appended (a row for a seat that
    never booted is the G-11 lie in a second file). Minting reads; it never writes, so a boot that
    dies between the mint and the append leaves no phantom row — only an empty transcript folder.
    """
    header, rows = read_csv_table(sessions_csv(pkg), SESSIONS_COLS)
    idx = {c: i for i, c in enumerate(header)}
    taken = {r[idx["session-id"]].strip() for r in rows
             if "session-id" in idx and idx["session-id"] < len(r)}
    return mint_session_id_from(taken, seat)


def start_pane_capture(pane, logpath):
    """`tmux pipe-pane` this pane into `logpath` from now on. Returns (ok, err).

    ⚠ NEVER `capture-pane` AT CLOSE. tmux scrollback dies with the tmux server, so a close-time
    capture returns NOTHING exactly when the backup matters. `pipe-pane` hands the pane's output to
    a process that appends to a file as it arrives, so whatever the pane had produced is already on
    disk when the server dies.

    `cat >> file` and not `tee`/`cat > file`: append is what survives a re-arm on the same pane
    (a renew respawning in place re-points the pipe), and `cat` writes through with no stdio
    buffering of its own, which is what makes the kill test come back non-empty.
    """
    logpath = Path(logpath)
    try:
        logpath.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"cannot create {logpath.parent}: {exc}"
    r = subprocess.run(["tmux", "pipe-pane", "-t", pane, f"cat >> {shlex.quote(str(logpath))}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False, r.stderr.strip() or "tmux pipe-pane failed"
    return True, ""


def widen_header(header, cols):
    """(header, changed) — the on-disk header plus any of `cols` it is MISSING, appended in order.

    G-152, and it is the difference between this task shipping and this task looking like it did.
    `read_csv_table` preserves the on-disk header verbatim, which is correct — a column contract a
    live reader already keys on must never be reordered or dropped under it. The consequence nobody
    had measured is that a NEW column then reaches only files that do not yet exist: every selftest
    fixture builds a fresh file, so the change reads green everywhere and is a silent no-op on
    run-1, run-2 and every existing package. `G-135` is the same defect at the daemon's SQLite
    store; two components, two persistence technologies, one blind spot — a schema change verified
    only where the schema is BORN, never where it LIVES.

    APPEND-ONLY, and that is the whole safety argument: existing columns keep their positions, so
    a positional reader cannot break (run-1 and run-2 already disagree on column ORDER, which is
    exactly why re-sorting into SESSIONS_COLS order would corrupt one of them). Nothing is ever
    renamed or removed here — a column this kit does not write stays, blank, because deleting it is
    a different decision with a different owner.

    ⚠ `model` USED TO BE THIS DOCSTRING'S EXAMPLE of such a column — hand-added to run-2's header
    and never populated. It stopped being one at ruling D19 (2026-08-11): it is a member of
    `SESSIONS_COLS` now and three writers fill it, so run-2's long-blank column starts carrying the
    model each session actually launched on. Nothing about this function changed; the example did.
    """
    missing = [c for c in cols if c not in header]
    return (header + missing, bool(missing))


def read_csv_table(path, cols):
    """(header, rows). The header is preserved VERBATIM from disk when the file exists — a column
    contract another seat may already read is never rewritten by a writer that merely appends.

    Widening an existing header is `widen_header`'s job, taken deliberately at the WRITE sites
    rather than here: a read must stay a read, or every reader silently rewrites the file it opened.
    """
    if not path.exists():
        return list(cols), []
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            table = list(csv.reader(fh))
    except (OSError, UnicodeDecodeError):
        return list(cols), []
    if not table:
        return list(cols), []
    return table[0], [r for r in table[1:] if any(c.strip() for c in r)]


def write_csv_table(path, header, rows):
    """Atomic: temp file + os.replace. A reader never sees a half-written trace, and a crash
    mid-write leaves the previous table intact (G-45's discipline applied to state files)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    os.replace(tmp, path)


def pad_row(row, header):
    """Widen a short row to the header. A row written before a column existed must not make the
    writer raise — it makes it write a blank cell."""
    while len(row) < len(header):
        row.append("")
    return row


# ---------- 7.607 E1: THE DERIVED LEASE, accessed — never re-implemented here ----------------
#
# `decisions.md#d-extinguishment-design-lock` item 1: "is this goal executing" is DERIVED at ask
# time from live evidence — the goal's tmux room existing + ancestry-verified live seat processes —
# with NO stored status of any kind. The one home of that derivation is
# `ignite/server/lease/lease.js`. THIS IS A THIN ACCESSOR OVER IT AND NOTHING MORE.
#
# ⚠ WHY A SHELL HOP RATHER THAN THREE LINES OF PYTHON. Deriving the room predicate here too would
# be a SECOND implementation of the sentence that decides whether a goal is running, in a second
# language, drifting silently — which is exactly what the register era produced: `runs.csv` had
# THREE independent parsers (inventory #33 / #36 / #37) and nothing made them agree. PRIN-11 says
# one home; one home with two language bindings costs one subprocess per ask, at a 30-second
# cadence, and buys a predicate that cannot fork.

LEASE_JS = Path(__file__).resolve().parent.parent / "server" / "lease" / "lease.js"


def derive_lease(goal):
    """(lease_dict, detail) — the goal's live lease, or ({}, why-it-is-unreadable).

    `goal` is the goal FOLDER. An UNREADABLE lease (no node, no tmux, a crash) returns ({}, detail)
    and is NEVER reported as an absent lease: a caller deciding on ignorance is the failure mode
    the stored register had in both directions at once. A readable lease with no room returns a
    dict whose `live` is False — that is an ANSWER, and callers may act on it.
    """
    goal = Path(goal).resolve()
    workspace_root = goal.parent.parent.parent      # <ws>/.rbtv/goals/<goal>
    if not LEASE_JS.is_file():
        return {}, f"the lease module is absent at {LEASE_JS} — liveness cannot be derived"
    try:
        r = subprocess.run(["node", str(LEASE_JS), str(workspace_root), goal.name],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return {}, f"could not run the lease module ({exc!r}) — liveness cannot be derived"
    try:
        out = json.loads(r.stdout or "{}")
    except json.JSONDecodeError:
        return {}, (f"the lease module printed no parseable JSON (exit {r.returncode}): "
                    f"{(r.stderr or r.stdout or '').strip()[:300]}")
    if not out.get("ok"):
        return {}, out.get("reason") or f"lease unreadable (exit {r.returncode})"
    return out, ""


# ── 7.607 E3b — `resolve_live_run` IS DELETED, AND SO IS THE `current-run` VERB ───────────────
#
# It was the register-era question ("which package of this goal is EXECUTING") wearing the lease's
# evidence, and design-lock item 8 removed its subject: THE PACKAGE IS THE GOAL FOLDER, so the
# function's whole answer had collapsed to "the goal's own name whenever a room exists". Its three
# fire-time callers (`selfheal-watch.py`, `recover-room.py`, `goal-watcher-job.py`) were re-founded
# on `derive_lease` in E3 — taking `rooms[0].packageDir` DIRECTLY, which is what fixed the live bug
# where they composed a `<goal>/runs/<name>` path that no longer exists. Keeping a second, thinner
# accessor beside the one that survived is a second definition of the same fact, which is what
# PRIN-11 forbids and what the register era's three `runs.csv` parsers actually were.
#
# The VERB goes with it rather than being re-pointed: it printed the goal name back to a caller who
# had to name the goal to ask, and its own `next:` line advertised a `--run` flag E2b deleted.
# `derive_lease` is the surviving question and `coordinate execution` the surviving stamp. Nothing
# else in this tree called either symbol (verified at 6fd40b3: the only call sites were
# `cmd_current_run` here and `probes/probe-finish-edge.py`'s F6 arms, which are re-founded on
# `derive_lease` in this same change).


def cmd_execution(args):
    """`execution` — print the goal's current execution stamp; `--mint` starts a new one.

    ⚠ `--mint` IS THE BOOT'S ONE ACT and has exactly one caller: `workflow_launcher.py`, on the arm
    where it CREATES the room (never where it joins one). That is what makes a re-fire of the same
    boot idempotent — a join mints nothing, so a retried launch does not silently invent a second
    execution of the same room. Anything else reads."""
    base = base_dir(args)
    if getattr(args, "mint", False):
        stamp = mint_execution(base)
        print(stamp)
        print(c("a NEW execution of this goal begins here (design-lock item 5). Session rows, "
                "message headers and watcher state written from now on carry this stamp; the "
                "files themselves stay single and append-only", C_HINT))
        return 0
    print(current_execution(base))
    return 0


# ---------- 7.607 E1: THE FINISH EDGE — the ONLY thing that finishes a goal -------------------
#
# `d-extinguishment-design-lock` item 3 (owner-shaped): a goal can ONLY be finished by an explicit
# deterministic EDGE, and firing it is what shuts the watchers off. Everything else that used to
# end a goal's watchers — a closed register row, an empty room, a dead seat — is now a CRASH, and a
# crash is RECOVERED (the watcher relaunches the room), never mistaken for completion.
#
# ⚠ THE EVENT IS AN EVENT, NOT A STATUS, AND THE DISTINCTION IS THE WHOLE DESIGN. It is appended
# ONCE to the append-only coordination message log and never mutated, never cleared, never read for
# liveness. `derive_lease` above cannot see it and must never learn to: the moment "finished" is
# something a reader can consult to decide whether a goal is running, it is a stored status and the
# 7.608 deadlock is rebuilt one file over. The lease answers "is it executing"; the finish event
# answers "was it declared done" — two questions, two surfaces, no overlap.
#
# ⚠ NO TYPE `finish`, AND THE VOCABULARY IS CLOSED AT EIGHT. This block read "NO SIXTH MESSAGE
# TYPE" until W4, and the correction is worth stating rather than deleting: the rule was never
# "five", it was that MINTING A TYPE FROM THE CODE is a registry edit made in the wrong place
# (P2, `concepts/message.md`). W4 added two — `queue-request` and `escalation` — and D2 a third,
# `stuck`, each through the registry with a named consumer, moving every enum site plus the
# store's CHECK in one change. `finish` is still not among them and still must not be: the event
# is a `completion` whose body OPENS with `FINISH_MARKER`, exactly the first-line convention
# `VERDICT_CLAUSE` established — findable by a scan, excluded from every other walk, expressible
# in the settled vocabulary.
#
# ⚠ `ESCALATION_MARKER` is the one first-line convention W4 retired AS AN IDENTITY: the two-strikes
# halt is a `type: escalation` row now (D-8). The marker string survives on the body because it is
# what keeps every pre-W4 halt findable — see `ESCALATION_TYPES` and its stated sunset.

FINISH_MARKER = "goal-finished: the finish edge fired"


def goal_finished(base):
    """The finish EVENT for this package, or None. `(number, timestamp)` when it has fired.

    Scans the append-only log for a `completion` whose body opens with FINISH_MARKER. Idempotent
    by construction: the FIRST such row wins, so a second firing cannot move the moment a goal
    was declared finished.
    """
    _, blocks = load_messages(Path(base) / "coordination")
    for b in blocks:
        if b.get("type") != "completion":
            continue
        body = "\n".join(b.get("lines", [])[1:]).strip()
        if body.startswith(FINISH_MARKER):
            return b["num"], b["ts"]
    return None


def fire_finish_edge(pkg, sender, note=""):
    """Record the finish event, then tear the room down. Returns (ok, detail).

    ORDER IS THE DESIGN, and it is the opposite of intuition: the EVENT IS WRITTEN FIRST. Tearing
    the room down first would produce, for the width of one write, a goal with no room and no
    finish event — which is EXACTLY the crash signature, and a watcher sampling in that window
    would relaunch the room it was just told to stop watching. Writing the event first makes the
    intermediate state 'finished, room still up', which every watcher reads correctly.

    NOT idempotent-by-overwrite: an already-finished goal is REFUSED rather than re-stamped, so a
    second firing cannot quietly move a historical moment. Re-finishing is a correction, and a
    correction should be visible. (`close_run_index`'s posture, carried over deliberately.)
    """
    pkg = Path(pkg)
    already = goal_finished(pkg)
    if already:
        return False, (f"this goal was ALREADY finished by message #{already[0]} at {already[1]} — "
                       f"refusing to re-fire; a correction must be visible, not silent")
    body = (f"{FINISH_MARKER}\n\n"
            f"The goal's execution is over by the deterministic finish edge (7.607 E1, design lock "
            f"item 3). Watchers terminate on THIS event and on nothing else: from here on, an "
            f"absent room is a finished goal rather than a crash to recover."
            + (f"\n\n{note}" if note else ""))
    num = append_message(pkg / "coordination", sender, "all", "completion", body)

    # The room to tear down is ASKED OF THE LEASE, never derived from the package path (`G-296`:
    # a path-derived session name was right only by coincidence and produced a sensor watching
    # nothing). The lease already measured which rooms exist; this tears down the one homed here.
    lease, lease_detail = derive_lease(goal_dir(pkg))
    if lease_detail:
        return True, (f"finish event recorded as message #{num}; the room could NOT be resolved for "
                      f"teardown ({lease_detail}) — tear it down by hand")
    rooms = [r for r in (lease.get("rooms") or [])
             if Path(r.get("packageDir") or "") == pkg.resolve()] or (lease.get("rooms") or [])
    if not rooms:
        return True, f"finish event recorded as message #{num}; no live room to tear down"
    torn, failed = [], []
    for r in rooms:
        room = r.get("room")
        k = subprocess.run(["tmux", "kill-session", "-t", room], capture_output=True, text=True)
        (torn if k.returncode == 0 else failed).append(room)
    detail = f"; room(s) torn down: {', '.join(torn)}" if torn else ""
    if failed:
        detail += (f"; `tmux kill-session` FAILED for {', '.join(failed)} — the event stands, "
                   f"tear them down by hand")
    return True, f"finish event recorded as message #{num}{detail}"


def cmd_finish_goal(args):
    gate(args, "finish-goal")
    pkg = package_dir(args)
    ok, detail = fire_finish_edge(pkg, args.as_agent or "leader", getattr(args, "note", "") or "")
    if not ok:
        refuse("state", detail, 1)
    print(detail)
    print(c("watchers terminate on this event alone. Until it fired, an absent room was a CRASH "
            "and the watcher relaunched it; from here it is a finished goal", C_HINT))
    # ---- s3-03: the LIFECYCLE MARKER SWEEP. `clear_lifecycle` has exactly ONE caller and this is
    # it. Without this block, "swept by the next close" would be a claim about code that does not
    # exist: every `state: "done"` entry would accumulate for the life of the goal and
    # `clear_lifecycle` would ship dead. Runs AFTER the finish edge fired, because a REFUSED finish
    # means the goal is not over and its marker is not this act's to touch.
    #
    # ⚠ IT MOVED HERE FROM `close-run` (7.607 E2b) AND IT MOVED BECAUSE ITS SUBJECT DID. The sweep
    # belonged to the run-close ceremony; runs are extinguished and `close-run` is deleted with the
    # register it stamped. The finish edge (design-lock item 3) is the ONE act that now ends the
    # thing whose end the marker was swept at — same act, new granularity, ONE caller still.
    #
    # The survivors are printed one per line and NAMED. A close that quietly left entries behind
    # would teach the leader that the marker is empty when it is not — and an in-flight entry at
    # close time is exactly the report worth reading.
    swept, survivors = sweep_lifecycle(base_dir(args))
    if swept:
        print(f"lifecycle marker: swept {len(swept)} completed "
              f"{'entry' if len(swept) == 1 else 'entries'} ({', '.join(swept)})")
    for _seat, _why in survivors:
        print(f"lifecycle marker: LEFT {_seat} — {_why}")


def claude_projects_dir():
    """Evaluated at CALL time, not import time, so a test can point HOME at a sandbox and have the
    resolver follow it. A module constant computed from Path.home() at import silently ignores the
    override and reads the real user's transcripts."""
    return Path.home() / ".claude" / "projects"


def claude_project_slug(cwd):
    """Claude's transcript directory name for a working directory: the absolute path with BOTH
    path separators AND DOTS replaced by '-'.

    THE DOT IS NOT COSMETIC AND ITS OMISSION WAS A REAL BUG. Every seat in a goal run lives under
    `.rbtv/`, so a slug that replaces only '/' yields `...-second-brain-.rbtv-goals-...` while the
    directory claude actually writes is `...-second-brain--rbtv-goals-...` (note the DOUBLE dash).
    The lookup missed for EVERY claude seat in this run and `native-session-id` came back empty
    every time.

    It went undetected because the original evidence for this mapping was a directory LISTING, not
    an exercise of this function: the directory was real, the derivation was never run against it.
    A check that resolves a real transcript out of a fixture projects dir now covers it — the
    earlier checks only ever asserted the '' outcome, so none of them could see it.
    """
    return str(Path(cwd).resolve()).replace("/", "-").replace(".", "-")


def claude_native_session_id(cwd, since=None, wait=0.0, projects=None):
    """This boot's claude session id for a seat working in `cwd`, or '' if not resolvable yet.

    EXACT rather than a heuristic, and only because of a property of this layout: every seat's cwd
    is its OWN seat folder, so that project directory holds that seat's sessions and nobody
    else's. `since` (the instant before the harness started) is what makes a RENEW correct — the
    previous session's transcript is static by then, so it sorts out; without `since` a renew
    would resolve to the session it replaced.

    Returns '' rather than guessing when nothing qualifies. An empty field is a stated gap; a
    wrong session id would send task 7.32's resume at another session entirely.
    """
    if not cwd:
        return ""
    d = (Path(projects) if projects else claude_projects_dir()) / claude_project_slug(cwd)
    deadline = time.time() + max(wait, 0.0)
    while True:
        best, best_m = "", -1.0
        if d.is_dir():
            for f in d.glob("*.jsonl"):
                try:
                    m = f.stat().st_mtime
                except OSError:
                    continue
                if since is not None and m < since:
                    continue
                if m > best_m:
                    best, best_m = f.stem, m
        if best or time.time() >= deadline:
            return best
        time.sleep(0.25)


def session_trace_safe(fn, *a, **kw):
    """Run a session-trace write so that its failure can never take down the act it records.

    The trace is bookkeeping ABOUT the run; it must not become a gate ON it. A read-only goal
    folder, a full disk, or a malformed csv would otherwise raise out of `launch_seat` AFTER the
    harness is already up — leaving a live seat the roster believes failed, which is G-11's exact
    shape wearing the bookkeeping mask. Failures are printed LOUDLY and swallowed; the same
    trade-off `refresh_mirrors_for` and `write_seat_statusline` already make.
    """
    try:
        return fn(*a, **kw), ""
    except Exception as exc:                                   # noqa: BLE001 — deliberate
        return None, f"{type(exc).__name__}: {exc}"


def proc_stat_fields(pid):
    """(starttime, tty_nr) from /proc/<pid>/stat as STRINGS, or ('', '').

    Parsed from the LAST ')' rather than by splitting the line, because field 2 (comm) is
    parenthesised and may itself contain spaces and parentheses — the classic way this parse goes
    quietly wrong. Field numbering matches the daemon's own reader
    (ignite/server/seat-identity/identity.js readProcStat), so both sides of the contract compute
    the pair the same way; a starttime that disagreed by one field would refuse every seat.
    """
    try:
        raw = Path(f"/proc/{int(pid)}/stat").read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError, TypeError):
        return "", ""
    close = raw.rfind(")")
    if close < 0:
        return "", ""
    rest = raw[close + 2:].split()
    if len(rest) < 22 - 3 + 1:
        return "", ""
    return rest[22 - 3], (rest[7 - 3] if len(rest) > 7 - 3 else "")


def pane_identity(pane):
    """(pid, pid-starttime, tty) for a seat's pane — all strings, all '' when unresolvable.

    `tty` is the NUMERIC tty_nr, not the /dev/pts path: the gate corroborates against
    /proc/<pid>/stat's tty_nr field, so a device path here would never compare equal and would
    look like a tty mismatch on every seat.

    Never raises and never guesses. An unresolvable pane yields blanks, and `session_open`'s note
    tells the operator — a blank identity is honest; a fabricated one authenticates an impostor.
    """
    if not pane:
        return "", "", ""
    try:
        pid = tmux_pane_pid(pane)
    except Exception:                                          # noqa: BLE001 — never break a boot
        return "", "", ""
    if not pid:
        return "", "", ""
    start, tty = proc_stat_fields(pid)
    return (str(pid), start, tty) if start else ("", "", "")


def session_open(args, w, since=None, wait=None, pane=None, session_id=None, recorded=""):
    """Append this seat's session row the moment it boots. Returns (session-id, note).

    `note` is non-empty when a field could not be resolved — the caller PRINTS it. A blank cell
    that nobody mentioned is indistinguishable from one that was never needed.

    `wait` is a parameter and not a constant read inside so the self-test can drive the resolver
    to its unresolved branch without sleeping through the real boot timeout.

    ⚠ AND `None` MEANS "read NATIVE_ID_WAIT NOW", because a default written as `wait=NATIVE_ID_WAIT`
    IS BOUND AT `def` TIME: a caller that lowers the module constant is then silently ignored, and
    the parameter above delivers its promise only to callers that pass one EXPLICITLY. The path
    that actually spends the budget — launch_seat — passes nothing, so the suite slept through the
    full timeout on every launch while believing it had opted out. Same trap, and the same cure, as
    `claude_projects_dir` evaluating Path.home() at call time instead of import.

    `pane` carries the seat's tmux pane so the row can record the IDENTITY PAIR the seat-identity
    gate decides on. It is the PANE's pid, deliberately, not this process's: every process the seat
    ever runs is a descendant of the pane, and the gate matches the registered pid against the
    CALLER'S ANCESTRY. Recording the launcher's own pid would name a process that is not an
    ancestor of the seat and would refuse every legitimate occupant.
    """
    pkg = package_dir(args)
    native = ""
    if w.get("harness") == "claude":
        native = claude_native_session_id(w.get("cwd"), since,
                                          wait=NATIVE_ID_WAIT if wait is None else wait)
    pid, pid_start, tty = pane_identity(pane)
    rec = {"session-id": "", "seat": w.get("agent", ""), "harness": w.get("harness", ""),
           "native-session-id": native, "workdir": str(w.get("cwd") or ""),
           # `recorded` is the pipe-pane marker of task 7.31, and it is written AT BIRTH by the
           # launch step that armed the capture (`launch_seat`) — never at close, never by a later
           # pass. It resolves to THIS session's transcript (`session_transcript_path`). It is
           # PASSED IN rather than derived here because the arming happened at pane birth, and the
           # marker must name the file the pipe is actually writing, not a path re-computed after
           # the fact. Blank still means exactly what it always meant: nothing was recorded — the
           # reading every row written before 7.31 carries, and the honest reading for a boot whose
           # capture failed to arm.
           "recorded": str(recorded or ""), "started": now(), "ended": "",
           "pid": pid, "pid-starttime": pid_start, "tty": tty,
           # The DATED EXECUTION STAMP this session was opened under (design-lock item 5): the
           # delimiter that separates this boot's rows from every previous boot's in a file that
           # is now goal-durable. READ, never minted here — minting is the boot's one act.
           # Off `pkg`, which this function already resolved — NOT a second `base_dir(args)` hop:
           # that call re-enters the package resolver and re-points the injection context mid-act.
           "execution": current_execution(pkg / "coordination"),
           # The cast this seat's session opened on (D19), off the SAME roster row `harness` is
           # read from two lines above — never re-derived, so the pair cannot disagree. Blank when
           # the roster names none, which is exactly what a blank cell means here.
           "model": w.get("model", "")}
    with coord_lock(base_dir(args)):
        path = sessions_csv(pkg)
        header, rows = read_csv_table(path, SESSIONS_COLS)
        # G-152: the widen happens HERE, on the one path every seat boot takes, so an EXISTING
        # trace gains the identity columns instead of the change being a no-op everywhere it
        # matters. Append-only, so no live reader's column positions move.
        header, widened = widen_header(header, SESSIONS_COLS)
        if widened:
            rows = [pad_row(r, header) for r in rows]
        idx = {c: i for i, c in enumerate(header)}
        taken = {r[idx["session-id"]].strip() for r in rows
                 if "session-id" in idx and idx["session-id"] < len(r)}
        if session_id:
            # 7.31: the id was minted at PANE BIRTH (`mint_session_id`, under this same lock)
            # because the transcript path carries it. A collision here means a row appeared under
            # that id in between — vanishingly unlikely, and never guessed past: raising is caught
            # by `session_trace_safe`, which prints LOUDLY and leaves the live seat alone. Silently
            # bumping the id would file the row away from the transcript already recording.
            if session_id in taken:
                raise RuntimeError(
                    f"session-id {session_id!r} was taken between its mint at pane birth and this "
                    f"append — the transcript already recording under it would be mis-filed")
            sid = session_id
        else:
            sid = mint_session_id_from(taken, rec["seat"])
        rec["session-id"] = sid
        rows.append([rec.get(c, "") for c in header])
        write_csv_table(path, header, rows)
    # 7.96: the per-session scratchpad, created HERE — the one place a session-id is minted, so
    # every door that opens a session row (launch, `close-seat --renew`, `cmd_session_open`) gets
    # it with no second call site to forget. Parity with the daemon's spawn path, which already
    # does this (`server/spawn/spawn.js`). `exist_ok`: a re-run against an existing id is not an
    # error, and this is created BEFORE the seat is told the id at its check-in, so the folder the
    # instruction names always exists by the time the seat reads it.
    scratch = seat_scratchpad(w.get("folder"), sid)
    if scratch:
        scratch.mkdir(parents=True, exist_ok=True)
    note = ("" if native or w.get("harness") != "claude"
            else "native-session-id UNRESOLVED at launch — retried at close")
    return sid, note


def session_open_ids(pkg, seat):
    """EVERY open session row of `seat` (`ended` empty), in file order, as session-ids. [] for none.

    7.97 needed the COUNT and not the last one: the state-cursor convention resolves the cursor's
    `session-id` from the writing seat's open row and rules that TWO open rows is "a defect to
    report, not a coin flip" (`r-stage0-state-cursor-interim-convention` (b)) — a question
    `session_open_id` cannot answer, because answering with the LAST open row is its design (a
    renew opens a new session of the same seat). One walk of the file with two readings of it,
    rather than a second walk one function over (PRIN-11).

    The blank-`session-id` sentinel is produced HERE, so both callers see an open row as an open
    row: "" is `session_open_id`'s "no open row" answer, and a row that IS open must never borrow
    it (see that function's own note).
    """
    path = sessions_csv(pkg)
    if not path.exists():
        return []
    header, rows = read_csv_table(path, SESSIONS_COLS)
    idx = {c: i for i, c in enumerate(header)}
    if not {"seat", "ended", "session-id"} <= set(idx):
        return []
    found = []
    for r in rows:
        pad_row(r, header)
        if r[idx["seat"]].strip() == seat and not r[idx["ended"]].strip():
            found.append(r[idx["session-id"]].strip() or "(open row, blank session-id)")
    return found


def session_open_id(pkg, seat):
    """The session-id of `seat`'s LAST OPEN row (`ended` empty), or "" when it has none.

    The guard `session_open` itself does not carry: `session_open` APPENDS unconditionally, which
    is right on the launch path (a renew is a new session of the same seat) and wrong for a
    launcher that RETRIES — a second spawn attempt would leave the seat two open rows and the
    trace would say two sessions ran. `cmd_session_open` reads this first and no-ops on a hit.

    ⚠ NOT `session_open_started`, which answers the same question and is NOT usable here: it
    returns None both for "no open row" and for an open row whose `started` stamp will not parse,
    and this caller must not read the second as the first — that reading is what appends the
    duplicate. It reports the ID, so an unparseable stamp still says "a row is open".

    Same reason an open row with a BLANK `session-id` reports `(open row, blank session-id)`: ""
    is this function's "no open row" answer, and giving it to a row that IS open would reopen the
    duplicate one field over.
    """
    ids = session_open_ids(pkg, seat)
    return ids[-1] if ids else ""


# ---------- 7.97: THE STATE CURSOR's advance-writer — the goal's position, APPENDED ----------
#
# `r-stage0-state-cursor-interim-convention` (goal `decisions.md`, recorded by s0-04) ruled this
# file, its header and its discipline — and ruled its Automation row **NONE in Stage 0**: the
# leader stamped every row BY HAND, and wiring a writer was filed as the follow-up this block
# discharges. `materialize-seats.py` creates the file HEADER-ONLY at package creation (its
# `STATE_CSV_HEADER`); until now nothing in the kit appended to it.
#
# ⚠ PACKAGE-GENERIC, NOT RUN-3. The task was authored against `runs/run-3/state.csv`. The run
# layer is EXTINGUISHED (`d-runs-extinguished`) and run-3 closed 2026-08-08, so this resolves its
# package through `package_dir(args)` exactly like every other command in this file and works on
# whatever goal package the caller stands in. Nothing here names a run.
#
# ⚠⚠ THE HEADER ON DISK IS THE SCHEMA. There is no `STATE_CSV_COLS` constant here ON PURPOSE, and
# the omission is the load-bearing part: the ruled header is 5 columns
# (`stamped-at,run-state,seat,session-id,note`) and the KG `state-cursor` record has since
# re-authored it to 6 — `execution-stamp` added, `run-state` renamed `goal-state`
# (`d-runs-extinguished-transcription`) — while `materialize-seats.py` still creates the 5-column
# form. A writer carrying its own column list would have to pick ONE of those and would write a
# malformed row into every package carrying the other. So the row is built BY NAME against the
# header the file already carries: a column this writer knows is filled, a column it does not know
# is left blank, and a column the file does not have is simply not written. BOTH spellings of the
# state column are filled for that same reason — whichever one the file carries is the one that
# lands, and the other is not there to receive it.
#
# The header is consequently NEVER rewritten and never widened. Widening it is
# `materialize-seats.py`'s decision (it owns the created form) — not this writer's, which is a
# strictly weaker act than `sessions.csv`'s writers take deliberately through `widen_header`.
STATE_CSV = "state.csv"
STATE_COL_STATE = ("run-state", "goal-state")   # the ruled spelling, and the KG's successor

# The goal WORKING-lifecycle vocabulary, read from the KG at build time rather than recalled:
# `sd-graph show "goal state"` — "The WORKING lifecycle advances planning -> staged -> executing
# -> verifying -> blocked (non-terminal) -> completed | failed and is monotone." The `run` record
# the task cites is RETIRED with the run layer; the vocabulary moved onto `goal state` UNCHANGED,
# value for value, which is why the task's set and this one are the same seven.
#
# ⚠ MONOTONICITY IS NOT ENFORCED HERE, deliberately. `blocked` is explicitly non-terminal, and the
# convention's Discipline row corrects a wrong row with a NEW row whose `note` names the one it
# supersedes. A writer that refused a "backward" advance would refuse both of those legal acts,
# and the second one is the ONLY correction mechanism an append-only file has.
GOAL_WORKING_STATES = ("planning", "staged", "executing", "verifying", "blocked",
                       "completed", "failed")


def state_csv(pkg):
    return pkg / STATE_CSV


def append_state_advance(pkg, header, state, seat, session_id, note):
    """Append EXACTLY ONE advance row to the goal's state cursor. Returns the row written.

    APPEND-ONLY BY CONSTRUCTION rather than by discipline: the file is opened in APPEND mode and
    one `csv.writer` row goes out. No existing row is read into memory on this path, so there is
    no read-modify-write for a future bug to turn into an edit — the whole class the convention's
    "a row is never edited or deleted" rule stands against is unreachable through this door.
    ⚠ `write_csv_table`, this file's other csv writer, rewrites the WHOLE table; using it here
    would have made every append a full rewrite of the history it is meant to preserve.

    `csv.writer` is also what pins the row's FIELD COUNT to the header's whatever the note holds:
    a note carrying commas, quotes or newlines is QUOTED, never split into an extra field. That
    is the mechanism behind this task's 6th-field red arm — the arm proves the property, it does
    not install it.
    """
    values = {"stamped-at": now(), "seat": seat, "session-id": session_id, "note": note,
              "execution-stamp": current_execution(pkg / "coordination")}
    for col in STATE_COL_STATE:
        values[col] = state
    row = [values.get(col, "") for col in header]
    with state_csv(pkg).open("a", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(row)
    return row


def cmd_advance_state(args):
    """`advance-state <state>` — stamp ONE row on the goal's state cursor."""
    seat = gate(args, "advance-state")
    if not seat:
        refuse("identity",
               "`advance-state` — the gate was carried but WHO is advancing could not be "
               "resolved, and the `seat` column is that answer. The cursor names the locus of "
               "every advance; a blank one records that the goal moved and nobody moved it.", 2)
    state = (getattr(args, "state", "") or "").strip()
    if state not in GOAL_WORKING_STATES:
        refuse("input",
               f"`advance-state` — {state!r} is not a goal working-lifecycle state. The "
               f"vocabulary is exactly {', '.join(GOAL_WORKING_STATES)} (KG `goal state`; the "
               f"retired `run` record's set, unchanged).\n"
               f"REFUSED rather than normalized to a neighbour: this file IS the goal's position, "
               f"and a normalized guess moves the position to somewhere nobody established.", 2)
    pkg = package_dir(args)
    path = state_csv(pkg)
    if not path.exists():
        refuse("state",
               f"no state cursor at {path} — this package carries none.\n"
               f"The cursor is created HEADER-ONLY at package creation (`materialize-seats.py`, "
               f"`r-stage0-state-cursor-interim-convention` (a)) and this writer only APPENDS to "
               f"the header the package already has. It never invents one: a header minted here "
               f"would fork the schema away from its single owner, and the two would drift with "
               f"nothing comparing them.", 1)
    header, _ = read_csv_table(path, [])
    if not [col for col in STATE_COL_STATE if col in header]:
        refuse("state",
               f"the cursor at {path} carries NO state column — its header is "
               f"`{','.join(header)}`, and neither `run-state` (the ruled spelling) nor "
               f"`goal-state` (the KG's successor) appears in it. The row would land with the "
               f"state nowhere, which is a cursor that does not say where the goal stands.", 1)
    open_ids = session_open_ids(pkg, seat)
    if len(open_ids) != 1:
        refuse("state",
               f"`advance-state` — {seat} has {len(open_ids)} OPEN session row(s) in "
               f"{sessions_csv(pkg)} ({'; '.join(open_ids) or 'none'}), and `session-id` is "
               f"resolved from EXACTLY ONE.\n"
               f"It is resolved at write time and is never an argument: an id off the command "
               f"line records which session the caller SAID it was, which is the one thing this "
               f"column is not for. Two open rows is a defect to REPORT, never a coin flip "
               f"(`r-stage0-state-cursor-interim-convention` (b)) — check in, or close the stale "
               f"row, then re-run.", 1)
    with coord_lock(base_dir(args)):
        row = append_state_advance(pkg, header, state, seat,
                                   open_ids[0], (getattr(args, "note", "") or "").strip())
    print(f"{state}: one row appended to {path}")
    print(c("  " + " · ".join(f"{col}={val}" for col, val in zip(header, row) if val), C_HINT))
    return 0


def session_backfill_native(args, seat):
    """Fill a live session row's `native-session-id` from the seat's OWN checkin. Returns the id
    filled, or ''.

    WHY THIS EXISTS, measured rather than anticipated: resolving at LAUNCH races the harness's own
    startup. claude writes its transcript when it first has something to write, which is AFTER
    `wait_harness_up` returns — the leader's 08:21 renewal resolved to '' because no transcript in
    its project dir was newer than the launch instant inside the launch-side window.

    Checkin is the correct hook and is exact: the seat is running, has processed its boot prompt,
    and the transcript it is actively writing is by definition the most recently modified file in
    its own project directory. No `since` is needed, and no window can expire.

    It also closes the case the launch-side resolver could never reach: a seat that CRASHES never
    closes, so a close-time backfill would never run — but a crashed seat did check in, and 7.32's
    native resume is exactly the path a crashed seat needs.
    """
    pkg = package_dir(args)
    with coord_lock(base_dir(args)):
        path = sessions_csv(pkg)
        if not path.exists():
            return ""
        header, rows = read_csv_table(path, SESSIONS_COLS)
        idx = {c: i for i, c in enumerate(header)}
        if not {"seat", "ended", "native-session-id", "harness", "workdir"} <= set(idx):
            return ""
        target = None
        for r in rows:
            pad_row(r, header)
            if (r[idx["seat"]].strip() == seat and not r[idx["ended"]].strip()
                    and not r[idx["native-session-id"]].strip()
                    and r[idx["harness"]].strip() == "claude"):
                target = r
        if target is None:
            return ""
        native = claude_native_session_id(target[idx["workdir"]].strip())
        if not native:
            # NEVER SILENT. A backfill that finds its row and fails to resolve used to return ''
            # exactly like one with nothing to do, and the caller printed nothing either way — so
            # the slug bug above sat invisible through every checkin in this run. A clean result
            # must never be readable as a clean class.
            return f"!unresolved: no claude transcript under {claude_project_slug(target[idx['workdir']].strip())}"
        target[idx["native-session-id"]] = native
        write_csv_table(path, header, rows)
        return native


def session_checkin(args, seat):
    """Stamp `checkin` on `seat`'s LAST OPEN session row. Returns (session-id, native, stamp).

    `("", "", "")` when there is no open row to stamp — no `sessions.csv` (a package that never
    launched through the kit), a header this widen cannot reach, or a seat with every row closed.
    The caller reports that as UNRESOLVED rather than as silence: an identity line that prints only
    when it can is indistinguishable from one that is never reached.

    ⚠ IT WRITES AND IT READS, and the pair is deliberate — the two acts 7.96 asks for are the SAME
    ROW, and resolving it twice is how "the id I was told" and "the row that was stamped" come to
    name different sessions. `session_backfill_native` runs FIRST at the call site, so the `native`
    returned here is that backfill's own result read back off disk rather than a second resolution
    of it.

    LAST OPEN ROW WINS — the same selection `session_close` and `sessions_open_ids` apply, stated
    once more here because this writer must stamp the row the check-out will later close.

    The header is WIDENED (G-152), which is what puts the column on the live traces rather than
    only on files born after it existed; historical rows are padded blank and no existing column
    moves."""
    pkg = package_dir(args)
    with coord_lock(base_dir(args)):
        path = sessions_csv(pkg)
        if not path.exists():
            return "", "", ""
        header, rows = read_csv_table(path, SESSIONS_COLS)
        header, widened = widen_header(header, SESSIONS_COLS)
        if widened:
            rows = [pad_row(r, header) for r in rows]
        idx = {c: i for i, c in enumerate(header)}
        if not {"seat", "ended", "session-id", "checkin"} <= set(idx):
            return "", "", ""
        target = None
        for r in rows:
            pad_row(r, header)
            if r[idx["seat"]].strip() == seat and not r[idx["ended"]].strip():
                target = r
        if target is None:
            return "", "", ""
        stamp = now()
        target[idx["checkin"]] = stamp
        write_csv_table(path, header, rows)
        return (target[idx["session-id"]].strip(),
                target[idx["native-session-id"]].strip() if "native-session-id" in idx else "",
                stamp)


# The identity line's UNRESOLVED marker — ONE literal, so the two ids that can go missing say the
# same word and a reader never has to tell two spellings of "we do not know" apart.
SESSION_UNRESOLVED = "UNRESOLVED"


def session_identity_line(seat, session_id, native, scratch):
    """The check-in's identity report, PURE so the selftest asserts the line and not a screen.

    Every field prints on EVERY check-in, resolved or not: the whole defect 7.96 closes is that the
    seat WAS told its ids — but only on the failure branch, which measured 0 hits in 104 sessions.
    A line that appears only when there is something to say teaches a seat that silence means
    nothing is wrong."""
    return (f"session: {session_id or SESSION_UNRESOLVED} · "
            f"native: {native or SESSION_UNRESOLVED} · "
            f"scratchpad: {scratch or SESSION_UNRESOLVED}")


def session_close(args, seat, disposition="", writer=DISPOSITION_WRITER_SEAT):
    """Complete the seat's open session row: stamp `ended`, and fill `native-session-id` if the
    launch could not resolve it yet. Returns the session-id closed, or ''.

    A silent no-op when the seat has NO open row — a seat closed twice, or one launched before
    this writer existed, must not gain a phantom row. The close path is reached by three commands
    (close-seat, depart, checkout) and a run may traverse more than one of them for one seat.

    dag-09: `disposition` is the DURABLE copy of the value `set_awaiting` records, and the two
    come from ONE variable at the one call site that knows it (`cmd_checkout`) — computing it
    twice is precisely the defect this column's acceptance row exists to catch.

    It DEFAULTS TO EMPTY, and empty is a truthful answer rather than a gap. Of the three commands
    that close a session, only `checkout` is the SEAT declaring its own disposition; `close-seat`
    and `depart` are somebody else ending the row, and neither witnessed what the occupant meant.
    An empty cell reads as `unknown` — never as `done` — so the fail-safe direction is a successor
    that stays BLOCKED, never one advanced on a fact nobody asserted."""
    pkg = package_dir(args)
    with coord_lock(base_dir(args)):
        path = sessions_csv(pkg)
        if not path.exists():
            return ""
        header, rows = read_csv_table(path, SESSIONS_COLS)
        # G-152, and it is the reason this widen is HERE and not only in `session_open`: a column
        # added to the constant reaches only files that do not yet exist unless a LIVE writer
        # widens the header it opened. Every selftest fixture builds a fresh file, so a change
        # verified only at the birth site reads green everywhere and is a silent no-op on run-2 —
        # a schema change proven where the schema is BORN and never where it LIVES.
        header, widened = widen_header(header, SESSIONS_COLS)
        if widened:
            rows = [pad_row(r, header) for r in rows]
        idx = {c: i for i, c in enumerate(header)}
        if "seat" not in idx or "ended" not in idx:
            return ""
        target = None
        for r in rows:                      # LAST open row wins — the live session
            pad_row(r, header)
            if r[idx["seat"]].strip() == seat and not r[idx["ended"]].strip():
                target = r
        if target is None:
            return ""
        target[idx["ended"]] = now()
        # dag-09: validated through the SAME boundary `awaiting-close.json`'s writer uses, so the
        # two surfaces cannot hold values from two different vocabularies AND the writer bound
        # holds on BOTH of them — `exited` is the attest arm's on this surface exactly as it is
        # over there. `writer` is a PARAMETER and not looked up from the mapping: deriving it from
        # the very table it is then checked against would be a guard that cannot fire.
        # An empty string is the one value that skips validation, because "nobody declared one" is
        # not a disposition — it is the absence of one, and it is recorded as such.
        if disposition and "disposition" in idx:
            validate_disposition(disposition, writer)
            target[idx["disposition"]] = disposition
            # 7.155: the AUTHOR, written from the SAME pair the line above validated — never
            # re-derived, never looked up. It is recorded here and not only on the ruled-flip path
            # because a column filled on one path and blank on the others cannot be read: a blank
            # would mean both "written before this column existed" and "written by a path that does
            # not bother", and the second reading would make the first unprovable.
            if "disposition-writer" in idx:
                target[idx["disposition-writer"]] = writer
        if ("native-session-id" in idx and not target[idx["native-session-id"]].strip()
                and target[idx.get("harness", 0)].strip() == "claude"):
            since = None
            if "started" in idx:
                try:
                    since = datetime.strptime(
                        target[idx["started"]].strip(), "%Y-%m-%d %H:%M").timestamp()
                except ValueError:
                    since = None
            wd = target[idx["workdir"]].strip() if "workdir" in idx else ""
            target[idx["native-session-id"]] = claude_native_session_id(wd, since)
        write_csv_table(path, header, rows)
        return target[idx["session-id"]].strip() if "session-id" in idx else ""


# ---- 7.32 leaf (ii)/(iii): HARNESS-NATIVE RESUME, and the restarter fallback -------------------
#
# THE ROW ALONE IS THE SOURCE, AND THAT IS THE WHOLE TEST. Task 7.37's criterion 4 —
# *"`sessions.csv` carries enough to drive task 7.32's native resume with no other source"* — was
# ruled MET AGAINST THE CONTRACT, NOT PROVEN BY USE (run-2 leader, `#463`/`#466`), because
# *"enough to DRIVE"* is a SUFFICIENCY claim provable only by driving it. So `sessions_resume_ref`
# reads the sessions row and NOTHING ELSE: no descriptor, no transcript, no tmux, no harness
# probe. If a field it needs is missing, the criterion is FALSE and this refuses saying which
# field — a reader that reached for a second source would make the criterion unfalsifiable.
#
# ⚠ WHAT THE DESCRIPTOR STILL SUPPLIES, said plainly so the claim stays honest: the successor's
# PANE and CWD come from the launch path as they always did (`launch_seat`). The claim under test
# is narrower and is exactly 7.37's: the RESUME REF — which conversation to re-enter, in which
# harness's own vocabulary — comes from the row.
#
# ⚠ RECOVERY, NOT SURVIVAL (the row's accepted trade, re-scoping CON-1). A resumed session re-enters
# the recorded conversation; the turn that was in flight when the process died is GONE. Nothing
# here is built to preserve it and nothing should be.

# The ONE re-orient nudge (`_Restart path (R4):_`, verbatim intent). ONE, and it is the entire
# prompt of a natively-resumed session: the session already holds its briefing, its history and its
# own memory — re-sending any of that would be the recreation this path exists to avoid.
REORIENT_NUDGE = ("You were RESUMED after your session's process died — this is the same "
                  "conversation, not a new one. Before acting: run `coordinate status`, then "
                  "re-read whatever your next act touches. The turn you were mid-way through was "
                  "lost with the process (recovery, not survival) — re-derive it, never assume it "
                  "landed.")

# The harness's OWN resume vocabulary. Keyed to `ignite/config/spawn-profiles.yaml`'s
# `session_ref:` source for each harness, verified against the installed CLIs 2026-08-05:
#   claude   `session_ref: {source: stdout-json, field: session_id}`        -> `--resume <id>`
#   codex    `session_ref: {source: stdout-json-event, field: thread_id}`   -> `resume <id>`
#   opencode `session_ref: {source: cwd-implicit}`                         -> `run --continue`
# ⚠ opencode is the CWD-IMPLICIT case and it takes NO id: its ref IS the workdir, so the row's
# `workdir` is the field that must be present for it and `native-session-id` legitimately is not.
# Reading it as "no id -> not resumable" would refuse the one harness whose profile says the
# workdir is the ref.
RESUME_NEEDS_ID = {"claude": True, "codex": True, "opencode": False}


def sessions_resume_ref(args, seat):
    """(ref, why) — the resume ref for `seat` from its LAST sessions.csv row AND NOTHING ELSE.

    `ref` is `{"session-id", "harness", "native-session-id", "workdir"}` on success; `None` means
    NOT RESUMABLE FROM THE ROW, and `why` names the field that is missing or wrong. That refusal is
    the fallback's trigger (leaf (iii)) and is also 7.37 criterion 4's falsifier — it is never
    repaired here by consulting anything else.

    THE LAST ROW, not the last OPEN row: a crashed session never gets `ended` stamped, but a seat
    whose predecessor session closed cleanly and whose CURRENT session then crashed has both shapes
    in the file. Ordering is the file's own — `sessions.csv` is append-ordered by construction
    (`session_open` appends), which is the property 7.37 built it on.
    """
    path = sessions_csv(package_dir(args))
    if not path.exists():
        return None, f"{path} does not exist — this run has no session trace to resume from"
    header, rows = read_csv_table(path, SESSIONS_COLS)
    idx = {c: i for i, c in enumerate(header)}
    need = {"seat", "harness", "native-session-id", "workdir", "session-id"}
    if not need <= set(idx):
        return None, (f"{path} is missing column(s) {', '.join(sorted(need - set(idx)))} — the "
                      f"trace cannot carry a resume ref at all")
    last = None
    for r in rows:
        pad_row(r, header)
        if r[idx["seat"]].strip() == seat:
            last = r
    if last is None:
        return None, f"{path} carries NO row for seat '{seat}' — nothing was ever recorded to resume"
    ref = {k: last[idx[k]].strip() for k in ("session-id", "harness", "native-session-id", "workdir")}
    if ref["harness"] not in RESUME_NEEDS_ID:
        return None, (f"the row's `harness` is {ref['harness']!r}, which has no resume form in this "
                      f"kit (known: {', '.join(sorted(RESUME_NEEDS_ID))})")
    if RESUME_NEEDS_ID[ref["harness"]] and not ref["native-session-id"]:
        return None, (f"the row's `native-session-id` is EMPTY and harness {ref['harness']!r} "
                      f"resumes BY ID — the trace records no conversation to re-enter")
    if ref["native-session-id"].startswith("!"):
        return None, (f"the row's `native-session-id` records a resolution FAILURE "
                      f"({ref['native-session-id']}), not an id")
    if not ref["workdir"]:
        return None, "the row's `workdir` is EMPTY — no launch home is recorded"
    return ref, (f"row {ref['session-id']} — harness {ref['harness']}, "
                 f"ref {ref['native-session-id'] or '(cwd-implicit: ' + ref['workdir'] + ')'}")


def resume_command(w, ref, prompt_path):
    """(shell command, '') that RE-ENTERS the recorded conversation, or (None, reason).

    Deliberately a SIBLING of `harness_command` rather than a flag on it: a resume and a boot are
    different command SHAPES (codex's is a subcommand, opencode's a flag on `run`), and folding
    them into one function is how the position bug G-13 got in — `opencode --auto run` exits 0 and
    launches nothing. The identity prefix and the prompt-from-file discipline are shared, and both
    are read from the same helpers, so neither can drift.
    """
    env = identity_prefix(w["agent"])
    arg = '"$(cat ' + shlex.quote(str(prompt_path)) + ')"'
    sid = shlex.quote(ref["native-session-id"])
    if ref["harness"] == "claude":
        return f"{env}{CLAUDE_BIN} --resume {sid} {arg}", ""
    if ref["harness"] == "codex":
        # 7.612 / `d-codex-hook-trust-bypass`. POSITION IS LOAD-BEARING: codex's grammar is
        # `codex [OPTIONS] <COMMAND>`, so the flag must precede the `resume` SUBCOMMAND —
        # placed after it, codex parses it as one of resume's own options and the hook trust
        # gate stays armed. Same G-13 class as opencode's `--auto`.
        return f"{env}{CODEX_BIN} --dangerously-bypass-hook-trust resume {sid} {arg}", ""
    if ref["harness"] == "opencode":
        # `--continue` continues the last session IN THIS CWD, which is exactly what
        # `session_ref: {source: cwd-implicit}` declares the ref to be. `--auto` after `run` —
        # G-13's position rule, unchanged.
        return f"{env}{OPENCODE_BIN} run --auto --continue {arg}", ""
    return None, f"harness '{ref['harness']}' has no resume form"


def restarter_prompt(w, args, why):
    """The RESTARTER-AGENT fallback prompt (leaf (iii)) — used when the row cannot drive a resume.

    ⚠ READING DISCLOSED, NOT ASSUMED. `_Restart path (R4):_` says *"a restarter AGENT is the
    FALLBACK ONLY — for a non-resumable harness or a corrupt transcript"*, and `restarter` is BUILD
    VOCABULARY: `sd-graph show restarter` resolves no record. What is built here is the fallback's
    substance and not a second launch component — the seat's own harness boots FRESH from its
    descriptor (the path that already existed) carrying a RESTARTER brief: an agent doing the
    re-orientation a native resume would have done for free. A separate restarter process would be
    a second thing that opens panes, which this kit deliberately has exactly one of.

    It NAMES WHY the native resume was refused, because the successor is the reader best placed to
    notice that the reason is wrong.
    """
    return (f"Your prior session DIED and could NOT be resumed natively: {why}. "
            f"You are a FRESH session of seat '{w['agent']}' standing in for it — the lost "
            f"session's conversation is gone and is not recoverable. "
            f"{boot_prompt(w, args)} "
            f"Before acting, run `coordinate status` and re-read whatever your next act touches: "
            f"work your predecessor reported may or may not have landed, so VERIFY it on disk "
            f"rather than trusting any record of intent.")


def sessions_last_ended_rows(pkg):
    """{seat: {column: value}} — every seat's LAST ENDED session row, WHOLE, in ONE read.

    D42: THE ROW SELECTION MOVED HERE AND STAYED ONE COPY. `sessions_last_ended` (below) is now a
    projection of this, so the "LAST IN FILE ORDER" rule argued in its docstring is stated once and
    every caller that needs a column those two cells do not carry — `disposition-writer` for the
    re-run door, `hold-anchor` for the hold — reads THE SAME selected row rather than re-selecting
    it with a second, subtly different rule.

    Cells are returned STRIPPED, exactly as the projection has always returned them. Same
    can-not-answer contract: `{}` for no `sessions.csv` and for a header predating dag-09."""
    path = sessions_csv(pkg)
    if not path.exists():
        return {}
    header, rows = read_csv_table(path, SESSIONS_COLS)
    idx = {c: i for i, c in enumerate(header)}
    if not {"seat", "ended", "disposition"} <= set(idx):
        return {}
    out = {}
    for r in rows:
        pad_row(r, header)
        seat = r[idx["seat"]].strip()
        if seat and r[idx["ended"]].strip():
            out[seat] = {c: r[i].strip() for c, i in idx.items() if i < len(r)}
    return out


def reopen_attempt_count(pkg, seat, reason):
    """How many PRIOR `--reopen` sittings of `seat` already carry this EXACT `reason` string, read
    off `sessions.csv` alone (D66's brake, kept coord.py-LOCAL — see the `--reopen` admission
    block's own comment in `cmd_launch` for why this does not touch brief 07's `heart.db` counter:
    that store's sole writer is `HeartStore.enqueue()`, and `--reopen`, like `--rerun` before it,
    is a LEADER-DIRECT door that never enqueues).

    Conservative by construction: counts every prior reopen under an UNCHANGED reason, whether or
    not that sitting later made progress — D52's progress-relief (the mail cursor moved, a row's
    disposition changed) is NOT evaluated here, so this can only OVER-count relative to the full
    ruling, never under-count. Over-counting is the fail-closed direction."""
    path = sessions_csv(pkg)
    if not path.exists():
        return 0
    header, rows = read_csv_table(path, SESSIONS_COLS)
    idx = {c: i for i, c in enumerate(header)}
    if not {"seat", REOPEN_REASON_COL} <= set(idx):
        return 0
    reason = (reason or "").strip()
    if not reason:
        return 0
    n = 0
    for r in rows:
        pad_row(r, header)
        if r[idx["seat"]].strip() != seat:
            continue
        cell = r[idx[REOPEN_REASON_COL]].strip()
        # The cell may carry this door's own messages.md pointer suffix (" (downstream flagged
        # in messages.md #N)") — compare the REASON PREFIX only, so a later read is not fooled
        # by its own annotation.
        if cell == reason or cell.startswith(reason + " ("):
            n += 1
    return n


def last_ended_pairs(rows):
    """{seat: (session-id, disposition)} from `sessions_last_ended_rows`' output.

    ONE derivation, shared by `sessions_last_ended` and by `ready_seat_rows`' single hoisted read,
    so the hoist can carry the WHOLE row without paying for a second read of the file — and without
    the two answers being able to straddle a concurrent append."""
    return {s: (r.get("session-id", ""), r.get("disposition", "")) for s, r in rows.items()}


def sessions_last_ended(pkg):
    """{seat: (session-id, disposition)} — every seat's LAST ENDED session row, in ONE read.

    THE SINGLE ROW SELECTION EVERY DURABLE-DISPOSITION QUESTION GOES THROUGH, and it is one
    function because there are now TWO questions about that same row — what the ending WAS
    (`session_disposition`) and whether an ending was DECLARED AT ALL (`undeclared_endings`).
    Selecting the row twice is exactly how the two would come to describe DIFFERENT sessions
    while reading as though they agreed; this file already carries that argument at
    `session_close`/`set_awaiting` ("ONE VARIABLE, READ BY BOTH SURFACES") and it is the same
    argument here.

    LAST IN FILE ORDER — preserved verbatim from `session_disposition`, which has always done
    this and whose behaviour must not move: rows are APPENDED in open order, so a seat's last
    ended row is its newest ended session. Deliberately NOT re-sorted by the `ended` cell; a
    sort would be a second, subtly different selection rule reaching the same readers.

    Returns {} on every surface that cannot answer — no `sessions.csv`, or a header predating
    dag-09 with no `disposition` column — which keeps `None`/absent meaning UNKNOWN in both
    readers rather than manufacturing a value neither file asserted."""
    return last_ended_pairs(sessions_last_ended_rows(pkg))


def sessions_open_ids(pkg):
    """{seat: session-id} — every seat's LAST OPEN `sessions.csv` row, in ONE read.

    THE OPEN-ROW TWIN OF `sessions_last_ended`, and it is one function for the same reason that
    one is: TWO questions now select a seat's open row — which session a handoff belongs to
    (`session_id_open`) and which session a seat-side disposition record is allowed to speak for
    (`session_disposition`'s 7.475 fallback). Selecting it twice is exactly how the two would come
    to describe DIFFERENT sessions while reading as though they agreed.

    LAST IN FILE ORDER — preserved verbatim from `session_id_open`, which has always done this and
    whose behaviour must not move: rows are APPENDED in open order, so a seat's last open row is
    its newest. Deliberately NOT re-sorted by the `started` cell; a sort would be a second, subtly
    different selection rule reaching the same readers.

    Returns {} on every surface that cannot answer — no `sessions.csv`, or a header missing any of
    `seat`/`ended`/`session-id` — which keeps an absent seat meaning UNKNOWN in both callers rather
    than manufacturing a match no file asserted. NEVER RAISES: both callers are read-only paths
    whose contract is a value, and `session_id_open`'s never-fatal guarantee is preserved HERE
    rather than only at its own call, so the second caller inherits it instead of re-stating it."""
    try:
        path = sessions_csv(pkg)
        if not path.exists():
            return {}
        header, rows = read_csv_table(path, SESSIONS_COLS)
        idx = {c: i for i, c in enumerate(header)}
        if not {"seat", "ended", "session-id"} <= set(idx):
            return {}
        out = {}
        for r in rows:
            pad_row(r, header)
            seat = r[idx["seat"]].strip()
            if seat and not r[idx["ended"]].strip():
                out[seat] = r[idx["session-id"]].strip()
        return out
    except (OSError, ValueError, csv.Error):
        return {}


def undeclared_endings(pkg, last_ended=None):
    """{seat: session-id} for every seat whose LAST ENDED row DECLARES NO DISPOSITION.

    THE STATE `session_disposition` CANNOT REPORT, AND THE WHOLE REASON THIS EXISTS. That reader
    returns `None` for two states it cannot tell apart:

      (a) NOTHING ENDED — no session row, or none of this seat's rows is ended. The seat has work
          ahead of it and is a legitimate launch candidate.
      (b) A SESSION ENDED AND NOBODY DECLARED WHAT IT MEANT — the cell is empty. The seat's work
          CONCLUDED; what is missing is the assertion, not the work.

    `ready_seat_rows` read that shared `None` as "not itself finished" and offered (b) to a
    launcher as unstarted work — a seat that had already finished, re-offered as ready.

    MEASURED ON THIS RUN, 2026-08-01, against run-3's own `sessions.csv` (219 rows, 120 seats):
    three seats sat in state (b) — `briefing-collision-verifier`, `fixture-sensor-runner`,
    `leader-briefing-home-mover` — and TWO of them were in the live READY set at that instant.
    The count is a FLOOR, not a closed population: the same computation returned 4 an hour
    earlier, and one seat left the class when a later session superseded its empty cell.

    ⚠ THIS REPORTS; IT DECIDES NOTHING, AND IT NEVER MEANS `done`. An undeclared ending is a
    DEFECT FOR THE `leader` to investigate — never a relaunch, because relaunching re-runs work
    that already concluded, which is the exact harm. It is also NOT a licence for any caller to
    infer the ending: only the occupant witnessed what its session meant, and nobody else may
    assert it on the occupant's behalf (the same bound that keeps `close-seat` and `depart`
    writing an empty cell instead of a convenient one).

    `last_ended` is injectable so a caller that already read the file passes its own map instead
    of paying for a second read — `ready_seat_rows` hoists exactly one."""
    le = sessions_last_ended(pkg) if last_ended is None else last_ended
    return {seat: (sid or "(session-id unrecorded)")
            for seat, (sid, disp) in le.items() if not disp}


def session_disposition(pkg, seat):
    """The DURABLE check-out disposition of `seat`, read off its LAST ENDED session row. `None`
    when there is not one.

    ⚠ `None` MEANS UNKNOWN AND NEVER MEANS `done`, and every case that returns it is a case
    nobody declared anything in: no `sessions.csv`, no `disposition` column (a run whose header
    predates dag-09), no ended row for this seat, or the cell is empty. THE ASYMMETRY IS THE
    SAFETY ARGUMENT — `done` is the single value that advances a DAG edge, so a reader that
    guessed `done` from an absence would advance a workflow on a check-out that never happened.
    Every historical row in every existing run package carries an empty cell, so a lenient reading
    here would mark an entire run's back-catalogue as cleanly finished in one release.

    The LAST ended row wins, mirroring `session_close`'s last-open-row rule: a seat that has been
    renewed several times has several ended rows, and its CURRENT disposition is the newest one.

    Read-only, and it takes `pkg` rather than `args` deliberately — it is the durable half of the
    ready arithmetic and must be callable by anything that can name a run package, not only by a
    command with a parsed argv (PRIN-13: the boundary is what makes it reusable, and `dag-10`'s
    `terminal()` is its first caller, not its owner).

    7.237: the row selection moved OUT to `sessions_last_ended` and is not reimplemented here.
    WHAT THIS FUNCTION RETURNS DID NOT CHANGE — same row, same file order, same `or None`, and an
    empty cell still reads UNKNOWN. What changed is that `undeclared_endings` can now ask a SECOND
    question about the SAME selected row (was an ending declared AT ALL?) without a second copy of
    the selection drifting away from this one.

    `sessions.csv` is the only source. Leftover `coordination/disposition-{seat}.json` files
    (the retired EROFS interim surface) are inert."""
    _sid, cell = sessions_last_ended(pkg).get(seat) or ("", "")
    return cell or None


# ---------- per-seat statusline (task 7.69, statusline half) ----------
#
# `p-statusline-scope` ruled (b): the launch profiles write a `.claude/settings.local.json`
# carrying the statusLine block INTO EACH SEAT FOLDER at launch. Option (a) — the owner's global
# ~/.claude/settings.json — was never on the menu: it fires for every claude session on this
# machine, including the owner's own, which is not run-scoped and not a leader's to authorize.
# This code therefore writes ONLY inside a seat's own cwd and touches no file above it.
#
# WHY IT WAS BROKEN: the statusline was wired only in the vault's project-scoped
# .claude/settings.local.json, and a seat's project dir IS its seat folder — so no seat ever fired
# it. No `session-pids` record, so ctx-monitor falls back to the `transcript~` heuristic instead of
# an exact pid->transcript map, and per-session windows are guessed.
#
# THE PATH IS ABSOLUTE AND DERIVED FROM THIS FILE'S OWN LOCATION, deliberately (issue G-72). The
# vault's wiring used "$CLAUDE_PROJECT_DIR/1-projects/.../team-kit/statusline-usage.py" and has
# been DEAD for every claude session on this box since the team-kit was promoted into the rbtv
# repo on 2026-07-26 — the promotion moved the script and nothing re-pointed the pointer, and a
# statusline fails silently. Deriving it from __file__ makes the pointer move WITH the file; and
# $CLAUDE_PROJECT_DIR would resolve inside the seat folder here, which is the same trap twice.

def seat_statusline_command():
    return f"python3 {Path(__file__).resolve().parent / 'statusline-usage.py'}"


def write_seat_statusline(w):
    """Write the statusLine block into this seat's own .claude/settings.local.json. Returns
    (path, action) where action is written | merged | kept | skipped.

    MERGES rather than replaces: a seat folder's settings may carry permissions or env a seat
    depends on, and a launch profile that overwrote them would break the seat to fix its
    statusline. An existing `statusLine` is KEPT — a seat that already declares one has been
    configured deliberately, and launch is not the place to overrule it.

    Never raises into the launch path: a seat that boots without a statusline is a seat with a
    worse sensor, while a seat that fails to boot is a hole in the wave.
    """
    if w.get("harness") != "claude" or not w.get("cwd"):
        return None, "skipped"
    # THE SEAT'S OWN FOLDER, OR NOWHERE. A seat's cwd is NOT guaranteed to be its own folder:
    # discover_workers falls back to `VAULT_ROOT` for a flat briefing file that declares no `cwd:`
    # (coord.py L2838), and a seat may point `cwd:` anywhere. Writing the block at cwd would then
    # land it in the VAULT ROOT — a shared, tracked, owner-owned settings file that governs every
    # claude session started there, which is the same class of harm `p-statusline-scope` forbids
    # for ~/.claude/settings.json, wearing a different mask.
    #
    # MEASURED, NOT THEORETICAL: this is exactly what happened at 08:06 on 2026-07-27 — the
    # self-test's own flat fixture seats (alpha/beta/watcher, no folder, no cwd:) resolved to
    # VAULT_ROOT and rewrote the vault's .claude/settings.local.json statusLine. Incident #542/#545,
    # issue G-75. A path check would have caught it; an IDENTITY check makes it impossible.
    folder = w.get("folder")
    if not folder:
        return None, "skipped"
    try:
        if Path(w["cwd"]).resolve() != Path(folder).resolve():
            return None, "skipped"
    except OSError:
        return None, "skipped"
    path = Path(w["cwd"]) / ".claude" / "settings.local.json"
    block = {"type": "command", "command": seat_statusline_command()}
    try:
        data, action = {}, "written"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                data = {}
            if not isinstance(data, dict):
                data = {}
            if data.get("statusLine"):
                return path, "kept"
            action = "merged"
        data["statusLine"] = block
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, json.dumps(data, indent=2) + "\n")
        return path, action
    except OSError:
        return path, "skipped"


def load_state_snapshot(base):
    """A `state.json` snapshot as a dict, or `None` on anything short of a clean read —
    missing, unreadable, unparseable, or the wrong shape. NEVER raises.

    ONE reader (PRIN-11). Its writer, team-monitor, is deleted [T4-R8, del-observers] — every
    room now reads as a missing snapshot, permanently. Kept because its two remaining callers
    (`state_agent_types`, a refusal path in `attest_exit_blockers`) already treat `None` as their
    ordinary fail-safe direction rather than raising or inventing a value; deleting this reader
    too would mean re-deriving their own `state.json` parse, a second copy of the same read."""
    try:
        snap = json.loads((base.parent / "state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return snap if isinstance(snap, dict) else None


