---
type: index
tags:
  - rbtv-sb-merge-refactor
---

# team-kit/ — reusable multi-agent team mechanics

The shared toolkit for running parallel multi-agent teams in tmux, extracted from the
2026-07-24 `kg-edges-visualization-improvements` run (owner-directed, 2026-07-24) and upgraded
with the full improvement set that run's observer logged. Reusable across this campaign's builds;
promote to the rbtv repo only after it proves out across runs.

| File | What it is |
|------|-----------|
| `coord.py` | The coordination CLI. Commands — everyday: `checkin` · `status` · `read` · `send` · `pending` · `checkout`; leader: `launch` · `close` · `close-seat` · `approve` · `panel` · `owner` · `add-to-group`; other: `workers` · `create-group` · `export-transcript` · `depart` · `selftest`. Identity is RESOLVED (calling pane → roster row, or `$COORD_AGENT`/`--as`) and verified, never typed — no command carries the caller's own name, and a claim contradicting the pane is refused. Messages are typed and threaded (`--re <ask#>`, required on answers); `read` is bounded (10 at a time, cursor advances only through what it SHOWED) with `--digest`/`--msg N`/`--after N`, and every filtered view is peek-only; `status` and `pending` answer "where am I" and "what is still open" in one shot; `--pretty` (or `COORD_PRETTY=1`) colours the view commands for a human reader, default output stays plain. Multi-harness (claude, codex, opencode — per-briefing `harness:`/`model:`/`effort:`/`ctx-refresh:`), per-seat launch profiles. All state lives in the run package, resolved `--package DIR` > `--run TAG` (auto-registry) > `$COORD_PACKAGE` > cwd walk-up — a seat working in its own folder passes no flag at all. `python3 coord.py selftest` verifies the mechanics; `coordinate -h` is the grouped command index, `coordinate <command> -h` the detail. On the ignite VPS it is also on PATH as `coordinate` (per-machine symlink, never synced by git). |
| `watch.py` | Deterministic liveness/inactivity/context monitor (the watcher-seat tool): flags leader with the exact `close --renew` command when thresholds cross. `python3 watch.py --selftest` verifies it. |
| `closer-prompt.md` | The closer seat's prompt template (`close <agent>` fills and spawns it): co-writes the seat's `memory.md` with the worker, then closes (and optionally renews) the seat. |
| `protocol.md` | The coordination protocol + execution rules every run's agents follow. |
| `briefing-template.md` | Template for a seat folder briefing (`workers/{agent}/agent.md`; `harness:`/`model:`/`window:`/`ephemeral:` frontmatter). |
| `tmux-overview` | Owner utility: live view of one tmux session's windows/panes plus Claude plan usage (`tmux-overview <session>`; on this VPS also on PATH, per-machine symlink). `--compact --package <run-package>` renders the ≤7-line control-panel dashboard via `overview-compact.py` — plan-usage bar charts left, windows with roster-resolved seat names right; the `panel` subcommand embeds exactly that in the leader window's 8-row strip. |
| `overview-compact.py` | The compact dashboard renderer behind `tmux-overview --compact`: colored usage bars for Claude (5h/7d) AND the worker providers (GLM 5h/7d, Codex 7d) + DeepSeek balance + Sakana console note, plus every window with member seat names mapped pane→agent from `coordination/workers.md` (claude panes rewrite their own titles, so the roster is the name source). |
| `provider-usage.py` | Read-only poller for worker-harness plan limits → `~/.claude/rbtv-runtime/provider-usage.json`: Z.AI coding-plan quota endpoint (5h/weekly %), DeepSeek balance endpoint, Codex plan windows from its LOCAL session files (no API call; fresh only while a codex seat runs), Sakana marked console-only (no documented endpoint). Keys stay in opencode's store, sent only to each provider's own documented host, never printed. The compact loop re-polls when data is >10 min old. |

> **Successor note (2026-07-24):** the `tmux-overview` / `overview-compact.py` / `provider-usage.py`
> trio was promoted, generalized, into the rbtv repo as the **`teamview`** CLI
> (`orchestration/cli/teamview/`, branch `ignite/core-daemon`) — multi-account providers with
> in-use highlighting, kimi+google added, four size-responsive layouts, session auto-detection.
> The kit copies stay authoritative for the in-flight kg-views-rebuild run; new runs and the
> `panel` strip should adopt `teamview` after that run closes. |
| `statusline-usage.py` | Claude Code statusline script (wired in the vault's `.claude/settings.local.json`): renders the status line, persists plan usage (5h/7d windows from the statusline payload's `rate_limits`) to `~/.claude/rbtv-runtime/plan-usage.{txt,json}` for `tmux-overview` to display, AND persists the session's pid map (`~/.claude/rbtv-runtime/session-pids/<sid>.json` — claude pid → transcript) so the rbtv `ctx-monitor` CLI can resolve a tmux pane's claude process to its EXACT transcript (per-pane context/model in `teamview`). |
| `system-design.md` | Designer-only: the kit's design rationale (see `CLAUDE.md` — run agents never read it; designers keep it updated). |

## Starting a new run

1. Create a run package folder (normally under the owning project's `build/`):
   `{package}/CLAUDE.md` (roster + surface-ownership map + run-specific rules, pointing at
   `protocol.md`), `{package}/workers/{agent}/` seat folders (briefing `agent.md` from the
   template + `CLAUDE.md`/`AGENTS.md` loaders), `{package}/coordination/` (empty —
   script-managed).
2. The owner starts `leader` by hand in a tmux pane (first boot only — renewals relaunch it
   automatically, see 3); leader runs
   `python3 {team-kit}/coord.py --package {package} launch` (optionally `--only a,b` for staged
   launches) — one seat per briefing, harness/model/effort/cwd from each briefing's frontmatter;
   `window: yes` seats get their own named window (tab), the rest tile as panes in the leader
   window (hybrid layout). Launch auto-names everything: pane/window titled with the agent's
   name; claude seats also get a `/rename <agent>` injected after boot (checkin re-titles the
   pane too, so recoveries stay named). Leader's own session: type `/rename leader` yourself when
   you start it — nothing automates the pane the owner opened by hand.
3. Lifecycle: a seat ends with `checkout`, which exports its transcript first (ephemeral seats use
   `depart`, which exports, checks out and kills their own pane in one command); leader closes or
   renews long-lived seats via `close <agent> [--renew]`
   (a sonnet closer co-writes `workers/{agent}/memory.md`, then `close-seat` kills — and with
   `--renew` freshly relaunches — the seat). The leader seat itself renews the same way
   (`close leader --renew`): the relaunched leader lands back as a pane in the window its old
   pane occupied (the control panel), boots resume-first from `workers/leader/memory.md`
   (its "Resume here" section — it continues the run, never re-runs completed work), and gets
   the auto `/rename` like any launched claude seat; a bare `launch` still never boots leader.
   A watcher seat loops `watch.py` to flag stalls and
   context overruns. Everything else follows `protocol.md`.

> **Naming note — SUPERSEDED (2026-07-25, ruling R29).** The earlier owner ruling (2026-07-24)
> kept this seat named `master`, holding it deliberately distinct from the system-definition
> registry's `leader` concept ("the master is not the team leader"). That ruling is SUPERSEDED:
> R29 finds the seat performed the KG `leader` function (per-team unblocking, arbitration, sole
> team voice to the owner), so it is re-keyed to `leader` here and in every kit artifact;
> `master` is reserved for the system-plane request door (R21). Run packages created before
> 2026-07-25 still name the seat `master` and are frozen — they are not re-keyed.

Prior-run provenance: the improvement evidence (P1–P26) lives in
`../kg-edges-visualization-improvements/team-observations.md` (tactical) and
`../kg-edges-visualization-improvements/agent-teams-strategic-lessons.md` (strategic).
First consumer run: `../kg-views-rebuild/`.
