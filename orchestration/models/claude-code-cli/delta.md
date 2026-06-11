# `claude-code-cli` package delta

Per-model delta for the **claude-code-cli** CLI worker — **Claude as a CLI-invocable worker** (`claude -p`, headless print mode). This is the D7 process-boundary sub-conductor: a Claude helper (or the conductor) launches `claude -p` as a CLI subprocess — the sanctioned escape from the Agent-tool nesting wall (a sub-agent cannot spawn a sub-agent; 4× documented), because a CLI subprocess is NOT an Agent-tool call.

**Evidence base — in-house probe, verdict HELD.** Every invocation claim below traces to the p3-6 probe (`1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/2026-06-07-claude-cli-probe.md` + the sibling capture folder `2026-06-07-claude-cli-probe/`; capture filenames cited inline as `helper-NN-*`) or to `claude --help` (capture `helper-help.txt`), corroborated by the production-harness article (`3-resources/knowledge-base/raw/medium/2026-06-06-building-a-production-agent-harness-turning-claude-code-into-a-multi-agent-engineering-pipeline.md`). The probe ran on Windows 11, Claude Code 2.1.168. No behavior here is assumption-authored; the one honest refinement (the default permission mode already permitted writes — H4-default) is folded in as a guardrail, not hidden.

**The UNIQUE property** (no other model package has it): CLI-Claude rooted in a workspace **natively auto-loads that workspace's `CLAUDE.md` / rules / skills and obeys them** (probe H5-pos returned the planted codeword; H5-neg with no file did not) — unlike Agent-tool helpers, which do NOT inherit workspace rules, and unlike kimi/codex, which need their guidance file (`AGENTS.md`) mirrored in. Consequence: **there is NO mirror for claude-code-cli** — the workspace's own `CLAUDE.md` IS the guidance file. See the invocation section "Workspace rooting" and the mirror ruling in `../../../shape.md`.

**Cost note:** claude-code-cli runs on the SAME Claude account/budget as the conductor. Selecting it buys a **process boundary** (a sub-conductor, native workspace rules, a parallel-safe separate process) — NOT a cheaper provider. There is **no cost arbitrage** here (contrast kimi/codex, which move work to a cheaper provider). Route to claude-code-cli for the capability, not to save money.

The render script (`../render-manuals.py`) composes the generic wrapper (`{rbtv_path}/orchestration/skills/orchestrating/cards/dispatch-wrapper.md`) with the sections below into `./manual.md`. Edit claude-code-cli behavior HERE; never in the rendered manual.

<!-- RENDER:DELTA model-binding-delta -->
**Claude-cli-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What claude-code-cli is bound to |
|------------|------------------------------|
| **Unattended writes are EXPLICIT, never assumed-default** | For any dispatch that must write files, pass `--permission-mode acceptEdits` (probe H4-accept: file landed deterministically). Do NOT rely on the default permission mode to be read-only OR write-capable: the probe's no-flag negative control ALSO wrote (H4-default, `helper-04-write-default-*` — the workspace default already permitted writes). The mode is the portable guarantee; the default is workspace-dependent and MUST NOT be trusted for confinement either way. NEVER pass `--dangerously-skip-permissions` / `bypassPermissions` as a confinement shortcut — that removes the guardrail, it does not set one. |
| **Confinement is the orchestrator's job — `--permission-mode` authorizes, it does not BOUND** | `acceptEdits` lets the worker write without a prompt; it does NOT restrict writes to an allowlist. Bound the worker by (a) running from / `--add-dir`-ing only the minimal dirs, (b) `--allowedTools`/`--disallowedTools` to strip tool families the task does not need, and (c) the mandatory post-run `git diff --name-only HEAD` of every changed path vs the task allowlist — the only reliable write enforcement (corroboration: the harness auto-reverts writes outside `case_dir` via a post-run git diff). Out-of-allowlist edit = halt + surface; never auto-revert silently. |
| **Native workspace rules are loaded — give the worker the RIGHT cwd, never `--bare`** | Run `claude -p` FROM the target workspace root (or root cwd there / `--add-dir` it) so the worker auto-loads that workspace's `CLAUDE.md` + rules + skills and is bound by them (probe H5). NEVER pass `--bare` (it DISABLES `CLAUDE.md` auto-discovery, per `--help`) when the worker needs the workspace rules. If the target workspace has no `CLAUDE.md`, inline the needed rules into the prompt — do not silently run rule-less. |
| **Sub-conductor depth cap ≤ 2 — a claude -p worker does NOT nest Agent-tool sub-agents** | A `claude -p` worker IS a sub-conductor (the D7 process-boundary escape, probe-exercised at one boundary: conductor → `claude -p`). It MAY shell out to further CLI subprocesses, but the depth cap ≤ 2 FORBIDS relying on deeper nesting, and the 4× documented Agent-tool nesting wall blocks a `claude -p` worker's own Agent-tool sub-agents from spawning further ones anyway. Do NOT design a claude -p dispatch that fans out Agent-tool sub-agents beneath itself. |
| **No self-commit unless the task grants it (default OFF)** | claude-code-cli MAY commit locally — and ONLY locally — after its declared validation passes, when the task file grants `commit_policy: local-only`. NEVER push, NEVER force-reset, NEVER amend. The commit subject MUST carry the run's mandated `[<task-id>]` convention; the returned hash MUST match `git log`. Absent an explicit grant, claude-code-cli does NOT commit (the conductor commits via `rbtv-commit`). When committing through Claude Code, honor the workspace's own commit conventions (the natively-loaded `CLAUDE.md` may mandate a trailer) — they bind this worker because it loaded them. |
| **Forbidden-ops are exhaustive** | The task's `forbidden_ops` list is the complete prohibition set; absence of mention is NOT permission. No writes outside the scoped work-dir, no `git push`, no destructive git reset, no external production API calls unless the task explicitly sanctions a mocked/local one, no `--dangerously-skip-permissions` / `--bare` unless the task names them. |
<!-- RENDER:DELTA-END model-binding-delta -->

<!-- RENDER:DELTA model-transport-note -->
**Claude-cli return surface:** run headless with `claude -p "<prompt>" --output-format json`. The JSON is a single envelope (probe H2/H3/H7, `helper-02/03/07-*`): `result` (the assistant's final text — where the five return fields live), `session_id`, `total_cost_usd`, `is_error`, `num_turns`, `duration_ms`, `permission_denials[]`, and `modelUsage.<model>.{contextWindow,maxOutputTokens,…}`. `--output-format text` gives the bare assistant text instead; `stream-json` streams events (one JSON object per line, not probed). The worker carries the five return fields in `result`; treat the message as a HINT, never the truth. A final-turn drop is possible (the generic CLI-worker lossy-return class — codex/kimi share it); on any garbled/absent return, reconcile from disk. **Ground truth is the exit code + `is_error`, not the prose**: `exit 0` + `is_error: false` = success (probe; corroboration: the harness trusts `git push` exit 0, never Claude's claim of success). The conductor reconciles every claude-code-cli return against `git status` / `git log` of the work-dir and the cited evidence files on disk — disk wins on any disagreement. For a known-path durable return, instruct the worker to ALSO write its five fields to an evidence file inside the allowlist (the JSON envelope can be captured to a file by redirecting stdout: `… --output-format json > <evidence-path>`).
<!-- RENDER:DELTA-END model-transport-note -->

<!-- RENDER:DELTA invocation -->
The claude-code-cli dispatch manual — the exact command shapes, flags, exit handling, resume, the native-workspace-rules property, and the claude-code-cli task contract. Every shape here is probe-HELD (p3-6) or sourced from `claude --help` (capture `helper-help.txt`); the probe environment was Windows 11, Claude Code **2.1.168**. Re-verify with `claude --help` / `claude --version` before relying on any flag — the CLI evolves fast; `--help` is ground truth for the installed build.

### Canonical unattended dispatch shape (Windows)

```bash
# In-session dispatch (bash carrier) — command BEGINS with `claude`; stdin redirect TRAILS:
claude -p "<PROMPT>" --output-format json --model <opus|sonnet|fullname> [--permission-mode acceptEdits] [--add-dir <DIR>] < /dev/null
```

```powershell
# Owner-typed `!` dispatch (PowerShell) — the leading $null| pipe is fine OUTSIDE the session classifier:
$null | claude -p "<PROMPT>" --output-format json --model <opus|sonnet|fullname> [--permission-mode acceptEdits] [--add-dir <DIR>]
```

The mandatory stdin redirect, the JSON envelope, `--model`, the optional unattended-write flag, and `--add-dir` are all probe-validated. For an IN-SESSION dispatch the command line MUST BEGIN with `claude` (generic packaging §1 D17 row): PowerShell's only stdin-redirect mechanism is a leading `$null |` pipe, which breaks the `claude:*` prefix match — so in-session dispatches go through the bash carrier, where `< /dev/null` trails the command. Run the command FROM the target workspace root so the worker auto-loads that workspace's `CLAUDE.md` (see "Workspace rooting").

### Pre-flight (before any dispatch)

| Check | Command | Gate |
|-------|---------|------|
| CLI present + version | `claude --version` (probe: `2.1.168`) | Absent/older → re-verify flags against `claude --help`. |
| **Pinned-flag existence** (routing §4 gate) | `claude --help` grepped for every non-trivial flag this dispatch pins (`-p`/`--print`, `--output-format`, `--model`, `--permission-mode`, `--add-dir`, `--allowedTools`/`--disallowedTools`, `--resume`/`--session-id`, `--max-budget-usd`) | Runs EVERY dispatch (NOT only on a version mismatch — a flag can vanish at the SAME version family the manual pinned; codex 0.137.0/`--ask-for-approval` is the cautionary case, p5-2). Any pinned flag absent → STOP, do not dispatch; re-resolve at THIS delta, re-render (`../render-manuals.py`), re-run the gate — NEVER hand-edit the rendered manual or pass an ad-hoc flag. A removed/renamed flag is a hard arg-parse error pre-spend if dispatched (probe H6: an unknown flag → exit 1, no spend). |
| Auth | (already authenticated — the conductor IS Claude Code on this machine) | On the SAME machine/user no per-dispatch auth is needed (the probe ran 8 API dispatches in-helper, no login step). A brand-new machine needs a one-time interactive `claude` login — that is the conductor's own setup (USER-EXECUTED-ONLY), not a per-dispatch pre-flight. |
| Guidance file | target workspace has `CLAUDE.md`? | **NO mirror** — CLI-Claude loads the workspace's OWN `CLAUDE.md` natively (H5). Present → run from / `--add-dir` that root so the worker inherits the rules. Absent → inline the needed rules into the prompt, or root cwd at a `CLAUDE.md`-bearing dir; NEVER generate a banner-stamped `CLAUDE.md` (it would clobber the user's file). NEVER pass `--bare` when rules are needed. |

### The invocation — `claude -p` (non-interactive print mode)

`-p` / `--print` runs Claude non-interactively: it executes the prompt and exits (probe: every H row). It skips the workspace trust dialog — run it ONLY in trusted directories. The prompt reaches the worker as the `-p` argument; **stdin MUST be redirected** or the CLI waits 3s for piped input (see "Windows stdin" below).

**Shape A — prompt as the `-p` argument (small prompts; command BEGINS with `claude`):**

```bash
claude -p "<task_prompt>" --output-format json --model sonnet --permission-mode acceptEdits < /dev/null
```

Use when the prompt fits comfortably under the host shell's single-argument limit (~32 KB single arg on Windows shells). Default for short dispatches.

**Shape B — large brief via a FILE POINTER (default in autonomous mode; command BEGINS with `claude`):**

```bash
claude -p "Read the file '<prompt-path>' and execute the task it contains exactly; create only the files it allowlists." \
  --output-format json --model opus --permission-mode acceptEdits --add-dir "<repo>" < /dev/null
```

Use when the prompt is large OR when running autonomously. The composed **header + payload** (generic packaging §1) is written to `prompt.md` on disk and the worker loads it via its own file tool — the command stays short AND begins with `claude` (the in-session permission requirement; the prompt file is the reuse surface on resume). Do **not** read the file into a shell variable first (`$prompt = Get-Content -Raw prompt.md; $null | claude -p "$prompt" …`): the leading assignment/pipe breaks the `claude:*` prefix match in-session — that form stays valid for owner-typed `!` dispatches only. (Claude reads the prompt from the `-p` arg, not from stdin in `-p` mode — stdin stays redirected; do not pipe the prompt via stdin.)

### Windows stdin — the mandatory redirect

| Symptom | Cause | Fix |
|---------|-------|-----|
| 3s pause + `no stdin data received in 3s, proceeding without it` on stderr; the warning pollutes `text` stdout | `claude -p` waits for piped stdin when none is redirected (probe C1) | ALWAYS redirect stdin: `< /dev/null` (bash, TRAILING — the in-session form, keeps the command beginning with `claude`) · `< NUL` (cmd) · `$null \|` (PowerShell — leading pipe, breaks the in-session `claude:*` prefix match; owner-typed `!` dispatches only). Probe C2 + every H row ran clean with the redirect. |

### Output format + the JSON envelope

| `--output-format` | Yields | Use |
|-------------------|--------|-----|
| `text` (default) | bare assistant final text | quick dispatches where you only need the answer string |
| `json` | one envelope: `result` · `session_id` · `total_cost_usd` · `is_error` · `num_turns` · `duration_ms` · `permission_denials[]` · `modelUsage.<model>.{contextWindow,maxOutputTokens,…}` · `terminal_reason` | the dispatch default — parseable status + cost + the session id for resume (probe H2/H3/H7) |
| `stream-json` | one JSON object per line (events) | streaming consumers (not probed) |

The five return fields (§3) live inside `result`. Capture the envelope to a file with `> <evidence-path>` for a durable return inside the allowlist.

### Model selection → variants

The claude-code-cli manifest declares two routable variants — route on `(claude-code-cli, variant)`:

| Variant | Flag | When |
|---------|------|------|
| `opus` | `--model opus` (or full name `claude-opus-4-8`) | Judgment-dense work and the **sub-conductor** role; the external-CLI **code-review reviewer floor** (reviewer for kimi/codex code is Opus — route it here). Max-reasoning Claude. |
| `sonnet` | `--model sonnet` | Partially-bounded work with `doubt_policy: halt`, and zero-context verification personas (recon, research, cold-verify, commits). Mid-tier; the default routable Claude-cli variant. |

`--model <alias|fullname>` is honored — the JSON `modelUsage` key names the ACTUAL model + its real context window (probe H3: `--model sonnet` → `modelUsage.claude-sonnet-4-6`, ctx 2e5). **The DEFAULT model is user-config-dependent**: on the probe machine the default was `claude-opus-4-8[1m]` (1M ctx, probe H2) — NOT sonnet, and NOT a constant to assume. ALWAYS pass `--model` explicitly for a deterministic dispatch; read the live `modelUsage` to confirm. **haiku is NOT a routable variant** (vault routing floors at sonnet absent a user-approved delegation map naming haiku — routing card §7).

### Permission modes — unattended writes

| Mode | Effect | Use |
|------|--------|-----|
| `acceptEdits` | file writes auto-approved, no prompt (probe H4-accept) | the explicit, portable unattended-write guarantee — pass it for any dispatch that must write |
| `default` | workspace-dependent — **the probe's default already wrote** (H4-default) | do NOT assume read-only OR write-capable; never rely on it for confinement |
| `plan` | plan-only, no execution | a read-only analysis leaf that must not act |
| `bypassPermissions` / `--dangerously-skip-permissions` | ALL permission checks off | NEVER as a confinement shortcut; only an externally-sandboxed env the task explicitly names (corroboration: the harness used `bypassPermissions` ONLY because a post-run git-diff boundary check + framing-layer hard rules confined it — the mode alone confines nothing) |

Modes available per `--help`: `acceptEdits`, `auto`, `bypassPermissions`, `default`, `dontAsk`, `plan`. **Confinement is the orchestrator's job** — `acceptEdits` authorizes writes but does NOT bound them; ALWAYS back a dispatch with the post-run `git diff --name-only HEAD` vs the allowlist.

### Workspace rooting — the unique native property (NO mirror)

CLI-Claude **natively auto-loads the cwd workspace `CLAUDE.md`** (and its rules/skills) and obeys it (probe H5-pos returned the planted codeword `XYZZY-ROOT`; H5-neg with no file returned "I don't have a codeword"). This is the property Agent-tool helpers LACK and the reason claude-code-cli is the sub-conductor of choice for in-workspace work.

| Need | Mechanism |
|------|-----------|
| Give the worker the workspace's rules | Run `claude -p` FROM the workspace root (cwd), or root cwd there. The worker inherits `CLAUDE.md` + rules + skills automatically. |
| Grant tool access to extra dirs beyond cwd | `--add-dir <dir>` (repeatable; confirmed in `--help`, the pre-staging-vs-`--add-dir` choice from the corpus). |
| Disable rule auto-load (rare) | `--bare` DISABLES `CLAUDE.md` auto-discovery (per `--help`) — the opposite knob; use only when the worker must run rule-less. |
| Target workspace has NO `CLAUDE.md` | Inline the needed rules into the prompt, or root cwd at a `CLAUDE.md`-bearing dir. Do NOT generate one — there is no mirror for claude-code-cli (a banner-stamped `CLAUDE.md` would clobber the user's primary project file; the workspace's own `CLAUDE.md` is the source of truth, loaded natively). |

**Why no mirror (ruling):** kimi/codex mirror their guidance file (`AGENTS.md` — a worker-specific, non-conflicting filename that does not exist natively) into a target workspace. claude-code-cli's guidance file IS `CLAUDE.md`, which the worker loads natively and which is the user's own hand-authored file. Mirroring `CLAUDE.md`→`CLAUDE.md` is a self-copy where the file exists (and a destructive banner-overwrite of the user's file) and circular where it is absent. So claude-code-cli ships **no `mirror-config.yaml`**, and its manifest omits `guidance_file.mirror_entry`. The routing card's pre-dispatch guidance-file check, for claude-code-cli, VERIFIES the workspace has a `CLAUDE.md` (and cwd/`--add-dir` points at it) — it never offers a mirror. (Full ruling: `../../../shape.md` mirror Decision, 2026-06-07.)

### Exit handling

| Code | Meaning | Conductor action |
|------|---------|------------------|
| `0` | Success — JSON `is_error: false`, `result` populated | Proceed to the return gate (reconcile against disk, then verification card). `exit 0` + `is_error:false` is ground truth, NOT the prose. |
| `1` | Arg-parse / usage error — fast (0.4s), **BEFORE any API spend** | Halt + surface; fix the command. A malformed dispatch costs nothing (probe H6: `--not-a-real-flag-xyz` → exit 1 + stderr `error: unknown option …`, no spend). |

No richer exit-code taxonomy was probed (no hang was engineered, per the task's "do NOT engineer a hang"; observed durations 0.4–10.1s). On any unexpected non-zero exit, reconcile disk state and recover-or-surface; do NOT blind-retry.

```bash
claude -p "<task>" --output-format json --model sonnet --permission-mode acceptEdits > out.json < /dev/null
code=$?
# non-zero -> halt + surface — H6: arg-parse error, no spend; fix the command
# else: parse out.json; trust is_error:false + exit 0, then reconcile against git status / git log
```

### Disk-state recovery (work landed, return/commit lost) — judgment-only

A final-turn drop on a long dispatch is possible (the generic CLI-worker lossy-return class; not separately probed for claude-code-cli — no hang was engineered). Treat it like the kimi exit-75 / codex disk-recovery class: valid only under a high-reasoning conductor (a lower-reasoning conductor halts + surfaces). Trigger only when ALL hold: the worker exited with NO structured return (no five fields / no commit hash) in the JSON `result` or the captured output; `git -C "<repo>" status --porcelain` shows uncommitted changes inside the allowlist; `git -C "<repo>" log -1 --pretty=%s` does NOT show the expected `[<task-id>]` prefix. Steps: (1) verify on-disk state against the task's Implementation Requirements; (2) run the declared `test_command` / smoke checks; (3) verify allowlist compliance (`git diff --name-only HEAD` — every changed path in the allowlist, else halt + surface); (4) verify forbidden-ops compliance; (5) commit manually with the mandatory `(orchestrator-recovered)` subject suffix:

```bash
git -C "<repo>" add <files-in-allowlist>
git -C "<repo>" commit -m "[<task-id>] <description> (orchestrator-recovered)" \
  -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

(6) log to the run-log: exit code, files verified + smoke result, the recovery commit hash, why not retrying, and that the reviewer MUST FULLY re-validate. The recovery commit is reversible (`git revert <hash>`). **Hung dispatch (claude -p never exits):** orchestrator kills it, evaluates disk state, then recover-commits (same steps) OR re-dispatches fresh (the prompt file is the reuse surface). Prefer resume (below) when a `session_id` was captured before the drop.

### Resume mechanics

| Mechanism | Command | Use |
|-----------|---------|-----|
| Resume a specific session | `claude -p --resume <session_id> "<follow-up>" --output-format json < /dev/null` (bash; in-session form) | After a `DOUBT_ESCALATED` / `NEEDS_CONTEXT` halt: supply the resolution into the SAME session by id (probe H7 recalled the earlier turn; the same `session_id` returns). The `session_id` comes from the prior JSON envelope. |
| Fork instead of continue | `claude -p --fork-session --resume <session_id> "<prompt>"` | Branch a new session from an existing one (per `--help`; not separately exercised). |
| Pin a session id | `claude -p --session-id <uuid> "<prompt>"` | Assign a known id up front (per `--help`). |
| Run without persisting | `claude -p --no-session-persistence "<prompt>"` | A print-only dispatch that should leave no resumable session (per `--help`). |

Resume is `session_id`-based and probe-validated (H7). Corroboration: the harness resumes the same Claude session across machines by UUID lookup — the session id is the durable handle. Capture the `session_id` from the JSON envelope on every dispatch you may need to resume; fall back to a fresh re-dispatch (prompt file = reuse surface) if resume does not engage.

### Confinement grammar — the orchestrator's job

CLI-Claude's `--permission-mode acceptEdits` AUTHORIZES writes but does NOT bound them to an allowlist; there is no native per-path write allowlist. Bound a worker by combining:

| Control | Mechanism |
|---------|-----------|
| Workspace scope | Run from the target workspace root (cwd) + `--add-dir <extra>` (repeatable). Keep the set minimal; cwd doubles as the `CLAUDE.md` auto-load root. |
| Tool surface | `--allowedTools` / `--disallowedTools` to allow/deny tool families (corroboration: the harness ran `--disallowedTools Bash` to prevent git races in read-only pipelines). No agent-file mechanism (unlike kimi). |
| Read confinement | Inline required context into the prompt; the natively-loaded workspace `CLAUDE.md` already scopes behavior. |
| **Write confinement** | **Post-run `git diff --name-only HEAD` of every changed path against the task's `allowlist`** — the ONLY reliable enforcement (corroboration: the harness auto-reverts writes outside `case_dir` via post-run git diff). Out-of-allowlist = halt + surface; NEVER auto-revert silently. |
| Permission posture | `--permission-mode acceptEdits` for an intended unattended write; `plan` for a no-act analysis leaf. NEVER `bypassPermissions` / `--dangerously-skip-permissions` as a confinement shortcut. |
| Commit / push | Local-only by policy; verify git state shows no push since dispatch. |
| Budget guard | `--max-budget-usd <amount>` + `--fallback-model <model>` (print-mode, per `--help`) cap an autonomous dispatch's spend. |

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| stdin not redirected → 3s wait + warning polluting `text` stdout | ALWAYS redirect stdin (`$null \|` / `< NUL` / `< /dev/null`) — probe C1 vs C2. |
| Default permission mode is NOT guaranteed read-only | The no-flag write control still wrote (H4-default); pass `--permission-mode acceptEdits` explicitly for an intended write, and never trust the default for confinement. |
| `--permission-mode` authorizes but does not BOUND writes | Always back with the post-run `git diff` vs allowlist — the only reliable write confinement. |
| `--bare` disables `CLAUDE.md` auto-load | Never pass `--bare` when the worker needs the workspace rules; it is the opposite of the native-rooting property. |
| Final-turn drop on a long dispatch | JSON/message is a HINT; reconcile from disk; `exit 0` + `is_error:false` is ground truth. Capture the envelope to a file for a durable return. |
| Treating the message as truth | `git push` / write exit code is ground truth, never Claude's prose claim of success (corroboration: the harness re-checks the wire, never the self-report). |
| Depth-cap violation | A claude -p worker must NOT nest Agent-tool sub-agents beneath itself (depth cap ≤ 2; the nesting wall blocks it anyway) — sub-conduct via further CLI subprocesses only. |

### The claude-code-cli task contract (plugs into the shared authoring core)

A claude-code-cli-executable task file extends the generic task-file contract (`{rbtv_path}/orchestration/workflows/_shared/authoring/`) with claude-code-cli-specific frontmatter and body sections. The orchestrator validates a `executor: claude-code-cli` task against this contract BEFORE dispatch; a missing required field = halt + report the malformed task — NEVER infer or mutate a field into shape (task shaping belongs to planning).

**Required frontmatter:**

```yaml
execution_kind: code            # or research/analysis/review for a read-only or verification leaf
executor: claude-code-cli
model: opus | sonnet            # the routed variant — opus for judgment/sub-conductor/code-review, sonnet for mid-tier/verification
allowed_workdir: <absolute-or-project-root-relative repo path>   # the cwd to run from (doubles as the CLAUDE.md auto-load root)
allowlist:
  - <file-or-folder-glob>
permission_mode: acceptEdits | plan | default   # acceptEdits for an intended write; plan for a no-act analysis leaf
commit_policy: local-only | none       # none = conductor commits via rbtv-commit
test_command: <command-or-NONE>
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - external production API calls
  - --dangerously-skip-permissions
  - --bare
doubt_policy: halt
reviewer: claude-opus           # reviewer floor for external-CLI code is Opus — non-overridable
```

**Required body sections:** Goal (one bounded deliverable) · Context Snapshot (all task-specific context inlined — the worker also inherits the workspace `CLAUDE.md` natively, so do NOT duplicate workspace rules into the prompt; inline only task-specific facts) · Allowed Paths (the allowlist in human-readable form) · Forbidden Paths · Permission + Rooting (the `--permission-mode` value, the cwd/`--add-dir` rooting, and whether `--bare` is forbidden) · Implementation Requirements (exact behavior — interfaces, data shapes, error semantics, every edge case enumerated) · Validation (the exact commands claude-code-cli runs before returning) · Commit Rule (local-only after validation, or none) · Return Format (the five-field return schema; capture the JSON envelope to an evidence file inside the allowlist).

**Review gates** every claude-code-cli coding task passes (verification card owns the gate): claude-code-cli self-report → orchestrator diff-vs-allowlist check → declared validation passing (or explicit blocker) → Claude/Opus spec-compliance review → Claude/Opus code-quality review → no push until owner/final-workflow publishes. Any gate fails → halt or route a fix task; never proceed on "close enough". When claude-code-cli is itself the cold verifier or reviewer (its strong suit — a separate Claude invocation with no authoring context, exactly the harness's adversarial/red-team pattern), it floors at the `opus` variant and receives ONLY the contract criteria + the running artifact, never the builder's claims.

### Recipes

All in-session recipes are bash-carrier, command BEGINS with `claude`, stdin redirect trailing (the `$null | claude …` PowerShell forms remain valid for owner-typed `!` dispatches only):

```bash
# Bounded write dispatch, JSON envelope captured to a durable file (Shape A), rooted in the workspace:
claude -p "<inlined task file content>" --output-format json --model sonnet \
  --permission-mode acceptEdits --add-dir "5-workbench/inni-cte-recon" > .claude-runs/t1.json < /dev/null
```
```bash
# Large brief via a FILE POINTER (Shape B), opus sub-conductor, rooted at the repo:
claude -p "Read the file '<prompt-path>' and execute the task it contains exactly" \
  --output-format json --model opus --permission-mode acceptEdits --add-dir "<repo>" > .claude-runs/t1.json < /dev/null
```
```bash
# Read-only analysis / cold-verify leaf (no writes), opus, no acceptEdits (plan mode):
claude -p "<verification task: exercise these criteria on the running artifact>" \
  --output-format json --model opus --permission-mode plan --add-dir "<repo>" > .claude-runs/verify.json < /dev/null
```
```bash
# Resume a halted session with the resolution:
claude -p --resume <session_id> "<resolution to the open question>" --output-format json > .claude-runs/t1-resume.json < /dev/null
```
<!-- RENDER:DELTA-END invocation -->
