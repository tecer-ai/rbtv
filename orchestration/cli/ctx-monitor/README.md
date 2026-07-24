# `ctx-monitor` — per-pane agent context / model / activity CLI

For every pane of a tmux team session, report the agent running there: **harness**, **model**,
**context-window used %**, and **last activity** — read from each harness's OWN session record
on disk. Local files only: no network calls, no credentials read. An orchestration-module
component (runnable CLI, python3 stdlib-only — no install step); also importable as a module —
`teamview` imports it for its per-pane columns.

Relation to the orchestration PostToolUse hook (`orchestration/hooks/context-monitor.py`):
that hook is **Claude-Code-only by construction** — Claude pipes it hook stdin and it parses
Claude's transcript format; no other harness ever invokes it. This CLI is the harness-agnostic
twin for observing panes FROM OUTSIDE a session; the hook keeps advising the conductor
in-session.

## Run

```bash
python3 orchestration/cli/ctx-monitor/ctx_monitor.py                    # panes of the session you are IN
python3 .../ctx_monitor.py <session> [--json]                           # any session by name
python3 .../ctx_monitor.py --pane %3                                    # one pane
python3 .../ctx_monitor.py --cwd <dir> --harness claude                 # no tmux: records directly
python3 .../ctx_monitor.py --selftest                                   # must exit 0 after ANY edit here
```

Text output is one aligned row per pane (`pane win title harness model ctx activity source`);
`--json` emits the same records with raw numbers (`ctx_pct`, `ctx_tokens`, `window_tokens`,
`as_of` epoch).

## Sources (best first; per harness)

| Harness | Record | Context math | Model | Activity |
|---------|--------|--------------|-------|----------|
| claude | pid→transcript map `~/.claude/rbtv-runtime/session-pids/<sid>.json` (EXACT — written by the team-kit `statusline-usage.py` running inside every session); fallback: cwd-heuristic over `~/.claude/projects/<munged-cwd>/*.jsonl`, shown as source `transcript~` | last main-chain assistant `usage`: input + cache_read + cache_creation vs the model window (200k; 1M for fable and `[1m]` ids; `RBTV_CONTEXT_WINDOW` env overrides). Synthetic/zero-usage entries (errors, interrupts) skipped | `message.model` | transcript mtime |
| codex | newest `~/.codex/sessions/**/rollout-*.jsonl` whose `session_meta` cwd matches the pane | last `token_count` event: `last_token_usage.total_tokens / model_context_window` | last `turn_context` | file mtime |
| opencode | `~/.local/share/opencode/opencode.db` (sqlite, opened read-only): newest session row for the cwd | last assistant message with non-zero tokens: total (else input+output+cache) vs a per-model window map | session/message `modelID` | message `time_updated` |
| kimi | `~/.kimi/sessions/<md5(cwd)>/<newest>/wire.jsonl` | last `StatusUpdate`: `context_tokens / max_context_tokens` (explicit) | — (argv fallback) | file mtime |
| any | argv `--model` flag on the pane's process (`ps` walk to the foreground harness); a visible `N% context left` style TUI footer (`tmux capture-pane`; reports REMAINING, converted to used) | | | |

**Claude same-cwd disambiguation (heuristic path):** when several panes (or unrelated
sessions) share one cwd, only transcripts whose first timestamp postdates the pane process's
start are candidates; panes claim them oldest-first in pane-creation order, one each.
RESUMED sessions predate their process, so they instead get a stable session-start-order
assignment over the recently-written files — sibling order can still be wrong, so
multi-candidate picks are flagged `ambiguous` (ctx rendered `~N%`). Transcripts mapped to a
live foreign pid are never candidates. The pid map pins every session exactly at its next
statusline tick (statusline renders stall through long streaming turns) — where the
statusline is installed the heuristic is only ever a bridge.

## Consumers

- `teamview` (sibling CLI) imports `pane_records(session)` for its per-pane columns.
- Standalone: point it at any tmux session for a one-shot context audit of a running team.
