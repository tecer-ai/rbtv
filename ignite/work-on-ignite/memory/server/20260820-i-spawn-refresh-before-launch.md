# 20260820-i-spawn-refresh-before-launch — Spawn refresh before launch

kind: issue
component: server
date: 2026-08-20
commit: ee64adde,a06723ec
deployed: yes
pin: server/spawn/probes/probe-spawn-refresh.js (ARM A2, scheduled)
seeded: true

## Seen
spawnSeat() could launch a seat using stale descriptor/state data.

`spawn.js`'s `spawnSeat()` could launch a seat using stale descriptor/state data because it read before refreshing — same commit `ee64adde` as the `outputs-declared-at-gate` entry (D36/D37 shipped together).

## Missed
none recorded in sources.

## Held
spawnSeat() runs --refresh before its first read; extended to the headless door next day.

`ee64adde` adds `probe-spawn-refresh.js` and a first refresh call in spawn.js; `a06723ec` (next day, D37 follow-up) extends refresh-before-launch specifically to "the HEADLESS door — the one every live seat launch takes," making sure the refresh never blocks the actual launch call.

## commit
ee64adde,a06723ec

## files
ignite/server/spawn/spawn.js; ignite/server/spawn/probes/probe-spawn-refresh.js

## deployed
yes

## pin
server/spawn/probes/probe-spawn-refresh.js (ARM A2, scheduled)

## ATTENTION
- a06723ec's own commit message calls out the headless door as "the one every live seat launch takes" — any NEW launch door (see the `lane-aware-launch-doors` entry, which rewired --rerun/--declare-only/--reopen) must also route through this same refresh-before-launch behavior or it silently regresses.
- headless door is the one every live seat launch takes; new launch doors must route through this refresh too
