# 20260820-c-stuck-becomes-a-brake — Stuck becomes a brake

kind: creation
component: engine
date: 2026-08-20
commit: 23de241f
deployed: yes
pin: engine/probes/probe-reconcile.js (D44 arms, many)
seeded: true

## Motivation
D34 (`2233233a`, 16:21:41Z) and D40 (`d813ebcc`, 17:20:45Z) made the watcher's strike counter actually fire — two no-progress passes, then typed `stuck` to the leader (sibling `20260820-i-watcher-retry-policy`). That closed the counter. It did not close the spend. `reconcileGoal`'s target loop still called `launchSitting()` whenever the seat was not already live, queued, or seen; `strike()` ran afterwards and returned nothing the loop consumed. D44 (`redesign-plan/decisions.md`, owner 2026-08-20): measured live on stools, `audio-component-smith` was launched 17 times between 17:29:05 and 19:41:10 — one full `claude-opus-5` boot per ~5 min, each ending `incomplete` in under 90s — on a row whose only blocker was an unanswered owner escalation (#145 / #167(B)). A later store read was `attempts=20, stuck_emitted=1` and the loop was still firing. This was not a coding defect against spec: `seats/resolve-watcher/seat.md:39` said in those words "A successful launch records the attempt; it does not clear it," and the code did that. The gap was between D34/D40's prose ("bounded", "then typed `stuck` to the leader") and a low-level spec that never gated the launch on `attempts`. Nobody caught it until `resolve-verify` pass 2 measured the spend.

## Design
`23de241f` (2026-08-20 20:28:17Z) added `stuckStands(store, goal, seat, reason, signature)`: true only when the stored attempt row has the same signature and `stuck_emitted` is set. In `reconcileGoal`'s target loop a `skip-stuck` branch is inserted before the launch branch. Once `stuck` has gone to the leader for that exact triple, the mechanical relaunch stops and the row is the leader's (D44: "the leader can relaunch it"). `strike()` still runs on the skip path, so the counter keeps advancing and the owner-alarm leg (`STRIKE_LIMIT` + `OWNER_AFTER_STUCK` = 2 + 3) is untouched — what stops is the spend.

Keyed on the signature so D34/D40 stay intact: a changed owed-set signature is progress, `stuckStands` goes false, `strike` resets attempts to 1, and launching re-arms in the same pass. Only a stuck-and-unchanged row is braked.

Rejected: leaving the written spec (open-ended relaunch spend; the "2 tries" guarantee is not real — that is what pass 2 measured). Accepted cost, recorded in D44: a seat that would have recovered spontaneously on attempt 3+ gets one fewer chance and comes back through the leader. D43 (paneless `--as` corroboration via `carrier_self_session()`) rode the same commit and deploy because the D43/D44 seat was already open; it is orthogonal and is filed under team-kit `20260821-c-caged-identity-corroboration`. It does not protect the signature key.

## How it works
Each owed target is considered once per pass. After the live/queued skip, `stuckStands` reads `getAttempt` for `(goal, seat, reason)` and compares `prev.signature` to this pass's owed signature. Match plus `stuck_emitted` → action `skip-stuck`, no `launchSitting`. Miss → launch as before. Then `strike()` records the pass (D34: the attempt is the pass, not the launch). `STRIKE_LIMIT` is 2 (at this commit a local constant; later imported from `heart-store.js` as `ADMISSION_BRAKE_LIMIT`).

To re-arm this layer, change the owed signature — typically the owed set's content changes (a new incomplete seat, a cleared reason). An owner Slack message does not lift this brake; that re-arm is D70 on the later `HeartStore.enqueue()` door (`20260822-c-admission-brake-door`). A leader who wants the seat to run again while the signature is unchanged must relaunch it as an explicit act (D39's two-act rule), not wait for the watcher.

## Consequences
Did not replace the D34/D40 counter; sits on top of it. Retired nothing. Same-commit D43 is identity, not reconcile.

Live the same evening: stools `audio-component-smith` last spawned 2026-08-20 20:27; `resolve-verify` pass 4 later read `attempts=114, stuck_emitted=1`, 38 rows, zero relaunches since the D44 deploy (`pass4-report.md`). Next day, meet's leader died three EROFS times (20:59:57 / 21:05:01 / 21:10:09Z); D44 emitted `stuck` at 21:10:04 (attempts=2); no fourth session. The counter kept climbing (15 at 22:15, 19 at 22:40) — owed still standing, spend stopped (`dead-sittings-diagnosis-2026-08-21.md`).

Two days later `affceae2` (D52/D66/D70) threaded reason+signature through `launchSitting` into `heartStore.enqueue()` so the admission door keys on the same string `strike`/`stuckStands` already use — it did not reformat the signature. That door is a second, independent lock (`20260822-c-admission-brake-door`); `launchSitting` now also surfaces a `braked` enqueue the way it already surfaced `deduped`. D88 (2026-08-22 ~15:27Z) then had to hand-relaunch meet's leader: heart.db `nonterm:leader=exited` at 219 attempts, `stuck_emitted=1`, signature unchanged, D70's owner-message re-arm still unbuilt. No later commit removes `stuckStands` / `skip-stuck`.

## Verification
New `reconcile.selftest.js` D44 arms. `brakePass` drains the queue between passes (otherwise last pass's enqueue makes the next `skip-live-or-queued` and the arm proves nothing about the brake) and asserts the action kind exactly as `skip-stuck` (never "not enqueue"). Pass 1 `enqueue`; pass 2 `stuck_emitted=1` and one stuck send; passes 3–4 same signature `skip-stuck` and no second send; pass 5 after a changed owed set (`worker-b` added) `enqueue` with attempts reset to 1. A RED-by-mutation arm patches the live `stuckStands(...)` branch to `false && stuckStands(...)` on a compiled copy and asserts the mutant would relaunch. The pre-existing "2 strikes on a REFUSED launch" arm moved with the ruling: passes 3–5 are now `skip-stuck`; the store still reads attempts=5 (owner-alarm leg unchanged). Commit message: `probe-reconcile.js` exit 0; `probe-suite --only reconcile` verdict=GREEN. The probe's description string now names "the D44 stuck-brake".

Deployed yes. First live effect is the 20:28Z landing itself (pass 4's 20:27 last-spawn). `fix-inventory.csv` D44 records the later batch snapshot at rbtv HEAD `ac1c08d8` (deployed 2026-08-21 18:14:37Z).

## ATTENTION
- The brake keys on the exact `(seat, reason, signature)` string triple. A later change to how `reason` or `signature` is computed (class B is still `unread:${seat}:${lastNum}`) silently unmatches a standing brake and mechanical relaunch resumes. `affceae2` threaded that same string into enqueue and did not reformat it; the trap is a future format change, not that commit.
- D44 changed a written spec by owner ruling, not a defect against spec. `seats/resolve-watcher/seat.md:39` still says "A successful launch records the attempt; it does not clear it." That line is superseded. Diffing this code against that seat.md and restoring the ungated launch rebuilds the 17-relaunch spend.
- This watcher brake is the terminal state of the retry loop in `20260820-c-verified-done-resolver` and `20260820-i-watcher-retry-policy`. A later second lock lives at `HeartStore.enqueue()` (`20260822-c-admission-brake-door`). They are not the same counter and an owner message does not lift this one (D70 is the later door).
- Re-arm is only a changed owed signature. An unchanged owed set (leader `exited`, unanswered escalation) stays braked at this layer. D88 hand-relaunched meet's leader at 219 attempts for that reason — Slack did not clear `stuckStands`.
