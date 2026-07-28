# team-monitor — the run's one raw-source sensor (exposure v1)

The ONE component that touches raw observation sources — tmux panes, harness session files, /proc RAM and pressure, pending prompts — and converts them into a single canonical timestamped snapshot at `{goal}/runs/run-{n}/state.json` that every other consumer reads instead.

Registry record: **CMP-20** (`sd-graph show team-monitor`), settled by `decisions.md#d-team-observation-tools`. The legacy name `ctx-monitor` is that record's ALIAS — it was renamed at the 2026-07-25 settle sitting (R24) — and resolves to this same component.

## Invocation — TWO runnables, ONE component

    rbtv orchestration team-monitor            # this entry point + both runnables
    tool/rbtv-team-monitor <verb> [args]       # the sensor: start/ensure/stop/status/selftest
    tool/rbtv-ctx-monitor  [args]              # the per-pane sensing ENGINE the sensor imports

⚠ **`rbtv-ctx-monitor` is not a second component.** The engine ships inside THIS capability's
`tool/` deliberately, so its runnable stays reachable without `rbtv orchestration` publishing a
component named with a name R24 retired to alias status. Ruled by the `leader` at core-build task
7.40 (`#852`), after the seat measured that "the orchestration three" was two components and one
engine. The engine is separately runnable and useful alone: the harness-agnostic outside-observer
audit of a live team's panes.

Verbs (`start` · `ensure` · `stop` · `status` · `selftest`), the snapshot schema, the
inheritance argument, and the boundary proofs are in the component's own README —
`orchestration/cli/team-monitor/README.md`. Not restated here (`PRIN-11`).

## What this folder is, and what it is NOT

This is the **exposure half only** (core-build task 7.40). It makes an already-shipping tool
reachable through the `rbtv` CLI; it moves no code and changes no behaviour.

**The implementation deliberately stays at `orchestration/cli/team-monitor/`.** That is not
drift: `rbtv/CLAUDE.md` § CLI Tool Placement rules that the existing off-tree orchestration CLIs
**stay in place until the Phase-6 migration materializes the CMP-5 tree and moves them**. So
`tool/rbtv-team-monitor` is a thin wrapper over the in-place script, in the same v1-stand-in
shape as `ignite/capabilities/goals-tree/tool/rbtv-goal`. When Phase-6 moves the script, this
wrapper is the one file that changes.

⚠ The per-machine symlinks (`coordinate`, `teamview` in `~/.local/bin/`) are NEVER synced by git
and point at the in-place paths. Nothing here repoints or breaks them, precisely because nothing
moved.
