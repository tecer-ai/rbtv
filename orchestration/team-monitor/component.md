---
description: The run's ONE raw-source sensor — reads tmux panes, harness session files, /proc RAM and pending prompts, and writes the single canonical snapshot ({goal}/runs/run-{n}/state.json) every other consumer reads instead.
---

# team-monitor — the run's one raw-source sensor

The ONE component that touches raw observation sources — tmux panes, harness session files, /proc RAM and pressure, pending prompts — and converts them into a single canonical timestamped snapshot at `{goal}/runs/run-{n}/state.json` that every other consumer reads instead.

Registry record: **CMP-20** (`sd-graph show team-monitor`), settled by `decisions.md#d-team-observation-tools`. The legacy name `ctx-monitor` is that record's ALIAS — it was renamed at the 2026-07-25 settle sitting (R24) — and resolves to this same component.

## Invocation — TWO runnables, ONE component

    tool/team_monitor.py <verb> [args]         # the sensor: start/ensure/stop/status/selftest
    tool/ctx_monitor.py  [args]                # the per-pane sensing ENGINE the sensor imports

⚠ **`ctx_monitor.py` is not a second component.** The engine ships inside THIS component's
`tool/` deliberately: `ctx-monitor` is CMP-20's RETIRED ALIAS (R24), so no component may carry
that name. Ruled by the `leader` at core-build task 7.40 (`#852`), after the seat measured that
"the orchestration three" was two components and one engine. The engine is separately runnable
and useful alone: the harness-agnostic outside-observer audit of a live team's panes — its own
doc is `tool/ctx-monitor.md`.

Verbs (`start` · `ensure` · `stop` · `status` · `selftest`), the snapshot schema, the
inheritance argument, and the boundary proofs are in the component's own README —
`tool/README.md`. Not restated here (`PRIN-11`).

## Migration note (2026-08-23)

The scripts moved here from `orchestration/cli/team-monitor/` and `orchestration/cli/ctx-monitor/`
in the owner-directed component-shape migration (the move `rbtv/CLAUDE.md` § CLI Tool Placement
used to defer to "Phase-6"). The former `tool/rbtv-team-monitor` / `tool/rbtv-ctx-monitor`
wrappers — whose only job was pointing at the off-tree scripts — are deleted; nothing referenced
their part-ids.
