---
description: Plan-time per-goal envelope compiler — template, deny-list, and daemon-owned records folded into a conflict-free bind list.
---

# envelope

The permissions unit of redesigned ignite. One plan-time compiler turns the versioned template + deny-list + daemon-owned records + the plan's fill-ins (named repos, project folder, credential names, extra paths) into a per-goal bind list. Every worker seat of the goal gets that same list. Staff stay uncaged; this component does not ship a staff cage profile.

This folder holds the **compiler** and its three owner-gated config files. Launch wiring (`composeCageFor`, refuse-before-spawn, env injection) is not here.

## Config (owner-gated, no runtime verb)

| File | Spec |
|---|---|
| `envelope-template.yaml` | seven T2-R3 families, benign cache/config/temp baked in |
| `envelope-deny-list.yaml` | starting deny set including the credential store |
| `daemon-owned-records.yaml` | record files + `coordination/` + `seats/` + proper-subfolder carve |

## Compiler API

`require('./compiler')`:

- `compile(input)` → `{ ok: true, binds, denies, credentialNames, posture: 'caged-worker' }` or `{ ok: false, refuse }`
- `compilePlanning(input)` → `compile` with zero plan fill-ins (the shipped planning envelope)
- `loadConfig(configDir?)` / `CONFIG_DIR`

Refuse is a **value**: `kind: conflict` carries the pair; `kind: unresolved` carries the path. The compiler never calls `lastCovering` and never creates a path to make a bind succeed.

## Tests

`node ignite/envelope/envelope-compiler.selftest.js` — stdout contains `PASS compiler`.
