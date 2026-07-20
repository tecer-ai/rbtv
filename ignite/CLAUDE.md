# ignite/ — the ignite daemon

Source of the **ignite daemon**: ONE Node.js service (one systemd unit) with a hard internal module boundary between the **server core** (owns `.rbtv/` runtime state; sole queue writer; ticker engine + spawn machinery) and the **gateway** (sender auth + client CLI; no queue handle, no spawn). Repo conventions for this folder (deployment model, no hardcoded paths, relocatable subtree, branch discipline): root `CLAUDE.md` § "ignite/ — Runnable Service Code (convention)".

Developed on branch `ignite/core-daemon`; design authority: the build specs under `1-projects/rbtv-sb-merge-refactor-core-build/build/phase-7-plan/specs/` (heart-store · ticker-engine · spawn-profiles · internal-api-contract · gateway-cli), governed by the `system-definition/` registry.

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
- **`sessions/` is per-workspace.** Stays at `.rbtv/sessions/` (consistent with the seat-folder target model). Accepted tradeoff: worker-writable areas remain inside the workspace.
- **Retention** (task 7.13) enumerates the per-machine root's artifact classes — `logs/`, `prompts/`, `exits/`, `ptys/`, `ticker.log`, `feed.jsonl` — and MUST explicitly exclude `heart.db`, which shares that root.

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
| `headed` | Opt-in. Runs inside a server-owned pty; JOIN (view live) and TAKE OVER (keyboard in) become possible. Requires a profile with a `headed:` block; typed rejection otherwise, at queue time AND spawn time. | Same columns; spawn spec Design 2; Batch 6 consumes |

### Core nouns

| Term | Definition | Where it appears |
|------|------------|------------------|
| job | A deterministic command (function + arguments), dry-run-validated at queue time; NO LLM in the path. | Registry `concepts/job.md`; `jobs` catalogue table |
| queue | The control-plane store of PENDING jobs only; the server core is its sole writer. | Registry `concepts/queue.md`; `queue` table |
| execution | One fired run of a job. One `jobs_log` row = one execution = one session record (D16 folded model). | Heart-store spec (D16); `jobs_log` |
| session | A running executor process started by the server core via a named launch profile; watchable live, survives disconnects, controllable at turn boundaries, killable at any time (D7 operational definition; complements registry `concepts/session.md`, Session = Executor + Trigger). Runs exactly ONE turn, ends on its own report. | decisions.md D7; every spec |
| worker | The spawned executor process a session runs (informal; the registry concept is `executor` = agent \| tool). Names the transient units: `rbtv-worker-<session-id>`. | Spawn spec; VPS notes §4 |
| seat-slot | The persistent work slot a chain of one-turn sessions occupies; the slot persists, sessions are cattle. v1 carries it implicitly as a turn chain (no slot table). | CMP-11; ticker spec § slot substrate |
| turn chain | Successive executions sharing ONE chain-stable thread, each linked to its predecessor via `jobs_log.parent_exec_id` (NULL = the chain's first execution) — ratified D24 Q3a. | Ticker spec; heart-store DDL |
| thread | The message-thread id a whole chain shares: `exec-<exec_id of the chain's FIRST execution>`, carried UNCHANGED across recycles (chain-stable, D24 Q3a). | `messages.thread`; ticker spec |
| tick | One pass of the ticker engine's fixed 7-phase loop (default cadence 10 s). | Registry CMP-11; `ticks` table; ticker spec |
| ticker engine | THE one runtime engine that makes the queue launch due jobs — deliberately singular; "heartbeat" is RETIRED and never names the engine. | Registry `concepts/ticker-engine.md`; ticker spec |
| launch profile | A named, config-pinned command-template set (exec/resume/caps/sandbox); the ONLY unit a caller can select, by NAME — callers never inject flags (DEC-1 R3). | Spawn spec Design 1; server config `profiles:` |
| sender | An authenticated identity (`kind: owner \| agent \| bridge`) presenting a per-sender token at the gateway; the resolved sender-id rides every forwarded request and lands in the audit columns. | D15; gateway spec; `messages.sender` |
| `enqueued_by` | CANONICAL column/argument name for "the authenticated sender who caused this run" — owner-ruled, 2026-07-14, decisions.md D26 (unifies the store columns' name across the store, spawn, and session-row surfaces; no synonym alias). | D26; `queue.enqueued_by`, `jobs_log.enqueued_by`; spawn spec `spawn()` signature |
| completion | The typed message that ends a turn, carrying status `done` \| `blocked` \| `failed` (report-failed is a completion with failed status — never a sixth type). | Registry CMP-8; `messages` table; ticker spec |

Retired words — MUST NOT be used for this module: `heartbeat` (the engine is the ticker engine), `spawning` (use `launching`), `orphaned-dead` (use `failed` + discovery data), `requested_by` (use `enqueued_by` — owner-ruled 2026-07-14, decisions.md D26).
