# Kimi CLI — Headless / Scripted Invocation Cheat-Sheet

Verified against **Kimi CLI v1.41.0** on 2026-06-03.

---

## Auth / Prerequisites

| Requirement | How |
|-------------|-----|
| Kimi account logged in | `kimi login` (one-time, interactive) — stores session in `~/.kimi/` |
| Verify installed | `kimi --version` · `kimi info --json` |
| Config file | `~/.kimi/config.toml` — sets default model, `max_context_size`, provider |

No env-var auth tokens needed for the default Kimi provider; login state is persisted locally.

---

## Canonical One-Shot / Non-Interactive Command

```powershell
kimi --work-dir "<absolute-repo-path>" --quiet --prompt "<self-contained task prompt>"
```

`--quiet` expands to `--print --output-format text --final-message-only`:
- Runs non-interactively (auto-approves all tool calls).
- Prints **only the final assistant message** to stdout.
- Process exits when done — safe to wrap in a script loop.

---

## Command Template to Write Code to a Target Path

```powershell
kimi `
  --work-dir "<absolute-path-to-repo>" `
  --quiet `
  --prompt "Write <description>. Output file: <relative-path-from-work-dir>. <full self-contained spec>"
```

The prompt must be **fully self-contained** — include interfaces, edge cases, file paths, and all decisions. Kimi is a non-reasoning executor; it will not resolve ambiguity.

### With constrained tools (recommended for code tasks)

```powershell
kimi `
  --work-dir "<repo>" `
  --agent-file "<path-to-agent.yaml>" `
  --quiet `
  --prompt "<task>"
```

Minimal agent file to strip web access:
```yaml
version: 1
agent:
  extend: default
  system_prompt_path: ./system.md
  exclude_tools:
    - "kimi_cli.tools.web:SearchWeb"
    - "kimi_cli.tools.web:FetchURL"
```

### Machine-parseable JSONL output (for orchestrators)

```powershell
kimi --work-dir "<repo>" --print --output-format stream-json --prompt "<task>"
```

Parse the last `assistant` line without `tool_calls` as the final result.

---

## Model / Flags

| Flag | Purpose |
|------|---------|
| `--model <name>` | Override default model from config |
| `--thinking` / `--no-thinking` | Toggle extended thinking |
| `--max-steps-per-turn <n>` | Cap tool calls per turn (default from config) |
| `--max-ralph-iterations <n>` | Cap autonomous loop iterations; **never use `-1`** (unbounded runaway) |
| `--agent-file <yaml>` | Custom agent spec — controls tool surface |

---

## Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| `0` | Success | Proceed / validate output |
| `1` | Non-retryable (auth, config, quota) | Halt + surface |
| `75` | Retryable (rate limit, timeout, 5xx) | Back off + retry |

```powershell
kimi --work-dir "<repo>" --quiet --prompt "<task>"
$c = $LASTEXITCODE
if ($c -eq 75) { Start-Sleep 10; <re-dispatch> }
elseif ($c -ne 0) { throw "kimi failed with exit $c" }
```

---

## Session Management

```powershell
# Resume a specific session
kimi --work-dir "<repo>" --session "<session-id>" --quiet --prompt "<follow-up>"

# Continue the most recent session for the work-dir
kimi --work-dir "<repo>" --continue --quiet --prompt "<follow-up>"

# Export full session audit trail
kimi export <session-id> -o "<repo>/.kimi-runs/<session-id>.zip" -y
```

---

## Confinement (no native allowlist — enforce externally)

1. **`--work-dir`** scopes the workspace. Keep it minimal.
2. **`--agent-file`** with explicit `tools` / `exclude_tools` trims tool surface.
3. **Post-run `git diff`** of every changed path vs. the task allowlist — only reliable write gate.
4. No CLI flag blocks network/prod APIs — strip web/MCP tools via agent file.

---

## Top Gotchas

| Gotcha | Detail |
|--------|--------|
| **Headless = auto-approve everything** | `--quiet` / `--print` / `--afk` all enable auto-approval of every tool call. There is no interactive gate and no native path allowlist. `--yolo` adds nothing extra. Confinement is entirely the caller's job. |
| **`cd` does not persist between shell calls** | Each shell command runs in an independent subprocess; working directory resets every call. Always set `--work-dir`; never chain `cd` in prompts. |
| **`--max-ralph-iterations -1` runs forever** | Autonomous loop with `-1` is unbounded. Always pass a positive cap for any scripted dispatch. |
| **Auth is interactive (one-time)** | `kimi login` requires a browser/interactive session. Must be done manually before any scripted use. |
| **Without `--prompt`, kimi drops into interactive TUI** | Always pass `--prompt` (or `--print` with stdin) in headless scripts or the process will hang waiting for input. |

---

## Can Kimi Be Driven Headlessly in a Loop?

**Yes.** With `--quiet --prompt`, each invocation is fully non-interactive and exits on completion. Wrap in a PowerShell/Bash loop, check `$LASTEXITCODE`, retry on `75`. No persistent state bleeds between invocations unless you explicitly use `--session`/`--continue`.

---

## Smoke Test Record

Command used:
```powershell
kimi --work-dir "C:\Users\henri\Documents\second-brain\3-resources\tools\hypresent" \
  --quiet \
  --prompt "Write a file named docs/kimi-smoketest.txt containing exactly one line: kimi headless smoke test OK"
```

Result: **PASS** — exit code `0`, file written with correct content, session id returned in stdout.
Date: 2026-06-03 · kimi v1.41.0
