---
description: Read before asking whether a seat is alive, before stamping any ending from an observed exit, or before reaping a finished sitting - the persisted registry, its boot re-adopt pass, and the one death-stamp path.
---

# supervisor

The ONE liveness surface. Law is
`1-projects/build-ignite/redesign/specs/spec-supervisor.md` sections 1-2, under
[C-15], [T4-R7], [T4-R8], [T2-R8]; the folder home is `spec-component-map`'s
(this replaces that spec's interim `ignite/engine/supervisor/`).

"Is this seat alive?" is answered HERE and nowhere else. A tmux pane is a
viewport, a cgroup carrier is identity, a stored ledger status is history, and
tick silence is not liveness at all - none of the three legacy predicates is an
answer to this question. The registry is.

## What is persisted

`registry.jsonl` beside this file - JSONL, one live row per supervised sitting:

| Field | Meaning |
|---|---|
| `goal` + `seat` | The sitting this row supervises (the pair every ending-store API is keyed by) |
| `pid` | The OS process id spawn returned |
| `start_time` | `/proc/<pid>/stat` field 22, clock ticks since boot - what makes the pid survive recycling |
| `launch_token` | Daemon-minted identity at launch. Pane ancestry is not identity [T2-R8] |
| `supervision` | `supervised` or `unsupervised` - a seat born outside the daemon flips on check-in |

The file is runtime state, not source: it is gitignored, and its path is a
default a caller may override (probes, selftests and a second instance each
need their own).

## The four write moments, and there are no others

1. Immediately after spawn returns a pid - `recordSpawn`.
2. Check-in of an outside-daemon seat - `recordCheckIn` (insert, or flip
   `unsupervised` to `supervised`).
3. After an ending is stamped AND confirm-and-reap succeeds - `dropRow`.
4. Boot re-adopt - which writes nothing at all.

## Boot re-adopt, before any stamp

`readopt(file)` returns `{ registryEmpty, rows, adopted, dead, skipped }` and
has no side effect. Only `dead` is eligible for evidence-stamping, and the
stamping itself belongs to the death-stamp path, not here. Three rules the
incident report bought:

- An empty or absent registry is a legal fresh boot: `dead` is empty, so the
  stamp count is zero. Absence is not evidence of death.
- A live OS process with no row is not `failed`. This pass never enumerates the
  process table - it can only see rows it persisted.
- Nothing may stamp or launch owed work before this pass. `assertReadoptDone`
  refuses a caller that skipped it.

## Death truth - the one stamp path

`stampDeath(evidence, { store, registryFile })` is where an observed exit BECOMES an
ending, and it is the only such place [T4-R7, T1-R1, T1-R18]. Every door that used
to stamp on its own - `spawn.js#closeSeatSessionRow`, coord's `attest-exit
--force-dead`, and the boot pass over `readopt().dead` - now hands it the facts it
witnessed and stamps nothing itself.

| evidence | stamp / act |
|---|---|
| checkout `done` present | confirm-and-reap the process, EVERY seat, never only `ephemeral: yes`. No `failed` |
| checkout `incomplete` present | the seat-declared ending stands; reap |
| dead, no checkout, never checked in | `failed: crash` - a strike |
| dead, no checkout, DID check in | `failed: crash` + exit code + transcript-tail pointer |
| evidence is provider-shaped | `failed: provider-error` (the strike/reroute policy is spec-recovery's) |

`exited` is dead vocabulary and is not reachable from here by convention: the ending
store refuses it at the write boundary.

The reap half - `confirmAndReap` - CONFIRMS before it acts. The only question asked is
the registry probe; a live process is signalled, waited for within a bounded budget,
and only then is its row dropped. A process that survives keeps its row, because a row
dropped for something still running is a leak nobody can see afterwards.

The ending store is INJECTED (`store`), the same posture `awaitingReap` takes with
`hasEnding`: liveness and endings stay two files that one caller wires together.

## The reap-debt surface

`awaitingReap(hasEnding, file)` is the successor to team-kit's retired
`awaiting-close.json`: a row still present whose sitting already carries an
ending is, by write moment 3, a reap that has not completed. The ending lookup
is injected, so this component holds no ending-store handle.

## APIs

Probe: `isAliveProcess` · `isRowAlive` · `processStartTime` · `isZombie`

Death truth: `stampDeath` · `confirmAndReap` · `providerShaped` · `buildEvidence` ·
`waitGone`

Registry: `loadRegistry` · `saveRegistry` · `makeRecord` · `recordSpawn` ·
`recordCheckIn` · `dropRow` · `awaitingReap` · `registryPath`

Boot: `readopt` · `assertReadoptDone`

Kit door (for team-kit's python): `cli.js --op NAME [--registry PATH] [--db PATH]
[--payload JSON|PATH|-]`, one JSON document on stdout. `--db` is required by the ops
that need an ENDING - `stampDeath` and `awaitingReap` - and by no other. The python
side of that door is `team-kit/supervisor_door.py`; `SUPERVISOR_REGISTRY` overrides the
registry file for a probe, a selftest or a second instance.

Selftests: `node registry.selftest.js` and `node death-stamp.selftest.js` - each prints
`ALL PASS` / exits 0.
