---
description: The run's read-only dashboard — one live screen of a multi-agent tmux run (seats, harness, model, context used, activity age, provider plan-limit bars), rendering the team-monitor snapshot and nothing else.
---

# teamview — the run's read-only dashboard

One live screen for a multi-agent tmux run: the session's windows and panes with their seat names, harness, model, context used and last-activity age, plus plan-limit bars for every provider account on the machine.

Registry record: **CMP-24** (`sd-graph show teamview`), settled by `decisions.md#d-teamview-record`.

**teamview RENDERS; it never SENSES and it never ACTS.** It reads the canonical snapshot
`{goal}/runs/run-{n}/state.json` written by `team-monitor` (CMP-20) and nothing else. No
threshold it displays is a threshold it enforces. The snapshot's age is always on screen and a
stale snapshot renders a visible warning rather than silently-current data.

## Invocation

    tool/teamview.py [--package <run-folder>] [--once]

The run folder resolves from `--package`, else by walking UP from the current directory, else a
teaching refusal at exit 2. Layouts, the view flags, and what is deliberately OUTSIDE the
state.json boundary are in the component's own README — `tool/README.md`. Not restated here
(`PRIN-11`).

## Migration note (2026-08-23)

The script moved here from `orchestration/cli/teamview/` in the owner-directed component-shape
migration (the move `rbtv/CLAUDE.md` § CLI Tool Placement used to defer to "Phase-6"). The former
`tool/rbtv-teamview` wrapper is deleted; nothing referenced its part-id.

⚠ The per-machine `teamview` symlink in `~/.local/bin/` is NEVER synced by git — it must be
repointed at `orchestration/teamview/tool/teamview.py` ON EACH MACHINE after this migration
(done on the ignite VPS 2026-08-23; the Windows desktop is pending).
