# `kimi` package delta

Per-model delta for the **kimi** CLI worker — the validated bounded-code executor (3 hypresent sessions + 2 inni phases, ~66 dispatches). This file fills the dispatch-wrapper template's INSERT points with kimi-specific binding obligations and the kimi return surface, plus the mandatory `invocation` section — the full kimi CLI dispatch manual that the generic card explicitly does NOT carry (dispatch-wrapper §7).

The render script (`../render-manuals.py`) composes the generic wrapper (`{rbtv_path}/orchestration/skills/orchestrating/cards/dispatch-wrapper.md`) with the sections below into `./manual.md`. Edit kimi behavior HERE; never in the rendered manual.

This package DISSOLVES the `kimi-code-execution` runtime component (the M3 mandate from `cp-workflow-rbtv-kimi-planning-orchestration.md`): the orchestrator's runtime kimi rules — task contract, invocation, guardrails, swarm — live in this manual now, self-contained, with no reference back to the human-facing `kimi-cli-reference.md` design doc.

<!-- RENDER:DELTA model-binding-delta -->
**Kimi-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What kimi is bound to |
|------------|------------------------|
| **Non-reasoning executor** | Kimi MUST NOT reason, decide, or interpret intent. Every interface, edge case, validation, and routing decision is pre-resolved in the task file. Kimi implements the enumerated behavior; it never designs, never "handles reasonably", never "fills in the blanks". A decision left to kimi is a planning bug, not kimi's call. |
| **No agentic exploration** | The task file's allowed paths are kimi's entire read/write universe. Kimi MUST NOT decide which files to read, MUST NOT load other task files / the plan / decisions.md beyond what the header inlines. Required context is inlined into the task body — kimi never goes reading broad PRDs at runtime (the ~250K budget is for inlined facts). |
| **Stray-file ban** | Create files ONLY where the allowlist directs. NEVER write scratch notes, logs, or summary files into the repo root or anywhere outside the allowlist — the post-run diff treats any such file as an out-of-allowlist write. |
| **Local-commit authorization (this is where a code worker's self-commit is granted)** | Kimi MAY commit locally — and ONLY locally — after its declared validation passes, when the task file grants `commit_policy: local-only`. NEVER push, NEVER force-reset, NEVER amend. The commit subject MUST carry the run's mandated `[<task-id>]` convention; the returned hash MUST match `git log`. Absent an explicit grant, kimi does NOT commit (the conductor commits via `rbtv-commit`). |
| **Swarm policy** | Kimi launches its own subagents (coder / explore / plan) ONLY when the task file sets `swarm_policy: allowed` with `max_kimi_subagents: N`. With `swarm_policy: disabled` (the default), kimi launching ANY subagent is a guardrail failure the conductor treats as a failed dispatch — surface it. Subagents cannot nest (one level only). |
| **Forbidden-ops are exhaustive** | The task's `forbidden_ops` list is the complete prohibition set; absence of mention is NOT permission. No writes outside the allowed work-dir, no `git push`, no destructive git reset, no external production API calls unless the task explicitly sanctions a mocked/local one. |
| **Per-file rule reads — NEVER one bulk read** | When the generic Rule-loading obligation fires (a `.agents/behavior-rules/` directory exists), kimi MUST read the rule files ONE FILE PER read call (or in small batches of a few files), issuing a separate `ReadFile` per file. NEVER read the whole directory in a single bulk call (`Get-Content … -Recurse`, `cat .agents/behavior-rules/*`, or any one command emitting every file's contents at once): that single command's combined output is truncated at the Shell-tool output ceiling BEFORE the alphabetically-last rule files, so the late-sorting rules (e.g. `rbtv-reasoning.md`, whose Pre-Agreement-Gate `<counter>` format lives nowhere else) never reach kimi's context and their rules are silently dropped. Reading each file individually keeps every rule's full body inside the per-call output budget. |
<!-- RENDER:DELTA-END model-binding-delta -->

<!-- RENDER:DELTA model-transport-note -->
**Kimi return surface:** kimi runs headless with `--quiet` (alias for `--print --output-format text --final-message-only`), which prints ONLY kimi's final assistant message to stdout — that message carries the five return fields. Treat it as a HINT, never the truth: a documented failure mode is kimi exiting 75 on the final return turn with the work correctly on disk but the structured message garbled or absent, and resumed long-context sessions drifting to conversational prose over the named-field schema (five instances in one session). The conductor reconciles every kimi return against `git status` / `git log` of the work-dir and the cited evidence files on disk — disk wins on any disagreement. For machine-parseable streaming, `--output-format stream-json` emits one JSON object per line; parse the last `assistant` message without `tool_calls` as the final result.
<!-- RENDER:DELTA-END model-transport-note -->

<!-- RENDER:DELTA invocation -->
The kimi CLI dispatch manual — the exact command shapes, flags, exit handling, resume, recovery, and the kimi task contract. Self-contained: this is the orchestrator's complete runtime kimi spec (the dissolved `kimi-code-execution` / M3 content). Verified against Kimi CLI **1.41.0** (`kimi info --json` → `agent_spec_versions: ["1"]`, `wire_protocol_version: "1.9"`). Re-verify with `kimi --help` / `kimi --version` before relying on any flag — the CLI evolves fast; `--help` is ground truth for the installed build.

### Launch-root vs work-target — the confinement split (G1)

Kimi keys its guidance to `--work-dir`. Under orchestration, `--work-dir` is ALWAYS the **orchestrator root** (the launch root, where the full rules/skills mirror lives — `AGENTS.md` + `.agents/behavior-rules/`), NEVER the work-target. The actual **work-target** (the repo the task edits — `allowed_workdir` in the task frontmatter) is passed via `--add-dir "<work-target>"`. Rooting kimi at a nested-repo work-target loads ZERO behavior-rules (the mirror skips nested git repos by design) — the a3e217d incident: a bare self-commit from a rules-blind kimi swept 5 foreign files. Three consequences:

- Every shape and recipe below sets `--work-dir "<orchestrator-root>" --add-dir "<work-target>"`.
- The post-run confinement diff runs in the **work-target's git**: `git -C "<allowed_workdir>" diff --name-only HEAD` (a diff in the launch-root's git passes vacuously when the work-target is a nested repo).
- The work-target's own local `CLAUDE.md`/`AGENTS.md` conventions are NOT auto-loaded from `--add-dir` — the conductor inlines the load-bearing ones into the task body or marks the file `[FULL READ]`.

### Mirror-equipped dispatch composition

When the launch root (`--work-dir`) contains a `.agents/behavior-rules/` directory (a mirror-equipped workspace), the conductor MUST prepend to the kimi task body an explicit ENUMERATED first step — a literal **Step 0** that reads, verbatim:

> **Step 0 — before any other work:** read each file under `.agents/behavior-rules/` individually (one read per file, NEVER a bulk `Get-Content -Recurse` / `cat .agents/behavior-rules/*` / any single command that emits every file at once). Then read your `AGENTS.md`. Treat all of it as binding, non-negotiable rules for this entire session. Only after you have read every rule file may you begin the task.

This forced task-step is MANDATORY for mirror governance — it is not optional and not a no-op the conductor MAY skip on a mirror-equipped launch root. The reason is proven, not theoretical: kimi does NOT reliably act on the passive header binding-addendum obligation alone — given only the addendum's "Rule-loading" row, kimi skipped the rule read ENTIRELY (0 rule-file reads on repeated bare-prompt runs), so `rbtv-reasoning.md`'s Pre-Agreement-Gate `<counter>` format never reached the model and the rules never governed. Only an explicit enumerated FIRST STEP in the task body reliably forces kimi to read each rule file (proven: the forced step drove ~17 separate per-file reads → the verbatim `<counter>` block). The per-file-read discipline (one read per file, never a bulk recursive read) carries over from the `model-binding-delta` obligation above — Step 0 names HOW to read so the late-sorting rules (e.g. `rbtv-reasoning.md`) are never truncated out of context. On a launch root with NO `.agents/behavior-rules/`, this composition rule does not fire — dispatch the bare task body unchanged.

### Pre-flight (before any dispatch)

| Check | Command | Gate |
|-------|---------|------|
| CLI present + version | `kimi --version` (`kimi, version 1.41.0`) | Absent/older → re-verify flags against `kimi --help`. |
| **Pinned-flag existence** (routing §4 gate) | `kimi --help` grepped for every non-trivial flag this dispatch pins (`--work-dir`, `--quiet`/`--print`/`--output-format`/`--final-message-only`, `--no-thinking`, `--agent-file`, `--add-dir`, `--session`/`--continue`). **Truncation caveat:** kimi's boxed help TRUNCATES long flag names at narrow widths (`--final-message-only` renders as `--final-message…`) — a literal string match on the boxed output false-negatives (verified live, 2026-06-10). Widen the render (`$env:COLUMNS='250'; kimi --help`) or match the truncated prefix before ruling a flag ABSENT. | Runs EVERY dispatch (NOT only on a version mismatch — a flag can vanish at the SAME version family the manual pinned; codex 0.137.0/`--ask-for-approval` is the cautionary case, p5-2). Any pinned flag absent → STOP, do not dispatch; re-resolve at THIS delta, re-render (`../render-manuals.py`), re-run the gate — NEVER hand-edit the rendered manual or pass an ad-hoc flag. A removed/renamed flag is a hard arg-parse error pre-spend if dispatched. |
| Auth | `kimi login` (interactive, one-time) | Login is interactive → USER-EXECUTED-ONLY. If unauthenticated, halt and ask the owner to run it; never automate it. |
| Guidance file | the LAUNCH ROOT (orchestrator root — the `--work-dir` value) has `AGENTS.md` + `.agents/behavior-rules/`? | Checked at the launch root, NEVER the work-target (the work-target needs no guidance file — the mirror skips nested repos by design). Absent at the launch root → offer to generate it via the mirror (`mirror_entry: kimi-mirror`, see the kimi `mirror-config.yaml`). |

### The two invocation shapes (functionally equivalent — pick by prompt size and host shell)

Kimi accepts the task prompt via one of two equivalent shapes. Pick the shape by prompt size and the host shell's `ARG_MAX`.

**Shape A — `--prompt` CLI argument (small prompts):**

```powershell
kimi --work-dir "<orchestrator-root>" --add-dir "<work-target>" --quiet --prompt "<task_prompt>"
```

Use when the prompt fits comfortably under the host shell's single-argument limit (Linux ~128 KB headroom; Windows PowerShell and Git Bash/MSYS2 both ~32 KB). Default for short, interactive dispatches.

**Shape B — large brief via a FILE POINTER (default in autonomous mode; command BEGINS with `kimi`):**

For a prompt too large to inline (≥ ~30 KB; PowerShell/Git Bash ~32 KB single-arg ceiling), write it to a file and point kimi at it with a SHORT `--prompt`:

```powershell
kimi --work-dir "<orchestrator-root>" --add-dir "<work-target>" --quiet --prompt "Read the file '<prompt-path>' and execute the task it contains exactly; create only the files it allowlists."
```

Kimi loads the brief via its own file tool, so the command stays short AND begins with `kimi` (the in-session permission requirement — generic packaging §1 D17 row). Do **not** pipe the brief with `cat prompt.md | kimi …` for an in-session dispatch: the pipe makes the command line BEGIN with `cat`, which does not match the `kimi:*` prefix rule and falls to the permission classifier. The stdin-pipe form (`cat prompt.md | kimi --work-dir "<orchestrator-root>" --add-dir "<work-target>" --print --input-format text --final-message-only`) stays functionally valid for owner-typed `!` dispatches only. **Both shapes** apply the same launch-root/work-target surface, honor the same return contract, and pass the same allowlist + forbidden-ops + swarm-policy checks on return.

The composed **header + payload** (generic packaging §1) is written to `prompt.md` on disk and dispatched FROM that file — the same prompt file is the reuse surface on resume.

### Variants and the thinking toggle

The kimi manifest declares two routable variants — route on `(kimi, variant)`:

| Variant | Flags added | When |
|---------|-------------|------|
| `default` | (none — thinking ON per the live config `default_thinking = true`) | The validated profile; default for bounded code. Thinking-on does NOT make kimi a judgment worker — it stays non-reasoning. |
| `no-thinking` | `--no-thinking` | Fully-bounded mechanical batches where step-by-step reasoning adds nothing; the cost-floor pick (no thinking tokens emitted). Set `--no-thinking` explicitly — config defaults thinking ON. |

`--thinking` / `--no-thinking` override the config default per dispatch. `--model <id>` overrides the configured model. Neither lifts kimi above `non-reasoning` for routing — reasoning tier is a property of the operating model (M1), not the toggle.

### Exit codes — drive retry/recovery logic

| Code | Meaning | Conductor action |
|------|---------|------------------|
| `0` | Success | Proceed to the return gate (reconcile against disk, then verification card). |
| `1` | Non-retryable (config, auth, quota) | Halt and surface — do NOT retry blindly. |
| `75` | Retryable (rate limits, timeouts, 5xx) | Back off and retry the SAME task — UNLESS the exit-75 recovery trigger fires (below), in which case recover, do not re-run. |

```powershell
kimi --work-dir "<orchestrator-root>" --add-dir "<work-target>" --quiet --prompt "<task>"; $code = $LASTEXITCODE
if ($code -eq 75) { <exit-75 recovery decision — see below> }
elseif ($code -ne 0) { <halt + surface> }
```

### Exit-75 recovery protocol (work landed, return/commit lost)

Kimi can exit 75 on the FINAL return turn — the LLM connection drops AFTER files are written to disk but BEFORE kimi prints the structured return and runs its local commit. The disk state is correct; there is no `[<task-id>]` commit and no Concerns list. NEVER blind-retry (re-runs 25+ min of work, wastes credits, risks the same drop) and NEVER halt-without-checking. Run this recovery instead — it is JUDGMENT work, valid only under a high-reasoning conductor (Opus+); a lower-reasoning conductor halts + surfaces exit 75 unless the plan explicitly authorizes the protocol.

**Trigger — fires only when ALL hold:**

1. Kimi exited non-zero with NO structured return on stdout (no `status`, no `landed`, no commit hash).
2. `git -C "<allowed_workdir>" status --porcelain` shows uncommitted changes inside the task's allowlist.
3. `git -C "<allowed_workdir>" log -1 --pretty=%s` does NOT show the expected `[<task-id>]` prefix (kimi did not commit before exiting).

If ANY is false → standard handling (`BLOCKED` + surface). Mid-task crash (kimi exits before writing files) → standard retry/BLOCKED, NOT this protocol.

**Recovery steps:**

1. **Verify on-disk state** against the task's Implementation Requirements — read each expected file; confirm structure, exports, signatures, content shape; note gaps.
2. **Run the task's declared `test_command` / smoke checks** — the same validation a normal `DONE` return would trigger. Pass → functionally complete despite the transient exit.
3. **Verify allowlist compliance** — `git -C "<allowed_workdir>" diff --name-only HEAD`; every changed path MUST be in the allowlist. Any out-of-allowlist edit → halt + surface (recovery does NOT bless out-of-allowlist writes).
4. **Verify forbidden-ops compliance** — no frozen-doc touches, no push, no force reset.
5. **Commit manually with the recovery marker** — the `(orchestrator-recovered)` subject suffix is MANDATORY (it flags the commit for EXTRA review scrutiny because kimi never printed its Concerns):

   ```bash
   git -C "<allowed_workdir>" add <files-in-allowlist>
   git -C "<allowed_workdir>" commit -m "[<task-id>] <description> (orchestrator-recovered)" \
     -m "Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

6. **Log to the run-log** — exit code, files verified + smoke result, the recovery commit hash, the reason for not retrying, and that the reviewer MUST FULLY re-validate (not trust the orchestrator's smoke pass).

The recovery commit is reversible (`git revert <hash>` restores pre-recovery state, then a fresh dispatch can re-run). Reviewer brief after an `(orchestrator-recovered)` commit: re-validate every Implementation Requirement against the as-shipped code, re-check the behavior contract, and be EXTRA willing to fix in place (kimi printed no Concerns).

**Hung dispatch (kimi never exits):** separate path — orchestrator kills it, evaluates disk state, then decides recover-commit (same steps 1–6) OR re-dispatch a fresh executor.

### Resume mechanics

| Mechanism | Command | Use |
|-----------|---------|-----|
| Resume a specific session | `kimi --work-dir "<orchestrator-root>" --add-dir "<work-target>" --session "<id>" --quiet --prompt "<follow-up>"` | After a `DOUBT_ESCALATED` / `NEEDS_CONTEXT` halt: supply the resolution into the SAME session by id. Re-pass the SAME launch-root/work-target flags as the original dispatch. |
| Continue the work-dir's previous session | `kimi --work-dir "<orchestrator-root>" --add-dir "<work-target>" --continue --quiet --prompt "<follow-up>"` | Pick up the last session for that launch root without tracking an id. |
| Capture the full audit trail | `kimi export <session-id> -o "<work-target>/.kimi-runs/<id>.zip" -y` | Archive session artifacts after a run. |

Avoid `--session` / `--resume` WITHOUT an id in headless mode — it opens an interactive picker. Resume drift warning: resumed long sessions favor prose over the named-field schema — reconcile the resumed return against disk especially hard.

### Allowlist grammar — confinement is the orchestrator's job

Kimi has **no native `--allowlist` / per-path permission flag**, and headless mode auto-approves every tool call. Bound a worker by combining:

| Control | Mechanism |
|---------|-----------|
| Workspace scope | `--work-dir <orchestrator-root>` (the launch root — guidance loads from here) + `--add-dir <work-target>` (+ further `--add-dir <extra>` only when the task needs it; repeatable). Keep the set minimal. |
| Tool surface | `--agent-file <kimi-agent.yaml>` with an explicit `tools` list or `exclude_tools` (e.g. strip `kimi_cli.tools.web:SearchWeb` / `FetchURL` for offline tasks). Use `--agent-file` ONLY when `swarm_policy: allowed` or a tool restriction is required. |
| Read confinement | Inline required context into the task prompt; use the `explore` / `plan` subagent types (read-only) where no writes are needed. |
| **Write confinement** | **Post-run `git -C "<allowed_workdir>" diff --name-only HEAD` of every changed path against the task's `allowlist`** — run in the WORK-TARGET's git, never the launch-root's (a nested-repo work-target has its own git; a launch-root diff passes vacuously). The ONLY reliable enforcement. Out-of-allowlist edit = halt + surface; NEVER auto-revert silently. |
| Commit / push | Local-only by policy; verify git state shows no push since dispatch. |
| Network / prod APIs | No CLI flag blocks these — strip web/MCP tools via the agent file and run with no network MCP servers configured. |

The `allowlist` in the task frontmatter is a list of file/folder globs (computed at planning time). The diff check matches every changed path against it — a glob the change does not match is an out-of-allowlist write.

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| Headless auto-approves all tools (no native allowlist) | Enforce scope externally (workspace + agent-file + post-run diff). |
| Launched with `--work-dir` = a nested-repo work-target → 0 behavior-rules loaded → rules-blind worker (the a3e217d sweep) | NEVER root kimi at the work-target: `--work-dir <orchestrator-root>` + `--add-dir <work-target>`, always (the G1 launch-root split above). |
| No native path allowlist | ALWAYS diff every changed path vs the allowlist on return. |
| `cd` does not persist between shell calls | Each shell command is an independent subprocess — set `--work-dir`; never rely on `cd` chaining in the prompt. |
| Exit 75 on the final return turn | Run the exit-75 recovery protocol (above), never blind-retry. |
| Image input fails | Only if the configured model lacks `image_in` (the live `kimi-for-coding` model has `image_in` + `video_in`; a re-pointed model may not). |
| Work-dir disappears mid-session | Crash report + exit; recover via session id. |
| `stream-json` input strictness | Must be valid JSONL, UTF-8, `\n` endings, one object per line. |
| Ralph-mode runaway | `--max-ralph-iterations -1` loops unbounded — cap it for any autonomous dispatch (live config caps at 0). |

### The kimi task contract (plugs into the shared authoring core)

A kimi-executable task file extends the generic task-file contract (`{rbtv_path}/orchestration/workflows/_shared/authoring/`) with kimi-specific frontmatter and body sections. The orchestrator validates a `executor: kimi` task against this contract BEFORE dispatch; a missing required field = halt + report the malformed task — NEVER infer or mutate a field into shape (task shaping belongs to planning).

**Required frontmatter:**

```yaml
execution_kind: code
executor: kimi
allowed_workdir: <work-target repo path — passed via --add-dir; NEVER the --work-dir launch root>
allowlist:
  - <file-or-folder-glob>
commit_policy: local-only
test_command: <command-or-NONE>
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - external production API calls
doubt_policy: halt
reviewer: claude-opus           # reviewer floor for kimi-produced code is Opus — non-overridable
swarm_policy: disabled | allowed
max_kimi_subagents: <N-or-0>
```

**Required body sections:** Goal (one bounded deliverable) · Context Snapshot (all task-specific context inlined — never make kimi infer from broad PRDs) · Allowed Paths (the allowlist in human-readable form) · Forbidden Paths · Implementation Requirements (exact behavior — interfaces, data shapes, error semantics, every edge case enumerated) · Validation (the exact commands kimi runs before returning) · Commit Rule (local-only after validation) · Swarm Rule (if `allowed`: subagent types, count, task partition) · Return Format (the five-field return schema).

**Swarm mode** (opt-in per task): set `swarm_policy: allowed` + `max_kimi_subagents: N` + a `kimi-agent.yaml` (via `--agent-file`) that defines the allowed subagents, and a prompt that tells kimi when/how to dispatch them. Use ONLY for independent code slices with disjoint allowlists — never for architecture, migrations, schema design, production-API work, or anything needing coordinated shared state. Kimi spawning subagents under `swarm_policy: disabled` is a guardrail failure.

**Review gates** every kimi coding task passes (verification card owns the gate): kimi self-report → orchestrator diff-vs-allowlist check → declared validation passing (or explicit blocker) → Claude/Opus spec-compliance review → Claude/Opus code-quality review → no push until owner/final-workflow publishes. Any gate fails → halt or route a fix task; never proceed on "close enough".

### Recipes

```powershell
# Single bounded worker, final text only (Shape A) — launch root = orchestrator root, work-target via --add-dir:
kimi --work-dir "<orchestrator-root>" --add-dir "5-workbench/inni-cte-recon" --quiet --prompt "<inlined task file content>"
```
```powershell
# Large brief via a FILE POINTER (Shape B — default autonomous/Windows; command BEGINS with `kimi`):
kimi --work-dir "<orchestrator-root>" --add-dir "<work-target>" --quiet --prompt "Read the file '<prompt-path>' and execute the task it contains exactly"
```
```powershell
# Constrained tools + streamed JSON for parsing:
kimi --work-dir "<orchestrator-root>" --add-dir "<work-target>" --agent-file "<kimi-agent.yaml>" --print --output-format stream-json --prompt "<task>"
```
```powershell
# Retry on transient failure (exit 75) — only when the recovery trigger does NOT fire:
kimi --work-dir "<orchestrator-root>" --add-dir "<work-target>" --quiet --prompt "<task>"; $c=$LASTEXITCODE
if ($c -eq 75) { Start-Sleep 10; kimi --work-dir "<orchestrator-root>" --add-dir "<work-target>" --quiet --prompt "<task>" }
```
<!-- RENDER:DELTA-END invocation -->
