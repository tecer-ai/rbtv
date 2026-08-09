# Ignite

## Purpose

The runtime layer of RBTV. Two parts share the module because they are two faces of the same substrate — agents doing coordinated work over time:

1. **The ignite daemon** (`ignite/` service code) — ONE Node.js service (server core + gateway) that makes a workspace's job queue launch due jobs on a runtime host. It is **deployed, never installed**: `install.py` does not copy it into any workspace's `.claude/`. Its conventions, install model, state layout, and terminology live in `ignite/CLAUDE.md` and the repo root `CLAUDE.md` § "ignite/ — Runnable Service Code".
2. **The team-kit** (`ignite/team-kit/`) — reusable mechanics for running a coordinated parallel multi-agent team in tmux: one pane per seat, verified seat identities, a typed append-only message log with threading and retractions, bounded reads, staged launches with per-seat harness/model/effort profiles, a pre-launch worker-mirror refresh so a codex/opencode seat never boots onto rules its gitignored `AGENTS.md`/`.agents/` mirror left stale, watcher and closer seats, and guards against the failure modes the runs measured (a re-check-in cannot split a seat across two live panes; a seat parked on an approval prompt is detected and never woken into its modal; the watcher's own loop is heartbeat-checked). Proven over four runs in the origin workspace (kg-edges-visualization-improvements → kg-views-rebuild → the tv-ux-review 28-seat batch test → the coordinate CLI redesign, 2026-07-23→25) before promotion (2026-07-26).

## Components

### `rbtv-team-kit` (skill)

- **What**: Thin loader into `ignite/team-kit/` — the kit's hard rules (`CLAUDE.md`), the run-setup guide (`team-kit.md` § Starting a new run), and the protocol every run agent follows (`protocol.md`). The kit's engine is `coord.py` (the `coordinate` CLI where symlinked): `checkin` · `status` · `read` · `send` · `pending` · `checkout` for every seat; `launch` · `close` · `close-seat` · `approve` · `panel` · `owner` for the leader; `python3 coord.py selftest` verifies the mechanics. All run state lives in the run package (`--package DIR` / `--run TAG` / cwd walk-up), never in the kit.
- **When to use**: Starting a new team run, building a run package, adding seats, or joining/operating an existing run.
- **How to invoke**: The `rbtv-team-kit` skill, or read `{rbtv_path}/ignite/team-kit/team-kit.md` directly.
- **Kit contents**: `coord.py` (coordination CLI; `launch` pre-flight-validates every seat's harness/model before any pane opens, so one bad slug refuses the launch instead of stalling a whole wave at boot) · `watch.py` (liveness/inactivity/context/approval-gate watcher, plus two box-level duties — system RAM/load pressure and a wave window left with no live seat — heartbeat-stamped so `workers` can report the detached loop `ok`/`STALE`) · `protocol.md` (agent protocol — every seat) · `roles.md` + `briefing-authoring.md` (its two role-scoped siblings, split out 2026-07-28: the role catalogue, read by a seat holding a special role or a non-claude harness; the briefing-authoring rules, read only by whoever authors briefings) · `team-kit.md` (index + run setup) · `briefing-template.md` (seat briefings) · `closer-prompt.md` (seat-close flow) · `system-design.md` (designer-only rationale) · `starter-set/` (`conduct.md` + `CLAUDE.md` + `budget.json` — the OWNER-APPROVED goal-generic base texts a created run package is born with, `d-owner-starter-set-approved-0808`; BYTE-COPIED by `scaffold-seats --conduct/--claude-md/--budget-json`, which refuses `create-inputs-missing` without them — plus `addressable.csv` (7.546), the register that makes the standing owner door a legal ROLE address in a run that rosters no authority seat, so `conduct.md`'s escalation clause resolves: tier 1 parks the question in the goal's `doubts.md` (the durable RECORD, kept — never retired), tier 2 sends it `--to master` where the chat bridge's bus ferry carries it to the owner's DM, tier 3 stops the dependent work. ⚠ `addressable.csv` is NOT yet a `scaffold-seats` creation input — a run created today does not receive it and tier 2 is refused until it is placed by hand; wiring it as the 4th `CREATION_INPUTS` tuple also has to pass it through `goal-creation-request`, and a REQUIRED 4th input breaks every caller that does not supply it. ⚠ NOT `conduct-template.md`: that is an unfilled FORM a run's conduct-author instantiates, and `--conduct` copies bytes rather than filling slots, so pointing the scaffold at it would give a run a rulebook whose law reads `{{INSTANTIATE}}`) · legacy dashboard trio (`tmux-overview`, `overview-compact.py`, `provider-usage.py` — superseded by the `teamview` CLI in orchestration).

### The ignite daemon (service code — not an installable component)

See `ignite/CLAUDE.md`. Client CLI: `ignite/cli/` (`ignite add-job` / `remove-job` / `inspect`).

### Capabilities

- **`daemon-operator`** (`ignite/capabilities/daemon-operator/`) — the ignite OPERATOR surface:
  local systemd USER unit ops that work precisely when the daemon is DOWN. Contract in
  `daemon-operator.md`.
- **`goals-tree`** (`ignite/capabilities/goals-tree/`) — the goals-tree machinery
  (`scaffold`/`reindex`/`lint`/`materialize`). Contract in `tool/README.md`.
- **`goal-creation-request`** (`ignite/capabilities/goal-creation-request/`) — the entry a
  goal-creation request arrives at: `validate`, `handle` (create → arm → launch), and
  `scaffold-and-queue`, the DAEMON-EXECUTED verb (task C2) that drains a staged request inbox,
  scaffolds each goal and queues its first workflow job ten minutes out. That verb exists because a
  Slack-caged channel master measurably cannot create a goal directory but can write its own seat
  folder, so the payload is file-staged and only the trigger crosses the gateway. Registered in
  `config/spawn-profiles.yaml` under `tools: goal-creation-request` and landed **dark** — arming is
  three gated acts in a fixed order. The workflow every master-created goal starts in is RULED
  (task C5, `d-owner-q10-launcher-0808`): `planning-deprecated` / entry seat `elicitator`, the existing meta
  component `.rbtv/mirror/meta/planning-deprecated/` (named `planning`/`planner-workflow` when ruled;
  renamed by R11, vault `01f60de16`, task 7.598). The launcher argv for it is now RULED AND
  LANDED too (task C5E, `d-owner-planning-entry-0808` + `-2-0808`): `spawn-profiles.yaml` carries a
  `workflows:` section, the goal is born WITH a `runs/run-1` package materialized through the ruled
  name `scaffold-seats`, and `tool/workflow_launcher.py` opens that run's own per-run detached tmux
  room before handing the launch to `coordinate` with an explicit target. That first fire DOES open
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
  does not govern a fire-tool row's `workdir`, which stays per-run and unvalidated (row 7.562).
- **`watch-operator`** (`ignite/capabilities/watch-operator/`) — the WATCH-LOOP operator surface:
  the fourth ignite service's power verbs plus its pass cadence (`heartbeat-set`). Separate from
  `daemon-operator` because its target is a RUN PACKAGE, not a fixed unit — the watch unit is
  transient and derived (`rbtv-watch-<digest>`), so every verb resolves WHICH run first and refuses
  rather than guessing. It delegates `unit`/`restart`/`stop`/`kill` back to `daemon-operator`.
  ⚠ `heartbeat-set` is the WATCH loop's cadence, never the ticker's `set-interval`. Contract in
  `watch-operator.md`.
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

rbtv ignite daemon start|restart|stop|kill|unit [--service ignite|chat-bridge|probe-suite]
                                                    -> capabilities/daemon-operator
rbtv ignite watch  unit|start|restart|stop|kill|heartbeat-show|heartbeat-set
                   (--package PKG | --goal NAME)    -> capabilities/watch-operator
rbtv ignite ticker show|set-interval|history        -> capabilities/ticker-settings
rbtv ignite register-job|add-job|remove-job|inspect|snooze|status|send|screen|kill   -> cli/ignite.js
```

The standalone `ignite` client is **unchanged and still the working surface** — `rbtv ignite <cmd>`
execs it and nothing else. Auth stays env-only (`IGNITE_SENDER_TOKEN` never in argv); the `rbtv`
process never handles the token's value.

⚠ **Three commands named `kill`, and they are different objects.** `rbtv ignite kill` kills a
SESSION through the gateway; `rbtv ignite daemon kill` SIGKILLs a fixed service's unit; `rbtv
ignite watch kill` SIGKILLs one RUN's transient watch unit. The extra token is what tells them
apart. Likewise `ignite status` (the daemon's report of itself, needs it alive) is not
`rbtv ignite daemon unit` (the machine's report about the daemon, works when it is dead).

⚠ **`rbtv ignite daemon unit` exits 0 for any unit it could READ**, including a failed or
crash-looping one. Health is the `health` field. **Branch on `health`, never on the exit status.**

## Scoping

Electing the module installs ONLY the `rbtv-team-kit` skill loader; the kit itself and the daemon are read/run in place from the repo. The kit was carried verbatim at promotion — its known instance couplings (a hardcoded spawn-cwd fallback, origin-vault paths in selftest fixtures and provenance prose) are enumerated in `ignite/team-kit/CLAUDE.md` § Known instance couplings and are owner-gated for generalization before this module ships beyond the `ignite/core-daemon` branch.
