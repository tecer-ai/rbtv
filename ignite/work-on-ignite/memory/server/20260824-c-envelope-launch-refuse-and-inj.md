# 20260824-c-envelope-launch-refuse-and-inj — envelope launch refuse and inject

kind: creation
component: server
date: 2026-08-24
commit: c9615ca2
deployed: no
pin: ignite/envelope/envelope-launch.selftest.js

## Motivation
The redesign refuses conflicting and unresolved binds at launch and stamps `failed: launch-refused` before any process is born [T2-R1, C-6, T1-R18]. The compiler sitting left `compile()` unhooked; this sitting is the consumer.

## Design
New modules under `ignite/envelope/` (`launch.js`, `credentials.js`, `stamp.js`) own admit, inject, and stamp. `composeCageFor` calls `admitLaunch` instead of assembling the 14-source grant array. `lastCovering` is a visibility query that throws on mixed access. Conflict/unresolved predicates and the per-launch (not per-entry) posture live in `seat-grants.js`. Rejected: growing the grants array in place; stamping through `close_session_seat`; a staff cage profile.

## How it works
`admitLaunch` loads `{goal}/envelope.json` fill-ins when present, else `compilePlanning`. A refuse value throws `LaunchRefused`; the three spawn doors stamp via `stampLaunchRefused` (ending-store `stampSystem`) and do not start a process. Staff names `leader` / `goal-master` / `channel-master` return `{uncaged: true}` and skip bwrap. `resolveCredentials` fails a plan naming a missing or empty store key; `injectDeclaredEnv` emits only declared names as `--setenv`. An `exposedCli` RO cover of an RW bind is a compose-time refuse.

## Consequences
The 14-source `composeSeatCage` grant list is no longer the worker cage. `MasterBinds` is not consulted. Cage probes that drive the old composer against `composeCageFor` will go red — `impl-envelope-walls-suite` owns those updates. `ignite/module.md` was left uncommitted (sibling hunks).

## Verification
`node ignite/envelope/envelope-launch.selftest.js` prints `PASS refusal` and `PASS injection` and writes a stamp fixture containing `launch-refused`. `node ignite/envelope/envelope-compiler.selftest.js` still prints `PASS compiler`. `node --check` on every new/edited `.js` exits 0. Deployed: no.

## ATTENTION
- Do not re-run `conflictBind` over a compiled bind list: authorized temp-floor carves (workspaces under `/tmp`) look like covering conflicts. The compiler already refused real conflicts.
- `HARNESS_CRED_PATHS` / `resolveHarnessCredGrants` stay in `spawn.js` for `impl-envelope-walls-suite`; this sitting stopped calling them from `composeCageFor` and must not delete them.
- `stampLaunchRefused` uses ending-store WRITE (`stampSystem`, `reason_class: launch-refused`). A second stamp on the same `(goal, seat)` is write-once unless `replace: true`.
- Filing under `server` because `envelope` is not yet a work-on-ignite memory component.
- Do not re-run conflictBind over a compiled bind list: authorized temp-floor carves look like conflicts.
- HARNESS_CRED_PATHS stay in spawn.js for walls-suite; do not delete them here.
- stampLaunchRefused is ending-store WRITE; second stamp is write-once unless replace.
- Filing under server because envelope is not yet a memory component.
