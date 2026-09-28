---
description: Use when operating Ignite — a primary agent's Slack turn or schedule (ignite-agent), a coordinated multi-agent team run, or the staffing browse. The module's CLIs self-explain; enter here to find which one you need.
---

# ignite

The runtime layer of rbtv. Ignite 0.2 is `agents/` — a Slack message or a scheduled wake runs one primary-agent turn (`ignite-agent`). `team-kit/` is the mechanics for a parallel multi-agent team in tmux. `teambuild/` is the staffing-discovery browse.

This file is the module entry point. It lists what is here in one line each and routes into the CLI. Each CLI self-explains through `-h`.

## Command-line capabilities

| Capability | One line | Reach it |
|---|---|---|
| `ignite-agent` | Settings, schedule, work, wake, post, and create against a primary-agent home. | `ignite-agent -h` |
| team-kit | A coordinated parallel multi-agent team in tmux: checkin, typed append-only messaging, bounded reads, staged launches, close/renew ceremonies. | `coordinate -h` |
| teambuild | Staffing-discovery browse over the component databases. Binds nothing. | `rbtv teambuild -h` |

## Drilling

```
rbtv ignite                  this module's components and action verbs
rbtv ignite <component>      that component's entry point
```

The coordination kit's protocol is [`team-kit/protocol.md`](team-kit/protocol.md). Operator steps for the 0.2 service are [`agents/runbook.md`](agents/runbook.md).

## Components

| Folder | One line |
|---|---|
| `agents/` | Ignite 0.2: runnable Node service. Slack or schedule wakes one primary-agent turn; state lives in the workspace `.rbtv/agents/`. Operator steps: `agents/runbook.md` |
| `team-kit/` | The coordination kit: the `coordinate` CLI and its split modules, addressing, declared outputs, tmux viewports, messages, the checkout write API, the mirror driver and the `team-kit` skill |
| `teambuild/` | The staffing-discovery browse (`rbtv teambuild`) over the component databases — binds nothing |
