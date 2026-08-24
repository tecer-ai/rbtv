---
description: Plan-time per-goal envelope compiler — template, deny-list, and daemon-owned records folded into a conflict-free bind list.
---

# envelope

The permissions unit of redesigned ignite. One plan-time compiler turns the versioned template + deny-list + daemon-owned records + the plan's fill-ins (named repos, project folder, credential names, extra paths) into a per-goal bind list. Every worker seat of the goal gets that same list. Staff stay uncaged; this component does not ship a staff cage profile.

This folder holds the **compiler**, its three owner-gated config files, and the **launch consumer**: refuse-before-spawn, `failed: launch-refused` stamp, and credential resolve + env injection.

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

## Launch consumer

`require('./launch')`:

- `admitLaunch(input)` → `{ spawn: true, binds, credentialNames }` or `{ spawn: false, refuse }`
- `isStaffUncaged(seatPath)` — `leader` / `goal-master` / `channel-master` only [T2-R4]
- `LaunchRefused` — thrown from `composeCageFor` on refuse

`require('./credentials')`: `resolveCredentials(names, store)` fails a plan naming a missing/empty credential; `injectDeclaredEnv` returns only declared names.

`require('./stamp')`: `stampLaunchRefused` writes `failed` / `reason_class: launch-refused` through the ending-store WRITE API.

Conflict and unresolved predicates live in `server/spawn/seat-grants.js` (`conflictBind`, `unresolvedBind`) so admission and spawn cannot drift.

## Tests

`node ignite/envelope/envelope-compiler.selftest.js` — stdout contains `PASS compiler`.
`node ignite/envelope/envelope-launch.selftest.js` — stdout contains `PASS refusal` and `PASS injection`.
