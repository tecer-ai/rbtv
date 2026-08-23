# 20260819-c-taskforce-validate-at-load — Taskforce validate at load

kind: creation
component: engine
date: 2026-08-19
commit: 8f7b1adf,79ede919,a64ba6c6
deployed: yes
pin: engine/probes/probe-frozen-frontier.js
seeded: true

## What it is
Load-time validation for taskforce.csv/DAG rows; refuses malformed rows loudly.

`seeding.js` gained load-time validation for `taskforce.csv` rows (8f7b1adf: also touches `probe-daemon-lane-watch.js`, `probe-goal-stall-alarm.js`); `queue-request.js` bounds its per-pass refusal log so repeated identical refusals don't flood it (79ede919); `probe-frozen-frontier.js`'s fixture was corrected to use a real undeclared-session row instead of a dangling `after` reference (a64ba6c6).

## Why
D16: malformed DAG rows failed silently deep in the engine instead of at load.

`fix-inventory.csv` D16 — one hardening seat's mandate: validate plan files at load, refuse malformed rows loudly, rather than letting a bad row fail silently deep inside the DAG/planning engine.

## How to use & where wired
seeding.js's load path validates taskforce.csv before rows enter the DAG.

`seeding.js`'s load path now validates taskforce.csv rows before they enter the DAG; `queue-request.js` caps repeated identical refusal logging per pass.

## commit
8f7b1adf,79ede919,a64ba6c6

## deployed
yes

## pin
engine/probes/probe-frozen-frontier.js

## ATTENTION
- probe-frozen-frontier.js's OWN fixture was buggy (used a dangling `after` instead of a real undeclared-session row) — any future edit to this probe should re-verify its fixture models a real seeding-time state, not a synthetic shortcut.
- This validation pass sits directly upstream of the frozen-goal-alarm defect found the next day (seq `frozen-goal-alarm-fix`) — the alarm bug surfaced BECAUSE this hardening started exercising more seeding paths.
- probe-frozen-frontier.js fixture itself was buggy; re-verify it models real seeding state
- this hardening pass is what surfaced the next day's frozen-goal-alarm defect
