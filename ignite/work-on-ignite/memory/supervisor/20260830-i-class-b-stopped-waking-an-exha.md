# 20260830-i-class-b-stopped-waking-an-exha — class B stopped waking an exhausted chair at the source

kind: issue
component: supervisor
date: 2026-08-30
commit: 44228d94
deployed: no
pin: ignite/supervisor/owed-from-endings.selftest.js

## Observed
Orchestrator verification of `fa89fa75` (2026-08-30) found the Defect-B fix's definition-of-done
clause unmet: after the cursor fix, a chair whose sittings keep ending without advancing the read
cursor (or keep dying on the same mail) was re-woken by `classifyOwed` on EVERY reconcile pass with
no limit visible at the wake itself — each wake is a paid sitting.

## Mechanism
`reconcile.js`'s own `counterDisarmed({ goal, seat, reason, config, countersFile })` (unedited,
outside this seat's walls) gates the LAUNCH, not the wake: `Boolean(row && Number(row.attempts) >=
config.attempt_counter_n)` — attempts-vs-n only, with no check of WHICH mail those attempts were
spent on. `classifyOwed`'s class B reported the chair as owed regardless of that gate, so any
caller of `deriveOwed` other than reconcile's own launch loop (and, on the pass where the gate
first trips, even reconcile's own downstream target list, which still receives the item and only
declines to launch it) still read `owed: true`. The wake itself never stopped; only one consumer's
reaction to it did, on the passes after the first exhaustion.

## Attempts
First attempt held for the read-cursor half — checked `20260830-i-class-b-unread-test-read-check`
(this same entry's own prior filing, `fa89fa75`, which fixed the cursor comparison but left this
clause unmet) and `20260828-c-supervise-hold-a-leader-hold-t` (the leader-HOLD exclusion, a
different owed-set exclusion in the same function, not a brake).

## Fix
`unreadFrontierExhausted(goal, chair, lastNum, countersFile)` in `owed-from-endings.js` reads the
SAME ledger `reconcile.js` already writes — `attempt-counters.js`, driver `RECONCILE_RESPAWN`,
subject `<goal>/<chair>`, `reasonClass: 'unread'`, the exact key `reconcile.js:983-991/1187-1206`
uses — and adds the ONE check `counterDisarmed` is missing: exhaustion (`attempts >= n`, `n` from
`recovery-config.js` via `RBTV_IGNITE_WORKSPACE_ROOT` — the same env var `fa89fa75`'s
`death-stamp.js` fix established) only suppresses class B when the CURRENT unread frontier
(`#<lastNum>`) is the one recorded on the counter row's `owed_items`. A frontier advance (new,
higher-numbered mail) is owed a first attempt, exactly as `attempt-counters.js#isRetryOf` already
treats it for the write side — re-deriving that same test rather than trusting `attempts` alone.
Re-arm needed no new wiring: `rearm()` (`resume {goal}`, a code-deploy, a config change, an
owner/leader act — unedited) deletes the counter row outright, so the next read here answers "not
exhausted" for free, off the same re-arm list every other counter uses.

Rejected: trusting `reconcile.js`'s `counterDisarmed` alone (it has no frontier check, so IT would
block legitimate new mail on an exhausted lane forever — reproduced as this fix's own RED 3/4 arm);
adding a new ledger or config key (the instruction was explicit, and `attempt_counter_n` /
`attempt-counters.json` already carry everything needed).

## Consequences
`classifyOwed`'s `classB` array can now be SHORTER than the raw unread-mail computation would
produce, for a lane the ledger has exhausted on its current frontier. No caller signature changed:
`countersFile` joins `classifyOwed`'s existing optional-opts list (undefined in every production
caller today, resolving to `attempt-counters.js`'s own `__dirname`-relative default — the same file
`reconcile.js` resolves to when it also does not override the path, since both modules live beside
each other and `__dirname` is per-file).

## Verification
`node owed-from-endings.selftest.js` — 7 arms, `ALL PASS`: arms 1/2 (cursor, unchanged from
`fa89fa75`); arm 3 — `attempt_counter_n` identical dead passes on frontier `#45`, then pass N+1
shows `classB` excluding the chair, counter row named `reconcile-respawn/<goal>/leader/unread`; arm
4 — a NEW, higher-numbered message on the SAME exhausted lane wakes the chair for the new frontier;
three RED mutations — revert to checkin/tsAfter (arm 1 flips), a cursor stuck at 0 (arm 2 flips),
and dropping the frontier check (an exhausted lane wrongly blocks the arm-4 new mail too,
reproducing `reconcile.js`'s own `counterDisarmed` gap). Full `ignite/supervisor/*.selftest.js`
sweep unchanged: `reconcile.selftest.js` still aborts at its pre-existing `:392` assertion, 6 PASS
before it — identical before this change, after `fa89fa75`, and after this follow-up. NOT deployed
at filing; commit `44228d94` on `ignite/core-daemon`. No `.rbtv/` planted under the repo root.

## ATTENTION
1. `reconcile.js`'s own `counterDisarmed` STILL has no frontier check (unedited, outside this
   seat's walls) — it independently blocks a launch once `attempts >= n`, regardless of item
   overlap. This fix's exclusion at the wake makes that gap MOOT for class B specifically (an
   exhausted-and-stale item never reaches reconcile's launch-target list at all, and a
   frontier-advanced item is correctly re-admitted to class B before reconcile ever runs
   `counterDisarmed` on it) — but `counterDisarmed` itself is unchanged and would still misfire if
   some OTHER caller ever handed it a class-B-shaped target through a path that skips
   `classifyOwed`.
2. `unreadFrontierExhausted` depends on `RBTV_IGNITE_WORKSPACE_ROOT` and a readable recovery config,
   exactly as `fa89fa75`'s `sittingStartedAt` does — a workspace where the env var is unset or the
   config is unreadable applies NO recovery clock here either (fails open: the chair keeps waking,
   never wrongly silenced), matching `reconcile.js#recoveryNumbers`'s own stated rule.
- reconcile.js counterDisarmed still has no frontier check; moot for classB, live for any other caller
