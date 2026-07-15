# `opencode` package delta

Per-model delta for the **opencode** CLI worker (OSS provider-agnostic coding CLI, `opencode run`). Evidence boundary: THREE live proofs. (1) The 2026-07-06 coordination-POC test (`1-projects/rbtv-sb-merge-refactor/build/inputs/coordination-poc/headless-sessions-handoff.md` §1–2) ran a real worktree task headless on `sakana/fugu-ultra` (git worktree created, file written, commit `6c0b1fb3`), proved two-turn session memory via `-c`, and diagnosed the mandatory stdin-EOF guard. (2) The 2026-07-09 smoke through THIS manual (opencode 1.17.11, sakana backend, vault worktree): Shape-B file-pointer dispatch exit 0 — the worker read the on-disk brief (logged `Read oc-task.md`), executed its exact contract, self-validated with a real byte-compare command, and returned a well-formed five-field message on stdout; the post-run confinement diff showed ONLY allowlisted paths; wall-clock ≈9 min for a trivial task (fugu-ultra's multi-agent loop is slow — see the failure-mode row); mirror-into-worktree guidance pre-flight exercised (`created AGENTS.md from CLAUDE.md`). (3) The 2026-07-09 four-backend pilot through THIS manual: ALL FOUR backends ran a real bounded-code task (temperature converter + pytest) — exit 0, conformant five-field return, confinement diff = only the allowlisted files, no worker commit, independent conductor re-validation; deepseek-flash 29s, deepseek-pro 41s, sakana 302s, z1 (`zai-coding-plan/glm-5.2`) 54s. Still **UNPILOTED**: resume inside a dispatch loop, the non-zero exit taxonomy, and self-commit — narrow these on future runs; the manifest carries `evidence_status: validated` package-wide and per variant.

Backend scope (owner rulings 2026-07-09, two rounds): **z1** (`zai-coding-plan/glm-5.2`), **sakana** (`sakana/fugu-ultra`), **deepseek-flash** + **deepseek-pro** (`deepseek/deepseek-v4-flash|pro` — the code-executor role inherited when `qwen-code-cli` was retired; `deepseek-api` keeps the text roles, partitioned via `routable_for`). Do NOT add gemini/kimi backends (already routable via `gemini-api`/`kimi-code-cli`), and never give the deepseek backends text roles (duplicates make RANK nondeterministic).

The render script (`../render-manuals.py`) composes the generic wrapper (`{rbtv_path}/orchestration/skills/orchestrating/cards/dispatch-wrapper.md`) with the sections below into `./manual.md`. Edit opencode behavior HERE; never in the rendered manual.

<!-- RENDER:DELTA model-binding-delta -->
**OpenCode-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What opencode is bound to |
|------------|---------------------------|
| **NO native sandbox — confinement is ENTIRELY the conductor's, and it is worktree-mandatory** | opencode has no sandbox, no approval gate in headless runs, and no work-dir/add-dir scoping flags (POC 2026-07-06: it ran `git status` on the LIVE vault unprompted). Every dispatch MUST run inside a dedicated **git worktree** passed via `--dir "<worktree>"` — never against a live repo or the vault root. The post-run `git -C "<worktree>" diff --name-only HEAD` of every changed path vs the task allowlist is the ONLY reliable enforcement; out-of-allowlist = halt + surface, never auto-revert. The `opencode.json` `permission` block and per-agent tool specs exist but are UNPILOTED — never rely on them as the boundary. A container per profile is the flagged FUTURE escalation for untrusted tasks (aligns with merge-refactor DEC-1 R3); worktree isolation is the shipped default for trusted build/read tasks. |
| **The worktree IS the launch root (deviation from the G1 launch-root split)** | opencode has NO `--add-dir` — `--dir` is both the working root and the work target, so the generic "launch at the orchestrator root, add the work-target" split does not apply. Consequence: guidance loads from the WORKTREE. A fresh vault worktree carries NO `AGENTS.md` (the vault gitignores mirror-generated guidance) — the pre-flight MUST generate it into the worktree via the mirror (`mirror_entry: opencode-mirror`, target = the worktree; the worktree DOES carry the tracked `CLAUDE.md` source) or the conductor inlines the load-bearing behavior rules in the prompt. Never dispatch assuming the worker read rules it could not see. |
| **API keys live in the PROCESS env — export before dispatch** | opencode resolves provider keys from the process environment (registry lookup for `zai`; `{env:SAKANA_API_KEY}` in the sakana provider block). rbtv's `env_file` is NOT auto-read by opencode. The dispatch wrapper resolves the variant's key per rbtv availability semantics (OS env → `env_file`) and exports it into the dispatch process env — never inlines it in the prompt, the task file, or any artifact. |
| **No self-commit unless the task grants it (default OFF)** | opencode MAY commit locally — and ONLY locally — after its declared validation passes, when the task file grants `commit_policy: local-only` (the POC task committed on a branch inside its worktree — capability proven). NEVER push, NEVER force-reset, NEVER amend. The commit subject carries the run's `[<task-id>]` convention; verify the returned hash against `git log`. Absent an explicit grant, opencode does NOT commit (the conductor commits via `rbtv-commit`). |
| **Stray-file ban** | Create files ONLY where the allowlist directs, inside the worktree. NEVER write scratch notes, logs, or summaries outside the allowlist — the post-run diff treats any such file as an out-of-allowlist write. |
| **Forbidden-ops are exhaustive** | The task's `forbidden_ops` list is the complete prohibition set; absence of mention is NOT permission. No writes outside the worktree, no `git push`, no destructive git reset, no external production API calls unless the task explicitly sanctions one, no `--dangerously-skip-permissions` unless the task names it. |
<!-- RENDER:DELTA-END model-binding-delta -->

<!-- RENDER:DELTA model-transport-note -->
**OpenCode return surface:** run headless with `opencode run` — the assistant's output prints to stdout (formatted text by default). The worker carries the five return fields in its FINAL message; capture stdout to a durable file via shell redirection (`> "<worktree>/.opencode-runs/<task-id>.txt"`) rather than scraping the console. For machine parsing, `--format json` streams raw JSON events (JSONL — the final result is the last assistant-text event); this is the escalation path if plain-text capture proves brittle (decision 2026-07-09: start with stdout text capture — option (a) of the worker plan; note the earlier "no --json" POC claim is STALE, `--format json` exists on 1.17.11). opencode also has a first-class server (`opencode serve` → `POST /session/{id}/message` returning JSON) — NOT used for dispatch (per-dispatch serve was evaluated and deferred). Treat any returned message as a HINT, never the truth: reconcile every return against `git -C "<worktree>" status` / `git log` and the cited evidence files on disk — disk wins on any disagreement.
<!-- RENDER:DELTA-END model-transport-note -->

<!-- RENDER:DELTA invocation -->
The opencode CLI dispatch manual — exact command shapes, flags, provider config, confinement, exit handling, resume, and the opencode task contract. Flags below were verified against **opencode 1.17.11** on 2026-07-09; the ignite VPS now runs **1.17.18** (`opencode --version`, 2026-07-15) — the flags have not been re-verified against that build. Re-verify with `opencode run --help` before relying on any flag — the CLI evolves fast; `--help` is ground truth for the installed build (the POC's "no --json" note was already stale by authoring time: 1.17.11 has `--format json`).

### Pre-flight (before any dispatch)

| Check | Command | Gate |
|-------|---------|------|
| CLI present + version | `opencode --version` (ignite VPS, 2026-07-15: `1.17.18`; flags in this manual were verified against `1.17.11`) | Absent/different → re-verify flags against `opencode run --help`. |
| **Pinned-flag existence** (routing §4 gate) | `opencode run --help` grepped for every non-trivial flag this dispatch pins (`--dir`, `-m`, `--format`, `-s`/`--session`, `-c`/`--continue`, `--title`) | Runs EVERY dispatch. Any pinned flag absent → STOP, do not dispatch; re-resolve at THIS delta, re-render (`../render-manuals.py`), re-run the gate — NEVER hand-edit the rendered manual or pass an ad-hoc flag. |
| Credential resolves (EITHER path) | **Path A — env var (the piloted one):** resolve the variant's key per rbtv availability semantics (OS env → `rbtv.json` `env_file`): z1 → `ZHIPU_API_KEY`, sakana → `SAKANA_API_KEY`, deepseek-flash/pro → `DEEPSEEK_API_KEY`; then EXPORT it into the dispatch process env. **Path B — stored opencode login (z1, deepseek-flash, deepseek-pro):** `opencode auth list` shows a stored credential (`Z.AI Coding Plan` for z1; `deepseek` for deepseek-flash/pro) → the variant dispatches with NO env var exported; nothing to export. | EITHER path is sufficient for z1, deepseek-flash, and deepseek-pro (route.py gates on env-var **OR** the stored credential — manifest `auth.credential_store`; task adhoc-1, 2026-07-15, live-probed both deepseek variants on the ignite VPS with no env var and no env_file, each returning exit 0). Both absent → variant unavailable; route elsewhere or halt (api-key semantics — never a USER-EXECUTED login at dispatch time). For a key supplied via Path A, opencode reads ONLY the process env — exporting it is mandatory on that path. sakana declares no credential store — adhoc-1 live-probed it with no env var / no env_file and it FAILED (`Forbidden: request was blocked by a gateway or proxy`; the capture does not distinguish a stored-credential gap from an account/gateway block), so it was NOT opted in and stays Path A only. |
| Provider config | z1 + deepseek backends: none needed (the `zai-coding-plan` and `deepseek` providers are models.dev-built-in — key-only). sakana: the custom provider block MUST exist in the machine-global `~/.config/opencode/opencode.jsonc` (template below) | `opencode models` lists the variant's `-m` id (`zai-coding-plan/glm-5.2` / `sakana/fugu-ultra` / `deepseek/deepseek-v4-flash` / `deepseek/deepseek-v4-pro`)? Absent → fix the provider config / key FIRST (a wrong `-m` id fails the dispatch). z1 uses the coding-plan endpoint — pay-per-token `zai/glm-5.2` 429s without an account balance. |
| Worktree exists | `git worktree add <path> -b <branch>` (or reuse the task's assigned worktree) | Worktree-mandatory — NEVER `--dir` a live repo root. One worktree per dispatch (sessions are per-cwd). |
| Guidance file in the WORKTREE | worktree root has `AGENTS.md`? | It will NOT by default (the vault gitignores mirror-generated guidance and a fresh worktree checks out only tracked files) → generate it: `python {rbtv_path}/orchestration/models/mirror/mirror.py --config {rbtv_path}/orchestration/models/opencode/mirror-config.yaml --target "<worktree>"` (the worktree carries the tracked `CLAUDE.md` source), or inline the load-bearing rules in the prompt. |

**Sakana provider block** (machine-global `~/.config/opencode/opencode.jsonc` — already present on this machine, 2026-07-09; reproduce on a new machine):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "sakana": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Sakana AI",
      "options": { "baseURL": "https://api.sakana.ai/v1", "apiKey": "{env:SAKANA_API_KEY}" },
      "models": { "fugu-ultra": { "name": "Sakana Fugu Ultra" } }
    }
  }
}
```

### The invocation shape — `opencode run` (non-interactive)

`opencode run` executes one headless turn (or resumes a session). The prompt is a positional argument. There is no separate print/quiet flag — `run` IS the headless mode.

**Stdin-EOF guard — MANDATORY on EVERY headless dispatch.** opencode reads stdin whenever it is non-TTY and HANGS forever on "Reading additional input from stdin..." without an EOF (the POC's first stuck launches, 2026-07-06). Force the EOF: **Bash dispatch → suffix `< /dev/null`** (PREFERRED — the line still BEGINS with `opencode`, preserving the §1 D17 binary-first allowlist match). **PowerShell dispatch → prefix `$null |`** (POC-verified) — but the line then begins with `$null`, breaking the `PowerShell(opencode:*)` prefix match: auto-mode/`!`-dispatch only. An owner's interactive terminal has a TTY stdin → no guard needed.

**Shape A — prompt as CLI argument (small prompts; PowerShell-fenced, apply the matching guard):**

```powershell
# Path A (env var). On Path B — a stored `opencode auth login` → "Z.AI Coding Plan"
# credential — SKIP this line entirely: opencode reads the credential from its own store.
$env:ZHIPU_API_KEY = "<resolved from env_file — never inline in artifacts>"
$null | opencode run --dir "<worktree>" -m zai-coding-plan/glm-5.2 --title "<task-id>" "<task_prompt>" `
  > "<worktree>/.opencode-runs/<task-id>.txt"
```

Use when the prompt fits comfortably under the host shell's single-argument limit (Windows ~32 KB). Swap `-m sakana/fugu-ultra` + `SAKANA_API_KEY` for the sakana variant.

**Shape B — large brief via a FILE POINTER (default in autonomous mode; Bash-fenced — the in-session binary-first-safe form):**

```bash
opencode run --dir "<worktree>" -m zai-coding-plan/glm-5.2 --title "<task-id>" \
  "Read the file '<prompt-path>' and execute the task it contains exactly; create only the files it allowlists." \
  > "<worktree>/.opencode-runs/<task-id>.txt" < /dev/null
```

The composed **header + payload** (generic packaging §1) is written to `prompt.md` INSIDE the worktree allowlist and dispatched FROM that file — the same prompt file is the reuse surface on resume. opencode loads the brief via its own file tool, so the command stays short and BEGINS with `opencode`. The file-pointer read is VALIDATED for opencode (2026-07-09 smoke, sakana backend: the worker's log shows the `Read oc-task.md` tool call and its return executed the brief's exact contract — exit 0, five-field return conformant).

**Structured events (escalation path):** add `--format json` to stream raw JSON events (JSONL); the final assistant-text event carries the return. Use only if plain-text capture proves brittle.

### Model selection → variants

Route on `(opencode, variant)`; `-m <provider>/<model>` selects the backend per dispatch:

| Variant | `-m` id | reasoning · coding · cost · evidence | Key env var | When |
|---------|---------|--------------------------------------|-------------|------|
| `z1` | `zai-coding-plan/glm-5.2` | 5 · 4 · 3 · validated (piloted 2026-07-09) | `ZHIPU_API_KEY` (a GLM Coding Plan key → the `zai-coding-plan` endpoint. Pay-per-token `zai/glm-5.2` 429s "insufficient balance") **OR** a stored `opencode auth login` → "Z.AI Coding Plan" credential (either satisfies availability — ruling 2026-07-15; the ignite VPS runs on the stored credential alone, no env var) | Open-weights/provider-diversity code executor at mid cost; 1M context. |
| `sakana` | `sakana/fugu-ultra` | 6 · 6 · 7 · validated (piloted 2026-07-09; grades remain vendor-reported, confidence low) | `SAKANA_API_KEY` (provisioned) | Model-diversity premium option; cost 7 ranks LAST — reached via pinned roles, never auto-picked. |
| `deepseek-flash` | `deepseek/deepseek-v4-flash` | 4 · 3 · 1 · validated (piloted 2026-07-09; deepseek-api twin grades) | `DEEPSEEK_API_KEY` (provisioned) **OR** a stored `opencode auth login` → `deepseek` credential (either satisfies availability — task adhoc-1, 2026-07-15; live-probed on the ignite VPS with no env var and no env_file, exit 0) | The cost-floor bounded-code executor (ex-qwen role). CODE roles only (`routable_for`) — text stays on `deepseek-api`. |
| `deepseek-pro` | `deepseek/deepseek-v4-pro` | 5 · 4 · 1 · validated (piloted 2026-07-09; deepseek-api twin grades) | `DEEPSEEK_API_KEY` (provisioned) **OR** a stored `opencode auth login` → `deepseek` credential (either satisfies availability — task adhoc-1, 2026-07-15; live-probed on the ignite VPS with no env var and no env_file, exit 0) | Heavier-reasoning cost-1 code executor. CODE roles only. |

**Effort dial — PROBED, single-mode.** opencode 1.17.11 exposes `--variant <level>` ("provider-specific reasoning effort, e.g., high, max, minimal" — note the flag-name collision with this table's variant ids: opencode's `--variant` is its EFFORT flag, not our routing variant). PROBED 2026-07-09 on all four backends: opencode does NOT validate `--variant` — a bogus level (`--variant bogus-xyz`) returns identically to high/max/minimal (exit 0, same output), so no backend honors an effort ladder through it. Treat every backend as single-mode; do NOT pin an effort level.

### Exit handling

`opencode run` returns a process exit code; `0` = success. The non-zero taxonomy is **UNPILOTED** — no known retryable-throttle code (unlike kimi's 75). On any non-zero exit: reconcile disk state (`git -C "<worktree>" status --porcelain`, the `.opencode-runs/` return file), then recover-or-surface — do NOT blind-retry.

```powershell
$null | opencode run --dir "<worktree>" -m zai-coding-plan/glm-5.2 "<task>" > "<worktree>/.opencode-runs/<task-id>.txt"; $code = $LASTEXITCODE
if ($code -ne 0) { <reconcile disk; recover-or-surface — do NOT blind-retry> }
```

**Disk-state recovery (work landed, return lost):** mirrors the codex candidate protocol — trigger only when the exit is non-zero with NO structured return, `git status` shows uncommitted in-allowlist changes, and no `[<task-id>]` commit exists. Verify the on-disk state against the task's requirements, run the declared validation, check allowlist + forbidden-ops compliance, then commit manually with the `(orchestrator-recovered)` subject suffix and log it. Valid only under a high-reasoning conductor; otherwise halt + surface. **Hung dispatch** (never exits — suspect a missed stdin guard first): kill it, evaluate disk, recover-commit or re-dispatch fresh.

### Resume mechanics

| Mechanism | Command | Use |
|-----------|---------|-----|
| Resume a specific session | `opencode run -s <SESSION_ID> --dir "<worktree>" "<follow-up>"` | After a `DOUBT_ESCALATED` / `NEEDS_CONTEXT` halt: supply the resolution into the SAME session by id. |
| Resume the cwd's last session | `opencode run -c --dir "<worktree>" "<follow-up>"` | POC-proven (two-turn memory, 2026-07-06). Per-cwd — safe ONLY because each dispatch owns its worktree; never share a cwd across dispatches. |
| Fork before continuing | `opencode run -c --fork --dir "<worktree>" "<follow-up>"` | Branch a session to explore a resolution without mutating the original. UNPILOTED. |

Session-id capture is UNPILOTED on the text path (the id is not printed in default format) — capture it from `--format json` events when resume-by-id matters; `-c` inside the dispatch's own worktree is the validated fallback.

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| Headless HANGS reading non-TTY stdin | Stdin-EOF guard on EVERY dispatch: Bash `< /dev/null` suffix (binary-first-safe) / PowerShell `$null \|` prefix (auto-mode only). The POC's multi-minute "stalls" were exactly this. |
| No native sandbox — writes anywhere | Worktree-mandatory `--dir` + post-run `git -C "<worktree>" diff --name-only HEAD` vs the allowlist. Never rely on the UNPILOTED `permission` block. |
| `-m` id does not resolve | Pre-flight `opencode models` lists the id? sakana needs its provider block (machine-global config); zai-coding-plan + deepseek need only the key. |
| z.ai key on the WRONG endpoint | z.ai exposes two providers: `zai` (pay-per-token, needs an account balance) and `zai-coding-plan` (GLM Coding Plan subscription, base `https://api.z.ai/api/coding/paas/v4`). A coding-plan key 429s ("insufficient balance") on `zai/*` and works on `zai-coding-plan/*`. `opencode auth login` → "Z.AI" stores the pay-per-token cred (does NOT cover coding-plan) — pick "Z.AI Coding Plan", or export `ZHIPU_API_KEY` and use `zai-coding-plan/glm-5.2` (the piloted path). |
| opencode HANGS on an upstream 429 (balance/quota) | It silently retries with backoff and never surfaces the error — the dispatch times out with only `> build · <model>` on stderr. Not a stdin-guard hang. Diagnostic: raw-curl the provider's `chat/completions` endpoint for the real HTTP status. (live-diagnosed 2026-07-09) |
| Key not visible to the worker | Export the variant's key into the PROCESS env at dispatch (opencode never reads rbtv's `env_file`). |
| Worker saw no behavior rules | A fresh worktree has NO `AGENTS.md` (gitignored) — run the mirror against the worktree, or inline the load-bearing rules in the prompt. |
| Cross-session `-c` contamination | One worktree per dispatch; never launch two dispatches with the same `--dir`. |
| Non-zero exit semantics unknown (UNPILOTED) | Reconcile disk + recover-or-surface; never blind-retry. |
| **Timeout-killed dispatch orphans the worker (live-diagnosed 2026-07-09)** | Killing the dispatch shell does NOT kill the opencode child on Windows — the orphan keeps executing and mutating the workspace (observed: it completed its task minutes after the kill, while a naive re-dispatch raced it in the same cwd). Before ANY re-dispatch after a timeout/kill: liveness-check (`Get-Process opencode`; a busy snapshot `index.lock` delete is also an orphan signal) and `taskkill /PID <pid> /T /F` survivors, then reconcile disk — the orphan may have finished the work. |
| Stale snapshot `index.lock` after a killed run | Benign WARN spam under `~/.local/share/opencode/snapshot/` on later runs; delete once no orphan holds it. |
| Runaway spend on sakana | cost 7 ($5/$30 per 1M) — bound the task tightly; sakana is pin-only, never an auto-pick. Fugu-ultra's multi-agent loop is SLOW on trivial tasks too — budget ≥10 min wall-clock per dispatch before suspecting a hang (a 5-min timeout killed a healthy run, 2026-07-09). |

### The opencode task contract (plugs into the shared authoring core)

An opencode-executable task file extends the generic task-file contract (`{rbtv_path}/orchestration/workflows/_shared/authoring/`) with opencode-specific frontmatter.

**Required frontmatter:**

```yaml
execution_kind: code            # or research/analysis for a read-only leaf
executor: opencode
model_backend: zai-coding-plan/glm-5.2   # or sakana/fugu-ultra — the -m id, pinned at planning
allowed_workdir: <the dedicated worktree path — the --dir value; worktree-mandatory>
allowlist:
  - <file-or-folder-glob, worktree-relative>
commit_policy: local-only | none       # none = conductor commits via rbtv-commit
test_command: <command-or-NONE>
forbidden_ops:
  - git push
  - writes outside the worktree allowlist
  - destructive git reset
  - external production API calls
  - --dangerously-skip-permissions
doubt_policy: halt
reviewer: claude-opus           # reviewer floor for external-CLI code is Opus — non-overridable
```

**Required body sections:** Goal · Context Snapshot (all task-specific context inlined — the worker cannot see the conversation) · Allowed Paths · Forbidden Paths · Confinement (the worktree path; the post-run diff the conductor will run) · Implementation Requirements · Validation (the exact commands opencode runs before returning) · Commit Rule · Return Format (the five-field return schema as the FINAL message; stdout is captured to `.opencode-runs/<task-id>.txt`).

**Review gates** every opencode coding task passes (verification card owns the gate): worker self-report → conductor diff-vs-allowlist check → declared validation passing (or explicit blocker) → Claude/Opus spec-compliance review → Claude/Opus code-quality review → no push until owner/final-workflow publishes. opencode is a separate-process worker with NO sandbox — the cold verifier and review pins apply exactly as for any external-CLI code worker, and the confinement diff is NEVER skippable.
<!-- RENDER:DELTA-END invocation -->
