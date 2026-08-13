# Ignite

## Purpose

The runtime layer of RBTV. Two parts share the module because they are two faces of the same substrate — agents doing coordinated work over time:

1. **The ignite daemon** (`ignite/` service code) — ONE Node.js service (server core + gateway) that makes a workspace's job queue launch due jobs on a runtime host. It is **deployed, never installed**: `install.py` does not copy it into any workspace's `.claude/`. Its conventions, install model, state layout, and terminology live in `ignite/CLAUDE.md` and the repo root `CLAUDE.md` § "ignite/ — Runnable Service Code".
2. **The team-kit** (`ignite/team-kit/`) — reusable mechanics for running a coordinated parallel multi-agent team in tmux: one pane per seat, verified seat identities, a typed append-only message log with threading and retractions, bounded reads, staged launches with per-seat harness/model/effort profiles, a pre-launch worker-mirror refresh so a codex/opencode seat never boots onto rules its gitignored `AGENTS.md`/`.agents/` mirror left stale, closer seats (the watcher seat is retired — detection is the deterministic watch layer's: team-monitor + goal-watcher-job), and guards against the failure modes the runs measured (a re-check-in cannot split a seat across two live panes; a seat parked on an approval prompt is detected and never woken into its modal). Proven over four runs in the origin workspace (kg-edges-visualization-improvements → kg-views-rebuild → the tv-ux-review 28-seat batch test → the coordinate CLI redesign, 2026-07-23→25) before promotion (2026-07-26).

## Components

### `rbtv-team-kit` (skill)

- **What**: Thin loader into `ignite/team-kit/` — the kit's hard rules (`CLAUDE.md`), the run-setup guide (`team-kit.md` § Starting a new run), and the protocol every run agent follows (`protocol.md`). The kit's engine is `coord.py` (the `coordinate` CLI where symlinked): `checkin` · `status` · `read` · `send`/`escalate` · `pending` · `checkout` for every seat; `launch`/`session-open` · `close` · `close-seat` (with its lifecycle siblings `reap` · `kill-pane` · `relaunch-pane` · `terminate-pid` · `finish-goal` · `advance-state` · `execution` · `attest-exit` · `rule-disposition` · `rule-relaunch` · `rule-guard`) · `approve` · `panel` · `owner` · `add-to-group`/`remove-from-group` for the leader; and an `other` group — `workers` · `descriptors` · `ready-seats` · `gateway-status` · `create-group` · `export-transcript` · `depart` · `gates`. `python3 coord.py selftest` verifies the mechanics. (`coord.py`'s own `HELP_EPILOG` is that grouping's source of truth; the only registered command absent from it is the deliberately hidden `lifecycle-exec`, declared in `HIDDEN_COMMANDS`.) All run state lives in the run package (`--package DIR` / `--run TAG` / cwd walk-up), never in the kit.
- **When to use**: Starting a new team run, building a run package, adding seats, or joining/operating an existing run.
- **How to invoke**: The `rbtv-team-kit` skill, or read `{rbtv_path}/ignite/team-kit/team-kit.md` directly.
- **Kit contents**: `coord.py` (coordination CLI; `launch` pre-flight-validates every seat's harness/model before any pane opens, so one bad slug refuses the launch instead of stalling a whole wave at boot; `launch` also ARMS `tmux pipe-pane` transcript capture at PANE BIRTH (7.31) — the log lands workspace-side under the goals tree at `<goal>/seats/<seat>/sessions/<session-id>/transcript.log`, and `sessions.csv`'s `recorded` column, reserved-and-always-empty until now, carries that path from the moment the row is written. ⚠ It is the SUBSTRATE-level backup and never the primary record: harness-native transcripts stay primary. Never capture-on-CLOSE — tmux scrollback dies with the tmux server, so a close-time capture returns nothing exactly when the backup matters. A blank `recorded` still reads as "nothing was recorded": a pre-7.31 row, or a boot whose capture failed to arm; `checkin` stamps the session's `checkin` time on its open `sessions.csv` row and prints the seat its own identity — session-id, native id and the per-session scratchpad `{seat folder}/sessions/{session-id}/` that every kit-opened session gets, `UNRESOLVED` per field when an id is missing) · `nudge.py` (+ `test_nudge.py` — deterministic nudge loop: fires a message at a NAMED SEAT every `--interval` seconds so a seat owing a recurring sweep cannot go passive, re-resolving the recipient's pane from the roster on every tick and appending a monotonic-seq heartbeat that `nudge.py check` reads back as `GAP`/`DUPLICATE`/`STALE` from the file alone; one loop per heartbeat, `flock`-enforced. NOT the daemon's ticker engine, and POSIX-only) · `protocol.md` (agent protocol — every seat) · `roles.md` + `briefing-authoring.md` (its two role-scoped siblings, split out 2026-07-28: the role catalogue, read by a seat holding a special role or a non-claude harness; the briefing-authoring rules, read only by whoever authors briefings) · `team-kit.md` (index + run setup) · `briefing-template.md` (seat briefings) · `closer-prompt.md` (seat-close flow) · `system-design.md` (designer-only rationale) · `starter-set/` (`conduct.md` + `CLAUDE.md` + `budget.json` — the OWNER-APPROVED goal-generic base texts a created run package is born with, `d-owner-starter-set-approved-0808`; BYTE-COPIED by `scaffold-seats --conduct/--claude-md/--budget-json`, which refuses `create-inputs-missing` without them; those three are the WHOLE starter set — `addressable.csv` was DELETED 7.696 and no longer ships, because it was a frozen run-layer register and the run layer was abolished 2026-08-09; `derive_addressable_register` computes the depth against the actual layout instead. The register itself lives on as a `scaffold-seats` creation surface (7.546/7.569): it makes the standing owner door a legal ROLE address in a run that rosters no authority seat, so `conduct.md`'s escalation clause resolves: tier 1 parks the question in the goal's `doubts.md` (the durable RECORD, kept — never retired), tier 2 sends it `--to master` where the chat bridge's bus ferry carries it to the owner's DM, tier 3 stops the dependent work. `addressable.csv` IS a `scaffold-seats` creation input since 7.569, and an OPTIONAL one deliberately: `--addressable` byte-copies a caller-supplied register when given, otherwise a bootstrap creation DERIVES the rows from the standing-seat homes whose own `seat.md` declares `addressable: non-member`, and creates nothing when none does — so no caller breaks for want of the flag, which a REQUIRED 4th `CREATION_INPUTS` tuple would have done to every caller including the armed `goal-creation-request` loop. ⚠ NOT `conduct-template.md`: that is an unfilled FORM a run's conduct-author instantiates, and `--conduct` copies bytes rather than filling slots, so pointing the scaffold at it would give a run a rulebook whose law reads `{{INSTANTIATE}}`) · legacy dashboard trio (`tmux-overview`, `overview-compact.py`, `provider-usage.py` — superseded by the `teamview` CLI in orchestration).

### The ignite daemon (service code — not an installable component)

See `ignite/CLAUDE.md`. Client CLI: `ignite/cli/` (`ignite add-job` / `remove-job` / `inspect`).

### `ignite/jobs/` — job scripts the daemon fires as `fire-tool` jobs

Deterministic scripts the daemon's ticker execs from a catalogue entry's `argv` verbatim
(`server/ticker/ticker.js` `runToolLikeExec`, caps `{}` / sandbox `{}` — a fired tool is
unsandboxed and uncapped, so containment lives INSIDE each script via `jobcontain.py`). Daemon
service code: **deployed, never installed** — no install-manifest entry. Directory front door:
`ignite/jobs/README.md`.

Inventory enumerated 2026-08-10 from `ls ignite/jobs/` at the repo root
(cwd `C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv`, branch `ignite/core-daemon`,
HEAD `65a9970f`). Each purpose line below is the file's own module docstring, first sentence,
QUOTED verbatim:

| File | Docstring (quoted) |
|------|--------------------|
| `edge-runner-job.py` | "edge-runner-job — CMP-25's pass: verify a finished seat's done contract and mark it `done` or `failed` (task 7.123 / M4-08), evaluate readiness of every row whose `after` names it (task 7.124 / M4-09), enqueue each LAUNCH CANDIDATE as a daemon job seeded with its predecessors' declared outputs (task 7.125 / M4-10), and exit (task C1 — see below: the exit is step 5 and it is the DAEMON that reads it)." |
| `goal-state-job.py` | "goal-state-job — recompute every seat's GOAL STATE from disk, on demand, per seat (task 7.127 / M4-12, from 7.56 item (b))." |
| `goal-watcher-job.py` | "goal-watcher-job — the ENFORCEMENT half of R24's observation architecture (task 7.32)." Per `ignite/jobs/README.md`: DARK today, no live catalogue entry. |
| `jobcontain.py` | "Self-containment for `fire-tool` job scripts (issues.md G-30)." Library, not a job — self-cap, wall clock, single-instance lock. |
| `recover-room.py` | "Re-create a dead team-kit room and boot a recovery seat into it (task 7.71)." The recovery argv `selfheal-room.py` runs. |
| `restart-daemon.py` | "Restart a systemd --user unit as a `fire-tool` job (ruling `r-restart-daemon-job`)." |
| `selfheal-room.py` | "Dead-room detector + recovery relaunch (task 7.71, owner ruling `r-selfheal-job`)." |
| `README.md` | The directory's own front door — the fire-tool job model plus a judge/act table for the self-heal detectors. |
| `probes/` | 14 probe scripts guarding this directory's jobs: `probe-dead-room-sensor-session.py`, `probe-detach-env.py`, `probe-goal-watcher-delivery-retry.py`, `probe-goal-watcher-door-exemption.py`, `probe-goal-watcher-ghostrow-debounce.py`, `probe-goal-watcher-homings.py`, `probe-goal-watcher-revival.py`, `probe-goal-watcher-selftest.py`, `probe-goal-watcher-worktree-watch-start.py`, `probe-headless-retention-unknown.py`, `probe-jobcontain-degrade.py`, `probe-team-monitor-activity-fallback.py`, `probe-team-monitor-approval-title.py`, `probe-team-monitor-homings.py`. Two landed with task 7.35: `probe-goal-watcher-homings.py` (the declared-cap census, the never-to-its-own-seat flag routing, and the revival attempt ladder — all re-homed from the retired `watch.py`) and `probe-team-monitor-homings.py` (the /tmp uid-quota canary and the ignorance escalation's bus half, re-homed into the surviving sensor). Three landed later, each with its fix: `probe-headless-retention-unknown.py` (7.556 — the live-worker count reads UNKNOWN once a still-running headless row ages out of the bounded view), `probe-goal-watcher-worktree-watch-start.py` (7.557 — the un-cleaned-worktree report fires ONCE at a healthy watch start, not only from the refusal branch), `probe-jobcontain-degrade.py` (7.715 — `jobcontain.py`'s POSIX containment is real on Linux and degrades LOUD, never silent, where `fcntl`/`resource` are absent). |
| `audit/` | 2 audit notes: `probe-record-edge-runner-enqueue-builder.md`, `trace-field-audit.md`. |

### Capabilities

- **`daemon-operator`** (`ignite/capabilities/daemon-operator/`) — the ignite OPERATOR surface:
  local systemd USER unit ops that work precisely when the daemon is DOWN. Contract in
  `daemon-operator.md`.
- **`ticker-settings`** (`ignite/capabilities/ticker-settings/`) — the ignite CADENCE-EDIT operator
  surface (task 7.66), reached as `rbtv ignite ticker`: `show` · `set-interval <dur> [--restart]` ·
  `history` · `selftest`. Like `daemon-operator` it presents no token, never crosses the gateway and
  works with the daemon DOWN — which is exactly when a cadence that wedged the box needs changing.
  The value is MACHINE-KEYED (`.rbtv/modules/ignite/settings.json`
  `machines.<hostname>.ticker.tick_interval_ms`, one appended `settings-history.jsonl` line per
  change) because that tree is committed and travels to every machine. `<dur>` requires a unit —
  a bare `15` is refused. Floor/ceiling are enforced TWICE, fail-closed at both (this surface, exit
  3; and daemon boot), because a surface-only bound is walked around with a text editor. Live
  reload is REJECTED, not unimplemented — write-then-restart composes two mechanisms that exist.
  Contract in `ticker-settings.md`.
- **`goals-tree`** (`ignite/capabilities/goals-tree/`) — the goals-tree machinery
  (`scaffold`/`reindex`/`lint`/`materialize`/`lane`/`pause`/`resume`/`dag`/`add-seat`/`retry-threshold`/`teardown`).
  `teardown` reclaims a goal's JOB-CATALOGUE rows so its NAME is registerable again (issue
  `IPH-27`): it removes their pending queue rows then `deregister-job --purge`es each one, composing
  the ids from the goal's own `taskforce.csv` — so run it BEFORE deleting the folder, which it never
  touches. ⚠ It is the ONLY verb in this capability that needs the daemon UP (the catalogue is in
  `heart.db`, served only by the gateway); it refuses typed rather than half-working.
  `retry-threshold` sets the consecutive-FAIL bar the dod-judge escalates at — per goal, with a
  per-milestone override column in `milestones.csv`, absent everywhere 2 (issue `IPH-11`).
  The last four GROW A LIVE GOAL'S SEAT ROSTER (issue `S-33`): `pause` rewrites the lane marker to
  `paused ` + its previous text verbatim and `resume` strips exactly that prefix back — no reader
  changed, because both lane readers already resolve any first token that is not `daemon` to
  `console`; ⚠ it bounds SEEDING, never a session already running. `dag` is the read-only one-shot
  graph view (every row's predecessors through the after grammar + its state derived from
  `executions.csv`). `add-seat` gates (paused · quiescent · no `--before` seat has run · no attached
  run · bindings cover the seat · no complex cell on a stashed daemon lane), mints through
  `team-kit/materialize-seats.py`, then splices the seat into the after-graph in ONE atomic write
  behind a canonical-form guard — every line but the re-parented ones is byte-unchanged. Every
  refusal carries a CODE, machine-readable under `--json`. `lane` is the DAEMON'S PICKUP BUTTON (owner
  ruling `d-daemon-lane-button`, 2026-08-10): it writes one word into `<goal>/execution-lane` saying
  which lane currently runs the goal, and the daemon's watch pass (`ignite/engine/lane-watch.js`,
  fired by the daemon loop before every tick) seeds the goals assigned `daemon` through
  `engine.seedGoal`. ⚠ Since task 7.789 that pass is also the SECOND caller of the C3 channel-ensure
  decision (`server/ticker/goal-channel-start.js#channelEnsureDecision`, performed by
  `ticker.js#ensureGoalChannel`): on the pass that FIRST adopts a goal, an `interactive` one gets
  its Slack channel — the queued `start-workflow` branch was the only caller before, so a
  daemon-lane goal had none and its seats' to-owner messages had nowhere to land. One decision, two
  callers, memoized once per goal. Absent means `console` — the daemon adopts only what it was explicitly given;
  `--set daemon` REFUSES a goal with any seat that declares no harness+model cast, naming them
  (the refusal names them); flipping it mid-goal is the supported act. Contract in
  `tool/README.md`; the lane half also in `capabilities/attached-execution/attached-execution.md`
  § The daemon lane's goal pickup.
- **`attached-execution`** (`ignite/capabilities/attached-execution/`) — the ATTACHED lane: the
  **`rbtv run`** verb (`rbtv run <goal-folder>` — ⚠ `--profile` RETIRED 2026-08-12; it was the FALLBACK for
  seats that declare no cast, and is required only when the goal has one; entry point
  `tool/rbtv-execution`, delegated from the TOP-LEVEL `rbtv` CLI — never `rbtv ignite`). Owner
  ruling `d-attached-run-embedded-engine`: ONE implementation of workflow advancement, TWO
  attachments — the same engine (`ignite/engine/`) the daemon runs, attached to the calling
  terminal instead of a systemd unit; store at `<goal-folder>/heart.db`, dies with the terminal,
  recovery is the owner re-running the verb. Carries `--status` (the read-only orientation
  surface — derived-only, never creates the store, works before a first run) and the foreground
  carrier (a held human-interactive seat runs as a foreground child of the runner; the tick loop
  blocks while it runs). Exit codes `0` complete or tick-bound · `1` refused or cannot advance
  (`seat-failed`) · `3` a worker asked a question and the run handed it back. Contract in
  `attached-execution.md`.
- **`goal-creation-request`** (`ignite/capabilities/goal-creation-request/`) — the entry a
  goal-creation request arrives at: `validate`, `handle` (create → launch), and
  `scaffold-and-queue`, the DAEMON-EXECUTED verb (task C2) that drains a staged request inbox and
  scaffolds each goal. That verb exists because a Slack-caged channel master measurably cannot
  create a goal directory but can write its own seat folder, so the payload is file-staged and only
  the trigger crosses the gateway. Registered in `config/spawn-profiles.yaml` under
  `tools: goal-creation-request` and landed **dark** — arming is two gated acts in a fixed order.
  ⚠ **`execution-lane` IS A REQUIRED REQUEST FIELD** (task 7.777, owner-ruled 2026-08-12), with
  `launch-profile` optional beside it. Creation REFUSES a request that names no lane — reject-set
  members `P5` (absent) and `V8` (not in `{daemon, console}`) — and there is NO derivation ladder,
  unlike `execution-mode`'s three tiers: the owner ruled the assignment EXPLICIT. The DAEMON writes
  the marker, forwarding `goal_cli.py scaffold --lane` in the same process that writes `goal.md`,
  and that routing is the FIX for a measured operator defect: the channel master's `goals-write`
  cage grant is a SPAWN-TIME SNAPSHOT, so a goal created during a sitting could never be written by
  that same sitting (`EROFS`). Through the request the master needs no goal-folder access at all.
  ⚠ **THE `start-workflow` DOOR IS DELETED** (task 7.778, same ruling). `scaffold-and-queue` no
  longer mints a `<goal>-workflow-start` job or queues it `--delay-seconds` out; the
  `tool/workflow_launcher.py` that row fired, the `workflows: planning:` registry entry that named
  it, and the whole `goal-launch-delay` capability are gone with it. What opens the entry seat now
  is the LANE: the daemon's watch pass reads `<goal>/execution-lane` every cadence and seeds a
  `daemon` goal; a `console` goal opens when a human types `rbtv run`. The `start-workflow` ACTION
  TYPE survives — it is a generic dispatch category with live consumers
  (`server/ticker/one-live-run.js`, `server/ticker/goal-channel-start.js`). The workflow every master-created goal starts in is RULED
  (task C5, `d-owner-q10-launcher-0808`): `planning` / entry seat `plan-interviewer`, the meta
  component `.rbtv/mirror/meta/planning/`. *(Issue C-2, 2026-08-10: the ruling originally landed
  against `planning-deprecated` / `elicitator` — named `planning`/`planner-workflow` when ruled,
  renamed by R11, vault `01f60de16`, task 7.598. That component was deleted and every fired
  creation refused `workflow-unknown`; the values were repointed at the 16-seat planning
  rewrite.)* The goal is born WITH its package materialized through the ruled name
  `scaffold-seats` — GOAL-DIRECT since 7.607, the package IS the goal folder and there is no
  `runs/run-N` compartment. **Instance-ordinal seat naming (7.545)** lives in that same script as
  the ONE place a nested-instance name is spelled: `compose_seat_name` / `parse_instance_seat_name`
  / `next_instance_ordinal` / `read_workflow_prefix`. The shape is owner-ruled
  (`d-owner-7545-7551-design-rulings-0808` criterion 1, amending
  `r-branch-seat-name-carries-the-instance-ordinal`): a nested workflow's seats are ORDINARY seats
  of the parent goal, named `<four-letters>-<seat>` for the FIRST instance and
  `<four-letters>-<n>-<seat>` from the SECOND onward — the ordinal is absent on the first, so two
  name shapes exist and every reader handles both, and no seat is ever renamed. The four letters
  are DECLARED as `four-letters:` in the workflow folder's `workflow.md` frontmatter (typed refusal
  on absence — derivation collides on real workflow ids) and are required only where an instance is
  composed, so existing manifests need no edit. Top-level seats keep BARE names. ⚠ A composed name
  is a DISK name only — folder, `taskforce.csv` seat cell, `after` member, descriptor `seat:` — and
  never a `seats.csv` or bindings key, which stay the catalog id. ⚠ Nothing COMPOSES one yet: the
  nested-workflow materialization path went with the branch folder in 7.607 and the launch half is
  still a typed refusal in `jobs/edge-runner-job.py`; the naming ships as the surface re-founding
  will consume.
  The ruled bare name now
  RESOLVES under the daemon: a fired tool used to inherit the systemd `--user` MANAGER's PATH, which
  carries no `~/.local/bin`, so `scaffold-seats` exited 127 and every daemon-fired creation refused
  after scaffolding — fixed at the CARRIER for the whole class, not at this call site
  (`d-owner-f1-carrier-env-0808`; `server/spawn/carrier.js` `toolExecEnv`). Landed is still not
  live, and that covers BOTH halves — the config file is boot-read AND the carrier fix is daemon
  code, so a RUNNING daemon has neither until the next restart; the PATH class is retired in the
  tree, not yet in the process. Arming remains the two gated acts. Contract in
  `goal-creation-request.md`. The carrier fix had ONE leak downstream of it, closed by task 7.551:
  `jobs/jobcontain.py` `detach_argv` opens a SECOND `systemd-run --user` so a recovery outlives the
  job that started it, and that inner hop went back through the MANAGER environment — so the
  composed PATH stopped at it and the detached process's descendants (`recover-room.py` →
  `coord.py`, which boots the harness by the bare name `claude`) were back on the manager PATH. It
  now FORWARDS `os.environ["PATH"]` — forwarded, never re-derived, so the composer stays singular
  (PRIN-11); guarded by `jobs/probes/probe-detach-env.py`.
- **`master-profile`** (`ignite/capabilities/master-profile/`) — the channel master choosing its OWN
  harness, model AND effort rung (issue C-1, same ruling). ⚠ **RETARGETED 2026-08-12.** The knob was
  `master_profile` in `.rbtv/config/chat-bridge-config.json` until the launch-cast unification
  (ruling D2) deleted that key's readers; it is now the master's own CASTING SHEET —
  `.rbtv/config/modules/meta/master-agent/bindings/channel-master.json` — written through
  `bindings.cast_seat`, the same validator and the same write `rbtv-bindings set` uses, and followed
  by a `materialize-seats.py --repass` that re-renders `seat.md` from it. Per
  `d-master-is-cast-like-any-other-seat` the SEAT governs; this CLI re-casts the seat. The requested
  caller names harness + model DIRECTLY (no profile NAME since 2026-08-12) and both are validated against the LIVE
  CASTABLE set at BOTH halves (narrower than `launch-specs:` — `coord.py#validate_seat` must accept the
  pair, so `test-sleep` is refused); an unknown SEAT is refused rather than created. ⚠ **Nothing is
  restarted and the requesting sitting survives** — a casting sheet is not boot-read: `spawn.js`
  reads `seat.md` per launch and `live-sessions.js` reaps a warm session whose conversation names a
  different profile, so the switch lands on the owner's NEXT message. The split into request/apply
  survives for ONE reason only — `--repass` writes under `.rbtv/goals/`, which every seat cage
  refuses to grant writably. ⚠ **`--effort` IS live** (the 2026-08-11 lane build): a rung 1..N on the
  TARGET profile's own ladder, stored in the sheet as the harness's own level string. Contract in
  `master-profile.md`.
- **`bindings`** (`ignite/capabilities/bindings/`) — the CASTING SHEET a workflow is run through
  (owner-ruled 2026-08-10): which harness, model and effort each seat gets. A workflow is the
  program, a **taskforce** is its running instance, and the bindings file is what casts one into the
  other; `team-kit/materialize-seats.py --bindings` is its ONE consumer. ⚠ **A cast is now HONOURED
  AT LAUNCH** (ruling D19, 2026-08-11): `launch-profiles/catalog.js` maps a seat's declared
  `(harness, model)` to the launch spec that runs it — task 7.54's catalog half, built — and
  `server/spawn/spawn.js#profileForSeatCast` applies it at the one point every lane's launch passes
  through, so a seat runs what its `seat.md` casts it as whether the daemon lane, the attached lane
  or a Slack revival dispatched it. Before it, every lane launched a caller-named profile and a seat
  cast as a frontier model silently ran the deployment's chat model. It shares ONE derivation law
  with this capability's own `catalog` verb (`bindings.py#catalog`) — `probe-binding-catalog`
  compares the two row for row so they cannot drift; an unmappable or ambiguous cast is a typed
  refusal, never a fallback; a seat declaring no cast (the channel master's `open_binding`) is
  untouched. Five verbs — `catalog`
  (every harness+model this workspace can spawn, each effort dial NUMBERED), `inspect` (every
  manifest seat with its definition file, staffing hints and casting state), `scaffold`
  (create-only), `set` (one seat), `set-many` (N seats of ONE workflow from a JSON file in one
  validated call — ALL-OR-NOTHING: each seat goes through `set`'s own path with `dry_run`, and the
  sheet is opened only if every one passes, so a batch with a bad seat leaves it byte-identical and
  names every offending seat's reason. The casting flow it serves: inspect → the owner decides →
  one batch call). ⚠ **NOT the two-part shape of the two capabilities above, and that is
  measured, not style**: the bindings tree sits in the channel master's `rw-paths` and NOTHING
  boot-reads it, so every verb is a plain direct file write — no staged inbox, no `enqueue-job`
  trigger, no restart. ⚠ **`catalog` IS the validator** `set` enforces: one derivation, two
  consumers, so the surface an agent reads and the surface that refuses it cannot disagree. It is
  composed from `launch-specs:` in `config/spawn-profiles.yaml` (which `r-seats-only-architecture` makes
  the workspace's spawnable set) plus each profile's own `effort:` block for whether a dial exists,
  and gated by `coord.py#validate_seat` — the predicate `materialize-seats.py`'s F6 gate imports, so
  a pair this tool offers can never be one materialize then refuses. The effort NUMBER indexes the
  HARNESS's native ladder (claude: 1=low … 5=max) and the file stores the harness's own string; the
  per-profile `effort.values` table is a different object (the daemon lane's four abstract levels)
  and using it would make `xhigh` unspellable. One file per WORKFLOW at
  `.rbtv/config/modules/{module}/{component}/bindings/{code}.json` — `{code}` is the workflow's
  code, the seat-id prefix its manifest rows carry, derived and never typed. Deployment config,
  never the mirror — and ONE INSTANCE of the general config convention
  (`.rbtv/config/modules/<module>/<component>/…`, stated in `team-kit/starter-set/conduct.md` § 11).
  ⚠ The pre-D15 `.rbtv/config/bindings/…` spelling still READS, with a WARN naming the new path, so
  an un-migrated deployment breaks loudly rather than silently. Contract in `bindings.md`.
- **Etiquette reaches every user-facing seat by materialization, not by nine remembered edits**
  (owner rulings D11 + D15, 2026-08-10). A seat whose prompt definition declares
  `human-interactive:` gets extra SKILL parts folded into its `exposes:` set by
  `team-kit/materialize-seats.py` as if it had declared them, so the injected reference passes the
  same resolution / method / entry-point gates an authored one does. ⚠ **WHICH parts is instance
  policy and appears nowhere in the shared source** — the list is a JSON array of part refs (the
  `exposes:` grammar) at the config convention's address for this component,
  `.rbtv/config/modules/ignite/team-kit/interactive-exposes.json`. No such file, no `.rbtv/config`,
  or an empty list injects NOTHING and renders byte-identically to before; a listed part that does
  not resolve takes the ordinary `exposes-ref-dangling` refusal at generation time.
- **What a caged seat may write in its own goal folder, and the gate that proves it** (owner rulings
  D2/D9/D13, 2026-08-10). The goal folder is read-only to a seat except for three carves in
  `config/spawn-profiles.yaml`'s `cage.SeatBinds`: the seat's own folder, the **five
  write-if-something ledgers** (`issues.md` · `decisions.md` · `doubts.md` · `gotchas.md` ·
  `ideas.md` — goal_cli's `WRITE_IF_SOMETHING`, so a seat that hits a tooling gap can actually file
  it where the router sends it), and the ONE path the seat's role produces, declared in the seat
  catalogue's **`goal-writes`** column (interviewer → `goal.md`) and emitted by
  `team-kit/materialize-seats.py` into `seat.md`'s frontmatter. ⚠ **The declaration is checked
  against the cage AT MATERIALIZATION, not discovered at spawn**: `_cage_rw_covers` reads that same
  `SeatBinds` list and REFUSES to materialize a seat whose declared write the sandbox will not open
  read-write — so a briefing can no longer promise a write the kernel answers `EROFS` to, which is
  how a full interviewing session was lost (2026-08-09). Identity ground truth stays refused by bind
  ORDER rather than by a second list: `sessions.csv` and `state.csv` are carved back read-only after
  the opening, peer seat folders are absent under the `seats` tmpfs, and `seat.md` keeps its own
  read-only carve. `append`-only is the intent and **read-write is the grant** — bwrap has no
  append-only mount, so the bound is the file set.
- **…and the DERIVED write surface every descriptor now carries** (2026-08-11). The gate above
  answers "is the declared PATH writable" and held; it is one question short of what an occupant
  needs, because **every RW opening over a file sits inside `ro-bind:{goalDir}`, so the file is
  writable and its DIRECTORY is not** — and `Write`/`Edit`, like every atomic writer, create
  `<file>.tmp.<hash>` as a sibling before renaming. The kernel answers `EROFS` naming the TEMP
  path; the occupant reads it as "I have no write access", re-tests by touching a probe file in
  the goal root (read-only by design, so it refuses forever), and reports a permission failure
  that was never one. A second interviewing session was lost to exactly that (2026-08-11) with the
  grant correct the whole time. So `materialize-seats.py` renders a **derived** write-surface
  section into every `seat.md` and a short twin into every `AGENTS.md`: the writable paths read
  out of `cage.SeatBinds` through `cagespec.evaluate` — the same evaluator the refusal gate uses,
  so shadowing carves are respected and the list cannot disagree with the kernel — plus the
  symptom→meaning line (`that EROFS means your file IS writable and your tool is not`) and the
  in-place `cat > path <<'EOF'` form. Both are regenerated on every materialize; the section
  states it beats any authored prose above it, which is how a `<permissions>` unit still saying
  "Write: the goal folder" stops misleading its occupant. Rows `CG-2` in the selftest.
- **Per-run arguments on a fired tool — an IDENTITY allowlist, refusing by default** (task 7.559,
  owner ruling `d-owner-7559-design-rulings-0808`; `server/heart/argv-template.js` +
  `server/ticker/ticker.js` `launchFireTool`). A `tools:` entry in `config/spawn-profiles.yaml` may
  declare `args_allowlist: { <key>: [ …literal values… ] }`; its argv may then carry `{{key}}`, and
  a queue row SELECTS one of those literals. It never supplies a string — admission is `===`
  identity against a list a human wrote, never a grammar, never a denylist. Anything else is a typed
  refusal recorded `failed`, and no child is exec'd. ⚠ **The list lives in the boot-read merged
  config and NOWHERE ELSE — that is the whole security condition**, because `register-job` is
  reachable by any enrolled AGENT token, so an allowlist in a job registration would be extensible
  by the agents it bounds with no restart and no reviewed diff. Extending it keeps costing exactly
  what the argv freeze cost: a reviewed diff plus an integrator-owned restart. **Frozen stays the
  default** — an entry declaring no `args_allowlist` takes the same code path and the same
  byte-identical argv as before, and an entry that templates a value WITHOUT declaring a list is
  refused (fail closed) rather than exec'ing a literal `{{goal}}`. The boot-time catalogue check
  walks allowlist values too (`server/heart/catalogue-paths.js`), so a member naming a folder that
  is gone logs one `error` per boot forever and refuses nothing — a stale permission is loud, and
  removing it is the same act as adding it. Guarded by `server/ticker/probes/probe-argv-template.js`
  (a real `ticker.tick()` fire, argv read back from the child's own `process.argv`) and
  `server/heart/probes/probe-defect-fix.js`. **Live scope today is ONE entry, `edge-runner`, with
  ONE permitted goal.** So the edge-runner can advance any PRE-APPROVED goal — not an arbitrary one
  — and approving each costs one config edit plus one restart; after that its advances are ordinary
  enqueues. ⚠ Two things this does NOT do: it does not sandbox a fired tool (`caps: {}` /
  `sandbox: {}` are unchanged — it bounds who can STEER a tool, never what a tool can DO), and it
  does not govern a fire-tool row's `workdir` — that is row 7.562's own door
  (`checkFireToolWorkdir`), which admits the configured `default_workdir_root` by EXACT equality or
  a path inside a `.rbtv/goals/<goal>` containment, and since ruling
  `d-0811-workdir-symlink-boot-resolve` also requires the value to resolve inside the goals root
  resolved ONCE at engine boot — closing the symlinked-goal-segment escape the C5 review measured,
  while still admitting a not-yet-scaffolded goal and a goals root that is itself a symlink.
- **`daemon-watchdog`** (`ignite/capabilities/daemon-watchdog/`) — the ignite LIVENESS surface
  (CMP-28): a systemd user timer firing one deterministic pass that probes the deployment,
  restarts what is down through the services' own units, and DMs the owner only when it acted or
  a restart failed. Unlike the other two it is not driven by a `rbtv` verb — a timer fires it.
  It CALLS `daemon-operator` for every restart rather than reimplementing restart-and-verify.
  Ships installed-and-DISABLED; enabling has a sender-mint prerequisite that fails LOUD (the
  watchdog has no fallback to another sender's token).
  Contract in `daemon-watchdog.md`.

### `ignite/module.md` — the module entry point (KG shape)

The skill-format front door the SECOND installer (`core/capabilities/installer/`, task 7.64)
realizes as this module's **discovery skill** on each harness — the pushed index of the
progressive-disclosure ladder (`PRIN-3`): one line per command-line capability, bodies on demand
through each CLI's own `-h`. It carries no bodies and restates neither `ignite/CLAUDE.md` nor
`protocol.md` (`PRIN-11`).

This file (`modules/ignite.md`) is the LEGACY module descriptor read by `install.py`; the two
coexist while the CMP-5 tree is unbuilt, exactly as the two installers do.

## Reaching this module from the `rbtv` CLI

The system CLI (`core/capabilities/rbtv-cli/`, task 7.65) is the agent-facing front door. It
**delegates** to everything below — no second implementation of any of it (`PRIN-11`), and a
delegated call's stdout, stderr and exit code are the delegate's, unchanged.

```
rbtv ignite                      the module's components, its rules, and its action verbs
rbtv ignite <component>          that component's entry point body + its invocable entry points

rbtv run <goal-folder> [--status]                 -> capabilities/attached-execution
rbtv ignite daemon start|restart|stop|kill|unit [--service ignite|chat-bridge|probe-suite]
                                                    -> capabilities/daemon-operator
rbtv ignite ticker show|set-interval|history        -> capabilities/ticker-settings
rbtv ignite register-job|deregister-job|add-job|remove-job|inspect|snooze|status|kill -> cli/ignite.js
```

The standalone `ignite` client is **unchanged and still the working surface** — `rbtv ignite <cmd>`
execs it and nothing else. Auth stays env-only (`IGNITE_SENDER_TOKEN` never in argv); the `rbtv`
process never handles the token's value.

⚠ **Two commands named `kill`, and they are different objects.** `rbtv ignite kill` kills a
SESSION through the gateway; `rbtv ignite daemon kill` SIGKILLs a fixed service's unit. The
extra token is what tells them apart. Likewise `ignite status` (the daemon's report of itself, needs it alive) is not
`rbtv ignite daemon unit` (the machine's report about the daemon, works when it is dead).

⚠ **`rbtv ignite daemon unit` exits 0 for any unit it could READ**, including a failed or
crash-looping one. Health is the `health` field. **Branch on `health`, never on the exit status.**

## Scoping

Electing the module installs ONLY the `rbtv-team-kit` skill loader; the kit itself and the daemon are read/run in place from the repo. The kit was carried verbatim at promotion — its known instance couplings (a hardcoded spawn-cwd fallback, origin-vault paths in selftest fixtures and provenance prose) are enumerated in `ignite/team-kit/CLAUDE.md` § Known instance couplings and are owner-gated for generalization before this module ships beyond the `ignite/core-daemon` branch.
