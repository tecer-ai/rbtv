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
| `last_progress_at` | The ONE work-product progress fact [T4-R1]. Stamped at spawn, advanced only by the collectors in `progress.js`; the no-progress kill and the frozen alarm read this and nothing else |

The file is runtime state, not source: it is gitignored, and its path is a
default a caller may override (probes, selftests and a second instance each
need their own).

## The write moments, and there are no others

1. Immediately after spawn returns a pid - `recordSpawn`.
2. Check-in of an outside-daemon seat - `recordCheckIn` (insert, or flip
   `unsupervised` to `supervised`).
3. After an ending is stamped AND confirm-and-reap succeeds - `dropRow`.
4. Boot re-adopt - which writes nothing at all.
5. A work-product progress signal fired - `recordProgress`, which advances
   `last_progress_at` on an existing row and touches nothing else. It never
   inserts a row: a signal for an unsupervised sitting answers `null`. Which
   signals may fire it is `progress.js`'s table, below.

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

## The door list - and every launch is on it [T4-R7, C-15]

`doors.js` carries spec-supervisor section 3 verbatim. A launch either flows
through the supervisor or is MARKED `unsupervised`; there is no silent arm.

| Door | Chokepoint | Disposition |
|---|---|---|
| seeding | `engine/seeding.js` `seedGoal` / `launchOwed` | wrapped |
| reconcile | `engine/reconcile.js` `deriveOwed` / `launchSitting` | wrapped |
| `--rerun` | `team-kit/launch.py` `cmd_launch --rerun` / `--declare-only` | wrapped |
| attest-exit | `spawn.js` `closeSeatSessionRow` -> `attest-exit --force-dead` | wrapped (it BECAME the death stamp) |
| console-uncaged | bare console / uncaged `claude` (IE-3) | marked-unsupervised until check-in |
| `E_GOAL_NOT_LIVE` | `engine/seeding.js` `readLease` / `goalNotLive` (IE-1) | wrapped as a REFUSAL |

The door NAME is derived from the identity a launch already carries - seeding's
and reconcile's `enqueued_by` on the queue row, `--rerun`'s own `leader-<door>-…`
reason token - so no call frame gained a parameter. A launcher the list does not
know still gets a row, flagged `unsupervised`: an ad hoc caller must be visible,
not refused and not invisible.

`refuseLaunch` is the `E_GOAL_NOT_LIVE` arm and asserts its three absences by
name: nothing spawned, nothing stamped, nothing enqueued. It is NOT a seat
`failed` - that class is envelope's `launch-refused`.

## One owed-work computer, and one enqueue [spec-supervisor §5, T4-R7, C-15]

Two functions used to answer "is this seat owed a launch?", and both of them
called `heartStore.enqueue`:

| Was | Cadence | Half it computed | Fate |
|---|---|---|---|
| `engine/seeding.js` `enqueueEligible` | ~10 s | whose `after` is satisfied and who has never fired | **retired as a computer** |
| `engine/reconcile.js` ledger classifier | ~300 s | class A (non-terminal ending), class B (unread mail) | **survivor**, relocated here |

They could disagree, and nothing could say which was right when they did: a seat
"not owed" by one and "owed" by the other simply behaved differently depending on
which cadence fired.

`owed.js` — `deriveOwed(goalFolder, opts)` is now the single "this seat is owed a
launch" function. It answers three classes from ONE call:

| Class | Means |
|---|---|
| A | the seat's last ending is non-terminal |
| B | a staff chair has unread mail |
| R | graph-derived launchability [T1-R3] — the half that used to live inside `enqueueEligible` |

Both cadences still exist and both still run: the watcher hands in the `ledger`
readers and reads A/B, seeding hands in the `graph` readers and reads R. **Two
callers of one computer is the design; two computers is the defect.** The readers
are injected rather than required because they live under `engine/` and a
top-level require in that direction would close a load cycle.

`deriveOwed` must never enqueue. An owed set is a STATEMENT, not an act — the
moment the computer can also launch, a second launch path exists by construction.

`launch-door.js` holds what seeding's retired computer left behind. Its five
gates are now refusals on the wrapped spawn, not a second owed set — a refusal
answers "this launch does not happen", never "this seat is not owed work", so the
seat stays owed and the next cadence asks again:

| Refusal `kind` | Fires when |
|---|---|
| `store-disagree` | coord ruled the seat READY and this store holds an unfinished execution row for it (the store may decline, never promote) |
| `hold` | the seat is human-interactive and detached to the foreground carrier |
| `cage-admit` | a declared output is inadmissible for a caged launch (§ D5) |
| `lane-reach` | the declared probe lane is not satisfied by the composed cage |
| `boot-prompt` | coord could not compose the seat's boot prompt |
| `store-dedup` / `braked` | the store suppressed it, or D52's fail-closed admission brake refused it |

`launchThroughDoor` is the ONLY `heartStore.enqueue` on the owed path. It calls
`enqueue()` and reads its verdict — it never replaces it, because D52's admission
brake lives inside `enqueue()` and is fail-closed by design. `enqueued_by` is read
off the door list by the caller and passed through, so it can only ever be a value
this component knows how to turn back into a door name.

`reconcile.selftest.js` holds the guard: `seeding.js`, `reconcile.js` and `owed.js`
must carry ZERO `.enqueue(` calls and `launch-door.js` exactly one, with a red arm
that re-adds a second path and proves the check fires.

## Asking whether a sitting is alive

`probe.js` — `probeSitting({goal, seat})` and `probeGoal(goal)`. The answer is
three-valued and that is load-bearing:

| `alive` | Means |
|---|---|
| `true` | a row exists and the pid+start-time pair still matches a live, non-zombie process |
| `false` | a row exists and the process is gone |
| `null` | NO row: the sitting is unsupervised. Never "probably running", never "dead" |

Collapsing `null` into `true` re-invents the pane; collapsing it into `false`
re-opens the mass-restamp hole. The seven legacy consumers - `coord.py`-lineage
`tmux.py`, `messages.py`, `cli_main.py`, `launch.py`, `carrier.py`, `checkout.py`
and `server/ticker/ticker.js` - all ask here now. The python side is
`team-kit/liveness.py`, one `node supervisor/probe.js` call per render.

## APIs

Probe: `isAliveProcess` · `isRowAlive` · `processStartTime` · `isZombie`

Death truth: `stampDeath` · `confirmAndReap` · `providerShaped` · `buildEvidence` ·
`waitGone`

Registry: `loadRegistry` · `saveRegistry` · `makeRecord` · `recordSpawn` ·
`recordCheckIn` · `dropRow` · `awaitingReap` · `registryPath`

Boot: `readopt` · `assertReadoptDone`

Owed work: `deriveOwed` · `seatState` · `deriveLaunchable`

Launch door: `admitLaunch` · `launchThroughDoor` · `storeDisagreeRefusal`

Doors: `DOORS` · `doorForLauncher` · `supervisionFor` · `superviseSpawn` ·
`markUnsupervised` · `registerCheckIn` · `refuseLaunch`

Probe: `probeSitting` · `probeGoal` (and `node probe.js --goal G [--seat S]`)

Kit door (for team-kit's python): `cli.js --op NAME [--registry PATH] [--db PATH]
[--payload JSON|PATH|-]`, one JSON document on stdout. `--db` is required by the ops
that need an ENDING - `stampDeath` and `awaitingReap` - and by no other. The python
side of that door is `team-kit/supervisor_door.py`; `SUPERVISOR_REGISTRY` overrides the
registry file for a probe, a selftest or a second instance.

Selftests: `node registry.selftest.js`, `node death-stamp.selftest.js` and
`node doors.selftest.js` - each prints
`ALL PASS` / exits 0.

---

# Recovery - progress, the kill clock, the config file, the checkpoint

Law is `1-projects/build-ignite/redesign/specs/spec-recovery.md` sections 1, 2.1
and 6, under [T4-R1], [T1-R19], [CF-1], [CF-2], [D4], [D15], [D-1-ruling],
[T1-R2], [T1-R11], [T4-R2], [F-simplicity-4]. Recovery policy lives in this
component, not a second folder (`spec-component-map` section 1).

## One progress fact, and a closed list of what advances it

`progress.js` is the only writer of `last_progress_at`. A signal is
`{goal, seat, kind, signal}`; `recordSignal` advances the fact iff the kind's
"advances" column carries that signal, and writes NOTHING otherwise.

| kind | advances | does not |
|---|---|---|
| `file-writing` (the default) | `file-write` · `progress-note` · `journal-append` · `tool-call-product` | `token-growth` · `transcript-growth` |
| `chat-only` | `message-sent` | `draft-unsent` · `mail-inbound` |
| `planning` (alias `orchestrator`) | `stage-artifact` · `progress-note` · `subagent-product-file` | `subagent-transcript` |
| `judge` | `verdict-write` · `progress-note` | `input-reread` |

A kind a plan does not name, or names in a word this build does not know,
resolves to `file-writing`. An unknown signal never advances anything.

ACCEPTED RISK, ruled [CF-1, T4 Reversals, T3-R13]: a seat that keeps emitting
listed signals is unkillable by the 30-minute clock, and planning waves that
emit product files stay "busy" indefinitely.

## The kill clock and its three pauses

`kill-clock.js`. The clock reads `last_progress_at` and nothing else - not
transcript growth, not the ledger fingerprint, not a pane. It pauses on exactly
three lane facts [T1-R19, D-1-ruling], and there is no fourth:

| lane fact | pause reason |
|---|---|
| `verified_open_ask` | `verified-open-ask` |
| `provider_backoff_until` (ISO-8601, still in the future) | `provider-backoff` |
| `disarmed` (until its `awaiting_event`) | `disarmed-incomplete` |

`provider_backoff_until` is produced by the provider-lanes work; until it is
written, that pause simply never fires. `disarmed` is spec-state-store's flag -
read here, never written here. A missing or unreadable progress fact never
kills: ignorance is not idleness.

## The recovery config file - the ONLY source of the numbers

`recovery-config.js` reads `{workspace}/.rbtv/config/ignite/recovery.json`
(spec-recovery 2.1). Eight keys, every one required, extra keys refused,
integers only, `0` or negative is a configuration-error. Missing, unreadable or
invalid means configuration-error and NO recovery clock is armed - there is no
in-code fallback, silent or otherwise. Boot and the config-change re-arm are the
same call (`armRecoveryClocks` is `loadRecoveryConfig`); nothing is cached.

The packaged seed is `recovery.defaults.json` beside this file. Seeding is
copy-if-absent: `seedRecoveryConfig(workspace)` writes the instance file only
when it does not exist, and an upgrade never overwrites owner tweaks. It is
deliberately NOT called by the loader - a loader that seeds on a miss can never
report a missing file.

This module is the ONE read api for the eight numbers. The counters/budget work
reads `attempt_counter_n` + both `relaunch_budget_*` keys, the provider-lanes
work reads the three `provider_backoff_*` keys, and the alarms work reads
`frozen_window_min` - all through `loadRecoveryConfig`, none by opening the file.
Seats never read it: `.rbtv/config/` is daemon admin.

## The checkpoint contract, operational

`checkpoint.js`. No checkpoint API, no transcript replay, no harness resume -
disk is the checkpoint [D4, T1-R2].

- **Progress note** `progress-note.md` in the seat folder: `done-so-far` /
  `next-step` / `open-questions`, all three on every write or the write is
  refused. A write advances the fact for the kinds that list `progress-note`.
- **Side-effect journal** `side-effect-journal.tsv`: one line
  `ISO-8601<TAB>kind<TAB>target<TAB>idempotency-key`, appended BEFORE the
  external act. A relaunch skips any act whose key is already journalled. An
  append advances the fact for file-writing seats.
- **Relaunch prompt** `relaunchPrompt({brief, seatDir})` = the original brief +
  the current note + the spec's verbatim continue-instruction.

## Recovery APIs

Config: `loadRecoveryConfig` · `armRecoveryClocks` · `seedRecoveryConfig` ·
`recoveryConfigPath` · `validateRecoveryConfig` · `RECOVERY_KEYS` ·
`RecoveryConfigError` (`code: E_RECOVERY_CONFIG`)

Progress: `recordSignal` · `progressOf` · `advances` · `isRefused` ·
`signalsFor` · `resolveKind` · `SIGNAL_TABLE` (registry side: `recordProgress` ·
`lastProgressAt`)

Kill clock: `killDecision` · `killDecisionFor` · `pauseState` · `PAUSE_REASONS`

Checkpoint: `writeProgressNote` · `readProgressNote` · `appendJournal` ·
`journalEntries` · `isJournaled` · `journalLine` · `relaunchPrompt` ·
`CONTINUE_INSTRUCTION`

Kit door ops (same `cli.js` surface): `seedRecoveryConfig` · `loadRecoveryConfig`
· `recordSignal` · `lastProgressAt`.

Selftests: `node progress.selftest.js`, `node kill-clock.selftest.js`,
`node recovery-config.selftest.js`, `node checkpoint.selftest.js` - each prints
`ALL PASS` / exits 0.
