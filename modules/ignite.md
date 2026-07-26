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
- **Kit contents**: `coord.py` (coordination CLI; `launch` pre-flight-validates every seat's harness/model before any pane opens, so one bad slug refuses the launch instead of stalling a whole wave at boot) · `watch.py` (liveness/inactivity/context/approval-gate watcher, plus two box-level duties — system RAM/load pressure and a wave window left with no live seat — heartbeat-stamped so `workers` can report the detached loop `ok`/`STALE`) · `protocol.md` (agent protocol) · `team-kit.md` (index + run setup) · `briefing-template.md` (seat briefings) · `closer-prompt.md` (seat-close flow) · `system-design.md` (designer-only rationale) · legacy dashboard trio (`tmux-overview`, `overview-compact.py`, `provider-usage.py` — superseded by the `teamview` CLI in orchestration).

### The ignite daemon (service code — not an installable component)

See `ignite/CLAUDE.md`. Client CLI: `ignite/cli/` (`ignite add-job` / `remove-job` / `inspect`).

## Scoping

Electing the module installs ONLY the `rbtv-team-kit` skill loader; the kit itself and the daemon are read/run in place from the repo. The kit was carried verbatim at promotion — its known instance couplings (a hardcoded spawn-cwd fallback, origin-vault paths in selftest fixtures and provenance prose) are enumerated in `ignite/team-kit/CLAUDE.md` § Known instance couplings and are owner-gated for generalization before this module ships beyond the `ignite/core-daemon` branch.
