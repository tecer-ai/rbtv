# ---- this module is IMPORTED, never `exec`d into `coord.py`'s namespace ----------------------
# It left `coord/` for the home `spec-component-map` §3 names, under the owner's 2026-08-25 ruling
# ("SPLIT_MODULES / coordinate split"). The move-only split loaded it by `exec` into ONE shared
# namespace; it is a real module now, so everything it did not define itself is named through the
# module that owns it.
#
# ⚠ QUALIFY — NEVER `from coord import NAME`. The selftest rebinds ~60 kit names at runtime
# (`global wake, atomic_write, ...` plus the `globals()[...]` sites), and a name copied into this
# module at import time is a SNAPSHOT: every later stub would be inert. Measured 2026-08-24 on the
# same bytes — 913 ok under a copying bind vs 1039 ok / PASS through the shared namespace. Reading
# `coord.NAME` at CALL time is what keeps a rebinding visible here.
#
# ⚠ The peer imports below are CIRCULAR by construction (`launch` <-> `attest`, `ready` <-> ...)
# and that is sound ONLY because every cross-module name is read inside a function body. A
# module-level read of a peer's attribute would break the import cycle — measure before adding one.

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import coord
import launch
import process

# ---- STAGE 3 (s3-03): the LIFECYCLE-INFLIGHT marker ------------------------------------------
# `{package}/coordination/lifecycle-inflight.json` — beside `awaiting-close.json` and
# `closing.json`, ONE SHARED FILE, a dict keyed by seat, written the way both of them are
# (`coord_lock` + `atomic_write`) and never fatal on any path.
#
# ⚠ TWO FILES NOW CARRY A `disposition` KEY OVER THE SAME done|renew VOCABULARY. THE AUTHORITY
# BETWEEN THEM IS SETTLED, AND IT IS NOT "WHICHEVER ONE THE READER OPENED":
#
#     `awaiting-close.json` is AUTHORITATIVE for INTENT/debt.
#     `lifecycle-inflight.json` is AUTHORITATIVE for EXECUTION state.
#
# The checkout ASSERTS what it meant — `set_awaiting`'s `disposition`, recorded at the one moment
# it was known — and that record is the DEBT: it deliberately never expires and `reap_blockers`
# gates a pane KILL on it. This file records what the executor has actually DONE about that
# intent: which steps verified, whether it is still running, how it ended. So a disagreement
# between the two is never a tie to be broken — read the intent from awaiting-close.json and the
# progress from here. Read the G-134 AWAITING-CLOSE DEBT block above (`awaiting_path` /
# `load_awaiting` / `set_awaiting` / `reap_blockers`) for the design this half is bound to; it is
# POINTED AT, never restated.
#
# Two of that block's rulings carry over unchanged, and are likewise pointed at rather than
# re-argued:
#   · "An assertion at the moment of truth beats an inference at the moment of action" — which is
#     why `steps-completed` is appended AFTER a step VERIFIES, never before. A step listed here
#     HAPPENED; no reader may have to wonder whether it merely started. `stamp_lifecycle` starts
#     the list EMPTY for exactly that reason.
#   · "A debt that ages out unpaid is not a debt" — which is why a finished renewal FLIPS to
#     `state: "done"` instead of being deleted. Deleting it would erase the only record that a
#     renewal happened OUT OF PANE, where nothing else saw it. `close-run` sweeps the done
#     entries (`sweep_lifecycle`) and nothing else may.
#
# The per-seat record:
#
#     {"engineer": {"disposition": "renew",
#                   "executor": {"pid": 41207, "starttime": "884231"},
#                   "caller":   {"pid": 41190, "starttime": "884118"},
#                   "pane": "%37", "tmux-target": "%37",
#                   "stamped-at": "2026-07-28 16:04",
#                   "steps-completed": ["caller-exited", "in-place-decided:in-place", "respawned"],
#                   "state": "in-flight", "failure": ""}}
#
# `stamped-at` goes through `now()` AND NOWHERE ELSE — the store writes it itself and overwrites
# whatever a caller supplies, so the package keeps ONE date format and `lifecycle_age_min` below
# reads it with `closing_age_min`'s arithmetic unchanged. (It cannot CALL `closing_age_min`: that
# one reads the key `since`, which is the closing record's name for the same thing.)
#
# `executor`/`caller` are normalized to `{"pid": int, "starttime": str}` at the boundary, and that
# is not tidiness. watch.py's revival detector reads `entry["executor"]["pid"]` and
# `["starttime"]` and answers False for ANY other shape, so a `(pid, starttime)` TUPLE written
# straight through would make every LIVE executor read as dead — turning MID-RENEWAL into CRASHED
# and double-launching the seat, which is the one outcome stages 3 and 4 both exist to prevent.

# HOW FAR A HONEST TRANSCRIPT MAY PRE-DATE THE ENDING ROW THAT POINTS AT IT (step 7).
#
# It is not a fudge factor: `cmd_checkout` EXPORTS the transcript and only afterwards stamps the
# ending whose `evidence_pointer` names it, so a correct transcript is ALWAYS older than its own
# record — by the length of the check-out's remaining bookkeeping (the roster flip, a call-2
# handoff write, the ledger close). Below this bound is that ordering; above it is an export from
# an EARLIER session of the same seat, which is what step 7 exists to catch.
#
# ⚠ IT IS 60s BECAUSE THAT IS WHAT THE PREDECESSOR ALREADY FORGAVE, not because a minute was
# measured. The old check compared minute-truncated local strings, so it tolerated anything up to
# a whole minute; naming the same bound keeps this a clock repair and not a silent loosening.
TRANSCRIPT_PRECEDES_STAMP_SLACK_S = 60


def ending_transcript(row):
    """The transcript path an ending row points at, or '' when no export landed.

    spec-state-store §1.2 makes `evidence_pointer` REQUIRED and non-empty, so a checkout whose
    transcript export never landed (`--no-export`, or a pane that died before the capture) still
    points AT something — `cmd_checkout` falls back to a `checkout:<seat>` token. So "was a
    transcript exported" is answerable from the pointer alone, and the discriminator is that a
    transcript pointer is an ABSOLUTE PATH: `export_transcript` returns one, under the package's
    own transcripts folder, while every `<kind>:<seat>` fallback the kit stamps is not.

    ⚠ TESTED AS A PATH, NEVER STRING-MATCHED AGAINST THE FALLBACK'S SPELLING. This reader is one
    file away from that writer; matching its literal would make a fallback nobody thought to grep
    for read as a live transcript path, which is the failure this whole step guards against."""
    ev = str((row or {}).get("evidence_pointer") or "")
    return ev if ev and Path(ev).is_absolute() else ""


def lifecycle_path(base):
    return Path(base) / "lifecycle-inflight.json"


def lifecycle_ident(ident):
    """`{"pid": int, "starttime": str}` from a `(pid, starttime)` tuple, an already-shaped dict, or
    anything else. `{}` when nothing resolves — NEVER a raise and never a partial dict: this runs
    inside a marker write, and bookkeeping ABOUT a lifecycle act must not break the act.

    `{}` rather than a pid-only dict on purpose. A pid ALONE is not an identity (`process_identity`
    carries the reason at length: the kernel recycles pids and a teardown is exactly when new
    processes start), and a half-identity here would be read as a live executor by a reader that
    only checked the key's presence."""
    if isinstance(ident, dict):
        pid, start = ident.get("pid"), ident.get("starttime")
    elif isinstance(ident, (tuple, list)) and len(ident) == 2:
        pid, start = ident
    else:
        return {}
    if pid is None or start is None or str(start) == "":
        return {}
    try:
        return {"pid": int(pid), "starttime": str(start)}
    except (TypeError, ValueError):
        return {}


def load_lifecycle(base):
    """{seat: record} — the marker as it stands, `{}` on ANY read or parse failure. NEVER raises.

    Same never-fatal contract as `load_awaiting`, and the same fail-safe direction: a marker that
    cannot be read must not take down the renewal it is bookkeeping for. A consumer reads
    `entry.get("disposition", "")` and NEVER `entry["disposition"]` — the blank is not `done`, it
    is "the executor recorded no intent here", and the INTENT is awaiting-close.json's to state."""
    path = lifecycle_path(base)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_lifecycle(base, data):
    coord.atomic_write(lifecycle_path(base), json.dumps(data, indent=2, sort_keys=True) + "\n")


def stamp_lifecycle(base, seat, record):
    """Write `seat`'s INITIAL record. Returns True/False, NEVER raises.

    Best-effort for `set_awaiting`'s reason one file over: the caller checks the return and SAYS
    SO when it is False; it does not abandon a renewal over an unwritten marker.

    THE STORE OWNS FOUR FIELDS and overwrites whatever the caller passed for them:
      `stamped-at`      -> `now()`, always (one date format in the package).
      `state`           -> `"in-flight"`, always. A stamp IS the start; only `finish_lifecycle`
                           writes a terminal state, so no caller can stamp a renewal as finished.
      `steps-completed` -> `[]`, always. A caller able to pre-load it could claim a step before it
                           ran — the exact inversion the G-134 block rules against.
      `executor`/`caller` -> normalized through `lifecycle_ident` (see the block above).
    Every other key the caller supplies is carried through unchanged."""
    try:
        rec = dict(record or {})
        for k in ("executor", "caller"):
            if k in rec:
                rec[k] = lifecycle_ident(rec[k])
        rec["disposition"] = str(rec.get("disposition") or "")
        rec["failure"] = str(rec.get("failure") or "")
        rec["state"] = "in-flight"
        rec["steps-completed"] = []
        rec["stamped-at"] = coord.now()
        with coord.coord_lock(base):
            data = load_lifecycle(base)
            data[seat] = rec
            _write_lifecycle(base, data)
        return True
    except (OSError, ValueError, TypeError):
        return False


def append_lifecycle_step(base, seat, step):
    """Append ONE verified step to `seat`'s `steps-completed`. Returns True/False, never raises.

    A step can only FOLLOW a stamp: an entry that does not exist is answered False rather than
    created. A step appended to nothing would be a claim about a renewal this file never saw
    start, and the caller must learn that immediately rather than read it back later as history."""
    try:
        with coord.coord_lock(base):
            data = load_lifecycle(base)
            entry = data.get(seat)
            if not isinstance(entry, dict):
                return False
            prior = entry.get("steps-completed")
            entry["steps-completed"] = ([str(s) for s in prior] if isinstance(prior, list)
                                        else []) + [str(step)]
            data[seat] = entry
            _write_lifecycle(base, data)
        return True
    except (OSError, ValueError, TypeError):
        return False


def finish_lifecycle(base, seat, state, failure=""):
    """Terminal write: `state` is `"done"` or `"FAILED"`, `failure` carries the text of the break.
    Returns True/False, never raises.

    ANY OTHER `state` IS REFUSED (False) rather than written. The sweep in `sweep_lifecycle` keys
    on these two strings exactly, so a third value would silently become an entry nothing ever
    clears and nothing ever reads as a failure.

    The entry is NOT deleted here — see the block above. `close-run` is the only sweep."""
    if state not in ("done", "FAILED"):
        return False
    try:
        with coord.coord_lock(base):
            data = load_lifecycle(base)
            entry = data.get(seat)
            if not isinstance(entry, dict):
                return False
            entry["state"] = str(state)
            entry["failure"] = str(failure or "")
            data[seat] = entry
            _write_lifecycle(base, data)
        return True
    except (OSError, ValueError, TypeError):
        return False


def clear_lifecycle(base, seat):
    """Remove ONE seat's entry. Returns True when one was actually removed.

    ⚠ RUN TEARDOWN ONLY — `sweep_lifecycle` (called from the finish edge, `cmd_finish_goal`, since
    `close-run` was deleted) is its ONE caller. NEVER
    called on success: a successful renewal FLIPS to `state: "done"` via `finish_lifecycle`, and
    deleting it there would erase the only record that the renewal happened out of pane."""
    try:
        with coord.coord_lock(base):
            data = load_lifecycle(base)
            if seat not in data:
                return False
            del data[seat]
            _write_lifecycle(base, data)
        return True
    except (OSError, ValueError, TypeError):
        return False


def lifecycle_age_min(entry, now_str=None):
    """Minutes since `stamped-at`, or None when the stamp is unreadable.

    `closing_age_min`'s arithmetic and `closing_age_min`'s format, deliberately — but not
    `closing_age_min` itself, which reads the key `since`. `now_str` (same `"%Y-%m-%d %H:%M"`
    form) lets a caller or a check supply the reference instant instead of sleeping for it."""
    try:
        ref = (datetime.strptime(str(now_str).strip(), "%Y-%m-%d %H:%M") if now_str
               else datetime.now())
        return max(0, int((ref - datetime.strptime((entry or {}).get("stamped-at", "").strip(),
                                                   "%Y-%m-%d %H:%M")).total_seconds() // 60))
    except (ValueError, AttributeError, TypeError):
        return None


def lifecycle_stale(entry, now_str=None):
    """THE FAILED-RENEWAL PREDICATE. True only when ALL THREE hold:

        1. `entry["state"] == "in-flight"`, AND
        2. the age of `stamped-at` exceeds `LIFECYCLE_STALE_MIN`, AND
        3. the executor ident is NOT live, by `ident_is_live_process`.

    ⚠⚠ READ THE COMPLEMENT, BECAUSE THE COMPLEMENT IS WHAT STAGE 4 ACTS ON: an entry that is
    `in-flight` WITH A LIVE EXECUTOR IS **MID-RENEWAL** — a renewal in progress, which must NEVER
    be fired on. Getting this one reading backwards turns MID-RENEWAL into CRASHED and
    DOUBLE-LAUNCHES A SEAT, which is the failure this whole predicate exists to make impossible.

    ⚠ CONJUNCT 3 IS `ident_is_live_process`, NEVER `ident_is_live_harness`. The executor is a
    PYTHON process; `ident_is_live_harness` rests on `is_harness_argv`, which matches only the
    claude/codex/opencode basenames in HARNESS_PROCS, so it reports EVERY LIVE EXECUTOR AS DEAD
    and this predicate would fire on healthy renewals. `ident_is_live_process`'s own docstring
    states the trap; the two are separate functions with separate names precisely so this line
    cannot be written by accident.

    FAIL-SAFE DIRECTION IS "NOT STALE". An unreadable stamp, a missing or malformed `executor`
    ident, a non-dict entry — every unprovable case answers False. Firing wrongly revives a seat
    that is alive (a double launch); declining wrongly leaves a stuck seat stuck AND REPORTED,
    which is recoverable. ⚑ The cost of that direction is real and is stated rather than hidden:
    an `in-flight` entry with no readable executor ident is stale to a human and False here
    forever — `sweep_lifecycle` will not clear it either, so it survives every close-run and is
    NAMED in each one's output. That visibility is the remedy; silence would not be."""
    if not isinstance(entry, dict) or entry.get("state") != "in-flight":
        return False
    age = lifecycle_age_min(entry, now_str)
    if age is None or age <= process.LIFECYCLE_STALE_MIN:
        return False
    ident = lifecycle_ident(entry.get("executor"))
    if not ident:
        return False
    return not process.ident_is_live_process((ident["pid"], ident["starttime"]))


# ---------- THE RENEW GATE: `renew` is not a failure, and "no successor" is not silence ---------
#
# A seat that checks out `--renew` is saying "I am coming back; my successor is pending". Every
# `after` gate read that as a crash — `ready_seat_rows` gave it the same `DONE` verdict `exited`
# gets, and `goal-watcher-job.py`'s shadow backstop decided WOULD-ENQUEUE in FAILURE MODE off the
# same equality. Measured on the forge instance 2026-08-18: a paneless seat declared `--renew`, no
# successor could be forked, and its dependents were held exactly as if it had died, with nothing
# in any surface distinguishing "coming back" from "gone".
#
# TWO STATES, AND THEY ARE DISTINGUISHABLE FROM EACH OTHER AND FROM FAILURE:
#   `successor-pending` — a successor is coming or has been placed. IN PROGRESS. It advances NO
#       edge (the work genuinely is not finished, and `after_member_state` still reads the raw
#       `renew` value, which is not `done`), but it is NOT the failure class: it routes to no
#       leader as a crash and it reads as an ending nobody ruled on nowhere.
#   `no-successor`      — no successor is possible. A REAL HALT, and it must LOOK like one, with a
#       reason a reader can act on.
#
# THE SIGNAL IS `paneless-renew`'s (commit ea56f75c) AND THERE IS NO SECOND ONE: the seat's entry
# in `coordination/lifecycle-inflight.json`, which `fork_lifecycle_renewal` stamps on the way in
# and `lifecycle_no_successor` flips FAILED on every arm that forks nothing.
#
# ⚠ AN ABSENT ENTRY IS `no-successor`, NOT `successor-pending`. `renew` on the durable record with
# no marker at all means the renewal never got as far as stamping — which is precisely the forge
# shape before `lifecycle_no_successor` existed. The fail-safe direction here is the LOUD one: a
# wrongly-loud row costs a reader one look, a wrongly-quiet one costs the lineage.
#
# ⚠ IT DOES NOT BECOME ABSORBING, and the two arms answer that differently because they are
# different claims. `in-flight` is bounded by `lifecycle_stale` — the executor died or the stamp
# aged past `LIFECYCLE_STALE_MIN` and the row flips to `no-successor` on its own, in TIME. `done`
# means the successor was PLACED, and its pendency is then superseded by the successor's OWN
# session row: the moment that session ends, `terminal_disposition` stops reading `renew` at all
# and this classifier is never consulted again. A successor that was placed and never opened a row
# is `undeclared_endings`' subject, not this one's.
RENEW_PENDING = "successor-pending"
RENEW_NO_SUCCESSOR = "no-successor"


def renewal_from_entry(entry, now_str=None):
    """(state, why) for a seat whose durable disposition is `renew`, off its lifecycle entry.

    NOT PURE, and saying so matters: the `in-flight` arms below reach `lifecycle_stale`, which
    reads `/proc` for the executor's liveness. Everything else is a function of the entry and a
    reference instant. `now_str` (the `"%Y-%m-%d %H:%M"` form `lifecycle_age_min` takes) lets a
    check supply the instant instead of sleeping for it. NEVER raises: every unreadable shape
    answers `no-successor` with a `why` that says what was actually found."""
    if not isinstance(entry, dict):
        return RENEW_NO_SUCCESSOR, ("no `lifecycle-inflight.json` entry — this seat's renewal "
                                    "never recorded a start, so no successor was ever forked")
    disposition, state = entry.get("disposition", ""), entry.get("state")
    if disposition != "renew":
        return RENEW_NO_SUCCESSOR, (
            f"its lifecycle entry records disposition `{disposition or '(none)'}`, not `renew` — "
            f"the marker is about a different act and asserts no successor for this check-out")
    if state == "FAILED":
        return RENEW_NO_SUCCESSOR, (entry.get("failure")
                                    or "its lifecycle entry is FAILED with no reason recorded")
    if state == "done":
        return RENEW_PENDING, ("its lifecycle entry is `done` — the successor was PLACED. It "
                               "reports through its own session row from here")
    if state != "in-flight":
        return RENEW_NO_SUCCESSOR, (
            f"its lifecycle entry carries the unenumerated state `{state or '(none)'}` — only "
            f"`in-flight`, `done` and `FAILED` are written, so nothing here reads it as a "
            f"successor")
    if lifecycle_stale(entry, now_str):
        _age = lifecycle_age_min(entry, now_str)
        return RENEW_NO_SUCCESSOR, (
            f"its lifecycle entry is STILL `in-flight` {_age}min after the stamp (bound "
            f"{process.LIFECYCLE_STALE_MIN}min) and its executor is NOT a live process — the fork never "
            f"completed and no successor is coming")
    _age = lifecycle_age_min(entry, now_str)
    # ⚠ THE ARM THAT KEEPS `successor-pending` FROM BEING ABSORBING, and `lifecycle_stale` cannot
    # be it. That predicate needs a READABLE executor ident (its conjunct 3) and answers False
    # without one FOREVER — its own docstring states that cost and accepts it, because firing the
    # REVIVAL actuator on an unprovable case double-launches a seat. This classifier decides the
    # opposite question with the opposite fail-safe: `fork_lifecycle_renewal` stamps `caller` and
    # deliberately NO `executor` (the child writes its own pair as its first act), so an entry
    # still identless well past the bound is a child that never announced itself — nothing is
    # coming, and a reader who is told `successor-pending` waits forever. Aged out, said out loud.
    if _age is not None and _age > process.LIFECYCLE_STALE_MIN and not lifecycle_ident(
            entry.get("executor")):
        return RENEW_NO_SUCCESSOR, (
            f"its lifecycle entry is STILL `in-flight` {_age}min after the stamp (bound "
            f"{process.LIFECYCLE_STALE_MIN}min) and NO EXECUTOR EVER RECORDED ITSELF — the detached "
            f"executor writes its own pid pair as its first act, so a marker this old without one "
            f"names a fork that never got that far. No successor is coming")
    return RENEW_PENDING, (
        f"its lifecycle entry is `in-flight`, stamped "
        f"{str(_age) + 'min ago' if _age is not None else 'unreadably'} — a successor IS being "
        f"forked. It flips to `no-successor` on its own once the stamp ages past "
        f"{process.LIFECYCLE_STALE_MIN}min with a dead executor — or with none ever recorded")


def renewal_state(base, seat, now_str=None, lifecycle=None):
    """(state, why) — `renewal_from_entry` against the marker on disk. THE ONE READER of the
    successor-pending signal: `ready_seat_rows` here, and `operator/attached-execution.js` on the JS
    side, transported through the `renewal-state` verb rather than re-deriving it. Two gates
    re-deriving one seat's state from one file is how they come to disagree about it.

    `lifecycle` lets a caller that already loaded the marker (`ready_seat_rows` hoists it once for
    N seats) spend that read instead of making a second one."""
    return renewal_from_entry(
        (load_lifecycle(base) if lifecycle is None else lifecycle).get(seat), now_str)


def sweep_lifecycle(base):
    """The finish edge's (`cmd_finish_goal`) marker sweep — moved here from the deleted `close-run`
    (7.607 E2b) when runs were extinguished and closed with `close-run`'s register. Returns
    `(cleared, survivors)`: `cleared` is the sorted seats
    removed, `survivors` is `[(seat, why)]` for every entry this REFUSES to touch. Never fatal —
    a run stays closable with an unreadable marker, which reads as no entries at all.

    ⚠ ONLY `state: "done"` IS SWEPT, and every survivor is NAMED by the caller. An `in-flight`
    entry is a renewal that never reported an ending, and clearing it would destroy the one record
    saying so at the exact moment the run closes and nobody looks again; a `FAILED` entry IS the
    failure report. An entry left behind SILENTLY is indistinguishable from one never written,
    which is the G-134 block's own argument for writing the record rather than re-deriving it."""
    cleared, survivors = [], []
    snapshot = load_lifecycle(base)
    for seat in sorted(snapshot):
        entry = snapshot.get(seat)
        state = entry.get("state") if isinstance(entry, dict) else None
        if state == "done":
            if clear_lifecycle(base, seat):
                cleared.append(seat)
            else:
                survivors.append((seat, "its entry is complete but the marker write FAILED, so "
                                        "nothing was cleared"))
        elif state == "in-flight":
            age = lifecycle_age_min(entry)
            survivors.append((seat, f"state=in-flight, stamped "
                                    f"{str(age) + 'min ago' if age is not None else 'unreadably'}"
                                    f" — a renewal that never reported an ending; this entry is "
                                    f"the only record that it started"))
        elif state == "FAILED":
            survivors.append((seat, f"state=FAILED: "
                                    f"{(entry.get('failure') or '').strip() or '(no failure text)'}"
                                    f" — the failure report outlives the run"))
        else:
            survivors.append((seat, f"state={state!r} is not a state this store writes — left "
                                    f"untouched rather than guessed at"))
    return cleared, survivors


def lifecycle_line(base):
    """The marker's READ SIDE: one block for the `status` and `workers` views, or `''` when the
    marker holds nothing an operator must act on.

    `undelivered_line`'s shape exactly — same `(base)` signature, same "a string or empty"
    contract, same never-fatal posture — because it exists for the same reason and has to be
    ignorable in the same way.

    ⚠ WITHOUT THIS FUNCTION THE MARKER IS WRITE-ONLY. `stamp_lifecycle` records every renewal that
    runs OUT OF PANE and, until Stage 4's revival arm lands, NOTHING READS IT. That is precisely
    the shape `undelivered_flags` documents one screen up: warnings "printed to a detached stderr
    file, and lost, while the loop went on reporting healthy". A marker nobody looks at is not a
    fix, and a step that can fail must fail LOUDLY AND VISIBLY.

    THREE CLASSES ARE REPORTED. The first two are the alarm; the third is not padding:

      STALE    `lifecycle_stale(entry)` — in-flight, past `LIFECYCLE_STALE_MIN`, executor NOT live.
               ⚠⚠ THE COMPLEMENT IS NEVER REPORTED: an in-flight entry with a LIVE executor is
               MID-RENEWAL, a renewal in progress. Reporting it would train the room to scroll
               past this line on the one night it is real — and the predicate is CALLED, never
               re-spelled, so this surface and Stage 4 can never hold two definitions of stale.
      FAILED   `state == "FAILED"`. NOT stale — it is young and its executor is legitimately gone —
               but it IS an alarm: the executor itself reported that the renewal broke.
      UNKNOWN  any other `state`. The store writes exactly `in-flight|done|FAILED`
               (`finish_lifecycle` refuses anything else), so a fourth value means the file was
               HAND-EDITED — and `sweep_lifecycle` will not clear it either, so it survives every
               close-run. Named here for `sweep_lifecycle`'s own reason: an entry left behind
               SILENTLY is indistinguishable from one never written.

    `state: "done"` is the only class deliberately silent. A completed renewal is not news.

    ⚠ AGES COME FROM `lifecycle_age_min`, NEVER `closing_age_min`. That one reads the key `since`;
    this record stamps `stamped-at`, so `closing_age_min` returns None on every entry here —
    silently — and every age would render as unknown while the line still looked correct.

    ⚠ `disposition` is read with a `""` DEFAULT, never `load_awaiting`'s `"done"`. A blank means
    the executor recorded no intent in THIS file, and the intent is `awaiting-close.json`'s to
    state — so the line SAYS to read it there rather than inventing `done`. What this line reports
    is EXECUTION state; the authority split between the two files is stated in full at the head of
    this section and is not restated here.

    NOT A REFUSAL, so it carries no `refuse()` layer token: this is display output, rendered by
    its two callers in `C_DEAD` — the constant `undelivered_line` is already rendered in. A
    rendered alarm an operator can act on is not a tool-gate verdict.

    The remedy is named in plain words because a reader who has never seen this line before is
    exactly the reader it is for: Stage 4's revival arm will act on it automatically once it
    lands; until then a leader must run `close-seat <seat> --renew` by hand. No `coord_invocation`
    prefix — the signature takes `base` alone (`undelivered_line`'s, deliberately) and no `args`
    is in scope to resolve one from."""
    entries = load_lifecycle(base)
    if not isinstance(entries, dict) or not entries:
        return ""
    rows = []
    for seat in sorted(entries):
        entry = entries.get(seat)
        if not isinstance(entry, dict):
            rows.append(f"  UNKNOWN {seat} — its entry is not a record but a "
                        f"{type(entry).__name__}; the file was hand-edited and no sweep will "
                        f"clear it")
            continue
        state = entry.get("state")
        if state == "done":
            continue
        if state == "in-flight" and not lifecycle_stale(entry):
            continue        # MID-RENEWAL, or too young to judge. Never fire on it.
        age = lifecycle_age_min(entry)
        aged = f"marker {age}min old" if age is not None else "marker of UNREADABLE age"
        disp = entry.get("disposition", "")
        disp_txt = (f"disposition={disp}" if disp else
                    "disposition NOT recorded here — read the intent from awaiting-close.json")
        ident = lifecycle_ident(entry.get("executor"))
        who = f"executor pid {ident['pid']}" if ident else "NO readable executor ident"
        steps = entry.get("steps-completed")
        steps = [str(s) for s in steps] if isinstance(steps, list) else []
        last = f"last verified step: {steps[-1]}" if steps else "NO step ever verified"
        if state == "FAILED":
            rows.append(f"  FAILED  {seat} — {disp_txt}; {who}; {aged}; {last} — the executor "
                        f"reported the break: "
                        f"{(str(entry.get('failure') or '').strip() or '(no failure text)')}")
        elif state == "in-flight":
            rows.append(f"  STALE   {seat} — {disp_txt}; {who}, and it is NOT running; {aged}; "
                        f"{last}")
        else:
            rows.append(f"  UNKNOWN {seat} — state={state!r} is not a state this store writes, so "
                        f"this file was hand-edited; {disp_txt}; {who}; {aged}; {last}. close-run "
                        f"will not sweep it either")
    if not rows:
        return ""
    return ("LIFECYCLE MARKERS IN ALARM: %d — a renewal ran OUT OF PANE and never reported a clean "
            # number-neutral on purpose: the block lists one entry or ten, and a header that says
            # "the seat below" reads as a lie the moment there are two.
            "ending. In plain words: EACH SEAT NAMED BELOW IS NEITHER ALIVE NOR CLOSED — nothing "
            "is running it, nothing has freed its pane, and it will not recover on its own.\n"
            "%s\n"
            "  Remedy: Stage 4's revival arm will act on this automatically once it lands. UNTIL "
            "THEN the remedy is manual — a leader runs `close-seat <seat> --renew`.\n"
            "  Read them all: %s"
            % (len(rows), "\n".join(rows), lifecycle_path(base)))


# ---- STAGE 3 (s3-05): the hidden `lifecycle-exec` subcommand and its FIVE ENTRY GUARDS --------
#
# WHAT RUNS HERE. `lifecycle-exec` is the DETACHED LIFECYCLE EXECUTOR's entry point: a fresh
# subprocess the caller forks (`s3-09`) so a seat's session rotation is carried OUT OF the pane
# that is dying. It is PURE CODE — there is no agent anywhere in this path — and it holds NO SEAT
# IDENTITY: it never calls `resolve_agent`, never calls `gate`, never calls `launch_gates`. There
# is no per-verb role gate anymore in this file at all [T2-R10, D24, F-simplicity-7]; this
# executor still holds no seat identity by construction, and still needs its own retry-shaped
# memory pre-flight (`lifecycle_memory_gate`) rather than `launch_gates`' hard exit. Ruled bound
# this realizes (`d-cos-may-launch`): the chief-of-staff may OPEN a
# session and may NEVER close, renew, reap, kill or revive one — every terminating act belongs to
# this executor and to Stage 4's revival arm, and nothing here gives any agent a new path to
# terminate a session.
#
# ⚠ IT WAS NEVER A CLOSER, AND MUST NEVER BE DESCRIBED AS ONE. `closer` was a settled term of the
# rbtv system definition (`sd-graph show closer`; `concepts/closer.md`, settled by
# `system-definition/decisions.md#d-agent-taxonomy`): a closer was a STAFF AGENT, spawned when a
# seat crossed its ctx-refresh threshold, that MESSAGED the seat and NEGOTIATED the handoff,
# landing the close at a turn boundary. Nothing here messages anybody, negotiates anything, or is
# an agent. The closer machinery was untouched by this whole stage when it was written (spec §
# Ruled, owner, design doc D7: the closer stays as-is, failure-path only, ZERO code change) — that
# ruling was superseded and the `closer-*` seat class (spawned by the now-deleted `close` verb) was
# deleted whole under [T2-R9], "only the daemon acts on other seats". This executor's distinction
# from a closer stands regardless: it still never messages, negotiates, or holds a seat identity.
#
# WHY IT LIVES INSIDE coord.py RATHER THAN AS A SIBLING MODULE (settled — do not "simplify" it
# out). `save-coord.py` gates coord.py ONLY, and it gates by IMPORTING the candidate AND running
# `python3 <candidate> --help`, i.e. by BUILDING THE FULL PARSER TREE including every subparser.
# A subparser registered here is therefore build-verified by the one gate this room already runs
# on every save. A sibling `lifecycle_exec.py` would get NO gate, would have to `import coord`
# anyway — inheriting coord's blast radius without its gate — and would be discovered broken at
# 04:00, detached and out of pane. Accepted cost: coord.py grows. Counterweight: the executor is a
# FRESH SUBPROCESS every time, so it always reads the current coord.py and can never hold the
# stale import surface that drifted four commits under a running loop (`watch.py:105-112`).
#
# NO POLICY NUMBER CROSSES THIS BOUNDARY (R-10, `r-floor-single-source`): argv is a copy, a file
# is a reference. The RAM floor is READ from the run's `budget.json` by the gate that needs it
# (`s3-06`), never received as a flag here.

# The four variables an inherited environment can use to make this process act as somebody else.
# Popped at ENTRY, even though `s3-09`'s caller also scrubs them in the `env=` it hands `Popen`.
# Doing it TWICE is deliberate: an executor that trusts its caller's scrub inherits whatever a
# FUTURE caller forgets. Each consequence below is MEASURED, not hypothetical:
#   TMUX / TMUX_PANE     watch.py's detached loop inherited TMUX_PANE from the shell that started
#                        it, and every send was refused with "you claimed 'watcher', but this pane
#                        (%145) is registered to 'chief-of-staff'" (`watch.py:962-972`).
#   COORD_AGENT          injected into every launched seat's harness command, so an executor
#                        forked out of a dying seat would resolve AS THE DYING SEAT.
#   COORD_LAUNCH_TARGET  `cmd_close_seat` resolves its target as
#                        `COORD_LAUNCH_TARGET or TMUX_PANE`. This executor MUST NOT inherit that
#                        fallback — the hazard is spelled out on `lifecycle_target_live`.
LIFECYCLE_SCRUB_ENV = ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET")

# THE ARGV VOCABULARY — executor-side ACTIONS, and the parser's `--disposition` choices are read
# FROM HERE so the two can never disagree.
#
# ⚠ `revive` LANDED WITH `s3-07`. It is the CRASH arm: no checkout preceded it, so it carries no
# awaiting-close record, no stamped handoff block and a caller that DIED rather than forked. It
# runs the `renew` sequence — the same body, gated on `LIFECYCLE_RELAUNCHING` below — and the two
# places it diverges are NAMED at their sites, never forked into a second implementation.
# (`dag-08` widens this enum a THIRD time; what a fourth value must touch is on
# `LIFECYCLE_RELAUNCHING` and `LIFECYCLE_INTENT_OF`, both immediately below.)
LIFECYCLE_DISPOSITIONS = ("renew", "close", "revive")

# WHICH DISPOSITIONS PUT A SUCCESSOR BACK. `close` tears down and stops; `renew` and `revive` both
# relaunch. ONE home for that fact, because `run_lifecycle_sequence` gates its whole relaunch half
# on it — the descriptor lookup, the binding check, the in-place decision, the RAM gate, the
# relaunch and the successor-alive verification. A NEW DISPOSITION DECLARES ITS SIDE HERE, in a
# line a reader can find, instead of by editing a boolean buried three hundred lines down.
LIFECYCLE_RELAUNCHING = ("renew", "revive")

# GUARD 4'S MAPPING, and the reason guard 4 is a MAPPING rather than a string comparison.
#
# The disposition is DECLARED ONCE at checkout, in `awaiting-close.json` (`s12-07`,
# `stage-1-2-gate-checkout-spec.md` §2.3) — the moment of truth — and CARRIED into
# `lifecycle-inflight.json` as the execution copy. Authority between the two files is settled and
# is stated ONCE, at the head of the marker-store section above: awaiting-close.json is
# authoritative for INTENT/debt, lifecycle-inflight.json for EXECUTION state. It is POINTED AT
# here, never restated — a second copy of an authority statement is a second copy to drift.
#
# ⚠⚠ THE TWO SIDES SPEAK TWO VOCABULARIES WITH NO SHARED VALUE. argv is `renew|close|revive`
# (executor ACTIONS); the awaiting-close record is `done|renew` (checkout INTENTS, s12-07's mint).
# A plain done-checkout writes `done` and forks `--disposition close` — so A RAW-EQUALITY GUARD
# REFUSES THE NORMAL PATH, the single most common invocation this executor will ever see. That is
# why the comparison goes through this dict and why the suite carries a row for exactly that shape.
#
# `LIFECYCLE_INTENT_ABSENT` means "no checkout happened, so NO awaiting-close record may exist" —
# legal for `revive` ONLY (s3-07), and the executor derives ONE more fact from it: `checked_out` in
# `run_lifecycle_sequence` is READ OFF THIS MAPPING rather than off a second list of disposition
# names, so the step that needs a checkout to have happened and the guard that forbids its record
# can never hold two opinions about which dispositions had one.
# The in-suite row "THE ENUM AND THE MAPPING CANNOT DRIFT" fails if only one of the two is widened.
# ⚠ EACH NON-ABSENT VALUE IS A TUPLE OF ADMITTED INTENTS, NOT ONE STRING (7.676). It was one
# string until `incomplete` landed, and the shape changed for a reason a reader must not have to
# reconstruct: ONE ARGV ACTION NOW CORRESPONDS TO TWO LEGAL CHECKOUT INTENTS. `close` is the
# executor's teardown sequence, and BOTH a finished seat (`done`) and a seat that declared itself
# unfinished (`incomplete`) are torn down by it — they differ in what the DAG may conclude, which
# is the RECORD's business, and not at all in what the executor must DO, which is this table's.
# Left as a string, guard 4 would have refused every close of an honestly-incomplete seat as
# DISPOSITION SKEW — making the honest ending unclosable and teaching every seat to lie again.
# A tuple of one is still a bound of one: `renew` admits exactly what it admitted before.
LIFECYCLE_INTENT_ABSENT = None
LIFECYCLE_INTENT_OF = {"close": ("done", "incomplete"), "renew": ("renew",),
                       "revive": LIFECYCLE_INTENT_ABSENT}


# ---- STAGE 3 (s3-08): THE BUS ALARM — the one surface an executor failure reaches a human on --
#
# ⚠ THE LOG IS EVIDENCE, NEVER THE ALARM. Everything `lifecycle_alarm` prints lands on THIS
# process's INHERITED stderr — the file `s3-09` opens, detached from every pane, that nobody is
# watching at 04:00. watch.py's recorded failure IS that shape, and `undelivered_flags`' own
# docstring one screen up spells it out: warnings "computed correctly, refused correctly, printed
# to a detached stderr file, and lost, while the loop went on reporting healthy. Silence and health
# were indistinguishable at exactly the wrong place." R-8 is explicit that a refused act reporting
# nothing is worse than no act, so every refusal is ALSO raised WHERE THE RUN LOOKS, in three
# steps, each one the fallback for the previous one failing:
#
#   1. MARKER   `finish_lifecycle(base, seat, "FAILED", failure)` — the DURABLE record, written
#               BEFORE the perishable one and read back INTO the alarm body, so the note can never
#               report a state the disk does not hold (R-7: a fact recorded only in a perishable
#               surface is not recorded).
#   2. BUS      ONE `type: note` from the machinery identity `lifecycle-exec`, sent IN-PROCESS
#               through `cmd_send` with a hand-built Namespace — watch.py's `notify_leader`
#               precedent (watch.py:957-985), field for field.
#   3. FLAG     on ANY refusal from that send, an append to `{base}/undelivered-flags.md` — the
#               file `undelivered_flags` reads and `undelivered_line` surfaces through `status` and
#               `workers`. Deliberately NOT a coord message: this reports that the MESSAGING LAYER
#               refused something, so routing it back through that layer is the one path guaranteed
#               to fail the same way.
#   …and when even the append fails, a last-resort PRINT. A monitor that cannot deliver must SHOUT
#   that it cannot deliver.
#
# WHAT THIS IS NOT: one loud message per failure and nothing else. No retry, no second recipient,
# no escalation policy — who is woken, how often, and what happens when nobody answers is Stage
# 4's, and this file must not grow a private copy of it. No memory machinery of any kind (R-14).

# THE RECIPIENT IS RESOLVED FROM THE PACKAGE, NEVER ASSUMED. `leader` is the ROLE WORD this file
# uses for the leader seat (no role-gate predicate names it anymore [T2-R10, D24, F-simplicity-7],
# but the seat name itself is still `leader` by convention), not a seat name typed here:
# it is offered to `known_recipients` — the SAME predicate `cmd_send` validates `--to` against — and
# admitted only when THIS package carries a roster row, a briefing, a group, a RELAY TOKEN or an
# addressable non-member of that name. A run that renames its leader seat declares
# `relays: leader` on the successor and this follows it with no code change (run-2 renamed
# `owner-liaison` -> `master` mid-run, so this is not hypothetical); a run that does neither gets
# the undelivered flag WITH THE REASON, never a send into a name nobody holds — which is S-7's
# shape and is refused by `cmd_send` anyway.
#
# The alarm is FAILURE-PATH traffic and failure path is the leader's lane, so no chief-of-staff
# `senders:` bound is implicated: the executor never addresses the chief-of-staff and needs no
# entry in any seat's sender allow-list.
LIFECYCLE_ALARM_ROLE = "leader"


def lifecycle_alarm_recipient(args, base):
    """(name, why) — WHO this run routes an executor failure to, resolved from its own package.

    `("", why)` when nothing resolves, and the caller must then take the undelivered-flags path
    rather than send into the void. Never raises: this runs inside a refusal, and a traceback
    replacing a refusal is worse than the defect it reports (`refusal_text`'s own rule)."""
    try:
        known = coord.known_recipients(args, base)
    except Exception as exc:                                   # noqa: BLE001
        return "", (f"this package's recipient set could not be read at all "
                    f"({type(exc).__name__}: {exc})")
    if LIFECYCLE_ALARM_ROLE in known:
        return LIFECYCLE_ALARM_ROLE, ""
    return "", (f"nothing in this package resolves {LIFECYCLE_ALARM_ROLE!r} — no roster row, no "
                f"briefing, no group, no relay token and no addressable non-member of that name. "
                f"A run that renamed its leader seat declares `relays: {LIFECYCLE_ALARM_ROLE}` on "
                f"the successor and this resolves again")


def lifecycle_alarm_body(layer, msg, base, args):
    """The alarm's TEXT — enough that a reader ACTS without opening the executor's log first.

    Six things, because a reader woken by this has none of them: the SEAT, the DISPOSITION, WHAT
    failed, what the DURABLE marker says (read back from disk AFTER step 1 wrote it), where that
    marker is, and where the executor's log landed. The LAYER is named per the layer-prefix
    convention s12-03 sweeps across this file: a seat that cannot tell coord.py's own gate from its
    harness's permission classifier sends the run at the wrong fix (R-8).

    An absent log path is ADMITTED with its reason rather than invented — `inherited_log_path`'s
    rule, restated at the one place a human reads the answer."""
    seat = str(getattr(args, "seat", "") or "<unknown seat>")
    disp = str(getattr(args, "disposition", "") or "<unknown disposition>")
    entry = {}
    if base is not None:
        try:
            found = load_lifecycle(base).get(seat)
            entry = found if isinstance(found, dict) else {}
        except Exception:                                      # noqa: BLE001
            entry = {}
    state = str(entry.get("state") or "")
    failed_text = str(entry.get("failure") or "")
    steps = entry.get("steps-completed")
    steps = [str(s) for s in steps] if isinstance(steps, list) else []
    log = str(entry.get("log") or "")
    log_note = str(entry.get("log-note") or "")
    return "\n".join([
        f"LIFECYCLE-EXEC ALARM — seat '{seat}', disposition '{disp}'.",
        f"what failed: {msg}",
        f"last verified step: {steps[-1] if steps else 'NONE — no step was verified'}",
        f"marker says: {state or 'NO ENTRY for this seat'}"
        + (f" — {failed_text}" if failed_text else ""),
        f"marker file: {lifecycle_path(base) if base is not None else 'NOT RESOLVED'}",
        f"executor log: {log or ('NOT RECORDED — ' + (log_note or 'the marker carries no path'))}",
        f"refusal layer: {layer} — this is coord.py's OWN gate, NOT the harness permission "
        f"classifier. Report it as \"coord {layer} refused\"; the two look alike and a bare "
        f"\"refused\" sends the run at the wrong fix.",
    ])


def lifecycle_alarm_namespace(args, to, body):
    """The Namespace `cmd_send` is called with IN-PROCESS. watch.py's `notify_leader`, field for
    field — this is a COPY of a precedent that works, not a new send path.

    ⚠ `agent="lifecycle-exec"` IS LOAD-BEARING, not decoration. `cmd_send` calls `resolve_agent`
    with `required=True`, whose order is `--as` > `args.agent` > `COORD_AGENT` > the calling pane's
    roster row and which EXITS 2 when all four are empty. This executor scrubbed COORD_AGENT and
    TMUX_PANE at entry (guard 1) and holds no roster row, so WITHOUT the explicit token every alarm
    would exit 2 by construction and could never reach the bus. It is an honest MACHINERY identity,
    exactly as the watch loop sends as the literal `agent="watcher"` — a seat's name here would be
    a fabricated identity and is what `as_agent=None` forbids.

    ⚠ NO `pane` ATTRIBUTE. `sender_origin` reads it and returns None for an unresolvable pane
    precisely to "preserve the status quo for out-of-pane callers like watch.py"; supplying one
    would make this process claim a pane it does not hold.

    ⚠ `type="note"`, NEVER `ask`. An `ask` from a sender no one can address opens a thread with NO
    POSSIBLE TERMINUS and `cmd_send` refuses it outright, with no `--force` override, deliberately
    (S-7 — 13 unclosable asks in one run). A failure report is a FACT, not a question: nothing is
    owed in reply, so `note` is also the honest type.

    ⚠ `force=False`. watch.py's own comment carries the reason: `--force` "would have suppressed
    every OTHER refusal too — including ones that should stop a bad send."

    ⚠ NO `inline` ATTRIBUTE, and that was VERIFIED rather than assumed (2026-07-29):
    `assert_argv_body_shell_safe` decides at `main()`'s dispatch boundary, gated on
    `CLI_INVOCATION and args.func is cmd_send`, so an in-process Namespace caller never reaches it.
    The gate has NOT moved into `cmd_send`. If it ever does, set `inline=True` here."""
    return argparse.Namespace(
        package=getattr(args, "package", None), base=getattr(args, "base", None),
        workers_dir=getattr(args, "workers_dir", None),
        agent="lifecycle-exec", as_agent=None, to=to, message=body,
        type="note", supersedes=None, re_num=None, file=None, force=False)


def lifecycle_record_undelivered(base, text, reason):
    """STEP 3 — append the alarm to `{base}/undelivered-flags.md`. True when it landed.

    `record_undelivered`'s shape from watch.py, including its own last-resort branch: a plain
    append under `coordination/` cannot be refused by a sender bound, a type enum, or a roster row
    — the three things that swallowed that night's warnings — and when even THIS fails it PRINTS,
    because the alternative is the silence being fixed.

    ⚠ THIS IS A SECOND WRITER OF ONE FILE, AND IT IS DECLARED RATHER THAN HIDDEN (PRIN-11 —
    single source of truth). watch.py's `record_undelivered` writes the same file in the same
    format, and it CANNOT be imported here: watch.py imports coord, never the reverse, so putting
    the shared home in watch.py would invert the dependency. The home belongs HERE, beside the two
    READERS (`undelivered_flags`, `undelivered_line`) that already live in this file — so this is
    the writer arriving next to its readers, and watch.py's copy is the one left to retire.
    Editing watch.py is out of this task's scope, so the unification is FILED, not smuggled in.
    The signature takes `base`, not `args`, precisely so watch.py can call it unchanged
    (PRIN-13 — built as a separable part, decoupled from its first caller). Both copies write
    through `now()`, so the stamp format cannot drift between them."""
    try:
        Path(base).mkdir(parents=True, exist_ok=True)
        line = (f"- {coord.now()} | UNDELIVERED ({reason}): "
                f"{' '.join(str(text).split())}\n")
        with open(Path(base) / "undelivered-flags.md", "a", encoding="utf-8") as fh:
            fh.write(line)
        return True
    except Exception as exc:                                   # noqa: BLE001
        print(f"lifecycle-exec: CANNOT RECORD an undelivered flag either ({exc}) — this alarm is "
              f"being LOST ENTIRELY, and this stderr line is all that is left of it: "
              f"{' '.join(str(text).split())[:400]}", file=sys.stderr)
        return False


def lifecycle_recipient_live(args, base, name):
    """(alive, why) — is anybody SITTING IN `name` right now? Never raises.

    ⚠ ADDRESSABILITY IS NOT LIVENESS, and the gap between them is the forge instance's whole
    silence. `lifecycle_alarm_recipient` answers "does this package RESOLVE the name" — a roster
    row, a briefing, a group, a relay token. On 2026-08-18 that answered YES for a leader chair
    that had been EMPTY FOR NINE MINUTES: the refused-renewal remedy was posted to it, the post
    succeeded, and the lineage ended with nobody reading. A send that lands in an empty chair is
    not a delivery, and this predicate is what lets the alarm SAY SO instead of reporting "sent".

    It does NOT suppress the send — mail persists and the chair's NEXT sitting drains it. It adds
    the escalation: an empty chair also gets an `undelivered-flags.md` row, which `status` and
    `workers` surface to every OTHER seat through `undelivered_line`.

    Both identity kinds, because the seat this fires for is usually the paneless one: a `%N` row is
    live when tmux still has the pane; a `sid:` row (F1, the daemon lane) is live when that session
    is still OPEN in `sessions.csv`. Any read failure is NOT live — the fail-safe direction here is
    "assume the chair is empty", because the cost of being wrong is one extra durable flag and the
    cost of the other error is the silence this exists to end."""
    try:
        _, _, rows = coord.load_workers(base)
        row = coord.current_row(rows, name)
    except Exception as exc:                                   # noqa: BLE001
        return False, (f"this package's roster could not be read at all "
                       f"({type(exc).__name__}: {exc}), so nothing vouches that anyone is sitting "
                       f"in '{name}'")
    if row is None:
        return False, (f"'{name}' holds NO roster row on this package — it resolves as an ADDRESS "
                       f"(a briefing, a group or a relay token) but no session has ever checked in "
                       f"under it")
    if str(row.get("active") or "") != "yes":
        return False, (f"'{name}''s roster row is NOT ACTIVE — its last sitting checked out, so "
                       f"the chair is empty until it is launched again")
    pane = str(row.get("pane") or "")
    if coord.is_tmux_pane(pane):
        if pane in coord.live_panes():
            return True, ""
        return False, (f"'{name}' is rostered ACTIVE in {pane}, but tmux no longer has that pane "
                       f"— the session died without checking out")
    if pane.startswith(coord.SID_PANE_PREFIX):
        sid = pane[len(coord.SID_PANE_PREFIX):]
        try:
            # F-6 (2026-08-21): MEMBERSHIP among the seat's open rows, not equality with the LAST
            # one. The roster token is now the carrier-proven id (`cmd_checkin`'s F-6 note), and
            # the daemon appends the session row after launch — so during a boot window, or while
            # a stale open row sits later in file order, "last open row" and the token can
            # legitimately name different rows of the SAME live seat. Measured 2026-08-20 22:23Z:
            # the live leader read as an empty chair for its whole sitting because the roster held
            # the stale row's id while its own row 404 was the last-open one.
            open_ids = coord.session_open_ids(coord.package_dir(args), name)
        except Exception as exc:                               # noqa: BLE001
            return False, (f"'{name}' is PANELESS (rostered against session {sid}) and this "
                           f"package's open-session set could not be read "
                           f"({type(exc).__name__}: {exc})")
        if sid in open_ids:
            return True, ""
        return False, (f"'{name}' is a PANELESS seat rostered ACTIVE against session {sid}, and "
                       f"that session is no longer open in sessions.csv")
    return False, (f"'{name}''s roster row carries neither a tmux pane nor a `{coord.SID_PANE_PREFIX}` "
                   f"token, so there is no identity to test liveness against")


def lifecycle_raise_alarm(layer, msg, base, args):
    """STEPS 2-3 — raise the bus alarm. Returns `(outcome, line)`; NEVER raises, NEVER exits.

    THE OUTCOME IS THE CONTRACT, and it is what lets `s3-06`/`s3-07` (and a human reading the
    detached log) tell "alarm raised" from "alarm failed to raise" instead of guessing:

      "sent"         a `type: note` from `lifecycle-exec` is in the package's message log.
      "undelivered"  the send was REFUSED and `undelivered-flags.md` holds the alarm instead —
                     `status` and `workers` surface it through `undelivered_line`.
      "lost"         the send was refused AND the flag could not be appended. The alarm now exists
                     ONLY in this process's stderr, which is the failure this whole function
                     exists to prevent, reported rather than hidden.
      "no-package"   the call site had no resolved package, so there was no bus to send on and no
                     directory to append to. Guard 2 is that site BY DESIGN — it refuses BEFORE
                     `base_dir` is called precisely so a guard claiming "it acted on nothing" has
                     not registered a run tag first — so its refusal reaches stderr ONLY. That is a
                     KNOWN, NAMED HOLE, not an oversight: `line` says so, out loud, every time.

    `line` is appended to the refusal text so the log states which of the four happened. It is the
    only self-report a detached process can make.

    ⚠ TMUX_PANE IS POPPED FOR THE SEND AND RESTORED AFTER — belt-and-braces over guard 1's scrub,
    and kept because watch.py's SECOND refusal was exactly this: a detached loop INHERITED
    TMUX_PANE from the shell that started it and every send was refused with "you claimed
    'watcher', but this pane (%145) is registered to 'chief-of-staff'". An executor forked from a
    dying seat's pane is the same shape. `--force` is NOT the remedy and is not used.

    ⚠ EVERY exception is caught, not just `SystemExit`. This runs inside a refusal; a traceback
    escaping here would REPLACE a refusal with a stack trace, which is strictly worse than the
    defect being reported."""
    if base is None or args is None:
        return "no-package", (
            "ALARM NOT RAISED — no package was resolved at this refusal, so there is no message "
            "log to post to and no coordination directory to flag in. This refusal exists ONLY in "
            "this process's stderr, which is a detached log file nobody is watching. Whoever reads "
            "it is the only reader it will ever get.")
    body = lifecycle_alarm_body(layer, msg, base, args)
    to, why = lifecycle_alarm_recipient(args, base)
    if not to:
        landed = lifecycle_record_undelivered(base, body, f"no recipient resolved — {why}")
        if landed:
            return "undelivered", (
                f"ALARM NOT SENT — {why}. It is recorded in "
                f"{Path(base) / 'undelivered-flags.md'} instead, where `status` and `workers` "
                f"surface it.")
        return "lost", (f"⚠⚠ ALARM LOST — {why}, AND the undelivered flag could not be appended "
                        f"either. This refusal exists only in this process's stderr.")
    ns = lifecycle_alarm_namespace(args, to, body)
    prior = os.environ.pop("TMUX_PANE", None)
    reason = ""
    try:
        coord.cmd_send(ns)
    except SystemExit as exc:
        reason = f"coord refused the send (exit {exc.code})"
    except Exception as exc:                                   # noqa: BLE001
        reason = f"the send raised {type(exc).__name__}: {exc}"
    finally:
        if prior is not None:
            os.environ["TMUX_PANE"] = prior
    if not reason:
        # THE ADDRESSEE'S LIVENESS, CHECKED — never assumed from the fact that the send succeeded.
        # `cmd_send` accepts any RESOLVABLE name; the forge instance posted its remedy to a leader
        # nine minutes dead and reported success. The send still stands (mail persists and the
        # chair's next sitting drains it) — what is ADDED is the escalation and the honest wording.
        alive, why_empty = lifecycle_recipient_live(args, base, to)
        raised = (f"ALARM RAISED: a `type: note` from `lifecycle-exec` is on this package's bus, "
                  f"addressed to '{to}'.")
        if alive:
            return "sent", raised + " That chair is LIVE."
        # ⚠ "ALARM RAISED" IS STILL THE FIRST CLAUSE, and deliberately so: the note DID leave this
        # process, which is the fact the executor's self-report exists to state and the fact a
        # reader of the detached log needs. What is ADDED is that landing is not reading.
        landed = lifecycle_record_undelivered(
            base, body, f"posted to '{to}' but THAT CHAIR IS EMPTY — {why_empty}")
        return "sent", (
            raised + f" ⚠ BUT NOBODY IS SITTING IN IT: {why_empty}. The note stays on the bus for "
            f"that chair's next sitting, and "
            + (f"it is ALSO recorded in {Path(base) / 'undelivered-flags.md'}, where `status` and "
               f"`workers` surface it to every OTHER seat through `undelivered_line`."
               if landed else
               f"⚠⚠ the undelivered flag could NOT be appended either, so no OTHER reader will "
               f"reach it."))
    landed = lifecycle_record_undelivered(base, body, reason)
    if landed:
        return "undelivered", (
            f"ALARM NOT DELIVERED — {reason}. It is recorded in "
            f"{Path(base) / 'undelivered-flags.md'} instead, where `status` and `workers` surface "
            f"it through `undelivered_line`.")
    return "lost", (f"⚠⚠ ALARM LOST — {reason}, AND the undelivered flag could not be appended "
                    f"either. This refusal exists only in this process's stderr.")


def lifecycle_alarm(layer, msg, code=2, base=None, args=None, failure=None):
    """The executor's ONE refusal chokepoint: mark, alarm the bus, emit the refusal, exit.

    Every entry guard refuses through here, and that is the point — the BUS ALARM is added at ONE
    site instead of five, and can never be added to four of them.

    THE THREE STEPS RUN IN THIS ORDER, and the order is the design (the section header above
    carries the full argument):

      1. the marker, when the caller passes `failure=` — DURABLE, and written FIRST;
      2. the bus alarm and its undelivered-flags fallback (`lifecycle_raise_alarm`);
      3. the layered refusal on stderr, carrying the outcome of step 2.

    ⚠ `failure=` IS OPT-IN, AND THAT IS NOT LAZINESS. An entry guard's whole claim is that it acted
    on NOTHING, and guard 3 in particular refuses precisely because ANOTHER live executor owns that
    seat's marker — flipping it FAILED there would destroy the other executor's record, which is
    the exact double-launch damage the marker exists to prevent. So a guard passes no `failure` and
    writes no marker; a FAILURE BRANCH (`s3-06`, `s3-07`) passes the text of the break and the
    marker is flipped before anything perishable is attempted.

    `base` is optional because guard 2 runs BEFORE the package is resolved. When it is given, the
    marker's own alarm block is appended by CALLING `lifecycle_line` — never by re-spelling
    STALE/FAILED/UNKNOWN here, so this surface and `s3-04`'s cannot hold two definitions that
    drift apart. When it is ABSENT the bus alarm cannot be raised at all, and `lifecycle_raise_alarm`
    says so in the refusal rather than letting the caller assume it was.

    ⚠ `layer` is passed through to `refuse` as a NAME, not a literal, so s12-03's L-a scan (which
    collects literals at `refuse`/`refusal_text` call sites and SKIPS any whose first argument is a
    Name) cannot see the layers this chokepoint routes. `_selftest_checks` carries a scan of THIS
    function's own call sites for that reason; without it, routing a refusal through a helper
    routes it out of the file's five-layer bound.
    """
    # ---- STEP 1: THE DURABLE RECORD, BEFORE THE PERISHABLE ONE (R-7). --------------------------
    if failure is not None and base is not None and getattr(args, "seat", ""):
        finish_lifecycle(base, args.seat, "FAILED", failure)
    # ---- STEPS 2-3: THE BUS ALARM. Reads the marker step 1 just wrote, so the note cannot report
    # a state the disk does not hold. Never raises and never exits — the refusal below is the ONE
    # exit of this chokepoint.
    _alarm_outcome, alarm_line = lifecycle_raise_alarm(layer, msg, base, args)
    # ---- STEP 3: the layered refusal, on the inherited stderr. `lifecycle_line` is read HERE,
    # after step 1, so `status`/`workers`' own rendering of the marker agrees with the note.
    text = "lifecycle-exec: " + msg
    if base is not None:
        marker = lifecycle_line(base)
        if marker:
            text += "\n" + marker
    text += "\n" + alarm_line
    coord.refuse(layer, text, code)


def lifecycle_target_live(target):
    """(ok, why) — is `--tmux-target` a target tmux ACTUALLY RESOLVES right now?

    ⚠⚠ THE EXECUTOR MUST REFUSE, NEVER GUESS. It has neither `COORD_LAUNCH_TARGET` nor `TMUX_PANE`
    (guard 1 popped both), so inheriting `cmd_close_seat`'s `COORD_LAUNCH_TARGET or TMUX_PANE`
    fallback would hand tmux an EMPTY target — and the hazard is measured, quoted verbatim from
    `recover-room.py:13-19`:

        Worse: it would not fail, it would guess. `launch` resolves its target as
        COORD_LAUNCH_TARGET or TMUX_PANE … and a daemon-fired `fire-tool` exec has NEITHER. With
        both unset, tmux resolves an empty target to the MOST RECENT session — measured, it
        answered `build-core-daemon-mvp`, the LIVE room. A recovery that opens agents into the
        live room believing it is repairing a dead one is worse than no recovery at all.

    Two resolution routes, in this order, because a target is a PANE id or a WINDOW id:
      1. the live pane set (`live_panes`) answers pane ids;
      2. `tmux_session_name` answers anything tmux can name a session for, which is how a window
         id resolves.
    An empty target short-circuits to False WITHOUT touching tmux at all — the caller's guard
    refuses before this is ever entered, and this arm exists so no other caller can slip an empty
    string past it either.
    """
    t = str(target or "").strip()
    if not t:
        return False, "it is EMPTY"
    if t in coord.live_panes():
        return True, ""
    if coord.tmux_session_name(t):
        return True, ""
    return False, ("tmux resolves neither a live pane nor a session for it — it names nothing "
                   "that exists right now")


def inherited_log_path(fd=1):
    """(path, why) — the FILE this process's `fd` is redirected to, resolved from /proc.

    THE EXECUTOR NEVER OPENS AND NEVER NAMES ITS OWN LOG. `s3-09` opens
    `{base}/lifecycle-exec-{seat}-{stamp}.log` and hands it over as the child's stdout/stderr, with
    ONE `{stamp}` computed once at the fork — two independently computed stamps would name two
    different files for one run, and the marker would point at the empty one. So this reads back
    WHAT WAS INHERITED rather than deriving a second name, and guard 5 records it.

    `""` plus a stated reason whenever fd is not a plain file (a tty, a pipe, a deleted file, an
    unreadable /proc). A blank recorded honestly beats a path that leads nowhere: the marker's
    whole purpose here is that a reader can FIND the evidence, and a wrong path is worse than an
    admitted absence. Never `DEVNULL` — that bar is `s3-09`'s.
    """
    try:
        resolved = os.readlink(f"/proc/self/fd/{int(fd)}")
    except (OSError, ValueError, TypeError) as exc:
        return "", f"/proc/self/fd/{fd} is unreadable ({type(exc).__name__})"
    if not os.path.isfile(resolved):
        return "", (f"fd {fd} is not a plain file — it resolves to {resolved!r}, so this run's "
                    f"output is not landing anywhere a reader can open")
    return resolved, ""


# ---- STAGE 3 (s3-09): THE CALLER-SIDE FORK — where the pane stops being trusted --------------
#
# THE SEAT'S OWN CHECKOUT FORKS THE EXECUTOR AND THEN EXITS. Everything `cmd_checkout` does before
# this seam is in-pane work that is SAFE in-pane — the handoff write, the transcript export, the
# roster flip, the sessions.csv close, the awaiting-close record. The renewal itself is not: it
# respawns or kills the very pane the caller runs in, so a process attempting it would die halfway
# through its own act (W1, and the reason `cmd_close_seat` prints its self-act WARNING). The fork
# is the seam between the two, and its ORDER is load-bearing:
#
#     … set_awaiting -> STAMP THE MARKER -> FORK -> EXIT.
#
# A caller killed BEFORE the fork degrades to TODAY's state — checked out, awaiting-close debt
# standing, leader closes it by hand. A known state with an existing remedy, not a new failure
# mode. That is also why the marker is stamped by the CALLER and not by the child: a stamped
# marker means a fork was reached, and no marker means the seat never got that far — a distinction
# nobody can recover afterwards if the child owns the first write.
#
# ⚠⚠ THE CHILD'S ENVIRONMENT IS A DENYLIST, NEVER AN ALLOWLIST, and that is load-bearing rather
# than stylistic. The four names in `LIFECYCLE_SCRUB_ENV` are the ones that would make the child
# act AS the dying seat or IN the caller's pane, and they are the ones removed. EVERYTHING ELSE IS
# INHERITED ON PURPOSE — `TMUX_TMPDIR` above all, which is what binds a process to ONE tmux SERVER.
# An acceptance room that isolates itself by giving the room its own `TMUX_TMPDIR` (rather than
# `tmux -L`, measured NON-isolating for the context sensor, which shells out to bare `tmux` and
# takes no socket parameter) would leak straight back onto the LIVE server the moment a narrow
# allowlist dropped that name — and its suite would report green while acting on the real box.
# That is `recover-room.py:13-19`'s hazard wearing a new mask: it would not fail, it would guess.


def lifecycle_fork_target(seat, pane):
    """(target, why) — the EXPLICIT tmux target for `seat`'s detached executor, or ("", reason).

    `cmd_close_seat`'s OWN placement logic, MINUS ITS FALLBACK. In-place (G-154) -> the pane
    itself; a PANE-placed seat whose old window still resolves to a session -> that window. What
    is deliberately NOT copied is the last line of that block,
    `os.environ.get("COORD_LAUNCH_TARGET") or os.environ.get("TMUX_PANE")` — the executor has
    NEITHER (it scrubs both at entry), and an empty target is not an error tmux reports:

        Worse: it would not fail, it would guess. `launch` resolves its target as
        COORD_LAUNCH_TARGET or TMUX_PANE … and a daemon-fired `fire-tool` exec has NEITHER. With
        both unset, tmux resolves an empty target to the MOST RECENT session — measured, it
        answered `build-core-daemon-mvp`, the LIVE room. A recovery that opens agents into the
        live room believing it is repairing a dead one is worse than no recovery at all.
        — ignite/runtime/jobs/recover-room.py:13-19

    So the answer here is a target or a REFUSAL, never a blank a caller might pass on.

    AND THE PANELESS LANE REFUSES BY ITS OWN NAME, FIRST. Every arm below needs a `%N`; a
    daemon-launched seat's roster row carries `sid:<session-id>` (F1) and never has one, so the
    `is_tmux_pane` arm at the top answers it before any tmux call is made. That is ALSO what makes
    the empty return structurally unreachable from the two SUCCESS arms: past that guard `pane` is
    a `%N` (the in-place arm returns it verbatim), and the window arm returns `window` only when
    `tmux_session_name(window)` has already resolved it. `fork_lifecycle_renewal` re-checks
    `if not target` regardless — belt and braces, not a substitute.

    The two tmux measurements are skipped when the pane is dead, which cannot change the verdict:
    `renew_in_place` short-circuits on `pane_live` and a dead pane has no window to read. That is
    an elision of unreachable work, not a second rule.
    """
    if not coord.is_tmux_pane(pane):
        # ⚠ THE PANELESS LANE, ANSWERED FIRST AND BY ITS OWN NAME (2026-08-18). This arm used to
        # read `if not pane`, which a paneless row does not satisfy: F1 puts the seat's OPEN
        # session id in the pane cell, prefixed — `sid:<uuid>` is TRUTHY, so a daemon-lane seat
        # fell through to the `not pane_live` arm below and was told "its pane sid:… is NOT LIVE",
        # naming a pane that never existed and pointing its reader at tmux. `is_tmux_pane` is the
        # SAME predicate every tmux wrapper in this file already guards with, so this arm is the
        # structural statement that the three measurements below cannot answer for this row:
        # `live_panes`, `tmux_pane_window` and `tmux_session_name` all take a `%N` and nothing else.
        # It is also what makes the empty target IMPOSSIBLE rather than merely refused — past this
        # line `pane` IS a `%N`, so the in-place arm returns a real pane id, and the window arm is
        # guarded on `tmux_session_name(window)` resolving.
        # ⚠ SHORT ON PURPOSE. This text is carried into `lifecycle_alarm_body`, which `cmd_send`
        # refuses at 2000 chars — measured: a fuller wording made the ALARM ITSELF undeliverable,
        # which is this whole change's failure mode arriving through its own fix.
        return "", (f"its roster row carries "
                    + (f"the PANELESS token {pane!r}" if pane else "no pane at all")
                    + ", not a tmux pane id — a DAEMON-launched seat has never been in a tmux "
                      "room, so no pane, window or session can be measured from it")
    pane_live = pane in coord.live_panes()
    if coord.renew_in_place(seat, pane, pane_live, coord.tmux_pane_window_name(pane) if pane_live else None):
        return pane, ""
    window = coord.tmux_pane_window(pane) if pane_live else ""
    if launch.seat_placement(seat)[0] == "pane" and window and coord.tmux_session_name(window):
        return window, ""
    if not pane_live:
        return "", (f"its pane {pane} is NOT LIVE, so neither that pane nor the window it sat in "
                    f"can name one")
    return "", (f"its pane {pane} is not in the window its descriptor asks for (so the pane "
                f"cannot be respawned in place) and tmux names no session for the window "
                f"{window or '(none)'} that pane sits in")


def lifecycle_no_successor(args, base, seat_name, pane, why, remedy, layer="state"):
    """THE CALLER-SIDE REFUSAL CHOKEPOINT: a renew that produces NO successor, recorded LOUDLY.

    ⚠⚠ WHAT THIS REPLACES IS THE DEFECT. Every arm of `fork_lifecycle_renewal` used to leave
    through a bare `refuse(...)` — text on the CHECKING-OUT SEAT'S STDERR and nothing else. That
    seat is about to stop existing. So on 2026-08-18 a paneless `checkout --renew` printed a
    refusal into a dying session, wrote NOTHING to disk about the missing successor, and routed
    its remedy to a leader that had been dead for nine minutes. The lineage ended and no reader
    anywhere could tell. `coordinate`'s own `checkout` epilog promises "renew: the same seat comes
    back"; when it cannot, the BREAKING of that promise has to be as durable as the promise.

    THREE SURFACES, and each is one a DIFFERENT reader actually reaches:
      1. `lifecycle-inflight.json` — the seat's entry flips to `state: FAILED` with the reason in
         `failure`. This is the SUCCESSOR-PENDING SIGNAL, and it is the whole point of stamping on
         a path that forks nothing: `state == "in-flight"` means a successor is coming,
         `"FAILED"` means NO successor is possible, and NO ENTRY means no renew was ever attempted.
         `status` and `workers` already render it through `lifecycle_line`.
      2. the BUS — `lifecycle_alarm` posts a `type: note` to this run's alarm chair, and
         `lifecycle_recipient_live` now says out loud when that chair is EMPTY and adds an
         `undelivered-flags.md` row that `status`/`workers` surface to every OTHER seat.
      3. the refusal itself, unchanged in substance, on the caller's inherited stderr.

    Everything after step 1 is `lifecycle_alarm`'s, verbatim — the executor's own chokepoint,
    reused rather than re-implemented, so the caller side and the executor side can never drift
    into raising different alarms for the same fact (PRIN-11).

    THE STAMP IS CONDITIONAL, and that is not a micro-optimisation: the log-open and spawn arms
    below fire AFTER a real stamp landed, carrying the caller identity, the resolved target and
    the log path. Re-stamping would blank exactly the evidence a reader needs, so a seat that
    already has an entry keeps it and only its terminal state is written.

    `args` here is `cmd_checkout`'s, which carries no `seat` and no `disposition` — the two fields
    `lifecycle_alarm` reads to mark the record and to head the alarm. The shim below supplies them
    and nothing else; it is NOT a fabricated identity (the send still goes out as the machinery
    token `lifecycle-exec`, per `lifecycle_alarm_namespace`).

    ⚠ THE LAYER IS SPELLED AS A LITERAL AT TWO CALL SITES BELOW RATHER THAN FORWARDED AS A NAME,
    and that is not style. `_selftest_checks`' s3-05 (L) row walks this file's AST, collects the
    string constants in every `lifecycle_alarm` call's FIRST argument, and refuses any site whose
    layer it cannot READ — because s12-03's own L-a scan already skips call sites whose first
    argument is a Name, so a chokepoint forwarding `layer` would route these refusals straight out
    of the file's five-layer bound. One extra branch buys the bound back.

    NEVER RETURNS — `lifecycle_alarm` exits through `refuse` with code 2."""
    if seat_name not in load_lifecycle(base):
        stamp_lifecycle(base, seat_name, {"disposition": "renew", "pane": str(pane or ""),
                                          "tmux-target": "", "log": ""})
    rest = (
        f"NO EXECUTOR WAS FORKED for '{seat_name}': {why} YOUR CHECKOUT STANDS — handoff written, "
        f"transcript exported, roster flipped, debt recorded; only the RELAUNCH did not happen, "
        f"and the marker and the alarm are what record that.\n"
        f"Leader brings the seat back by hand: {remedy}",
        2, base,
        argparse.Namespace(package=getattr(args, "package", None),
                           base=getattr(args, "base", None),
                           workers_dir=getattr(args, "workers_dir", None),
                           seat=seat_name, disposition="renew"),
        why)
    if layer == "environment":
        lifecycle_alarm("environment", *rest)
    else:
        lifecycle_alarm("state", *rest)


def fork_lifecycle_renewal(args, base, seat_name, pane):
    """Stamp the in-flight marker and FORK the detached `lifecycle-exec` for a RENEW checkout.

    `arm_pid_reaper`'s FORM, verbatim — `setsid` plus `start_new_session=True`, ONE call, no
    double-fork anywhere — with the three deltas Stage 3 forces:

      · `sys.executable` + THIS FILE's absolute path, never `bash -c`. The reaper's payload is
        pure shell; this executor must reach `renew_in_place`, `launch_seat` and
        `verify_pids_gone`, which are Python.
      · stdout/stderr to a FILE, never `DEVNULL`. `DEVNULL` is right for a four-line reaper and
        wrong here: this room has already lost a detached loop's output that way — "printed to a
        detached stderr file, and lost, while the loop went on reporting healthy"
        (`undelivered_flags`). ⚠ THE LOG IS EVIDENCE, NEVER THE ALARM. The alarm path is
        `lifecycle_alarm` (marker -> bus -> refusal) and nothing here duplicates any part of it.
      · the four `LIFECYCLE_SCRUB_ENV` names REMOVED from the child's `env=` — a DENYLIST, for the
        reason the section header above states at length. The executor pops them AGAIN at entry
        (`s3-05` guard 1); the redundancy is deliberate, so a future caller that forgets is still
        caught by the child.

    IT REFUSES RATHER THAN FORKING BLIND. Five ways this can fail — no descriptor, no computable
    target, no readable caller identity, no marker, no log — and each exits 2 naming the seat and
    the manual remedy. THE CHECKOUT ITSELF HAS ALREADY HAPPENED at this point and is NOT undone;
    every refusal says so in as many words, so a seat reading one does not believe its handoff was
    thrown away.

    ⚠ ONE `{stamp}`, COMPUTED ONCE, HERE. `s3-05`'s guard 5 reads the log path back off
    `/proc/self/fd/1` instead of recomputing a name, precisely so two independent stamps can never
    name two files for one run and leave the marker pointing at the empty one.

    ⚠ RENEW ONLY. `d-cos-may-launch` bounds this: the fork is the SEAT's own act on its OWN
    checkout, and nothing here is reachable from a chief-of-staff-facing command, flag or path.
    """
    seats = [w for w in launch.discover_workers(coord.workers_dir(args)) if w["agent"] == seat_name]
    if not seats:
        lifecycle_no_successor(
            args, base, seat_name, pane,
            f"no briefing in {coord.workers_dir(args)} carries `agent: {seat_name}`, so its placement "
            f"cannot be read and no target can be computed for the successor.",
            f"{coord.coord_invocation(args)} launch --only {seat_name} (once the briefing exists)")
    target, why = lifecycle_fork_target(seats[0], pane)
    if not target:
        lifecycle_no_successor(
            args, base, seat_name, pane,
            f"its tmux target could not be computed — {why}. Refusing rather than passing an "
            f"empty target down: tmux resolves an empty target to the MOST RECENT session, "
            f"measured to be the LIVE room.",
            f"{coord.coord_invocation(args)} close-seat {seat_name} --renew")
    caller_start = process.proc_stat(os.getpid())[1]
    if not caller_start:
        lifecycle_no_successor(
            args, base, seat_name, pane,
            f"this process cannot read its own /proc/{os.getpid()}/stat, so it has no "
            f"(pid, starttime) pair to hand over. The PAIR is what lets the executor tell 'my "
            f"caller exited' from 'a recycled pid landed on its number'; a pid alone is not an "
            f"identity.",
            f"{coord.coord_invocation(args)} close-seat {seat_name} --renew",
            layer="environment")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = Path(base) / f"lifecycle-exec-{seat_name}-{stamp}.log"
    # THE CALLER'S RECORD, AND ONLY THE CALLER'S. `executor` is deliberately ABSENT: the child
    # writes its own pair as its first act (`s3-05` guard 5), so an `executor` key in this file
    # always means a child really started. `stamp_lifecycle` owns `state`, `steps-completed` and
    # `stamped-at` and overwrites anything passed for them — a caller able to pre-load a step
    # could claim one before it ran, which is the inversion the G-134 block rules against.
    if not stamp_lifecycle(base, seat_name, {
            "disposition": "renew",
            "caller": (os.getpid(), caller_start),
            "pane": str(pane or ""),
            "tmux-target": target,
            "log": str(log_path)}):
        lifecycle_no_successor(
            args, base, seat_name, pane,
            f"the in-flight marker at {lifecycle_path(base)} could NOT be written. Forking anyway "
            f"would leave a renewal running that nothing on disk records — invisible to `status`, "
            f"and invisible to the revival arm, which reads exactly this file. ⚠ THE ALARM BELOW "
            f"IS THE ONLY DURABLE SURFACE LEFT on this arm: the marker write is what just failed.",
            f"{coord.coord_invocation(args)} close-seat {seat_name} --renew",
            layer="environment")
    # ⚠ THE DOOR THAT CARRIES `lifecycle-exec`, NOT THIS FILE. This module is imported, never
    # run — `python3 lifecycle_exec.py` defines that verb nowhere. The fork re-enters through
    # the CLI, which is `coord.COORD_PY`.
    argv = ["setsid", sys.executable, str(coord.COORD_PY), "lifecycle-exec",
            "--package", str(coord.package_dir(args)),
            "--seat", seat_name,
            "--disposition", "renew",
            "--pane", str(pane or ""),
            "--tmux-target", target,
            "--caller-pid", str(os.getpid()),
            "--caller-starttime", caller_start,
            # Always "1" on this path BY CONSTRUCTION, not by assumption: `cmd_checkout` reaches
            # this seam only from CALL 2, and call 2 refuses before the body unless the block
            # landed and verified. The executor re-reads memory.md and refuses the claim anyway.
            "--handoff-written", "1"]
    child_env = {k: v for k, v in os.environ.items() if k not in LIFECYCLE_SCRUB_ENV}
    try:
        handle = open(log_path, "ab")
    except OSError as exc:
        finish_lifecycle(base, seat_name, "FAILED",
                         f"the executor log {log_path} could not be opened ({exc}); nothing was "
                         f"forked")
        lifecycle_no_successor(
            args, base, seat_name, pane,
            f"its log {log_path} could not be opened ({exc}). A detached executor whose output "
            f"goes nowhere is the exact failure this room has already paid for once, so it is not "
            f"started at all. The marker is flipped FAILED so nothing reads this as a renewal in "
            f"progress.",
            f"{coord.coord_invocation(args)} close-seat {seat_name} --renew",
            layer="environment")
    try:
        subprocess.Popen(argv, stdout=handle, stderr=handle,
                         start_new_session=True, env=child_env)
    except OSError as exc:
        finish_lifecycle(base, seat_name, "FAILED",
                         f"the detached executor could not be spawned ({exc})")
        handle.close()
        lifecycle_no_successor(
            args, base, seat_name, pane,
            f"the spawn itself failed ({exc}). The marker is flipped FAILED so nothing reads this "
            f"as a renewal in progress.",
            f"{coord.coord_invocation(args)} close-seat {seat_name} --renew",
            layer="environment")
    handle.close()
    print(f"lifecycle: detached executor forked for '{seat_name}' — target {target}, evidence "
          f"{log_path}")


# ---- STAGE 3 (s3-06): THE DISPOSITION SEQUENCES — what the executor actually DOES -------------
#
# ONE SEQUENCE, THREE DISPOSITIONS. `close` IS `renew` MINUS EVERY RELAUNCH STEP, and `revive`
# (`s3-07`) IS `renew` MINUS EVERY STEP THAT NEEDS A CHECKOUT TO HAVE HAPPENED — neither is a
# second implementation of the same teardown. The two halves are gated on ONE boolean each
# (`relaunching`, from `LIFECYCLE_RELAUNCHING`; `checked_out`, from `LIFECYCLE_INTENT_OF`) so the
# three paths cannot drift into disagreeing about how a pane is killed, how a kill is verified, or
# what is cleared afterwards. Both booleans are read from the module's own vocabulary constants,
# never from a disposition name spelled a second time down here.
#
# EVERY STEP IS APPENDED AFTER IT VERIFIES, NEVER BEFORE. That is `append_lifecycle_step`'s own
# rule and the G-134 inversion the marker exists to make impossible: a marker recording a step
# that did not happen is WORSE than a marker recording nothing, because a later reader — and
# Stage 4's revival detector — reads it as history.
#
# EVERY FAILURE BRANCH LEAVES THROUGH `lifecycle_alarm` WITH `failure=` AND EXIT CODE 3. Three
# properties come from the chokepoint and are therefore NOT restated at the branches (s3-08):
#   - the marker is flipped FAILED with the text BEFORE anything perishable is attempted (R-7);
#   - ONE `type: note` reaches the package's leader-role recipient, else `undelivered-flags.md`,
#     else a stderr shout — the ladder is the chokepoint's and this file grows no second copy;
#   - the exit code stays 3, which is the split `s3-05` established and this task preserves:
#     2 = an entry GUARD refused this invocation, 3 = the guards passed and the SEQUENCE broke.
#     A reader of a detached log can tell "you were not allowed to" from "you were, and it broke".
#
# ⚠⚠ NO `finish_lifecycle` CALL IN ANY FAILURE BRANCH HERE. `s3-08` folded that write INTO
# `lifecycle_alarm` so the durable-before-perishable ORDER lives at ONE site instead of being a
# discipline eight branches could each forget. A branch writing its own would be a DUPLICATE write
# and would silently reorder itself past the alarm that reports it.
#
# ⚠ AND NO SECOND `coord_lock` WRAPPER ANYWHERE IN THIS SECTION. `flock` blocks the SAME process on
# a fresh fd (measured, `s4-05`), and `finish_lifecycle`, `append_lifecycle_step`, `clear_awaiting`,
# `clear_closing` and `cmd_send` each take and release it themselves, sequentially. Wrapping a lock
# around any of them deadlocks the executor with nobody left to notice.

# The RAM gate's RETRY CADENCE. MECHANISM, not policy — and the distinction is `r-floor-single-source`'s
# own: that ruling binds the FLOOR, a policy number with exactly one home (the run's budget.json,
# read per act, never held here and never received as a flag). How long THIS loop is willing to wait
# for memory to come back is a property of the loop. Bounded on purpose: an unbounded wait leaves a
# seat neither alive nor closed, which is the state LIFECYCLE_STALE_MIN exists to surface.
LIFECYCLE_MEM_RETRIES = 3
LIFECYCLE_MEM_RETRY_S = 20
# How often the settle wait re-asks /proc. Small enough that the common case (the caller is already
# gone at the first look) costs no sleep at all.
LIFECYCLE_SETTLE_POLL = 0.25


def lifecycle_record_step(base, seat, step):
    """Append ONE VERIFIED step to the marker, and SAY SO LOUDLY when the append fails (R-8).

    `append_lifecycle_step` is best-effort BY CONTRACT — bookkeeping ABOUT a lifecycle act must not
    break the act — so it answers False rather than raising. False here means the sequence is still
    running while the marker has stopped recording it, and the two readers that matter (Stage 4's
    revival detector, and a human at `status`) would then see a renewal frozen at an earlier step
    than it actually reached. Reported, never swallowed."""
    if append_lifecycle_step(base, seat, step):
        return True
    print(coord.c(f"WARNING lifecycle-exec: step {step!r} VERIFIED but could NOT be appended to seat "
            f"{seat!r}'s marker. The sequence continues; the marker is now BEHIND it, and anything "
            f"reading `steps-completed` will understate how far this renewal got.", coord.C_DEAD),
          file=sys.stderr)
    return False


def lifecycle_settle(caller, budget_s=None):
    """§3.1 THE SETTLE WAIT — bounded, then PROCEED REGARDLESS OF THE OUTCOME.

    Returns the settle's OWN `steps-completed` entry — one of the few that report a STATE rather
    than an act — and it must say which of the two happened: `"caller-exited"` or
    `"caller-still-live-after-settle"`.

    ⚠ A `revive` CALLER IS EXPECTED TO BE STILL LIVE, AND THAT IS NOT A FAILURE (`s3-07`).
    Stage 4's `check_revival()` in watch.py forks this executor and its loop KEEPS RUNNING, so
    `--caller-pid` names a process that never exits and this wait always burns its full budget
    before answering `caller-still-live-after-settle`. Bounded expiry RECORDED, never refused — the
    seat whose session already CRASHED is the one that must not be left un-relaunched.

    ⚠ `ident_is_live_process`, NEVER `ident_is_live_harness`. The caller is a PYTHON process and
    `is_harness_argv` matches only the claude/codex/opencode basenames, so the harness predicate
    reports every live caller DEAD and silently turns this wait into a no-op. The two are separate
    functions with separate names precisely so this line cannot be written by accident.

    ⚠ AND `ident_is_live_process` OFFERS NO "CANNOT TELL" (`s3-02`): a zombie and an unreadable
    /proc BOTH answer False = gone. This loop has exactly two outcomes and is not written as if a
    third existed.

    ⚠ THE WAIT IS COURTESY, NOT CORRECTNESS, and nothing downstream branches on its answer.
    CHECKOUT is the turn boundary: `cmd_close_seat` runs against an already-checked-out seat and
    kills its pane with NO turn-boundary negotiation of any kind, and by the time this executor
    runs the handoff is in `memory.md`, the transcript is exported, the roster is flipped and the
    sessions.csv row is closed — so per `concepts/session.md` invariants 1 and 3 nothing durable is
    left inside the session to rescue. That is why the budget is bounded and its EXPIRY is
    RECORDED rather than refused."""
    budget = process.LIFECYCLE_SETTLE_S if budget_s is None else budget_s
    deadline = time.monotonic() + max(0.0, float(budget))
    while True:
        if not process.ident_is_live_process(caller):
            return "caller-exited"
        if time.monotonic() >= deadline:
            return "caller-still-live-after-settle"
        time.sleep(LIFECYCLE_SETTLE_POLL)


def lifecycle_descriptor(args, base):
    """The seat's DESCRIPTOR, discovered the identical way `cmd_close_seat` discovers it — never
    returned without one, and never guessed.

    A renew with no descriptor is `cmd_close_seat`'s own "nothing to relaunch" path, and inventing
    one would boot a seat from a briefing nobody wrote. Resolved BEFORE anything is killed (G-51):
    a seat killed and then found unlaunchable is the worst-ordered failure this sequence can
    produce, so the refusal happens while the seat is still untouched."""
    found = [w for w in launch.discover_workers(coord.workers_dir(args)) if w["agent"] == args.seat]
    if found:
        return found[0]
    lifecycle_alarm(
        "state",
        f"NO DESCRIPTOR carries `agent: {args.seat}` in {coord.workers_dir(args)}, so there is nothing "
        f"to relaunch this seat FROM and this executor will not guess one. NOTHING HAS BEEN "
        f"KILLED — the descriptor is resolved before any kill precisely so a renew can never leave "
        f"a seat closed AND unlaunchable (G-51). Add the seat's briefing, then bring it back by "
        f"hand: {coord.coord_invocation(args)} launch --only {args.seat}",
        3, base, args=args,
        failure=(f"no descriptor carries `agent: {args.seat}` — the renew stopped BEFORE any kill "
                 f"and the seat is untouched"))


def lifecycle_check_bindings(args, seats, base):
    """G-51's descriptor-vs-`taskforce.csv` check, run BEFORE any kill and routed onto the
    executor's OWN alarm.

    ⚠ WHY THE EXISTING CHECK IS CALLED AND ITS EXIT CONVERTED, RATHER THAN A SECOND COPY WRITTEN.
    `check_bindings` refuses through the plain `refuse()`, which prints its full per-field detail
    and exits 2. Out of THIS process that exit would leave the marker `in-flight` with a dead
    executor — read as MID-RENEWAL until LIFECYCLE_STALE_MIN, the one reading Stage 4 must never be
    handed wrongly — and would reach nobody, because the caller is gone and stderr here is a
    detached log file. Re-deriving the divergence would be a duplicate of `binding_divergence`, so
    the real check RUNS (its detail is already on the log) and only its EXIT is converted into the
    chokepoint every other failure branch leaves through."""
    try:
        launch.check_bindings(args, seats, f"lifecycle-exec --disposition {args.disposition}")
        return
    except SystemExit:
        pass
    lifecycle_alarm(
        "state",
        f"the DESCRIPTOR for '{args.seat}' disagrees with this run's taskforce.csv (G-51) — the "
        f"per-field detail is printed immediately above this line by the shared binding check. "
        f"Checked BEFORE any kill, so NOTHING HAS BEEN KILLED and the seat is untouched. Fix "
        f"whichever side is wrong — the descriptor is what actually binds — then renew again.",
        3, base, args=args,
        failure=("descriptor/taskforce.csv binding divergence (G-51) — the renew stopped BEFORE "
                 "any kill and the seat is untouched"))


def lifecycle_memory_floor(args, base):
    """(floor_mb, why) — this run's DECLARED launch floor, READ per act from its own `budget.json`.

    ⚠ THE FLOOR IS NEVER CARRIED AND NEVER DEFAULTED (`r-floor-single-source`, task 7.82): argv is
    a COPY, a file is a REFERENCE. `memory_gate` takes `floor_mb` as a required positional with NO
    default precisely so no consumer can invent one, and this resolves it through the SAME call
    `launch_gates` makes — same helper, same `which`, same two exception classes.

    ⚠ THE TWO FAILURES ARE DIFFERENT FACTS AND GET DIFFERENT REFUSALS. A `budget.json` that IS
    declared and cannot be read is not the same fact as no declaration at all; collapsing them is
    what once made a WRONG PATH observationally identical to a package with no budget. `budget.py`
    keeps them as two exception classes for that reason, and this consumer keeps them as two
    messages a reader can act on differently."""
    try:
        return coord.budget_mod.floor_source(coord.package_dir(args), "refuse", None)
    except coord.budget_mod.FloorUnreadable as exc:
        lifecycle_alarm(
            "state",
            f"this run's budget.json IS DECLARED and could NOT be read: {exc}. That is NOT the same "
            f"fact as no budget being declared and is never treated as one — a wrong path and an "
            f"undeclared budget must not look alike. The relaunch needs a memory floor, this "
            f"executor may not invent one, and the seat's pane is already down. Repair the file, "
            f"then bring the seat back by hand: {coord.coord_invocation(args)} launch --only {args.seat}",
            3, base, args=args,
            failure=(f"budget.json is DECLARED and unreadable ({exc}) — no floor could be resolved "
                     f"and the executor refused rather than defaulting"))
    except coord.budget_mod.FloorUndeclared as exc:
        lifecycle_alarm(
            "state",
            f"NO memory floor is DECLARED for this run: {exc}. The floor's one home is the run's "
            f"budget.json (`r-floor-single-source`), a consumer that invents a number is the exact "
            f"defect that ruling deleted, and the seat's pane is already down. Declare the launch "
            f"floor there, then bring the seat back by hand: {coord.coord_invocation(args)} launch "
            f"--only {args.seat}",
            3, base, args=args,
            failure=(f"no floor is declared for this run ({exc}) — the executor refused rather "
                     f"than defaulting to a number of its own"))


def lifecycle_memory_gate(args, base, n_seats=1):
    """The relaunch's MEMORY pre-flight — alarmed and RETRIED, never silently given up on.
    Returns the floor it used; never returns when the gate stays shut.

    ⚠ THE EXECUTOR MUST NOT CALL `launch_gates`. That helper hard-refuses (exits) on a memory
    shortfall; this out-of-pane process needs to ALARM AND RETRY instead, on a bounded schedule,
    because a seat closed and never relaunched is the worst outcome this stage can produce. So the
    memory check is taken apart and re-implemented here rather than reused — `launch_gates` no
    longer carries a role check to avoid either [T2-R10, D24, F-simplicity-7], but its
    hard-refusal SHAPE is still wrong for a detached executor that cannot just exit and give up.

    ⚠ A REFUSAL IS NOT THE END. A seat closed and never relaunched is the worst outcome this stage
    can produce, and memory pressure is the one refusal reason that CLEARS ON ITS OWN. So the first
    refusal RAISES the bus alarm and the gate is re-evaluated on a bounded schedule; only an
    exhausted budget is terminal. At most two messages, saying different things — "blocked, still
    trying" and "gave up" — which is why the first goes through `lifecycle_raise_alarm` (it
    RETURNS) and only the last through `lifecycle_alarm` (it never does).

    ⚠ `available_mb() == 0` PASSES, by `memory_gate`'s own fail-safe: a broken sensor must not be
    able to stop a run. Stated here because it is why no RAM-gate row can live inside
    `_selftest_checks`, where `available_mb` is stubbed to exactly that."""
    floor_mb, floor_why = lifecycle_memory_floor(args, base)
    print(f"memory gate: floor {floor_why}")
    reason = process.memory_gate(n_seats, process.available_mb(), floor_mb)
    if not reason:
        return floor_mb
    _, first_line = lifecycle_raise_alarm(
        "state",
        f"the relaunch of '{args.seat}' is BLOCKED ON MEMORY and this executor is RETRYING, not "
        f"giving up — {reason} The seat is checked out and its pane is already down; it comes back "
        f"only if this gate clears, so freeing another seat now is what unblocks it.",
        base, args)
    print(first_line, file=sys.stderr)
    for attempt in range(1, LIFECYCLE_MEM_RETRIES + 1):
        time.sleep(LIFECYCLE_MEM_RETRY_S)
        reason = process.memory_gate(n_seats, process.available_mb(), floor_mb)
        if not reason:
            lifecycle_record_step(base, args.seat, f"memory-gate-cleared-on-retry-{attempt}")
            return floor_mb
    lifecycle_alarm(
        "state",
        f"the relaunch of '{args.seat}' is REFUSED ON MEMORY after {LIFECYCLE_MEM_RETRIES} "
        f"retries — {reason} The seat is checked out, its pane is down, and it is NOT coming back "
        f"on its own: bring it back by hand once memory is free — "
        f"{coord.coord_invocation(args)} launch --only {args.seat}",
        3, base, args=args,
        failure=(f"the relaunch was refused on memory after {LIFECYCLE_MEM_RETRIES} retries — the "
                 f"seat is closed and NOT relaunched"))


def run_lifecycle_sequence(args, base, target):
    """THE DISPOSITION SEQUENCE (`s3-06`, widened by `s3-07`): `renew`, `close` and `revive`, each
    step VERIFIED before it is recorded, each failure LOUD (R-8). Returns the successor's pane on a
    completed `renew`/`revive` and `""` on a completed `close`; NEVER RETURNS from a failure branch.

    `target` is the caller's validated `--tmux-target` (guard 2). This executor NEVER computes one:
    an unresolved target lands wherever tmux picks, which was measured to be the LIVE room.

    TWO BOOLEANS SHAPE THE BODY, and each is read from the module's vocabulary rather than from a
    disposition name spelled here:

      `relaunching`  (`LIFECYCLE_RELAUNCHING`) — does a successor go back? `renew` and `revive` yes,
                     `close` no. Gates steps 2, 3, 5 and 8 plus the RAM gate and the descriptor.
      `checked_out`  (`LIFECYCLE_INTENT_OF` mapping to `LIFECYCLE_INTENT_ABSENT`) — did a CHECKOUT
                     precede this act? `renew`/`close` yes, `revive` no. Gates step 7's transcript
                     read and step 6's roster invariant, the two that are ONLY true because a
                     checkout ran first.

    ⚠ `revive` IS `renew` ON A SEAT WHOSE SESSION CRASHED (`s3-07`, Stage-4 delta 1). The crash
    means there was no turn boundary at which anything could be written: no awaiting-close record,
    no exported transcript, no stamped handoff block, and a roster row still reading ACTIVE on the
    pane that died. Those are INPUTS to this sequence, not faults in it — a revive that refused on
    any of them would refuse in exactly the case revival exists for.
    """
    seat_name = args.seat
    relaunching = args.disposition in LIFECYCLE_RELAUNCHING
    # ⚠ DERIVED FROM THE MAPPING, NEVER FROM A NAME. `LIFECYCLE_INTENT_ABSENT` is guard 4's own
    # statement that no checkout happened for this disposition, and this is the same fact read a
    # second time by the sequence. Spelling `!= "revive"` here would put that fact in two places,
    # and the day `dag-08` adds a fourth disposition the two would answer differently.
    # `.get(..., "done")` never fires from the command path — guard 4 refuses an unmapped
    # disposition before this runs — and covers the direct-call path the suite uses for `close`.
    checked_out = LIFECYCLE_INTENT_OF.get(args.disposition, "done") is not LIFECYCLE_INTENT_ABSENT
    pane = str(getattr(args, "pane", "") or "")
    descriptor, in_place, new_pane = None, False, ""

    # ---- THE FIRST MARKER ENTRY ON A NO-CHECKOUT ACT, so a reader can tell a REVIVAL from a
    # RENEWAL by the marker ALONE. `steps-completed` is what Stage 4's detector and whoever is
    # woken at 04:00 actually read, and the two acts produce otherwise near-identical lists; the
    # `disposition` field says `revive` too, but a field is not what a step-list reader is reading.
    # Named off the disposition rather than hardcoded, so a fourth no-checkout act names itself.
    if not checked_out:
        lifecycle_record_step(base, seat_name, f"{args.disposition}-no-checkout")

    # ---- 0a. THE DESCRIPTOR AND THE BINDING CHECK — both BEFORE anything is killed (G-51). ------
    # Only a relaunching disposition needs a descriptor: a plain close relaunches nothing, so
    # demanding a briefing it will never read would refuse exactly the seats most in need of being
    # closed. The args NAMESPACE the callees need is THIS process's own — argparse already put
    # `--package` on it, and the global `--base`/`--workers-dir` ride along — so no second
    # hand-built Namespace is constructed here: a copy of an object that already exists is the
    # duplication this build is explicitly not to create.
    if relaunching:
        descriptor = lifecycle_descriptor(args, base)
        lifecycle_check_bindings(args, [descriptor], base)

    # ---- 0b. THE SETTLE WAIT. Bounded; both outcomes converge on the same sequence. -------------
    # Named exactly, because it reports a STATE rather than an act — and `s3-11`(a) reads it to
    # prove the executor never depended on the caller. On a `revive` the caller is Stage 4's watch
    # loop, which does NOT exit after forking, so this entry reads `caller-still-live-after-settle`
    # on the normal revival path and the sequence proceeds anyway.
    lifecycle_record_step(base, seat_name,
                          lifecycle_settle((args.caller_pid, args.caller_starttime)))

    # ---- STEP 1: RE-MEASURE THE OUTGOING HARNESS. A DEAD PANE IS A LEGAL INPUT. -----------------
    # Measured HERE, while the pane still exists (G-10), and NOT refused when it comes back empty:
    # a run that refused on a dead pane would strand exactly the seat most in need of a renew.
    old_idents = process.pane_harness_idents(pane) if pane else []
    lifecycle_record_step(base, seat_name, f"harness-idents-measured:{len(old_idents)}")

    if relaunching:
        # ---- STEP 2: THE G-154 BRANCH — the identical call `cmd_close_seat` makes. --------------
        # `renew_in_place` is PURE and stays pure: the window the pane is in RIGHT NOW is measured
        # by this caller and passed in, because that is the only thing that can say whether the
        # seat is already where its briefing wants it.
        in_place = coord.renew_in_place(descriptor, pane, pane in coord.live_panes(),
                                  coord.tmux_pane_window_name(pane) if pane else None)
        lifecycle_record_step(base, seat_name,
                              "in-place-decided:" + ("in-place" if in_place else "re-place"))

        # ---- STEP 3: MIRROR + HISTORY LIMIT. Its contract is that it never blocks a launch. -----
        # A renewed seat re-reads its rules at boot, and a renew lands mid-run — exactly when
        # sources have been drifting. Its own failure is already a loud WARNING inside
        # `refresh_mirrors_for`; anything it raises is caught here for the same reason, because a
        # stale mirror still carries the previous render's rules rather than none.
        try:
            launch.refresh_mirrors_for([descriptor])
            coord.tmux_raise_history_limit()
            lifecycle_record_step(base, seat_name, "mirror-and-history-refreshed")
        except Exception as exc:                                   # noqa: BLE001
            print(coord.c(f"WARNING lifecycle-exec: the pre-launch refresh raised "
                    f"{type(exc).__name__}: {exc}. CONTINUING — its contract is that it never "
                    f"blocks a launch, and a stale mirror beats no seat.", coord.C_DEAD), file=sys.stderr)

    # ---- STEP 4: TAKE THE OUTGOING SESSION DOWN, AND PROVE IT WENT. -----------------------------
    # 4a in-place: respawn the SAME pane (G-12 — kill+split re-tiles the whole window and destroys
    #    the layout the owner arranged). On a respawn failure, fall back to kill+split exactly as
    #    `cmd_close_seat` does: a re-tiled window is a cosmetic loss, a seat that never comes back
    #    is not.
    # 4b otherwise: kill the pane.
    # BOTH arms verify through `verify_pids_gone`, whose every signal passes `ident_is_live_harness`
    # — identity re-derived from /proc at the instant of signalling, so a recycled pid can never be
    # hit. Pane ancestry is no substitute: G-12's in-place respawn puts the replacement under the
    # SAME pane, so an ancestry test would confirm the very process it must protect.
    same_cell = None
    if relaunching and in_place:
        ok, rerr = coord.tmux_respawn_pane(pane, descriptor["cwd"])
        if ok:
            same_cell = pane
        else:
            print(coord.c(f"respawn-in-place FAILED ({rerr}) — falling back to kill+split, which "
                    f"re-tiles this window", coord.C_DEAD), file=sys.stderr)
            in_place = False
            coord.tmux_kill_pane(pane)
            lifecycle_record_step(base, seat_name, "respawn-failed-fell-back-to-kill")
    elif pane:
        ok, kerr = coord.tmux_kill_pane(pane)
        if not ok:
            print(coord.c(f"WARNING lifecycle-exec: `tmux kill-pane -t {pane}` reported {kerr!r}. The "
                    f"process check below is what decides whether the session is actually gone.",
                    coord.C_DEAD), file=sys.stderr)
    survivors, note = process.verify_pids_gone(old_idents)
    if survivors:
        # G-10: kill-pane SIGHUPs the process group and a blocked harness survives it as a ghost
        # the roster never mentions. The reaper is ARMED before the alarm — it outlives this
        # process, which the alarm's exit is about to end — and then the failure is reported. A
        # ghost holding a seat's memory is not something a renewal may launch on top of.
        process.arm_pid_reaper(old_idents)
        lifecycle_alarm(
            "state",
            f"the outgoing harness of '{seat_name}' DID NOT DIE — {note} A detached reaper has "
            f"been armed for pid(s) {', '.join(str(p) for p, _ in survivors)}, but this sequence "
            f"STOPS here rather than launching a successor on top of a ghost that still holds the "
            f"seat's memory. Confirm the pid(s) are gone, then bring the seat back by hand: "
            f"{coord.coord_invocation(args)} launch --only {seat_name}",
            3, base, args=args,
            failure=(f"the outgoing harness survived kill-pane, SIGTERM and SIGKILL "
                     f"({', '.join(str(p) for p, _ in survivors)}); a reaper was armed and the "
                     f"sequence stopped before any relaunch"))
    lifecycle_record_step(
        base, seat_name,
        ("respawned-in-place:" + pane if same_cell else
         ("killed:" + pane if pane else "no-pane-recorded-nothing-to-kill"))
        + (f" ({note})" if note else ""))

    if relaunching:
        # ---- THE RAM GATE, immediately before the spend it gates. ---------------------------
        lifecycle_memory_gate(args, base)

        # ---- STEP 5: RELAUNCH THE SUCCESSOR. -----------------------------------------------------
        # The deterministic keystroke path — `prompt_file` -> `harness_command` -> `wake` (which
        # refuses multi-line) -> `wait_harness_up`. On a RENEW no boot-prompt change is needed:
        # `boot_prompt` already tells a non-ephemeral seat to read its `memory.md` as its memory
        # from prior sessions of this seat, which is where the checkout's handoff block landed.
        #
        # ---- 7.32 leaves (ii)+(iii): A REVIVE TRIES THE HARNESS'S OWN RESUME FIRST. --------------
        # A renew followed a CHECKOUT, so its predecessor wrote a handoff and recreation is the
        # correct act. A REVIVE follows a CRASH: there is no handoff, and the conversation the dead
        # process was holding still exists in the harness's own store. Recreating from `seat.md`
        # there discards it — CMP-21 invariant 4's "recreation, not resurrection", which is what
        # 7.32 leaf (ii) exists to close. So: resume from the sessions row when the ROW ALONE can
        # drive it, else the restarter-agent fallback (leaf (iii)). The step recorded says WHICH,
        # because "the seat came back" is true of both and they are different facts.
        resume_ref, resume_why = (coord.sessions_resume_ref(args, seat_name) if not checked_out
                                  else (None, "renew: the predecessor checked out and handed off"))
        boot = None
        if resume_ref:
            boot = coord.REORIENT_NUDGE
        elif not checked_out:
            boot = coord.restarter_prompt(descriptor, args, resume_why)
        lifecycle_record_step(base, seat_name,
                              (f"resume-native:{resume_ref['harness']}:"
                               f"{resume_ref['native-session-id'] or 'cwd-implicit'}") if resume_ref
                              else (f"resume-REFUSED-fallback-restarter: {resume_why}"
                                    if not checked_out else "renew-recreates-from-descriptor"))
        new_pane, lerr = launch.launch_seat(descriptor, args, target, prompt=boot, pane=same_cell,
                                     resume=resume_ref)
        # ---- 7.32 leaf (iii), THE SECOND TRIGGER: A CORRUPT TRANSCRIPT. -------------------------
        # `_Restart path (R4):_` names TWO fallback triggers — *"a non-resumable harness OR a
        # CORRUPT TRANSCRIPT"* — and `sessions_resume_ref` can only see the first: it reads the ROW
        # and nothing else BY CONSTRUCTION (that is 7.37 criterion 4's whole test), so a row that
        # names a conversation the harness can no longer open looks perfect to it. That failure
        # therefore surfaces where it actually happens — the harness refusing to come up — and it
        # falls back HERE rather than stranding the seat on a broken resume. Validating the
        # transcript in the reader instead would consult a second source and destroy the claim.
        #
        # ⚠ ONE RETRY, AND ONLY OFF THE RESUME PATH. `same_cell` is dropped: the resume attempt may
        # have consumed the in-place respawn, so the fallback re-places rather than assuming a cell
        # it no longer owns. A fallback that itself fails takes the normal alarm below — this is a
        # second CHANCE, never a loop.
        if resume_ref and (lerr or not new_pane):
            lifecycle_record_step(base, seat_name,
                                  f"resume-FAILED-at-harness-fallback-restarter: "
                                  f"{lerr or 'launch_seat returned no pane'}")
            new_pane, lerr = launch.launch_seat(
                descriptor, args, target,
                prompt=coord.restarter_prompt(descriptor, args,
                                        f"the recorded session {resume_ref['native-session-id'] or 'in this workdir'} "
                                        f"would not reopen — {lerr or 'the harness did not come up'}"))
        if lerr or not new_pane:
            lifecycle_alarm(
                "state",
                f"THE RELAUNCH FAILED and '{seat_name}' IS CLOSED AND NOT BACK — "
                f"{lerr or 'launch_seat returned no pane'}. This is the outcome the whole sequence "
                f"is ordered to avoid, and it STOPS here: nothing further is verified or cleared, "
                f"so the awaiting-close debt and this marker both stay on the books where "
                f"`status` and `workers` will keep showing them. Bring the seat back by hand: "
                f"{coord.coord_invocation(args)} launch --only {seat_name}",
                3, base, args=args,
                failure=(f"the relaunch (step 5) failed — {lerr or 'launch_seat returned no pane'} "
                         f"— the seat is CLOSED AND NOT RELAUNCHED"))
        lifecycle_record_step(base, seat_name, f"relaunched:{new_pane}"
                              + (" (same pane, layout intact)" if same_cell else ""))

    # ---- STEP 6: THE ROSTER MUST NOT LIE ABOUT THIS SEAT. ---------------------------------------
    # ⚠ WHAT IS ACTUALLY CHECKABLE HERE, AND WHY IT IS NOT "the row shows the successor's pane".
    # NOTHING on the launch path writes a roster row: `launch_seat` opens the pane and starts the
    # harness, and the ROW is written by the successor's own `checkin` — minutes later, from inside
    # the new session. So at this instant the honest invariant is the NEGATIVE one, and it is the
    # G-11 family: the roster may not carry an ACTIVE row for this seat pointing at a pane that is
    # no longer the seat's. The checkout flipped the row inactive; an ACTIVE row here means either
    # the checkout never happened or a stale row survived, and both are the roster claiming a
    # session that is not there.
    #
    # ⚠⚠ AND THAT INVARIANT IS TRUE ONLY BECAUSE A CHECKOUT RAN — SO IT IS GATED ON `checked_out`
    # (`s3-07`). "The checkout never happened" is not a defect on a `revive`; it is the DEFINITION
    # of one. A crashed session flips nothing, so its roster row is STILL ACTIVE on the pane that
    # died — which is the very conjunct (`roster_absent` / GHOSTROW) Stage 4's detector fires the
    # revival ON. Left ungated, this alarm would kill every revive whose pane could not be
    # respawned in place (`new_pane` differs → the test trips), i.e. exactly the crashed seats
    # revival exists for. The stale row is the crash's own signature, not a lie this executor
    # introduced, and it is superseded the moment the successor writes its own row at check-in.
    # It is RECORDED rather than repaired: repairing a roster row is `close-seat`'s act, and this
    # executor holds no seat identity to perform one with.
    row = coord.current_row(coord.load_workers(base)[2], seat_name)
    row_pane = str((row or {}).get("pane") or "")
    row_active = bool(row) and (row or {}).get("active") == "yes"
    if checked_out and row_active and row_pane != new_pane:
        lifecycle_alarm(
            "state",
            f"the roster still carries an ACTIVE row for '{seat_name}' on pane {row_pane or '(none)'}"
            + (f", which is NOT the successor's pane {new_pane}" if new_pane
               else ", and this close killed that pane") +
            ". A row reading ACTIVE for a session that is not there is the G-11 lie, and it is what "
            "every other seat routes messages by. Fix the roster before anything reads it: "
            f"{coord.coord_invocation(args)} close-seat {seat_name}",
            3, base, args=args,
            failure=(f"the roster shows an ACTIVE row for the seat on {row_pane or '(no pane)'} "
                     f"after the session was taken down"))
    lifecycle_record_step(base, seat_name, "roster-verified:" + (
        (f"active on {row_pane}"
         + ("" if checked_out else " — STALE, left by the crash; the successor writes its own "
                                   "at checkin"))
        if row_active else "no active row — the successor writes its own at checkin"))

    # ---- STEP 7: THE TRANSCRIPT THE CHECKOUT EXPORTED. ------------------------------------------
    # ⚠⚠ THIS STEP READS THE ONE ENDING STORE [spec-state-store §1.2, §4.1 Row A], and that read is
    # a REPAIR, not a refactor. It used to ask `load_awaiting(base)` — and `awaiting-close.json`
    # went away with §4.1's second ending writer, so that call has answered a permanent `{}` since.
    # Every field below was therefore absent BY CONSTRUCTION on every checked-out act: `exported`
    # False, `path` empty, `since` unparseable. The first alarm is unconditional and
    # `lifecycle_alarm` exits, so EVERY `checkout --renew` reached this line and died here with
    # `NO EXPORTED TRANSCRIPT` — a renewal that had just exported a perfectly good transcript,
    # refused by the step written to protect it. A guaranteed-false alarm is worse than no alarm:
    # it is the one every reader learns to skip past, including on the run where it is true.
    #
    # THE SUCCESSOR FACT NEEDS NO SECOND FILE. `cmd_checkout` stamps the exported path AS the
    # ending row's `evidence_pointer` and falls back to a non-path token when no export landed, so
    # `ending_transcript` (top of this file) answers "the transcript, or nothing" from the pointer
    # alone. The separate `exported` flag has no successor because it never carried anything the
    # pointer does not — that pair WAS the dual record §4.1 deleted.
    #
    # The FILE is still checked and not only the pointer, for `reap_blockers`' stated reason: a
    # recorded path whose file has since gone is not a transcript.
    #
    # ⚠ SKIPPED WHOLE ON A NO-CHECKOUT ACT (`s3-07`), and an ENTRY IS STILL RECORDED. There is no
    # awaiting-close record to read — guard 4 REFUSED if one existed — so every branch below would
    # alarm on a `revive`, on the fact that a crash produced no export. The substitute entry keeps
    # the marker POSITION-FOR-POSITION alignable with a renewal's (which is how `s3-07`'s row 4
    # proves `revive` reuses this body rather than a copy that quietly drops a verification), and
    # it says WHY the transcript is missing instead of leaving a gap a reader must interpret.
    # Nothing re-exports it: the pane and its scrollback died with the session.
    if not checked_out:
        lifecycle_record_step(base, seat_name, "no-checkout-no-transcript-to-verify")
    else:
        try:
            record = coord.ending_store.get_current_ending(
                coord.package_dir(args, register=False), seat_name) or {}
        except coord.ending_store.EndingStoreError as _ev_exc:
            # UNREADABLE IS NOT ABSENT. The store being unreachable says nothing about whether a
            # transcript was exported, and alarming `NO EXPORTED TRANSCRIPT` on it would report the
            # wrong break — the same conflation of "cannot establish" with "established false" that
            # `attest_exit_blockers` refuses on its own snapshot read.
            lifecycle_alarm(
                "state",
                f"the ending store could not be read for '{seat_name}', so this act cannot "
                f"establish whether its checkout exported a transcript — {_ev_exc}. Refusing "
                f"rather than assuming: an unreadable store is evidence in neither direction.",
                3, base, args=args,
                failure=(f"the ending store was unreadable at the transcript verification step — "
                         f"{_ev_exc}"))
        tpath = ending_transcript(record)
        if not tpath:
            lifecycle_alarm(
                "state",
                f"'{seat_name}' has NO EXPORTED TRANSCRIPT recorded for this checkout "
                f"(the ending row's evidence pointer is "
                f"{record.get('evidence_pointer') or '(none)'!r}, which names no file), so the "
                f"session that just ended left no readable account of itself. The pane is already "
                f"down and the scrollback went with it, which is why this is reported rather than "
                f"repaired: nothing can re-export a pane that no longer exists.",
                3, base, args=args,
                failure=("no exported transcript is recorded for this checkout — the session ended "
                         "with no readable account of itself"))
        if not Path(tpath).exists():
            lifecycle_alarm(
                "state",
                f"the transcript recorded for '{seat_name}' is NOT ON DISK: {tpath}. The record "
                f"says exported, the file says otherwise, and the pane it came from is already "
                f"down.",
                3, base, args=args,
                failure=f"the recorded transcript {tpath} is not on disk")
        # ⚠ THE STALENESS TEST'S CLOCK IS NOW UNAMBIGUOUS, AND ITS SLACK IS NOW DECLARED. It used
        # to parse `awaiting-close.json`'s `since`, stamped through `now()` ("%Y-%m-%d %H:%M") in
        # LOCAL time. Two things were wrong with that and only one of them was the file: the
        # comparison was timezone-naive, and its tolerance was an ACCIDENT OF STRING GRANULARITY —
        # truncating to the minute happened to forgive a transcript written just before its own
        # record, which is EVERY transcript, because `export_transcript` runs before the stamp
        # that points at it. The ending row's `stamped_at` is ISO-8601 UTC to the millisecond, so
        # comparing it raw would have made this alarm fire on every honest checkout — the same
        # always-true shape this step was just repaired from, reintroduced by a precision upgrade.
        #
        # So the tolerance is a NAMED CONSTANT instead of a rounding artifact. It is set at the
        # bound the old truncation could reach, so nothing this used to forgive is newly refused.
        # What it catches is unchanged and is the case that matters: a file left over from an
        # EARLIER session of the same seat, which is a stale export wearing a fresh record's name,
        # and which pre-dates its record by a whole session rather than by the length of one
        # check-out's own bookkeeping.
        stale_note = ""
        _stamped_at = str(record.get("stamped_at") or "").strip()
        try:
            checkout_at = datetime.fromisoformat(
                _stamped_at[:-1] + "+00:00" if _stamped_at.endswith("Z") else _stamped_at)
            if checkout_at.tzinfo is None:
                checkout_at = checkout_at.astimezone()
        except (ValueError, TypeError):
            checkout_at = None
            stale_note = " (ending stamp unreadable — freshness not established)"
        if (checkout_at is not None
                and Path(tpath).stat().st_mtime
                < checkout_at.timestamp() - TRANSCRIPT_PRECEDES_STAMP_SLACK_S):
            lifecycle_alarm(
                "state",
                f"the transcript recorded for '{seat_name}' PRE-DATES its own checkout: {tpath} "
                f"was last written before {_stamped_at}. That is an earlier session's "
                f"export carried on this checkout's ending row, so the session that just ended is "
                f"unaccounted for.",
                3, base, args=args,
                failure=f"the recorded transcript {tpath} pre-dates the checkout it is filed under")
        lifecycle_record_step(base, seat_name, f"transcript-verified:{tpath}{stale_note}")

    if relaunching:
        # ---- STEP 8: THE SUCCESSOR IS ACTUALLY RUNNING (G-11). ----------------------------------
        # `wait_harness_up` inside `launch_seat` already refuses on POSITIVE absence, but it
        # deliberately returns "" when liveness is UNVERIFIABLE — so a launch can succeed on
        # "cannot tell". This asks the question again, at the end, and records the answer as the
        # marker's own evidence that a row reading ACTIVE would not be a lie this time.
        new_idents = process.pane_harness_idents(new_pane)
        if not new_idents:
            lifecycle_alarm(
                "state",
                f"'{seat_name}' RELAUNCHED INTO {new_pane} BUT NO HARNESS IS RUNNING THERE. That is "
                f"G-11 exactly: a start line the pane's shell swallowed while everything upstream "
                f"reported success. The seat is not back, whatever the pane looks like. Capture it "
                f"to see what the shell did: tmux capture-pane -p -t {new_pane}",
                3, base, args=args,
                failure=(f"the successor pane {new_pane} carries NO harness process (G-11) — the "
                         f"relaunch reported success and the seat is not running"))
        lifecycle_record_step(
            base, seat_name,
            "successor-alive:" + ",".join(f"{p}:{s}" for p, s in new_idents))

    # ---- STEP 9: SETTLE THE DEBTS THE CHECKOUT OPENED. ------------------------------------------
    # ⚠ THIS IS THE ANSWER `s12-07` DEFERRED TO STAGE 3, and it is what releases `reap_blockers`'
    # `disposition=renew` hold: that blocker is the checkout's ASSERTION that a renewal is in
    # flight, and it is cleared by the act that COMPLETES the renewal — this one. `clear_awaiting`
    # is `close-seat`'s and is reused, not re-implemented; `clear_closing` goes with it for G-21's
    # reason — a closing flag that outlives its seat would quietly filter a live successor's
    # messages. Both are notes, never failures: the sequence has already succeeded by here, and a
    # debt that could not be cleared is visible in `status` rather than fatal.
    #
    # ⚠ THIS STEP IS **NOT** GATED ON `checked_out`, AND THAT IS A DECISION, NOT AN OVERSIGHT
    # (`s3-07`). A `revive` has no awaiting-close record by construction — guard 4 refused if one
    # existed — so `clear_awaiting` is a no-op that answers False and prints nothing. `clear_closing`
    # is NOT a no-op: a closer may have been engaged on the seat when it CRASHED, and G-21's whole
    # hazard is a closing flag outliving the session it narrowed — which is exactly what a revived
    # successor would inherit. Gating this step off would have re-opened G-21 on the one path where
    # nothing else clears the flag. Both calls are already absence-safe, so the correct widening
    # here was to widen NOTHING.
    if coord.clear_closing(base, seat_name):
        print(f"inbox: '{seat_name}' closing state cleared")
    lifecycle_record_step(base, seat_name, "awaiting-and-closing-cleared")

    # ---- STEP 10: THE MARKER IS DONE. -----------------------------------------------------------
    # `finish_lifecycle`, never `clear_lifecycle`: a successful renewal FLIPS to `done` and the
    # entry stays until `close-run` sweeps it, because it is the only record that the renewal
    # happened out of pane at all.
    if not finish_lifecycle(base, seat_name, "done"):
        lifecycle_alarm(
            "state",
            f"the {args.disposition} sequence for '{seat_name}' COMPLETED, but its marker could "
            f"NOT be flipped `done`. Everything above actually happened; the record does not say "
            f"so, and an entry left `in-flight` with a dead executor reads as a FAILED renewal to "
            f"Stage 4 once LIFECYCLE_STALE_MIN elapses. Reported rather than left to be "
            f"rediscovered as a phantom failure.",
            3, base, args=args,
            failure=(f"the {args.disposition} sequence completed and the marker could not be "
                     f"flipped done — the work landed, the record did not"))
    print(f"lifecycle-exec: {args.disposition} COMPLETE for '{seat_name}'"
          + (f" — relaunched in {new_pane}"
             + (" (same pane, layout intact)" if same_cell else "") if relaunching else ""))
    return new_pane


def cmd_lifecycle_exec(args):
    """THE DETACHED LIFECYCLE EXECUTOR — entry guards (`s3-05`) plus the disposition sequences
    (`s3-06`).

    ALL ARGV, NOTHING FROM THE ENVIRONMENT. `--package` is never inferred: the caller resolves it
    (`package_dir`) and passes it absolute. Everything this process needs to decide is on its
    command line or in the run package's own files; the environment is scrubbed, not read.

    THE FIVE GUARDS, IN THIS ORDER, BEFORE THE EXECUTOR ACTS ON ANYTHING:
      1. scrub the environment AGAIN, at entry;
      2. validate `--tmux-target` — empty or unresolvable REFUSES and acts on nothing;
      3. the ADOPTION CHECK — never a second executor on one seat;
      4. cross-verify the disposition against `awaiting-close.json` THROUGH `LIFECYCLE_INTENT_OF`;
      5. record the inherited log path into the marker (the executor does NOT open the log).

    The `renew` handoff re-read sits between 4 and 5: `--handoff-written` is the caller's
    ASSERTION, and an assertion the executor can cheaply re-verify is one it must re-verify. It
    reads `memory.md` through the LANDED reader (`handoff_blocks` / `handoff_truncated`, `s12-06`)
    and never a fresh regex; it READS ONLY — writing, rewriting or parsing `memory.md` beyond the
    delimiters is out of scope and belongs to `s12` (R-14).

    ⚠ WHAT THIS FUNCTION DOES NOT DO. The caller-side fork is `s3-09`'s. `revive` (`s3-07`) is now
    a full member of the enum and passes through every guard above unchanged: guard 4 takes its
    `LIFECYCLE_INTENT_ABSENT` branch (no checkout happened, so a record is the fault and its ABSENCE
    is the healthy state), and the handoff re-read below is keyed on `renew` so a crashed session is
    never asked for a block it had no turn boundary to write. Past the five guards it hands off to
    `run_lifecycle_sequence` (`s3-06`), which
    owns every act and leaves through `lifecycle_alarm` (`s3-08`) on any failure. THE EXIT-CODE
    SPLIT IS PRESERVED AND IS THE CONTRACT: 2 = a GUARD refused this invocation, 3 = the guards
    passed and the SEQUENCE broke. A marker is never left `in-flight` on a failure — that reads as
    a renewal in progress, which is the one reading Stage 4 must never be given wrongly.
    """
    # ---- GUARD 1: SCRUB THE ENVIRONMENT, AT ENTRY, BEFORE ANY OTHER STATEMENT. ------------------
    # The full argument for popping these a second time is on LIFECYCLE_SCRUB_ENV above. What is
    # RECORDED is which ones were actually present: that is evidence about the CALLER, and the day
    # a future caller forgets its own scrub, the marker says so instead of the room guessing.
    scrubbed = sorted(v for v in LIFECYCLE_SCRUB_ENV if os.environ.pop(v, None) is not None)

    # ---- GUARD 2: VALIDATE `--tmux-target`. Empty or unresolvable -> refuse, act on nothing. ----
    # Deliberately BEFORE the package is resolved: `base_dir` registers the run tag, and a guard
    # whose whole claim is "it acted on nothing" must not have written a registry entry first.
    target = str(getattr(args, "tmux_target", "") or "").strip()
    if not target:
        lifecycle_alarm(
            "input",
            "--tmux-target is EMPTY. This executor has neither COORD_LAUNCH_TARGET nor TMUX_PANE "
            "(guard 1 popped both) and it will NOT fall back to them the way cmd_close_seat does: "
            "with both unset tmux resolves an empty target to the MOST RECENT session, which was "
            "measured to be the LIVE room. Acting on nothing instead. The caller (s3-09) must "
            "pass the pane or window id it measured.", 2, args=args)
    target_ok, why = lifecycle_target_live(target)
    if not target_ok:
        lifecycle_alarm(
            "environment",
            f"--tmux-target {target!r} is unusable: {why}. Refusing and acting on nothing — a "
            f"lifecycle act aimed at a target tmux cannot resolve would land wherever tmux picks, "
            f"and opening a session into the wrong room is worse than not opening one at all.",
            2, args=args)

    base = coord.base_dir(args)

    # ---- GUARD 3: THE ADOPTION CHECK — never a second executor on one seat. ---------------------
    # ⚠ `ident_is_live_process` OFFERS NO "CANNOT TELL" (s3-02): a zombie and an unreadable /proc
    # BOTH answer False = gone. So this guard has exactly two outcomes and must not be written as
    # if a third existed. False here therefore means "no live executor holds this seat", and this
    # process proceeds and SUPERSEDES the older entry — which is correct and is the only thing that
    # keeps a seat whose executor died from being unrecoverable forever. The cost is stated rather
    # than hidden: the superseded entry's own record (its steps, its failure text) is overwritten,
    # so the fresh stamp is the only surviving account of the seat from this point on.
    #
    # The condition is the COMPLEMENT of `lifecycle_stale`'s conjunct 3 — in-flight WITH a live
    # executor is MID-RENEWAL. `lifecycle_line` deliberately never reports that class, so this
    # refusal cannot be phrased in its vocabulary and does not try to: it names the live executor
    # and stands down.
    existing = load_lifecycle(base).get(args.seat)
    if isinstance(existing, dict) and existing.get("state") == "in-flight":
        held = lifecycle_ident(existing.get("executor"))
        if held and process.ident_is_live_process((held["pid"], held["starttime"])):
            steps = existing.get("steps-completed")
            steps = [str(s) for s in steps] if isinstance(steps, list) else []
            lifecycle_alarm(
                "state",
                f"STANDING DOWN — seat {args.seat!r} is ALREADY IN FLIGHT: its marker is "
                f"`in-flight` and its recorded executor (pid {held['pid']}, starttime "
                f"{held['starttime']}) IS STILL RUNNING. That is a renewal in progress, not a "
                f"stuck one. Last verified step: "
                f"{steps[-1] if steps else 'NONE — it has not verified a step yet'}. A second "
                f"executor on one seat is the double-launch this marker exists to prevent, so "
                f"this process acts on NOTHING and leaves the other one's record untouched.",
                2, base, args=args)

    # ---- GUARD 4: CROSS-VERIFY THE DISPOSITION, THROUGH THE MAPPING. ----------------------------
    # The full argument for the mapping (and for why raw equality refuses the NORMAL path) is on
    # LIFECYCLE_INTENT_OF above.
    if args.disposition not in LIFECYCLE_INTENT_OF:
        lifecycle_alarm(
            "state",
            f"--disposition {args.disposition!r} is accepted by the parser but has NO row in "
            f"LIFECYCLE_INTENT_OF, so this executor cannot tell what checkout intent it should "
            f"correspond to. The enum and the mapping were widened apart; widen both.", 2, base, args=args)
    expected = LIFECYCLE_INTENT_OF[args.disposition]
    pkg = coord.package_dir(args, register=False)
    try:
        _ending = coord.ending_store.get_current_ending(pkg, args.seat)
    except coord.ending_store.EndingStoreError:
        _ending = None
    record = ({"disposition": (
        "renew" if _ending and _ending.get("ending") == "incomplete"
        and _ending.get("diagnostic") == "context full"
        else (_ending or {}).get("ending")
    )} if _ending else None)
    if record is not None and not isinstance(record, dict):
        lifecycle_alarm(
            "state",
            f"awaiting-close.json holds an entry for {args.seat!r} that is not a record but a "
            f"{type(record).__name__}. The checkout intent is unreadable, and this executor never "
            f"proceeds on an intent it cannot read.", 2, base, args=args)
    if expected is LIFECYCLE_INTENT_ABSENT:
        # `revive` (s3-07): there was no checkout, so there must be no record. This branch was
        # written by s3-05 and UNREACHABLE until this task mapped `revive` here; it is now the
        # normal path of every revival, and its refusal arm is the one that catches a `revive`
        # fired at a seat that actually checked out.
        if record is not None:
            lifecycle_alarm(
                "state",
                f"--disposition {args.disposition} means NO checkout happened, but "
                f"awaiting-close.json HOLDS a record for {args.seat!r} "
                f"(disposition={str(record.get('disposition', 'done'))!r}). Absence is legal for "
                f"this disposition only, and this is not absence.", 2, base, args=args)
    elif record is None:
        lifecycle_alarm(
            "state",
            f"--disposition {args.disposition} requires the checkout that DECLARED it, and "
            f"awaiting-close.json holds NO record for {args.seat!r}. The intent is stated once, at "
            f"checkout, and this executor does not infer one that was never written.", 2, base, args=args)
    else:
        # `.get("disposition", "done")`, NEVER `record["disposition"]` — run packages written
        # before s12-07 hold records with no such key, and `done` is what those records meant.
        declared = str(record.get("disposition", "done"))
        # 7.676: MEMBERSHIP, not equality — `expected` is the TUPLE of intents this argv action
        # legitimately tears down (see LIFECYCLE_INTENT_OF). The guard is unweakened: it still
        # refuses every value the action does not admit, and `renew`'s tuple admits exactly one.
        if declared not in expected:
            lifecycle_alarm(
                "state",
                f"DISPOSITION SKEW on seat {args.seat!r} — argv says --disposition "
                f"{args.disposition!r}, which maps to the checkout intent(s) "
                f"{', '.join(repr(e) for e in expected)}, but "
                f"awaiting-close.json records disposition={declared!r}. The record is the "
                f"assertion made at the one moment the intent was known; argv is a copy that "
                f"travelled. Acting on nothing rather than picking a side.", 2, base, args=args)

    # ---- The `renew` handoff re-read. `--handoff-written` is the caller's ASSERTION. ------------
    # ⚠ `revive` (s3-07) passes 0 and MUST NOT require a block: a crashed session had no turn
    # boundary at which to write one, so requiring it would make revival impossible in exactly the
    # case revival exists for. THAT IS WHY THIS IS KEYED ON `renew` AND NOT ON `relaunching` — the
    # relaunching set now holds both, and the day someone "simplifies" this line to the boolean two
    # lines of code apart, every crash becomes unrecoverable. The refusal itself is s3-07's row 3.
    #
    # ⚠ AND THE PREDECESSOR'S LAST UNREAD BLOCK IS LEFT EXACTLY WHERE IT IS. This executor READS
    # `memory.md` and never writes it (R-14); the `unread=` attribute is s12-08's cursor, flipped at
    # the SUCCESSOR's check-in, and a revived successor is handed its predecessor's block by that
    # same mechanism (the s12-08 header's keyed-on-(seat, unread) clause). s3-07's row 6 asserts the
    # file's bytes are unchanged across a revive for that reason.
    if args.disposition == "renew":
        if args.handoff_written is None:
            lifecycle_alarm(
                "input",
                "--handoff-written is REQUIRED on --disposition renew: the successor session is "
                "handed the block this flag claims exists, and an unasserted claim cannot be "
                "re-verified.", 2, base, args=args)
        if str(args.handoff_written) == "1":
            memory = coord.workers_dir(args) / args.seat / "memory.md"
            try:
                text = memory.read_text(encoding="utf-8")
            except OSError:
                text = ""
            # Through the LANDED reader (s12-06), never a fresh regex over memory.md: the writer
            # and the reader must not hold two opinions about what a block looks like. READ ONLY —
            # this executor never writes, rewrites, or parses memory.md beyond the delimiters
            # (R-14; the one sanctioned memory touchpoint is s12's checkout).
            if not coord.handoff_blocks(text):
                # `handoff_truncated` is the WRITER's own refusal test, reused rather than
                # re-derived: a half-written block must look the same to both sides.
                shape = ("the file's LAST delimiter is an OPENER, so a block was half-written and "
                         "memory.md is TRUNCATED" if coord.handoff_truncated(text)
                         else "no delimiter pair is present at all")
                lifecycle_alarm(
                    "state",
                    f"--handoff-written 1 claims this seat's checkout WROTE a handoff block, "
                    f"but {memory} carries NO COMPLETE block — {shape}. Renewing on that claim "
                    f"would open the successor with nothing carried over, which is the one "
                    f"artifact the whole ceremony exists to produce.", 2, base, args=args)

    # ---- GUARD 5: RECORD THE LOG PATH — the executor does NOT open the log. ---------------------
    # `s3-09` owns opening `{base}/lifecycle-exec-{seat}-{stamp}.log` and handing it over as this
    # process's stdout/stderr. The duty HERE is only to RECORD where that evidence landed, so a
    # reader of the marker can find it. Reading it back from /proc rather than recomputing a name
    # is what guarantees ONE stamp per run.
    log_path, log_note = inherited_log_path()
    stamped = stamp_lifecycle(base, args.seat, {
        "disposition": args.disposition,
        # This process's own identity, in the (pid, starttime) form watch.py's revival detector
        # reads. `stamp_lifecycle` normalizes it; the tuple is handed over deliberately, because
        # the store owning that normalization is what keeps every writer honest.
        "executor": (os.getpid(), process.proc_stat(os.getpid())[1]),
        # The forking caller's identity, as the caller measured it — the input to `s3-06`'s settle
        # wait (LIFECYCLE_SETTLE_S) and to the died-mid-flight evidence.
        "caller": (args.caller_pid, args.caller_starttime),
        "pane": str(args.pane or ""),
        "tmux-target": target,
        "log": log_path,
        "log-note": log_note,
        # Which of the four the caller leaked into this process. Empty is the healthy answer.
        "scrubbed": scrubbed,
    })
    if not stamped:
        lifecycle_alarm(
            "environment",
            f"the lifecycle marker for seat {args.seat!r} could NOT be written, so nothing would "
            f"record that this executor ran: no reader could see it start, and Stage 4 could never "
            f"see it fail. Refusing before acting rather than acting unrecorded.", 2, args=args)

    # ---- PAST THE GUARDS: THE DISPOSITION SEQUENCE (`s3-06`). ----------------------------------
    # Every guard above has passed and the marker is stamped `in-flight` with this process's own
    # identity. From here the sequence owns the outcome: it flips the marker `done` when it
    # completes, and every failure inside it leaves through `lifecycle_alarm` with exit 3 — so
    # this call either returns having finished, or does not return at all.
    run_lifecycle_sequence(args, base, target)
