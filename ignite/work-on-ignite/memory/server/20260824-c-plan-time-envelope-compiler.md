# 20260824-c-plan-time-envelope-compiler — plan-time envelope compiler

kind: creation
component: server
date: 2026-08-24
commit: 570131d9
deployed: no
pin: ignite/envelope/envelope-compiler.selftest.js

## Motivation
The redesign replaces the 14-source per-seat `composeCageFor` grant stack and `lastCovering` later-wins with one plan-time per-goal envelope compiled to a simple bind list [T2-R1/R2/R3]. This sitting lands the pure compiler and its three owner-gated config files so launch can consume them later.

## Design
A new `ignite/envelope/` component (spec-component-map home) holds `compile` / `compilePlanning` plus `envelope-template.yaml`, `envelope-deny-list.yaml`, and `daemon-owned-records.yaml`. Refuse is a returned value (conflict pair or unresolved path), never a thrown spawn, never `lastCovering`. `spawn.js` / `cage.js` / `seat-grants.js` were not touched. Rejected: landing the compiler under `server/spawn/` (the map pins `envelope/`); growing `composeCageFor` in place (sibling `impl-envelope-launch` owns that hook).

## How it works
`compiler.js#compile` takes workspace/goal/rbtvRepo plus optional plan fill-ins (named repos, project folder, credential names, extra paths) and the three YAML files. It realpaths every source, refuses if a path is missing, folds the seven families plus daemon-owned RO carves, and returns `{ok, binds}` or `{ok:false, refuse}`. `compilePlanning` is the same call with zero fill-ins (spec §6). Credentials are names only — never binds. Launch (`impl-envelope-launch`) is the consumer.

## Consequences
No live launch path changed. `widen-cage` / grant store / credential-pierce stay deleted. Own-seat RW punch-back is recorded on `daemon-owned-records.yaml` (`own-seat-folder-rw`) but not applied here — every worker still gets the same per-goal list; launch punches `{self}`. Goal `scratch/` must already exist or compile refuses (compiler never mkdir). `ignite/module.md` gained an envelope row in the working tree mixed with sibling-seat hunks and was not committed.

## Verification
`node ignite/envelope/envelope-compiler.selftest.js` prints `PASS planning-zero-fill-in` and `PASS compiler`. `node --check` on the four new `.js` files exits 0. Config load asserts the seven family ids, twelve deny rows, and daemon-owned files/dirs. Deployed: no.

## ATTENTION
- Do not wire this into `composeCageFor` from a later envelope-compiler sitting — that hook belongs to `impl-envelope-launch`.
- Same-path different access is always a refuse; parent/child covering under `/tmp` (probe workspaces live there) is an authorized temp-floor carve, not `lastCovering`.
- `{home}/.config/opencode` and the other harness cred stores are excluded from family 7 on purpose — they are not extra RW openings [T2-R11].
- Filing this creation under `server` because `envelope` is not yet a work-on-ignite memory component.
- Do not wire compile() into composeCageFor
