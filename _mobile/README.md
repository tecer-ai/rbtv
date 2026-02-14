# RBTV `_mobile` Harness Boundary

This folder contains the RBTV-side integration harness for Robotville mobile operations.

The harness exists to map RBTV workflow intents into Nanobot gateway interactions without rebuilding Nanobot internals.

## Scope

`_mobile` owns only adapter and policy logic that RBTV needs to connect safely to Nanobot:

- command mapping and routing from RBTV inputs to gateway-ready calls
- canonical workflow-state access through `project-memo.md`
- pre-routing safety gates such as allowlist enforcement
- deployment-facing integration artifacts for this harness (for example systemd templates and small ops patches)

## Non-Duplication Rules

`_mobile` must never duplicate Nanobot transport or runtime responsibilities.

`_mobile` must never implement its own websocket/socket-mode client, event loop runtime, or gateway process manager.

`_mobile` must never fork or shadow Nanobot channel/provider configuration schemas.

`_mobile` must never persist a second workflow-state authority when `project-memo.md` is the canonical source.

When a behavior already exists in Nanobot, `_mobile` must call or adapt it rather than re-implement it.

## Responsibility Split

Nanobot owns:

- Slack and provider transport/runtime lifecycle
- gateway process execution and resilience behavior
- channel protocol handling and low-level message delivery

RBTV `_mobile` harness owns:

- translation of RBTV commands into Nanobot-compatible intents
- deterministic routing decisions for allowed command paths
- read/write adapter logic for canonical project memo continuity
- pre-routing policy checks before handing work to Nanobot

## Documentation

| Document | Purpose |
|----------|---------|
| `HOW-IT-WORKS.md` | Architecture, bootstrap system, inbound pipeline, agent system, VPS instance layout, VPS deployment, design decisions |
| `_docs/` | Operational docs — deployment runbook, smoke checklist, server access, env template, troubleshooting, provisioning guide |

## Implementation Contract

All new harness modules must live under `_bmad/rbtv/_mobile/`.

Operational documentation (runbooks, checklists, server access) lives under `_mobile/_docs/`.

Any change that blurs ownership between `_mobile` and Nanobot is out of scope and must be rejected.
