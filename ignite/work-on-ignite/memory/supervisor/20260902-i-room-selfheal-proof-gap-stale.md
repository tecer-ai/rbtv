# 20260902-i-room-selfheal-proof-gap-stale — room-selfheal proof gap + stale mutation arm (task 166)

kind: issue
component: supervisor
date: 2026-09-02
commit: ab4b65144e748704fc5dee185f7905d7294ffaac
deployed: yes
pin: ignite/supervisor/probes/probe-room-selfheal-no-leader.js

## Observed
`judge-final` (this plan's `redesign-continue-1` closeout) found two problems with the standing
evidence for task 166 (dead tmux room self-heal reopened idempotently): (1) its only proof lived inside
`reconcile.selftest.js`, which aborts pre-existing at a stale `D35` assertion BEFORE reaching the
room-selfheal arms — confirmed against the parent commit via `git show` (not `git stash`) — so nothing
actually COMMITTED proved 166 green; (2) `probe-lane-room-open.js`, the other probe touching this area,
exited 1.

## Mechanism
`probe-lane-room-open.js` carried a combined mutation arm asserting "the daemon-lane guard is dropped →
BOTH console-owned rooms and paused goals get rooms". At some point after that arm was authored, the
pause check moved to its OWN earlier, independent `laneIsPaused` continue in the production code —
so dropping only the later `lane !== DAEMON` guard can no longer expose a paused goal at all; the
combined assertion had become unsatisfiable by its own mutation, i.e. it was asserting a joint failure
mode the code could no longer produce with that single mutation. Verified pre-existing and unrelated to
`lane-watch.js` (untouched all session — `git diff HEAD -- ignite/supervisor/lane-watch.js` empty).

## Attempts
First attempt held — checked: `reconcile.selftest.js`'s existing room-selfheal arms (the pre-existing
evidence judge-final rejected) — these were never wrong on their own terms, just unreachable because
the suite aborts earlier at the unrelated `D35` fixture bug (see the `0e4a270c` fixture-only fix, same
plan, filed separately as not-required for memory since it made no behaviour change).

## Fix
Added `probe-room-selfheal-no-leader.js`: a self-contained probe against a REAL private tmux server,
independent of `reconcile.selftest.js`, auto-discoverable by `ignite/deploy/probe-suite.js` on its own
(no dependency on the aborting suite reaching it). Four arms: reopen-with-no-leader (the fix in
action), RED (the fix's hunk reverted, proving the room stays dead-forever without it), a
leader-present control (the unrelated, unchanged path stays unchanged), and idempotence on an
already-live room (a second reopen call is a no-op). Separately, split `probe-lane-room-open.js`'s
stale combined mutation arm into two honestly-discriminating arms: a console-only arm (pause stays
protected by its own, now-earlier gate) and a new arm that actually drops the `laneIsPaused` guard
directly, so each arm again tests exactly what its own single mutation can produce.

## Consequences
No production code changed — both files touched are probes/tests only. `probe-lane-room-open.js` now
exits 0. The room-selfheal behaviour itself (task 166/165) is unchanged; only its evidence surface
changed from "unreachable, inside an aborting suite" to "reachable and independently proven".

## Verification
`probe-room-selfheal-no-leader.js`: EXIT 0, 15/15 across the four arms. `probe-lane-room-open.js`: EXIT
0 after the split. `judge-supervisor` re-verdict on relaunch: PASS — both probes EXIT 0, and the judge
independently confirmed the split mutants are each genuinely RED on their own (console-only vs
paused-only), so nothing was weakened to reach green. Deployed live on deploy tree `e8524c31`
(`ignite/core-daemon`).

## ATTENTION
1. `reconcile.selftest.js` still aborts before its own room-selfheal arms whenever the unrelated `D35`
   region breaks — do not treat that suite as proof of task 166/165 behaviour; `probe-room-selfheal-
   no-leader.js` is now the independent, suite-external source of truth for it.
2. A mutation arm that combines two guards into one assertion can go silently unsatisfiable when the
   production code splits those guards apart later — this exact pattern bit `probe-lane-room-open.js`
   once already; a future refactor that merges or reorders `lane-watch.js` guards should re-check
   whether any probe's combined arm still matches a real, single-mutation failure mode.
