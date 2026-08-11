# Ignite

## Purpose

The runtime layer of RBTV. Two parts share the module because they are two faces of the same substrate — agents doing coordinated work over time:

1. **The ignite daemon** (`ignite/` service code) — ONE Node.js service (server core + gateway) that makes a workspace's job queue launch due jobs on a runtime host. It is **deployed, never installed**: `install.py` does not copy it into any workspace's `.claude/`. Its conventions, install model, state layout, and terminology live in `ignite/CLAUDE.md` and the repo root `CLAUDE.md` § "ignite/ — Runnable Service Code".
2. **The team-kit** (`ignite/team-kit/`) — reusable mechanics for running a coordinated parallel multi-agent team in tmux: one pane per seat, verified seat identities, a typed append-only message log with threading and retractions, bounded reads, staged launches with per-seat harness/model/effort profiles, a pre-launch worker-mirror refresh so a codex/opencode seat never boots onto rules its gitignored `AGENTS.md`/`.agents/` mirror left stale, watcher and closer seats, and guards against the failure modes the runs measured (a re-check-in cannot split a seat across two live panes; a seat parked on an approval prompt is detected and never woken into its modal; the watcher's own loop is heartbeat-checked). Proven over four runs in the origin workspace (kg-edges-visualization-improvements → kg-views-rebuild → the tv-ux-review 28-seat batch test → the coordinate CLI redesign, 2026-07-23→25) before promotion (2026-07-26).

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
  (`scaffold`/`reindex`/`lint`/`materialize`/`lane`). `lane` is the DAEMON'S PICKUP BUTTON (owner
  ruling `d-daemon-lane-button`, 2026-08-10): it writes one word into `<goal>/execution-lane` saying
  which lane currently runs the goal, and the daemon's watch pass (`ignite/engine/lane-watch.js`,
  fired by the daemon loop before every tick) seeds the goals assigned `daemon` through
  `engine.seedGoal`. Absent means `console` — the daemon adopts only what it was explicitly given;
  `--set daemon` requires `--profile`; flipping it mid-goal is the supported act. Contract in
  `tool/README.md`; the lane half also in `capabilities/attached-execution/attached-execution.md`
  § The daemon lane's goal pickup.
- **`attached-execution`** (`ignite/capabilities/attached-execution/`) — the ATTACHED lane: the
  **`rbtv run`** verb (`rbtv run <goal-folder> --profile <name>`; entry point
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
  goal-creation request arrives at: `validate`, `handle` (create → arm → launch), and
  `scaffold-and-queue`, the DAEMON-EXECUTED verb (task C2) that drains a staged request inbox,
  scaffolds each goal and queues its first workflow job ten minutes out. That verb exists because a
  Slack-caged channel master measurably cannot create a goal directory but can write its own seat
  folder, so the payload is file-staged and only the trigger crosses the gateway. Registered in
  `config/spawn-profiles.yaml` under `tools: goal-creation-request` and landed **dark** — arming is
  three gated acts in a fixed order. The workflow every master-created goal starts in is RULED
  (task C5, `d-owner-q10-launcher-0808`): `planning` / entry seat `plan-interviewer`, the meta
  component `.rbtv/mirror/meta/planning/`. *(Issue C-2, 2026-08-10: the ruling originally landed
  against `planning-deprecated` / `elicitator` — named `planning`/`planner-workflow` when ruled,
  renamed by R11, vault `01f60de16`, task 7.598. That component was deleted and every fired
  creation refused `workflow-unknown`; the values were repointed at the 16-seat planning
  rewrite.)* The launcher argv for it is now RULED AND
  LANDED too (task C5E, `d-owner-planning-entry-0808` + `-2-0808`): `spawn-profiles.yaml` carries a
  `workflows:` section, the goal is born WITH its package materialized through the ruled name
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
  will consume. Alongside it, `tool/workflow_launcher.py` opens the goal's ONE detached tmux
  room, named for the goal (design-lock item 2), before handing the launch to `coordinate` with an
  explicit target. That first fire DOES open
  the entry seat — `coordinate launch`'s cold-start admission (team-kit 7.406) admits a virgin
  package on the empty-room bound — **subject to the RAM floor, which the launcher deliberately
  leaves binding** (it passes `--force`, never `--force-memory`: this is a NEW launch and that floor
  is sized for exactly it), so under memory pressure the first fire opens nothing and exits
  non-zero. Cold-start clears the CAPACITY gate; it is not a guarantee that a seat opens. And the
  launcher's exit code IS the store record: `0` means a
  seat pane opened and nothing else, `3` means the launch ran and admitted nobody (recorded
  `failed`, never a false `done`; the row is one-shot, so that failure has no cadence to recur on).
  Task 7.548 measured both and corrected the contrary claim this doc, the launcher and
  `spawn-profiles.yaml` had carried — including its instruction to put the team-monitor census
  sensor in the arming sequence, which is impossible: the sensor refuses until a seat has checked
  in. Task **7.552** then closed what that left open — `coordinate launch` now hands
  `team_monitor.py ensure` the room's session, the one it just launched into, so the census sensor
  STARTS with the room's first seat instead of refusing on a roster nobody has checked into yet.
  Without it the cold-start bound was spent ONCE and every SUBSEQUENT fire read `CAP UNENFORCEABLE`
  and deferred every counted candidate — and the second fire is exactly Wave D's advancement, so a
  run's first fire worked and the run then stalled (`capabilities/goal-creation-request/probes/probe-sensor-start.py`).
  The ruled bare name now
  RESOLVES under the daemon: a fired tool used to inherit the systemd `--user` MANAGER's PATH, which
  carries no `~/.local/bin`, so `scaffold-seats` exited 127 and every daemon-fired creation refused
  after scaffolding — fixed at the CARRIER for the whole class, not at this call site
  (`d-owner-f1-carrier-env-0808`; `server/spawn/carrier.js` `toolExecEnv`). Landed is still not
  live, and that covers BOTH halves — the config file is boot-read AND the carrier fix is daemon
  code, so a RUNNING daemon has neither until the next restart; the PATH class is retired in the
  tree, not yet in the process. Arming remains the three gated acts. Contract in
  `goal-creation-request.md`. The carrier fix had ONE leak downstream of it, closed by task 7.551:
  `jobs/jobcontain.py` `detach_argv` opens a SECOND `systemd-run --user` so a recovery outlives the
  job that started it, and that inner hop went back through the MANAGER environment — so the
  composed PATH stopped at it and the detached process's descendants (`recover-room.py` →
  `coord.py`, which boots the harness by the bare name `claude`) were back on the manager PATH. It
  now FORWARDS `os.environ["PATH"]` — forwarded, never re-derived, so the composer stays singular
  (PRIN-11); guarded by `jobs/probes/probe-detach-env.py`.
- **`goal-launch-delay`** (`ignite/capabilities/goal-launch-delay/`) — the channel master retiming
  its OWN queue delay (issue C-1, owner-ruled 2026-08-10). The knob has no settings file: it IS the
  `--delay-seconds` operand of the `tools: goal-creation-request:` argv above, so the tool performs
  a LINE-PRECISE edit of that document and never round-trips it through a YAML dumper. Three verbs:
  `show` (the value, whether it is explicit or the tool's own 600 default, and the `file:line` it
  comes from), `request` (the SEAT's verb — validate, stage the payload in the seat's own folder,
  `add-job` the trigger), `apply` (the DAEMON's verb — drain, edit, record the outcome, restart
  `rbtv-ignite` LAST). Same two-part transport as `goal-creation-request` and for the same measured
  reasons (read-only cage · static `fire-tool` argv · `enqueue-job` the one verb open to a `bridge`
  token). Registered under `tools: goal-launch-delay`; arming is the same three gated acts. Contract
  in `goal-launch-delay.md`.
- **`master-profile`** (`ignite/capabilities/master-profile/`) — the channel master choosing its OWN
  harness and model (issue C-1, same ruling). The knob is `master_profile` in
  `.rbtv/config/chat-bridge-config.json`, read at boot by the bridge and selected for master (DM)
  traffic by `forward-path.js#profileFor` (`masterProfile || sessionProfile`). The requested name is
  validated against the LIVE `profiles:` set of `spawn-profiles.yaml` at BOTH halves — an unknown
  name does not fail at the bridge, it fails at the spawn one owner message later — and an ABSENT
  `master_profile` key is refused rather than created (creating it would split master and session
  traffic apart without anyone deciding to). Restarts `rbtv-chat-bridge`, which ends the requesting
  sitting, so the outcome record lands before the restart. ⚠ **No `--effort` flag, by measurement:**
  effort is not on the master spawn wire at all — `forward-path.js` enqueues `{profile, prompt}`,
  the `chat-agent` job's schema admits no effort key, `ticker.js#launchAgent` calls a
  `spawnManager.spawn` signature with no effort parameter, and the per-profile `effort:` translation
  table has NO daemon caller (`dispatch.js` says so verbatim). Contract in `master-profile.md`.
- **`bindings`** (`ignite/capabilities/bindings/`) — the CASTING SHEET a workflow is run through
  (owner-ruled 2026-08-10): which harness, model and effort each seat gets. A workflow is the
  program, a **taskforce** is its running instance, and the bindings file is what casts one into the
  other; `team-kit/materialize-seats.py --bindings` is its ONE consumer. Four verbs — `catalog`
  (every harness+model this workspace can spawn, each effort dial NUMBERED), `inspect` (every
  manifest seat with its definition file, staffing hints and casting state), `scaffold`
  (create-only), `set`. ⚠ **NOT the two-part shape of the two capabilities above, and that is
  measured, not style**: the bindings tree sits in the channel master's `rw-paths` and NOTHING
  boot-reads it, so every verb is a plain direct file write — no staged inbox, no `enqueue-job`
  trigger, no restart. ⚠ **`catalog` IS the validator** `set` enforces: one derivation, two
  consumers, so the surface an agent reads and the surface that refuses it cannot disagree. It is
  composed from `profiles:` in `config/spawn-profiles.yaml` (which `r-seats-only-architecture` makes
  the workspace's spawnable set) plus each profile's own `effort:` block for whether a dial exists,
  and gated by `coord.py#validate_seat` — the predicate `materialize-seats.py`'s F6 gate imports, so
  a pair this tool offers can never be one materialize then refuses. The effort NUMBER indexes the
  HARNESS's native ladder (claude: 1=low … 5=max) and the file stores the harness's own string; the
  per-profile `effort.values` table is a different object (the daemon lane's four abstract levels)
  and using it would make `xhigh` unspellable. One file per WORKFLOW at
  `.rbtv/config/bindings/{module}/{component}/{code}.json` — `{code}` is the workflow's code, the
  seat-id prefix its manifest rows carry, derived and never typed. Deployment config, never the
  mirror. Contract in `bindings.md`.
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

rbtv run <goal-folder> (--profile NAME | --status)  -> capabilities/attached-execution
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
