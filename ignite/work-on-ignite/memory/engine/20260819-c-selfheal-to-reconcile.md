# 20260819-c-selfheal-to-reconcile — Selfheal to reconcile

kind: change
component: engine
date: 2026-08-19
commit: 808902df,d1ca8097,9c3aee33,173b1fe3,b4f0f0e0
deployed: yes
pin: engine/probes/probe-reconcile.js
components: jobs,team-kit
seeded: true

## What it is
reconcile.js: one per-goal reconciliation loop replacing event/job selfheal.

`ignite/engine/reconcile.js` (808902df, 582 new lines) is a new per-goal watcher/reconciliation loop that replaces the old event/job-based "selfheal" machinery: `ensure-room-selfheal.js`, `jobs/ensure_room_selfheal.py`, `jobs/selfheal-room.py`, `jobs/selfheal-room-for-goal.py` (all deleted in `d1ca8097`), and later `jobs/goal-watcher-job.py` + its 12 dedicated probes (deleted in `9c3aee33`, a chore commit two days later — filed separately under `jobs`).

## Why
D1/D15: old selfheal fired off events/jobs disconnected from ledger state.

`fix-inventory.csv` D1/D15; `redesign-plan-seed.md#3` names "watcher/reconcile launching without measuring progress" as a recurring theme. The old design fired self-healing off discrete events/scheduled jobs, disconnected from the live ledger state; the redesign ruled a single per-goal reconcile loop should read owed work directly from the ledgers (sessions.csv, heart-store) and act first, escalate second.

## How to use & where wired
Invoked by lane-watch.js per goal tick; reads heart-store.js ledger state.

`reconcile.js` is invoked by the daemon's `lane-watch.js` per goal tick; it reads owed ledger state (heart-store.js/migrations.js/schema.sql additions land in the same commit) and drives seat relaunch/escalation. `jobs/README.md` and `ignite/CLAUDE.md` (173b1fe3, b4f0f0e0) were rewritten the same week to say "the goal watcher is engine/reconcile.js, not a job" (custody rule 4).

## commit
808902df,d1ca8097,9c3aee33,173b1fe3,b4f0f0e0

## deployed
yes

## pin
engine/probes/probe-reconcile.js

## ATTENTION
- The docs correction (173b1fe3/b4f0f0e0) exists because agents kept looking for "the goal watcher" under `ignite/jobs/` — it is `engine/reconcile.js`, not anything under jobs/.
- This commit's deletions (ensure-room-selfheal.js, selfheal-room*.py) sit in the same area where a later ruling (D12, not in this component) deleted grant machinery on an UNVERIFIED assumption reconcile already relaunched seats by name — verify any future deletion near reconcile.js against what the code actually does, not an assumption.
- docs correction shows the watcher was under jobs/ before; it is now engine/reconcile.js
- verify future deletions near reconcile.js against actual behavior, not assumption (cf D12)
