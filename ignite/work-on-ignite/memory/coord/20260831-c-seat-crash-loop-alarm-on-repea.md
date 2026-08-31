# 20260831-c-seat-crash-loop-alarm-on-repea — Seat crash-loop alarm on repeated pre-checkin deaths

kind: creation
component: coord
date: 2026-08-31
commit: abb899e8
deployed: no
pin: ignite/coord/crash_loop.py
components: supervisor

## Motivation
Task 98 (redesign-continue-1) required a named crash-loop alarm when the same seat dies pre-checkin ≥2 times in a bounded window, visible outside executions.csv. Grep of `ignite/coord` for `crash-loop|crash_loop` was zero. The daemon-watchdog crash-loop (`observation/daemon-watchdog`, systemd `NRestarts`) is a different alarm and was not reused. Classification of a single pre-checkin death already lived in `supervisor/death-stamp.js#stampDeath` (`ending: failed`, diagnostic `crash before check-in`); this creation does not restamp endings.

## Design
One new module `coord/crash_loop.py`, hooked from `coord/supervisor_door.py#death_stamp` after the supervisor returns — the coord-owned choke point every `attest-exit --force-dead` close already walks (`spawn.js#closeSeatSessionRow` → `cmd_attest_exit` → `close_session_seat` → `supervisor_stamp` → `death_stamp`). Count is read off `sessions.csv` rows for that seat with an empty `checkin` cell and `ended` inside a 3600s window, not off the `checkedIn` flag the closer passes (that flag is sourced from workers.md). Threshold 2; one JSON document `{package}/coordination/seat-crash-loop.json` plus one stderr line named `seat-crash-loop`; a third death in the same episode returns the existing row and does not reprint.

Rejected: stamping in `death-stamp.js` (supervisor JS is outside this custody group; classification there is already done). Rejected: widening `runtime/ticker/ticker.js`'s crash sweep (task 29 / `ticker-crash-sweep` owns that file). Rejected: posting through `observation/emitter.js` from this closer (the emitter requires an injected Slack `post`; T4-R10 forbids a second composer; an alarm is not a wake). Rejected: resurrecting the kit's unconditional `exited` stamp.

## How it works
`death_stamp` still classifies nothing. After `supervisor_op("stampDeath", …)` returns, `crash_loop.observe_failed_death` runs and never raises. `note_failed_death` no-ops unless `result.ending == "failed"`. It then counts pre-checkin ended rows; below threshold it writes nothing. At threshold, if that seat already has an `alarm: seat-crash-loop` key in the package file, it returns that dict. Otherwise it writes the file (count, window, session ids) and prints `seat-crash-loop: seat=… count=…` on stderr. `python3 crash_loop.py` is the selftest.

## Consequences
No ending vocabulary change. `coord.py` was not edited (not a split module; no `save-coord.py`). Owner-facing Slack is not wired — the named record is the package file and the journal line. A follow-up that wants the one emitter would be an ordinary `observation/emitter.js` caller with a `post`, not a second composer in coord.

## Verification
`python3 ignite/coord/crash_loop.py` — ALL PASS (one death silent; two raise once; third does not re-emit; `done` skipped; outside-window skipped; checked-in rows skipped). Scratch `test-` package through `attest.cmd_attest_exit --force-dead`: first close ending `failed` / `crash before check-in`, no alarm file; second close of the same seat writes `coordination/seat-crash-loop.json` and the stderr line; third close leaves the file byte-identical; no `executions.csv`. `node ignite/supervisor/death-stamp.selftest.js` ALL PASS (pre-existing). Not deployed.

## ATTENTION
- Do not reuse `observation/daemon-watchdog`'s `NRestarts` crash-loop as this seat alarm — different subject (unit vs sitting), different evidence.
- Count `sessions.csv` checkin, not workers.md. `attest.py#close_session_seat` still passes `checked_in` from the roster row; a new sitting that dies before check-in while the roster still holds a prior checkin would be mis-labelled `after check-in` in the death stamp even though this alarm still counts the empty sessions.csv cell.
- The alarm file is per-package and never cleared. A later healthy sitting of the same seat does not re-arm it; adding a clear-on-success is a new decision, not an obvious fix.
- Do not reuse daemon-watchdog NRestarts as this seat alarm.
- Count sessions.csv checkin, not workers.md roster checkin.
