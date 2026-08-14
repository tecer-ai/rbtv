# ignite/ — the ignite daemon

Source of the **ignite daemon**: ONE Node.js service (one systemd unit) with a hard internal module boundary between the **server core** (owns `.rbtv/` runtime state; sole queue writer; ticker engine + spawn machinery) and the **gateway** (sender auth + client CLI; no queue handle, no spawn). Repo conventions for this folder (deployment model, no hardcoded paths, relocatable subtree, branch discipline): root `CLAUDE.md` § "ignite/ — Runnable Service Code (convention)".

Developed on branch `ignite/core-daemon`; design authority: the build specs under `1-projects/rbtv-sb-merge-refactor-core-build/build/phase-7-plan/specs/` (heart-store · ticker-engine · spawn-profiles · internal-api-contract · gateway-cli), governed by the `system-definition/` registry.

## team-kit/ — the module's second component

`ignite/team-kit/` holds the **team-kit**: reusable mechanics for coordinated parallel multi-agent team runs in tmux (`coord.py` coordination CLI, `protocol.md`, watcher/closer seats, briefing templates). Unlike the daemon it IS an installable component — the `rbtv-team-kit` skill (manifest module `ignite`) is a thin loader into it; the kit's scripts and docs are read/run in place from the repo, never copied into `.claude/`. Its rules live in `ignite/team-kit/CLAUDE.md` (including the owner-gated instance-coupling list to generalize before master). Promoted 2026-07-26 from the second-brain campaign workspace after three proving runs; docs: `modules/ignite.md`.

## capabilities/ — standalone operator surfaces the `rbtv` CLI delegates to

`ignite/capabilities/` holds this module's capability-shaped components — each a self-contained
operator surface with its own contract doc, reached from the `rbtv` CLI by delegation
(`PRIN-11` — no second implementation):

- **`daemon-operator/`** — the ignite OPERATOR surface: local systemd USER unit ops (`start` /
  `restart` / `stop` / `kill` / `unit`) that work precisely when the daemon is DOWN. Contract:
  `capabilities/daemon-operator/daemon-operator.md`.
- **`goals-tree/`** — the goals-tree machinery (`scaffold` / `reindex` / `lint` / `materialize` /
  `lane` / `pause` / `resume` / `dag` / `add-seat` / `retry-threshold` / `teardown`).
  ⚠ **`teardown` is the ONE verb here that needs the DAEMON UP**, and reasoning from its siblings
  will mislead you: every other verb is a local file operation *precisely so* it works daemon-down,
  but what teardown reclaims is the job CATALOGUE, which lives in the machine's `heart.db` and is
  served only by the gateway (§ State layout). It calls `ignite deregister-job --purge` for each of
  a goal's rows so the goal's NAME is free again (issue `IPH-27`) — scaffolding WRITES those rows,
  deleting the goal folder removed none of them, and `register-job` is create-only, so a deleted
  goal BURNT its name. It composes the ids from the goal's own `taskforce.csv`, so **run it BEFORE
  deleting the folder**; it never deletes the folder itself (owner-ruled 2026-08-12 — it cannot
  prove it created that directory) and never kills a live session. `retry-threshold` is the
  MILESTONE RETRY BAR (issue `IPH-11`): the consecutive-FAIL count at which the dod-judge escalates
  to the owner — per goal, with a per-milestone override in the `retry-threshold` column of
  `milestones.csv`, absent everywhere = 2. It writes the two files `coord.py`'s
  `resolve_retry_threshold` reads, which is the enforcing authority; `coordinate fail-status` is
  where a seat READS the resolved bar, so no prompt ever types a number.
  `lane` is the DAEMON'S PICKUP BUTTON: **one word — and since `#d-abolish-profile-names` that is
  literal** — in `<goal>/execution-lane` that the daemon's watch pass reads before every tick,
  `d-daemon-lane-button`. The retired second token named a fallback launch profile; a marker still
  carrying one does not parse as `daemon`, so it reads `console` (fail-closed) and BOTH readers say
  so loudly. `--set daemon` REFUSES a goal with any uncast seat, naming them. The last four grow a LIVE goal's seat roster (issue `S-33`): `pause`
  stashes the lane assignment behind a `paused ` prefix BOTH lane readers already resolve to
  `console` (so no reader changed) and `resume` returns it byte-for-byte; `dag` is the read-only
  one-shot graph view; `add-seat` gates, mints through `team-kit/materialize-seats.py`, then
  splices the seat into the after-graph in ONE atomic registry write. ⚠ **Pausing bounds SEEDING,
  not execution** — it stops the daemon starting anything new for the goal, never a session already
  running. Contract: `capabilities/goals-tree/tool/README.md`.
- **`attached-execution/`** — the ATTACHED lane, the **`rbtv run`** verb (`rbtv run <goal-folder>`
  — ⚠ `--profile` is GONE since `#d-abolish-profile-names` (2026-08-12): a seat runs the launch
  spec its own CAST resolves, and an UNCAST seat is a NAMED refusal at this door; entry point
  `capabilities/attached-execution/tool/rbtv-execution`, reached by
  delegation from the TOP-LEVEL `rbtv` CLI — never `rbtv ignite`). Owner ruling
  `d-attached-run-embedded-engine`: ONE implementation of workflow advancement, TWO attachments —
  the SAME engine (`ignite/engine/`) the daemon runs, attached to the calling terminal instead of a
  systemd unit; store at `<goal-folder>/heart.db`, dies with the terminal, recovery is the owner
  re-running the verb (ruled — no watcher). Carries `--status` (console-run A3: the read-only
  orientation surface — everything it prints is derived, it never creates the store, and it works
  before the goal has ever run) and the foreground carrier (console-run B1: a held
  human-interactive seat runs as a foreground child of the runner in YOUR terminal; the tick loop
  blocks while it runs). Exit codes: `0` complete or tick bound reached · `1` refused or cannot
  advance (`seat-failed`) · `3` a worker asked a question and the run handed it back. Contract:
  `capabilities/attached-execution/attached-execution.md`.
- **`master-profile/`** — the channel master's self-service knob (issue C-1, owner-ruled
  2026-08-10): which harness+model+effort the master's next sitting runs on. A **two-part
  capability** — the seat's `request` verb stages a file and triggers, the daemon's `apply` verb
  performs the act — because `fire-tool` argv is static, so a request BODY can only travel as a
  staged file, with `enqueue-job` the one gateway verb open to a `bridge` token. It was RETARGETED
  2026-08-12 off the retired `master_profile` key onto the master's own CASTING SHEET
  (`.rbtv/config/modules/meta/master-agent/bindings/channel-master.json`), which its cage GRANTS it
  — so it writes through `bindings.cast_seat` (one validator, one write, shared with
  `rbtv-bindings set`) and splits ONLY because the `materialize-seats.py --repass` that makes the
  write take effect writes `<goal>/seat.md`, and every seat cage refuses grants overlapping
  `.rbtv/goals/`. ⚠ **It restarts nothing and no longer costs the owner the chat session he is using
  to turn it**: a casting sheet is not boot-read, so the switch lands on the next message. Contract:
  `capabilities/master-profile/master-profile.md`.
  ⚠ **Its former sibling `goal-launch-delay/` is DELETED** (task 7.778, owner-ruled 2026-08-12).
  It retimed the `--delay-seconds` operand of a queued `<goal>-workflow-start` row, and both that
  row and the `workflow_launcher.py` it fired are gone: a created goal now declares its LANE at
  birth (`<goal>/execution-lane`, task 7.777) and the daemon's watch pass seeds it from that
  marker — there is no delay left to tune. Do not reason from `master-profile` to a second knob;
  there is only one.
- **`bindings/`** — the CASTING SHEET surface (owner-ruled 2026-08-10): which harness, model and
  effort each seat of a workflow runs on. A workflow is the program, a taskforce is its running
  instance, and the bindings file is what casts one into the other —
  `team-kit/materialize-seats.py --bindings` is its ONE consumer. Five verbs: `catalog` (every
  spawnable harness+model with each effort dial NUMBERED), `inspect`, `scaffold` (create-only),
  `set` (one seat) and `set-many` (N seats of one workflow from a JSON file, ALL-OR-NOTHING —
  every seat validated through `set`'s own path before the file is opened, so a batch with one bad
  seat leaves the sheet byte-identical and reports every seat's reason). ⚠ **NOT a two-part capability, and that is measured**: the bindings tree is in the channel
  master's `rw-paths` and NOTHING boot-reads it, so every write is a plain direct file write — no
  staged inbox, no daemon fire, no restart. Its two siblings above are split for the opposite
  reason, not by house style. ⚠ **`catalog` is the validator, not a display**: derived from
  `profiles:` in `config/spawn-profiles.yaml` (the workspace's spawnable set) and gated by
  `coord.py#validate_seat` (the predicate materialize's F6 gate imports), so what an agent reads and
  what refuses it are ONE object. One file per WORKFLOW at
  `.rbtv/config/modules/{module}/{component}/bindings/{code}.json` — deployment config, never the mirror,
  which carries component definitions only. Contract: `capabilities/bindings/bindings.md`.
- **`daemon-watchdog/`** — the ignite LIVENESS surface (`CMP-28`): a systemd user timer firing one
  deterministic probe/restart/report pass over the whole deployment. **The one capability here the
  `rbtv` CLI does NOT delegate to** — a watchdog is a scheduled act, not a verb a human types, so
  its reach is the timer. It CALLS `daemon-operator` for EVERY restart, including the probe-suite
  `.timer` (`PRIN-11` — restart-and-verify is not written twice). That row was briefly a bypass,
  because the operator's survival check demanded a `MainPID` a `.timer` never has; `7127713` made
  the check unit-type-aware, so the bypass was deleted rather than kept as dead flexibility.
  Its unit templates live beside it in `capabilities/daemon-watchdog/units/` rather than in
  `deploy/`, so the capability folder stays self-contained per CMP-5. Contract:
  `capabilities/daemon-watchdog/daemon-watchdog.md`.

All but the watchdog are documented for the `rbtv` CLI's delegation table in `modules/ignite.md`
§ Capabilities, which also carries the watchdog.

## launch-profiles/ — the ONE shared launch-spec resolver

`ignite/launch-profiles/` holds the shared resolver every launch goes through (task 7.42; registry
`decisions.md#d-profile-source-unification`, CMP-6 § Interface (1)). ⚠ The FOLDER keeps its name;
the TERM it was named for does not — `launch spec` succeeds `launch profile`
(`#d-abolition-terminology`), and a folder rename is a cascade with no behavioural gain. It owns
launch-spec resolution,
slot validation, the carriage vocabulary, the workdir guard, caged/portable half selection, the
effort translation slot, and the pinned-flag pre-flight.

It requires **nothing under `server/`** — that bound is the point ("a second interpreter of the one
file is the same drift as a second file"), and it is what makes the profiles consumable outside the
daemon process. `server/spawn/config.js` is now a thin daemon-side adapter over it. It is a shared
LIBRARY, not a capability: `capabilities/` above is for standalone operator surfaces the `rbtv` CLI
delegates to, which this is not. The other two ruled consumers — the attached dispatch capability
(7.43) and the orchestration conductor's CLI-worker dispatch (7.54) — are **not built**; shipping
with one live consumer is 7.42's scope. ⚠ **7.54's CATALOG half IS built** (ruling D19, 2026-08-11):
`catalog.js` resolves a seat's declared `(harness, model)` to the launch spec that runs it, and
`server/spawn/spawn.js#launchSpecForSeat` applies it at the single point every launch passes
through — so a seat runs what its `seat.md` casts it as on every lane. Since
`#d-abolish-profile-names` (2026-08-12) that is the ONLY resolution: `launch-specs:` is keyed by
the pair, NO caller may select a spec, and an uncast seat REFUSES (`E_UNCAST_SEAT`). The conductor-dispatch half
of 7.54 remains unbuilt, as does 7.43.

Contract, the caller bounds, and the disclosed residuals: `launch-profiles/README.md`.

## probes/ — every module's probes, and the ONE runner that counts them

Each component keeps its probes in a `probes/` folder beside it; a probe is a self-contained script
that writes its verdict into an adjacent `.out`. **Run them with `node deploy/probe-suite.js`** —
`--list` to enumerate, `--dir <rel>` to scope, `--only <name>` for a single probe, `--selftest` to
prove the runner itself.

**⚠ ASKING WHETHER ANYTHING ALREADY GUARDS X? USE THE ENUMERATOR — never a hand-glob of `probes/`
folders.** There are more of them than you will guess, and the obvious guesses miss: the inspect
target set is guarded from `server/internal-api/probes/`, not `server/probes/`. The count is
deliberately not written here — a literal in this sentence contradicts the sentence, and it went
stale twice (TWELVE, then EIGHTEEN) before this note replaced it.

```
node deploy/probe-suite.js --list | grep -E '\.(js|py)$' | xargs grep -l <SYMBOL>
```

`G-179`: a leader and the engineer independently hand-globbed the wrong folders, both concluded
"unguarded", and **corroborated each other into ratifying work on a defect that had been closed for
hours**. Nothing caught it, because **a search of the wrong places and a search of the right places
return the SAME EMPTY RESULT** — absence is the one claim whose wrong answer is indistinguishable
from its right one. The runner already knew: a tool not used, not a tool missing. General form:
**an absence claim over a tree that HAS an enumerator must go through the enumerator.**

**Run ONE probe with `--only <name>`, never `node probes/probe-x.js` (`G-163`).** Running a probe
by hand rewrites its tracked capture with pure noise — a wall time, an ephemeral port, a timestamp
— so verification itself dirties files the seat never edited, and three commits swept that noise in
one night. Through the runner the capture is restored byte-identical and the fresh output is kept
outside the repo. Measured on the same probe: by hand leaves it modified, `--only retention` leaves
the tree clean.

The runner exists because nothing enumerated, executed or counted these scripts (`G-141`): two
probes were dead for seven days across two commits, and the last "green" sweep covered 21 of 82
probes while reading complete. Three rules follow, and MUST hold in anything that replaces it:
**the denominator is written before the first probe runs** · **an incomplete run exits `2`, never
`0` or `1`** — so "nothing failed" and "nothing ran" can never look alike, and zero discovered is a
refusal · **`SUITE-COMPLETE` is written last**, so a truncated run is detectable with no exit code
in hand. A verdict comes from a live child-process exit plus a capture refreshed inside that
probe's own run window — **never from the content of a committed `.out`**.

Probes write their `.out` in place, so a run always rewrites captures — but the runner restores
each one byte-identical (mtime included) and keeps the fresh output beside the summary, so **the
working tree is unchanged by default**. Regeneration is the deliberate `--write-captures`. The
summary and captures default to `<tmpdir>/rbtv-probe-suite/` — never into the repo (§ Installation
model's no-runtime-state-in-the-repo rule), and since 7.607 E3 not into the workspace `.rbtv/`
either: a read-only check must not write into the goals workspace as the price of running, so a
dispatch fenced against `.rbtv/**` can run the suite without breaching its own fence. A summary
worth keeping is worth naming — pass `--summary <path>` and it is written verbatim there.

## jobs/ — three scripts ACT on Linux only (author their briefs against the VPS)

`ignite/jobs/` holds the daemon's `fire-tool` detector scripts. Three of them —
`goal-watcher-job.py`, `selfheal-room.py` and `restart-daemon.py` — import
`jobcontain.py`, whose containment ACTIONS exist only on POSIX: `single_instance`'s `fcntl`
double-run lock and `contain`/`child_preexec`'s `resource` memory cap. Since task 7.715 those
imports are LAZY and keyed on `ImportError`, so the three scripts LOAD anywhere — they can be read
and statically checked on the Windows desktop — but they only ACT on Linux.

**Author any brief that EXERCISES their real behaviour against the ignite VPS, not the desktop.**
On a POSIX host the containment is byte-unchanged and REAL; degrading when the modules are absent
is LOUD (one stderr line per function, keyed on the import failing — never on a platform name) and
pinned by `jobs/probes/probe-jobcontain-degrade.py`. The other scripts in the folder
(`recover-room.py`, `agent-tmp-clean.py`) do not import
`jobcontain` and already load anywhere.

## Installation model

Canonical statement of the ignite install model (owner ruling D27, 2026-07-14, `…/phase-7-plan/decisions.md`).

- **Workspace-scoped, not machine-scoped.** A **workspace** is the folder that roots `.rbtv/` (a root dir is usually a git repo, or a branch of one). **"Installed" = this workspace has ONE VPS server configured to run ignite for it** — installing on the VPS is installing in the workspace it serves, never "installed on one machine".
- **Install state lives at `.rbtv/modules/ignite/`** — one folder per module, holding:

  | File | Holds |
  |------|-------|
  | `status.json` | installed flag · version · first-run stamp |
  | `server.json` | the **endpoint record**, a **machine-keyed map**: each machine's install lives under `machines[<hostname>]` — tailnet hostname + IP · gateway port · SSH host/user/port for the tunnel fallback · that machine's per-machine `state_root`. The file travels via git to EVERY machine (see travel split below), so a single flat value would be right on one machine and wrong on every other; the map records each machine's install instead. The CLI selects its own machine's entry when it records a server, else the one entry that does |
  | `settings.json` | current settings |
  | `settings-history.jsonl` | append-only settings history — NEVER rewritten |

  Future per-module files land beside them. First run creates the folder and its files **idempotently**; the installed test is: a valid `server.json` exists.
- **The travel split is load-bearing.** `.rbtv/modules/ignite/` is **COMMITTED** — the installation travels with the repo, so a `git pull` on another machine carries it and that machine's agents find and reach the server via `server.json` (the cross-machine intent). Live per-machine runtime state (the heart store, logs — see § State layout) lives in the machine's own state root, outside the workspace; per-workspace state that stays inside `.rbtv/` but must not travel (`sessions/`, future `goals/`) is **GITIGNORED**. **Credentials NEVER travel in git**: each machine's/sender's token is distributed out-of-band into a gitignored env surface (the workspace `.env` pattern), and SSH private keys never appear in the repo — the tailnet is the preferred client path (no SSH material needed once a device is enrolled); the SSH-tunnel fallback requires the connecting machine's public key authorized on the VPS, done once out-of-band.
- **Registry note:** this model EXTENDS the draft runtime-root component CMP-1 (which sketches flat `config/module*.json`; interface explicitly undesigned) — a documented D8 (iii) divergence/extension feeding task 7.5's reconciliation table and Phase 3. The heart store's home is the per-machine state root (§ State layout — batch-08 item 10 moved it out of `.rbtv/heart/`, CMP-2's former sketch); flag the divergence for registry transcription, never edit the registry from here.

## State layout — the two roots (owner ruling, 2026-07-20, registry-reconciliation batch 08 item 10)

ignite's state lives in exactly TWO roots, split by ONE membership test: **"can the user work with this WITHOUT ignite?"** Yes → per-workspace. No → per-machine.

| Root | Purpose | Holds |
|------|---------|-------|
| **Per-workspace** — `{workspace}/.rbtv/` | Everything a user can work with without the daemon — an interactive session on a machine with no ignite carries the same modules and configs as the server machine | `modules/`, `runtime/`, `sessions/`, future `goals/`, `mirror/` |
| **Per-machine** — the machine's state root (recorded as `state_root` in `server.json`'s machine entry; on the VPS `~/.local/state/rbtv-ignite/`, provisioned by the unit's `StateDirectory=` and passed as `RBTV_IGNITE_DATA_ROOT`) | Ignite-only configs, logs, and runtime | `heart.db`, `logs/`, `prompts/`, `exits/`, `ptys/`, `ticker.log`, `feed.jsonl` |

- **`heart.db` is per-machine, WHOLE.** The membership test cuts through the store (the `jobs` catalogue is user-authorable; `queue`/`jobs_log`/`messages` are runtime) — owner ruled it stays one file, per-machine, at `{state_root}/heart.db`. Accepted consequence: the jobs catalogue is not readable without the daemon.
- **`sessions/` — RETIRED** (`r-seats-only-architecture`, 2026-08-06, completing `r-711-staged-retirement`): the flat `.rbtv/sessions/` launch path is gone; every daemon spawn homes as a seat under its goal (`.rbtv/goals/<goal>/runs/<run>/seats/<seat>/`). A dispatch with no home is a refusal, not a flat dir. Mentions of `sessions/` in the table above are historical layout.
- **Retention** (task 7.13, BUILT — `server/retention.js`, swept at daemon boot and daily) enumerates the per-machine root's artifact classes — `logs/`, `prompts/`, `exits/`, `ticker.log`, `feed.jsonl` — as a POSITIVE enumeration (`ptys/` and `ttyd.log` left it at task 7.29 with the pty module and the ttyd surface; a positive enumeration means a dropped class is never VISITED, so leftovers on a deployed box are now untouched rather than swept): `heart.db` and `.runtime-config/` are never visited by construction. Age-based only, NO size cap; window `RBTV_IGNITE_LOG_RETENTION_DAYS` (default 90, `0` = never, below 7 rejected at boot); read-only on `inspect daemon`'s `config` block.

## Dependencies

`dependencies.txt` at this module's root lists EVERY external dependency the module needs — npm packages AND system-level tools — each with the command that installs it (npm preferred; another manager only when npm cannot provide it). It is maintained AS THE MODULE DEVELOPS: any task that adds, removes, or changes a dependency updates `dependencies.txt` IN THE SAME CHANGE (the docs-in-sync discipline applied to dependencies); reviewers check the manifest reflects the diff. `package.json` remains npm's machine manifest — `dependencies.txt` is the complete human-readable inventory on top, per the human-verifiability requirement (NEED-3). Owner ruling D28, 2026-07-14, `…/phase-7-plan/decisions.md`.

## Terminology

Canonical vocabulary for every spec, task, dispatch, review, and code file of this module (owner ruling D23, 2026-07-14, `…/phase-7-plan/decisions.md`). Specs and code MUST use exactly these words for these things. A term is invented or changed ONLY when necessary, and every invented or changed term is OWNER-APPROVED before it binds; if a term already exists for what you are writing, USE it — never create an alias.

### Session lifecycle states (`jobs_log.status` — the ONE stored lifecycle, closed enum)

| Term | Definition | Where it appears |
|------|------------|------------------|
| `launching` | The job fired and the spawn was initiated; the process is not yet confirmed running. | Store column `jobs_log.status` (heart-store spec DDL, ratified D24 Q2a); spawn spec (replaces its former `spawning` — same meaning, store term wins, D23) |
| `running` | The process is alive; the turn is in progress. | `jobs_log.status`; spawn spec; ticker spec (both used this word already) |
| `done` | The session ended its turn with its own `completion` report, status done. | `jobs_log.status`; `messages.status`; registry `concepts/session.md`, CMP-8 |
| `blocked` | The session reported blocked-on-X and ended its turn; the slot persists. | `jobs_log.status`; `messages.status`; `concepts/session.md`, CMP-8 |
| `failed` | Terminal without a successful completion: tool exit ≠ 0, crash-swept agent, or found dead at the boot orphan rescan. The ONLY exit-status path — D18(4) uniform exit reporting. Absorbs the spawn spec's former `orphaned-dead` (retired, D23): the orphan-discovery detail (found at boot, exit unrecoverable) is DATA on the row/synthetic completion, never a status word. | `jobs_log.status`; `messages.status`; heart-store spec § edge cases; ticker spec § crash sweep |
| `stalled` | Silent past the stall rung (24 ticks) while the process lives; the slot's automatic action is halted; the process is NOT auto-killed. | `jobs_log.status`; ticker spec § Enforce |
| `killed` | Explicitly killed via the kill surface (TERM → grace → KILL, whole process tree). | `jobs_log.status`; spawn spec (both used this word already) |

**Process-level facts are NOT statuses** (genuinely different things — kept distinct, D23): a process being alive or **exited** (ended, exit code observable) is a carrier observation, computed live (`systemctl show` / PID check) or carried in the `pid` / `exit_code` data columns — never a second stored lifecycle. When a process exits, the session's STATUS resolves to `done` / `blocked` / `failed` through completion handling. The spawn spec's former carrier-state enum (`spawning | running | exited | killed | orphaned-dead`) is retired.

### `session_mode` values (closed enum, fixed at creation — D7/D17)

| Term | Definition | Where it appears |
|------|------------|------------------|
| `headless` | Default. One-shot detached session; watchable and killable, resumable at turn boundaries; can NEVER be joined mid-turn. | `queue.session_mode`, `jobs_log.session_mode`; spawn/heart-store/gateway specs |
| `headed` | Opt-in. Runs in a tmux pane in the goal's run-scoped room (task 7.30); a human joins it over SSH. Requires a profile with a `headed:` block AND `RBTV_IGNITE_TMUX_ROOM` set on the unit — typed rejection otherwise, at queue time AND spawn time. Ran inside a server-owned pty with a browser JOIN/TAKE-OVER surface until task 7.29 retired that module. | Same columns; spawn spec Design 2 |

### Core nouns

| Term | Definition | Where it appears |
|------|------------|------------------|
| job | A deterministic command (function + arguments), dry-run-validated at queue time; NO LLM in the path. | Registry `concepts/job.md`; `jobs` catalogue table |
| queue | The control-plane store of PENDING jobs only; the server core is its sole writer. | Registry `concepts/queue.md`; `queue` table |
| execution | One fired run of a job. One `jobs_log` row = one execution = one session record (D16 folded model). | Heart-store spec (D16); `jobs_log` |
| session | A running executor process started by the server core on the launch spec its seat is CAST to; watchable live, survives disconnects, controllable at turn boundaries, killable at any time (D7 operational definition; complements registry `concepts/session.md`, Session = Executor + Trigger). Runs exactly ONE turn, ends on its own report. | decisions.md D7; every spec |
| worker | The spawned executor process a session runs (informal; the registry concept is `executor` = agent \| tool). Names the transient units: `rbtv-worker-<session-id>`. | Spawn spec; VPS notes §4 |
| seat-slot | The persistent work slot a chain of one-turn sessions occupies; the slot persists, sessions are cattle. v1 carries it implicitly as a turn chain (no slot table). | CMP-11; ticker spec § slot substrate |
| turn chain | Successive executions sharing ONE chain-stable thread, each linked to its predecessor via `jobs_log.parent_exec_id` (NULL = the chain's first execution) — ratified D24 Q3a. | Ticker spec; heart-store DDL |
| thread | The message-thread id a whole chain shares: `exec-<exec_id of the chain's FIRST execution>`, carried UNCHANGED across recycles (chain-stable, D24 Q3a). | `messages.thread`; ticker spec |
| tick | One pass of the ticker engine's fixed 7-phase loop (default cadence 10 s). | Registry CMP-11; `ticks` table; ticker spec |
| ticker engine | THE one runtime engine that makes the queue launch due jobs — deliberately singular; "heartbeat" is RETIRED and never names the engine. | Registry `concepts/ticker-engine.md`; ticker spec |
| launch spec | A config-pinned command-template set (exec/resume/caps/sandbox/effort ladder), keyed by **(harness, model)** in `launch-specs:`. NO caller anywhere selects one: a seat's CAST resolves it at spawn time, and callers never inject flags (DEC-1 R3). Successor to the RETIRED term "launch profile" (owner ruling `#d-abolition-terminology`, 2026-08-12). | Spawn spec Design 1; server config `launch-specs:` |
| cast | The assignment of one executor (harness · model · effort) to one seat. A bindings sheet is composed of casts, and a cast is what resolves a launch spec. NOUN only — never a verb (`PRIN-7`/`PRIN-10`). | `.rbtv/config/modules/{module}/{component}/bindings/{code}.json`; `capabilities/bindings/` |
| sender | An authenticated identity (`kind: owner \| agent \| bridge`) presenting a per-sender token at the gateway; the resolved sender-id rides every forwarded request and lands in the audit columns. | D15; gateway spec; `messages.sender` |
| `enqueued_by` | CANONICAL column/argument name for "the authenticated sender who caused this run" — owner-ruled, 2026-07-14, decisions.md D26 (unifies the store columns' name across the store, spawn, and session-row surfaces; no synonym alias). | D26; `queue.enqueued_by`, `jobs_log.enqueued_by`; spawn spec `spawn()` signature |
| completion | The typed message that ends a turn, carrying status `done` \| `blocked` \| `failed` (report-failed is a completion with failed status — never a type of its own). | Registry CMP-8; `messages` table; ticker spec |
| `session-killed` | The audit record `kill-session` appends after a kill succeeds — attribution only (WHO killed WHICH session WHEN), never a payload. The one record kind this module still WRITES to a session's audit file. ⚠ A READER of that file may still meet three retired kinds on disk — `keys-accepted`, `screen-read`, `screen-read-summary` — written before task 7.29 retired the two pty intents; no code writes them now, and any tool that parses the file must still understand them. | Per-session audit file; `server/internal-api/keys-audit.js`, `server/internal-api/dispatch.js`; `probe-keys-audit.js` |

Retired words — MUST NOT be used for this module: `heartbeat` (the engine is the ticker engine), `spawning` (use `launching`), `orphaned-dead` (use `failed` + discovery data), `requested_by` (use `enqueued_by` — owner-ruled 2026-07-14, decisions.md D26), **`launch profile`** (use `launch spec` — owner-ruled 2026-08-12, `#d-abolition-terminology`; the NAME layer that term implied is abolished outright by `#d-abolish-profile-names`, so the word now names nothing that exists). RETIRED SURFACES (task 7.29, the words stay legible for history but name nothing live): `send-to-session`, `capture-session-screen`, the `ignite send`/`ignite screen` wrappers, the web terminal and its ttyd surface, the in-unit dtach holder, the pty bridge — a headed session is a tmux pane and SSH is the human trust boundary.
