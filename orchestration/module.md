---
description: "The orchestration module — formerly the team-monitor sensor and teamview dashboard, both deleted; only the unplaced hooks/ folder remains."
---

<module>

# orchestration

The `orchestration/` module hosted the components that OBSERVED a live multi-agent run. The
coordination mechanics themselves (seats, rooms, messaging) are the ignite module's team-kit; this
module used to sense and render.

**Migrated to the component shape 2026-08-23 (owner-directed).** The scripts previously sat
off-tree under `orchestration/cli/` behind thin `rbtv-*` wrappers in `capabilities/` — the layout
`rbtv/CLAUDE.md` § CLI Tool Placement deferred to "Phase-6". The wrappers were deleted then; the
module-root `exposure.csv` split into per-component manifests (its dangling `dispatch-scaffold`
row was dropped — its entry point existed nowhere).

## Components — both deleted (owner ruling, redesign D19, del-observers)

`team-monitor/` (CMP-20, the run's raw-source sensor writing `{goal}/runs/run-{n}/state.json`)
and `teamview/` (CMP-24, the dashboard rendering that snapshot) are DELETED. A terminal pane is a
viewport, never a heartbeat [T4-R8, C-15, C6]: "is it alive" is now answered only by probing the
supervisor registry (not yet built by any seat) — no standalone monitor, no dashboard reading a
snapshot file nothing writes any more. `teamview/` had no independent data source of its own; it
only ever rendered `team-monitor`'s output, so it could not survive the sensor's deletion either.

## hooks/ — unplaced, pending owner ruling

`hooks/context-monitor.py` (+ its tests) predates the component shape and has no home in it (the
KG's component-folder children include no hooks folder). It keys on a retired skill name
(`rbtv-orchestrating`) and is registered in no settings file, so it cannot fire today. Deletion or
re-homing is the owner's call — recorded 2026-08-23, left in place untouched.
