# 20260820-i-same-minute-sitting-not-supers — Same minute sitting not superseded

kind: issue
component: engine
date: 2026-08-20
commit: 2ddb8644
deployed: yes
pin: NONE
seeded: true

## Seen
Two same-minute sittings could match a sitting against itself in supersession.

reconcile.js's supersession logic (which decides whether an older sitting for a seat is superseded by a newer one) could match a sitting against itself when two sittings landed in the same minute (timestamp granularity collision), incorrectly marking a live sitting as superseded.

## Missed
none recorded in sources.

## Held
Exclude a sitting from superseding itself; add same-minute test arms.

reconcile.js's supersession check now excludes a sitting from superseding itself; reconcile.selftest.js gained arms covering the same-minute case.

## commit
2ddb8644

## files
ignite/engine/reconcile.js; ignite/engine/reconcile.selftest.js

## deployed
yes

## pin
NONE

## ATTENTION
- Any future change to timestamp-based ordering/supersession logic in reconcile.js should include a same-minute (equal-timestamp) test case — this exact granularity collision is what caused F-1.
- any future supersession-logic change should test the equal-timestamp collision
