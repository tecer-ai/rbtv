---
id: daemon-ops
description: "Operate the ignite daemon itself — start/stop/health, the ticker's cadence knobs, the probe suite that proves the tree, and the PATH relink after a tool moves. Reach for it whenever the DAEMON (not a goal, not a seat) is the subject. Internal-daemon tools are deliberately absent."
inputs: what you need from the daemon — its health, a start/stop/reload, a cadence change, a proof that the tree still works, or a re-link of the shared bin dir
outcome: the daemon question is answered or the daemon act is done through the one tool that owns it, without reaching for a systemd unit or hand-editing a config file
outputs: a health/state reading, a changed daemon or ticker setting, a probe-suite verdict, or a refreshed set of PATH links — returned to the caller, never routed or saved by this capability
---

<capability>

# daemon-ops — which daemon tool, and when

Law: `spec-component-map.md` §7.2. This file answers only **"which tool"**. Every tool below
documents its own flags — ask it (`<tool> -h`), never guess, and never expect this file to
restate a flag surface.

The daemon is ONE long-lived process with a ticker inside it. Nothing here edits its state
store directly: an operator tool talks to the daemon, and the daemon owns its own records.

## Do you need this at all?

- **A goal, a seat, or a run** is your subject → `goal-ops`, not this file.
- **Reading what the daemon is currently doing** — its queue, its executions, its logs →
  `observe`. This file is for acting ON the daemon; `observe` is for reading THROUGH it.
- **The daemon looks wrong and you want it restarted** → that is an owner-console act, and
  `rbtv ignite daemon` is the door. Never `systemctl` behind its back.

## The cheapest rung that works — stop at the first row that holds

| You need | Reach for |
|---|---|
| To know whether the daemon is up, and what it thinks its state is | `rbtv ignite status` (`observe`'s cheapest rung — it costs one gateway call and no privilege) |
| To START, STOP, RELOAD or otherwise operate the daemon process | `rbtv ignite daemon <verb>` |
| To change how often the ticker fires, or to read the cadence it is on | `rbtv ignite ticker <verb>` |
| To PROVE the tree still works after an edit — the repo-wide probe suite | `probe-suite` |
| To re-link the shared bin dir after a tool moved, was added, or went missing from PATH | `link-tools` |

**The skipped rung is the first one.** Reaching for `rbtv ignite daemon` to answer "is it
alive?" is the common waste — a read is a read, and the front door already answers it.

**The over-reached rung is `link-tools`.** A tool missing from PATH is almost always a
missing or misplaced `method=path` row on its owning component's `exposure.csv`; re-linking
over a bad declaration relinks nothing. Fix the row, then link.

## Deliberately not in this bundle

| Tool | Why not |
|---|---|
| `rbtv-ignite-watchdog` | internal-daemon (§7.1) — the daemon's own supervisor, invoked by systemd, never by you |
| `probe-suite-scheduled` | internal-daemon — the systemd timer's wrapper around `probe-suite`. Run `probe-suite` yourself instead |

A skill is discovery, not a grant: a caged seat still runs only what its `exposed-clis:`
block names.
