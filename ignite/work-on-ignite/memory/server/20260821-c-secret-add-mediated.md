# 20260821-c-secret-add-mediated — Secret add mediated

kind: creation
component: server
date: 2026-08-21
commit: ac1c08d8,b6c64a25,92e7156c
deployed: yes
pin: server/internal-api/probes/probe-secret-add.js; server/spawn/probes/probe-secret-add-cage.js; team-kit/test_secret_add.py (UNSCHEDULED)
components: gateway,team-kit
seeded: true

## What it is
Mediated, out-of-cage secret-add: a caged seat requests, the daemon writes.

`b6c64a25` first builds coord.py's `secret-add` verb — a mediated, append-only env-var write for masters (268 lines). `ac1c08d8` (D49.1, next day) moves the actual secret-add WRITE out of the caged seat process entirely into an out-of-cage daemon intent (`server/internal-api/secret-add.js`, `authz.js`, `dispatch.js`), with `gateway/parse.js` and `gateway_client.py` carrying the mediated request, and `test_secret_add.py` shrunk (200→152 lines) since the write logic moved server-side. `92e7156c` (same window) is the truly-everything master cage referenced by the `truly-everything-master-cage` entry.

## Why
D49/D-6: a caged seat writing secrets directly is a forgery/leak risk.

`fix-inventory.csv` D49; `redesign-plan/decisions.md#D49` — a master seat needs to add secrets/env vars, but a caged seat writing directly to a secrets file is a forgery/leak risk; mediation moves the actual write to the daemon (never inside any cage) while the seat only submits a request.

## How to use & where wired
masters call coord.py secret-add; the daemon executes the write out-of-cage.

Masters call coord.py's `secret-add` verb, which hits `server/internal-api/secret-add.js` via the gateway, authorized by `authz.js`, executed by the daemon (out-of-cage), landing as an append-only env write.

## commit
ac1c08d8,b6c64a25,92e7156c

## deployed
yes

## pin
server/internal-api/probes/probe-secret-add.js; server/spawn/probes/probe-secret-add-cage.js; team-kit/test_secret_add.py (UNSCHEDULED)

## ATTENTION
- test_secret_add.py is explicitly UNSCHEDULED — it will not run in the routine probe-suite; if you touch secret-add, run it by hand, since the scheduled suite gives false confidence here.
- The write path moved TWICE in two days (b6c64a25 in-cage-ish → ac1c08d8 fully out-of-cage) — the out-of-cage daemon-intent shape (ac1c08d8) is the one that held; don't reintroduce a caged-seat direct write.
- test_secret_add.py is UNSCHEDULED; run it by hand when touching secret-add
- the write path moved twice in two days; out-of-cage daemon-intent is the shape that held
