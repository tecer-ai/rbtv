# 20260902-i-crash-loop-alarm-never-clears — crash-loop alarm never clears; check-ins disagreed

kind: issue
component: coord
date: 2026-09-02
commit: 50d6287ef446ae506aff480dca89716760514ed8
deployed: yes
pin: ignite/coord/crash_loop.py (selftest)
components: supervisor

## Observed
`seat-crash-loop.json` (`crash_loop.py`, built in `abb899e8`) raises an alarm after 2+ pre-checkin
deaths inside a detection window, but once tripped nothing ever cleared an entry — the alarm stayed
armed indefinitely even after the seat later ran cleanly. Separately, `attest.py`'s
`close_session_seat`/`attest_exit_seat` read `checked_in` from `workers.md`, while `crash_loop.py`'s
own `precheckin_deaths` counts pre-checkin deaths from `sessions.csv`'s `checkin` cell — the two
closers could report the wrong "crashed after check-in" vs "crashed before check-in" diagnostic
(consumed by `death-stamp.js`) depending on which table happened to be asked.

## Mechanism
`note_failed_death` (the only place that writes an alarm entry) had no counterpart that ever removed
one — the JSON store at `alarm_path(pkg)` was append/keep-only. For the second edge, `workers.md` and
`sessions.csv` are two independently-written surfaces for the same fact (whether a seat had checked in
before it crashed); `attest.py` trusted the former, `crash_loop.py` counted from the latter, so a race
or lag between the two writers could put a seat's diagnostic on the wrong side of "before/after
check-in" even though the alarm counter itself was correct.

## Attempts
First attempt held — checked: the crash-loop creation entry (`abb899e8`, 2026-08-31,
`ignite/coord/_creations.md`) for whether a clearing path already existed; it did not — the entry
covers only the raise path.

## Fix
Added `prune_stale(pkg, now=None, window_sec=WINDOW_SEC)`: drops any alarm entry once `now` is a full
detection window past its own `raised_at` — the same window that raised it, so the alarm's own
definition ("N deaths inside window_sec") is what ages it back out, with no second config knob.
Called first, unconditionally, at the top of `note_failed_death` — the path already invoked on every
session close (crash or clean) via `supervisor_door.death_stamp` — so the alarm self-heals on the
seat's next close of ANY kind once the window has passed, without needing a hook into
`coord/records.py`'s check-in writer (deliberately out of scope: outside this change's granted files).
Both `attest.py` closers were switched to read `checked_in` from `sessions.csv` (by session id where
held, else the seat's last open row) — the same source and cell `crash_loop.py#precheckin_deaths`
already counts, removing the second independent source instead of reconciling two.

## Consequences
No change to the raise threshold or window semantics. A `done` close that lands INSIDE the window
still leaves the alarm standing (stated as deliberate design, not a bug) — the clear only fires once
the window has actually elapsed, on whichever close (of any ending) happens after that.

## Verification
`crash_loop.py` selftest: 10 arms, 4 new (alarm-still-armed-before-window, prune clears at window
elapsed, alpha re-trips after a clear, a later clean close disarms via the prune-first hook) — all
PASS. The check-in mismatch proven red-first against the real product diagnostic: the old
`workers.md`-sourced path yielded `crash after check-in` (wrong, contradicting the row actually
counted), the new `sessions.csv`-sourced path yields `crash before check-in`. `death-stamp.selftest.js`
run as a regression check, ALL PASS. `coord.py selftest`: 1042 checks, 24 FAIL — verified line-by-line
against this plan's `judge-coord.md` as the same pre-existing set, zero new failures. Deployed live on
deploy tree `e8524c31` (`ignite/core-daemon`).

## ATTENTION
1. The clearing rule is window-based, not check-in-based: an alarm can still read armed for a seat
   that HAS since checked in successfully, until the window elapses on its own — do not "fix" this by
   adding a second, disagreeing clear condition without checking `prune_stale`'s docstring first.
2. `attest.py`'s two closers and `crash_loop.py#precheckin_deaths` must keep reading the SAME check-in
   source (`sessions.csv`'s `checkin` cell) — reintroducing a `workers.md` read in either closer
   reopens the exact "crash after check-in" vs "crash before check-in" mismatch this fix closed.
