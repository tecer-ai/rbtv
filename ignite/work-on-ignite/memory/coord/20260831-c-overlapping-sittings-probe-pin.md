# 20260831-c-overlapping-sittings-probe-pin — Overlapping-sittings probe pins the retired SKEW class

kind: creation
component: coord
date: 2026-08-31
commit: a4de64d8
deployed: no
pin: ignite/coord/probes/probe-overlap-sittings.py
components: supervisor,state-store

## Motivation
Build tasks 95 and 135 both described one class of false permanent SKEW: a SEAT-keyed live ending
surface set against a SESSION-keyed `sessions.csv`. 95 was an out-of-package check-out that wrote
`coordination/awaiting-close.json` with no matching `sessions.csv` row, so `terminal_disposition`
compared THIS sitting to the LAST ENDED row of a DIFFERENT sitting and reported
`SKEW(incomplete|exited)` no leader verb could honestly clear. 135 was two OVERLAPPING sittings of
one seat, where the dying older sitting's kit-attested `exited` landed on top of the newer sitting's
`done` at ~4,589 daemon warnings a day. Both were already closed by other work by the time they were
picked up; nothing on disk PROVED they were closed, and a defect class believed closed with no
executable pin is a defect class that comes back.

## Design
A probe, and no code change — the two fixes already exist and both are load-bearing elsewhere, so
adding a third guard would have been a second source for one rule. The probe is one file because it
pins ONE property: two sittings of one seat cannot mint a permanent disagreement about that seat's
ending. Its three arms are the three ways that property can fail — the older sitting's own
check-out, the older sitting's death, and a second ending writer reappearing — plus a RED arm that
makes the first two falsifiable. The RED was built by mutation rather than by asserting the guard's
source text, because a source-text assertion moves with the code and passes whatever it reads.

## How it works
`ignite/coord/probes/probe-overlap-sittings.py` builds a scratch workspace that ROOTS AN INSTALL
(D27's `.rbtv/modules/ignite/server.json`, never a bare `.rbtv/`), opens two sittings of one seat
with the second starting before the first closes, and drives the real doors. Arm A1: the newer
sitting checks out `done`, the older sitting's later check-out is REFUSED by the roster gate and the
stored `stamped_at` is unchanged. Arm A2: the older sitting dies and `attest.py#close_session_seat`
runs on ITS session-id — the closer originates nothing, `supervisor/death-stamp.js#stampDeath`
returns `confirm-and-reap` with `stamped: false`, and the older sitting's own row is the one closed.
Arm B copies `death-stamp.js` to the fixture with `declaredEndingIsStale` forced to `return true`,
re-points its two relative `require`s at the real tree, and drives `stampDeath` through a small
node driver against the real store: the mutant STAMPS OVER the newer `done`, the shipped module
refuses the identical call. Arm C reads `ready.py#terminal_disposition` on the G-leader-0822-2342
shape and on an absent seat, reads `records.py#undeclared_endings` on an out-of-package sitting that
has an ending and no `sessions.csv` row at all, and evaluates `ready.py#conjunction_admits` on a
hand-built skewed row. `deploy/probe-suite.js` discovers `probes/probe-*` by filename, so the probe
enrolled in the scheduled hourly suite with no registration edit.

## Consequences
Replaced nothing and deleted nothing. It records that `coord.py selftest` is RED AT HEAD
independently of this work: run at pristine `e73d41de` in a detached worktree it exits 1, ABORTED
with 20 failures, all in the messaging/capacity rows (`P2`, `P12`, `P26`, `T2`, `T4`, `workers lag`,
`addressable`, `harness/G-215`) and none touching endings or check-out. Two pre-existing conditions
this probe walked past without touching: `records.py#session_disposition` now has no production
caller (only `coord_selftest.py` reads it) because the `sessions.csv` `disposition` column has had
no writer since spec-state-store §4.1; and every kit probe carries its own copy of the same fixture
helpers (`load_coord`, `_NoTmux`, `make_package`, `ns`, `checkout`).

## Verification
`python3 probes/probe-overlap-sittings.py` — 14/14 checks, exit 0, run three times with identical
output and no residue in the tree or `/tmp`. The RED arm is the falsification: with
`declaredEndingIsStale` mutated to `return true` the same evidence yields
`stamped: true, ending: failed` over the newer `done`. `node deploy/probe-suite.js --list` reports
the probe at `coord/probes/probe-overlap-sittings.py` in a discovery of 234. Live check on the
warning volume 135 measured: `journalctl --user -u rbtv-ignite --since '24 hours ago'` returns 0
lines matching SKEW across 51,555 lines, and the stools `goal-master` seat carries no ending row at
all in the live store. NOT DEPLOYED by this change — probe only, `coord.py` untouched.

## ATTENTION
1. `declaredEndingIsStale` compares `sessions.csv`'s `started` (`YYYY-MM-DD HH:MM`, parsed by
   `Date.parse` as LOCAL time) against `stamped_at` (ISO with a `Z`, parsed as UTC). This box is
   `Etc/UTC`, so the two agree here and the guard is correct as measured — on a box with any other
   zone the comparison is off by the offset, and the guard's own rule is that an unprovable side
   must never read as stale.
2. Do not write a probe's driver or mutant beside its subject. The first cut of arm B put a
   `drive.js` inside `ignite/supervisor/` for the green half — a probe writing into the tree it
   measures, and it appears in `git status` as if a source file had been added.
3. `python3 coord.py selftest` is RED at HEAD for reasons unrelated to endings. Grade a coord change
   against a pristine-worktree control at the same commit, never against exit 0 — this suite's exit
   code cannot currently distinguish your change from the tree you found.
4. The overlap is refused in BOTH directions but by two DIFFERENT mechanisms: the older sitting's
   check-out by the seat-keyed roster gate ("no ACTIVE roster row"), the older sitting's death by
   `declaredEndingIsStale`. A change to either one alone leaves the other half of the class open.
- coord.py selftest is RED at HEAD — grade against a pristine-worktree control, never exit 0
