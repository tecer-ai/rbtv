# 20260821-c-truly-everything-master-cage — Truly everything master cage

kind: creation
component: server
date: 2026-08-21
commit: 92e7156c
deployed: yes
pin: server/spawn/probes/probe-master-cage.js (D48-annotated, scheduled)
seeded: true

## What it is
A wide "truly-everything" cage profile for masters; workers explicitly refuse writes.

`cage.js`/`spawn.js`/`config/spawn-profiles.yaml` gain a "truly-everything" cage profile specifically for master seats (broad read access), while worker/peer seats explicitly refuse writes (`launch-profiles/profiles.js`, `cagespec.py`); `probe-master-cage.js` (160 new lines) pins the new profile.

## Why
D48/F-8: masters need broad visibility that worker seats must not have.

`fix-inventory.csv` D48; `redesign-plan/decisions.md#D49` — masters need broad visibility (to coordinate, mediate secret-add, review other seats' work) that worker seats must NOT have; the decision-review batch (system-problems-2026-08-21.md) approved widening the master cage while tightening the worker cage in the same commit.

## How to use & where wired
spawn.js selects the truly-everything profile for any seat classified as master.

`config/spawn-profiles.yaml`'s master profile now grants the wide "truly-everything" read scope; `spawn.js` selects it for any seat classified as master at launch.

## commit
92e7156c

## deployed
yes

## pin
server/spawn/probes/probe-master-cage.js (D48-annotated, scheduled)

## ATTENTION
- This master-wide cage was hardened FURTHER the next day by `stools-undeclared-tool-refusal` (D56/D74) and `ro-mask-private-scope-fix` (D53/#576) — read those two before assuming this commit is the cage's final shape.
- "Truly-everything" for masters is an intentionally wide grant — any future narrowing must not silently break secret-add mediation or the launch-identity corroboration (D43/D45), both of which assume a master can observe broadly.
- hardened further the next day by stools-undeclared-tool-refusal and ro-mask-private-scope-fix
- narrowing this grant must not break secret-add mediation or launch-identity corroboration
