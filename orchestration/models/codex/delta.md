# `codex` package delta

Per-model delta for the **codex** CLI worker (OpenAI Codex CLI, `codex exec`). Codex is invocable today and live-proven ONCE as a **separate-process worker**: in investor run **B4D** (`1-projects/rbtv-evolution/orchestration/rbtv-plan-orchestration/cp-rbtv-plan-orchestration-nested-subagent-isolation-validation.md`, row B4D/p4-4), the refuter's opt-in Codex backend ran as a **separate OS process** and delivered the live context-isolation that an in-harness Claude sub-agent could not (the nesting wall). That separate-process isolation is the ONE validated fact. The full headless worker contract — return parsing, exit semantics, confinement-as-the-orchestrator's-job, resume inside a dispatch loop — is **UNPILOTED**: it is authored here from the live `codex exec --help` (CLI **0.137.0**, verified on this machine) and the schema, NOT from a pilot run. Areas that the corpus does not prove are marked **UNPILOTED** inline, and the manifest carries `evidence_status: probe-pending`. The p5-2 smoke probe is the first real `codex exec` dispatch through this manual.

The render script (`../render-manuals.py`) composes the generic wrapper (`{rbtv_path}/orchestration/skills/orchestrating/cards/dispatch-wrapper.md`) with the sections below into `./manual.md`. Edit codex behavior HERE; never in the rendered manual.

<!-- RENDER:DELTA model-binding-delta -->
**Codex-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What codex is bound to |
|------------|------------------------|
| **Sandbox + approval are the confinement, and they are the conductor's to set (UNPILOTED enforcement)** | Codex has a real native sandbox (`-s/--sandbox`: `read-only` · `workspace-write` · `danger-full-access`) and an approval policy (`-a/--ask-for-approval`: `untrusted` · `on-request` · `never`). A non-interactive dispatch MUST run `--ask-for-approval never` (any other value stalls headless waiting for a human) paired with the TIGHTEST sandbox the task needs — `read-only` for analysis/research leaves, `workspace-write` for code that edits the work-dir, NEVER `danger-full-access` and NEVER `--dangerously-bypass-approvals-and-sandbox` unless the task explicitly sanctions it. The pairing `never` + `workspace-write` is the bounded-write default. The sandbox is real but its reliability as a confinement boundary for THIS orchestrator is UNPILOTED — back it with the same post-run `git diff --name-only` vs the allowlist that every CLI worker gets. |
| **Workspace scope is `-C`/`--cd` + `--add-dir`; writes outside the work-dir are a guardrail breach** | Set `-C <repo-root>` (or run from that cwd) and add only the minimal extra writable dirs via `--add-dir`. Files created/modified outside the scoped workspace are an out-of-allowlist write the conductor catches on the post-run diff — surface, never auto-revert. `--skip-git-repo-check` is required ONLY when the work-dir is not a git repo (codex refuses to run outside a repo otherwise). |
| **No self-commit unless the task grants it (default OFF)** | Codex MAY commit locally — and ONLY locally — after its declared validation passes, when the task file grants `commit_policy: local-only`. NEVER push, NEVER force-reset, NEVER amend. The commit subject MUST carry the run's mandated `[<task-id>]` convention; the returned hash MUST match `git log`. Absent an explicit grant, codex does NOT commit (the conductor commits via `rbtv-commit`). This authorization, and the commit message convention's survival across a codex run, are UNPILOTED — verify the hash and the subject string on return. |
| **Project trust is a pre-flight, not a runtime grant** | Codex records per-project `trust_level` in `~/.codex/config.toml` (`[projects.'<path>']`). An untrusted target project triggers a first-run interactive trust prompt — a USER-EXECUTED-ONLY pre-flight (run codex once interactively in the workspace, or pre-set trust) before any headless dispatch. Do NOT attempt to clear a trust prompt programmatically. |
| **Stray-file ban** | Create files ONLY where the allowlist directs. NEVER write scratch notes, logs, or summary files into the repo root or anywhere outside the allowlist — the post-run diff treats any such file as an out-of-allowlist write. Use `-o/--output-last-message <file>` to land the structured return at a known path INSIDE the allowlist rather than scraping stdout. |
| **Forbidden-ops are exhaustive** | The task's `forbidden_ops` list is the complete prohibition set; absence of mention is NOT permission. No writes outside the scoped work-dir, no `git push`, no destructive git reset, no external production API calls unless the task explicitly sanctions a mocked/local one, no `--dangerously-bypass-*` flags unless the task names them. |
<!-- RENDER:DELTA-END model-binding-delta -->

<!-- RENDER:DELTA model-transport-note -->
**Codex return surface:** run headless with `codex exec` (alias `codex e`). The final assistant message goes to stdout; pass `-o/--output-last-message <file>` to ALSO write that final message to a file on disk (the durable copy — prefer it over stdout scraping). `--json` streams events as JSONL (one JSON object per line) for machine parsing — the final result is the last `agent_message`/assistant event. The worker carries the five return fields in that final message; treat the message as a HINT, never the truth. Codex runs autonomously to completion under `--ask-for-approval never`, so a dropped or garbled final turn is possible (UNPILOTED failure surface — codex's exact behavior on a mid-return connection drop is not corpus-validated; treat it like the kimi exit-75 class and reconcile from disk). The conductor reconciles every codex return against `git status` / `git log` of the work-dir and the cited evidence files on disk — disk wins on any disagreement. For a strictly-shaped final response, `--output-schema <file>` constrains the model's final JSON to a supplied JSON Schema.
<!-- RENDER:DELTA-END model-transport-note -->

<!-- RENDER:DELTA invocation -->
The codex CLI dispatch manual — the exact command shapes, flags, sandbox/approval grammar, exit handling, resume, and the codex task contract. Verified against **Codex CLI 0.137.0** (`codex --version` → `codex-cli 0.137.0`) on this machine. Re-verify with `codex --help` / `codex exec --help` / `codex --version` before relying on any flag — the CLI evolves fast; `--help` is ground truth for the installed build. Evidence boundary: the separate-process isolation property is live-proven (B4D); everything else here is **UNPILOTED** until the p5-2 smoke probe and is marked where it matters.

### Pre-flight (before any dispatch)

| Check | Command | Gate |
|-------|---------|------|
| CLI present + version | `codex --version` (`codex-cli 0.137.0`) | Absent/older → re-verify flags against `codex exec --help`. |
| Auth | `codex login status` (this machine → `Logged in using ChatGPT`) | Login is interactive (`codex login`, ChatGPT sign-in) OR `printenv OPENAI_API_KEY \| codex login --with-api-key`. First-time interactive login → USER-EXECUTED-ONLY; if unauthenticated, halt and ask the owner to run it; never automate the browser sign-in. |
| Project trust | target project has `trust_level = "trusted"` in `~/.codex/config.toml` `[projects.'<path>']`? | Untrusted → first-run interactive trust prompt (USER-EXECUTED-ONLY). Pre-trust the workspace or run codex once interactively there before headless dispatch. |
| Guidance file | target workspace has `AGENTS.md`? | Absent → offer to generate it via the mirror (`mirror_entry: codex-mirror`, see the codex `mirror-config.yaml`). Codex natively reads `AGENTS.md`. |

### The invocation shape — `codex exec` (non-interactive)

`codex exec` (alias `codex e`) runs Codex non-interactively. The prompt reaches the worker as a CLI argument OR via stdin (use `-` as the prompt, or pipe; if stdin is piped AND a prompt arg is given, stdin is appended as a `<stdin>` block).

**Shape A — prompt as CLI argument (small prompts):**

```powershell
codex exec --cd "<repo>" --sandbox workspace-write --ask-for-approval never `
  --output-last-message "<repo>/.codex-runs/<task-id>.txt" "<task_prompt>"
```

Use when the prompt fits comfortably under the host shell's single-argument limit (Windows PowerShell ~32 KB). Default for short dispatches.

**Shape B — prompt via stdin (large prompts; default in autonomous mode):**

```bash
cat prompt.md | codex exec --cd "<repo>" --sandbox workspace-write --ask-for-approval never \
  --output-last-message "<repo>/.codex-runs/<task-id>.txt" -
```

Use when the prompt is large OR when running autonomously and you cannot afford a per-prompt size halt. The trailing `-` tells codex to read the prompt from stdin. **Both shapes** apply the same `--cd` scope, the same sandbox + approval policy, and pass the same allowlist + forbidden-ops checks on return. The composed **header + payload** (generic packaging §1) is written to `prompt.md` on disk and dispatched FROM that file — the same prompt file is the reuse surface on resume. (Windows note: PowerShell ~32 KB single-arg ceiling — prefer Shape B for any non-trivial prompt. Stdin piping was the validated transport for the kimi worker on this machine; codex's stdin handling on Windows is UNPILOTED — verify on the first dispatch.)

### Sandbox + approval grammar — the confinement axis

| Flag | Values | Use |
|------|--------|-----|
| `-s` / `--sandbox` | `read-only` · `workspace-write` · `danger-full-access` | The blast-radius control. `read-only` = analysis/research leaf (no file writes). `workspace-write` = code that edits the scoped work-dir (the bounded default for code). `danger-full-access` = NEVER unless the task explicitly sanctions it. |
| `-a` / `--ask-for-approval` | `untrusted` · `on-request` · `never` | Headless MUST use `never` (the model never pauses for human approval; failures return to the model). `untrusted`/`on-request` stall a headless run waiting for input. `on-failure` is DEPRECATED. |
| `--dangerously-bypass-approvals-and-sandbox` | (flag) | Skips ALL approvals AND sandboxing. EXTREMELY DANGEROUS — only for an externally-sandboxed environment the task names. Forbidden by default. |
| `-C` / `--cd <dir>` | path | The agent's working root. Scope codex to the repo. |
| `--add-dir <dir>` | path (repeatable) | Extra writable dirs alongside the primary workspace. Keep minimal. |
| `--skip-git-repo-check` | (flag) | Required only when the work-dir is NOT a git repo (codex refuses outside a repo otherwise). |
| `--ignore-rules` | (flag) | Do NOT load user/project execpolicy `.rules` files. Use only when a workspace `.rules` file would wrongly block a sanctioned dispatch. |
| `--ignore-user-config` | (flag) | Do NOT load `~/.codex/config.toml` (auth still uses `CODEX_HOME`). Use for a clean, reproducible dispatch independent of the machine's personal codex config. |

**Confinement is the orchestrator's job (UNPILOTED reliability):** the sandbox is real, but its reliability as the sole confinement boundary for this orchestrator is not corpus-validated. ALWAYS back it with the post-run `git diff --name-only HEAD` of every changed path against the task's `allowlist` — the same reliable enforcement every CLI worker gets. Out-of-allowlist edit = halt + surface; NEVER auto-revert silently.

### Model + reasoning-effort settings → variants

The codex manifest declares routable variants — route on `(codex, variant)`:

| Variant | Flags / config | When |
|---------|----------------|------|
| `default` | (machine config: `model = "gpt-5.5"`, `model_reasoning_effort = "medium"`) | The mid-tier profile; partially-bounded code/analysis with `doubt_policy: halt`. |
| `high-reasoning` | `-c model_reasoning_effort="high"` (or the workspace's configured high-effort model) | Judgment-denser work that still routes to codex. Higher latency + spend. |

`-m/--model <id>` overrides the configured model per dispatch; `-c model_reasoning_effort="<low|medium|high>"` overrides reasoning effort (a `-c` dotted-path config override, TOML-parsed). `-p/--profile <name>` layers a `$CODEX_HOME/<name>.config.toml` profile on top of the base config. The configured model on this machine is `gpt-5.5` at `medium` effort (`~/.codex/config.toml`); a re-pointed model/profile changes the reasoning tier — re-confirm against the live config before routing. The exact reasoning-tier-to-boundedness mapping for codex is UNPILOTED; the manifest marks the package `probe-pending`.

### Exit handling

Codex `exec` returns a process exit code; `0` = success. A non-zero exit means the run did not complete cleanly — halt and surface; do NOT blind-retry. The precise non-zero exit-code taxonomy (which codes are retryable rate-limit/throttle vs non-retryable config/auth) is **UNPILOTED** on this machine — unlike kimi's documented exit-75, codex's retry semantics are not corpus-validated. Until a probe establishes them: on any non-zero exit, reconcile disk state, and if uncommitted in-allowlist work landed without the structured return, apply the disk-state recovery pattern below rather than re-running.

```powershell
codex exec --cd "<repo>" --sandbox workspace-write --ask-for-approval never `
  --output-last-message "<repo>/.codex-runs/<task-id>.txt" "<task>"; $code = $LASTEXITCODE
if ($code -ne 0) { <reconcile disk; recover-or-surface — do NOT blind-retry> }
```

### Disk-state recovery (work landed, return/commit lost) — UNPILOTED, judgment-only

Mirrors the kimi exit-75 recovery in shape; codex's exact drop behavior is unvalidated, so treat this as a candidate protocol, valid only under a high-reasoning conductor (a lower-reasoning conductor halts + surfaces). Trigger only when ALL hold: codex exited non-zero with NO structured return (no `status`, no commit hash) in the `--output-last-message` file/stdout; `git -C "<repo>" status --porcelain` shows uncommitted changes inside the allowlist; `git -C "<repo>" log -1 --pretty=%s` does NOT show the expected `[<task-id>]` prefix. Steps: (1) verify on-disk state against the task's Implementation Requirements; (2) run the declared `test_command` / smoke checks; (3) verify allowlist compliance (`git diff --name-only HEAD` — every changed path in the allowlist, else halt + surface); (4) verify forbidden-ops compliance; (5) commit manually with the mandatory `(orchestrator-recovered)` subject suffix:

```bash
git -C "<repo>" add <files-in-allowlist>
git -C "<repo>" commit -m "[<task-id>] <description> (orchestrator-recovered)" \
  -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

(6) log to the run-log: exit code, files verified + smoke result, the recovery commit hash, why not retrying, and that the reviewer MUST FULLY re-validate. The recovery commit is reversible (`git revert <hash>`). **Hung dispatch (codex never exits):** orchestrator kills it, evaluates disk state, then recover-commits (same steps) OR re-dispatches fresh.

### Resume mechanics

| Mechanism | Command | Use |
|-----------|---------|-----|
| Resume a specific session | `codex exec resume <SESSION_ID> "<follow-up>"` | After a `DOUBT_ESCALATED` / `NEEDS_CONTEXT` halt: supply the resolution into the SAME session by id (UUID or thread name). Add `-` as the prompt to read the follow-up from stdin. |
| Resume the most recent | `codex exec resume --last "<follow-up>"` | Pick up the newest recorded session for the cwd without tracking an id. `--all` disables cwd filtering. |
| Run without persisting | `codex exec --ephemeral …` | A dispatch that should leave NO session files on disk (no resume possible afterward). |

Resume is session-id based (`codex exec resume`). Resume reliability inside an autonomous dispatch loop is UNPILOTED — verify the session id round-trips before depending on resume for recovery; fall back to a fresh re-dispatch (the prompt file is the reuse surface) if resume does not engage.

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| Headless stalls waiting for approval | ALWAYS pass `--ask-for-approval never` for a non-interactive dispatch; any other value blocks. |
| Refuses to run outside a git repo | Pass `--skip-git-repo-check` when the work-dir is not a repo. |
| First-run project trust prompt | Pre-trust the workspace (`[projects.'<path>'] trust_level`) or run codex once interactively there — USER-EXECUTED-ONLY; never clear it programmatically. |
| Interactive login required | `codex login` (ChatGPT) or `--with-api-key` via stdin is USER-EXECUTED-ONLY; halt + ask the owner. |
| Sandbox reliability as sole confinement (UNPILOTED) | Always back the sandbox with the post-run `git diff` vs allowlist; the sandbox is not corpus-validated as the only boundary for this orchestrator. |
| `cd` does not persist between shell calls | Each shell command is an independent subprocess — set `--cd`; never rely on `cd` chaining in the prompt. |
| Non-zero exit retry semantics (UNPILOTED) | Codex's exit-code taxonomy is not validated on this machine — on any non-zero exit reconcile disk + recover-or-surface, never blind-retry. |
| Final-message drop on a dropped turn (UNPILOTED) | Prefer `--output-last-message <file>` for a durable return; reconcile from disk on any garbled/absent return. |
| Machine config leaks into a reproducible dispatch | Use `--ignore-user-config` (and `--ignore-rules` if a workspace `.rules` wrongly blocks) for a clean, deterministic run. |

### The codex task contract (plugs into the shared authoring core)

A codex-executable task file extends the generic task-file contract (`{rbtv_path}/orchestration/workflows/_shared/authoring/`) with codex-specific frontmatter and body sections. The orchestrator validates a `executor: codex` task against this contract BEFORE dispatch; a missing required field = halt + report the malformed task — NEVER infer or mutate a field into shape (task shaping belongs to planning).

**Required frontmatter:**

```yaml
execution_kind: code            # or research/analysis for a read-only leaf
executor: codex
allowed_workdir: <absolute-or-project-root-relative repo path>   # → --cd
allowlist:
  - <file-or-folder-glob>
sandbox: read-only | workspace-write   # the tightest the task needs (never danger-full-access by default)
commit_policy: local-only | none       # none = conductor commits via rbtv-commit
test_command: <command-or-NONE>
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - external production API calls
  - --dangerously-bypass-approvals-and-sandbox
doubt_policy: halt
reviewer: claude-opus           # reviewer floor for codex-produced code is Opus (external-CLI code) — non-overridable
```

**Required body sections:** Goal (one bounded deliverable) · Context Snapshot (all task-specific context inlined — never make codex infer from broad PRDs) · Allowed Paths (the allowlist in human-readable form) · Forbidden Paths · Sandbox + Approval (the `--sandbox` value and the mandatory `--ask-for-approval never`) · Implementation Requirements (exact behavior — interfaces, data shapes, error semantics, every edge case enumerated) · Validation (the exact commands codex runs before returning) · Commit Rule (local-only after validation, or none) · Return Format (the five-field return schema; land it via `--output-last-message`).

**Review gates** every codex coding task passes (verification card owns the gate): codex self-report → orchestrator diff-vs-allowlist check → declared validation passing (or explicit blocker) → Claude/Opus spec-compliance review → Claude/Opus code-quality review → no push until owner/final-workflow publishes. Any gate fails → halt or route a fix task; never proceed on "close enough". Codex is a SEPARATE-PROCESS worker (its one validated property, B4D) — the cold verifier and review pins apply exactly as for any external-CLI code worker.

### Recipes

```powershell
# Bounded code edit, durable return file (Shape A):
codex exec --cd "5-workbench/inni-cte-recon" --sandbox workspace-write --ask-for-approval never `
  --output-last-message ".codex-runs/t1.txt" "<inlined task file content>"
```
```bash
# Large prompt via stdin (Shape B — default autonomous/Windows):
cat prompt.md | codex exec --cd "<repo>" --sandbox workspace-write --ask-for-approval never \
  --output-last-message "<repo>/.codex-runs/t1.txt" -
```
```powershell
# Read-only analysis/research leaf (no writes), JSONL events for parsing:
codex exec --cd "<repo>" --sandbox read-only --ask-for-approval never --json "<analysis task>"
```
```powershell
# High reasoning effort, clean of machine config:
codex exec --cd "<repo>" --sandbox workspace-write --ask-for-approval never `
  -c model_reasoning_effort="high" --ignore-user-config "<task>"
```
```powershell
# Resume a halted session with the resolution:
codex exec resume <SESSION_ID> "<resolution to the open question>"
```
<!-- RENDER:DELTA-END invocation -->
