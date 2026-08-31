# 20260831-i-crash-sweep-raced-execstoppost — Crash sweep raced ExecStopPost into failed

kind: issue
component: runtime
date: 2026-08-31
commit: cb9034f8
deployed: no
pin: ignite/runtime/ticker/probes/probe-crash-sweep-marker-race.js

## Observed

The ticker crash sweep stamped `failed` plus `slot halted: session crashed` on the same tick a process went inactive, before the carrier's ExecStopPost had written the exit marker. Measured 2026-08-08 (1/5 solo, 3/10 concurrent) and reproduced 2026-08-31 on HEAD: a planted gone exec with no marker file became `status=failed` with corpus `crash sweep: exit=null` in 172ms (`probe-crash-sweep-marker-race` red). The same composition left `ignite add-job --fn seat-<goal>-<seat>` failures undiagnosable (queue 1467 exec 31122, queue 1561 execs 31504/31505): never-spawned and spawned-and-crashed both wrote `exit=null` plus an empty tail. Deployed daemon still runs the pre-fix copy.

## Mechanism

`readExitMarker` is one `readFileSync`. After the G-222 already-reported branch, `enforce()` treated only `marker.present && exitCode===0` as `done` and routed every other gone process — including marker-absent — to `failed` on that tick. ExecStopPost (`echo $EXIT_STATUS > exitFile`) runs after the unit reports inactive, so the first gone observation is a structural race, not a crash. When neither marker nor `info.exitCode` existed, the corpus interpolated `null` and did not distinguish a row that never received a `session_id` from one that started and died before the hook landed.

## Attempts

First attempt held — checked: `a554197b` (lane-aware `--rerun`, sibling of add-job, never the crash-sweep composition); `20260824-c-jobs-log-to-history-closer-sta` (closer stamps `failed:crash` from marker evidence, does not wait for the hook); `20260819-c-selfheal-to-reconcile` (KEEP the ticker crash sweep, do not replace it with owed-work). Writing the marker earlier was rejected: it would invert `--collect` exit collection.

## Fix

Marker-absent plus a parseable result line records `done` this tick. Marker-absent plus a `session_id` defers one tick (`crash-sweep-deferred`); a second consecutive gone observation with still nothing is `failed` and still halts. A row with no `session_id` fails immediately as `never spawned`. The corpus names `never spawned`, `no exit marker found`, `exit=<marker>`, or `carrier error: …` — never `exit=null`. The seat closer runs only on a decided outcome, not on the defer. G-222 already-reported turns are still session-closed and not rewritten.

## Consequences

Existing crash probes that asserted same-tick `crash-sweep` after SIGKILL now follow one optional defer tick (`probe-crash`, `probe-stalled-crash-sweep`, G-222 control arm only). Scenario 1 of `probe-g222-terminal-turn` is unchanged. `crashedThisTick` in `enforce()` remains written and unread (pre-existing). `probe-goal-paused-gate` C4 is red on HEAD ticker as well as this commit — not this change.

## Verification

Red: `node ignite/runtime/ticker/probes/probe-crash-sweep-marker-race.js` on pre-fix tree, all five legs FAIL, corpus `crash sweep: exit=null`. After: same probe ALL PASS (defer, two-tick crash, result→done, never spawned, distinct spawned corpus). `probe-g222-terminal-turn`, `probe-crash`, `probe-stalled-crash-sweep` PASS. `node ignite/deploy/probe-suite.js --dir runtime/ticker/probes`: 27/28, the one failure is pre-existing `probe-goal-paused-gate` (red against HEAD ticker.js too). Not deployed.

## ATTENTION

- The first process-gone with no marker is the ExecStopPost window; failing it on that tick deafens the chain (no owner message wakes a failed tail).
- Never-spawned is `session_id` empty, not "live=false". A spawned row with no marker waits one tick, then `no exit marker found`.
- Do not move closer onto the defer arm: attest-exit on a turn that then records `done` from a late marker is a false crash stamp.
- G-222 already-reported turns stay un-overwritten; the sweep still closes the leaked session.
