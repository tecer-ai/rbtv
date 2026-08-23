# 20260822-c-admission-brake-door — Admission brake door

kind: creation
component: engine
date: 2026-08-22
commit: 8478c7a5,affceae2,6c997616,c833046e
deployed: yes
pin: server/ticker/probes/probe-seat-queue.js (scheduled)
components: server,gateway
seeded: true

## Motivation
2026-08-20 burned 356 leader sittings in one day (stools 202 + meet 154, both on a 5-minute relaunch cadence) at 806,687,424 input / 6,962,033 output tokens, ~98% cache-read (`redesign-plan/seed/dead-sittings-diagnosis-2026-08-21.md`). The proximate D35 timestamp bug (`Number(checkin)`) was already fixed and deployed; the diagnosis's line is that "the class survived it." D34/D40/D44 (`23de241f`, sibling `20260820-c-stuck-becomes-a-brake`) had already bound the watcher's own `strike()`/`stuckStands()` loop to two no-progress attempts — after live measurement of stools `audio-component-smith` launched 17 times in ~2 hours, still firing at `attempts=20`. Those three rulings live inside `reconcile.js`. They do not bind `HeartStore.enqueue()`. The watcher itself calls `launchSitting` with `onSeatBusy: 'queue'`, which opts out of the Q9 seat-busy dedupe; `c833046e`'s comment names that caller and that 356-sitting day as why D52 exists. Owner 2026-08-22 asked for "one launch brake." D52 (`redesign-plan/decisions.md:714-718`): "a fail-closed admission brake in the persistent queue that NO caller can opt out of."

## Design
`c833046e` (2026-08-22 16:17:36Z) put the door inside `HeartStore.enqueue()` itself — after the dry-run return (so dry-run still means nothing was written) and before the Q9 seat-busy branch, so it binds both `'dedupe'` and `'queue'`. Scoped to `job.action_type === 'launch-agent'` only: a periodic fire-tool or start-workflow never reaches the branch, so cadences and the frozen-work watchdog stay untouched. `ADMISSION_BRAKE_LIMIT = 2` is owned here and imported by `reconcile.js` as `STRIKE_LIMIT` — the same D34 number relocated to bind every caller, not a new policy. A caller that omits `reason` falls into one merged `door:__enqueue` bucket (`BRAKE_REASON_FLOOR`); omitting a reason merges budgets, which is stricter. `door:`-prefixed keys share the `reconcile_attempts` table with the watcher's unprefixed `strike()` rows as a second independent lock. FOLD (replace `stuckStands`) was considered and refused: D62 default KEEP; `system-problems/build/07-brake/report.md:94` records the fold was not attempted because pinning arms were not proven green at a new locus and red-by-mutation.

D84 exemption is `home.seat !== 'goal-master'` — identity, not absence of a reason. Goal-master is a D24 summoned seat the watcher never targets, so any `launch-agent` enqueue reaching that identity is already event-driven. D70 owner re-arm is `req.senderKind === 'owner'`, stamped in `dispatch.js` `handleEnqueueJob` from the authenticated sender, never from the wire payload.

`6c997616` widened `enqueue_log.outcome`'s CHECK to accept `'braked'` via an additive table-rebuild (migration version 9; old table renamed `enqueue_log_pre_d52`) because SQLite cannot ALTER a CHECK and `ALTER TABLE…RENAME TO` on the new table re-quotes the identifier and would break the fresh-vs-migrated byte-identity proof. `gateway/parse.js` and `dispatch.js` both gained optional `reason` (DEC-3 double-validation). `affceae2` threads the watcher's already-computed `reason` + `progressSignature` into `enqueue()` — they had been derived in `reconcileGoal` and dropped before the call — and excludes `sender === 'ignite-daemon'` from `deriveOwed` class-B so the brake's own `stuck` mail cannot count as progress (D70).

Rejected: a per-caller convention; a trusted-caller skip flag; folding the two brakes; trusting `kind: 'owner'` from the payload.

## How it works
On a `launch-agent` enqueue that is not `goal-master` and has a goal+seat: `brakeSeat` is the seat or `seat#shard` (shard isolation independent of `seatKeyOf`), `brakeReason` is `door:` plus caller `req.reason` or `door:__enqueue`, `brakeSignature` is the watcher's `req.progressSignature` or a 16-hex SHA-256 of stamped `argsForRow` (`hashArgsFloor` — never raw caller `args`). Look up `getReconcileAttempt(goal, brakeSeat, brakeReason)`. If not owner, signature unchanged, and `attempts >= ADMISSION_BRAKE_LIMIT`: refuse — the counter still advances, an `enqueue_log` row is written with `outcome: 'braked'`, and `{braked: true, because, attempts, signature}` is returned instead of a queue row. Else admit: reset to 1 on a changed signature or an owner call, else +1.

`launchSitting` handles `enq.braked` the same way as `enq.deduped` (warn, `{ok: false, error: 'braked'}`). HeartStore must not import engine — the typed `stuck` message still comes from the watcher's own `strike()`, not from the door. `listEnqueueUnfired()` adds `AND e.outcome != 'braked'` so a refusal never trips the unfired-stall alarm. Gateway reason shape: `^[a-z][a-z0-9_-]{0,63}$`. To re-arm: change the signature (owed condition changed) or enqueue as owner (`senderKind === 'owner'`). A new caller that omits `reason` shares the merged floor budget with every other reasonless caller at that (goal, seat[#shard]).

## Consequences
Did not replace `stuckStands`/`strike`. Retired nothing. Same-day `8478c7a5` had to give `probe-seat-queue.js` scenario B distinct reasons (`holder`/`stale`/`fresh`/`periodic`) because four byte-identical reasonless launch-agent rows hit the merged floor and the 3rd/4th refusal made `getQueueRow(undefined)` throw.

D52's last clause — per-sitting token spend recorded in the ledger — was never built; `coord.py`'s checkout path was not touched. D84's accepted cost stands: a Slack-message loop to `goal-master` is unbounded by this brake. Sibling `17d75459` (`launch --only --reopen`) built a `coord.py`-local counter over `sessions.csv` that does not honor D70 owner re-arm. No later commit on the seven touched paths after `8478c7a5`.

## Verification
Pin is `server/ticker/probes/probe-seat-queue.js` (scheduled) — the same probe the door broke and `8478c7a5` repaired. Build-time `deploy/probe-suite.js --only` 11/11 PASS including `probe-reconcile.js`, `probe-enqueue-record.js`, `probe-idempotent-door.js`, `probe-enqueue.js`, `probe-job-seat-launch.js` (`system-problems/build/07-brake/report.md:59`). `reconcile.selftest.js` D34/D44 arms: one stuck after 2 refusals; launch success never clears; only a changed or empty owed set does; progress re-arms. Mutation on a discarded scratch copy: bound 2→99999, `brakedSeen = false`. Fresh-vs-migrated `enqueue_log`: `IDENTICAL (comments stripped): true`, `RAW BYTE IDENTICAL: true`, after a first migration guard matched the word `'braked'` in its own SQL comment and became a permanent no-op. Live `heart.db` read at build: meet `nonterm:leader=exited` at attempts=224, `stuck_emitted=1` — that is the watcher's counter, not the door's; the door's own live-path effect was proven on a scratch copy of that db (attempt 3 returned `braked:true` for `door:nonterm`). Header records `deployed: yes`. The 07-brake seat itself did not run `rbtv ignite daemon deploy` (`report.md:87`); no later commit on these files; the deploy event that flipped the header was not found in the sources checked.

## ATTENTION
- Fail-closed, no-opt-out by design (D52). A "trusted caller" bypass parameter would reopen the exact 356-sitting-burn class this relocates out of `reconcile.js` into `enqueue()`.
- `probe-seat-queue.js` going red is a real regression, not fixture flakiness — it already caught one same-day collision (`8478c7a5`) when four identical-args rows shared the reasonless floor.
- The door and `reconcile.js` `strike()`/`stuckStands` are independent locks sharing `reconcile_attempts` under `door:` vs unprefixed keys (D62 KEEP). Unifying them needs the pinning arms green at the new locus AND red-by-mutation; the 07-brake seat declined that fold.
- D84 exempts `goal-master` by identity. A rapid Slack-message loop to that seat is unbounded by this brake; no separate cap exists. Check this before diagnosing unexplained `goal-master` launch volume as a new bug.
- A caller that omits `reason` shares one merged `door:__enqueue` budget with every other reasonless caller at that (goal, seat[#shard]). That is stricter on purpose; do not invent implicit unique reasons to "give each caller its own budget."
