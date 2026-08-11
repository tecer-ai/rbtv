---
type: index
tags:
  - rbtv-sb-merge-refactor
---

# team-kit/ — reusable multi-agent team mechanics

The shared toolkit for running parallel multi-agent teams in tmux, extracted from the
2026-07-24 `kg-edges-visualization-improvements` run (owner-directed, 2026-07-24) and upgraded
with the full improvement set that run's observer logged. Run-agnostic and reusable across any
workspace's builds; promoted into the rbtv repo (ignite module) on 2026-07-26 after three proving
runs.

| File | What it is |
|------|-----------|
| `coord.py` | The coordination CLI. Commands — everyday: `checkin` · `status` · `read` · `send` · `pending` · `checkout`; leader: `launch` · `close` · `close-seat` · `approve` · `panel` · `owner` · `add-to-group`; other: `workers` · `create-group` · `export-transcript` · `depart` · `selftest`. Identity is RESOLVED (calling pane → roster row, or `$COORD_AGENT`/`--as`) and verified, never typed — no command carries the caller's own name, and a claim contradicting the pane is refused. Messages are typed and threaded (`--re <ask#>`, required on answers); `read` is bounded (10 at a time, cursor advances only through what it SHOWED) with `--digest`/`--msg N`/`--after N`, and every filtered view is peek-only; `status` and `pending` answer "where am I" and "what is still open" in one shot; `--pretty` (or `COORD_PRETTY=1`) colours the view commands for a human reader, default output stays plain. Multi-harness (claude, codex, opencode — per-briefing `harness:`/`model:`/`effort:`/`ctx-refresh:`), per-seat launch profiles; `launch` pre-validates every seat's harness/model (alias/slug shapes, local knowledge only) and refuses BEFORE opening any pane (PROP-8). All state lives in the run package, resolved `--package DIR` > `--run TAG` (auto-registry) > `$COORD_PACKAGE` > cwd walk-up — a seat working in its own folder passes no flag at all. Session identity is TOLD to the seat: `checkin` stamps the durable trace `{package}/sessions.csv` — whose `checkin` column is the 15th, appended last, holding that session's LATEST check-in (a re-check-in moves the cell, it never adds a row), stamped on the seat's last open row and reaching live traces by header-widening, with an EMPTY cell meaning never-checked-in or a row predating the column and never read as `started` — and then prints the identity line `session: … · native: … · scratchpad: …`, every field on every check-in, each printing `UNRESOLVED` when that id could not be resolved. Every session opened through the kit creates the seat's per-session scratchpad `{seat folder}/sessions/{session-id}/` at session-open, and the boot prompt tells the seat to put every working file it produces there — the seat's `seat.md`/`agent.md` descriptor, its `memory.md` and any `conventions.md` STAY at the seat-folder root; the scratchpad is excluded from the boot-staleness walk alongside `transcripts/`, since neither is read at boot. `python3 coord.py selftest` verifies the mechanics; `coordinate -h` is the grouped command index, `coordinate <command> -h` the detail. On the ignite VPS it is also on PATH as `coordinate` (per-machine symlink, never synced by git). |
| `nudge.py` | Deterministic nudge loop: fires a message at a NAMED SEAT every `--interval` seconds, so a seat that must run a recurring sweep (the chief-of-staff's cadence pass) cannot go passive. `python3 nudge.py run --package {package} --to {seat} [--interval 60] [--transport tmux\|file\|stdout] [--once\|--max-ticks N] [--dry-run] [--message …] [--heartbeat PATH]`; `python3 nudge.py check --heartbeat PATH` reports `GAP`/`DUPLICATE`/`STALE`/`UNPARSEABLE`/`MISSING`/`EMPTY` from the heartbeat file ALONE (exit 0 clean, 1 dirty). The recipient's pane is RE-RESOLVED FROM THE ROSTER ON EVERY TICK following `coord.py`'s own recipient semantics — there is deliberately no `--pane` flag, because a remembered `%n` protects a dead pane while the real recipient goes un-nudged. Every tick appends a monotonic-seq record to `{package}/coordination/nudge-heartbeat-{seat}.jsonl`, which is what makes a STOPPED loop distinguishable from a quiet room; one loop per heartbeat file, enforced by `flock` (a second refuses with exit 3). ⚠ It is NOT the runtime's ticker engine and must never be wired into the daemon's clock. Under the `tmux` transport a recipient parked on an approval modal is SKIPPED rather than typed into — the tick records `skipped:at-approval-gate` with `ok:false`, so the non-delivery is readable from the heartbeat alone, and the seat picks the nudge cadence back up once leader clears the gate (G-289, built 2026-08-10). The detector is `coord.py`'s own `at_approval_gate` (pane TITLE only), imported LAZILY and non-fatally — never re-implemented here, and never able to stop a tick: if `coord.py` cannot be imported the loop says so once on stderr and delivers as before. The check is scoped to the `tmux` transport because only a pane can be corrupted by a modal, which also keeps `stdout`/`file` runs tmux-free. ⚠ It still has no composer detection (`coord.py` has it): a recipient mid-compose can still have the nudge land in its editor. ⚠ POSIX-only (`fcntl`). Its acceptance suite is `python3 test_nudge.py` (16 claims, 19 controls; exit 0 only when every claim passed AND every control went red) — claim C6 re-extracts `WORKER_ROW` from the sibling `coord.py` at test time, because `nudge.py` deliberately COPIES that grammar rather than importing `coord` for it (the approval-gate predicate is the ONE thing it does import), and a silent drift would resolve the wrong pane. Promoted into the kit 2026-08-10 from its build folder in a closed run; run it from here, never from a run package. |
| `closer-prompt.md` | The closer seat's prompt template (`close <agent>` fills and spawns it) — the FAILURE PATH: co-writes the seat's `memory.md` with the worker, then closes (and optionally relaunches) a seat that cannot check itself out. A healthy seat renews itself with `checkout --renew --handoff`, with no closer in the path. |
| `protocol.md` | The coordination protocol + execution rules every run's agents follow. |
| `briefing-authoring.md` | The briefing/seat-descriptor authoring rules — read ONLY by whoever authors them (the assembler at bootstrap, or a live run's seat-authoring role), never by an executing seat. Split out of `protocol.md` 2026-07-28. |
| `roles.md` | The role catalogue (leader, deputy, scientist, judge, verifier, worker, closer, watcher) + the codex/opencode harness note — read by a seat that HOLDS one of the special roles or runs a non-claude harness. Split out of `protocol.md` 2026-07-28. |
| `communication.md` | How a run talks: the volunteer floor plus ten rules on message form, length, address and correction, each marked `[TOOL]` (the CLI refuses a breach) or `[HAND]` (held by discipline, a breach is silent). Ships as-is — a run adopts it unchanged. |
| `conduct-template.md` | The run conduct manual, unfilled: run-agnostic law (deterministic-first, surfaces + lifecycle distribution, decisions/ledgers, git, gated cutover, verify/fail-loud, dispatch carry-through) plus `{{slots}}` a run's conduct-author fills at bootstrap (mission, terminology hook, budget + model policy). |
| `briefing-template.md` | Template for a seat folder briefing (`workers/{agent}/agent.md`; `harness:`/`model:`/`window:`/`ephemeral:` frontmatter). |
| `tmux-overview` | Owner utility: live view of one tmux session's windows/panes plus Claude plan usage (`tmux-overview <session>`; on this VPS also on PATH, per-machine symlink). `--compact --package <run-package>` renders the ≤7-line control-panel dashboard via `overview-compact.py` — plan-usage bar charts left, windows with roster-resolved seat names right; the `panel` subcommand embeds exactly that in the leader window's 8-row strip. |
| `overview-compact.py` | The compact dashboard renderer behind `tmux-overview --compact`: colored usage bars for Claude (5h/7d) AND the worker providers (GLM 5h/7d, Codex 7d) + DeepSeek balance + Sakana console note, plus every window with member seat names mapped pane→agent from `coordination/workers.md` (claude panes rewrite their own titles, so the roster is the name source). |
| `provider-usage.py` | Read-only poller for worker-harness plan limits → `~/.claude/rbtv-runtime/provider-usage.json`: Z.AI coding-plan quota endpoint (5h/weekly %), DeepSeek balance endpoint, Codex plan windows from its LOCAL session files (no API call; fresh only while a codex seat runs), Sakana marked console-only (no documented endpoint). Keys stay in opencode's store, sent only to each provider's own documented host, never printed. The compact loop re-polls when data is >10 min old. |
| `statusline-usage.py` | Claude Code statusline script (wired in the vault's `.claude/settings.local.json`): renders the status line, persists plan usage (5h/7d windows from the statusline payload's `rate_limits`) to `~/.claude/rbtv-runtime/plan-usage.{txt,json}` for `tmux-overview` to display, AND persists the session's pid map (`~/.claude/rbtv-runtime/session-pids/<sid>.json` — claude pid → transcript) so the rbtv `ctx-monitor` CLI can resolve a tmux pane's claude process to its EXACT transcript (per-pane context/model in `teamview`). |
| `system-design.md` | Designer-only: the kit's design rationale (see `CLAUDE.md` — run agents never read it; designers keep it updated). |

> **Successor note (2026-07-24, updated 2026-07-26):** the `tmux-overview` /
> `overview-compact.py` / `provider-usage.py` trio was promoted, generalized, into the rbtv repo
> as the **`teamview`** CLI (`orchestration/cli/teamview/`, branch `ignite/core-daemon`) —
> multi-account providers with in-use highlighting, kimi+google added, four size-responsive
> layouts, session auto-detection. The hold that kept these kit copies authoritative has EXPIRED:
> it was scoped to the then in-flight kg-views-rebuild run, which closed on 2026-07-24. Whether
> the kit now DROPS the trio for `teamview` or KEEPS it for the `panel` strip is an OWNER-GATED
> decision, open at `CLAUDE.md` § Known instance couplings — not settled here. Until it is ruled
> these copies stay in place and `panel` keeps using them.

## Starting a new run

1. Create a run package folder (normally under the owning project's `build/`):
   `{package}/CLAUDE.md` (roster + surface-ownership map + run-specific rules, pointing at
   `protocol.md`), `{package}/workers/{agent}/` seat folders (briefing `agent.md` from the
   template + `CLAUDE.md`/`AGENTS.md` loaders), `{package}/coordination/` (empty —
   script-managed). Settle the roster's shape BEFORE writing briefings: § Roster assembly (below)
   for the surface partition + checker coverage the ownership map records, § Run capacity for how
   many seats the box can carry.
2. The owner starts `leader` by hand in a tmux pane (first boot only — renewals relaunch it
   automatically, see 3); leader runs
   `python3 {team-kit}/coord.py --package {package} launch` (optionally `--only a,b` for staged
   launches) — one seat per briefing, harness/model/effort/cwd from each briefing's frontmatter;
   `window: yes` seats get their own named window (tab), the rest tile as panes in the leader
   window (hybrid layout). Launch auto-names everything: pane/window titled with the agent's
   name; claude seats also get a `/rename <agent>` injected after boot (checkin re-titles the
   pane too, so recoveries stay named). Leader's own session: type `/rename leader` yourself when
   you start it — nothing automates the pane the owner opened by hand.
   **Worker-mirror refresh:** a codex/opencode seat reads its rules from the `AGENTS.md` +
   `.agents/` MIRROR of its launch root, which only refreshes when the installer runs — and every
   `AGENTS.md` is gitignored, so drift is per-machine and invisible to git. `launch` therefore
   refreshes the mirror for each distinct non-claude launch root before opening any pane (once per
   root, not per seat; claude seats need none and trigger none). `close-seat --renew` does the same
   for the seat it relaunches. A refresh that fails WARNS and launches anyway — a broken installer
   must not be able to stop a run. A workspace with no `rbtv.json`, or one electing no mirrorable
   worker, is skipped silently.
3. Lifecycle: a seat ends with `checkout` — plain for the done disposition, `--renew --handoff
   "<note>"` to renew itself (two-step, CLI-taught; the handoff lands in its `memory.md`; no
   closer in that path; protocol item 8 carries the evidence) — which exports its transcript
   first (ephemeral seats use
   `depart`, which exports, checks out and kills their own pane in one command). `close <agent>
   [--renew]` is the FAILURE PATH, leader-gated and manual: a sonnet closer co-writes
   `workers/{agent}/memory.md`, then `close-seat` kills — and with `--renew` freshly relaunches —
   a seat that cannot check itself out (a memoryless `close: mechanical` seat, or one whose own
   renewal refused). No healthy renewal routes through it. The leader seat renews itself like any
   other seat (`checkout --renew --handoff "<note>"`): the relaunched leader lands back as a pane
   in the window its old
   pane occupied (the control panel), boots resume-first from `workers/leader/memory.md`
   (its "Resume here" section — it continues the run, never re-runs completed work), and gets
   the auto `/rename` like any launched claude seat; a bare `launch` still never boots leader.
   Everything else follows `protocol.md`.

## Run conduct and communication — both are read-and-follow, on every seat

Two documents bind every seat of a run, and neither is optional reading:

- **`communication.md` ships AS-IS.** A run adopts it by pointing every seat loader at this file by
  absolute path — never by copying it into the package, which forks it silently. Amendments inside a
  live run are that run's leader's rulings.
- **`conduct-template.md` is INSTANTIATED,** at bootstrap, as the package's own `conduct.md`: fill
  every `{{slot}}` (mission + done contract, terminology hook, budget + model policy — always
  measured per box). Once ratified it is FROZEN; amendments are leader rulings, each recorded as a
  sitting in the goal's `decisions.md`.

Every seat-folder loader lists both, with the protocol, as imperative read-and-follow steps — a
non-claude seat reads nothing ambiently, so a manual nothing points at is a manual nobody obeys.

## Roster assembly — partition by surface, then put a checker on every surface

Whoever assembles a run owns this, and it is decided BEFORE any briefing is written (S§4 — the
run-1 observer's "load-bearing structural lever"). Two moves that pull against each other, so both
are deliberate:

- **Partition by SURFACE, not by task.** Coordination cost is not spread evenly across a roster —
  it concentrates entirely where two seats' file-sets overlap. In run 1 every single coordination
  incident happened at an overlap (the generator, the ledger, the id counter); the seats with
  genuinely disjoint surfaces coordinated for FREE and produced zero incidents. So cut the work so
  each seat owns a disjoint set of files, and treat every remaining overlap as a cost you chose:
  make it an explicit single-writer critical section (`protocol.md` R-single-writer) and say so in
  the ownership map. Adding a seat to a shared surface is more expensive than it looks; splitting
  the surface first is usually cheaper than coordinating the split later.
- **Then put a checking vantage on every critical surface — on purpose.** A team's value is
  redundancy of vantage, not speed: in run 1 EVERY wrong number was caught by another seat or by
  re-computation, and not one by its author's own care. But checking only happens where vantages
  overlap — which the partition above deliberately minimizes. The one change that shipped
  unreviewed in run 1 was precisely the one no other seat's surface touched. So coverage cannot be
  left to hope: assign it.
- **The surface-ownership map carries BOTH columns.** The run package's `CLAUDE.md` map names, per
  surface, its single writer AND who checks it (a judge, a verifier, or a peer whose work reads
  it). A surface with no checker is listed explicitly as unchecked-by-choice, with the owner's
  acceptance — never left blank. A blank reads as "covered" to everyone who opens the map, which is
  the failure this rule exists to prevent.

## Run capacity — budget the box before you size the roster

Whoever assembles a run owns this; it is a property of the BOX, not of the work (queue 11 —
the kg-views-rebuild run hit its box's memory ceiling mid-run and the mitigation was a swapfile
added by hand, which is an environment patch, not a budget).

- **Seats are not free.** Budget RAM per seat before choosing the roster size: each harness
  session is a live process with its own context, and a wave of seats that fits on paper can
  still OOM the box. Measure one seat of each harness on the target box, multiply, leave headroom
  for the tools the seats themselves spawn — then set `max concurrent seats` and stage the launch
  (`launch --only a,b`) rather than starting everyone at once.
- **Headless browsers are serialized across the whole run** — one at a time, claimed and released
  by message (`protocol.md` R-serialized-browser). Chromium is the single biggest per-seat
  allocation most runs make, and several at once is the usual path to the ceiling.
- **State the ceiling in the run package's `CLAUDE.md`** — the box's memory ceiling, the max
  concurrent seats it implies, and which seats may spawn heavyweight processes. A budget nobody
  wrote down is re-derived wrongly by whichever seat launches next.
- **Swap is a safety net, not the budget.** Provisioning swap keeps a breach from killing seats;
  it does not raise the number of seats the box can actually run.

> **Naming note — SUPERSEDED (2026-07-25, ruling R29).** The earlier owner ruling (2026-07-24)
> kept this seat named `master`, holding it deliberately distinct from the system-definition
> registry's `leader` concept ("the master is not the team leader"). That ruling is SUPERSEDED:
> R29 finds the seat performed the KG `leader` function (per-team unblocking, arbitration, sole
> team voice to the owner), so it is re-keyed to `leader` here and in every kit artifact;
> `master` is reserved for the system-plane request door (R21). Run packages created before
> 2026-07-25 still name the seat `master` and are frozen — they are not re-keyed.

Prior-run provenance — the three proving-run packages are NOT stored beside this kit; `CLAUDE.md`
records the workspace that holds them. The improvement evidence (P1–P26) lives in the
`kg-edges-visualization-improvements` package: `team-observations.md` (tactical) and
`agent-teams-strategic-lessons.md` (strategic). First consumer run: the `kg-views-rebuild`
package, whose proposals P27–P38 are evidenced in its `run-observations.md` and `roster-review.md`.
The `coordinate` CLI redesign (T1–T6) is the `team-kit-redesign` package.
