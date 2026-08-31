# 20260831-i-done-checkout-left-harness-ali — Done checkout left harness alive

kind: issue
component: coord
date: 2026-08-31
commit: f616be02
deployed: no
pin: ignite/coord/probes/probe-checkout-reaps-done.py
components: supervisor

## Observed
Meet-transcript-summarizer on 2026-08-23 left four agent processes alive after clean `done` checkouts — `plan-4-plan-assembler`, `plan-4-plan-resource-definer`, and two `plan-4-plan-task-definer` — oldest then 2d11h, idle, ~16–60 minutes CPU. Filing G-leader-0823-0217-2. The row closed; the process did not. `state.json run.live_executors` read 1 off stale panes while the execution record showed the agent finished 12.8 hours earlier. HEAD (unfixed) still reproduced: a scratch worktree at a54ea425 ran `probe-checkout-reaps-done.py` and a persistent done checkout left pid 498114 alive. Re-census 2026-08-31 of the original PIDs 476076/482460/1189328/1127453: all gone; exact-argv-token walk of /proc was empty. Deployed tree does not yet carry the fix.

## Mechanism
`cmd_checkout`'s non-renew path armed `arm_pid_reaper` only inside `ephemeral: yes`, then killed that pane. Persistent seats printed "leader frees the pane" and returned. `death-stamp.js#stampDeath` confirm-and-reaps a `done` for every seat, but only when an exit is already observed — a living process never reached it. `cmd_reap --go` can confirmAndReap awaiting-reap debt, but it is leader-gated and observe-by-default, which is why the 2d11h orphans were never drained.

## Attempts
First attempt held — checked: `engine/20260824-c-supervisor-death-stamp` (confirm-and-reap on done for every seat, never only ephemeral), `team-kit/20260824-i-attest-exit-becomes-the-superv` (`cmd_reap` gained `supervisor_reap_arm`), `supervisor/20260830-i-stale-done-from-an-earlier-sit` (stale done must not swallow a later crash). Those close the stamp/reap table once death is seen; they never made checkout itself terminate a still-living harness.

## Fix
Design (a): checkout itself arms `arm_pid_reaper` (pid+starttime) for every non-renew ending — done, incomplete, unverified — not only ephemeral. Rejected (b) a named sweeper on `cmd_reap`: that verb already existed and is what failed to drain the leak. Persistent seats still leave the pane for leader `close-seat` (relay-door). Crash without checkout stays `stampDeath` → `confirmAndReap`.

## Consequences
Ephemeral self-close still kills its pane after the same reaper. `cmd_reap` is unchanged. death-stamp table is unchanged. No pane-kill-by-pattern. Selftest W4 arm 7 (messages.py pending nag) was already red and is out of this seat's custody.

## Verification
`probe-checkout-reaps-done.py`: ps before/after a real stub harness on persistent done (pid 448544 alive→gone) and incomplete (451218 alive→gone); in-probe mutant and scratch worktree at a54ea425 both leave the process alive. `coord.py selftest` rows for persistent done/incomplete reaper green. `node ignite/deploy/probe-suite.js --only probe-checkout-reaps-done` GREEN. Deployed: no.

## ATTENTION
- death-stamp confirm-and-reap on `done` is not a sweeper of live processes: it runs after observed death. Do not read that table as "checkout already reaps."
- `arm_pid_reaper` fires only on exact (pid, starttime) plus a harness argv; a sleep stub is not a kill target — use a `claude` basename stub.
- Persistent checkout still does not kill the pane. Killing the viewport here would skip the relay-door refusal on `close-seat`.
- death-stamp confirm-and-reap is not a live-process sweeper
