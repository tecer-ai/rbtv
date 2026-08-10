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
- ⚠ **Known bound — the shipped claude profiles pin no `--model` in `headed.tui`** (`argv: ["claude"]`),
  so a foreground seat runs the harness's default model rather than the profile's. The harness binds;
  the model does not. Fixing it is a one-line change per profile in `config/spawn-profiles.yaml` with
  daemon-headed blast radius — **filed, not smuggled in.**
- ⚠ **No cage.** A session sharing the owner's terminal has neither bwrap nor a systemd slice —
  the accepted bound of the console-run design (§ Cautions), the same one d1's hand-run elicitator
  had. The detached seats of the same run are caged exactly as before.
- **It needs a real tty**, so `rbtv run` on a goal with held seats cannot be a skill session's Bash
  call. The entry skill hands the user the command to type.
- **No `sessions.csv` row is written for a foreground seat** — that row is the daemon spawn path's,
  which this carriage deliberately does not go through. Consequence: a package whose seats were all
  carried in the terminal has no launch trace, and the edge-runner's check-out fast path refuses a
  traceless package wholesale. Filed for a ruling rather than patched here.

### Crash semantics — the contract, stated explicitly

A foreground seat killed mid-work leaves an execution row nobody ended, because the process that
would have ended it died with the child. This is what happens, and none of it is a retry:

| Event | What the run does |
|---|---|
| the seat's session exits **0** | turn `done`, session `closed` — the same exit-code rule the ticker's sweep applies to every other seat. The DAG advances on the next pass. |
| the session exits **non-zero** | turn `failed`, session `crashed`. The run does not advance past the seat: it returns `seat-failed`, exit **1**, naming it. |
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
grant re-open finished work · drop the `seat-failed` verdict).

`ignite/engine/probes/probe-cross-lane-resume.js` — **B3, and its verdict is negative.** Cross-lane
resume does not hold in either direction: the daemon lane has no path that seeds a goal's taskforce
into its own store (one seeding function, one non-probe caller), and the attached lane re-ran a seat
the daemon store recorded as done, under the most generous key-matching assumption available. The
goal folder DOES carry a lane-independent trace (`sessions.csv`) — no engine module reads it. And
nothing under `server/` asks whether a seat is `human-interactive`, so a held seat dispatched by the
daemon lane is spawned as an ordinary detached child and the `fallback:` it is required to declare
can fire nowhere. The daemon-side behavioural half is a **measured refusal**: it needs a live daemon,
a gateway and an armed `edge-fastpath.json`, and the probe says so instead of faking it.

`ignite/engine/probes/probe-attached-status.js` — the `--status` verb (A3).

`ignite/engine/probes/probe-engine-library.js` — 57 checks over criteria 1–4 and the seam. Every
refusal carries a positive control in the same run, and the wave and resume claims are measured at
the DECISION rather than at what happened to fire (both were rewritten after a mutation sweep
showed the first versions could not fail). What it deliberately does not prove is stated in its own
header: nothing about Windows, and the seats it launches are `sleep`, not harnesses.
