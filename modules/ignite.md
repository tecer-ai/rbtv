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
- **Kit contents**: `coord.py` (coordination CLI; `launch` pre-flight-validates every seat's harness/model before any pane opens, so one bad slug refuses the launch instead of stalling a whole wave at boot) · `watch.py` (liveness/inactivity/context/approval-gate watcher, plus two box-level duties — system RAM/load pressure and a wave window left with no live seat — heartbeat-stamped so `workers` can report the detached loop `ok`/`STALE`) · `protocol.md` (agent protocol — every seat) · `roles.md` + `briefing-authoring.md` (its two role-scoped siblings, split out 2026-07-28: the role catalogue, read by a seat holding a special role or a non-claude harness; the briefing-authoring rules, read only by whoever authors briefings) · `team-kit.md` (index + run setup) · `briefing-template.md` (seat briefings) · `closer-prompt.md` (seat-close flow) · `system-design.md` (designer-only rationale) · `starter-set/` (`conduct.md` + `CLAUDE.md` + `budget.json` — the OWNER-APPROVED goal-generic base texts a created run package is born with, `d-owner-starter-set-approved-0808`; BYTE-COPIED by `scaffold-seats --conduct/--claude-md/--budget-json`, which refuses `create-inputs-missing` without them. ⚠ NOT `conduct-template.md`: that is an unfilled FORM a run's conduct-author instantiates, and `--conduct` copies bytes rather than filling slots, so pointing the scaffold at it would give a run a rulebook whose law reads `{{INSTANTIATE}}`) · legacy dashboard trio (`tmux-overview`, `overview-compact.py`, `provider-usage.py` — superseded by the `teamview` CLI in orchestration).

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
  (task C5, `d-owner-q10-launcher-0808`): `planning` / entry seat `elicitator`, the existing meta
  component `.rbtv/mirror/meta/planner-workflow/`. The launcher argv for `planning` is now RULED AND
  LANDED too (task C5E, `d-owner-planning-entry-0808` + `-2-0808`): `spawn-profiles.yaml` carries a
  `workflows:` section, the goal is born WITH a `runs/run-1` package materialized through the ruled
  name `scaffold-seats`, and `tool/workflow_launcher.py` opens that run's own per-run detached tmux
  room before handing the launch to `coordinate` with an explicit target. Landed is still not live —
  the file is boot-read, so the entry activates at the next daemon restart, and arming remains the
  three gated acts. Contract in `goal-creation-request.md`.
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
