# teamview — the run's read-only dashboard (exposure v1)

One live screen for a multi-agent tmux run: the session's windows and panes with their seat names, harness, model, context used and last-activity age, plus plan-limit bars for every provider account on the machine.

Registry record: **CMP-24** (`sd-graph show teamview`), settled by `decisions.md#d-teamview-record`.

**teamview RENDERS; it never SENSES and it never ACTS.** It reads the canonical snapshot
`{goal}/runs/run-{n}/state.json` written by `team-monitor` (CMP-20) and nothing else. No
threshold it displays is a threshold it enforces. The snapshot's age is always on screen and a
stale snapshot renders a visible warning rather than silently-current data.

## Invocation

    rbtv orchestration teamview                # this entry point + the runnable surface
    tool/rbtv-teamview [--package <run-folder>] [--once]

The run folder resolves from `--package`, else by walking UP from the current directory, else a
teaching refusal at exit 2. Layouts, the view flags, and what is deliberately OUTSIDE the
state.json boundary are in the component's own README —
`orchestration/cli/teamview/README.md`. Not restated here (`PRIN-11`).

## What this folder is, and what it is NOT

This is the **exposure half only** (core-build task 7.40). It makes an already-shipping tool
reachable through the `rbtv` CLI; it moves no code and changes no behaviour.

**The implementation deliberately stays at `orchestration/cli/teamview/`.** That is not drift:
`rbtv/CLAUDE.md` § CLI Tool Placement rules that the existing off-tree orchestration CLIs
**stay in place until the Phase-6 migration materializes the CMP-5 tree and moves them** — and
names `orchestration/cli/teamview/` explicitly. So `tool/rbtv-teamview` is a thin wrapper over
the in-place script, in the same v1-stand-in shape as
`ignite/capabilities/goals-tree/tool/rbtv-goal`. When Phase-6 moves the script, this wrapper is
the one file that changes.

⚠ The per-machine `teamview` symlink in `~/.local/bin/` is NEVER synced by git and points at the
in-place script. Nothing here repoints or breaks it, precisely because nothing moved.
