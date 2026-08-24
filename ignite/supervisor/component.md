---
description: Read before asking whether a seat is alive, or before stamping any ending on boot - the persisted supervised-sitting registry and its boot re-adopt pass.
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

## The reap-debt surface

`awaitingReap(hasEnding, file)` is the successor to team-kit's retired
`awaiting-close.json`: a row still present whose sitting already carries an
ending is, by write moment 3, a reap that has not completed. The ending lookup
is injected, so this component holds no ending-store handle.

## APIs

Probe: `isAliveProcess` · `isRowAlive` · `processStartTime` · `isZombie`

Registry: `loadRegistry` · `saveRegistry` · `makeRecord` · `recordSpawn` ·
`recordCheckIn` · `dropRow` · `awaitingReap` · `registryPath`

Boot: `readopt` · `assertReadoptDone`

Kit door (for team-kit's python): `cli.js --op NAME [--registry PATH]
[--payload JSON|PATH|-]`, one JSON document on stdout.

Selftests: `node registry.selftest.js` - prints `ALL PASS` / exits 0.
