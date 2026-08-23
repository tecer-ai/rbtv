# 20260820-c-outputs-declared-at-gate — Outputs declared at gate

kind: creation
component: engine
date: 2026-08-20
commit: ee64adde
deployed: yes
pin: engine/probes/probe-outputs-resolver.js (OUTPROJ-3, scheduled)
components: team-kit
seeded: true

## What it is
Outputs declared where the gate reads them; a typed schema for non-file outputs.

`cage-admission.js` + `materialize-seats.py` + `coord.py` gain an outputs-declaration path (D36/D37, same commit): materialize-seats projects a seat's `Write:` grant paths directly into its descriptor's `## Outputs` section, and a typed schema covers non-file (chat) outputs. Companion in the same commit: `server/spawn/spawn.js` + `probe-spawn-refresh.js` implement "refresh-before-launch" (D37, detailed separately in the `spawn-refresh-before-launch` entry, filed under server).

## Why
D36: the gate reading declared outputs read a different source than where seats declared writes.

`fix-inventory.csv` D36 — the gate that verifies a seat's declared outputs exist was reading a different source of truth than where seats actually declared writes, so outputs review/planning tasks kept reading stale or absent declarations.

## How to use & where wired
materialize-seats.py writes Outputs directly from the seat's own cage grants.

`materialize-seats.py`'s descriptor-writing step now writes Outputs directly from the seat's own cage grants; `cage-admission.js` and `coord.py` read/consume the same field.

## commit
ee64adde

## deployed
yes

## pin
engine/probes/probe-outputs-resolver.js (OUTPROJ-3, scheduled)

## ATTENTION
- This landed in the SAME commit as `spawn-refresh-before-launch` (server) — easy to conflate; this entry is about WHAT gets written into a descriptor's Outputs section, the other is about WHEN spawn.js re-reads state before launching.
- A later ruling (D90, team-kit, "goal-root-relative-outputs") revisited output declaration grammar again — check that ruling before assuming this is the final output-declaration shape.
- same commit as spawn-refresh-before-launch; don't conflate WHAT vs WHEN
- D90 (team-kit) later revisited output declaration grammar again
