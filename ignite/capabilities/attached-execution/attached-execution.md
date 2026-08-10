# attached-execution — the `rbtv run` verb

**Built for core-build task 7.44.** Owner ruling `decisions.md#d-attached-run-embedded-engine`:
**ONE implementation of workflow advancement, TWO attachments.**

The daemon attaches ignite's engine to a systemd unit behind a gateway. This capability attaches
**the same engine** — same heart store shape, same queue, same tick algorithm, same fire path — to
the calling terminal, and it dies with that terminal.

| | daemon lane | attached lane |
|---|---|---|
| entry | `rbtv ignite daemon start` | `rbtv run <goal-folder> --profile <name>` |
| store | `{state_root}/heart.db` | `<goal-folder>/heart.db` |
| lifetime | outlives the terminal | dies with it |
| recovery | `goal-watcher-job` | **the owner re-runs the verb** — no watcher, ruled |
| engine | `ignite/engine/` | `ignite/engine/` — the same one |

## Entry point

`tool/rbtv-execution` — reached as `rbtv run`. It owns argv, output and exit codes and NO advancement
logic. Exit codes: `0` complete (or the tick bound was reached) · `1` refused, or the run cannot
advance — a blocked dependency chain, or a seat that failed (`seat-failed`) · `3` **a worker asked a
question and the run handed it back**. The third is distinct on purpose: a run that stopped to ask is
neither a success nor a failure, and a caller must be able to tell without parsing prose.

⚠ **A run that cannot advance RETURNS.** Nothing live, nothing queued, and a seat that already ran
without finishing is a state no further tick can change — the loop used to spin on it every cadence
forever. It now returns `seat-failed` and names the seat.

## Orientation — `rbtv run <goal-folder> --status`

**Console-run wave A, item A3.** The same entry point, asked to REPORT instead of run: it prints
`done` / in-flight / `ready (next)` / waiting for the goal's seats, plus any seat **held for you**,
and exits `0`. Read-only, no `--profile`, **no daemon**, and it works before the goal has ever run.

Everything it prints is DERIVED — console-run design ruling 2: no engine breadcrumb, no
session-maintained doc, nothing written in order to be read back later. Sources: the goal's
`taskforce.csv`, the goal's **execution record** (`executions.csv` — the completion authority both
lanes write, § below), its own `heart.db` *if one exists*, the seat descriptors, and the
`execution-mode` file. ⚠ The record is not an exception to ruling 2 and it is worth saying why: it is
not orientation state maintained for a reader's benefit, it is the OUTCOME of each execution written
by the lane that witnessed it — the same class of artifact as `sessions.csv`. Ruling 2 bars a second
copy of what the run can compute; the record carries what a single lane's store cannot know.

- **It never creates the store.** Opening a heart store creates and migrates it, so a status call
  before the first run would leave a `heart.db` behind and make *"has this goal ever run?"*
  unanswerable from disk. The file is opened only when it is already there.
- **It shares the engine's ONE eligibility predicate** (`seatState`) with the enqueue pass. A
  second copy of the wave math is a status surface that can disagree with the engine it reports on.
- **Held-for-user is TWO gates**, the D14 pair the console-run design's ruling 5 names: the seat
  declares `human-interactive:` in its descriptor AND the goal's `execution-mode` reads
  `interactive` (absent = `autonomous`, the ratified default). Both readers are the chat bridge's
  own (`bridges/chat/bus-ferry.js`), so this surface and the gate that actually parks an
  owner-addressed message cannot drift apart.
- **Only UNANSWERED questions are listed** — and since console-run B1 the RUN LOOP uses the same
  correlation. It previously filtered asks against a per-loop `seenAskIds` set that nothing ever
  added to, so the first ask a goal ever recorded ended every later run at its first tick, on a
  question that may well have been answered while the run was down.
- **The same listing rule, stated once:** Asks and answers correlate by `thread` and nothing
  marks the ask row itself, so answered ones are paired off greedily in `msg_id` order — two asks
  and one answer on a thread leaves the second still listed, because hiding an open question is
  the one direction this surface must never err in.
- **An INTERRUPTED seat is named as one.** A foreground row still `launching` belongs to a runner
  that is gone, and the shared predicate correctly calls it `live` — which reads to an operator as
  *"something is working on it"* when nothing is. The verb reports `interrupted` alongside the state
  rather than instead of it: `seatState` stays the engine's one copy of the wave math, and the next
  run's reconciliation is what actually resolves the row.
- Refusals are distinct: a path that is not a goal folder names the goal-folder shape; a goal with
  no `taskforce.csv` names the missing file.

Guarded by `ignite/engine/probes/probe-attached-status.js` (both gates measured with the other held
open; the read-only claim measured as a before/after directory listing; both arms proven red by
mutation).

## The foreground carrier — a seat that runs in YOUR terminal

**Console-run wave B, item B1** (design ruling 1). The engine stays the **only** DAG-advancer. What
changes for one class of seat is the **carriage**, and nothing else.

**Which seat: two gates, both of them** (ruling 5 / D14) — the seat declares `human-interactive:` in
its `seat.md` frontmatter AND the goal's `execution-mode` reads `interactive`. Both readers are the
chat bridge's own (`bridges/chat/bus-ferry.js`), the same ones the `--status` verb reports from.

**What happens:** instead of a detached caged child, the engine launches that seat's harness session
as a **foreground child of the runner**, sharing this terminal (`stdio: inherit`). The tick loop
BLOCKS while it runs — nothing else in the run advances. When the session ends, its turn is closed
and the next pass releases the seats that were waiting on it. There is no hold state and no release:
the carrier is a spawn variant.

| | detached seat | foreground seat |
|---|---|---|
| carriage | `systemd-run`/`setsid`, bwrap cage | a foreground child of `rbtv run` |
| command | the profile's `exec:` template | the profile's **`headed.tui:`** template |
| `jobs_log.enqueued_by` | `attached-execution` | **`attached-foreground`** |
| `jobs_log.session_mode` | `headless` | `headed` |
| turn ends on | the carrier's exit marker, swept by the ticker | the child's exit code, in the same pass |

- **The command is the profile's `headed.tui` block, never a filtered `exec:`.** `exec:` is the
  headless template (`-p --output-format stream-json`); composing an interactive command out of it
  would be the second interpreter of the one config `DEC-1` § Shared profile source forbids. A
  profile with no `headed.tui` **refuses**, naming the seat and the profile — the headed block IS the
  declaration that a profile can carry a human (D17). `seat.md` still rides the system prompt through
  the one composer (`--append-system-prompt-file`, claude-only and conditional on the file existing).
- **`headed.tui` pins the profile's model** (owner ruling `decisions.md#d-s21-headed-tui-pins-model`,
  closing S-21). It did not: `argv: ["claude"]` bound the harness and left the model to the harness
  default, so `claude-opus` meant opus detached and *whatever claude defaults to* in a terminal. All
  11 shipped profiles with a headed block now carry the same flag and the same value their detached
  templates do (`--model <m>` for claude, `-m <provider/model>` for opencode — a ROOT option there,
  so it applies to the bare TUI command and not only to `run`). **This changes the daemon-headed lane
  too** (tmux-pane seats), ruled knowingly. `codex` and `kimi` declare no `headed:` block at all, so
  no profile is left inconsistent with its detached half.
- ⚠ **No cage.** A session sharing the owner's terminal has neither bwrap nor a systemd slice —
  the accepted bound of the console-run design (§ Cautions), the same one d1's hand-run elicitator
  had. The detached seats of the same run are caged exactly as before.
- ⚠ **THE TICKER IS FROZEN while a foreground seat runs.** The loop blocks in the carrier, so no
  tick happens: the crash sweep, the stall ladder and the exit sweep are all suspended, and the
  run's DETACHED siblings are unsupervised for the whole time a human sits in the seat. A sibling
  that dies — including one systemd kills at its profile's `runtime_max` — is not observed until the
  seat's session ends. Accepted for v1 (the alternative is a second thread of advancement, which is
  what the one-engine ruling forbids); disclosed because nothing else would tell you.
- ⚠ **The goal's execution mode is read ONCE, at boot.** Flipping `execution-mode` mid-run does not
  affect the run in flight. `--status` reads it LIVE, so the two can disagree while a run is up:
  after an `autonomous` → `interactive` flip, `--status` calls a seat held that the running engine
  will detach. Stop the run and re-run it to change the answer.
- **It needs a real tty**, so `rbtv run` on a goal with held seats cannot be a skill session's Bash
  call. The entry skill hands the user the command to type.
- **A foreground seat writes the goal's `sessions.csv` row, like any other launch** (owner ruling
  `decisions.md#d-s20-foreground-seat-writes-session-row`, closing S-20). It did not — that row was
  written only by the daemon spawn path this carriage deliberately does not go through — so a package
  whose seats were ALL carried in the terminal was traceless, and the edge-runner's check-out fast
  path refuses a traceless package wholesale. That case is now gone rather than carved out.

  | | daemon at-dispatch row | foreground row |
  |---|---|---|
  | writer | `spawn.js` (task 7.75) | `attached-execution.js` — same schema, same moment (before the child starts), same key |
  | `session-id` | the launch's, joining its `jobs_log` row | **the same**: the join (task 7.73) is what marks it foreground — its execution carries `enqueued_by = attached-foreground` |
  | `pid` / `pid-starttime` | the worker process's | **the runner's** — `coord.py pane_identity`'s rule: every process the seat runs is a descendant of `rbtv run`, and the identity gate matches against the caller's ANCESTRY. (`spawnSync` yields the child's pid only once it is dead, so there is no other honest choice.) |
  | `tty` | always empty | the runner's numeric `tty_nr` — non-zero exactly when the run has a real terminal, which is the human-readable mark of a terminal-carried row |
  | `ended` / `disposition` | `coord.py session_close`, called by the seat | **the carrier**, on the child's exit — see below |

  ⚠ **The identity pair is LANE-identifying, not SEAT-discriminating** (review finding). Every
  foreground row of a run carries the SAME pid/starttime — the runner's — because that is what is
  true: each seat genuinely runs as a child of `rbtv run`, one at a time, on one terminal. A process
  matched against these rows therefore matches EVERY foreground seat of that run, not the one it is
  sitting in. Nothing is broken by this today, and the reason is not this row: a console-lane seat
  never reaches the identity gate at all — `checkIdentity` refuses it `E_GOAL_NOT_LIVE`, there being
  no tmux room on this lane. **So the gate's protection here is the no-room refusal, not the pair.**
  If a future change gives the console lane a room, the pair must become seat-discriminating FIRST
  (the child's pid is only knowable after it dies, so that needs a different carriage, not a
  different column). Flagged for the ledger.

  The header is **not spelled in the engine**: `coord.py` owns `SESSIONS_COLS` and is asked for it, at
  run time, only when the append has already refused for want of one — the same contract `spawn.js`
  follows, so an all-foreground package's trace is born with the owner's header. A failure to record
  is **loud and never fatal**: the seat is about to own the terminal, and refusing a launch over its
  trace would be the worse outcome. (`appendRowEnsuringHeader` is not exported from `spawn.js`, so
  the ~10 lines of *mechanism* exist twice while the *schema* still has one owner — flagged.)

- **…and the carrier CLOSES that row on the child's exit** (review finding). A row is normally closed
  by `coord.py session_close`, which a console-lane seat can never reach (`E_GOAL_NOT_LIVE` — no tmux
  room), so an opened-and-never-closed row made `goal-state-job`'s `open_session_seats` — *rows whose
  `ended` is empty* — report every **finished** foreground seat as a live-or-crashed sitting for the
  rest of the goal's life. A new false divergence signal, created by the row itself. The carrier is
  the one honest witness (it blocks on the child), so on exit it stamps:

  | cell | value | why that one |
  |---|---|---|
  | `ended` | the exit timestamp | this is what closes the sitting |
  | `disposition` | **`exited`** | `coord.py` reserves it for *"the kit attesting that a harness terminated, a fact a seat cannot witness about itself"*. **Never `done`** — `done` is a seat reporting its own work finished, which no exit code asserts. Every reader treats `exited` as NOT-done (edge-runner: `renew`/`revive`/`exited` do not advance the fast path), so nothing advances on an attestation nobody made. |
  | `disposition-writer` | `kit` | the pair the value is validated against |

  The exit CODE is not invented into a column: it is on the `jobs_log` row this session id joins to.
  It closes **only its own open row** (matched by session id, skipped if `ended` is already set), so a
  seat that did reach `coord`'s closer keeps that closer's values. Measured after a clean
  all-foreground run: `open_session_seats` → empty (was: both seats, forever) and
  `coord.session_disposition` → `exited` (was: `None`). **Consequence, stated rather than found
  later:** the check-out fast path can now *answer* for a console-lane seat, and its answer is
  NOT-done — truthfully, since no seat on this lane can declare its own check-out. The console lane
  does not need it to: the attached engine advances from its own `heart.db`. The two surfaces
  therefore disagree by construction on a console-run goal (engine: `done`; trace: `exited`), and
  that is the honest state of affairs rather than a defect to paper over. Flagged for the ledger.
  ⚠ The close is a read-modify-write of the whole file with no lock (`coord.py`'s `coord_lock` has no
  JS binding, and the daemon's own append door takes none either); the window is one read/write pair
  while the ticker is frozen.

### Crash semantics — the contract, stated explicitly

A foreground seat killed mid-work leaves an execution row nobody ended, because the process that
would have ended it died with the child. This is what happens, and none of it is a retry:

| Event | What the run does |
|---|---|
| the seat's session exits **0** | turn `done`, session `closed` — the same exit-code rule the ticker's sweep applies to every other seat. The DAG advances on the next pass. |
| the session exits **non-zero** | turn `failed`, session `crashed`. The run does not advance past the seat: it returns `seat-failed`, exit **1**, naming it. |
| the seat **asked a question** and its session exited non-zero | both are true and both are reported: the run returns `question` / exit **3** (an unanswered ask is checked first), and the seat's row is already `failed` / `crashed`. Resuming therefore needs `--relaunch <seat>` as well as an answer. |
| **Ctrl-C / SIGKILL / a closed terminal** mid-seat | the row is left non-terminal. At the **next run's boot**, before the first pass, `reconcileForegroundOrphans` ends every non-terminal `attached-foreground` row as `failed` / `crashed` — a foreground child cannot outlive the terminal it was attached to, so this is an observation, not a guess. The run then behaves as the row above: it refuses, naming the seat. |

**It NEVER blindly re-enqueues.** Seeding is create-only, and re-firing a seat because its row looks
unfinished is exactly the false-relaunch that rule exists to prevent. Running it again is an explicit
human act:

**`--relaunch <seat>` (repeatable) — a one-shot grant.** It presents that seat to the eligibility
predicate *without its execution history*, so a dead seat reads `ready` again. Three bounds:
nothing in the store is rewritten (the failed attempt stays on record); a seat that **finished** is
never re-opened by a grant; and the grant is **spent at the launch**, so one invocation gives one
attempt. There is no grant file and no new state — PRIN-11: the act is the typed flag.

⚠ Killing the runner's **pid alone** (rather than signalling the process group, which is what Ctrl-C
and a closed terminal do) leaves the foreground child running with no parent. The reconciliation
still ends the row; the orphaned process is not reaped, because this carriage has no cage to reap it
with.

### One runner per goal — enforced, not assumed

Everything above rests on one attached run owning a goal at a time. Nothing enforced it: the store's
`E_SECOND_WRITER` guard is an in-PROCESS singleton, and a second process opens the same sqlite file
happily. **Measured harm** (wave-B review): runner B read runner A's LIVE foreground row, applied the
reconciliation's premise — *a non-terminal foreground row means its runner is gone*, true for one
runner and no more — ended A's row, exited `seat-failed`, and told the operator to
`--relaunch alpha`, which would start a **second session for a seat a human was working in**. A's own
turn-end then silently rewrote B's row. Loud in neither direction.

So the premise is now a precondition. `rbtv run` takes `<goal>/.attached-run.lock` — created
`O_EXCL` (the atomicity is the filesystem's), carrying the runner's pid and its process **start
time**, released on the normal path and on a signal, and only ever released if it is still ours.

- **A live holder REFUSES the second runner, loudly, naming the pid.** It does not reconcile, does
  not open the store, and changes nothing.
- **A stale lock clears itself.** `kill(pid, 0)` plus the start time answers "is that runner still
  there"; the start time is what stops a RECYCLED pid from bricking a goal forever. A crashed runner
  never needs manual cleanup — which is what keeps this inside PRIN-11's spirit: the file is a
  liveness interlock that cannot survive the process it names, not state anything reads to decide.
- **`--status` never takes it.** Orientation stays read-only and works beside a live run.
- **Belt and braces:** if a foreign writer ever ends a foreground row anyway, the carrier REFUSES to
  overwrite the terminal row and says so, rather than replacing another writer's outcome silently.

## The goal's execution record — ONE place answers "did this seat finish"

**Owner ruling `decisions.md#d-s23-single-execution-record-now`** (pulling forward the Phase-6 task
filed by `#d-s18-cross-lane-refusal`, and closing the `done`-vs-`exited` question S-23).

**The term is MINTED.** `execution record` is now a registry concept —
`system-definition/concepts/execution-record.md`, settled by
`system-definition/decisions.md#d-execution-record` (owner ruling
`#d-execution-record-name`, 2026-08-10). The words below are that term, not this document's
coinage: use it as spelled, and take the definition, membership test and differentiation from
the record (`sd-graph show 'execution record'`) rather than restating them here.

`<goal-folder>/executions.csv` is the goal's **execution record**: one row per seat execution, opened
at dispatch and closed with its outcome, written by **every lane that runs the goal's seats** and read
by **every lane before it seeds**. A seat finished in one lane is not re-run by the other.

| column | what it carries |
|---|---|
| `seat` | the taskforce seat — the CROSS-LANE identity. Never a job id: `seat-<name>` is unique in a per-goal store and is not unique in the daemon's, which holds every goal at once. |
| `session-id` | the join key back to both operational surfaces (`jobs_log.session_id`, `sessions.csv`). It makes the record a POINTER to the evidence, and makes an append idempotent. |
| `lane` | `attached` \| `daemon` — **derived** from where the writing store sits (CMP-2 § Two store kinds), never declared by a caller. |
| `started` / `ended` | from the execution; an empty `ended` means the row is still open. |
| `outcome` | the store's OWN turn vocabulary, `done` \| `blocked` \| `failed` \| `killed` — no new words. `done` is the only value that stops another lane re-running the seat. |

**What question it answers, stated narrowly (review F5).** The record answers **completion for
SCHEDULING**: *may this seat be dispatched again, by any lane?* It is the single authority for THAT
question and every scheduling reader asks it. It is deliberately **not** the only completion-shaped
surface in the system, and the coexistence is stated rather than glossed:

| surface | question it answers | owner |
|---|---|---|
| `executions.csv` (this file) | may this seat be dispatched again — engine OUTCOME | the engine, both lanes |
| `sessions.csv` `disposition` | did this session's process end, and how | `coord.py` / the kit |
| coord's check-out attestation (`goal-state-job`) | did the SEAT attest its work done | `coord.py`, the seat itself |

`goal-state-job` reads the attestation and knows nothing of this file, and that is correct: an engine
`done` (the process finished cleanly) and a seat's attested `done` (the human-or-agent says the work is
finished) are different facts, and its own fixture contains cases where they rightly disagree. Nothing
here maps one onto the other.

**Why this is not a mirror of two stores (`PRIN-11`).** The two `heart.db` files stay each lane's
operational store — queue, turns, messages, liveness. Exactly one question moves here, and it moves
whole. A lane's own store is still consulted by that lane as its local no-double-fire guard
(create-only seeding is unchanged), which can only ADD done-ness — so the union can never cause a
double run, only decline to re-run something a lane already ran.

**Where `sessions.csv` stands, unchanged.** The trace stays **launch/lifecycle accounting**: one row
per launched session, closed by whoever witnessed the termination — a fact about a PROCESS, which is
why a foreground row closes `exited`/`kit` and never `done`. The record carries the **outcome** — a
fact about the WORK. That is the S-23 divergence dissolving: two surfaces, two questions, one answer
each, and neither overloaded into the other.

**Who writes it, and when.**

- **At the tick**, for every seat execution in the writing store — `engine.tick()` in
  `engine/index.js` calls `publishToRecord`. The publish sits at the ONE thing both lanes call, so no
  hook is needed in the completion path, the crash sweep, the kill path or the spawn door: whatever
  ended a seat's turn, the next tick sees the terminal row and publishes it.
  ⚠ **`engine.tick()` — not `ticker.tick()`.** The daemon's loop (`server/index.js`) calls the engine
  façade for exactly this reason. It called the raw ticker in the first version of this build, which
  meant the daemon lane published NOTHING and a daemon-run seat stayed invisible to the record —
  caught in review. A probe arm now asserts the daemon loop's call site, alongside the behavioural one.
  Accepted bound: **a lag of one tick** between a completion and the shared record. A record write that
  fails is logged and never fatal.
- **At the dispatching act**, for a foreground seat, because that call BLOCKS for as long as the human
  works and the publish would not come round again until the seat is over.
- **There is no separate boot "adoption" call, deliberately.** One stood here and was deleted: every
  path through the run ticks, the tick publishes, and within a lane the store's own rows already govern
  seeding — so removing that call changed nothing any arm could detect. What the run guarantees is
  stated instead: after any run, the goal's record carries this store's outcomes. A goal that ran
  before this record existed is carried in by its next run, one tick in.

**Who reads it, and what it stops.** `seatState` (the ONE eligibility predicate — so the enqueue pass,
the foreground carrier and `--status` all inherit it), `evaluateExit`, and `engine.seedGoal`.
`--status` reads it **without opening any store**, so it reports a seat the daemon finished on a goal
this lane has never run (`everRun: false`, seats already `done`).

A row stops a dispatch in **three** cases, not one — the review's F3/F6 findings, and the reason the
at-dispatch row is written at all:

| the record's row for this seat | what happens here |
|---|---|
| `outcome = done` | the seat is `done`. Nothing re-runs it, and no grant can re-open it. |
| **still OPEN**, and no execution in THIS store owns its session id | the seat is **`live`** — somebody else is running it *right now*. Dispatching would be a concurrent double-run of one seat. |
| ended **non-`done`** (failed / blocked / killed), same test | the seat is **`live`** — held until an explicit `--relaunch <seat>` grant, which is exactly what a LOCAL failure already requires. Without this the two lanes were asymmetric: a local failure needed the grant, the same failure elsewhere re-ran silently. |

⚠ **The membership test is the `session-id` join, not the `lane` column.** `lane` says which KIND of
store wrote the row; two attached runs on two machines share that value, so a lane comparison would
call another machine's live seat "ours" and dispatch it twice.

⚠ **The disclosed bound, with its unstick path.** A foreign writer that CRASHED leaves its row open,
and the seat stays held. That is not a dead end: that lane's next run publishes from its own store (a
crashed foreground row reconciles to `failed`, a killed detached one to `failed`/`killed`), and the
seat becomes grantable. If that lane will never run again, `--relaunch <seat>` is the operator's act —
the same one a local failure requires. Holding is the safe direction; the unsafe one is running a seat
somebody else may still be running.

**Every write takes a lock, and that is not belt-and-braces.** The close shipped as an unlocked
read-modify-write in the first version of this build; measured in review, **300 appends racing 300
closes lost 336 of 601 rows** — whole rows, nothing malformed for a reader to detect, and
`finishedSeats` transiently reading EMPTY (the one wrong answer that re-runs a finished seat). Two
lanes over one goal is what this record is FOR, so that interleaving is the normal case. Both halves
of the cure are needed and both are probed (`D5`, two real processes): a **lockfile** (`O_EXCL`,
self-clearing, stale-stolen after 5s) around every write, and an **atomic replace** (temp + `rename`)
for the rewrite, so a reader — which takes no lock, and must not have to — never sees a partial or
empty file.

## The daemon lane's goal pickup — BUILT, trigger and all

Until this build **the daemon lane had no path that seeds a goal's taskforce at all** (measured: one
seeding function, one non-probe caller — the attached lane's own boot). Seeding has been moved out of
this capability into `engine/seeding.js`, unchanged in behaviour, because none of it was ever a
property of the terminal a run is attached to; the engine BOTH lanes boot now exposes it:

```js
engine.seedGoal({ goalFolder, goal, profile })
// -> { seats, skippedAsFinished, heldByOtherLane, enqueued, states }
```

`skippedAsFinished` and `heldByOtherLane` are reported separately because they are different facts an
operator must be able to tell apart: one seat is DONE, the other is somebody else's right now.

It publishes, reads the record, seeds create-only, and enqueues only what is due — skipping every seat
the record says is finished, whichever lane finished it. Job ids are **namespaced per goal**
(`seat-<goal>-<seat>`) for a shared store, because `seat-<name>` collides across goals there; the
attached lane passes no namespace and its ids are byte-identical to what it has always written, so
every goal already on disk resumes exactly as before. **Cross-lane identity never rides on the job id**
— it rides on the seat name in the record.

### The trigger — a per-goal lane assignment the daemon watches

The follow-on this section used to name is **discharged** (owner ruling
`decisions.md#d-daemon-lane-button`, 2026-08-10). *What tells the daemon to pick a goal up* was an
owner-facing arming question, and the owner answered it: **a marker file in the goal folder, written
by a CLI, read by the daemon once a cadence.**

| Piece | Where |
|---|---|
| the marker | `<goal>/execution-lane` — one word, the `execution-mode` file's precedent exactly. A `daemon` assignment carries its launch profile as a second token: `daemon claude-sonnet` |
| the writer | `rbtv goal lane <goal> [--set daemon --profile <name> \| --set console]` (`capabilities/goals-tree/`). Read-only with no `--set`. **Works daemon-down** — which is most of why the trigger is a file and not a gateway intent |
| the watch | `engine/lane-watch.js#runLaneWatch`, called by `server/index.js` immediately **before** every tick (boot tick included), so a seat the pass enqueues is dispatched by that same tick |
| the seeding | `engine.seedGoal` and nothing else — the pass decides WHICH goals, never HOW to seed (`PRIN-11`) |

⚠ **ABSENT MEANS `console`, and the daemon adopts only goals EXPLICITLY assigned to it.** An
unreadable file, a junk word and a missing file are ONE answer, exactly as everything that is not
`interactive` is `autonomous`. The choice is fail-closed on purpose: every goal folder already on
disk predates this build and carries no assignment, so the opposite default would have adopted the
whole tree on the first tick after deploy. "Assigned to the console" and "assigned to nobody" are
deliberately not distinguished — neither is the daemon's business, and a third state would be a
state nothing reads.

⚠ **A `daemon` assignment MUST name a launch profile, and the CLI refuses `--set daemon` without
one.** Seeding takes a profile BY NAME from the one shared config and never derives one (`DEC-1`
§ Shared profile source — the same argument `rbtv run --profile` makes); `taskforce.csv`'s
harness/model columns are task **7.54**'s catalog, not a profile name. There is no third place to
read it from, so the marker carries it.

**What the pass skips, and why:**

- a goal whose marker is not `daemon` — the assignment is the whole trigger;
- a goal with no `taskforce.csv` yet — scaffolded but not materialized is a normal state, not a fault;
- a goal a **console runner is attached to right now** — `.attached-run.lock` is READ (with its own
  `runnerAlive` liveness test, so a crashed runner's leftover lock cannot park a goal forever), never
  taken and never cleared: it is the attached lane's interlock and a stale one is the next `rbtv run`'s
  to clear. The record's open-row holds already stop a per-SEAT collision one cadence later; the lock
  answers "somebody is attached to this goal RIGHT NOW" with no lag at all, and both are kept.

Nothing in the pass is fatal: a goal that fails to seed is logged and skipped, and the tick that
serves every other goal continues. `heldByOtherLane` rides the log line an operator reads, beside
`enqueued` and `skippedAsFinished` — an operator has to be able to tell "somebody else is running
this seat" from "this seat is done".

**THE SWITCH is the supported act.** Flipping the marker mid-goal is what the ruling calls the
button: the daemon lets go on its very next pass, and the other lane resumes from the execution
record with nothing re-run. Measured end to end, in the owner's own direction — the daemon enqueues
and dispatches `alpha`, its own tick publishes `alpha=done`, the marker flips to `console`, and
`rbtv run` runs `bravo` and never touches `alpha` (`engine/probes/probe-daemon-lane-watch.js` L6,
with three mutations red at L8).

⚠ **The human-interactive fallback gap is NOT solved here and the existing behaviour stands.** The
pass passes no `isHeld` predicate, so the daemon dispatches a human-interactive seat exactly as it
does today; what *should* happen to a seat with no terminal to reach is migrate task **7.626**.
Passing a predicate here would have parked such seats forever — a new behaviour wearing a bug fix's
clothes.

⚠ **The marker's TERM is being minted registry-side; the filename is descriptive and this build
coined no noun for it** (the same discipline `executions.csv` followed before
`d-execution-record-name`).

## The cross-lane refusal — RETIRED (it was v1, and this is its retirement)

`assertNoCrossLaneEvidence` — the S-18 guard that refused a goal carrying execution evidence its own
store could not account for — is **deleted** with this build, exactly as its own pointer comment said
it would be. The guard refused because it could not tell WHICH seats the other lane had finished; the
record tells it, so the crossover is **resumed** instead of refused.

⚠ **The one case the guard covered that the record does not**, stated rather than quietly dropped: a
seat run **by hand** in a tmux sitting writes a `sessions.csv` row and no record row, so it is
invisible to the record and the seat WILL be re-run. Closing such a seat is one outcome row in
`executions.csv` — the same act every lane performs. Measured as an arm, not assumed
(`probe-cross-lane-resume.js` D4, "BOUND").

## What it runs

The goal folder's `taskforce.csv` is the workflow. Each row is a seat; the row's **`after` column is
the wave structure**. Seats with no `after` are wave 1 and are enqueued together; a seat whose
`after` names another is released only once that one is **done** — started is not enough. How many
run at once is the ticker's `max_live_agent_sessions`, not this capability's: the wave decides
ELIGIBILITY, the ticker decides DISPATCH.

**The profile is passed by NAME and never derived.** Mapping an elected (harness, model) onto one
profile name is core-build task **7.54**'s catalog; a second mapping here is exactly the drift
`DEC-1` § Shared profile source exists to prevent. All four properties of the widened sole-spawn
gate hold: a pinned NAMED profile from the one shared config · picked by name · caller free text
never reaching argv · the pure-mechanism boundary intact.

## Resume, and the absence of a watcher

State lives in `<goal-folder>/heart.db`, and completion in `<goal-folder>/executions.csv`.
Re-running the verb reopens the store and continues: job registration is create-only and a seat that
already has an execution row is never re-enqueued, so a re-run is a **resume, not a replay** — and
since `#d-s23-single-execution-record-now` that rule reaches ACROSS LANES, because the record is read
before seeding (§ The goal's execution record). Proven by SIGKILLing a live run and re-running it
(`ignite/engine/probes/probe-engine-library.js`, section C3c).

⚠ **No watcher runs for an attached lane, and that is RULED rather than missing**
(`decisions.md#d-attached-lane-no-watcher`). The accepted cost, in the ruling's own words: *an
attached run that dies unattended stays dead until the owner notices.* Recovery is re-running this
command. Do not build a watchdog for this lane and do not file its absence as a gap.

## Windows

The verb runs on Windows as a **supported, DEGRADED substrate**
(`decisions.md#d-windows-degraded-attached-lane`) — but **the degraded branch bodies are not built
yet, and it says so rather than pretending.** `ignite/engine/substrate.js` refuses a non-POSIX host
with a typed `E_SUBSTRATE_UNSUPPORTED` naming all four sites (carrier · tree-kill ·
filesystem-wall · seat-room) and **core-build task 7.84**, which carries them.

The refusal is deliberate. Falling through would run POSIX constructs on a host that cannot honour
them — most sharply, the tree-kill signals a process GROUP inside a swallowing `try/catch` whose
liveness re-check reads a throw as *"the process is gone"*, so it would report a successful kill
having killed nothing. **A silent false green is worse than a refusal.**

## Probes

`ignite/engine/probes/probe-foreground-carrier.js` — the foreground carrier (B1). A held seat and a
detached seat in ONE run, read off the rows each carriage wrote; both gates measured with the other
held open; the enqueue pass's own bar measured where it stands; the `headed.tui` provenance and the
descriptor injection; the no-headed-block refusal with its control; and the crash edge done for real
— a `rbtv run` subprocess SIGKILLed while a foreground seat holds it, then re-run. Every arm proven
red by mutation (drop the enqueue bar · force the predicate true · no-op the reconciliation · let a
grant re-open finished work · drop the `seat-failed` verdict · remove the run lock · treat a live
holder as stale · treat a dead holder as live · overwrite a foreign terminal row). Sections **B1h**
(S-20) and **B1i** (S-21) carry the two later rulings: the foreground row joins its own execution by
session id, is schema-conformant against the file's OWN header, carries the runner's identity pair,
is CLOSED on the child's exit (`ended` + `exited`/`kit`) — verified through the real python readers,
`goal-state-job.open_session_seats` and `coord.session_disposition`, not by inspecting a cell —
and an ALL-FOREGROUND package's trace is born with the schema owner's header; every shipped
`headed.tui` pins its profile's own model, and the pin survives composition on the real carrier path
with a shipped profile. Mutations, all red: no-op the trace row · unpin one profile · pin the WRONG
model on one profile · **no-op the closer** · close with `done` instead of `exited`. `tty` is
REPORTED, never asserted — a probe cannot own a terminal.

`ignite/engine/probes/probe-cross-lane-resume.js` — **B3's verdict, REPURPOSED onto the record that
answers it.** It measured a negative until 2026-08-10 (cross-lane resume did not hold in either
direction); its arms now measure the resume, behaviourally, in both:

- **D1 attached -> daemon.** The attached lane runs the goal; the record carries `alpha=done/attached`;
  a DAEMON-rooted engine then seeds the same goal folder and **skips alpha, enqueues bravo**. This is
  the half that could only be measured structurally before.
- **D2 daemon -> attached.** A daemon-side execution is synthesized and then published by the
  DAEMON'S OWN CALLER — a daemon-rooted `engine.tick()`, plus a second arm asserting that
  `server/index.js` is what calls it (the first version of this probe called `publishToRecord`
  directly, which measured the function and not its caller — and that is precisely how a daemon loop
  on the raw ticker shipped). The attached lane then runs the goal and re-runs nothing.
  **Discriminating mutation:** delete alpha's ROW from the record and the same fixture re-runs the
  seat — so the skip tracks the recorded row, not the file's existence, the seat's name, or the trace.
- **F3/F6 the holds.** An OPEN foreign row holds the seat (never dispatched twice, `--status` says
  `live`, the run RETURNS `blocked` instead of spinning, an explicit grant releases it); a foreign
  `failed` holds it the same way, and no grant can ever re-open a `done` seat.
- **F2 adoption.** A goal whose record is deleted has its store's history republished by its next run,
  and the daemon then skips those seats off the republished record.
- **D5 the two-writer race.** 300 appends racing 300 closes from two REAL processes: every row and
  every stamp survives, an unlocked reader never sees the file go backwards or empty, and no lock file
  is left behind.
- **D4** measures that a goal carrying another lane's evidence RUNS (the v1 refusal is gone), that
  `--status` answers `done` off the record with no store at all, the false-positive **control** (the
  attached lane re-running its own goal re-fires nothing), and the **BOUND** (a trace row with no
  record row neither refuses nor stops a re-run).
- **D3 is unchanged** and still negative: nothing under `server/` asks whether a seat is
  `human-interactive`, so a held seat dispatched by the daemon lane is spawned as an ordinary detached
  child and its `fallback:` can fire nowhere (that gap is task 7.626, ruled by `#d-s19`).
- D1's former **measured bound** — "`seedGoal` exists and nothing under `server/` calls it" — is
  RETIRED with the trigger it named: the pass and its call site are measured next door.

`ignite/engine/probes/probe-daemon-lane-watch.js` — **the trigger** (`#d-daemon-lane-button`). The
marker's grammar (absent, empty, junk and `console` are ONE answer; only `daemon` opens it, trimmed
and case-insensitive) · the CLI as the writer, cross-checked against the engine's reader so the two
languages cannot drift, with `--set daemon` REFUSED without a profile · one watch pass over a real
goals tree: the assigned goal adopted, the **console-assigned control** untouched with nothing of it
reaching the daemon's store, a goal under a genuinely LIVE run lock skipped and then adopted on the
pass after the lock is gone (the pair, so "not seeded" can never pass for an inert watch), and a seat
the other lane has not finished HELD **and reported on the log line** · the SWITCH end to end — the
daemon enqueues and dispatches `alpha`, its own tick publishes `alpha=done/daemon`, the owner flips
the marker, the daemon lets go on the next pass, and `rbtv run` runs `bravo` having never fired
`alpha` · the call site asserted in `server/index.js` with comments stripped, and asserted to run
BEFORE the tick. Three mutations, each an asserted single-string change compiled in memory and
required to go red: **the assignment ignored** (the daemon seeds a console goal) · **the run lock
ignored** (it seeds a goal a live console runner is attached to) · **the watch call removed** from the
loop (the state this build closed). Substitutions disclosed in its header: no daemon PROCESS, one
synthesized completion (the dispatch itself is real), and `sleep` for a harness.

`ignite/engine/probes/probe-attached-status.js` — the `--status` verb (A3).

`ignite/engine/probes/probe-engine-library.js` — 57 checks over criteria 1–4 and the seam. Every
refusal carries a positive control in the same run, and the wave and resume claims are measured at
the DECISION rather than at what happened to fire (both were rewritten after a mutation sweep
showed the first versions could not fail). What it deliberately does not prove is stated in its own
header: nothing about Windows, and the seats it launches are `sleep`, not harnesses.
