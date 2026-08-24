# 20260824-c-persisted-supervisor-registry — Persisted supervisor registry + boot re-adopt

kind: creation
component: engine
date: 2026-08-24
commit: b7a174ca
deployed: no
pin: ignite/supervisor/registry.selftest.js
components: server,team-kit

## Motivation
Liveness had three disjoint answers (a tmux pane, the cgroup carrier, tick silence) and no
persisted record of what the daemon had spawned. A watchdog restart therefore came up with an
empty in-memory view, absence read as death, and the boot pass was free to stamp every live seat
`failed` at once — the mass-restamp hole (C-15 / F-adversarial-7). The redesign's cure is one
liveness surface that survives a restart, plus an ordering rule: re-adopt before any stamp.

## Design
A new component `ignite/supervisor/` — the home `spec-component-map` names, replacing
spec-supervisor's interim `ignite/engine/supervisor/`. Two product files, split by subject rather
than by size: `registry.js` (the record, its JSONL persistence, the liveness probe, the four write
moments) and `readopt.js` (the boot pass and its ordering guard). Rejected: reusing
`engine/attached-execution.js`'s `runnerAlive`/`processStartTime` — that is the LEGACY copy on the
attached-operator lane, and depending on it would point the dependency the wrong way, since the
operator lane consumes liveness and supervisor is where liveness is answered. Also rejected:
tombstone rows (a deleted row plus the ending store already carries the whole fact) and an
in-memory Map (the exact thing the incident was).

## How it works
`registry.jsonl` sits beside the module: JSONL, one line per live supervised sitting, carrying
`goal` + `seat` (the pair every ending-store API is keyed by), `pid`, `start_time`
(`/proc/<pid>/stat` field 22, read after the comm closing paren — index 19 of that split),
`launch_token` and a `supervised`/`unsupervised` flag. Written at exactly four moments:
`recordSpawn` right after spawn returns a pid, `recordCheckIn` when an outside-daemon seat checks
in (insert, or flip `unsupervised` → `supervised`), `dropRow` after an ending is stamped AND
confirm-and-reap succeeds, and boot re-adopt — which writes nothing. `isAliveProcess` is
`kill(pid, 0)` (EPERM counts as alive) + start-time match + not-a-zombie, and it is the ONLY
liveness answer. `readopt(file)` returns `{registryEmpty, rows, adopted, dead, skipped}` with no
side effect; only `dead` is eligible for evidence-stamping, and the stamping itself belongs to the
death-stamp path. `assertReadoptDone(result)` refuses a caller that never ran the pass.
`awaitingReap(hasEnding, file)` is the reap-debt surface: a row still present whose sitting already
carries an ending is a reap that did not complete. `cli.js --op NAME [--registry PATH]` is the
JSON door for team-kit's python, the same shape the ending store's `cli.js` settled on.

## Consequences
Nothing is rewired yet — this entry lands the module only. `engine/attached-execution.js`'s
`runnerAlive`/`processStartTime`, `coord.py`'s `live_panes` and `carrier_self_session`, and
`ticker.js`'s tick-silence knobs are still the legacy predicates; retiring them into this probe is
the doors seat's act. `attest-exit` / `close_session_seat` still stamp independently until the
death-stamp seat routes them here. team-kit's `load_awaiting` still answers `{}` — `awaitingReap`
is the successor surface it should be wired to, and until it is, `cmd_reap` finds no debt and the
G-134 pane-leak guard stays unguarded. `registry.jsonl` is runtime state and is gitignored at the
repo root (nested `.gitignore` files are ignored by this repo's own rule).

## Verification
`node ignite/supervisor/registry.selftest.js` — 8 cases, ALL PASS, exit 0. The two load-bearing
ones use real child processes: (b) a persisted live pid+start-time survives a simulated watchdog
restart (module cache cleared, file re-read) and lands in `adopted` with stamp-count 0, and the
same row classifies `dead` once the process really ends; (c) an absent AND an empty registry, with
three live processes running, both yield stamp-count == 0. Red-ability was measured, not assumed:
forcing the probe to answer dead reddens (b) with "expected 1 adopted row, got 0", and
reinstating the mass-restamp hole in `readopt` (synthesizing dead rows from `/proc` when the
registry is empty) reddens (c) alone with "stamp-count must be 0 on an absent registry, got 5".
Not deployed — worktree branch `ignite/core-redesign`, no daemon restart.

## ATTENTION
1. A ZOMBIE answers `kill(pid, 0)` and still carries its original start-time. A probe built on
   those two alone calls a finished seat alive forever, so it can never be stamped or reaped —
   `isAliveProcess` reads `/proc/<pid>/stat` field 3 and treats `Z` as dead.
2. An empty or absent `registry.jsonl` is a LEGAL fresh boot, never evidence of death. Any future
   reader that treats "no row" as "failed" reopens C-15 — the pass deliberately never enumerates
   the process table, so a live process with no row is invisible to it rather than doomed by it.
3. A torn or hand-mangled JSONL line is SKIPPED, not thrown on. A registry that refuses to load is
   a registry that re-adopts nothing, and re-adopting nothing IS the mass-restamp hole.
4. `dropRow` fires after the ending is stamped AND the reap succeeds — not after the stamp alone.
   Dropping on the stamp erases exactly the fact `awaitingReap` reports, and the reap debt would
   silently vanish again the way `awaiting-close.json` did.
5. `readopt` writes nothing on purpose. A pass that pruned dead rows before the death-stamp path
   ran would lose the debt on any crash between the two.
- empty registry is a fresh boot, never a mass death
