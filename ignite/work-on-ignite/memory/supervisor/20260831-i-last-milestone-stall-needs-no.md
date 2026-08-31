# 20260831-i-last-milestone-stall-needs-no — last-milestone stall needs no live leader

kind: issue
component: supervisor
date: 2026-08-31
commit: fd2b4399
deployed: no
pin: ignite/supervisor/finish-no-leader.selftest.js
components: coord

## Observed

On `stools-canvas-audio-elevenlabs-close`, `boundary-auditor` completion #45 (M7 PASS, 2026-08-28 22:17) arrived after leader sitting 9 had checked out. Sitting 10 died on HTTP 429 before `coordinate finish-goal`. The last milestone sat unaccepted from 22:18 until 2026-08-30 16:38. Manual patch: the daemon re-opened `leader` (message #46); sitting `a3b4f591` accepted M7 and fired the finish EVENT (#47/#48). Reproduced 2026-08-31 on HEAD against a fixture: last-milestone `completion` present, leader chair empty (done sitting, no live), no `FINISH_MARKER` — `goal_finished` stayed None and reconcile owed/rebuilt the leader. Distinct from finish-gate (task B+153, `34d5b018`): that gate stops resurrection AFTER the EVENT; this stall is BEFORE it fires. Distinct from task 66 (`monitor.js` 429 detection).

## Mechanism

`records.py#cmd_finish_goal` is the only writer of the finish EVENT. Where `taskforce.csv` names `leader`, any other identity is refused (`gate` + `taskforce_leader`). There was no daemon path that, seeing last-milestone complete and no EVENT, called `fire_finish_edge`. Class B would normally relaunch the leader for unread completion mail; a 429-killed sitting plus attempt/budget exhaustion still stalled for days. The finish-gate EVENT reader (`finishEvent`) correctly does nothing until the marker exists, so an empty chair after last-milestone completion is a finished-work, un-finished-goal.

## Attempts

First attempt held — checked: `20260831-i-finished-goals-resurrected-aft` (`34d5b018`, EVENT is canonical; do not re-rule store), `20260827-i-summoned-goal-master-chair-see` (`91da4a8d`, role gate must stay — goal-master must not finish a staffed goal), `20260830-i-stale-done-from-an-earlier-sit` (429 death swallowed by stale done — different file, death-stamp), `20260828-c-the-finish-edge-s-3-line-compl` (ferry already consumes the marker). Retry-until-finish-goal was rejected: the incident already was a 429 on the retry sitting, and re-launching the leader risks re-executing M7-style work.

## Fix

A new coord verb `finish-on-completion` (hidden; daemon-only) fires the same `fire_finish_edge` EVENT, attributed to `ignite-daemon`, never `from: leader`. It admits only `DAEMON_IDENTITY` (and refuses if `COORD_AGENT` is a seated name). It refuses unless every last-milestone seat (taskforce DAG leaf with a `milestone-id`) has posted a non-finish `completion`. `cmd_finish_goal`'s leader role gate is untouched. `reconcileGoal` calls this after the finishEvent skip fails, then treats a fired EVENT as `skipped: 'finished'` so the chair is not relaunched.

## Consequences

Every unfinished reconcile pass now shells `coord.py finish-on-completion` (fast refuse when last milestone is not complete). `HIDDEN_COMMANDS` gained the verb so seats do not see it in `-h`. `coord_selftest.py` s3-03 (7f–7h) was written then withheld from the commit because a sibling seat was concurrently rewriting that 16k-line file. Probe F7–F9 and `finish-no-leader.selftest.js` carry the proof. JS still does not write the marker (one Python writer).

## Verification

`node ignite/supervisor/finish-no-leader.selftest.js` ALL PASS (stall writes EVENT from ignite-daemon; reconcile actions=`finish-on-completion` only; mid-pipeline does not finish; red mutation with `finishOnCompletionFn` disabled resurrects). `python3 ignite/coord/probes/probe-finish-edge.py` 18/18 PASS including F1–F5 and F7–F9. Targeted s3-03 7a/7f/7g/7h via imported `cmd_finish_goal`/`cmd_finish_on_completion` ALL True. `node ignite/supervisor/finish-gate.selftest.js` still OK. Full `python3 coord.py selftest` ABORTED after 702 checks at a pre-existing FileNotFoundError (`capg/seat.md`) — s3-03 never reached. Commit `fd2b4399` on `ignite/core-daemon`. NOT DEPLOYED.

## ATTENTION

- Canonical finish source is the EVENT (`FINISH_MARKER` completion), not `stored='finished'`. This seat writes that same source. Do not stamp the store.
- `cmd_finish_goal` as `goal-master` on a taskforce that names `leader` must still refuse. The daemon door is a different verb with a different identity.
- A mid-pipeline completion (predecessor, not DAG leaf) must not fire the edge. Last-milestone means leaf seats with a `milestone-id`.
- Do not write `FINISH_MARKER` from JS. `fire_finish_edge` is the one writer; `finishEvent` is the one JS reader.
- Do not mix `coord_selftest.py` edits with sibling seats; that file is a contended 16k-line suite.
