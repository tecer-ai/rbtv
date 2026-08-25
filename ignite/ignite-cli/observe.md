---
id: observe
description: "See what the fleet is doing — jobs, queue, executions, logs, open owner asks, tmux panes, and provider spend. Reach for it before asking anyone what happened, and BEFORE concluding a run is stuck. It reads; it never acts on a goal or a seat."
inputs: what you want to see — a job or queue row, an execution's status or log, the owner asks still waiting, the live panes, or where the provider budget went
outcome: the caller holds the reading, taken from the surface that actually owns it, instead of inferring fleet state from a stale file or a seat's own self-report
outputs: a jobs/queue/execution listing, a log tail, the open-ask set, a pane overview, or a provider-usage breakdown — returned to the caller, never routed or saved by this capability
---

<capability>

# observe — which reading surface, and when

Law: `spec-component-map.md` §7.2. This file answers only **"which tool"**. Every tool below
documents its own flags — ask it (`<tool> -h`, `rbtv ignite <verb> --help`), never guess, and
never expect this file to restate a flag surface.

Fleet state lives in the daemon's store and is read through the front door. Panes and spend
live outside it and have their own readers. A component's own self-report is not a reading:
a dead process keeps its last good status line.

## Do you need this at all?

- **You want to CHANGE something** — the daemon, a goal, a seat's cast → `daemon-ops`,
  `goal-ops`, `staffing`. This bundle answers questions.
- **You are inside a goal and owe the team a message** → `coord-ops`.

## The cheapest rung that works — stop at the first row that holds

| You need | Reach for |
|---|---|
| One-line "is the daemon alive and what does it think it is doing" | `rbtv ignite status` |
| The job catalogue, the pending queue, or one execution's status | `rbtv ignite inspect jobs` / `inspect queue` / `inspect status <id>` |
| An execution's log, or its thread's messages | `rbtv ignite inspect logs <id>` / `inspect messages <id>` |
| Every run in ONE state — every failed, every stalled | `rbtv ignite inspect executions --status <s>` |
| To change the job/queue set itself — register, deregister, enqueue, remove a queue row, snooze a warning, kill a session | the `rbtv ignite` job/queue/session verbs (`register-job`, `deregister-job`, `add-job`, `remove-job`, `snooze`, `kill`) |
| Every owner ask still OPEN across every goal | `rbtv ignite inspect asks` — the fleet view |
| The asks THIS caller still owes an answer to | `owed-answers` |
| What the live tmux panes are doing, at a glance | `tmux-overview`, or `overview-compact` when the glance must fit in a small pane |
| Where the provider spend went | `provider-usage` |

**The skipped rung is the first one.** Opening a log to find out whether the daemon is up is
the recurring waste — `status` costs one gateway call.

**The wrong rung is the file system.** Reading a goal's state file directly races the daemon
that owns it; the `inspect` targets are the read half of the same records.

## Deliberately not in this bundle

| Tool | Why not |
|---|---|
| `teamview` | gone — archive-moved out of the repo (§7.1). No successor; use `tmux-overview` |
| `team-monitor`, `ctx-monitor` | gone — deleted with the observer batch (§7.1) |
| `statusline-usage` | internal-daemon — a harness statusline hook, not a reading you take |

A skill is discovery, not a grant: a caged seat still runs only what its `exposed-clis:`
block names.
