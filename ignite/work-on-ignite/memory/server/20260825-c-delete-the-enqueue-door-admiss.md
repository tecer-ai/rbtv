# 20260825-c-delete-the-enqueue-door-admiss — Delete the enqueue-door admission brake [C-4 kill map]

kind: change
component: server
date: 2026-08-25
commit: 01196394
deployed: no
pin: NONE
components: engine,supervisor

## Motivation
The enqueue-door brake was the second lock on a comparison that never held still.

`c833046e` (D52/D66) put a fail-closed admission brake inside `HeartStore.enqueue()` after the 356-sitting burn, and `20260822-c-admission-brake-door` records that FOLDING it into reconcile's `strike`/`stuckStands` was considered and refused (D62 default KEEP, pinning arms not proven at a new locus). spec-recovery §5 and the [C-4] kill map settle that open question the other way: both brakes are the wrong capability, and both go together — a byte-equality path left beside the replacement would reset the new counter for the same reason it reset the old ones.

## Design
Delete the door and count at the driver instead — `enqueue()` mints no counter at all.

`ADMISSION_BRAKE_LIMIT`, `BRAKE_REASON_FLOOR` and `hashArgsFloor` are deleted with the whole `launch-agent` brake block inside `enqueue()`, and the now-unused `node:crypto` require goes with them. The pinning-arm objection the 07-brake seat raised is answered rather than waived: the replacement (`ignite/supervisor/attempt-counters.js`) lands with its own suite AND with three red-by-mutation arms in `reconcile.selftest.js`, so the bound is proven green at the new locus and red when mutated — which is exactly the condition that entry named for the fold.

## How it works
`enqueue()` now returns only its own dedup verdict; nothing reads `req.progressSignature` and no row is written to `reconcile_attempts` from this path. `supervisor/launch-door.js` loses its dead `enq.braked` refusal branch, so `launchThroughDoor` reports `store-dedup` and nothing else. The bound moved OUT of the shared door and INTO each unbounded driver, which is what makes it visible: a driver knows its own refusal class, and the door only ever knew bytes.

## Consequences
`enqueue()` can no longer answer `braked`. `engine/seeding.js` still carries a `launched.kind === 'braked'` message branch that is now unreachable, and `team-kit/launch.py`'s docstring and refusal text still name the brake — both are other seats' files this change deliberately did not touch, and both are dead references a follower must clear. The `reconcile_attempts` table and its `getReconcileAttempt`/`upsertReconcileAttempt`/`clearReconcileAttempt` methods survive with no writer on the owed path; `migrations.js` keeps the `enqueue_log` `'braked'` outcome as history.

## Verification
`probe-suite --dir server/heart/probes` 23/23 GREEN (including `probe-enqueue`, `probe-idempotent-door`, `probe-seat-queue`), `--dir server/ticker/probes` 27/27 GREEN, `probe-reconcile` PASS, `probe-suite --selftest` 26/26. `node ignite/engine/reconcile.selftest.js` prints `reconcile.selftest OK`. Not deployed — worktree branch `ignite/core-redesign`, pre-cutover.

## ATTENTION
1. Do not re-add a brake at `enqueue()`. Two locks on one condition is the defect this removed; the ONE bound is the driver's attempt counter.
2. `enq.braked` is dead. Any surviving reader of it (seeding's message branch, launch.py's refusal text) is describing a refusal that can no longer occur.
3. `reconcile_attempts` is now an orphan table on the owed path. A new writer to it is almost certainly re-inventing the signature reset.
- enq.braked is dead — a surviving reader describes a refusal that cannot occur
