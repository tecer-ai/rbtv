<!-- AUTO-GENERATED — DO NOT EDIT. Rendered by orchestration/models/render-manuals.py from orchestration/skills/orchestrating/cards/dispatch-wrapper.md + orchestration/models/qwen-code-cli/delta.md. -->

> [!danger] GENERATED FILE — DO NOT EDIT
> This dispatch manual is composed by `orchestration/models/render-manuals.py` from:
> - the generic dispatch contract `orchestration/skills/orchestrating/cards/dispatch-wrapper.md`, and
> - the `qwen-code-cli` package delta `orchestration/models/qwen-code-cli/delta.md`.
>
> Hand-edits are overwritten on the next render and are forbidden. To change
> packaging/addendum/return behavior, edit the wrapper template; to change
> qwen-code-cli-specific behavior, edit the delta. Then re-render:
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
| API-worker dispatch is ALL-`[INLINED]` | An API worker has no file-read tool — it can never do a `[FULL READ]`. EVERY reference in an API-worker dispatch MUST be `[INLINED]`; the runner inlines each `--target-file` into the request. The whole composed prompt is bounded by the variant's `context_window` — a dispatch that won't fit must be SPLIT, never handed off as a path for the worker to read. |
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
| **Rule-loading (mirror-equipped workspace)** | Before ANY other action — before reading any task-referenced file, writing, running a tool, or responding — inspect your work-dir for a `.agents/behavior-rules/` directory. If it exists (a mirror-equipped workspace), you MUST FIRST read your own guidance file at the work-dir root (`AGENTS.md` for a Codex/Kimi worker, `QWEN.md` for a qwen worker) AND every file under `.agents/behavior-rules/`, and treat their entire contents as binding, non-negotiable rules governing this whole session — exactly as if they were part of this dispatch. Reading them is mandatory even when this task body never mentions rules; the absence of a rule-read instruction in the task is NOT permission to skip them. If the work-dir has no `.agents/behavior-rules/` directory, this obligation is a silent no-op — proceed normally. |

**Conductor obligation — instruct the rule-read for harnesses that do NOT auto-read (CLI workers).** A CLI worker whose governance depends on the behavior-rule fan-out only obeys the Rule-loading obligation above if its harness actually reads its rules directory. Harnesses differ: **codex auto-reads** its rules directory (no explicit instruction needed); **kimi and qwen do NOT** — kimi needs an enumerated Step-0 naming the read, and qwen ignores even imperative directory-read prose unless the dispatch invokes its `QWEN.md` preamble by name OR names the specific rule files (qwen delta `model-binding-delta`). So when composing a dispatch for a non-auto-reading CLI worker in a mirror-equipped work-dir, the conductor MUST add an EXPLICIT rule-read instruction to the dispatch prompt (the per-model proven form, from that model's delta); do NOT rely on the generic obligation alone. That instruction MUST tell the worker to read the rule files ONE FILE PER CALL (or in small batches) — NEVER a single recursive bulk read: a bulk `Get-Content -Recurse`-style read of a multi-file rule library truncates silently mid-corpus, so an alphabetically-later rule's body never reaches the model and the obligation it carries goes unread despite the read "firing" (the 2026-06-09 kimi `<counter>` incident). (The mirror-driver `guidance.py` half of this guarantee is deferred to the mirror-install follow-up — not authored here.)

The addendum is GENERIC. A model package's delta MAY add model-specific obligations on top (e.g., a worker that must be told not to write stray files in the repo root, or a swarm-policy constraint) — it plugs in at the insertion point below and NEVER restates the generic obligations.

**Qwen-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What qwen is bound to |
|------------|------------------------|
| **Approval mode is the confinement dial, and it is the conductor's to set** | A non-interactive dispatch MUST set `--approval-mode` explicitly. **For headless WRITE work, `yolo` (= `-y`) is REQUIRED** (or an explicit `--allowed-tools` grant): live-proven on qwen 0.17.1 (p2-3, 2026-06-10), headless `--approval-mode auto` DENIES every write/edit/shell tool call outright ("…use the -y flag"), so `auto` is READ-ONLY in practice and `auto-edit` cannot be relied on to write headless either. `yolo` auto-approves ALL tool calls and runs at host privilege with NO sandbox (probe-confirmed warning) — use it for headless write work with the post-run diff + a minimal workspace scope as the boundary. Reserve `auto` (and `auto-edit`) for read-only/analysis leaves where no write is needed. NEVER leave the mode at `default` for a headless run (it prompts for approval and stalls). Suppress the yolo host-privilege notice with `QWEN_CODE_SUPPRESS_YOLO_WARNING=1` when `yolo` is the chosen posture. The `--sandbox`/`-s` container option exists (Docker/Podman-backed) but is **AUTH-PENDING + backend-unverified** on this Windows host — confirm a container backend before relying on it; do NOT assume `--sandbox` is available. |
| **Workspace scope is the CWD root + `--include-directories`/`--add-dir`; there is no single `--work-dir` flag** | The current working directory IS the workspace root; extra writable/readable dirs are ADDITIVE via `--include-directories` (alias `--add-dir`, comma-separated or repeated). Keep the set minimal. Files created/modified outside the scoped workspace are an out-of-allowlist write the conductor catches on the post-run diff — surface, never auto-revert. For parallel waves, prefer `--worktree` (native isolation, below) over sharing a work-dir. |
| **No self-commit unless the task grants it (default OFF)** | Qwen MAY commit locally — and ONLY locally — after its declared validation passes, when the task file grants `commit_policy: local-only`. NEVER push, NEVER force-reset, NEVER amend. The commit subject MUST carry the run's mandated `[<task-id>]` convention; the returned hash MUST match `git log`. Absent an explicit grant, qwen does NOT commit (the conductor commits via `rbtv-commit`). This authorization, and the commit-message convention's survival across a qwen run, are AUTH-PENDING — verify the hash and the subject string on return. |
| **Auth is a USER-EXECUTED-ONLY pre-flight, not a runtime grant** | An unauthenticated headless run exits 1 (`No auth type is selected …`, probe-verified). The orchestrator CANNOT self-provision Qwen auth — OAuth needs a browser it cannot drive headlessly, and API-key auth needs the user to obtain a key from a paid provider and place it in env/settings (the free OAuth tier was discontinued 2026-04-15). Before any headless dispatch, confirm auth is configured; if not, HALT and ask the owner to run the §auth pre-flight. NEVER attempt to complete the OAuth browser flow or fabricate a key. |
| **Tool-call budgets are the runaway guard, and `--continue`/`--resume` need chat recording** | Bound every unattended dispatch with `--max-wall-time` (e.g. `10m`) and `--max-session-turns` (e.g. `30`); add `--max-tool-calls` where the tool count is knowable. Qwen has NO retryable-throttle exit code — set `QWEN_CODE_UNATTENDED_RETRY=1` so transient 429/529 retry in-process (capped 5 min, 30s stderr heartbeat) rather than bouncing an external retry loop. `--continue`/`--resume`/`--session-id`/`--fork-session` work ONLY with chat recording ON (the default unless `--chat-recording false`) — do NOT disable recording on a dispatch you may need to resume. |
| **Stray-file ban** | Create files ONLY where the allowlist directs. NEVER write scratch notes, logs, or summary files into the repo root or anywhere outside the allowlist — the post-run diff treats any such file as an out-of-allowlist write. Use `--json-file <path>` (or capture stdout) to land the structured result at a known path INSIDE the allowlist rather than scattering files. |
| **Forbidden-ops are exhaustive** | The task's `forbidden_ops` list is the complete prohibition set; absence of mention is NOT permission. No writes outside the scoped work-dir, no `git push`, no destructive git reset, no external production API calls unless the task explicitly sanctions a mocked/local one, no `--yolo` without the task sanctioning host-privilege auto-approval. |
| **Rule-read must name the file or invoke the `QWEN.md` preamble's own language** | Generic directory-read prose ("read `.agents/behavior-rules/`") does NOT reliably make qwen3.6-plus fan out and actually read the rule files — it answers from priors and the read never fires. When the generic Rule-loading obligation applies (a `.agents/behavior-rules/` directory exists), the dispatch MUST drive the read in ONE of two proven ways: (a) invoke `QWEN.md`'s OWN preamble language by name — "your `QWEN.md` preamble requires reading every file under `.agents/behavior-rules/` before any action; do that now, reading each file individually"; OR (b) NAME the specific rule files to read explicitly. Either form triggers the fan-out read; bare generic prose does not (proven p3-3: fmt1 name-file + fmt3 preamble-language read the rules, fmt2 generic prose did not). Read each file individually so no rule body is dropped. |
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

### Transport — same fields, multiple carriers

The schema is identical across workers; only HOW the fields arrive differs by worker type. This is the one axis the per-model delta touches for the return.

| Worker type | Transport |
|-------------|-----------|
| **Agent-tool helper (Claude sub-agent)** | The five fields ARE the final reply — the sub-agent writes them as its return message; there is no separate file channel required. |
| **CLI worker (`kimi`, `codex exec`, `claude -p`, `qwen`, …)** | The fields appear in the worker's final message AND the evidence they cite is on disk as files. The final message is treated as a HINT; the disk state and the cited evidence files are the truth the conductor reconciles. |
| **sdd composite dispatch (`superpowers:subagent-driven-development`)** | sdd is ONE composite dispatch wrapped by the outer gates (routing §5). Its outer-wrapper return carries the five fields as the in-session final reply — same as the Agent-tool row — over its whole code body; its internal TDD sub-structure is not surfaced as separate returns. |
| **API worker (shared runner `models/_api/run.py`)** | The conductor invokes `run.py` via Bash; the RUNNER writes the deliverable output file(s) AND a `return.json` carrying the five fields into the conductor-supplied `--output-folder`. The conductor reads the output folder + `return.json` — the API model cannot write to the repo, run git, or commit. Same "message is a hint, disk is truth" discipline; here "disk" = the output folder, NOT a git repo (so reconciliation is file-exists + non-empty + envelope-valid, not `git log`). |

**Qwen return surface:** run headless by supplying the prompt non-interactively (positional argument — canonical on `0.17.1`; `-p`/`--prompt` is deprecated-but-functional) WITHOUT `-i`/`--prompt-interactive`. Add `--output-format json` for a buffered machine-readable result object at completion (message objects of type `system`/`assistant`/`result`); `text` (default) prints the human-readable final message; `stream-json` emits line-delimited events live. The exact `json`/`stream-json` payload shape is **docs-sourced, AUTH-PENDING** — treat the documented field names (`assistant.message.content`/`usage`/`model`; `result.subtype`/`is_error`/`duration_ms`/`usage`) as the contract and confirm against a real authenticated run. The worker carries the five return fields in that final message; treat the message as a HINT, never the truth. Qwen runs autonomously to completion under `--approval-mode yolo`/`auto`, so a dropped or garbled final turn is possible (AUTH-PENDING failure surface — not corpus-validated; reconcile from disk). The conductor reconciles every qwen return against `git status` / `git log` of the work-dir and the cited evidence files on disk — disk wins on any disagreement. For a strictly-shaped final response, `--json-schema <json|@path>` (HEADLESS ONLY) registers a synthetic `structured_output` tool and ends the session on the first valid call — the durable structured return.
<!-- The model package delta names this worker's exact return surface (e.g., the CLI's final-message flag, the evidence-file convention) here. The fields above never change. -->

---

## Invocation — the exact command shape

The qwen CLI dispatch manual — the exact command shapes, flags, approval/confinement grammar, exit handling, resume, and the qwen task contract. Verified against **Qwen Code CLI `0.17.1`** (`qwen --version` → `0.17.1`; `npm ls -g` → `@qwen-code/qwen-code@0.17.1`; Node `v24.11.1`) on Windows 11. Re-verify with `qwen --help` / `qwen --version` before relying on any flag — the CLI evolves fast; `--help` is ground truth for the installed build. Node `>=22.0.0` required. Evidence boundary: CLI launch, flag-parsing, and the exit-1 auth-gate are locally verified; the exit-0 success path, JSON output shape, and swarm/turn facets are **AUTH-PENDING** (auth-gated, §auth) until the p5-2 smoke probe and are marked where it matters.

### Pre-flight (before any dispatch)

| Check | Command | Gate |
|-------|---------|------|
| CLI present + version | `qwen --version` (`0.17.1`); `npm ls -g @qwen-code/qwen-code` | Absent/older → re-verify flags against `qwen --help`. Node `>=22.0.0`. |
| **Pinned-flag existence** (routing §4 gate) | `qwen --help` grepped for every non-trivial flag this dispatch pins (`--approval-mode`/`-y`, `--output-format`, `--include-directories`/`--add-dir`, `--worktree`, `--max-wall-time`/`--max-session-turns`/`--max-tool-calls`, `--json-file`/`--json-schema`, `--resume`/`--session-id`, `--exclude-tools`) | Runs EVERY dispatch (NOT only on a version mismatch — a flag can vanish at the SAME version family the manual pinned; codex 0.137.0/`--ask-for-approval` is the cautionary case, p5-2). Any pinned flag absent → STOP, do not dispatch; re-resolve at THIS delta, re-render (`../render-manuals.py`), re-run the gate — NEVER hand-edit the rendered manual or pass an ad-hoc flag. A removed/renamed flag is a hard arg-parse error pre-spend if dispatched. (Note: the `qwen auth` subcommand was already removed — exactly this drift class.) |
| Auth | one auth type MUST be selected (flag / env / `~/.qwen/settings.json`) | Unauthenticated headless run exits 1 (`No auth type is selected …`). Auth is interactive/key-provisioning → USER-EXECUTED-ONLY. If unauthenticated, halt and ask the owner to run the §auth pre-flight; never automate it. |
| Guidance file | target workspace has `QWEN.md`? | Absent → offer to generate it via the mirror (`mirror_entry: qwen-mirror`, see the qwen `mirror-config.yaml`). Qwen natively reads `QWEN.md` (project + `~/.qwen/QWEN.md`, hierarchical); `AGENTS.md` is supported via the `context.fileName` setting. |

### The canonical invocation shape — headless, one bounded task

Headless mode is entered by supplying a prompt non-interactively WITHOUT `-i`/`--prompt-interactive`. The default positional behavior is one-shot (`qwen [query..]` → "Defaults to one-shot"): the process runs the task and exits; stdout is the return, the exit code signals success/budget/error.

**Shape A — positional prompt (canonical on 0.17.1; small prompts):**

```powershell
$env:QWEN_CODE_UNATTENDED_RETRY = "1"   # in-process 429/529 retry for unattended runs
qwen "<self-contained task prompt>" --output-format json --approval-mode yolo `
  --max-session-turns 30 --max-wall-time 10m
```

The prompt is a **POSITIONAL argument**. `--help` marks `-p`/`--prompt` deprecated ("Use the positional prompt instead. This flag will be removed in a future version.") though `-p` still works today — prefer the positional form for forward-compatibility; fall back to `-p` only if a downstream tool requires a flag.

**Shape B — stdin pipe (large prompts / when the prompt content is a file):**

```powershell
# PowerShell:
Get-Content prompt.md | qwen "<instruction>" --output-format json --approval-mode yolo --max-wall-time 10m
```
```bash
# bash: the positional prompt is APPENDED to the piped stdin input
cat prompt.md | qwen "<instruction>" --output-format json --approval-mode yolo --max-wall-time 10m
```

Prompt transport is **either** — positional arg OR stdin pipe; a positional/`-p` prompt is appended to any stdin content. **Both shapes** apply the same approval mode, the same workspace scope (CWD + `--add-dir`), and pass the same allowlist + forbidden-ops checks on return. The composed **header + payload** (generic packaging §1) is written to `prompt.md` on disk and dispatched FROM that file — the same prompt file is the reuse surface on resume. (Windows note: PowerShell stdin uses `Get-Content file | qwen "..."`; positional and stdin both work — prefer stdin for any non-trivial prompt to avoid an arg-size ceiling.)

### Approval + sandbox grammar — the confinement axis

| Flag | Values | Use |
|------|--------|-----|
| `--approval-mode` | `plan` · `default` · `auto-edit` · `auto` · `yolo` | The PRIMARY confinement dial. `plan` = plan only (no execution). `default` = prompt for approval (STALLS headless — never use). `auto-edit` = auto-approve edit tools only. `auto` = **headless: DENIES every write/edit/shell tool call outright** ("Tool requires user approval but cannot execute in non-interactive mode… use the -y flag") — live-proven on qwen 0.17.1 (p2-3, 2026-06-10), refuting the earlier docs-sourced "LLM classifier auto-approves safe / blocks risky" reading for headless runs. A headless `auto` dispatch is **READ-ONLY in practice**; use it ONLY for read-only/analysis leaves. For headless WRITE work use `yolo`/`-y` (or an explicit `--allowed-tools` grant). `yolo` = auto-approve ALL, host privilege, no sandbox. |
| `--yolo` / `-y` | (flag) | Shorthand for `--approval-mode yolo`. Auto-approve all actions, no sandbox implied. Suppress the host-privilege notice with `QWEN_CODE_SUPPRESS_YOLO_WARNING=1`. |
| `--sandbox` / `-s` | (flag) | Docker/Podman-backed container isolation (or `QWEN_SANDBOX` env / `tools.sandbox` setting; image via `tools.sandboxImage`). **AUTH-PENDING + backend-unverified on this Windows host** — verify the container backend before relying on it. |
| `--include-directories` / `--add-dir` | path(s) (comma-sep or repeated) | Additional workspace directories alongside the CWD root. There is NO single `--work-dir` flag — the CWD is the root; extra dirs are additive. Keep minimal. |
| `--worktree` | `[SLUG\|#PR\|URL]` | Run the session inside a git worktree at `<repoRoot>/.qwen/worktrees/<slug>/`. Bare `--worktree` auto-generates a slug. The native parallel-isolation primitive (kimi requires manual worktree setup). |
| `--exclude-tools` | ARRAY | Strip tools (e.g. web/shell) for an offline or narrowed dispatch. The tool-stripping control. |
| `--allowed-tools` | ARRAY | Allowlist that bypasses confirmation for the named tools. |
| `--core-tools` | ARRAY | Restrict the core tool set. |
| `--allowed-mcp-server-names` | ARRAY | Restrict which configured MCP servers the worker may reach. |
| `--bare` | (flag) | Skip implicit startup auto-discovery; honor only explicit CLI inputs. Use for a clean, reproducible dispatch independent of ambient config. |

**Confinement is the orchestrator's job:** `--approval-mode` and `--sandbox` are real, but headless `--yolo` runs at host privilege with no sandbox (probe-confirmed) and the container sandbox is unverified here. ALWAYS back the chosen posture with the post-run `git diff --name-only HEAD` of every changed path against the task's `allowlist` — the same reliable enforcement every CLI worker gets. Out-of-allowlist edit = halt + surface; NEVER auto-revert silently.

### Model + variants — the four ModelStudio US backends

Qwen runs against **four configured backends** (`~/.qwen/settings.json` `modelProviders.openai`, all on the
ModelStudio US endpoint `https://dashscope-us.aliyuncs.com/compatible-mode/v1` under `DASHSCOPE_API_KEY`).
Per-dispatch selection adds ONE flag to the canonical invocation: `--auth-type openai -m <id>` (omit `-m`
to fall back to the configured `model.name` = `qwen3.6-plus`). Each is a routable `(qwen-code-cli, variant)`
modeled ONLY where a routing-relevant field differs (manifest field-count discipline). All four reply-probed
exit-0 on ModelStudio US 2026-06-10 (`init.model` echoes the id); `deepseek-v4-flash` passed a full
bounded-code done-gate the same day (evidence:
`1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/2026-06-10-qwen-multi-model.md`).

| Variant | `-m` id | reasoning · ctx · max_out · cost | Pick it when | Evidence |
|---------|---------|----------------------------------|--------------|----------|
| `default` | _(none)_ → `qwen3.6-plus` | mid · 1M · 65,536 · low | The native home backend; no `-m` needed; default bounded code/agentic | validated (2026-06-09 pilot) |
| `deepseek-flash` | `deepseek-v4-flash` | mid · 1M · 384K · low | Cheapest bulk code; single-turn output may exceed ~64K (6× the default cap) | **validated** (bounded-code done-gate 2026-06-10) |
| `deepseek-pro` | `deepseek-v4-pro` | top · 1M · 384K · mid | Deeper reasoning within the code fleet, mid cost sanctioned (reasoning_tier `top` is spec-derived → `doubt_policy: halt`) | served; bounded-code unexercised |
| `glm` | `glm-5.1` | mid · 204,800 · 131,072 · mid | Fleet diversity (non-DeepSeek, non-Qwen agentic); task fits ~200K context | served; bounded-code unexercised |

`cost_class` values are reference-provider-derived; ModelStudio US per-backend billing is unconfirmed
(research Q2 — owner-console-only) and may re-rank `glm` vs `deepseek-pro`. A `sandbox` variant (`--sandbox`)
remains possible if a container backend is confirmed on the host — not shipped until verified.

**Per-backend invocation** (the one-flag delta — everything else in the canonical shape carries over):

```powershell
qwen "<task>" --auth-type openai -m deepseek-v4-flash --output-format json --approval-mode yolo --max-wall-time 10m
qwen "<task>" --auth-type openai -m deepseek-v4-pro   --output-format json --approval-mode yolo --max-wall-time 10m
qwen "<task>" --auth-type openai -m glm-5.1           --output-format json --approval-mode yolo --max-wall-time 10m
qwen "<task>"                                          --output-format json --approval-mode yolo --max-wall-time 10m   # default → qwen3.6-plus
```

**Disambiguation — qwen-via-DeepSeek (this package) vs the DeepSeek API worker (`deepseek-api`):** both can
run DeepSeek models, but they are DIFFERENT ROLES — never interchangeable.

| Use… | …when |
|------|-------|
| **`(qwen-code-cli, deepseek-flash\|deepseek-pro)`** — the CLI **code/agentic** role | The task is **bounded CODE or agentic work**: it must write/edit files, run shells/tests, use the `agent`/MCP tools, isolate via `--worktree`, and be confined by a post-run allowlist diff. The qwen CLI carries DeepSeek as a tool-using code executor. |
| **`deepseek-api`** — the **text-synthesis** role | The task is **stateless TEXT generation** (summarize, classify, rewrite, JSON-mode synthesis) with `code_competence: none` and no filesystem/tool loop — the cheapest text leaf. NEVER for code execution. |

Rule of thumb: **does the task touch the filesystem or run tools? → qwen-via-DeepSeek. Pure text in → text out? → `deepseek-api`.**

### Context window + output sizing

- **Context window is model- and provider-dependent.** The local-setup docs example sets `131072` (128K); the Qwen3.5 model card cites `262144` (256K native). Treat the effective window as provider/config-dependent — confirm the configured value for the actual provider before sizing task context; do NOT assume. As with kimi, the budget is for INLINED task facts, not for the worker to read broad PRDs at runtime.
- `max_output` (single-turn output cap) is provider-dependent and NOT surfaced as a CLI flag — DATA NOT FOUND for a fixed value. Size large-output tasks conservatively and split if a single turn would exceed the provider's completion limit.

### Exit handling — drive retry/recovery logic

| Code | Meaning | Conductor action |
|------|---------|------------------|
| `0` | Success | Proceed to the return gate (reconcile against disk, then verification card). *(docs-sourced; AUTH-PENDING — not yet exercised.)* |
| `1` | Generic failure (e.g. **no auth type selected** — verified locally; also config/usage errors) | Halt and surface — do NOT retry blindly. For the auth case, the fix is USER-EXECUTED (§auth). |
| `53` | `--max-session-turns` overrun | Turn-budget hit. Re-dispatch with a higher cap or split the task; NOT a transient retry. |
| `55` | Budget exceeded — `--max-wall-time` or `--max-tool-calls` overrun (`FatalBudgetExceededError`) | Wall/tool budget hit. Re-dispatch with a higher cap or a smaller task; NOT a transient retry. |
| `130` | SIGINT (Ctrl+C) | Interrupted. |

```powershell
$env:QWEN_CODE_UNATTENDED_RETRY = "1"
qwen "<task>" --output-format json --approval-mode yolo --max-wall-time 10m --max-session-turns 30
$code = $LASTEXITCODE
if ($code -eq 55 -or $code -eq 53) { <budget hit — re-scope or raise caps; not transient> }
elseif ($code -ne 0) { <reconcile disk; halt + surface — do NOT blind-retry> }
```

**No dedicated retryable-throttle exit code** (unlike kimi's 75). Transient HTTP 429/529 are handled IN-PROCESS by `QWEN_CODE_UNATTENDED_RETRY=1`: set it and the CLI retries indefinitely with exponential backoff (capped at 5 min), printing a stderr heartbeat every 30s. For unattended orchestration prefer that env switch over an external exit-code retry loop, and bound the run with `--max-wall-time` so a stuck retry exits 55 rather than hanging.

### Disk-state recovery (work landed, return/commit lost) — AUTH-PENDING, judgment-only

Mirrors the kimi exit-75 recovery in shape; qwen's exact drop behavior is unvalidated (auth-gated), so treat this as a candidate protocol, valid only under a high-reasoning conductor (a lower-reasoning conductor halts + surfaces). Trigger only when ALL hold: qwen exited non-zero with NO structured return (no `status`, no commit hash) on stdout / in the `--json-file`; `git -C "<repo>" status --porcelain` shows uncommitted changes inside the allowlist; `git -C "<repo>" log -1 --pretty=%s` does NOT show the expected `[<task-id>]` prefix. Steps: (1) verify on-disk state against the task's Implementation Requirements; (2) run the declared `test_command` / smoke checks; (3) verify allowlist compliance (`git diff --name-only HEAD` — every changed path in the allowlist, else halt + surface); (4) verify forbidden-ops compliance; (5) commit manually with the mandatory `(orchestrator-recovered)` subject suffix:

```bash
git -C "<repo>" add <files-in-allowlist>
git -C "<repo>" commit -m "[<task-id>] <description> (orchestrator-recovered)" \
  -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

(6) log to the run-log: exit code, files verified + smoke result, the recovery commit hash, why not retrying, and that the reviewer MUST FULLY re-validate. The recovery commit is reversible (`git revert <hash>`). **Hung dispatch (qwen never exits):** orchestrator kills it, evaluates disk state, then recover-commits (same steps) OR re-dispatches fresh.

### Resume mechanics

| Mechanism | Command | Use |
|-----------|---------|-----|
| Resume a specific session | `qwen --resume <id> "<follow-up>" --output-format json --approval-mode yolo` | After a `DOUBT_ESCALATED` / `NEEDS_CONTEXT` halt: supply the resolution into the SAME session by id. |
| Resume the most recent for the project | `qwen --continue "<follow-up>" --output-format json --approval-mode yolo` | Pick up the most recent session for the current project without tracking an id. |
| Set a session id for this run | `qwen --session-id <id> "<task>" …` | Pin a known id at dispatch so resume targets it deterministically. |
| Fork a resumed session | `qwen --resume <id> --fork-session "<follow-up>" …` | Branch a new session from the resumed one (use WITH `--resume`/`--continue`). |

All resume mechanics require chat recording ON (default unless `--chat-recording false`). Avoid `--resume` WITHOUT an id in headless mode — it opens an interactive picker. Prefer pinning `--session-id` at dispatch so resume round-trips deterministically; fall back to a fresh re-dispatch (the prompt file is the reuse surface) if resume does not engage.

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| Headless stalls waiting for approval | NEVER leave `--approval-mode default` for a non-interactive dispatch; set `auto`/`auto-edit`/`yolo`. |
| Headless `--approval-mode auto` silently does no write work (denies every write/edit/shell call) | Live-proven on qwen 0.17.1 (p2-3, 2026-06-10): headless `auto` does NOT grade tool calls — it DENIES them all ("…use the -y flag"), so an `auto`-mode headless dispatch is read-only in practice. Headless WRITE work requires `yolo`/`-y` (or an explicit `--allowed-tools` grant) backed by the standard external enforcement (post-run `git diff --name-only HEAD` vs the task allowlist; out-of-allowlist = halt + surface). Reserve `auto` for read-only/analysis leaves. |
| `yolo` auto-approves ALL tools at host privilege, no sandbox | Use the tightest graded mode the task allows; back ANY mode with the post-run `git diff` vs allowlist; `QWEN_CODE_SUPPRESS_YOLO_WARNING=1` only silences the notice, not the exposure. |
| Unauthenticated run exits 1 (`No auth type is selected`) | Auth is USER-EXECUTED-ONLY (§auth) — confirm before dispatch; halt + ask the owner; free OAuth tier discontinued 2026-04-15. |
| No retryable-throttle exit code | Set `QWEN_CODE_UNATTENDED_RETRY=1` for in-process 429/529 backoff; bound with `--max-wall-time` (→ exit 55). |
| Budget overrun → exit 53/55 | Turn/wall/tool budget hit — re-scope or raise caps; NOT a transient retry. |
| `--continue`/`--resume` silently do nothing | They require chat recording ON — do NOT pass `--chat-recording false` on a resumable dispatch. |
| `--sandbox` unavailable | Needs Docker/Podman; unverified on this Windows host — confirm the backend before relying on container isolation. |
| `cd` does not persist between shell calls | Each shell command is an independent subprocess — pass the workspace via CWD + `--add-dir`; never rely on `cd` chaining in the prompt. |
| Final-message drop on a dropped turn (AUTH-PENDING) | Prefer `--json-file <path>` / `--json-schema` for a durable structured return; reconcile from disk on any garbled/absent return. |

### Swarm / subagents

- Qwen Code has an **`agent` tool** (the `--max-tool-calls` docs state "`agent` tool dispatch = 1; inner calls exempt") — the worker CAN dispatch its own sub-tasks/subagents.
- Depth: treat as **one-level** (the worker spawns sub-tasks; those do not recurse) pending live confirmation — matches the kimi subagent model and the D7 depth cap ≤2. **AUTH-PENDING** (not pilot-verified) → manifest `swarm_support` carries `probe-pending` on the depth fact.
- Safe default posture: **disabled** for bounded worker dispatches (enable only for independent slices with disjoint allowlists), consistent with the kimi/codex swarm policy.
- ACP mode (`--acp`) and `serve` (`--http-bridge`) are alternative programmatic surfaces, NOT the bounded-worker pattern — out of scope for the standard dispatch.

### Authentication — the USER-EXECUTED-ONLY pre-flight

The CLI is installed and verified; only auth remains, and it CANNOT be done by an agent (OAuth needs a browser the orchestrator cannot drive; API-key auth needs the user to obtain + place a key from a PAID provider — the free OAuth tier was discontinued 2026-04-15). An unauthenticated headless run exits 1. The user runs ONE of:

**Option A — OpenAI-compatible API key (e.g. DashScope; recommended for unattended use):**

```powershell
# In an interactive shell the agent must NOT run on the user's behalf:
$env:OPENAI_API_KEY  = "<your-key>"
$env:OPENAI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"   # or another OpenAI-compatible provider
$env:OPENAI_MODEL    = "qwen3-coder-plus"
qwen "Reply with exactly: QWEN-PROBE-OK" --auth-type openai --output-format json --approval-mode yolo --max-wall-time 60s
```

`settings.json` auth shape (`~/.qwen/settings.json`): `{ "security": { "auth": { "selectedType": "openai" } } }`. Auth types: `--auth-type openai|anthropic|qwen-oauth|gemini|vertex-ai` (env vars: `OPENAI_API_KEY`/`OPENAI_BASE_URL`/`OPENAI_MODEL`; `ANTHROPIC_API_KEY`/…; `GEMINI_API_KEY`/…). The `qwen auth` subcommand is REMOVED — do NOT script it; use `/auth` (interactive), `--auth-type` + env/keys, or `settings.json`.

**Option B — interactive Qwen OAuth (note: free tier discontinued; needs a paid plan to be useful):**

```powershell
qwen          # then use /auth, pick the provider, complete the browser login
```

After auth is configured, a clean exit 0 from the §canonical invocation with the expected output graduates the JSON-output, exit-0, and swarm facets from `probe-pending` toward `validated` — this is the p5-2 smoke-probe moment.

### The qwen task contract (plugs into the shared authoring core)

A qwen-executable task file extends the generic task-file contract (`{rbtv_path}/orchestration/workflows/_shared/authoring/`) with qwen-specific frontmatter and body sections. The orchestrator validates a `executor: qwen` task against this contract BEFORE dispatch; a missing required field = halt + report the malformed task — NEVER infer or mutate a field into shape (task shaping belongs to planning).

**Required frontmatter:**

```yaml
execution_kind: code            # or research/analysis for a read-only leaf
executor: qwen
allowed_workdir: <absolute-or-project-root-relative repo path>   # the CWD root (no --work-dir flag; CWD is the root)
allowlist:
  - <file-or-folder-glob>
approval_mode: auto | auto-edit | yolo   # the tightest the task needs; never `default` (stalls headless)
commit_policy: local-only | none         # none = conductor commits via rbtv-commit
test_command: <command-or-NONE>
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - external production API calls
  - --yolo without sanctioned host-privilege auto-approval
doubt_policy: halt
reviewer: claude-opus           # reviewer floor for qwen-produced code is Opus (external-CLI code) — non-overridable
swarm_policy: disabled | allowed
max_qwen_subagents: <N-or-0>
```

**Required body sections:** Goal (one bounded deliverable) · Context Snapshot (all task-specific context inlined — never make qwen infer from broad PRDs) · Allowed Paths (the allowlist in human-readable form) · Forbidden Paths · Approval Mode (the `--approval-mode` value; the mandatory non-`default` posture) · Implementation Requirements (exact behavior — interfaces, data shapes, error semantics, every edge case enumerated) · Validation (the exact commands qwen runs before returning) · Commit Rule (local-only after validation, or none) · Swarm Rule (if `allowed`: subagent posture, count, disjoint partition) · Return Format (the five-field return schema; land a durable copy via `--json-file`/`--json-schema`).

**Review gates** every qwen coding task passes (verification card owns the gate): qwen self-report → orchestrator diff-vs-allowlist check → declared validation passing (or explicit blocker) → Claude/Opus spec-compliance review → Claude/Opus code-quality review → no push until owner/final-workflow publishes. Any gate fails → halt or route a fix task; never proceed on "close enough". Qwen ships `evidence_status: probe-pending` — until the p5-2 smoke probe validates a real authenticated turn, treat every AUTH-PENDING leg as unverified and reconcile hard against disk.

### Recipes

```powershell
# Bounded code edit, JSON result, in-process throttle retry (Shape A):
# headless WRITE work REQUIRES yolo/-y — auto DENIES every write/edit/shell call (see Approval grammar)
$env:QWEN_CODE_UNATTENDED_RETRY = "1"
qwen "<inlined task file content>" --output-format json --approval-mode yolo `
  --max-session-turns 30 --max-wall-time 10m --json-file ".qwen-runs/t1.json"
```
```bash
# Large prompt via stdin (Shape B) — write work, so yolo (auto is read-only headless):
cat prompt.md | qwen "<instruction>" --output-format json --approval-mode yolo --max-wall-time 10m
```
```powershell
# Read-only analysis/research leaf (strip write/shell tools), live JSONL events:
qwen "<analysis task>" --output-format stream-json --approval-mode plan --exclude-tools "write_file,run_shell_command"
```
```powershell
# Parallel-isolated dispatch in a native git worktree:
qwen "<task>" --worktree --output-format json --approval-mode yolo --max-wall-time 10m
```
```powershell
# Strictly-shaped structured return (headless only):
qwen "<task>" --json-schema "@return-schema.json" --approval-mode auto --max-wall-time 10m
```
```powershell
# Resume a halted session with the resolution (yolo if the resolution writes; auto only for a read-only follow-up):
qwen --resume <session-id> "<resolution to the open question>" --output-format json --approval-mode yolo
```
