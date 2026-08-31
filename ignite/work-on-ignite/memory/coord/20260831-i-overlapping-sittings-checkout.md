# 20260831-i-overlapping-sittings-checkout — Overlapping sittings: checkout closed wrong row + tz hazard

kind: issue
component: coord
date: 2026-08-31
commit: fa0f50f1
deployed: no
pin: NONE
components: supervisor

## Observed
Build tasks 95/135 (`coord-skew`, 2026-08-31) surfaced a SEPARATE live defect while proving the
SKEW verdict class closed: `records.py#session_close` selects the row to close by "LAST OPEN ROW
in file order" unconditionally. Two open `sessions.csv` rows for one seat is the shape a `--renew`
produces (the new sitting's row opens before the old one has checked out) — when the OLDER sitting
then checks out FIRST, `session_close` closed the NEWER sitting's row instead of its own: the older
row leaked open forever, and the newer sitting could never check out at all (the row it would have
closed was already gone). Reported as a `redesign-continue-1` loose end (`#d/must`,
`d-overlap-row-close`), which also folded in a timezone hazard the same seat found in the same
close path: `ignite/supervisor/death-stamp.js#declaredEndingIsStale` compares `sessions.csv`'s
naive `started` (`YYYY-MM-DD HH:MM`, no offset) against an ISO `stamped_at` (explicit `Z`) via
`Date.parse(started)` — non-ISO-format parsing is IMPLEMENTATION-DEFINED per MDN ("support ... is
by convention only"), so the guard measured correct only because this box is `Etc/UTC`.

## Mechanism
`session_close`'s row-selection loop (`for r in rows: ... target = r`) kept overwriting `target`
with each matching open row for the seat, so the LAST one in file order always won — it never
asked "is this row mine". `checkout.py#session_id_open`'s own docstring already names this same
rule ("LAST open row wins, the same rule `session_close` itself applies") as deliberate, unaware
it was the defect. `carrier.carrier_self_session()` (F-6, 2026-08-21) already solved the identical
class for check-in — a process reads its OWN identity (the daemon-minted cgroup unit, or the
calling pane's own (pid, pid-starttime) against the pair `session_open` recorded on the row at
boot) instead of trusting file order — but `session_close` never used it.

## Attempts
First attempt held — checked: F-6 (`checkout.py` `cmd_checkin`, 2026-08-21) is the only prior fix
of this defect CLASS (row selection by unprovable recency), and it only ever covered check-in, not
close. `coord-skew`'s `probe-overlap-sittings.py` (commit `a4de64d8`, memory entry
`20260831-c-overlapping-sittings-probe-pin.md`) pins a DIFFERENT class (SKEW verdict disagreement
between a seat-keyed ending and a session-keyed row) and explicitly walked past this one as outside
its own mission.

## Fix
Added `own_open_row(args, idx, open_rows)` in `records.py`, tried in the SAME order F-6 established:
(1) `carrier.carrier_self_session()` matched against `session-id` (daemon lane), (2) the calling
pane's own `(pid, pid-starttime)` matched against exactly one open row (attached/tmux lane, only
when unambiguous). `session_close` now uses `own_open_row(...) or open_rows[-1]` — identity wins
when provable, and the fallback is BYTE-IDENTICAL to the old behaviour otherwise, so every existing
caller that never resolves an identity (paneless callers with no carrier unit, headers predating
the pid/pid-starttime columns) is unchanged. Rejected: refusing a seat from minting a second open
row outright — `--renew` legitimately opens the new row before the old one closes, so refusing the
mint would break renew; binding by identity is the deeper, non-breaking fix. `death-stamp.js`:
replaced `Date.parse(started)` with `parseStartedLocal` (manual regex + the `Date` CONSTRUCTOR's
per-field form, which ECMA-262 guarantees is always local) — same semantics as V8's current
behaviour, but no longer resting on an implementation-defined fallback.

## Consequences
No production behaviour changes on this box (both fixes preserve today's outcome; they change what
happens off it / off file-order). Four `death-stamp.selftest.js` fixtures wrote `started` in ISO
`Z` form, which never exercised the real naive-local `sessions.csv` shape — converted to the real
`YYYY-MM-DD HH:MM` format (`d-overlap-row-close`'s vacuous-check risk, avoided rather than repeated
a third time this run). No files deleted or renamed.

## Verification
`python3 coord.py selftest` (run from `ignite/coord/`): 24/24 pre-existing failures unchanged
versus a pristine-worktree baseline at the same parent commit (none touch endings/check-out; per
`coord-skew`'s own ATTENTION, grade against that control, never against exit 0) — plus 7 new PASS
arms (`d-overlap-row-close` SETUP/RED/cleanup/FIXED x2/pid-lane). RED-first: the new arm stubs
`own_open_row` to `None` (simulating the pre-fix code path) with a real carrier identity resolving
to the older sitting, and confirms it STILL closes the newer row (mutation-verified). `node
death-stamp.selftest.js`: 13/13 PASS including a new `(tz)` arm run under a real child process with
`TZ=America/New_York`; mutating `parseStartedLocal` back to `Date.UTC`-style parsing turns that arm
RED (confirmed and reverted). Not deployed.

## ATTENTION
1. `own_open_row`'s pid/pid-starttime lane trusts a match only when it is UNAMBIGUOUS (exactly one
   open row agrees) — a caller that gets an ambiguous or zero match falls through to the unchanged
   last-open-row fallback rather than guessing.
2. The `death-stamp.selftest.js` fixtures now write `started` in the REAL naive-local
   `sessions.csv` format; a future fixture that reverts to ISO/`Z` for convenience silently stops
   exercising `parseStartedLocal`'s actual code path and reads green either way.
3. `coord.py selftest` is RED at HEAD for reasons unrelated to endings/check-out (24 failures,
   messaging/capacity rows) — grade any coord change against a pristine-worktree control at the
   same commit, never against exit 0 (same caution `coord-skew` already recorded).
- own_open_row's pid lane trusts only an UNAMBIGUOUS match — ambiguous/none falls back to last-open-row
- death-stamp.selftest.js fixtures must keep the real naive-local started format or parseStartedLocal's path goes untested
- coord.py selftest is RED at HEAD (24 unrelated failures) — grade against a pristine-worktree control, never exit 0
