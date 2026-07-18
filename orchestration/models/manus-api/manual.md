<!-- AUTO-GENERATED — DO NOT EDIT. Rendered by orchestration/models/render-manuals.py from orchestration/skills/orchestrating/cards/dispatch-wrapper.md + orchestration/models/manus-api/delta.md. -->

> [!danger] GENERATED FILE — DO NOT EDIT
> This dispatch manual is composed by `orchestration/models/render-manuals.py` from:
> - the generic dispatch contract `orchestration/skills/orchestrating/cards/dispatch-wrapper.md`, and
> - the `manus-api` package delta `orchestration/models/manus-api/delta.md`.
>
> Hand-edits are overwritten on the next render and are forbidden. To change
> packaging/addendum/return behavior, edit the wrapper template; to change
> manus-api-specific behavior, edit the delta. Then re-render:
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
| **In-session CLI spawns BEGIN with the worker binary (D17)** | A CLI dispatch issued from inside a Claude session is permitted by PREFIX allowlist rules (`Bash(<bin>:*)` / `PowerShell(<bin>:*)`, installer-managed from the package manifest's `permission_rules`) — they match ONLY a command line that BEGINS with the worker binary. A leading `cd …`, an inline env assignment, or a `cat …\|`/`Get-Content …\|` stdin pipe breaks the match and the spawn falls to the permission classifier, which denies in-session yolo spawns. So: run from the conductor's CWD (pass the work-target via the model's add-dir flag, never a leading `cd`), set env vars in a SEPARATE prior statement, and hand a large brief to the worker as a SHORT positional/file-pointer prompt naming the prompt file — never a stdin pipe. Pipe and env-prefixed forms remain functionally valid ONLY for owner-typed `!` dispatches (those bypass the session classifier). Each model's delta carries its binary-first shape. |
| **Absolute paths in every launch command** | Every path in a CLI/server launch command — the prompt-file pointer, any stdout/stderr redirect, the work-target/add-dir argument — MUST be absolute. A relative path resolves against the spawning shell's CWD, which drifts after any prior `cd`: a relative launch path once resolved against the wrong directory and no worker ran while a redirect error masqueraded as the worker's exit code. This is the workspace `rbtv-sub-agents` rule's write-path hygiene (Pre-Dispatch Gate, workspace-root-absolute paths) applied at launch time — follow it, do not restate it. |
| **Launch-root = orchestrator root; work-target via add-dir (G1)** | ALWAYS launch a CLI worker with its guidance-root = the **orchestrator root** (the workspace the conductor runs from, where the full rules/skills mirror lives) and pass the actual **work-target** separately via the model's add-dir flag. The per-model launch-root flag comes from the model's delta (claude-cli/codex key guidance to CWD/`-C`; kimi to `--work-dir`; opencode to `--dir` — the DOCUMENTED exception: its launch root IS the work-target worktree, no add-dir split exists). NEVER root the worker at the work-target when the work-target is a nested repo: the mirror skips nested git repos BY DESIGN, so a worker rooted there loads ZERO behavior-rules and operates blind (the a3e217d incident — a bare kimi self-commit swept 5 foreign files because its guidance-root was the unmirrored nested repo). State the split explicitly to the worker in the dispatch: "your rules load from your launch root; create/modify files ONLY inside `<work-target>` per the allowlist". Two caveats the conductor owns: (a) the post-run confinement diff MUST run in the **work-target's git** — `git -C <work-target> diff --name-only HEAD` — never in the launch-root's git (a nested-repo work-target has its own git; a launch-root diff passes vacuously); (b) the work-target's OWN local `CLAUDE.md`/`AGENTS.md` conventions are NOT auto-loaded from an add-dir — inline the load-bearing ones into the dispatch or mark the file `[FULL READ]`. |
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
| **Evidence integrity & byte-exact paths** | Before returning, VERIFY every evidence capture cited in `validation` is NON-EMPTY; a cited capture that is empty or absent is reported as such, NEVER quoted as if it held content (a husk citation is the fabricated-evidence class — a CLI worker cited two empty captures while quoting their supposed content). Any file path consumed OR produced from an existing filename is COPIED BYTE-EXACT from a machine-written source (a list file, a directory listing), NEVER retyped — curly quotes and non-ASCII characters survive a copy but not a transcription. A read that fails is reported as READ-FAIL with the EXACT path used, NEVER classified as a missing/absent file (a transcription typo read-fails on a file that exists, and "file does not exist" then silently drops real work). |
| **Content/order/identity proof** | Any assertion or grading of a content, order, or identity criterion MUST prove that property DIRECTLY; a count (rows, slides, length) is necessary but NEVER sufficient and MUST NOT stand alone as the proof. A count-preserving silent slide-drop passed every count check while dropping real data; the count-only weakening recurred 3× in one run across two models AND the cold-verifier role. The verification card §2b standing pre-flag references this dispatch-side obligation; the `rbtv-done-gate` protocol carries the criterion-exercise twin of the same rule. |
| **Computed claims — authored briefs & checkpoint verdicts** | Every factual claim you WRITE for another agent to act on — a fact stated in a task brief you author, a checkpoint or "done" verdict, a resume/status claim — is COMPUTED from a command AT THE MOMENT OF WRITING, never recalled from memory or derived by reasoning. `rbtv-deterministic-first`'s Compute gate binds these surfaces; follow it, do not restate it. A brief's factual claims are consumed by the receiving agent as ground truth, so an unverified one is not a wrong ANSWER but a wrong INSTRUCTION, executed (2026-07-15: five brief-borne assertions in one run were each wrong and each computable in one command; every one was caught only because the receiving worker recomputed instead of complying — one catch stopped a "fix" that would otherwise have silently REMOVED an existing safeguard while being described as strengthening it). This binds you whenever you author or grade, not only when you answer: under the depth cap a worker may itself drive a sub-conductor and author briefs. |
| **Commit discipline** | Commits go through `rbtv-commit` (routing pins this to a commit-capable worker — CLI workers are kept OFF commits by default). Local commits only; NEVER push. A CLI worker is authorized to self-commit ONLY when its task file / model delta explicitly grants it (the default is no self-commit; the kimi package's delta is where a code-executing worker's local-commit authorization is declared). When the worker IS authorized: validation passes first, the commit message follows the run's mandated convention, and the returned commit hash must match what is actually in `git log` (the conductor checks the message string and the hash, not just the file list). An authorized self-commit MUST be **pathspec-scoped to the allowlist**: stage with `git add <allowlist-paths>` and commit with `git commit -- <allowlist-paths>`; `git add -A`, `git add .`, and a bare `git commit -a` are FORBIDDEN regardless of authorization — an unscoped self-commit sweeps foreign uncommitted files into the commit (the a3e217d defect class: 5 foreign files swept by one bare kimi self-commit). The dispatch INLINES the exact pathspec-scoped commit command when self-commit is granted. |
| **Forbidden operations** | Honor the task's forbidden-ops list (no pushes, no writes outside the allowed work-dir, no destructive git resets, no external production API calls unless the task explicitly allows a mocked/local one). The git prohibition is MUTATING-ONLY: read-only git (`status`, `log`, `diff`, `show`) is permitted to every worker and briefs MUST NOT widen it to a blanket "never run git" — reconciling one's own claims against disk state is an obligation, not a violation (narrowed 2026-07-18, sysdef-archive closeout: repeated harmless read-only-git "drift" against blanket-banned briefs). |
| **Rule-loading (mirror-equipped workspace)** | Before ANY other action — before reading any task-referenced file, writing, running a tool, or responding — inspect your **launch root** (the directory your guidance keys to: your CWD/`-C` root, or kimi's `--work-dir`; under orchestration this is the orchestrator root, NOT the work-target) for a `.agents/behavior-rules/` directory. If it exists (a mirror-equipped workspace), you MUST FIRST read your own guidance file at that root (`AGENTS.md` for a Codex/Kimi/OpenCode worker) AND every file under `.agents/behavior-rules/`, and treat their entire contents as binding, non-negotiable rules governing this whole session — exactly as if they were part of this dispatch. Reading them is mandatory even when this task body never mentions rules; the absence of a rule-read instruction in the task is NOT permission to skip them. If the launch root has no `.agents/behavior-rules/` directory, this obligation is a silent no-op — proceed normally. |

**Conductor obligation — instruct the rule-read for harnesses that do NOT auto-read (CLI workers).** A CLI worker whose governance depends on the behavior-rule fan-out only obeys the Rule-loading obligation above if its harness actually reads its rules directory. Harnesses differ: **codex auto-reads** its rules directory (no explicit instruction needed); **opencode auto-reads `AGENTS.md`** at its `--dir` root when present (worktree dispatches must mirror it in first — opencode delta pre-flight) but its `.agents/behavior-rules/` read is UNPILOTED — instruct it explicitly; **kimi does NOT** auto-read — it needs an enumerated Step-0 naming the read (kimi delta `model-binding-delta`). So when composing a dispatch for a non-auto-reading CLI worker with a mirror-equipped launch root, the conductor MUST add an EXPLICIT rule-read instruction to the dispatch prompt (the per-model proven form, from that model's delta); do NOT rely on the generic obligation alone. That instruction MUST tell the worker to read the rule files ONE FILE PER CALL (or in small batches) — NEVER a single recursive bulk read: a bulk `Get-Content -Recurse`-style read of a multi-file rule library truncates silently mid-corpus, so an alphabetically-later rule's body never reaches the model and the obligation it carries goes unread despite the read "firing" (the 2026-06-09 kimi `<counter>` incident). (The mirror-driver `guidance.py` half of this guarantee is deferred to the mirror-install follow-up — not authored here.)

The addendum is GENERIC. A model package's delta MAY add model-specific obligations on top (e.g., a worker that must be told not to write stray files in the repo root, or a swarm-policy constraint) — it plugs in at the insertion point below and NEVER restates the generic obligations.

**Manus-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What the manus worker is bound to |
|------------|------------------------------------|
| **Agentic-web worker — no local filesystem access** | The runner submits a task to the Manus API; the agent reads NOTHING from our workspace. ALL context the task needs MUST be inlined into the prompt file at dispatch time — it is inlined into the Manus task `description`. The runner writes ONLY into `--output-folder`. |
| **Server-side autonomous loop — not ours to constrain** | Manus runs its own browser/tool loop server-side. We do NOT pass an agent file, an MCP server, or a tool allowlist that constrains it; its autonomy is invisible to our topology and depth cap. Confinement is the runner's job (scoping the written OUTPUT), not a work-dir the conductor passes. |
| **Always raw-dump — no JSON envelope, no code cold-verify** | `structured_output` is False, so every dispatch returns `DONE_WITH_NOTES` + `raw-output.md` (the agent narration) + any fetched file artifacts + optional `structured-output.json` (if `structured_output_schema` was passed) + a concern naming the raw-dump. There is no structured `{files:[…]}` envelope. The return is **non-development** — verified by a Claude reviewer reading the content for quality, NOT by a code cold-verify (there is no code artifact). |
| **Per-task billing + minutes-scale latency** | Manus is billed PER TASK, not per token — forecast budget by task count. A real autonomous run can take minutes; a `WALL_MS` of seconds-to-minutes is normal and is NOT a hang. The dispatch never exceeds the configured timeout (default 300s / 5 minutes). |
| **No session resumption** | The poll loop is internal to a single dispatch. A `error`/`timeout`/`DOUBT_ESCALATED` halt triggers a fresh re-dispatch (resolution inlined into the prompt); there is no `--session` / `--continue` path. The conductor does NOT attempt to resume. |
| **Key-resolution availability** | The runner checks `MANUS_API_KEY` in the OS environment, then the `env_file` path in `rbtv.json`. If absent in both, the package is unavailable for this dispatch; the conductor logs it and degrades — never halts the run. The key is sent as `x-manus-api-key` header and never echoed. |
| **Validated status** | The single variant is `evidence_status: validated` — piloted live 2026-06-09 against Manus API v2 (`https://api.manus.ai/v2`). `context_window`/`max_output` remain unverified placeholders (Manus publishes no token limits) — do not size large inlined contexts on them. |
| **File artifacts fetched (shipped 2026-06-10, D-exec-14)** | The client parses `assistant_message.attachments[]` from `task.listMessages` (no `verbose=true` needed) and downloads each attachment into `--output-folder`. Single-GET download (revised 2026-06-11, D3/D6 superseded): every attachment is a CloudFront presigned URL (`private-us-east-1.manuscdn.com`) whose query signature carries the authorization — the client does ONE GET (the `x-manus-api-key` header is retained but ignored by the CDN) and fails loud on any non-200. The prior with-key/no-key fallback + login-page heuristic was removed after a 40-call live probe across 10 artifact types found 100% presigned delivery and no login-masking case (`2-areas/rbtv/orchestration/manus-artifact-fetch/auth-probe/summary.md`). A per-file download failure (e.g. an expired signature → 403) is NON-FATAL: recorded in `raw_response["artifact_errors"]` and surfaced as a runner `concerns` line. Live-validated 2026-06-10 (paid CSV deliverable) + 2026-06-11 (40-call auth probe). |
| **`structured_output_schema` supported via `--extra-params` (D7/D8)** | Pass `--extra-params '{"structured_output_schema": {...}}'`; it goes top-level on `task.create`. Result lands in `--output-folder` as `structured-output.json` carrying the full wrapper `{success, value, error}` (consumers read `.value`). **STRICT-mode JSON Schema is REQUIRED** (see `open.manus.ai/docs/v2/structured-output`): every object must carry `additionalProperties: false` AND `required` listing ALL properties; root must be `type: object`; max nesting depth 5. UNSUPPORTED keywords: `pattern`, `format`, `minLength`/`maxLength`, `minimum`/`maximum`/`exclusiveMinimum`/`exclusiveMaximum`/`multipleOf`, `minItems`/`maxItems`/`uniqueItems`, `allOf`/`oneOf`/`not`, `if`/`then`/`else`. A non-strict schema → HTTP 400 `invalid_argument` at `task.create`, BEFORE any task is created (no spend) — live-confirmed 2026-06-10. Note: this `structured_output_schema` top-level field is DISTINCT from the runner’s `structured_output: False` flag (the chat-envelope mechanism); do not conflate them. |
| **System-role messages excluded from task description (D5)** | When assembling the Manus `task.create` `description`, the runner excludes `role == "system"` messages. The `{files:[…]}` chat-envelope system instruction never leaks into the Manus task description. |
| **Capture-bound dispatch — demand the deliverable in the reply MESSAGE TEXT** | When the dispatch's deliverable IS the captured content (a research result, a synthesized answer, a data extract — not a side-effect file), the prompt MUST explicitly demand that the complete deliverable appear in the agent's reply message text (`assistant_message.content` → `raw-output.md`), NOT only as a fetched attachment. An attachment-only return failed live: the agent answered by attaching a file and leaving the message body empty, so the raw-dump carried no deliverable. State the requirement in the Manus task `description` ("return the full {deliverable} in your reply text, not only as an attachment"); attachments remain welcome as extras, never as the sole carrier. |
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

**Manus return surface — always raw-dump (the only mode Manus has):**

The `_api/run.py` runner submits the task, polls to completion, and writes results into `--output-folder`. Because the client declares `structured_output: False`, the runner uses the **raw-dump path**, not the JSON-envelope path:

1. **`return.json`** in `--output-folder` — the runner's five-field structured return: `status`, `landed`, `validation`, `concerns`, `open_questions`. For Manus, `status` is `DONE_WITH_NOTES` on success (raw-dump is the only path), `landed` lists every written file (narration + any artifacts), `validation` records the task duration (`WALL_MS`), the raw-dump-fallback flag (always set for Manus), and `artifact_count`; `concerns` names the raw-dump. This is the machine-parseable contract the conductor reads after every dispatch.
2. **`raw-output.md`** in `--output-folder` — the agent's narration (`assistant_message.content`), written as the primary output file. This is NOT a parsed `{files:[…]}` envelope — it is the whole agent output as one file.
3. **Fetched file artifacts** (if any) in `--output-folder` — each attachment from `assistant_message.attachments[]` downloaded and written with a sanitized, de-duplicated filename so it never clobbers `return.json`, `raw-output.md`, or each other. Every written artifact is appended to `landed`. A per-file failure is non-fatal: recorded in `raw_response["artifact_errors"]` and surfaced as a `concerns` line. (Each attachment is a single-GET presigned-URL download — see the artifacts row above; there is no auth-mode variation to record.)
4. **`structured-output.json`** in `--output-folder` (only when `structured_output_schema` was passed) — the full `structured_output_result` wrapper `{success, value, error}`. Consumers read `.value` for the schema-shaped answer.

The conductor treats `return.json` as the primary return signal and reconciles it against the on-disk output file — on any disagreement, disk wins. A missing `return.json` (runner crashed) means the dispatch status is `BLOCKED`; no recovery path exists (re-dispatch fresh).

**Non-development verification path:** a Manus return carries no code artifact to cold-verify. The independent verifier is a Claude **reviewer** that reads the raw-dumped content for quality against the task contract — there is no build/test/lint cold-verify step, because Manus produced agent output, not code.
<!-- The model package delta names this worker's exact return surface (e.g., the CLI's final-message flag, the evidence-file convention) here. The fields above never change. -->

---

## Invocation — the exact command shape

The Manus API dispatch manual — the exact runner invocation, the single profile, exit/halt handling, and the manus task contract. Sourced from `routing-system.md` Part II — Manus + Manus API docs + the built client (`_api/clients/manus.py`).

This manual is validated against Manus API v2 (piloted live 2026-06-09). Pricing: ~$0.01/credit, ~150 credits/task ≈ ~$1.50/task. `context_window`/`max_output` in the manifest are unverified placeholders — Manus publishes no token limits; do not size large inlined contexts on them. Reference: `https://api.manus.ai/docs`.

### Pre-flight (before any dispatch)

| Check | How | Gate |
|-------|-----|------|
| Runner present | `python orchestration/models/_api/run.py --help` | Absent → the package cannot dispatch; halt and surface |
| API key resolves | `$env:MANUS_API_KEY` present, or `env_file` in `rbtv.json` carries the key | Absent → package unavailable; conductor degrades, does not halt the run |
| Task is worth an agent run | Confirm the task genuinely needs autonomy/browser (not a bounded code or chat task) | A non-autonomous task wastes a per-task fee — route it to a chat/code worker instead |

### Invocation shape

The runner is always non-interactive. Manus has a single profile — `--model manus-autonomous` selects it (there is no alternate API model id to swap):

```powershell
python orchestration/models/_api/run.py `
  --provider manus `
  --model manus-autonomous `
  --prompt-file <path/to/prompt.md> `
  --output-folder <path/to/output-dir/>
```

| Flag | Required | Notes |
|------|----------|-------|
| `--provider manus` | yes | Selects the Manus client in `_api/clients/` (`ProviderName.MANUS`) |
| `--model manus-autonomous` | yes | The single RBTV routing label; Manus has no selectable API model id — this names the profile |
| `--prompt-file <f>` | yes | Path to the prompt file written by the conductor; its content is inlined into the Manus task `description` (the agent reads nothing from the local filesystem) |
| `--output-folder <d>` | yes | Directory the runner writes `return.json` and the raw-dumped output file into; created by the runner if absent |

### The single profile

Manus declares ONE variant — `manus-autonomous` — because it has a single operating profile (autonomous server-side agent run). There is no second variant: no reasoning-tier, cost-class, or capability field differs across a "mode", so a second entry would be schema bloat (manifest-schema.md §2 variant field-count discipline).

| RBTV variant | Routing profile | Manus selector |
|--------------|-----------------|----------------|
| `manus-autonomous` | `reasoning: 1`, `coding: 1`, `cost: 1` (per-task), `web_access: true`, `routable_for: [web-research]` — the autonomous-web leaf; never the code path | `--model manus-autonomous` (no alternate API id) |

### Exit handling

The runner exits 0 on success and non-zero on failure. There is no exit-75 retry convention.

| Runner exit | Meaning | Conductor action |
|-------------|---------|------------------|
| `0` | Task completed | Read `return.json` (`status: DONE_WITH_NOTES`, raw-dump) from `--output-folder`; reconcile against the raw-dumped output file; hand to a Claude reviewer for content-quality review |
| Non-zero | Task status `error`, poll timeout, task-creation failure after retries, or key unresolved | Halt; read runner stderr for the error class (auth/error-task/timeout/network); surface; re-dispatch fresh after resolution |

Task-creation HTTP retries (429, 5xx, 3 attempts with backoff) are the client's responsibility — the conductor does not implement its own retry loop. The poll loop (every ~2s until `stopped`/`error`/timeout) is internal to the single dispatch.

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| Task `status == error` | The runner returns `BLOCKED` + the Manus error in `open_questions`; no recovery path — re-dispatch fresh |
| Poll exceeds timeout (task never completes) | The runner returns `BLOCKED` + a timeout note; it never hangs past the configured timeout (default 300s) |
| Task-creation `POST` fails after 3 retries | `BLOCKED` + the HTTP error |
| `MANUS_API_KEY` unresolved | Pre-flight key-resolution check; the runner exits non-zero with a clear stderr message and never echoes the key; conductor degrades, does not halt the run |
| Treating a long run as a hang | Minutes-scale latency is normal for a real autonomous task — only the configured timeout bounds it; do NOT kill a still-polling dispatch as "stuck" |
| Per-task cost surprise | Manus bills per task, not per token — confirm the task warrants an agent run before dispatch; a wasted run costs a whole task fee |
| Unverified token sizing | `context_window`/`max_output` are placeholders — do not size large inlined contexts on them; re-verify before any pilot |

### The manus task contract

A manus-executable task file extends the generic task-file contract with the following agentic-web requirements. The conductor validates before dispatch; a missing required field = halt + report.

**Required frontmatter additions:**

```yaml
execution_kind: agentic   # autonomous agent task — produces raw agent output, not code artifacts or a JSON envelope
executor: manus
variant: manus-autonomous
output_folder: <path relative to the dispatch root — runner writes the raw dump + return.json here>
doubt_policy: halt
```

**Required body sections:** Goal (one bounded autonomous task the agent can complete end-to-end) · Context Snapshot (ALL context inlined into the prompt — the agent reads nothing from the workspace) · Output Requirements (what the agent's output should contain; note it is raw-dumped as one file) · Return Format (five-field return schema in `return.json`; `status: DONE_WITH_NOTES` + raw-dump concern is the success shape).

### Recipes

```powershell
# Manus autonomous task dispatch — the only shape (always raw-dump):
python orchestration/models/_api/run.py `
  --provider manus `
  --model manus-autonomous `
  --prompt-file dispatch/prompt.md `
  --output-folder dispatch/output/
```

(No second variant and no alternate model id — Manus has a single autonomous profile.)
