---
description: Plan-time per-goal envelope compiler — template, deny-list, and daemon-owned records folded into a conflict-free bind list.
---

# envelope

The permissions unit of redesigned ignite. One plan-time compiler turns the versioned template + deny-list + daemon-owned records + the plan's fill-ins (named repos, project folder, credential names, extra paths) into a per-goal bind list. Every worker seat of the goal gets that same list. Staff stay uncaged; this component does not ship a staff cage profile.

This folder holds the **compiler**, its three owner-gated config files, the **launch consumer** (refuse-before-spawn, `failed: launch-refused` stamp, credential resolve + env injection), **scratch-config shims** for file-reading tools, and the **template-defect wall report** record.

## Config (owner-gated, no runtime verb)

| File | Spec |
|---|---|
| `envelope-template.yaml` | the seven T2-R3 families (the old `rbtv-and-mirror` split 2026-08-30 into `rbtv-repo` and its own `mirror` family, so a plan may carve rw under the mirror without touching the rbtv repo) + family 8, the ending store (`.rbtv/runtime/ignite`, rw — the seat stamps its own ending); benign cache/config/temp baked in |
| `envelope-deny-list.yaml` | starting deny set including the credential store |
| `daemon-owned-records.yaml` | record files + `seats/` + proper-subfolder carve (`coordination/` is NOT here — the bus is the seat protocol’s own write surface, D3) |

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
- `loadFillIns(goalDir)` — reads `{goal}/envelope.json`, THE SOLE READER. `planning/path_b.py#_land_envelope` is now the writer (owner-flagged `owner-flagged-birth-writes-no-envelope`, 2026-08-30 — nothing wrote it before). A goal born via Path B (marked by `planning/bound-plan.json`, the one signal available here) with no `envelope.json` warns once to stderr before falling back to `compilePlanning`, same as always — any other goal shape stays silent

`require('./credentials')`: `resolveCredentials(names, store)` fails a plan naming a missing/empty credential; `injectDeclaredEnv` returns only declared names. `admitLaunch` is the production caller: a compiled `credentialNames` list that is missing or empty in `.rbtv/config/.env` returns `{ spawn: false, refuse: { kind: 'missing-credential' } }` — no silent unset spawn. The planning-stage producer of those names is `ignite/planning/plan_envelope.py` (writes `<plan-artifacts>/envelope.json` into the bound commit); `path_b.py#_land_envelope` copies that file at mint.

`require('./stamp')`: `stampLaunchRefused` writes `failed` / `reason_class: launch-refused` through the ending-store WRITE API.

`require('./shims')`: `writeConfigShims` copies an **enumerated set of config files** — never a store directory — into `{goal}/scratch/config-shims/` at launch: `~/.claude.json`, `~/.claude/settings.json`, `~/.claude/.credentials.json`, `~/.codex/config.toml`, `~/.codex/auth.json`, `~/.config/opencode/opencode.json{,c}`, `~/.local/share/opencode/{auth,mcp-auth}.json`, and the stools/gtools `config.yaml`. Real store paths never join the bind list. A store's data tree is orders of magnitude larger than its config (`~/.local/share/opencode` is a 6.4 GB session database) — widening an entry to its parent directory fills the disk on one launch.

`admitLaunch` **creates `{goal}/scratch` before it compiles**. Template family 4 bakes that path and the compiler refuses any baked path that does not resolve, so the launch step that writes the shims into scratch is also the step that materializes it; compiling first refused every first launch of every goal.

`require('./wall-report')`: `writeWallReport` writes `{path, family-match, seat, goal}`. `family-match` is `cache` / `config` / `temp` / `none`. No Slack post.

Conflict and unresolved predicates live in `supervisor/spawn/seat-grants.js` (`conflictBind`, `unresolvedBind`) so admission and spawn cannot drift.

## Tests

`node ignite/envelope/envelope-compiler.selftest.js` — stdout contains `PASS compiler`.
`node ignite/envelope/envelope-launch.selftest.js` — stdout contains `PASS refusal`, `PASS injection`, `PASS missing-credential-refuses`, and `PASS path-b-born-warns-once`.
`node ignite/envelope/probes/probe-credential-injection.js` — stdout/out file contains `ALL LEGS PASS`.
`node ignite/envelope/wall-report.selftest.js` — stdout contains `PASS wall-report`.
`node ignite/envelope/envelope-shims.selftest.js` — stdout contains `PASS shims`.

## What moved in with the component-first migration

`spec-component-map` §2 landed these here, with history, as part of impl-structure
(move-only; no symbol changed):

- from `engine/`: `cage-admission.js` - the pre-enqueue admission test - plus its two
  probes (`probes/probe-cage-workspace-grammar.js`, `probes/probe-outputs-resolver.js`)
- from `config/`: `spawn-profiles.yaml`, the boot-read launch configuration
  `RBTV_IGNITE_CONFIG_PATH` points at. There is no top-level `ignite/config/` any more.

## The fence — what a seated process can touch (D3, 2026-08-19)

The sandbox is a **fence**, not a cage. Threat model: agents writing in **repos that are not the
goals tree**. Rogue writes on another seat's folder or on the wrong file inside the goal folder are
not a concern for now. **Record forgery is a NON-goal.**

Allow-list (bwrap, fail-closed if `bwrap` is missing — D59):

1. the goal's **worktree branches** — read/write
2. the **goal folder** — read; **goal-folder artifacts — write/edit** (one `bind:{goalDir}` covers
   ledgers, planning, coordination, `sessions.csv`)
3. the seat's **own seat folder** — read/write, **except `seat.md`**
4. **the rbtv repo** — read, no carve; **the workspace `.rbtv/mirror/`** — read by default, but (2026-08-30) a plan may carve a write grant under it, the same carve exception the vault-wide read floor already admits
5. **coordination ledgers — WRITABLE** (no file-level ro-bind of records, no proxy writers)
6. **env/secret files — simply not present** (hardcoded denies + pattern floor; do not pierce)

A wall-control surface stays file-level RO: `seat.md`. That is the fence holding its own posts, not
forgery-prevention. Its former sibling `coordination/permission-edits.csv` (the leader's audited
cage-widen store) is GONE [T2-R12, T1-R9]: owner auth is an answer to a live ask, not a standing
grant a cage reads back.

**PID namespace is gone — and so is the cgroup namespace (F-6, owner-ruled 2026-08-21).** The fence
unshares user/ipc/uts only. The cgroup unshare was inherited from decomposing `--unshare-all` (never
a chosen protection — no cgroupfs is mounted in the cage) and it blinded the kit's
`carrier_self_session()`, the D43 identity corroborator, structurally shutting the crashed-row door
for every caged chair; a seat now reads its own `rbtv-worker-<session-id>` unit from
`/proc/self/cgroup`, which is the point. In-cage `/proc` shows **host pids**, so the kit's liveness
read (`ident_is_live_process`) is true. **Accepted consequence:** a seat can see and signal host
processes. The threat model is filesystem writes outside the goals tree, not process isolation. Do
not build a mitigation.

**Secrets (D13).** The agent cannot read the key; the tool can. Env files are never bound into a
fence. The launcher/daemon reads the env file and starts the **TOOL process** with
`EnvironmentFile=` (`supervisor/spawn/carrier.js#buildSystemdRunArgs`). `--setenv` is the
never-secret channel (PATH / `IGNITE_GATEWAY_ADDR` only). Agents never read envs. No broker, no
gate, no capability-request dance.
