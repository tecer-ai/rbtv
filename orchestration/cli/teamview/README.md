# `teamview` — responsive team-run dashboard CLI

One live screen for a multi-agent tmux run: the session's windows/panes with agent names, plus
plan-limit bars for every AI provider account on the machine.

> **teamview RENDERS the run's state; it no longer SENSES it** (settle ledger R24, task 7.34).
> `team-monitor` is the run's one raw-source sensor — it reads the tmux panes, the harness session
> files and `/proc`, and writes ONE canonical snapshot to `{goal}/runs/run-{n}/state.json`.
> teamview reads that file and nothing else. It **always shows the snapshot's age**, and a **stale
> snapshot renders as a visible WARNING** rather than as silently-current data. See
> [Proving the boundary](#proving-the-boundary) for what is deliberately outside it, and
> [What changed in R24](#what-changed-in-r24) for the two behaviour changes this cost. Below the constant first line, the
body renders the COMBINED view (limits + every window/pane) statically whenever the measured
frame is large enough to show everything at once; only when it is too small does the body CYCLE
every ~10s instead — the windows/panes view (itself paged into as many views as the height
needs), then the plan-limits view, then the messages view (the coordination log's last sends,
off the snapshot), then back around. `--view {auto,limits,panes,messages,combined}` pins
one body instead of the adaptive default. An orchestration-module component (runnable CLI,
python3 stdlib-only — no install step). Generalized: nothing user-, workspace-, or
machine-specific is baked in; accounts come from a config file or auto-discovery of whatever
harness credential stores exist.

Origin: promoted 2026-07-24 from a workspace team-kit's overview tooling after it proved
out on a live multi-agent run.

## Run

```bash
python3 orchestration/cli/teamview/teamview.py                  # the run package found by walking
                                                                #   UP from the current directory
python3 .../teamview.py --package <run-folder>                  # or name the run folder outright
                                                                #   (the canonical form)
python3 .../teamview.py <session>                               # a name is CHECKED against the
python3 .../teamview.py session <session>                       #   snapshot's own `session` field
python3 .../teamview.py --once | --interval 5 | --refresh       # snapshot / cadence / poll now
python3 .../teamview.py --once --no-rotate                      # COMPLETE combined snapshot:
                                                                #   limits + every window/pane,
                                                                #   no view cycle (can exceed
                                                                #   terminal height)
python3 .../teamview.py --view limits | panes | messages         # pin one body: bars only /
                                                                #   windows+panes only / last
                                                                #   coordination sends only, no
                                                                #   alternation ever (auto is
                                                                #   the fit-based default;
                                                                #   combined = --no-rotate)
python3 .../teamview.py --help-providers | --help-config        # reference: usage sources /
                                                                #   accounts schema (-h stays short)
python3 .../teamview.py --help-security | --help-panes          # audit surface (writes/endpoints/
                                                                #   never-touches-tmux) / pane states
python3 .../teamview.py --audit                                 # resolved accounts -> source kind ->
                                                                #   redacted path -> last poll result
                                                                #   (never prints a key or full path)
python3 .../teamview.py --selftest                              # must exit 0 after ANY edit here
```

**Nothing resolves to a guess.** With no `--package` and no `state.json` in any parent
directory, teamview REFUSES — printing the two runnable commands that fix it (point at a run
folder; or start the sensor if the run folder is right but has no snapshot) to stderr, and
exiting 2 with an empty stdout. A positional name that disagrees with the snapshot's own
`session` refuses the same way. This is the old unknown-session refusal's contract kept
verbatim: a wrapper script must never record success for a view that showed nothing.

Every failure to READ the snapshot — missing, corrupt, wrong-shaped, or listing zero panes —
renders as a loud error frame naming the cause, never as an empty dashboard. An empty dashboard
reads as a quiet room, and that mistake has a number in this project (G-153).

An explicit `--config` path that does not exist warns on stderr before falling back to
account auto-discovery — the fallback is never silent.

`--interval` is the DISPLAY repaint cadence only — it never re-polls providers; provider
data refreshes via `--provider-ttl` (background) or `--refresh` (poll NOW — codex excepted,
whose usage is a local session-file parse with no endpoint to re-poll; pair `--refresh`
with `--once` for a one-shot fresh frame, since without `--once` it enters the live loop).

Symlink it onto PATH per machine (like `ignite` / `sd-graph` — never synced by git):
`ln -s <abs>/teamview.py ~/.local/bin/teamview && chmod +x ~/.local/bin/teamview`.

## What it shows

- **Session block** — an ASCII grid: each window is a column (bold header, `*` = active
  window; see the R24 note on window LABELS below) with its PANES stacked beneath it; a seat
  that has been ACTIVE RECENTLY carries a trailing `+` (⚠ R24 CHANGED THIS SIGNAL'S INSTRUMENT
  AND ITS MEANING: it used to mean "this pane's visible content differed across two tmux
  captures ~0.6s apart"; it now means "this seat's harness wrote to its transcript within 45s
  of the capture". Coarser, and from a different instrument — relabelled here rather than
  silently reused under the old description). A pane whose harness has exited (a bare shell) renders dim with an explicit
  `shell` tag — distinct from a live pane whose agent info merely failed to resolve. An
  empty-titled pane with no roster name renders a dim `?`. Work is often bursty,
  so a seat flips between `+` and unmarked as it starts and finishes turns — that is honest,
  not a glitch. Seat names come from the snapshot's own `seat` field (team-monitor resolves
  them against the run roster) because agent TUIs rewrite their own pane titles; a pane whose
  occupant has not checked in yet carries no seat name and falls back to its cleaned title —
  a launched-but-silent harness is a real state and is reported as one, never guessed. Pure ASCII
  markers throughout — no arrow or box-drawing glyphs (ambiguous-width characters break column
  alignment in some terminal fonts). Narrow/tiny layouts render each window as its own flowed
  line block (`*name:` then panes), wrapping between panes. The BODY renders the COMBINED
  view (limits + every window/pane) STATICALLY whenever the measured frame is large enough to
  show everything at once; only when it is too small does the view CYCLE every ~10s instead
  (stateless — derived from wall clock, so the refresh loop cycles naturally and `--once`
  shows whichever page is current): the windows view — paged into as many views as the height
  needs, with a `(windows N-M/T - rotating)` note — then ONE plan-limits view, then ONE
  messages view (see below; the slot exists only when the snapshot carries a message tail),
  then back around; nothing is permanently hidden, and the first line stays constant across
  every phase. `--view {auto,limits,panes,messages,combined}` pins one body instead of this
  adaptive default: `limits`, `panes`, or `messages` show only that body at every tick (never
  alternating), `combined` forces the static
  combined frame (= `--no-rotate`), and `auto` (default) is the fit-based behavior above.
  The WINDOWS header carries the run's average dispatch payload — `dispatch ~N tok avg/seat`,
  the ~tokens a freshly launched seat must read before working regardless of its prompt or
  agent type (shared boot files + its own `seat.md`/`memory.md`), rendered straight off the
  snapshot's `dispatch_tokens` field and rendered as NOTHING (never a fake 0) when the
  snapshot predates the field.
- **Messages block** — the coordination log's last sends off the snapshot's `messages` field
  (team-monitor parses `coordination/messages.md`; teamview never opens the log — R24), in
  log order (newest LAST), one aligned row each: how long ago · sender → recipient · as much
  of the text as the row can hold (`…` marks the cut; the age and route columns pad to the
  block's widest so the text starts on one straight edge). Overflow drops the OLDEST rows
  with a `(+N older not shown)`
  note, never the newest. A snapshot without the field renders a loud explanation on the
  messages page rather than an empty one.
  A SINGLE window with more panes than fit rotates its OWN pane list
  the same way, with a `(panes N-M/T - rotating)` note — a 6-seat window in a 1-pane-tall
  slot never renders as if it were a dead 1-seat window with no hint the rest exist. A
  CRITICAL pane — past its own ctx-refresh threshold, at/above 85% context regardless of
  `--package`, or stuck awaiting approval — is PINNED into every rotation page instead of
  cycling out of view (the note gains a `· pinned` tag when this holds a page steady); the
  pin holds the WHOLE cycle on that windows page — the limits view waits until the pane is
  dealt with, while the alarm-rollup header line keeps every phase honest. The pin only
  matters while CYCLING: a frame that fits the static combined view renders every window and
  pane regardless, so nothing is hidden for the pin to hold open.
  `--no-rotate` (= `--view combined`) disables the cycle entirely for a COMPLETE combined
  snapshot in one frame — the limits block plus every window and every pane at once, best
  paired with `--once` (the output can grow taller than the terminal). A seat stuck at a
  permission or trust prompt renders its name RED
  with a trailing `?!` (detected in the same busy-sampling capture — claude's numbered
  Yes/No dialogs, codex's "Action Required", and generic trust-this-folder prompts — no
  extra tmux call), overriding the busy `+` marker.
- **Per-seat context-refresh warning** — with `--package`, each seat's `ctx-refresh:` % is
  read from its OWN `workers/<agent>/agent.md` frontmatter (no key = no threshold, never
  enforced). A pane whose context used % has reached that seat's own threshold renders its
  ctx cell RED with a trailing `!` (e.g. `ctx55%!`), regardless of the normal green/yellow/
  red color band it would otherwise get. WITHOUT `--package` this check never runs — the
  session-stats line then carries a `no --package: thresholds/roster off` cue so a plain
  green `ctxN%` is never mistaken for "confirmed under threshold" when it really means "never
  checked" (an operator made a wrong renewal call on exactly this silent gap).
- **Graceful degradation at every width** — the no-package cue, every rotation footer, and
  every PLAN LIMITS/ctx VALUE shrink to a shorter but still-COMPLETE form as the pane
  narrows (down to ~60 cols) instead of relying on the outer hard clip's blind mid-word cut.
  A bar and its suffix drop before the percent number does; a seat's harness/age drop before
  its ctx% (and any past-threshold `!`) does; a rotation footer shrinks from
  `(windows 2-3/5 - rotating)` down to a bare `(2-3/5)` or `+3` before disappearing
  entirely — it is never shown at a length that would need cutting mid-value.
- **System RAM+CPU readout** — the header line also carries available RAM and CPU load
  (`RAM 1989MB/7746MB  CPU 0.7/4`), read stdlib-only from `/proc/meminfo` and
  `os.getloadavg()`/`os.cpu_count()` — no new deps. Colored by pressure (green comfortable,
  yellow past ~1.5GB-available/75%-load, red past ~500MB-available/at-or-over core count)
  so an operator or the watcher spots an OOM risk at a glance (this run hit an OOM cascade
  with no such warning). Degrades the same graceful way as every other cue — RAM detail
  shrinks before CPU drops, then the whole cue vanishes rather than clip mid-value — and
  disappears entirely (no crash) on a platform where neither reading is available.
- **Alarm rollup line** — every layout's windows header also carries a fixed one-line
  rollup — `13 panes · worst ctx94%~ · 1 red · 0 ?!` (total panes, worst context %, count
  at/past red, count awaiting approval) — above the rotating detail, so a single glance
  proves (or disproves) "nothing is alarming" even when rotation currently hides most
  panes. It shrinks to a short form (`13p ctx94%~ 1r 0?!`) before ever clipping.
- **Marker legend — OFF the dashboard entirely** (owner ruling 2026-07-28). No layout renders
  a legend at any size, on either phase: every row goes to data. This REVERSES the earlier
  decision that put a one-line mini legend on the strip/narrow/tiny layouts, and the accepted
  cost is stated plainly — an operator on a small pane now has no on-screen key for `?`
  (awaiting approval) or the color bands, and must run the command below to decode them.

  The key lives in one place: **`teamview interface-legend`** — prints every marker, one per
  line, and exits. It is a positional subcommand intercepted BEFORE package discovery, so it
  works from anywhere, including outside a run package where the dashboard itself refuses with
  exit 2; reading the key never depends on having a live run. It touches no snapshot, no cache,
  no network. It renders from the SAME `LEGEND_ITEMS` / `LEGEND_CTX` tuples the pane cells mark
  with, so a marker added to the dashboard cannot silently go undocumented (pinned by a
  selftest). The same legend text remains in `-h`'s description, and `--help-panes` documents
  every pane state with its cause and remedy. Truncation glyphs are split: `…` marks EVERY text cut
  (names, titles, clipped lines); `~` means ONLY ctx-match uncertainty, never truncation.
  Color-band thresholds are explicit everywhere: green <60, yellow <85, red ≥85 (plain red
  = high value; red with `!` = past this seat's own threshold). The console-only PROVIDER group (Sakana /
  Google / Kimi — no readable usage endpoint) is word-wrapped the same way in the `full` and
  `narrow` layouts, so a long provider list never hard-clips mid-word either (e.g. cutting
  "google (key present; aistudio.google.com)" down to "...google (ke~").
- **Per-pane agent info** — every pane row also carries the agent running in it:
  `seat+ harness:model ctxN% age` — harness (the pane command, dim), model, context-window
  used % (colored green <60 / yellow <85 / red ≥85), and last-activity age (`now`, `Nm`,
  `NhMMm`, `NdNh`). Resolved by the sibling **ctx-monitor** CLI
  (`orchestration/cli/ctx-monitor/ctx_monitor.py`, imported by path) from each harness's own
  session record — claude transcript (exact pid→transcript map when the team-kit statusline
  is installed), codex rollout, opencode db, kimi wire, argv/TUI fallbacks — see its README.
  Without ctx-monitor the rows degrade to seat + pane command.
- **Plan-limit bars** — one bar per usage window per account, colored by headroom (green <60%,
  yellow <85%, red ≥85%); money-balance and console-only providers render as footer notes;
  stale local snapshots carry `as of <time>`, and the full layout's `providers polled Nm
  ago` header adds `— some bars older, see per-bar 'as of'` whenever any bar carries such
  a stamp, so the poll age never over-claims a local-parse bar's freshness. A model-scoped
  weekly like `7d fable` is a SUBSET of the plain `7d` window (that model's usage counts
  against both bars — see `--help-providers`). The account each harness ACTUALLY uses renders
  CYAN (bold alone proved invisible in some terminal themes); extra accounts render dim.
  Window headers in the session grid are bold+underlined to separate them from pane rows.

Every layout leads with two fixed rows: the **session-stats line** (windows · panes · time) on its own — constant across the whole cycle — then the current view's own bold+underlined header (`WINDOWS · PANES` or `PLAN LIMITS`), carrying the alarm rollup, scoped over the body beneath. So the session stats are never misread as a table header, and every cycle phase names itself. (`--no-rotate` renders both headers in its one combined frame.)

## Proving the boundary

The R24 criterion is that **no raw-source read remains** in teamview. Two lanes are deliberately
outside that boundary, and they are NAMED rather than quietly scoped out — a proof that passes
because someone narrowed it, without saying what was narrowed away, is theatre.

| Lane | Why it is outside | Its reads |
|---|---|---|
| **Provider plan-limit bars** | They read PROVIDER ACCOUNTS, not run state. Task 7.34's own `_Note:_` orders them left exactly as they are: *"do not 'purify' them out while refactoring."* | `ps_processes` (`ps -eo pid=,args=`), `claude_account_of` (`/proc/<pid>/environ`, for `CLAUDE_CONFIG_DIR` only), `opencode_store`, `claude_oauth_windows` / `parse_claude_statusline`, `codex_windows_from_rl` |
| **Box CPU usage %** | `state.json`'s `box{}` carries RAM, swap, load, cores and memory pressure — and NO cpu field. Ruled PROVISIONAL by the run-2 leader (2026-07-27), extending the `_Note:_`'s own classification to a second named lane. | `cpu_usage_pct` (`/proc/stat`) |

⚠ **Box CPU is not a field to "just move" into `box{}` later.** `cpu_usage_pct` is a
**between-frames delta** — teamview repaints every ~1s, so it reads like `top`'s. team-monitor
captures every ~20s. Adding a `cpu` field at the sensor's cadence, under the same label, would
silently turn a ~1-second reading into a 20-second average. Whoever closes that follow-on must
change the LABEL too, or not ship it.

`--selftest` proves the boundary mechanically, and it is an **AST walk, not a grep**: written as
a text scan it matched this file's own prose — the module docstring's `/proc/meminfo`, the
`--help-security` text, and the source of the check itself. A proof that counts the words
DESCRIBING a read as a read is not a proof. The hand-runnable grep, for a human who wants to see
it directly (every hit must fall in a lane above):

```bash
grep -n '/proc/\|"tmux"\|ctx_monitor' teamview.py | grep -v '^\s*#'
```

## What changed in R24

Two behaviour changes, stated rather than left to be discovered:

1. **Bare `teamview` no longer auto-picks the only running tmux session.** It resolves a run
   package — `--package`, else a walk UP from the current directory (the convention `coordinate`
   already uses, so it keeps working from any seat pane). From OUTSIDE any run package it now
   refuses with the exact command to run. That auto-pick was a *tmux* capability, and R24 removes
   teamview's right to ask tmux anything; restoring it would mean inventing a scan of
   `.rbtv/goals/*/runs/*` from an assumed vault root, a discovery convention this system does not
   have.

2. **Window headers show `INDEX NAME`, and the `*` marker works again.** Field (1) of the R24
   follow-on is CLOSED. The sensor chain now asks tmux for `#{window_name}`, `#{window_active}`
   and `#{pane_active}` alongside `#{window_index}` (`ctx_monitor.list_panes`), and
   `team_monitor` carries all three into `seats[].window_name` / `.window_active` /
   `.pane_active`.

   The INDEX always leads the header and is never dropped — it is the tmux target, while the
   name is display-only and drifts independently of what the window holds.

   The two active flags are **distinct facts and are never collapsed**: tmux has one active
   window per SESSION and one active pane per WINDOW. So `*` on a header marks the single tab
   you'd land on when attaching, while `*` prefixing a seat name marks that window's focused
   split — several of those show at once, and the starred header is what ranks them. It is a
   PREFIX by design: the suffix slot already carries `+` (busy) and `?` (awaiting approval),
   and cells shrink from the right, so a suffixed star would be the first casualty on exactly
   the narrow frames where focus matters most.

   A snapshot written by a pre-follow-on sensor still renders — bare index, nothing starred.
   It degrades by one field; it never blanks or crashes.

   Field (2), box CPU%, is deliberately NOT closed with it — at the sensor's ~20s cadence it
   becomes a different metric wearing teamview's ~1s label. See `ideas.md`.

Also new: `roster_absent` (the GHOSTROW input — a roster row whose pane left the room, or whose
pane is still there holding no harness process) renders as a trailing `absent` pseudo-window.
Dropping it would render a vanished seat as nothing, which is absence indistinguishable from
health.

## Responsive layouts (chosen from the pane's own size, re-measured every frame)

| Pane shape | Layout |
|------------|--------|
| ≥70 cols, ≥16 rows | **full** — sectioned view: big bars + per-window member list |
| wide, <16 rows | **strip** — full-width window grid and full-width folded bars, one per cycle phase when cycling (the team-kit control-panel shape); `--no-rotate`/`--view combined` render them side by side |
| <70 cols, tall | **narrow** — stacked mini-bars + window list |
| <70 cols, <18 rows (≈1/6 screen) | **tiny** — token summary lines, no bars. Plan-usage limits render ONE `label: N%` per line (never two flowed onto the same line) so a percent can never visually read as belonging to a neighboring label at this width — and the percent KEEPS its green/yellow/red urgency color (color costs zero columns; a bare `97%` rendering identically to `12%` was a verified false all-clear) |

## Providers and sources (read-only; keys never printed, sent ONLY to their own provider's documented endpoint)

| Provider | Source | Shows |
|----------|--------|-------|
| claude | per-account OAuth usage endpoint — `GET api.anthropic.com/api/oauth/usage` with the STORED `accessToken` from that account's `{config_dir}/.credentials.json` (the same call the Claude Code `/usage` screen makes; read-only, owner-sanctioned — see Hard rule below; tokens are never refreshed, an expired one falls back to the statusline-persisted `rate_limits` JSON until that account runs a real session) | 5h/7d bars PLUS every model-scoped weekly window the plan carries (e.g. `7d fable`); which Claude ACCOUNT is in use comes from the live processes' own `CLAUDE_CONFIG_DIR`, never from statusline recency |
| codex | LOCAL `~/.codex/sessions/**/rollout-*.jsonl` `payload.rate_limits` (no API call) | plan bars; "as of <time>" when the snapshot is stale |
| zai | `GET https://api.z.ai/api/monitor/usage/quota/limit` (`Authorization: <key>`, no Bearer) | 5h + weekly used-% bars, plan tier |
| deepseek | `GET https://api.deepseek.com/user/balance` (Bearer) | money balance |
| kimi | subscription OAuth login: no usage endpoint → console-only group. Opt-in: an `sk-kimi` key (mint at kimi.com/code/console, supply via an `env`/`file` source) polls `GET api.kimi.com/coding/v1/usages` — community-verified, not officially documented. A Moonshot platform key instead uses the documented `GET /v1/users/me/balance` | login note / per-model plan bars / balance |
| google | no usage-read endpoint for an AI Studio API key (verified 2026-07-24; project-level quota IS readable via gcloud OAuth + Cloud Monitoring — out of scope for key polling) | console-only group |
| sakana | no balance/usage endpoint (verified 2026-07-24: chat/responses/models only, no rate-limit headers documented) | console-only group |

Providers with no readable usage nest under one visually distinct footer line —
`no usage API > sakana (key present; console.sakana.ai) · google (…) · kimi (…)` — yellow-
prefixed and separate from the API-backed facts (balances) above it.

**Auditor surface:** `--help-security` prints the complete write-set (only the provider
cache file), the complete endpoint list, and the never-mutates-tmux guarantee (every tmux
call is read-only); `--audit` dumps each resolved account as
`provider:name -> source kind -> redacted path -> last poll result` — paths redact to
`…/basename`, env vars show their NAME only, and no key, token, or full path is ever
printed.

**Hard rule:** never add a probe of an undocumented endpoint with stored keys — verify the
endpoint in the provider's official docs first, read-only GETs only. **One owner-sanctioned
exception (2026-07-24):** the read-only `GET api.anthropic.com/api/oauth/usage` call with a
Claude account's stored access token — it is the exact call the Claude Code `/usage` screen
makes and the only source of the model-scoped weekly windows the owner asked for. The
sanction covers that single read-only GET and nothing more: teamview MUST NOT refresh,
rotate, or write tokens (an expired token means statusline fallback until that account runs
a real session).

## Accounts config (optional — multiple accounts per provider)

`~/.config/rbtv/teamview.json` (or `--config` / `RBTV_TEAMVIEW_CONFIG`):

```json
{"accounts": [
  {"provider": "zai",      "name": "main", "source": {"type": "opencode"}},
  {"provider": "zai",      "name": "alt",  "source": {"type": "env", "var": "ZAI_KEY_ALT"}},
  {"provider": "deepseek", "name": "main", "source": {"type": "opencode"}},
  {"provider": "claude",   "name": "main", "source": {"type": "statusline",
                            "path": "~/.claude/rbtv-runtime/plan-usage.json"}},
  {"provider": "codex",    "name": "main", "source": {"type": "codex-local"}},
  {"provider": "kimi",     "name": "api",  "source": {"type": "env", "var": "MOONSHOT_API_KEY"}}
]}
```

`source.type`: `opencode` (that harness's credential store; optional `store_key` override) ·
`env` · `file` · `statusline` · `codex-local` · `kimi-local`. An account is marked **IN USE**
(cyan) only while a LIVE agent process on this box spends it — claude resolved through each
process's own `CLAUDE_CONFIG_DIR`, opencode through its `--model <provider>/<id>` prefix,
codex/kimi by process name; recomputed every frame, since in-use flips far faster than the
provider poll. An account whose credential exists with nothing running is **CONFIGURED**
(dim) — a distinct state, not a weaker one. Source type no longer implies in-use: keying on
"a credential exists" marked six idle providers in use while dimming the two Claude accounts
a whole run was burning (`issues.md` G-17). Pin either state per account with
`"in_use": true/false`. With no config, accounts are auto-discovered from the stores present
on the machine.

**Multiple Claude accounts** — one config dir per account, discovered automatically: any
`~/.claude-<tag>` directory becomes account `claude:<tag>` reading
`~/.claude/rbtv-runtime/plan-usage-<tag>.json`. The companion statusline script keys its output
file by `CLAUDE_CONFIG_DIR`, so a session launched as
`CLAUDE_CONFIG_DIR=~/.claude-<tag> claude` (wrap it in a tiny launcher, e.g. `claude-<tag>`)
tracks that account's windows separately; the default `~/.claude` account is untouched. An
account with no sessions yet reports "no data file yet" rather than vanishing.

## Caching

Provider data caches at `$XDG_CACHE_HOME/rbtv/teamview-providers.json` (default
`~/.cache/rbtv/`), re-polled in a detached background process when older than
`--provider-ttl` (default 600 s) so render frames never block on the network.
