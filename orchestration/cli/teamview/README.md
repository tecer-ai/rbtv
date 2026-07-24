# `teamview` — responsive team-run dashboard CLI

One live screen for a multi-agent tmux run: the session's windows/panes with agent names, plus
plan-limit bars for every AI provider account on the machine. An orchestration-module component
(runnable CLI, python3 stdlib-only — no install step). Generalized: nothing user-, workspace-,
or machine-specific is baked in; accounts come from a config file or auto-discovery of whatever
harness credential stores exist.

Origin: promoted 2026-07-24 from the second-brain team-kit's `tmux-overview` /
`overview-compact.py` / `provider-usage.py` trio (first proven on the kg-views-rebuild run).

## Run

```bash
python3 orchestration/cli/teamview/teamview.py                  # dashboard of the session you are IN
python3 .../teamview.py <session>                               # any session by name
python3 .../teamview.py --package <run-package>                 # pane->agent names from the
                                                                #   team-kit roster (workers.md)
python3 .../teamview.py --once | --interval 5 | --refresh       # snapshot / cadence / poll now
python3 .../teamview.py --selftest                              # must exit 0 after ANY edit here
```

Symlink it onto PATH per machine (like `ignite` / `sd-graph` — never synced by git):
`ln -s <abs>/teamview.py ~/.local/bin/teamview && chmod +x ~/.local/bin/teamview`.

## What it shows

- **Session block** — an ASCII grid: each window is a column (bold header, `*` = active
  window) with its PANES stacked beneath it; a seat whose TUI reports it is WORKING carries a
  trailing `+` (the working/thinking indicator, derived from the busy glyph agent TUIs write
  into their pane title, re-encoded ASCII-safe). A `legend:` line explains the markers in
  place. Names resolve pane-id → agent from a team-kit run package's `coordination/workers.md`
  (`--package`, or `RBTV_TEAMVIEW_PACKAGE`) because agent TUIs rewrite their own pane titles;
  fallback is the cleaned pane title. Quota renewal times render as plain `renews <time>` —
  no arrow or box-drawing glyphs anywhere (ambiguous-width characters break column alignment
  in some terminal fonts). Narrow/tiny layouts fall back to inline `window[pane pane]` tokens.
- **Plan-limit bars** — one bar per usage window per account, colored by headroom (green <60%,
  yellow <85%, red ≥85%), with reset times; money-balance and console-only providers render as
  footer notes. The account each harness ACTUALLY uses is highlighted `*bold`; extra accounts
  render dim.

## Responsive layouts (chosen from the pane's own size, re-measured every frame)

| Pane shape | Layout |
|------------|--------|
| ≥70 cols, ≥16 rows | **full** — sectioned view: big bars + per-window member list |
| wide, <16 rows | **strip** — bars fold into 1–3 columns beside a flowed window list (the team-kit control-panel shape) |
| <70 cols, tall | **narrow** — stacked mini-bars + window list |
| <70 cols, <18 rows (≈1/6 screen) | **tiny** — token summary lines, no bars |

## Providers and sources (read-only; keys never printed, sent ONLY to their own provider's documented endpoint)

| Provider | Source | Shows |
|----------|--------|-------|
| claude | statusline-persisted `rate_limits` JSON (a Claude Code statusline script writes it; path per account) | 5h/7d bars (+ model-specific windows when reported) |
| codex | LOCAL `~/.codex/sessions/**/rollout-*.jsonl` `payload.rate_limits` (no API call) | plan bars; "as of <time>" when the snapshot is stale |
| zai | `GET https://api.z.ai/api/monitor/usage/quota/limit` (`Authorization: <key>`, no Bearer) | 5h + weekly used-% bars, plan tier |
| deepseek | `GET https://api.deepseek.com/user/balance` (Bearer) | money balance |
| kimi | subscription login state (`~/.kimi/credentials/`) — no usage endpoint; an API-key account uses Moonshot `GET /v1/users/me/balance` (`api.moonshot.ai` → `.cn` fallback) | login note / balance |
| google | no usage-read endpoint | key presence + console pointer (aistudio.google.com) |
| sakana | no balance endpoint (checked 2026-07-24) | key presence + console pointer (console.sakana.ai) |

**Hard rule:** never add a probe of an undocumented endpoint with stored keys — verify the
endpoint in the provider's official docs first, read-only GETs only.

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
`env` · `file` · `statusline` · `codex-local` · `kimi-local`. Harness-backed types
(opencode / codex-local / statusline / kimi-local) are marked IN USE by default — they are what
the harnesses actually read; override per account with `"in_use": true/false`. With no config,
accounts are auto-discovered from the stores present on the machine.

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
