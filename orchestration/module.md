---
description: "The orchestration module — observing a live multi-agent run: the team-monitor sensor (the run's one canonical snapshot) and the teamview dashboard that renders it."
---

<module>

# orchestration

The `orchestration/` module hosts the components that OBSERVE a live multi-agent run. The
coordination mechanics themselves (seats, rooms, messaging) are the ignite module's team-kit; this
module senses and renders.

**Migrated to the component shape 2026-08-23 (owner-directed).** The scripts previously sat
off-tree under `orchestration/cli/` behind thin `rbtv-*` wrappers in `capabilities/` — the layout
`rbtv/CLAUDE.md` § CLI Tool Placement deferred to "Phase-6". The wrappers are deleted; the
module-root `exposure.csv` split into per-component manifests (its dangling `dispatch-scaffold`
row was dropped — its entry point existed nowhere).

## Components

| Component | What it is |
|-----------|-----------|
| `team-monitor/` | **CMP-20** — the run's ONE raw-source sensor: reads tmux panes, harness session files, /proc, pending prompts, and writes the canonical snapshot `{goal}/runs/run-{n}/state.json`. Its `tool/` also ships `ctx_monitor.py`, the per-pane sensing engine (CMP-20's retired-alias name; not a component). |
| `teamview/` | **CMP-24** — the run's read-only dashboard: renders the team-monitor snapshot (seats, harness, model, context, activity, provider plan-limit bars); never senses, never acts. |

## hooks/ — unplaced, pending owner ruling

`hooks/context-monitor.py` (+ its tests) predates the component shape and has no home in it (the
KG's component-folder children include no hooks folder). It keys on a retired skill name
(`rbtv-orchestrating`) and is registered in no settings file, so it cannot fire today. Deletion or
re-homing is the owner's call — recorded 2026-08-23, left in place untouched.
