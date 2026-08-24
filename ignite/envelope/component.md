---
description: Plan-time per-goal envelope compiler — template, deny-list, and daemon-owned records folded into a conflict-free bind list.
---

# envelope

The permissions unit of redesigned ignite. One plan-time compiler turns the versioned template + deny-list + daemon-owned records + the plan's fill-ins (named repos, project folder, credential names, extra paths) into a per-goal bind list. Every worker seat of the goal gets that same list. Staff stay uncaged; this component does not ship a staff cage profile.

This folder holds the **compiler**, its three owner-gated config files, the **launch consumer** (refuse-before-spawn, `failed: launch-refused` stamp, credential resolve + env injection), **scratch-config shims** for file-reading tools, and the **template-defect wall report** record.

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

- `admitLaunch(input)` → `{ spawn: true, binds, credentialNames, shims }` or `{ spawn: false, refuse }`
- `isStaffUncaged(seatPath)` — `leader` / `goal-master` / `channel-master` only [T2-R4]
- `LaunchRefused` — thrown from `composeCageFor` on refuse

`require('./credentials')`: `resolveCredentials(names, store)` fails a plan naming a missing/empty credential; `injectDeclaredEnv` returns only declared names.

`require('./stamp')`: `stampLaunchRefused` writes `failed` / `reason_class: launch-refused` through the ending-store WRITE API.

`require('./shims')`: `writeConfigShims` copies an **enumerated set of config files** — never a store directory — into `{goal}/scratch/config-shims/` at launch: `~/.claude.json`, `~/.claude/settings.json`, `~/.claude/.credentials.json`, `~/.codex/config.toml`, `~/.codex/auth.json`, `~/.config/opencode/opencode.json{,c}`, `~/.local/share/opencode/{auth,mcp-auth}.json`, and the stools/gtools `config.yaml`. Real store paths never join the bind list. A store's data tree is orders of magnitude larger than its config (`~/.local/share/opencode` is a 6.4 GB session database) — widening an entry to its parent directory fills the disk on one launch.

`admitLaunch` **creates `{goal}/scratch` before it compiles**. Template family 4 bakes that path and the compiler refuses any baked path that does not resolve, so the launch step that writes the shims into scratch is also the step that materializes it; compiling first refused every first launch of every goal.

`require('./wall-report')`: `writeWallReport` writes `{path, family-match, seat, goal}`. `family-match` is `cache` / `config` / `temp` / `none`. No Slack post.

Conflict and unresolved predicates live in `server/spawn/seat-grants.js` (`conflictBind`, `unresolvedBind`) so admission and spawn cannot drift.

## Tests

`node ignite/envelope/envelope-compiler.selftest.js` — stdout contains `PASS compiler`.
`node ignite/envelope/envelope-launch.selftest.js` — stdout contains `PASS refusal` and `PASS injection`.
`node ignite/envelope/wall-report.selftest.js` — stdout contains `PASS wall-report`.
`node ignite/envelope/envelope-shims.selftest.js` — stdout contains `PASS shims`.
