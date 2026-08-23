# 20260821-c-delete-goal-watcher-job — Delete goal watcher job

kind: change
component: jobs
date: 2026-08-21
commit: 9c3aee33
deployed: yes
pin: NONE FOUND — deletion's correctness is the absence of the deleted surface
components: engine
seeded: true

## What it is
Delete the dead goal-watcher-job program and its 12 dedicated probes.

Deletion of `ignite/jobs/goal-watcher-job.py` (3053 lines) and its 12 dedicated probes (probe-dead-room-sensor-session.py, probe-goal-watcher-census-inrun.py, probe-goal-watcher-delivery-retry.py, probe-goal-watcher-door-exemption.py, probe-goal-watcher-ghostrow-debounce.py, probe-goal-watcher-homings.py, probe-goal-watcher-revival.py, probe-goal-watcher-selftest.py, probe-goal-watcher-worktree-watch-start.py, probe-headless-retention-unknown.py, plus team-kit/probes/probe-lifecycle-exec.py and probe-watchdog-goal-watcher-arm.py under daemon-watchdog), plus docs updates (ignite/CLAUDE.md, jobs/README.md, modules/ignite.md, team-kit/roles.md, floor-lint.py).

## Why
D1/D15: dead/unreachable after engine/reconcile.js replaced it two days earlier.

`fix-inventory.csv` D1/D15 — this program was already dead/unreachable after the `selfheal-to-reconcile` creation (engine) replaced it with `engine/reconcile.js` two days earlier (`d1ca8097` deleted the smaller selfheal-room* siblings; this commit finishes the job by deleting the larger goal-watcher-job.py itself and its dedicated probes).

## How to use & where wired
Nothing — pure deletion. engine/reconcile.js is the live replacement.

Nothing — this is a pure deletion. The reconcile.js watcher (see `selfheal-to-reconcile`, engine) is the live replacement.

## commit
9c3aee33

## deployed
yes

## pin
NONE FOUND — deletion's correctness is the absence of the deleted surface

## ATTENTION
- D62's KEEP-until-proven-safe discipline (system-problems digest §2) applies to any FUTURE proposed deletion matching a fix-inventory row — this deletion predates/motivated that rule; don't assume every large deletion is automatically safe just because this one was.
- This is the SECOND of two deletion commits for the same dead machinery (d1ca8097 two days earlier deleted the smaller selfheal-room* files) — understanding "what used to watch goals before reconcile.js" needs both commits, not just this one.
- D62 KEEP-until-proven-safe discipline was motivated partly by deletions like this one
- second of two deletion commits for the same dead machinery; both needed to understand the history
