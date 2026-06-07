<!-- AUTO-GENERATED — DO NOT EDIT. Rendered by orchestration/models/render-manuals.py from orchestration/skills/orchestrating/cards/dispatch-wrapper.md + orchestration/models/kimi/delta.md. -->

> [!danger] GENERATED FILE — DO NOT EDIT
> This dispatch manual is composed by `orchestration/models/render-manuals.py` from:
> - the generic dispatch contract `orchestration/skills/orchestrating/cards/dispatch-wrapper.md`, and
> - the `kimi` package delta `orchestration/models/kimi/delta.md`.
>
> Hand-edits are overwritten on the next render and are forbidden. To change
> packaging/addendum/return behavior, edit the wrapper template; to change
> kimi-specific behavior, edit the delta. Then re-render:
>
> ```
> python orchestration/models/render-manuals.py
> ```

## 1. Task packaging — the dispatchable unit

The unit sent to a worker is a **self-contained task artifact** (it already satisfies §1–§7 of the task-file contract — this card does not re-author it) composed with the run's binding context. Composition is **header + payload**, never a rewrite of the task file.

| Element | Rule |
|---------|------|
| **Payload = the task file, verbatim** | The dispatched prompt carries the task file's content unedited and untruncated. The worker reads NOTHING from conversation history — the artifact IS the brief. Editing the task body at dispatch time is forbidden; if the task is wrong, fix the task file (and log the amendment), then re-dispatch. |
| **Header = run-binding context** | Prepend only what the worker needs that is not already in the task file: the binding addendum (§2), the return schema (§3), the run's worker-facing `decisions.md` pointer (or its inlined relevant entries), and — for a research leaf — the `rbtv-web-searching` directive in imperative form. The header is composed; the payload is verbatim. |
| **Prompt-file reuse** | For workers driven by a prompt file (CLI workers, and Agent-tool dispatches large enough to warrant it), write the composed header+payload to a prompt file on disk and dispatch FROM that file. The same prompt file is the reuse surface on resume — re-dispatch reads the file, it is not re-composed from memory. |
| **One dispatch = one bounded task (or one disjoint-allowlist batch)** | Routing sized the batch (30–90 min, disjoint allowlists for parallel workers). This card packages exactly that unit — never silently merge two tasks into one dispatch. |

### Reference-doc inlining (D21)

A task references other documents. The conductor decides per referenced doc whether the worker reads the source or receives an inlined excerpt — and MARKS each reference so the worker knows which:

| Reference kind | Mark | Worker behavior |
|----------------|------|-----------------|
| **Inlined** | `[INLINED]` | The relevant excerpt is pasted into the header under a labelled heading (`### {Doc} — {Section}`, with source path). The worker treats the excerpt as authoritative and does NOT re-read the source unless escalating a doubt. |
| **Full read** | `[FULL READ]` | The worker opens the source itself via its file tool when it needs the content. |

Inlining rules:

| Rule | Detail |
|------|--------|
| Inline frozen-doc and credential excerpts — never grant read access | A frozen reference doc or a credentials path is inlined as the needed excerpt; the worker is NEVER given a read path into it. (Mirrors routing's pre-staging rule: judgment over external files → extend read surface; mechanical need of a fixed excerpt → inline/pre-stage it.) |
| Inline what is small and load-bearing; point to what is large | A short contract clause the work hinges on → inline it. A large design doc the worker may need parts of → `[FULL READ]` with the exact section named. Budget per the task-file contract's context budgets — a task whose inlined context will not fit gets split, not truncated. |
| Each inlined excerpt is standalone | Do not assume cross-references between excerpts unless stated; label each with its source so a doubt-escalation can find the full doc. |
## 2. The binding addendum — worker obligations

Every dispatch carries this addendum in its header. These are the obligations the worker is held to regardless of model; they are the conductor's enforcement contract on return. State them imperatively in the dispatch ("you MUST…", "return…", "do NOT…") — never permissively.

| Obligation | What the worker is bound to |
|------------|-----------------------------|
| **Return-schema compliance** | Return the named-field schema in §3 exactly — every field, no field renamed, none invented. The conductor parses these fields; a prose-only return is a contract violation that triggers re-exercise of the return, not acceptance. |
| **Allowlist boundary** | Create / modify / delete ONLY the files in the task's allowlist. Out-of-allowlist file ops are not silently wrong but are NOT silent — they force conductor review (the conductor diffs actual changes against the allowlist on return). State the allowlist in the dispatch even though the task file also carries it. |
| **Halt / doubt policy** | On ambiguity the task does not resolve, HALT and return `DOUBT_ESCALATED` (or `NEEDS_CONTEXT`) — never guess, never improvise past a doubt. A fully-bounded task should contain no ambiguity; if the worker hits one, the task was under-specified and the conductor needs to know. |
| **Evidence-file requirement** | Capture validation evidence as FILES on disk during the work (command output, logs, screenshots for UI), not as prose claims in the reply. For CLI workers the return message is lossy at session end (documented: a completed dispatch returned a garbage final message while the commit had landed) — evidence on disk is what survives. The `validation` field cites what was run; the captures are the proof. |
| **Commit discipline** | Commits go through `rbtv-commit` (routing pins this to a commit-capable worker — CLI workers are kept OFF commits by default). Local commits only; NEVER push. A CLI worker is authorized to self-commit ONLY when its task file / model delta explicitly grants it (the default is no self-commit; the kimi package's delta is where a code-executing worker's local-commit authorization is declared). When the worker IS authorized: validation passes first, the commit message follows the run's mandated convention, and the returned commit hash must match what is actually in `git log` (the conductor checks the message string and the hash, not just the file list). |
| **Forbidden operations** | Honor the task's forbidden-ops list (no pushes, no writes outside the allowed work-dir, no destructive git resets, no external production API calls unless the task explicitly allows a mocked/local one). |

The addendum is GENERIC. A model package's delta MAY add model-specific obligations on top (e.g., a worker that must be told not to write stray files in the repo root, or a swarm-policy constraint) — it plugs in at the insertion point below and NEVER restates the generic obligations.

**Kimi-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What kimi is bound to |
|------------|------------------------|
| **Non-reasoning executor** | Kimi MUST NOT reason, decide, or interpret intent. Every interface, edge case, validation, and routing decision is pre-resolved in the task file. Kimi implements the enumerated behavior; it never designs, never "handles reasonably", never "fills in the blanks". A decision left to kimi is a planning bug, not kimi's call. |
| **No agentic exploration** | The task file's allowed paths are kimi's entire read/write universe. Kimi MUST NOT decide which files to read, MUST NOT load other task files / the plan / decisions.md beyond what the header inlines. Required context is inlined into the task body — kimi never goes reading broad PRDs at runtime (the ~250K budget is for inlined facts). |
| **Stray-file ban** | Create files ONLY where the allowlist directs. NEVER write scratch notes, logs, or summary files into the repo root or anywhere outside the allowlist — the post-run diff treats any such file as an out-of-allowlist write. |
| **Local-commit authorization (this is where a code worker's self-commit is granted)** | Kimi MAY commit locally — and ONLY locally — after its declared validation passes, when the task file grants `commit_policy: local-only`. NEVER push, NEVER force-reset, NEVER amend. The commit subject MUST carry the run's mandated `[<task-id>]` convention; the returned hash MUST match `git log`. Absent an explicit grant, kimi does NOT commit (the conductor commits via `rbtv-commit`). |
| **Swarm policy** | Kimi launches its own subagents (coder / explore / plan) ONLY when the task file sets `swarm_policy: allowed` with `max_kimi_subagents: N`. With `swarm_policy: disabled` (the default), kimi launching ANY subagent is a guardrail failure the conductor treats as a failed dispatch — surface it. Subagents cannot nest (one level only). |
| **Forbidden-ops are exhaustive** | The task's `forbidden_ops` list is the complete prohibition set; absence of mention is NOT permission. No writes outside the allowed work-dir, no `git push`, no destructive git reset, no external production API calls unless the task explicitly sanctions a mocked/local one. |
<!-- The model package delta inserts its model-specific binding obligations here. -->
## 3. The unified return schema (D8)

ONE schema for EVERY worker — bounded CLI worker, mid-tier Claude, top-tier conductor-grade Claude, research worker. The fields are FIXED: the schema is named-field precisely because prose returns drift (resumed long-context sessions favored conversational summaries over the contract — five instances in one session). Named fields are the conductor's parse surface and the substrate the tripwire field-checks (§4) run against.

The worker returns exactly these five fields:

| Field | Content |
|-------|---------|
| **`status`** | EXACTLY one of: `DONE` · `DONE_WITH_NOTES` · `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT`. No other value is valid. |
| **`landed`** | What actually changed on disk: files created/modified/deleted, and the commit hash(es) if the worker committed. This is the claim the conductor reconciles against `git status` / `git log`. |
| **`validation`** | Each validation performed: the command run, its `EXIT` code, its `WALL_MS` (wall-clock duration), and any skipped check WITH its reason. The sub-field `SKIPPED_COUNT` carries the number of checks skipped (0 when none); any skip it counts MUST carry a per-skip reason — a skip without a reason, or `SKIPPED_COUNT > 0` with no reasons, is a contract violation. Empty validation on a code task is itself a flag. |
| **`concerns`** | Anything the worker noticed that the conductor should weigh — risks, smells, partial confidence, adjacent issues spotted but not fixed. Distinct from blockers: concerns did not stop the work. |
| **`open_questions`** | Questions the worker could not resolve and that bear on this or downstream work. For `DOUBT_ESCALATED` / `NEEDS_CONTEXT` this carries the precise question that halted the work. |

### Status semantics

| Status | Means | Conductor's next move |
|--------|-------|-----------------------|
| `DONE` | Every contracted outcome met; nothing to surface | Reconcile against disk, then proceed (verification card owns the gate). |
| `DONE_WITH_NOTES` | Work landed, but `concerns` / `open_questions` carry items worth the conductor's attention | Reconcile, then weigh the notes before proceeding. |
| `BLOCKED` | Work could not be completed — an external obstacle, a failed validation that the worker cannot resolve | Route recovery (recovery card); do NOT mark the task done. |
| `DOUBT_ESCALATED` | The worker hit an ambiguity and stopped rather than guess; `open_questions` holds the doubt | Resolve the doubt (halt-to-user or a doc-reader), then **resume** per halt-recovery §2 (same CLI session via `-r` where supported; a fresh re-dispatch for an Agent-tool worker that has no session) — never accept a guess in its place. Halt-recovery owns the resume-vs-re-dispatch choice. |
| `NEEDS_CONTEXT` | The task lacked something the worker needed to proceed (a missing file, an unstated decision) | Supply the context (amend the task file + log it), then resume / re-dispatch per halt-recovery §2. |

### Transport — same fields, two carriers

The schema is identical across workers; only HOW the fields arrive differs by worker type. This is the one axis the per-model delta touches for the return.

| Worker type | Transport |
|-------------|-----------|
| **Agent-tool helper (Claude sub-agent)** | The five fields ARE the final reply — the sub-agent writes them as its return message; there is no separate file channel required. |
| **CLI worker (`kimi`, `codex exec`, `claude -p`, `qwen`, …)** | The fields appear in the worker's final message AND the evidence they cite is on disk as files. The final message is treated as a HINT; the disk state and the cited evidence files are the truth the conductor reconciles. |
| **sdd composite dispatch (`superpowers:subagent-driven-development`)** | sdd is ONE composite dispatch wrapped by the outer gates (routing §5). Its outer-wrapper return carries the five fields as the in-session final reply — same as the Agent-tool row — over its whole code body; its internal TDD sub-structure is not surfaced as separate returns. |

**Kimi return surface:** kimi runs headless with `--quiet` (alias for `--print --output-format text --final-message-only`), which prints ONLY kimi's final assistant message to stdout — that message carries the five return fields. Treat it as a HINT, never the truth: a documented failure mode is kimi exiting 75 on the final return turn with the work correctly on disk but the structured message garbled or absent, and resumed long-context sessions drifting to conversational prose over the named-field schema (five instances in one session). The conductor reconciles every kimi return against `git status` / `git log` of the work-dir and the cited evidence files on disk — disk wins on any disagreement. For machine-parseable streaming, `--output-format stream-json` emits one JSON object per line; parse the last `assistant` message without `tool_calls` as the final result.
<!-- The model package delta names this worker's exact return surface (e.g., the CLI's final-message flag, the evidence-file convention) here. The fields above never change. -->

---

## Invocation — the exact command shape

The kimi CLI dispatch manual — the exact command shapes, flags, exit handling, resume, recovery, and the kimi task contract. Self-contained: this is the orchestrator's complete runtime kimi spec (the dissolved `kimi-code-execution` / M3 content). Verified against Kimi CLI **1.41.0** (`kimi info --json` → `agent_spec_versions: ["1"]`, `wire_protocol_version: "1.9"`). Re-verify with `kimi --help` / `kimi --version` before relying on any flag — the CLI evolves fast; `--help` is ground truth for the installed build.

### Pre-flight (before any dispatch)

| Check | Command | Gate |
|-------|---------|------|
| CLI present + version | `kimi --version` (`kimi, version 1.41.0`) | Absent/older → re-verify flags against `kimi --help`. |
| Auth | `kimi login` (interactive, one-time) | Login is interactive → USER-EXECUTED-ONLY. If unauthenticated, halt and ask the owner to run it; never automate it. |
| Guidance file | target workspace has `AGENTS.md`? | Absent → offer to generate it via the mirror (`mirror_entry: kimi-mirror`, see the kimi `mirror-config.yaml`). |

### The two invocation shapes (functionally equivalent — pick by prompt size and host shell)

Kimi accepts the task prompt via one of two equivalent shapes. Pick the shape by prompt size and the host shell's `ARG_MAX`.

**Shape A — `--prompt` CLI argument (small prompts):**

```powershell
kimi --work-dir "<allowed_workdir>" --quiet --prompt "<task_prompt>"
```

Use when the prompt fits comfortably under the host shell's single-argument limit (Linux ~128 KB headroom; Windows PowerShell and Git Bash/MSYS2 both ~32 KB). Default for short, interactive dispatches.

**Shape B — stdin pipe (large prompts; default in autonomous mode):**

```bash
cat prompt.md | kimi --work-dir "<allowed_workdir>" --print --input-format text --final-message-only
```

Use when the prompt is ≥ ~30 KB OR when running autonomously and you cannot afford a per-prompt size halt. `--quiet` is a documented alias for `--print --output-format text --final-message-only`; the stdin pipe replaces the `--prompt TEXT` arg with the same content via standard input. **Both shapes** apply the same `--work-dir` surface, honor the same return contract, and pass the same allowlist + forbidden-ops + swarm-policy checks on return. Default to Shape B at ≥30 KB or in autonomous mode; Shape A is fractionally less ceremony for small interactive dispatches. (Windows note: Git Bash/MSYS2 has a tighter arg limit than Linux; PowerShell ~32 KB single arg. Both pipe cleanly via stdin — prefer Shape B on Windows for any non-trivial prompt.)

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
kimi --work-dir "<repo>" --quiet --prompt "<task>"; $code = $LASTEXITCODE
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
| Resume a specific session | `kimi --work-dir "<repo>" --session "<id>" --quiet --prompt "<follow-up>"` | After a `DOUBT_ESCALATED` / `NEEDS_CONTEXT` halt: supply the resolution into the SAME session by id. |
| Continue the work-dir's previous session | `kimi --work-dir "<repo>" --continue --quiet --prompt "<follow-up>"` | Pick up the last session for that work-dir without tracking an id. |
| Capture the full audit trail | `kimi export <session-id> -o "<repo>/.kimi-runs/<id>.zip" -y` | Archive session artifacts after a run. |

Avoid `--session` / `--resume` WITHOUT an id in headless mode — it opens an interactive picker. Resume drift warning: resumed long sessions favor prose over the named-field schema — reconcile the resumed return against disk especially hard.

### Allowlist grammar — confinement is the orchestrator's job

Kimi has **no native `--allowlist` / per-path permission flag**, and headless mode auto-approves every tool call. Bound a worker by combining:

| Control | Mechanism |
|---------|-----------|
| Workspace scope | `--work-dir <repo-root>` + `--add-dir <extra>` (repeatable). Keep the set minimal. |
| Tool surface | `--agent-file <kimi-agent.yaml>` with an explicit `tools` list or `exclude_tools` (e.g. strip `kimi_cli.tools.web:SearchWeb` / `FetchURL` for offline tasks). Use `--agent-file` ONLY when `swarm_policy: allowed` or a tool restriction is required. |
| Read confinement | Inline required context into the task prompt; use the `explore` / `plan` subagent types (read-only) where no writes are needed. |
| **Write confinement** | **Post-run `git diff --name-only HEAD` of every changed path against the task's `allowlist`** — the ONLY reliable enforcement. Out-of-allowlist edit = halt + surface; NEVER auto-revert silently. |
| Commit / push | Local-only by policy; verify git state shows no push since dispatch. |
| Network / prod APIs | No CLI flag blocks these — strip web/MCP tools via the agent file and run with no network MCP servers configured. |

The `allowlist` in the task frontmatter is a list of file/folder globs (computed at planning time). The diff check matches every changed path against it — a glob the change does not match is an out-of-allowlist write.

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| Headless auto-approves all tools (no native allowlist) | Enforce scope externally (workspace + agent-file + post-run diff). |
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
allowed_workdir: <absolute-or-project-root-relative repo path>
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
# Single bounded worker, final text only (Shape A):
kimi --work-dir "5-workbench/inni-cte-recon" --quiet --prompt "<inlined task file content>"
```
```bash
# Large prompt via stdin (Shape B — default autonomous/Windows):
cat prompt.md | kimi --work-dir "<repo>" --print --input-format text --final-message-only
```
```powershell
# Constrained tools + streamed JSON for parsing:
kimi --work-dir "<repo>" --agent-file "<kimi-agent.yaml>" --print --output-format stream-json --prompt "<task>"
```
```powershell
# Retry on transient failure (exit 75) — only when the recovery trigger does NOT fire:
kimi --work-dir "<repo>" --quiet --prompt "<task>"; $c=$LASTEXITCODE
if ($c -eq 75) { Start-Sleep 10; kimi --work-dir "<repo>" --quiet --prompt "<task>" }
```
