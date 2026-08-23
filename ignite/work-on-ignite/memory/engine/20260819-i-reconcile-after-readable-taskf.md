# 20260819-i-reconcile-after-readable-taskf — Reconcile after readable taskforce

kind: issue
component: engine
date: 2026-08-19
commit: dfecb8aa
deployed: yes
pin: NONE
seeded: true

## Observed
Twenty-six minutes after `808902df` (2026-08-19 21:23:11Z) created `reconcile.js` and wired `maybeReconcile` into `runLaneWatch`, `dfecb8aa` (21:49:24Z) named the symptom in its subject: one stall posted two owner alarms. The new call sat at the top of the per-goal loop, gated only on `taskforce.csv` or `sessions.csv` existing (`fs.existsSync`), before `readLane` and before the later `readTaskforce` try/catch. In the same iteration `reconcileGoal` called `alarmOnStall` for `derived.readyRefused` (ready-seats subprocess refused or errored) and for `derived.classE` (frozen-frontier: zero READY, pending seats, nothing live or queued). Lane-watch then hit its pre-existing LE-13 branch and called `alarmOnStall` again with `pickup.frozen.kind: 'taskforce-unreadable'` when `readTaskforce` throws. `goal-stall-alarm.js` dedups by goal plus condition signature (kind + sorted seat names), so two kinds are two Slack posts. Frontmatter says deployed yes, pin NONE; at HEAD the detect-not-alarm split for those two conditions still holds, and a same-day follow-up added a second `maybeReconcile` site for pause.

## Mechanism
Two independent defects in the `808902df` wiring. Placement: `maybeReconcile` ran before `readLane`, so it fired for console-lane goals and for any folder that merely had a sessions ledger. `readySeats` then spawned `coord.py ready-seats --json` with `COORD_TIMEOUT_MS` 60s (`seeding.js`); on a probe fixture or an unreadable package that hangs, the rest of that goal's iteration — including the LE-13 `alarmOnStall` continues that were the single pre-reconcile alarm path — waited out the timeout. The `dfecb8aa` comment states this: a reconcile that called ready-seats first would spend `COORD_TIMEOUT_MS` on probe fixtures and starve the stall alarm. Dual alarmer: even when both paths finished, `reconcileGoal` required `./lane-watch` and called `alarmOnStall` with `pickup.readinessRefused` or `pickup.frozen.kind: 'frozen-frontier'`; lane-watch later called it with `taskforce-unreadable` (or another LE-13 continue). Dedup cannot collapse those signatures. The move did **not** skip the `readTaskforce` catch: at `dfecb8aa` and still on HEAD, `maybeReconcile` sits after the daemon-lane continue and the `!exists taskforce.csv` quiet continue, still before `readTaskforce`. "Readable" in the commit means a daemon goal whose taskforce file exists, not that `readTaskforce` succeeded.

## Attempts
First attempt held — checked: `git log --before=2026-08-19T21:23:11` on `lane-watch.js` / `reconcile.js`; `reconcile.js` is new in `808902df` (582 insertions), so no earlier trial of this double-alarm exists. Closest prior alarm-scoping work is `de271c65` (2026-08-18, a disposition SKEW blocks its own seat, never the whole goal), cited in the `goal-stall-alarm.js` header and a different defect. Map `missed_trials_source` is NONE.

## Fix
Two changes, both required. `runLaneWatch` deletes the top-of-loop `maybeReconcile` and reinserts it after the daemon-lane continue and the no-taskforce-yet continue; the new gate is only `!goal.startsWith('_')` because existence is already established. Inside `reconcileGoal`, both `alarmOnStall` blocks become `actions.push({ kind: 'detect', why: 'ready-seats-refused', detail })` and `{ kind: 'detect', why: 'frozen-frontier', seats }`. `strike()`'s `reconcile-stuck` `alarmOnStall` (owner escalation after D15 strikes) is untouched — different signature, present since `808902df`. This is a same-day correction inside the D1/D15 feature `808902df` shipped (D1: the reconciliation loop is the watcher, acts first, escalates second; D15: 3 mechanical attempts, 5-minute cadence, then typed `stuck`); `dfecb8aa` itself cites no D-id. Net 15 insertions / 35 deletions. No separately recorded rejected design beyond leaving reconcile as a second alarmer.

## Consequences
Same-day `2058b965` (22:22:31Z, 33 minutes later; `20260819-i-honour-goal-pause-in-reconcile`) adds another `maybeReconcile` immediately after `readLane`, gated on `laneIsPaused`. A paused marker flattens to console, so the new DAEMON-only site never saw paused goals; without that addition, pause would skip reconcile by accident of the flatten. Scope gap in this reordering, not a regression of the double-alarm. Later commits on these two files (`61ce15d9` through `affceae2`, 2026-08-20–22) are other D-numbered work; none revert the call-site order or the detect-vs-alarm split for `readyRefused` / `classE`. No other memory entry cites this sha.

## Verification
`dfecb8aa` touches only `lane-watch.js` and `reconcile.js`. No `.selftest.js` or `probes/` change — pin NONE is correct. `reconcile.selftest.js` and `probe-reconcile.js` were created in `808902df` and extended in `2058b965` (67 selftest lines for pause), not here. Deployed yes per frontmatter; ignite JS is inert until `rbtv ignite daemon deploy`; no deploy timestamp for this sha was found.

## ATTENTION
- `maybeReconcile` in `runLaneWatch` must stay after the daemon-lane and `taskforce.csv`-exists continues, not at the top of the per-goal loop. Putting it back before `readLane` re-runs reconcile on console/absent folders and can spend `COORD_TIMEOUT_MS` (60s in `readySeats`) on probe fixtures before the LE-13 stall-alarm continues fire.
- `reconcileGoal` must keep `ready-seats-refused` and `frozen-frontier` as `kind: 'detect'` action records. Re-adding `alarmOnStall` for those two conditions creates a second signature in `goal-stall-alarm.js` (dedup key is goal + kind + sorted seats) and double-posts Slack next to lane-watch's own branches.
- A paused goal reads as console, so the post-DAEMON site never sees it. `2058b965` added a `laneIsPaused` call site right after `readLane` for that reason; deleting that site while keeping this order silently stops reconcile on paused goals.
- `strike()` still calls `alarmOnStall` for `reconcile-stuck` after D15 strikes. That is a different condition, present since `808902df`; collapsing it into detect would silence owner escalation, not fix double-alarm.
