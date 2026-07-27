# `teamview` — responsive team-run dashboard CLI

One live screen for a multi-agent tmux run: the session's windows/panes with agent names, plus
plan-limit bars for every AI provider account on the machine. Below the constant first line the
whole body CYCLES every ~10s — the windows/panes view (itself paged into as many views as the
height needs), then the plan-limits view, then back around. An orchestration-module component
(runnable CLI, python3 stdlib-only — no install step). Generalized: nothing user-, workspace-,
or machine-specific is baked in; accounts come from a config file or auto-discovery of whatever
harness credential stores exist.

Origin: promoted 2026-07-24 from a workspace team-kit's overview tooling after it proved
out on a live multi-agent run.

## Run

```bash
python3 orchestration/cli/teamview/teamview.py                  # session you are IN; from OUTSIDE
                                                                #   tmux: the only running session
python3 .../teamview.py <session>                               # any session by name (works from
python3 .../teamview.py session <session>                       #   outside tmux; both forms equal)
python3 .../teamview.py --package <run-package>                 # pane->agent names from the
                                                                #   team-kit roster (workers.md)
python3 .../teamview.py --once | --interval 5 | --refresh       # snapshot / cadence / poll now
python3 .../teamview.py --once --no-rotate                      # COMPLETE combined snapshot:
                                                                #   limits + every window/pane,
                                                                #   no view cycle (can exceed
                                                                #   terminal height)
python3 .../teamview.py --help-providers | --help-config        # reference: usage sources /
                                                                #   accounts schema (-h stays short)
python3 .../teamview.py --help-security | --help-panes          # audit surface (writes/endpoints/
                                                                #   never-touches-tmux) / pane states
python3 .../teamview.py --audit                                 # resolved accounts -> source kind ->
                                                                #   redacted path -> last poll result
                                                                #   (never prints a key or full path)
python3 .../teamview.py --selftest                              # must exit 0 after ANY edit here
```

Outside tmux with several sessions running and no name given, it lists the candidates and
exits rather than guessing. An UNKNOWN session name is a refusal, not an empty frame: it
prints the bad name, a closest-match suggestion, and the live session list to stderr and
exits 2 (a wrapper script never records success for a view that showed nothing). An
explicit `--config` path that does not exist warns on stderr before falling back to
account auto-discovery — the fallback is never silent.

`--interval` is the DISPLAY repaint cadence only — it never re-polls providers; provider
data refreshes via `--provider-ttl` (background) or `--refresh` (poll NOW — codex excepted,
whose usage is a local session-file parse with no endpoint to re-poll; pair `--refresh`
with `--once` for a one-shot fresh frame, since without `--once` it enters the live loop).

Symlink it onto PATH per machine (like `ignite` / `sd-graph` — never synced by git):
`ln -s <abs>/teamview.py ~/.local/bin/teamview && chmod +x ~/.local/bin/teamview`.

## What it shows

- **Session block** — an ASCII grid: each window is a column (bold header, `*` = active
  window) with its PANES stacked beneath it; a seat whose TUI reports it is WORKING carries a
  trailing `+` (the working indicator — detected by CHANGE: a pane whose visible content
  differs across two samples ~0.6s apart is actively rendering — spinner cycling, tokens
  streaming, tool output. A frozen title spinner glyph is NOT trusted, since it persists when a
  turn ends). A pane whose harness has exited (a bare shell) renders dim with an explicit
  `shell` tag — distinct from a live pane whose agent info merely failed to resolve. An
  empty-titled pane with no roster name renders a dim `?`. Work is often bursty,
  so a seat flips between `+` and unmarked as it starts and finishes turns — that is honest,
  not a glitch. Names resolve pane-id → agent from a team-kit
  run package's `coordination/workers.md` (`--package`, or `RBTV_TEAMVIEW_PACKAGE`) because
  agent TUIs rewrite their own pane titles; fallback is the cleaned pane title. Pure ASCII
  markers throughout — no arrow or box-drawing glyphs (ambiguous-width characters break column
  alignment in some terminal fonts). Narrow/tiny layouts render each window as its own flowed
  line block (`*name:` then panes), wrapping between panes. The WHOLE VIEW CYCLES every ~10s
  (stateless — derived from wall clock, so the refresh loop cycles naturally and `--once`
  shows whichever page is current): the windows view — paged into as many views as the height
  needs, with a `(windows N-M/T - rotating)` note — then ONE plan-limits view, then back
  around; nothing is permanently hidden, and the first line stays constant across every phase.
  A SINGLE window with more panes than fit rotates its OWN pane list
  the same way, with a `(panes N-M/T - rotating)` note — a 6-seat window in a 1-pane-tall
  slot never renders as if it were a dead 1-seat window with no hint the rest exist. A
  CRITICAL pane — past its own ctx-refresh threshold, at/above 85% context regardless of
  `--package`, or stuck awaiting approval — is PINNED into every rotation page instead of
  cycling out of view (the note gains a `· pinned` tag when this holds a page steady); the
  pin holds the WHOLE cycle on that windows page — the limits view waits until the pane is
  dealt with, while the alarm-rollup header line keeps every phase honest.
  `--no-rotate` disables the cycle entirely for a COMPLETE combined snapshot in one frame —
  the limits block plus every window and every pane at once, best paired with `--once` (the
  output can grow taller than the terminal). A seat stuck at a permission or trust prompt renders its name RED
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
- **Marker legend** — the full-screen (`full`) layout's footer explains every marker
  (`name?!`, `ctxN%!`, the color bands, `+`, `…`, `*`, `ctxN%`, `ctx~`, `Nm/Nh`, in-use
  color, `name shell`, `?`) — ALARM items first, so when the legend must drop lines at a
  narrow width the alarm keys are the last lost, never the first; it is
  WORD-WRAPPED to the frame's own width so a narrow pane never hard-clips an item mid-word
  (previously it could silently drop everything past ~80 columns, e.g. cutting
  "ctx~ = pane match uncertain" down to "...pane ma~" with no other sign anything was
  missing). The same legend text is also in `-h`'s own description, so its meaning is
  discoverable without ever running a live frame — and `--help-panes` documents every pane
  state with its cause and remedy. The strip/narrow/tiny layouts append a ONE-line mini
  legend (`?!=approval · ctx%!=threshold · red>=85 yel>=60 · …`) — alarm keys first, tail
  items dropped as width shrinks. Truncation glyphs are split: `…` marks EVERY text cut
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

## Responsive layouts (chosen from the pane's own size, re-measured every frame)

| Pane shape | Layout |
|------------|--------|
| ≥70 cols, ≥16 rows | **full** — sectioned view: big bars + per-window member list |
| wide, <16 rows | **strip** — full-width window grid and full-width folded bars, one per cycle phase (the team-kit control-panel shape); `--no-rotate` renders them side by side |
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
