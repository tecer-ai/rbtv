---
description: Use when operating the ignite runtime — the daemon and its job queue, the goals tree, or a coordinated multi-agent team run. The module's CLIs self-explain; enter here to find which one you need.
---

# ignite

The runtime layer of rbtv: agents doing coordinated work over time. Two faces of one
substrate — the **ignite daemon** (a Node.js service that makes a workspace's job queue
launch due jobs on a runtime host) and the **team-kit** (mechanics for running a parallel
multi-agent team in tmux).

This file is the module entry point (`module entry point` — the skill-format front door the
installer realizes as this module's discovery skill). It lists what is here in one line each
and routes into the CLI; **it carries no bodies.** Each CLI self-explains through `-h`, which
is where the detail lives — progressive disclosure (`PRIN-3`), one rung at a time.

## Command-line capabilities

| Capability | One line | Reach it |
|---|---|---|
| `daemon-operator` | Local systemd USER unit ops that work precisely when the daemon is DOWN — `start`/`restart`/`stop`/`kill`/`unit`, on any of the three FIXED services via `--service ignite\|chat-bridge\|probe-suite`. Health is a FIELD, never the exit status. | `rbtv ignite daemon <verb>` · `-h` |
| `goals-tree` | The goals-tree machinery — `scaffold`/`reindex`/`lint`/`materialize` over a goal folder. | `rbtv goal <verb>` · `-h` |
| `daemon-watchdog` | One bounded liveness pass over the whole deployment — probe, restart through the units, DM the owner only on action or failure to restore. Normally nobody runs it: a systemd timer does, every 60s. | `capabilities/daemon-watchdog/tool/rbtv-ignite-watchdog --dry-run` · `-h` |
| `master-profile` | The channel master choosing its OWN harness and model — the `master_profile` field of the chat-bridge config, validated against the LIVE `profiles:` set. Same three verbs; the apply restarts `rbtv-chat-bridge`, which ends the requesting sitting — so `request --chat-thread <channel>:<ts>` makes it SELF-REPORT the outcome first: one `to: owner` bus row carrying the bracketed `[chat-thread:]` token, appended before the restart and carried into the thread by the chat bridge's bus ferry, which POSTS it verbatim on the `[deliver: post]` disposition rather than minting a sitting to paraphrase it. No `--effort`: effort is measurably not on the master spawn wire. | `capabilities/master-profile/tool/rbtv-master-profile <verb>` · `-h` |
| `bindings` | The CASTING SHEET a workflow is run through — which harness, model and effort each seat gets. `catalog` (what this box can spawn, effort NUMBERED, and the validator `set` uses), `inspect` (seats, definitions, hints, what is still uncast), `scaffold` (create-only), `set`. One file per workflow at `.rbtv/config/modules/{module}/{component}/bindings/{code}.json`; direct writes, no daemon, no restart. | `capabilities/bindings/tool/rbtv-bindings <verb>` · `-h` |
| gateway client | Enqueue and remove scheduled/periodic jobs, inspect runtime state. | `rbtv ignite <command>` · `-h` |
| team-kit | Run a coordinated parallel multi-agent team in tmux: checkin, typed append-only messaging, bounded reads, staged launches, close/renew ceremonies. | `coordinate -h` |

## Drilling

```
rbtv ignite                  this module's components, rules, and action verbs
rbtv ignite <component>      that component's entry point body + its invocable entry points
```

The daemon's conventions, install model, and state layout live in `ignite/CLAUDE.md`; the
team-kit's protocol in `ignite/team-kit/protocol.md`. Neither is restated here (`PRIN-11`).
