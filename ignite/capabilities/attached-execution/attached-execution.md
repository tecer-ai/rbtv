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

Everything it prints is DERIVED — console-run design ruling 2: there is no new state file, no
engine breadcrumb, no session-maintained doc. Sources: the goal's `taskforce.csv`, its own
`heart.db` *if one exists*, the seat descriptors, and the `execution-mode` file.

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

## The cross-lane refusal — v1, and it has a retirement date

**Owner ruling `decisions.md#d-s18-cross-lane-refusal`, closing S-18.** Each lane keeps its own heart
store, and seeding is create-only **within a store** — so a goal half-run in one lane and picked up by
the other RE-RUNS finished seats. Measured, not feared (`probe-cross-lane-resume.js` D2: the attached
lane re-ran a seat the daemon store recorded as done, under the most generous key-matching assumption
available). v1 answer: **a lane refuses a goal carrying execution evidence its own store cannot
account for, naming what it found.**

**What counts as evidence, and why it is not the obvious thing.** "The goal folder has a
`sessions.csv`" is NOT lane-discriminating: an attached run's own detached seats go through the daemon
spawn path and write exactly those rows. The deciding fact is the **join**: a trace row for a seat of
this taskforce whose `session-id` no execution in **this goal's own store** owns. That is the cheapest
honest detector available today, and it needs no new record.

- It **refuses before the goal is touched** — before the run lock and before the store.
- It reads the goal's store **only if one already exists** (same bar `--status` holds), and reads it
  **READ-ONLY, through a `readOnly` sqlite handle rather than `openHeartStore`**: the store's
  constructor sets WAL pragmas and runs migrations, so going through it would have migrated an
  out-of-date store — before the lock, i.e. behind a live runner's back — as the price of declining
  to run. Probed on a store stamped `user_version = 0`: it stays 0, and the file stays byte-identical.
  (⚠ The accepted price, measured: a WAL reader must create `heart.db-wal`/`-shm`, and a read-only
  connection cannot remove them, so a refusal leaves those two sidecars beside the store. They are
  deliberately NOT deleted — this runs before the lock, and unlinking another live runner's `-wal`
  loses committed transactions. Litter over data loss.)
- **The claim is scoped to the CURRENT taskforce's seats.** Trace rows are filtered against
  `taskforce.csv`, so a row for a seat since renamed or dropped is invisible to the guard: *"evidence
  its own store cannot account for"* means the seats the goal has now, not the whole file. The
  direction is safe — it under-refuses rather than blocking a goal over a seat it no longer has.
- **No store at all + trace rows gets its OWN message and its own remedies** (`rm heart.db` on a goal
  this very lane ran lands here). Blaming "another lane" there is false and unactionable, so the
  refusal says what is true — the trace names launched sessions nothing can account for — and offers
  the three honest options: restore the store, move `sessions.csv` aside consciously and accept the
  re-run, or start a fresh goal.
- **`--status` never refuses.** Orientation is read-only, and a goal you cannot run is the goal you
  most need to orient on.
- It also catches a seat **run by hand** (a team-kit tmux sitting writes its own row through
  `coord.py`). That is the same hazard in another coat — work this store has no record of — so the
  message says what was measured rather than asserting which lane wrote it.
- **The daemon direction is VACUOUSLY HELD, and that was measured rather than assumed.** One function
  seeds a goal's taskforce (`seedTaskforce`) and its only non-probe caller is the attached lane's own
  boot, so there is no daemon-side path that could pick up a goal and re-run its seats. A symmetric
  refusal on that side would be dead code today; it becomes live the moment anything under `server/`
  seeds a taskforce.
- ⚠ **v1, with its successor already filed.** The full fix is Phase-6 work in
  `rbtv-sb-merge-refactor-migrate` — *"Build the lane-independent execution record so a goal can move
  between the daemon and console lanes"*: both lanes read/write ONE goal-folder record, and **this
  guard retires when it lands**. Do not grow it into that record.

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

State lives in `<goal-folder>/heart.db`. Re-running the verb reopens it and continues: job
registration is create-only and a seat that already has an execution row is never re-enqueued, so a
re-run is a **resume, not a replay**. Proven by SIGKILLing a live run and re-running it
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

`ignite/engine/probes/probe-cross-lane-resume.js` — **B3's negative verdict, and now the S-18 guard
that answers it.** Cross-lane resume does not hold in either direction: the daemon lane has no path
that seeds a goal's taskforce into its own store (one seeding function, one non-probe caller), and the
attached lane re-ran a seat the daemon store recorded as done, under the most generous key-matching
assumption available. Nothing under `server/` asks whether a seat is `human-interactive`, so a held
seat dispatched by the daemon lane is spawned as an ordinary detached child and the `fallback:` it is
required to declare can fire nowhere. The daemon-side behavioural half is a **measured refusal**: it
needs a live daemon, a gateway and an armed `edge-fastpath.json`, and the probe says so instead of
faking it. Section **D4** measures the refusal built on that basis — the message names the seat and
the session id, no store or lock is left behind, `--status` still answers, and the guard is proven
DISCRIMINATING by a pair: give the goal's own store an execution for that session id and the very same
goal runs, while a goal the attached lane ran itself (two trace rows, one per carriage) is never
refused. It also measures the store-PRESENT refusal path (an out-of-date store is left out of date)
and the absent-store message. Mutations, all red: disable the guard · make it ignore the store join ·
no-op the foreground trace row · read the store through the migrating `openHeartStore` · drop the
absent-store branch. ⚠ The byte-identity check ALONE was proven **non**-discriminating by that
fourth mutation — `openHeartStore` leaves an already-current store byte- and mtime-identical — which
is why the arm asserts an unstamped `user_version` instead.

`ignite/engine/probes/probe-attached-status.js` — the `--status` verb (A3).

`ignite/engine/probes/probe-engine-library.js` — 57 checks over criteria 1–4 and the seam. Every
refusal carries a positive control in the same run, and the wave and resume claims are measured at
the DECISION rather than at what happened to fire (both were rewritten after a mutation sweep
showed the first versions could not fail). What it deliberately does not prove is stated in its own
header: nothing about Windows, and the seats it launches are `sleep`, not harnesses.
