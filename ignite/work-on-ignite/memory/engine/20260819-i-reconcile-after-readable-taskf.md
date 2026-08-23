# 20260819-i-reconcile-after-readable-taskf — Reconcile after readable taskforce

kind: issue
component: engine
date: 2026-08-19
commit: dfecb8aa
deployed: yes
pin: NONE
seeded: true

## Seen
reconcile fired the alarm/reconcile path twice for one readable-taskforce event.

`reconcile.js` and `lane-watch.js` could fire the reconcile/alarm path twice for the same condition when a taskforce became readable — a double-alarm rather than a single reconcile pass.

## Missed
none recorded in sources.

## Held
lane-watch.js's readable-taskforce check now gates a single reconcile call.

`lane-watch.js`'s readable-taskforce check now gates a single reconcile call; `reconcile.js`'s own alarm-adjacent logic was simplified (net -20 lines) to stop double-firing.

## commit
dfecb8aa

## files
ignite/engine/lane-watch.js; ignite/engine/reconcile.js

## deployed
yes

## pin
NONE

## ATTENTION
- This landed the same day as reconcile.js's own creation (808902df, see the `selfheal-to-reconcile` entry) — it is an early hardening pass on brand-new code. If reconcile.js's taskforce-readability check is refactored again, re-verify the alarm doesn't double-fire.
- early hardening pass on brand-new reconcile.js; re-verify no double-fire if taskforce-readability check is refactored
