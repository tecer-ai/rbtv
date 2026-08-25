---
description: One ending store — seat endings, goal words, open asks, and derived predicates.
---

# state-store

The ONE ignite ending store. Record shape and predicates are law in
`1-projects/build-ignite/redesign/specs/spec-state-store.md`. Tables live inside
the host `heart.db` opened by `ignite/state-store/heart/heart-store.js`. This folder
is the write/read API siblings consume.

Runtime file (workspace-relative, GENERAL): `.rbtv/runtime/ignite/heart.db`.

## APIs

Write: `stampSeatDeclare` · `stampSystem` · `replaceSeatEnding` · `writeGoalWord` ·
`insertAsk` · `postAsk` · `reapAndRelaunch` · `incrementRecoveryRelaunch` ·
`setLeaderAttemptUsed` · `fireNamedEvent`

Read: `getCurrentEnding` · `getGoalState` · `getAsk` · `seatWaitingOnOwner` ·
`goalWaitingOnOwner` · `countOpenAsks` · `isGoalPaused` · `isGoalRunning` ·
`isGoalFinished` · `isLaunchable` · `checkDoneOutputs` · `killClockPauses` ·
`endingStorePath`

Kit/engine door: `cli.js` (`--db` `--op` `--payload`). One-shot cutover copy:
`copy-home.js` (do not run against a live daemon).

## What moved in with the component-first migration

`spec-component-map` §2 landed `state-store/heart/` here, with history, as `heart/` -
move-only, no body split (`heart-store.js` is a named over-budget leftover this plan
does not touch). The daemon's own process host is `runtime/`; this component is the store.

## State layout — the two roots (owner ruling, 2026-07-20)

ignite's state lives in exactly TWO roots, split by ONE membership test: **"can the user work with
this WITHOUT ignite?"** Yes → per-workspace. No → per-machine.

| Root | Purpose | Holds |
|---|---|---|
| **Per-workspace** — `{workspace}/.rbtv/` | Everything a user can work with without the daemon — an interactive session on a machine with no ignite carries the same modules and configs as the server machine | `modules/`, `runtime/`, `goals/`, `mirror/` |
| **Per-machine** — the machine's state root (recorded as `state_root` in `server.json`'s machine entry, provisioned by the unit's `StateDirectory=` and passed as `RBTV_IGNITE_DATA_ROOT`) | Ignite-only configs, logs, and runtime | `heart.db`, `logs/`, `prompts/`, `exits/`, `ptys/`, `ticker.log`, `feed.jsonl` |

- **`heart.db` is per-machine, WHOLE.** The membership test cuts through the store (the `jobs`
  catalogue is user-authorable; `queue` / `jobs_log` / `messages` are runtime) — owner ruled it
  stays one file, per-machine, at `{state_root}/heart.db`. Accepted consequence: the jobs catalogue
  is not readable without the daemon.
- **The flat `.rbtv/sessions/` launch path is RETIRED** (`r-seats-only-architecture`, 2026-08-06):
  every daemon spawn homes as a seat under its goal
  (`.rbtv/goals/<goal>/runs/<run>/seats/<seat>/`). A dispatch with no home is a refusal, not a
  flat dir.
- **Retention** (`runtime/retention.js`, swept at daemon boot and daily) enumerates the per-machine
  root's artifact classes — `logs/`, `prompts/`, `exits/`, `ticker.log`, `feed.jsonl` — as a
  POSITIVE enumeration (a dropped class is never VISITED, so leftovers on a deployed box are
  untouched rather than swept): `heart.db` and `.runtime-config/` are never visited by
  construction. Age-based only, NO size cap; window `RBTV_IGNITE_LOG_RETENTION_DAYS` (default 90,
  `0` = never, below 7 rejected at boot); read-only on `inspect daemon`'s `config` block.

## Terminology

Canonical vocabulary for every spec, task, dispatch, review, and code file of this module (owner
ruling D23, 2026-07-14). Specs and code MUST use exactly these words for these things. A term is
invented or changed ONLY when necessary, and every invented or changed term is OWNER-APPROVED
before it binds; if a term already exists for what you are writing, USE it — never create an alias.

### Turn-audit states (`jobs_log.status` — HISTORY, closed enum)

⚠ **`jobs_log.status` IS HISTORY. IT IS NEVER LIVENESS AND NEVER WORK-STATE** [T4-R8]. The seven
words below stay writable on `jobs_log` and only on `jobs_log`, as the daemon's audit/turn log of
what a fired execution last recorded about itself. Nothing schedules, launches, relaunches or waits
on them. The three questions they used to be asked stand answered elsewhere:

| the question | the surface that answers it |
|---|---|
| is this seat's process alive? | the supervisor registry — MEASURED liveness, never a stored word |
| how did this seat's work END? | this store's `seat_endings` — `done` / `incomplete` / `failed`, one current row per (goal, seat) |
| may this seat launch, or is it waiting? | the DERIVED predicates of `spec-state-store` §2 — launchability off the task graph, `waiting-on-owner` off a posted, still-open `open_asks` row |

A `running` row means "the last thing written about this turn", not "this seat is working" — a
process that dies unobserved leaves that word in place until a sweep gets to it, which is precisely
why liveness moved off this column.

| Term | Definition |
|---|---|
| `launching` | The job fired and the spawn was initiated; the process is not yet confirmed running. (Replaces the retired `spawning` — same meaning, store term wins, D23.) |
| `running` | The process is alive; the turn is in progress. |
| `done` | The session ended its turn with its own `completion` report, status done. |
| `blocked` | The session reported blocked-on-X and ended its turn; the slot persists. |
| `failed` | Terminal without a successful completion: tool exit ≠ 0, crash-swept agent, or found dead at the boot orphan rescan. The ONLY exit-status path — D18(4) uniform exit reporting. Absorbs the retired `orphaned-dead`: the orphan-discovery detail is DATA on the row, never a status word. |
| `stalled` | Silent past the stall rung while the process lives; the slot's automatic action is halted; the process is NOT auto-killed. |
| `killed` | Explicitly killed via the kill surface (TERM → grace → KILL, whole process tree). |

**Process-level facts are NOT statuses** (genuinely different things — kept distinct, D23): a
process being alive or **exited** (ended, exit code observable) is a carrier observation, computed
live or carried in the `pid` / `exit_code` data columns — never a second stored lifecycle. When a
process exits, the session's STATUS resolves to `done` / `blocked` / `failed` through completion
handling. The former carrier-state enum (`spawning | running | exited | killed | orphaned-dead`)
is retired.

### `session_mode` values (closed enum, fixed at creation — D7/D17)

| Term | Definition |
|---|---|
| `headless` | Default. One-shot detached session; watchable and killable, resumable at turn boundaries; can NEVER be joined mid-turn. |
| `headed` | Opt-in. Runs in a tmux pane in the goal's run-scoped room; a human joins it over SSH. Requires a launch spec with a `headed:` block AND `RBTV_IGNITE_TMUX_ROOM` set on the unit — typed rejection otherwise, at queue time AND spawn time. |

### Core nouns

| Term | Definition |
|---|---|
| job | A deterministic command (function + arguments), dry-run-validated at queue time; NO LLM in the path. |
| queue | The control-plane store of PENDING jobs only; the server core is its sole writer. |
| execution | One fired run of a job. One `jobs_log` row = one execution = one session record (D16 folded model). |
| session | A running executor process started by the server core on the launch spec its seat is CAST to; watchable live, survives disconnects, controllable at turn boundaries, killable at any time (D7). Runs exactly ONE turn, ends on its own report. |
| worker | The spawned executor process a session runs (the registry concept is `executor` = agent \| tool). Names the transient units: `rbtv-worker-<session-id>`. |
| seat-slot | The persistent work slot a chain of one-turn sessions occupies; the slot persists, sessions are cattle. |
| turn chain | Successive executions sharing ONE chain-stable thread, each linked to its predecessor via `jobs_log.parent_exec_id` (NULL = the chain's first execution). |
| thread | The message-thread id a whole chain shares: `exec-<exec_id of the chain's FIRST execution>`, carried UNCHANGED across recycles. |
| tick | One pass of the ticker engine's fixed 7-phase loop (default cadence 10 s). |
| ticker engine | THE one runtime engine that makes the queue launch due jobs — deliberately singular; "heartbeat" is RETIRED and never names the engine. |
| launch spec | A config-pinned command-template set (exec/resume/caps/sandbox/effort ladder), keyed by **(harness, model)** in `launch-specs:`. NO caller anywhere selects one: a seat's CAST resolves it at spawn time, and callers never inject flags (DEC-1 R3). Successor to the RETIRED "launch profile" (`#d-abolition-terminology`). |
| cast | The assignment of one executor (harness · model · effort) to one seat. A bindings sheet is composed of casts, and a cast is what resolves a launch spec. NOUN only — never a verb (`PRIN-7`/`PRIN-10`). |
| sender | An authenticated identity (`kind: owner \| agent \| bridge`) presenting a per-sender token at the gateway; the resolved sender-id rides every forwarded request and lands in the audit columns. |
| `enqueued_by` | CANONICAL column/argument name for "the authenticated sender who caused this run" (D26) — no synonym alias. |
| completion | The typed message that ends a turn, carrying status `done` \| `blocked` \| `failed` (report-failed is a completion with failed status — never a type of its own). |
| `session-killed` | The audit record `kill-session` appends after a kill succeeds — attribution only (WHO killed WHICH session WHEN), never a payload. ⚠ A READER of a session audit file may still meet three retired kinds on disk — `keys-accepted`, `screen-read`, `screen-read-summary` — written before the pty intents were retired; no code writes them now, and any tool that parses the file must still understand them. |

**Retired words — MUST NOT be used for this module:** `heartbeat` (the engine is the ticker
engine), `spawning` (use `launching`), `orphaned-dead` (use `failed` + discovery data),
`requested_by` (use `enqueued_by`), **`launch profile`** (use `launch spec`; the NAME layer that
term implied is abolished outright by `#d-abolish-profile-names`, so the word names nothing that
exists). RETIRED SURFACES (the words stay legible for history but name nothing live):
`send-to-session`, `capture-session-screen`, the `ignite send` / `ignite screen` wrappers, the web
terminal and its ttyd surface, the in-unit dtach holder, the pty bridge — a headed session is a
tmux pane and SSH is the human trust boundary.
