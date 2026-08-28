---
description: Read before asking whether a seat is alive, before stamping any ending from an observed exit, before reaping a finished sitting, or before reaching for a launch or remedial verb - the `supervise` CLI, the persisted registry, its boot re-adopt pass, and the one death-stamp path.
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

## The supervision CLI, and the six Python modules behind it

`supervise.py` is this component's front door — the daemon's and a leader's remedial surface over
a run, and the OTHER half of what used to be the single `coordinate` entry point. The owner split
that entry point by AUDIENCE on 2026-08-25: "one for the daemon or for leaders (if smth broken),
the other for all agents working on ignite (checkin, checkout, message, etc)". Seat-facing
coordination stayed at `coordinate` (`coord/coord.py`); nothing else moved and no verb's
behaviour, flags or output changed.

`supervise -h` is the command list. Sixteen verbs, in three groups: the launch composer
(`launch`, `session-open`, `descriptors`, `boot-prompt`), the readiness arithmetic (`ready-seats`,
plus the daemon-only `renewal-state` and `surface-refusal`), and the remedies (`close-seat`,
`reap`, `kill-pane`, `relaunch-pane`, `terminate-pid`, `approve`, the daemon-forked
`lifecycle-exec`, and the death stamp's `attest-exit` / `route-fail`).

⚠ AUDIENCE, NOT MODULE HOME. `rule-guard` is defined in `attest.py` here and is an AGENT command
on the other door: the seat named in the (seat, key) pair is the only writer of its own guard
value. The door table (`cli_main.py#SUPERVISION_COMMANDS`) is the one place that mapping is
spelled, and everything not in it is a `coordinate` command by default.

| Part | File | What it is |
|---|---|---|
| the CLI entry | `supervise.py` | The `supervise` front door. A thin door and nothing else: it imports the kit and dispatches into the same `main()` `coordinate` uses, telling it which door it is |
| process truth | `process.py` | ps snapshot, process identity, the live-process and live-harness predicates, exit verification, the pid reaper. Registry probe INPUT, never a second liveness surface |
| lifecycle remedies | `lifecycle_exec.py` | The lifecycle-inflight marker, the hidden `lifecycle-exec` verb, the bus alarm, the caller-side fork, the disposition sequences |
| readiness | `ready.py` | The ready-seat arithmetic, the derived `dead` state, the launch-admission predicate |
| the launch composer | `launch.py` | Seat discovery, descriptor validation, the boot prompt, harness command resolution, `session-open` |
| the death stamp | `attest.py` | The attest-exit arm and the session closer |
| the carrier bound | `carrier.py` | The asserted-identity launch bound — the paneless cgroup predicate that corroborates a `--as` claim |
| the door's written reference | `skills/supervise-a-seat/SKILL.md` | The leader-facing skill over this door — when to `accept`, when to `instruct`, and the close/relaunch/route acts. A `method=skill` `exposure.csv` row; the verb bodies for `accept`/`instruct` live in `coord/ruling.py`, which is where every `supervise` verb's body lives |

### How the seam works, and why it is shaped this way

These six are REAL Python modules: imported, never `exec`d. That was measured before they moved —
an AST walk over the kit's 17 product files found 1,506 cross-module references and exactly ONE
of them at module level. Every other reference is read inside a function body, so the module cycle
the two halves form resolves at CALL time and plain module-object imports are sound. There is no
shared layer to extract: the halves are mutually recursive, and these six need 192 distinct
agent-side names, so the structure is `supervisor/` depending on `coord` as a library and `coord`
naming the six back.

⚠ QUALIFY, NEVER COPY. Every name one of these takes from the kit is spelled `coord.NAME`, and
every name the kit takes from them is `<module>.NAME`. A `from coord import NAME` here would be a
SNAPSHOT taken at import: the selftest rebinds ~60 kit names at runtime, and a copied name leaves
every stub inert — measured 2026-08-24 as 913 ok under a copying bind against 1039 ok / PASS
through call-time lookup. `coord.py` also re-exports these modules' public names for callers
OUTSIDE the kit (`spec-component-map` §3); nothing in the kit may read one of those aliases, for
the same reason.

⚠ A module-level read of a peer's attribute would break the import cycle. Adding one is a measure,
not an edit.

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
| seeding | `supervisor/seeding.js` `seedGoal` / `launchOwed` | wrapped |
| reconcile | `supervisor/reconcile.js` `deriveOwed` / `launchSitting` | wrapped |
| `--rerun` | `coord/launch.py` `cmd_launch --rerun` / `--declare-only` | wrapped |
| attest-exit | `spawn.js` `closeSeatSessionRow` -> `attest-exit --force-dead` | wrapped (it BECAME the death stamp) |
| console-uncaged | bare console / uncaged `claude` (IE-3) | marked-unsupervised until check-in |
| `E_GOAL_NOT_LIVE` | `supervisor/seeding.js` `readLease` / `goalNotLive` (IE-1) | wrapped as a REFUSAL |

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
| `supervisor/seeding.js` `enqueueEligible` | ~10 s | whose `after` is satisfied and who has never fired | **retired as a computer** |
| `supervisor/reconcile.js` ledger classifier | ~300 s | class A (non-terminal ending), class B (unread mail) | **survivor**, relocated here |

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
| `store-dedup` | the store suppressed it (its own dedup) |

`launchThroughDoor` is the ONLY `heartStore.enqueue` on the owed path. It calls
`enqueue()` and reads its verdict. The admission brake that used to live inside
`enqueue()` is DELETED [spec-recovery §5, C-4 kill map] — it gated on a byte
comparison whose volatile fields reset it before it could bound anything, so the
bound is now the attempt counter, applied by each driver at the driver and never
at this door. `enqueued_by` is read off the door list by the caller and passed
through, so it can only ever be a value this component knows how to turn back
into a door name.

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
and `runtime/ticker/ticker.js` - all ask here now. The python side is
`coord/liveness.py`, one `node supervisor/probe.js` call per render.

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
side of that door is `coord/supervisor_door.py`; `SUPERVISOR_REGISTRY` overrides the
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

## Is this goal paused - two writers, and EITHER one holds

`lane-watch.js#laneIsPaused(goalFolder, heartStore)` is the ONE reader both pause
gates spend (`reconcile.js`'s gate and the lane pass itself); `goal_cli.py#lane_is_paused`
is its DEC-1 Python twin and the two change together. There are two WRITERS of
"this goal is paused" and they are different surfaces:

| writer | surface | who reaches it |
|---|---|---|
| `state-store#writeGoalWord` | the `goal_states` row | the owner's Slack `pause {goal}`, through the fifteenth gateway intent |
| `rbtv goal pause` (`operator/goals-tree/tool/goal_cli.py`) | the first token of `execution-lane` | the owner or an operator at the console |

**The gate is an OR: paused if EITHER says so.** a0d7e42c had converged it onto the
ROW (the row's existence decided, the marker a shim), which was right for its own
defect - a stale marker beating a row that had actually been updated - and wrong the
moment the Slack verb became reachable: NO goal on the instance carried a row, so the
first Slack verb would mint one that then overrode the console marker for good, and a
Slack `resume` would silently un-park every operator-parked goal (each leader waking
is a real, paid sitting). The frozen-goal case a0d7e42c was closing is answered where
it is now VISIBLE instead: `state-store/heart/pause-resume.js` REFUSES a resume that
meets a live console marker, names the marker, names `rbtv goal resume` as the lift,
and reports `applied: false`. Absent or unreadable is NOT paused, on both surfaces.

Retiring the lane-file writer collapses this back to one record and is OWNER-GATED.
Arm: `lane-skip.selftest.js` (all four combinations) and `reconcile.selftest.js`
(the PASS honouring it).

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

---

# Recovery - the attempt counter, its exit, and the relaunch budget

Law is `1-projects/build-ignite/redesign/specs/spec-recovery.md` sections 2, 4
and 5, under [T4-R3], [T1-R6], [T1-R8], [T4-R6], [T4-R10], [C-2], [C-4], [C-5],
[C-11], [CF-3], [D6], [D-2-ruling].

## What was deleted, and it was two things at once

| Deleted | Where it lived | Why it never worked |
|---|---|---|
| `strike()` / `stuckStands()` | `supervisor/reconcile.js` | counted only while the owed-set SIGNATURE stayed byte-identical; a drifting timestamp or session id read as PROGRESS and reset the count to 1 |
| `ADMISSION_BRAKE_LIMIT` (+ `BRAKE_REASON_FLOOR`, `hashArgsFloor`) | `state-store/heart/heart-store.js` `enqueue()` | the same comparison, a SECOND independent lock on the same table, with the same volatility |
| the end-of-pass counter sweep | `supervisor/reconcile.js` | cleared the count whenever the owed set changed - evidence-driven reset, which is the defect itself |

Both brakes went TOGETHER, and no byte- or fingerprint-reset path was kept
beside the replacement. That is the ruling, not a preference [C-4 kill map].

## The counter

`attempt-counters.js`. One counter per `(driver, subject, reason class)`.

- **Increments** on a same-reason RETRY: the driver's failure/refusal CLASS is
  unchanged AND this pass is a second attempt at work the counter already
  counted. Never an owed-content fingerprint - the key is refused outright if
  it carries an ISO timestamp, a uuid, a hex digest or a long id.
- **Does not increment** when the driver hands in `items` (the owed-item marker)
  and NONE of the items recorded at the last advance is still owed. That pass is
  a FIRST attempt at different work, not a retry. It does NOT reset - the count
  stands exactly where it was, and only a named re-arm event ever clears it. The
  marker rides the counter ROW (`owed_items`), never the key. A driver that
  hands in no items always counts, unchanged.
  ⚠ THIS IS NOT THE DELETED SWEEP. That one CLEARED the count whenever the owed
  set changed; this one declines to ADD to it when nothing it counted is left.
  An owed set that GROWS while its old rows stand still counts - `{a}` then
  `{a,b}` still reaches N, which is the [C-4] inversion, untouched.
- **Resets** on the closed list and nothing else: `code-deploy`,
  `config-change` (including a recognition-list edit), `owner-leader-act`,
  `resume`. A deploy or a config change clears every counter; an owner/leader
  act and a `resume` clear that lane's. Alarms never re-arm [T4-R10].
- **N** is `attempt_counter_n` from the recovery config file, passed in by the
  caller. There is no default in this module - a missing `n` is refused.

| driver | the loop it bounds |
|---|---|
| `ticker-deferred` | `ticker.js`'s DEFERRED re-fire: unknown tool, unknown workflow, an argv template that always refuses |
| `reconcile-respawn` | the `CADENCE_MS` wake / sitting re-spawn (leader wake, unread wake, room rebuild) |
| `reconcile-class-a-relaunch` | `deriveOwed` class A `incomplete` - the relaunch of a named seat |
| `alarm-refire` | any other unbounded alarm re-fire; the api impl-alarms counts through |

EXCLUDED, and mechanically so: `FROZEN_HOURLY_REPEAT` is a named driver this
module REFUSES [C-5]. The designed hourly frozen repeat is not an unbounded
retry, and counting it would stamp the alarm's own subject `incomplete:` after N
hours and cancel the alarm [T1-R15].

Storage is `attempt-counters.json` beside this file (override `countersFile`),
rewritten tmp-then-rename. Not a table in the ending store - spec-state-store
pins three record kinds there and a counter is not one of them.
`listCounters({goal})` is the read-only scope reader: the rows a re-arm is about
to delete, so the caller can report what it cleared and from what count.

## A leader HOLD is a row this pass honours [owner ruling 2026-08-28, decision 4(c)]

A `failed` ending becomes a `nonterm` owed row (`owed-from-endings.js`
`classifyEnding`) and this pass answers it by launching the LEADER, every cadence,
until the row is ruled. `supervise accept` and `supervise instruct` stop that
because both END the row. The leader's THIRD legitimate verdict — "I have read
this and it cannot be ruled until X happens" — used to be a message and nothing
else, and this pass reads rows, never mail: it counted each HOLD sitting as a
burned attempt, disarmed the lane at N=3, and the next code deploy re-armed the
counter and bought three more. Nine identical HOLD verdicts on
`goal-memory-management`, 2026-08-28, nine paid opus-5 sittings.

`supervise hold <seat> --until <change> --anchor "<evidence>" --go` writes a
`seat_holds` row into the ONE workspace ending store (`state-store/tables.sql`;
NOT a column on `seat_endings` — a `failed` row's CHECKs cannot carry it and a
re-stamp would archive it away with the ending it rules on). A seat under a LIVE
hold is excluded from class A entirely, the same shape `dead` and `summoned`
already have — so there is no launch target, and therefore no launch AND no
attempt counted, from ONE exclusion rather than two agreeing rules. The pass
NAMES what it excluded, on its own `reconcile: pass` line, as `heldExcluded`.

| `--until` | live while | released by |
|---|---|---|
| `new-ending` | the seat's ending still carries the `stamped_at` it had when the leader ruled | any re-stamp of that ending |
| `ask-answered:<ask-id>` | that `open_asks` row is still `open` | the answer, through `reapAndRelaunch` — §2.1's own mechanism, no second watcher |
| `release` | the row exists | `supervise release <seat> --go`, which deletes it |

Liveness is `state-store/predicates.js#seatHeld` and is evaluated on every pass,
so the hold clears ITSELF the moment the named change is observed — no sweep, no
writer, and the released row is worth exactly ONE leader sitting, not a fresh N.
Every unknown (an ask id that names no row, a word this build does not know)
answers NOT HELD: a broken hold can only let the daemon do what it did before
holds existed, where the opposite default is a lane stopped forever by a typo.

⚠ NEITHER IS `hold-anchor` RETURNING. That was a thirteenth column on
`sessions.csv` under the deleted grant-store authority model [T2-R12, T1-R9], and
both `HELD` and `hold-anchor` are refused at the ending store's own door. What
was killed was a SECOND work-state writer beside the ending store; this is a row
IN it, and it changes no ending.

## The re-arm, and who produces the four events

`exhaustion.js#rearmScope({store, goal, event})` - "this named event happened,
re-arm what it owns", returning the rows it cleared. Scope is the EVENT's, never
the caller's preference: `code-deploy` / `config-change` clear everything;
`resume` / `owner-leader-act` clear the named lane. It calls `consumeDisarmed`
per subject, so the ending half (`fireNamedEvent`) and the counter half
(`counters.rearm`) stay one act; `store` is OPTIONAL because nothing in the
deployed tree sets `engine.endingStore`, and a disarmed lane there exists ONLY
as a counter row.

Until 2026-08-27 the closed re-arm list had NO PRODUCER at all: `rearm` had one
caller (`consumeDisarmed`) and that caller had none, so a driver that reached N
was disarmed permanently - through every restart and every deploy (seven live
lanes). The producers now wired:

| event | producer | fires when |
|---|---|---|
| `code-deploy` | `runtime/code-deploy-rearm.js`, at boot | this boot's `ignite/` code digest differs from the one the last boot recorded on the marker (first boot with no record fires too) |
| `resume` | `state-store/heart/pause-resume.js`, the fifteenth gateway intent's executor | the owner types `resume {goal}` in Slack. WIRED in production since the owner direction of 2026-08-28: the bridge's door now SENDS the `pause-resume` intent and the daemon holds the ledger, so the port that was unwired for the process-boundary reason is gone rather than injected |
| `config-change` | none | there is no config-reload path to hook: `loadRecoveryConfig` is re-read at each use, with no watcher, no SIGHUP and no cache to invalidate, so there is no moment that IS the change |
| `owner-leader-act` | none | out of this seat's scope |

⚠ `code-deploy` NO LONGER CLEARS EVERY ROW, and the exception is that event's own
premise. It fires because THE CODE CHANGED, so the rows it may clear are the ones
whose failure the code could have caused — a crash, a launch refusal, a provider
error. A `reconcile-respawn` / `nonterm` row counts leader wakes over ANOTHER
seat's `failed` ENDING: a row written before this daemon booted, which new bytes
do not change and which a fourth wake is no likelier to resolve than the third.
That pair is `attempt-counters.js#DEPLOY_IMMUNE` and it SURVIVES a deploy with its
attempts intact (owner ruling 2026-08-28, decision 4(c); it narrows
`20260827-c-the-four-named-re-arm-events-g` ATTENTION 5). Every other class, every
other driver and every other event are unchanged — a lane-scoped `resume` or
`owner-leader-act` still clears whatever it names, because a person asking for a
lane back is a fact about the lane, never about the code. The boot pass journals
one `info` per row it did NOT clear, saying why: a lane that stays disarmed
through a deploy must be as audible as one that was re-armed.

## The exit at N

`exhaustion.js`. Two acts, and only two:

1. The lane is stamped `incomplete:` + `disarmed` through the ending api
   (`stampSystem`, diagnostic `attempt-counter exhaustion` - the store's own
   listed row, which supplies `armed: 0` and `named_event`). The words are the
   store's; this file invents none. The refusal TEXT rides on the ask record the
   `evidence_pointer` names, because the listed diagnostic is matched byte for
   byte and may not be decorated.
2. ONE signature-grouped ask RECORD per failure signature - `(driver, reason
   class)` - never one per lane [T1-R8, D-2-ruling]. Ten lanes failing the same
   way land as ten entries on ONE record. Options are the ladder's:
   `retry-with-change` / `drop-lane` / `pause-goal`.

The record is `{workspace}/.rbtv/runtime/ignite/asks/<ask-id>.json` plus one
`open_asks` row with `posted = 0`. **Zero Slack, zero outbox, not one byte** -
impl-slack reads the record and posts it.

`listOpenGroupedAsks(workspaceRoot)` is the read-only half of that record - one
row per file in the digest's own shape - and `runtime/internal-api/dispatch.js`'s
`inspect asks` merges it with the `open_asks` listing, which is what finally makes
this exit owner-VISIBLE [spec-recovery 5] instead of a file nothing rendered.

## The disarm is audible, ONCE

`reconcile.js#announceDisarm`. A disarmed lane is the strongest thing a pass can
do - every mechanical relaunch for that reason class stops until a named
external event - and `skip-disarmed` used to say NOTHING: no journal line, no
ask, no owner surface. On 2026-08-27 the `scratch-tool-reach-note` leader
disarmed at 17:11Z and four hours of passes printed only `reconcile: pass`.

The announcement is a journal `warn` carrying the counter row, the owed items
and the four re-arm events, plus a `recordGroupedAsk` on the SAME owner surface
the exhaustion exit writes - no new channel. It fires ONCE per (subject,
disarm); the once-marker is `disarm_announced_at` on the counter row, so a
restart does not re-announce and `rearm` deleting the row is what makes the next
disarm audible again. The exhaustion exit sets the marker itself, so the two
never both speak for one disarm.

⚠ A PASS WITH NO ENDING STORE ALSO ANNOUNCES. `reconcile.js` reads
`engine.endingStore`, which nothing in the deployed tree sets, so the exit at N
could neither stamp nor record and returned `exit: 'no-ending-store'` in
silence - five live counter rows sat at or past N with zero journal lines and no
`asks/` directory at all. That branch now announces the stop it cannot stamp.

`consumeDisarmed` is the other half of spec-recovery section 4 row 1: the
mechanical `resume {goal}` on a disarmed-counter lane re-arms the ending and
resets THAT counter. It spends no relaunch budget and rewrites no brief - there
is no budget call in it at all, and that absence IS the [C-11] guarantee.

## The relaunch budget and the leader handoff

`relaunch-budget.js`. The budget counts RECOVERY relaunches only - `kill`,
`crash`, `armed-incomplete` - off the ending row's own store-visible counters,
so it can never disagree with the row the scheduler reads.

| cap | key | trips on |
|---|---|---|
| failures | `relaunch_budget_failures` | `failure_strike_count` (the ending store advances it when a `failed` is stamped) |
| total | `relaunch_budget_total` | `recovery_relaunch_count` (advanced by `spendRecoveryRelaunch`) |

Each `failed` counts against BOTH. An ask-resume counts against NEITHER
[C-11] - `spendRecoveryRelaunch` refuses the cause `ask-resume` by name so it
cannot be routed through by accident. Budget and attempt-counter are
INDEPENDENT: whichever trips first takes its exit, and the other does not also
fire in the same act.

Exhaustion stops the lane and hands off to the leader ONCE [D6, T1-R8].
`leaderHandoff` assembles the payload and sets `leader_attempt_used` in the same
act, so a second handoff cannot be assembled at all. Every field is required and
a missing one is refused [T4-R6]: the seat's brief, BOTH sittings' progress
notes (read through the checkpoint contract), the kill reasons, the transcript
pointers.

Leader decides, daemon executes [CF-3, T2-R5, D7]. `executeLeaderInstruction`
performs one of exactly four, and refuses an instruction carrying the seat's own
work:

| instruction | the daemon act |
|---|---|
| `rewrite-brief` | write the new brief at its path, stamp the lane armed `incomplete` |
| `reassign` | stamp the judgment against the lane naming the seat design it goes to |
| `blocked-pending-plan-gap` | record the D13 scoped re-plan request, stamp the lane disarmed (`materialize-failed`, the store's listed plan-side row) |
| `escalate` | record a formed decision-ask - same grouped record, same no-post rule |

### How the ask goes out and how the answer comes back [B11, 2026-08-26]

Until 2026-08-26 neither half existed: `leaderHandoff` and
`executeLeaderInstruction` were exported and had NO production caller anywhere in
the repo, so this exit was never taken and the leader was never asked.

**The ask** is asked by `reconcile.js`. In the launch loop, a class-A
`incomplete` target (the recovery cause `armed-incomplete`) has its budget asked
FIRST - before the attempt counter, and that branch returns, which is what keeps
the two bounds independent. On exhaustion the pass assembles the handoff from
what it already reads (the seat's `seat.md` as the brief, its last two ended
session rows for the kill reasons and transcript pointers, `progress-note.md`
through the checkpoint contract) and wakes the LEADER through the door that
already puts a question in front of it - the D33(a) leader wake, boot prompt
first and `handoffPayloadText` appended after it. The exhausted seat is not
relaunched and its counter is not struck.

⚠ THE PROGRESS NOTE IS ONE FILE PER SEAT, not one per sitting. Only the latest
sitting's note can be on disk; the earlier one is reported absent WITH THAT
REASON rather than as a seat that wrote nothing.

**The answer** is a JSON file the leader writes and `drainLeaderInstructions`
applies - `.rbtv/runtime/ignite/leader-instructions/<goal>--<seat>.json`, beside
the ask records, the same shape `blocked-pending-plan-gap` already writes
`replan-requests/` in. A file and not a CLI verb because there is no ruling
instrument left to carry it: `rule-disposition` was deleted [T2-R12, T1-R9] and
nothing replaced it. The drain runs at the TOP of each reconcile pass (never on a
dry pass), applies each pending file through `executeLeaderInstruction` - the one
place an instruction is ever performed - and moves the file to `done/` or to
`refused/` with an `.outcome.json` beside it. A file that stayed would re-apply
the same judgment on every cadence.

**The spend** is `spendRecoveryRelaunch({cause: 'armed-incomplete'})`, called at
the moment a class-A relaunch actually reached the queue - never on intent.

## Counter / budget APIs

Counter: `countAttempt` · `peekCounter` · `rearm` · `keyOf` · `DRIVERS` ·
`DRIVER_LIST` · `RE_ARM` · `RE_ARM_EVENTS` · `FROZEN_HOURLY_REPEAT` ·
`AttemptCounterError` (`code: E_ATTEMPT_COUNTER`)

Exit: `exhaust` · `recordGroupedAsk` · `consumeDisarmed` · `signatureOf` ·
`askIdFor` · `askRecordPath` · `readAskRecord` · `ASK_OPTIONS` ·
`EXHAUSTION_DIAGNOSTIC`

Budget: `budgetState` · `spendRecoveryRelaunch` · `assembleHandoff` ·
`leaderHandoff` · `executeLeaderInstruction` · `handoffPayloadText` ·
`drainLeaderInstructions` · `leaderInstructionsDir` · `leaderInstructionPath` ·
`LEADER_INSTRUCTIONS_REL` · `RECOVERY_CAUSES` · `INSTRUCTIONS` ·
`RelaunchBudgetError` (`code: E_RELAUNCH_BUDGET`)

Proof that a new staff mail is not a retry and that a disarm is audible:
`probes/probe-leader-wake-counter.js` - 26 checks over the real `reconcileGoal`
on a throwaway workspace, including the live daemon's shape (a counter already
at N, no ending store) and two red mutation arms (strip the owed-item marker;
silence the announcement).

Selftests: `node --test attempt-counters.selftest.js` and
`node --test relaunch-budget.selftest.js` - exit 0.

---

# Recovery - the provider split, the reroute and the per-lane skip

[spec-recovery §3, T1-R13, T1-R17, T4-R4, CF-8, C-9, C-10]

## What was broken, and it was three things wearing one coat

Provider errors were not classified at all, so one error text drove opposite
wrong behaviours: a transient quota outage STRUCK the seat's counter and burned
it toward a dead end for something no seat did (inventory ST-10), and a
plan-declared bad slug got a silent no-strike dead end with the pin never
surfaced (ST-19). And underneath both, one bad lane froze the whole goal:
`lane-watch.js` `continue`d the entire goal when `uncastSeats` was non-empty, and
again for a registered-but-unbuilt row (ST-20).

## The per-lane skip [D16, C-9]

`uncastSeats` is a whole-goal COMPUTER and stays one - every door still asks it
the same question. What changed is its READERS. `lane-watch.js` now turns both
lists into a `seat -> reason` map and threads it into `seedGoal({ laneSkips })`;
`launchOwed` skips exactly those lanes, names each one at `warn`, and seeds every
sibling. The refusals are UNCHANGED - an uncast seat is still not launched, an
unbuilt row is still built and still not seeded that cadence. Only the blast
radius moved. The pass reports what it skipped as `laneSkipped` (the fifth
held-for-a-reason set), because a state an operator cannot see is a state that
costs a live investigation.

`reconcile.js#launchSitting` already read the list per-seat and is untouched.

## The two recognition lists - data, not code

| file | class | seeds |
|---|---|---|
| `provider-transient.json` | transient | tokens `quota`, `rate-limit`, `provider-down`; strings `429`, `rate_limit`, `overloaded`, `capacity`, `temporarily unavailable` |
| `provider-configuration.json` | configuration | tokens `model-not-found`, `bad slug`, `auth-rejected`; strings `404 model`, `unknown model`, `invalid_api_key`, `unauthorized` |

Match is case-insensitive SUBSTRING against the provider/cast error text. First
list that hits wins; both hit -> CONFIGURATION; UNRECOGNISED -> CONFIGURATION.
Fail closed, both times: a strike an owner can see beats a silent reroute that
hides a pin. Editing either file is a `config-change` named re-arm
[spec-recovery §5] - `listsFingerprint()` is the content-derived value the
config-change path compares across passes.

## What each class does

| | TRANSIENT | CONFIGURATION |
|---|---|---|
| strike | never | yes - the ordinary `failed` + strike through the attempt counter |
| reroute | ONE pass through the eligible alternates, per launch attempt | never |
| record | every reroute recorded on the seat | - |
| all alternates fail | provider backoff; kill clock paused; frozen suppressed [C-5] | - |

The one pass is mechanical, not a promise: `tried` accumulates inside the attempt
and only a backoff or a successful launch clears it, so a second pass cannot
happen inside one attempt.

## The shared routing table

`ignite/supervisor/models.csv` - moved out of `core/sub-agents/tool/` so it is
ONE file with two readers: `cast route` (`lib/route.js#CSV_LOCAL`) asks which
model runs a job of a given class, `routing-table.js#eligibleAlternates` asks
which models this lane may try instead. Two copies would be a daemon rerouting
onto a model `cast` cannot launch. Eligible = `mode=cli` and `use=route`, minus
the lane's own pin and anything already tried this attempt; table order is the
owner's ranking and nothing here re-ranks it.

## The override ruling [C-10, CP1 - RULED, final]

A per-seat model override SUPPRESSES reroute. First configuration fault on an
override is `failed` + strike, full stop. A transient fault on an override still
does not strike and still does not reroute - it goes straight to backoff, because
a pinned lane has no alternates by definition.

The pin is MEASURED off surfaces that already exist, not off a new declaration:
`seatModelOverride` compares the seat DESCRIPTOR's model (`seat.md`, what
`spawn.js#launchSpecForSeat` obeys) against its BINDING (`taskforce.csv`, what
`rbtv-bindings set` writes). Different -> somebody pinned that seat by hand, and
that pin is what the ruling protects. Absent on either side is not an override.

## The backoff ladder, and the numbers are the config file's

Initial `provider_backoff_initial_min`, times `provider_backoff_multiplier` per
consecutive all-alternates-failed pass, capped at `provider_backoff_cap_h`
[spec-recovery §2.1]. Never literals: `backoffMinutes` refuses a config missing
any of the three rather than picking 15.

## The readable facts [C-5] - expose only, never emit

Nothing here emits an alarm or posts anything. Two names are load-bearing and are
spelled to match their one consumer each:

| fact | read by |
|---|---|
| `provider_backoff_until` (ISO-8601) | `kill-clock.js#pauseState` - the no-progress clock's provider-backoff pause |
| `provider_backoff_waiting` | `observation/frozen.js#predicate` - the frozen exclusion |
| `reroute_pending` | `observation/frozen.js#predicate` - the same exclusion, mid-pass |

`laneFacts({goal, seat})` returns those plus `reroutes` (what this lane actually
ran), `backoff_streak` and `tried`. The monitor must not report healthy through a
provider outage [T1-R13], which is why these are readable rather than internal.

## Provider APIs

Classify: `classifyProviderError` · `readList` · `listsFingerprint` ·
`TRANSIENT` · `CONFIGURATION` · `CLASSES` · `TRANSIENT_LIST` ·
`CONFIGURATION_LIST` · `ProviderListError` (`code: E_PROVIDER_LIST`)

Lanes: `onLaunchFailure` · `onLaunchSucceeded` · `laneFacts` ·
`seatModelOverride` · `backoffMinutes` · `lanesPath` · `keyOf`

Table: `eligibleAlternates` · `readTable` · `tablePath` · `RoutingTableError`
(`code: E_ROUTING_TABLE`)

Selftests: `node --test provider-classify.selftest.js`,
`node --test provider-lanes.selftest.js` and (the per-lane skip, in the engine)
`node --test ../engine/lane-skip.selftest.js` - exit 0.

## What moved in with the component-first migration

`spec-component-map` §2 landed these here, with history, as part of impl-structure
(move-only; no symbol changed, no body split):

- from `engine/`: `reconcile.js`, `lane-watch.js`, `seeding.js`, `execution-record.js`,
  and the two ending-store readers they consume (`ending-reads.js`, `owed-from-endings.js`)
- from `supervisor/spawn/`: the whole spawn/fire path, now `spawn/`
- from `launch-profiles/`: the shared launch-spec resolver, now `launch-profiles/`
- from `config/`: `worker-session-settings.json`
- the probes that travel with those product files, now `probes/`

## The goal watcher is `reconcile.js`, not a job (D1/D15, 2026-08-20)

Goal-level health — non-terminal seat rows, unread staff mail, a dead or empty tmux room — is owned
by ONE per-goal reconciliation pass (`reconcile.js`, called from `lane-watch.js`, cadence 300 s, 3
mechanical attempts then a typed `stuck` to the leader). It is armed structurally: every goal the
watch pass sees is reconciled, with no per-goal job to register.

What that retired: the `selfheal-room*` jobs and their launch-spec entries, their job scripts and
both auto-arm call sites, plus every `goal-watcher*` catalogue row. `runtime/jobs/recover-room.py`
STAYS — reconcile shells it directly (`RECOVER_ROOM` in `reconcile.js`). `goal-watcher-job.py` was
left on disk dark and unreachable, and was DELETED on 2026-08-21 (owner ruling: *"if the program is
dead, delete it — there must be no dead code"*), together with its 12 dedicated probes.

⚠ The ticker's per-execution silence ladder (`stall_warn_ticks` / `stall_halt_ticks` /
`stall_kill_ticks`, and the hung-kill rung that read a process's log bytes/CPU time off it) is
DELETED [T4-R1, del-observers]: "is it alive" is answered by the supervisor registry, and
no-progress is measured off work-product (`last_progress_at`), never off ticks of silence.
Reconcile asks only the GOAL's ledgers.

## The leader chair fails CLOSED [B16, 2026-08-26]

`leaderSeat()` answers "which seat is this goal's leader" from `taskforce.csv`, which is the
register of who holds which chair. It used to return `seats[0]` when there was no `leader` row —
so an ordinary worker was printed as the chair on every pass, woken for judgment calls that are
not its to make, and named as the seat the tmux room is rebuilt under. Measured on
`goal-memory-management`, whose one row is the worker `distill-ignite-memory`. The `catch` arm was
worse: an UNREADABLE taskforce produced the literal name `leader`, a chair asserted from a file
nobody could read.

It now returns `{ seat: 'leader' }` or `{ seat: null, why, detail }` — never a substitute — with
`why` one of `no-leader-row` / `taskforce-unreadable`. Every consumer refuses rather than
substituting, and each refusal is a `warn` naming the goal and the reason:

| consumer | with no chair |
|---|---|
| the pass's `leader` field + `reconcile: pass` line | `null`, plus one `warn` per pass naming the reason |
| the class-A `nonterm` wake (rows only the leader may close) | nothing is woken; action `no-leader-chair`, the rows stand |
| the room rebuild (`recover-room.py --seat`) | the room is NOT rebuilt; action `room-refused`, error `no-leader-chair` |
| the B11 budget handoff | the payload is not handed anywhere; action `budget-exhausted-no-handoff` |

The warn fires on EVERY pass, deliberately: this is a staffing state only a `materialize` clears,
and the alternative was promoting a worker into the chair in silence. The BACKFILL that repairs it
already exists and is not this component's — `planning/materialize-seats.py` mints the missing
chairs on the next materialize that touches the goal.

## A daemon goal with no taskforce is named, never skipped in silence [B12, 2026-08-26]

`lane-watch.js` adopts a daemon-lane goal only when `taskforce.csv` exists. That skip used to
`continue` under a comment reading *"a normal state between `rbtv-goal scaffold` and `rbtv-goal
materialize`, not a fault. Quiet."* — wrong on both halves. It is not a transient: `taskforce.csv`
has exactly one writer in the system (`scaffold-seats`, reached only by the creation route), and
nothing the daemon runs is it, so the goal stands there forever. Measured on
`cli-tools-reachability-report` — zero daemon journal mentions over its whole life.

The pass now names the goal, the missing file, and the command that writes one (`scaffold-seats`,
NOT `rbtv goal materialize`, which refuses in exactly this state). It rides `shouldShout`, so it is
loud once per (goal, lane-marker text) and `debug` after — the same bound every other loud line in
that file has, and it re-arms the moment the marker changes or the goal seeds.

The CAUSE is fixed at the creation verb: `rbtv goal scaffold --lane daemon` now refuses unless the
creation route declares `--materialize-follows` (`operator/goals-tree/tool/README.md` § The daemon
lane). This line is the second half — the goals that reached this state before that gate existed
are named instead of vanishing.

## The daemon lane opens a goal's FIRST room [2026-08-27]

`seeding.js` refuses every launch on a goal whose tmux room is down (`deriveLease().live`, the D9
seed gate), and until now NO daemon-side path opened a FIRST one. `reconcile.js` REBUILDS a room,
but only when `deriveOwed` says work is owed — false by construction for a goal that never launched
a seat, since its `sessions.csv` does not exist. The boot cockpit opens only `rbtv-cockpit`. And
7.778 deleted `workflow_launcher.py`, the code that opened the room and launched the entry seat,
recording *"WHAT OPENS THE ENTRY SEAT NOW: the LANE"* without giving the lane an opener. Measured on
`scratch-cli-reach-report`: born through the creation-request route with a 7-row `taskforce.csv` and
7 seat folders, then journalled *"goal NOT seeded this pass … has NO live room … Start the room
(`rbtv run`)"* every 10 s, forever. That contradicts the lane's own contract
(`meta/master/references/master-scaffold-flow.md`: "the daemon picks the goal up by itself and runs
its seats unattended"; owner ruling OQ-22: "No queue — the lane advances the goal").

`lane-watch.js#openGoalRoom` closes it: immediately before `engine.seedGoal`, the pass opens the
room itself and seeds in the SAME cadence. It is placed HERE and not in `seeding.js` because
`seedGoal` is deliberately lane-agnostic ("a FUNCTION AND NOT A TRIGGER") and the attached lane and
the probes call it too.

By the call site the lane-shaped guards are already established — daemon-assigned (a `paused`
marker flattens to `console` and never reaches here), `taskforce.csv` present, no console run live.
The opener owes four more, and each is a state a room must NOT be opened in:

| guard | why |
|---|---|
| no launchable row (every seat unbuilt or uncast) | a room nothing can ever use |
| the lease is UNREADABLE | refused on ignorance, exactly as `seedGoal` refuses — "tmux is unreadable" is not "there is no room" |
| the room is LIVE | the idempotence: never a second room, whoever opened the first |
| the goal has `sessions.csv` rows | seats HAVE run here, so the room was closed after the fact (an owner closing it is the ordinary case). That is the OWED path's subject — `reconcile.js` rebuilds it under the leader chair — and re-opening from here would race it and re-open a room the owner deliberately closed |

The vector is `spawn/tmux.js#composeDetachedSession`, the ONE detached-session opener, shared with
the boot cockpit: `systemd-run --user --scope --collect --unit=rbtv-tmux-room-<uuid> -- tmux
new-session -d -s <goal> -c <goal folder> -P -F …`. NO command follows `-c`, so tmux starts the
default shell and the room's only pane cannot exit on its own; NO `-n`, so a room the daemon opened
is byte-indistinguishable from one a human opened with `tmux new-session -s <goal>`. The
`systemd-run --scope` wrapper is load-bearing and not decoration — an unwrapped `new-session` forks
the tmux SERVER into the daemon's own `KillMode=control-group` cgroup, and the next restart reaps
every pane on the box.

One `info` line, `room opened by the daemon lane (first seeding)`, fires once per room by
construction: the next pass sees a live room and returns `room-already-live`. Fail-soft like every
other act in the pass — a refusing tmux is one `warn` and a goal left for the next cadence.
`seeding.js`'s not-live refusal text now names WHO opens the room per lane instead of telling a
daemon-lane goal to run `rbtv run`.

Proof: `probes/probe-lane-room-open.js` — six goals on a PRIVATE tmux server, six red mutation arms.

## The pane cap does not measure the daemon lane [G-leader-0828-0524, 2026-08-28]

`launch.py`'s capacity term SKIPS the `cap.agent_panes` pane census (`<goal>/state.json`, whose
writer died with the team-monitor sensor) on a goal whose `execution-lane` reads `daemon` — naming
in one line why (this lane opens no pane) and which gates still bind it (the memory floor at
`coord.launch_gates`, both lanes; the daemon door's per-seat admission) — because a roomless goal
that has already run seats is neither countable nor cold-start and so deferred every counted seat
forever, stranding a leader's ruled `--rerun` of a crashed seat on `scratch-death-recovery-1-exec`;
the tmux lane is untouched (an absent census there still defers, in the same words), proof
`coord/coord_selftest.py` rows `E22-CAP-1/2/3`.

## A SUMMONED chair is never seeded (D24's seeding half, 2026-08-27)

`coord/identity.py#SUMMONED_SEATS` is the ONE list of chairs that exist only when the owner
summons them — today `("goal-master",)`. Its readiness half has held since D24 (`ready.py` answers
`verdict: IDLE`, "ON-DEMAND summoned seat — NOT OFFERED") and its owed half since the same ruling
(`reconcile.js` never derives class B for such a chair). The SEEDING half was missing, and the gap
cost a goal: on 2026-08-27 `scratch-cli-reach-report`'s `goal-master` row was enqueued at the first
seeding pass (15:27:01Z) with no owner message anywhere, and that cold sitting executed the goal's
own contract and fired `coordinate finish-goal`, tearing the room down with three of the five
planning seats never enqueued.

WHY coord's IDLE verdict never arrived. `ending-reads.js#readyFromEndings` builds the frontier from
the ENDING LEDGER and the `after` column and reads NO `verdict` field off coord's rows — it takes
only `seat`, `after` and `seed` from them. So `seedGoal`'s own "`ready` IS COORD'S ANSWER, HANDED
IN" note was true of the transport and false of the answer.

WHERE IT IS FIXED: `seeding.js#readySeats`, immediately after `readyFromEndings` — the ONE place
the launchable set is derived and the seam every consumer passes through (seeding's enqueue pass,
`reconcile.js`, the attached lane's status verb, the probes). The list is READ OFF COORD by the
`summonedSeats()` transport, which MOVED here from `reconcile.js` and is imported back by it: two
readers of one list is exactly the second source of truth D24's own note forbids. A failed read
yields the EMPTY set and logs — degradation is toward the old behaviour, never a silent hole.

This is a SEEDING exclusion, not an unreachability. The summon path does not read this frontier: an
owner message on the goal's channel reaches the chair through `chat/forward-path.js`, and an
explicit `launch --only goal-master` still admits by conjunction. One `info` line names it once per
(goal, chair) per process — `chair <seat> is SUMMONED — not seeded (launched per owner message)`.

Proof: `probes/probe-seed-gates.js` arms 8a–8e, with `leader` as the discriminating control (same
root row, same cast, same descriptor writer — only the name differs).

## The pass YIELDS between goals, and a pass never stacks [A-1 option (a), owner ruling 2026-08-28]

`runLaneWatch` is `async` and `await`s one `setImmediate` turn at the head of the per-goal loop.
Everything the loop then does per goal is blocking — `maybeReconcile` and `engine.seedGoal` spend
`execFileSync(python …)`, measured at ~2.4 s per seeded goal — and the daemon's gateway listener
(`runtime/gateway/gateway.js`) lives on that same single event loop. Before the yield the pass held
the loop for the whole sweep: with three seeded goals, a median 7.9 s and up to 12.6 s of every 10 s
cadence, so `inspect daemon` could not be answered at all and the watchdog's 10 s cutoff landed
inside that spread — 30 timeouts, 29 owner DMs, and never a dead daemon. A log line does not yield,
which is why the journal looked alive throughout.

**What the yield buys is availability, not speed.** The sweep costs exactly what it cost. What
changes is the WAIT a client on that loop pays: it was the whole sweep, and therefore grew with
every goal added to the tree; it is now a small fixed number of loop turns — measured at two to
three goal-blocks — no matter how many goals there are. That bound, not the ratio, is the point.

**One pass at a time.** The cadence callback (`runtime/index.js`) holds a `passInFlight` flag: a
tick that arrives while a pass is still running is DROPPED, never queued behind it, and named once
at `debug`. Without it an overrunning pass would be joined by the next one — two sweeps over one
tree, both seeding, both enqueueing. The order inside the cadence is unchanged and is load-bearing:
watch, then frozen, then tick — `frozenPass` reads the facts the pass just collected and the tick
dispatches what that same pass just enqueued, so both must observe a FINISHED pass. Before the pass
yielded that came free from statement order; now it is the `await`.

**The accepted cost, stated.** A gateway request can now land BETWEEN two goals, on a half-done
pass. The guard covers pass-vs-pass only; nothing serialises a pass against a request, and no lock
is added. Every write the loop makes is per-goal and idempotent on the next cadence, so a request
that observes a half-done pass sees a tree in which some goals have been seeded this cadence and
the rest have not — the same state it would have seen one cadence earlier for those goals.

**NOT covered:** `reconcile.js#recoverRoom` still holds the loop for a single `spawnSync` with a
120 000 ms timeout (observed at 66.6 s on 2026-08-27). That is one goal's single call, inside one
goal-block, and the yield does not shorten it.

Proof: `probes/probe-lane-watch-yield.js` — a 4-goal and an 8-goal synthetic sweep whose per-goal
work is a 300 ms synchronous block (no subprocess of any kind), a real HTTP client and server on the
same event loop, and the daemon's own cadence callback compiled verbatim from `runtime/index.js`.
Red arms: the `await` deleted (the client waits the whole sweep and is answered nothing inside it)
and the guard block deleted (two overlapping ticks start two passes).
