---
description: Use when operating Ignite — a primary agent's Slack turn or schedule (ignite-agent). The CLI self-explains; enter here to find what you need.
---

# ignite

The runtime layer of rbtv. Ignite 0.2 is `agents/` — a Slack message or a scheduled wake runs one primary-agent turn (`ignite-agent`).

This file is the module entry point. It lists what is here in one line each and routes into the CLI. Each CLI self-explains through `-h`.

## Command-line capabilities

| Capability | One line | Reach it |
|---|---|---|
| `ignite-agent` | Settings, schedule, work, wake, post, and create against a primary-agent home. | `ignite-agent -h` |

## Drilling

```
rbtv ignite                  this module's components and action verbs
rbtv ignite <component>      that component's entry point
```

Operator steps for the 0.2 service are [`agents/runbook.md`](agents/runbook.md).

## Components

| Folder | One line |
|---|---|
| `agents/` | Ignite 0.2: runnable Node service. Slack or schedule wakes one primary-agent turn; state lives in the workspace `.rbtv/agents/`. Operator steps: `agents/runbook.md` |
