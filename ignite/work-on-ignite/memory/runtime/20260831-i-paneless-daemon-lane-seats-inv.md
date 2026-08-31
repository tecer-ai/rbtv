# 20260831-i-paneless-daemon-lane-seats-inv — Paneless daemon-lane seats invisible to the lease

kind: issue
component: runtime
date: 2026-08-31
commit: 944782cc
deployed: no
pin: ignite/runtime/lease/probes/probe-lease.js
components: supervisor

## Observed
Meet-transcript-summarizer's leader filed G-leader-0823-0025 on 2026-08-23 00:31: `derive_lease` returned `ok=true, live=true, seats=[], evidence.seats-verified=0` while an open paneless leader sitting and completed paneless sittings were in `sessions.csv` (`tty=''`). team-monitor read that zero as "nothing executing" and escalated toward `coordinate finish-goal`. The leader declined the false alarm (`p-leader-team-monitor-lease-alarm-blind-to-the-paneless-lane-0823`) and recorded that it would recur. Reproduced 2026-08-31 on HEAD: a live room plus a live pid whose ancestry does not hit a pane still yields `seats-verified=0` when the row has no `tty` column (the meet shape); the same pid verifies once the row carries the empty `tty` cell daemon-lane spawn writes.

## Mechanism
`verifiedSeats` required three conjuncts: pid alive, starttime match, and `/proc` ancestry intersecting the room's pane pids. Daemon-lane spawn (`spawn.js`) writes `tty: ''` and never puts the harness in a pane, so the third conjunct could never fire. `live` already treats a room with zero verified seats as a live lease (mid-relaunch), but `evidence['seats-verified']` was the occupant count and was the number the deleted sensor treated as "nothing executing". team-monitor, the only consumer that escalated that number to the finish edge, was deleted 2026-08-24 (`549a0f8b`, T4-R8). Remaining `lease.seats` readers are the ticker gate (queues a start on `lease.live`, seats are prose) and bus-write authz (`room.seats.length === 0` skips the grant). `cmd_finish_goal` does not read the occupant count.

## Attempts
First attempt held — checked: lease.js header (ancestry over pane pids confirmed, not a relayed fiction); `ignite/work-on-ignite/memory/team-kit/20260824-c-delete-team-monitor-cli-and-te`; grep of `seats-verified` under `ignite/` (producer only); `records.py#fire_finish_edge` / `cmd_finish_goal` (leader identity gate, no liveness conjunct); sibling task 4 is paneless-successor *placement*, a different producer.

## Fix
`verifiedSeats` now admits a second membership shape: `tty` present on the header and empty on the row, with pid+starttime still live. A header without `tty` is not paneless evidence (older pane-only logs), so a live pid outside the room still fails — that is why probe L12 stays red and L17 (same pid, empty `tty`) is green. Rejected: treating any open-ended live pid as verified (would green L12 and grant occupancy to an impostor). Rejected: reporting `seats-verified` as UNKNOWN while `live=true` (the filing's interim; counting the spawn evidence closes the hole). Rejected: restoring team-monitor or gating `fire_finish_edge` on occupant count (no remaining consumer fires finish from that shape; the finish edge stays a leader act).

## Consequences
Bus-write authz that skipped rooms with `room.seats.length === 0` will now grant while a paneless occupant is live — that is the occupant set the grant was meant to track, previously empty on the daemon lane. `one-live-run.js` reason text still says "ancestry-verified"; seats in that string can now include paneless rows. spawn.js comments still describe the bus conjunct as pane-ancestry only (pre-existing prose, not edited). Coord and the finish edge were not changed.

## Verification
`node ignite/deploy/probe-suite.js --only probe-lease` PASS 30/30. Red arm: scratch worktree at HEAD (pre-fix `lease.js`) plus the new L17 probe → `FAIL L17`, then the same probe on the fixed tree PASS. Isolated fixture: meet shape `seats-verified=0` with live room; empty-`tty` row `seats-verified=1` naming the paneless pid. Idle throwaway `test-lease-idle-*` `coordinate --as leader finish-goal` recorded the finish event with no room to tear down. Not deployed.

## ATTENTION
- Do not treat every live pid as verified: L12 (no `tty` column) must stay red; empty `tty` is the paneless discriminator.
- `seats-verified=0` with `live=true` is mid-relaunch, not finished. Do not restore a sensor that recommends `finish-goal` from occupant count. Task 4 is placement, not this observer.
