<!-- AUTO-GENERATED — DO NOT EDIT. Rendered by orchestration/models/render-manuals.py from orchestration/skills/orchestrating/cards/dispatch-wrapper.md + orchestration/models/gemini/delta.md. -->

> [!danger] GENERATED FILE — DO NOT EDIT
> This dispatch manual is composed by `orchestration/models/render-manuals.py` from:
> - the generic dispatch contract `orchestration/skills/orchestrating/cards/dispatch-wrapper.md`, and
> - the `gemini` package delta `orchestration/models/gemini/delta.md`.
>
> Hand-edits are overwritten on the next render and are forbidden. To change
> packaging/addendum/return behavior, edit the wrapper template; to change
> gemini-specific behavior, edit the delta. Then re-render:
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

The addendum is GENERIC. A model package's delta MAY add model-specific obligations on top (e.g., a worker that must be told not to write stray files in the repo root, or a swarm-policy constraint) — it plugs in at the insertion point below and NEVER restates the generic obligations.

**Gemini-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What the gemini worker is bound to |
|------------|-------------------------------------|
| **API chat worker — no filesystem access** | The runner calls the Gemini API and writes ONLY into `--output-folder`. The worker never reads the workspace, runs no shell commands, and executes no tools. All context it needs MUST be inlined into the prompt file at dispatch time. |
| **Stateless — no session resumption** | Every dispatch is an independent API call. A `DOUBT_ESCALATED` or `NEEDS_CONTEXT` halt triggers a fresh re-dispatch (with the resolution inlined into the prompt); there is no `--session` / `--continue` path. The conductor does NOT attempt to resume. |
| **Model id is a dispatch-time parameter** | The routing variant (`3.5-flash` or `3.1-flash-lite`) selects the RBTV routing profile. The actual Gemini API model id is supplied via `--model <id>` at dispatch; re-verify the id against live provider docs before every pilot — the routing label is NOT an API id. |
| **Key-resolution availability** | The runner checks `GEMINI_API_KEY` in the OS environment, then the `env_file` path in `rbtv.json`. If absent in both, the package is unavailable for this dispatch; the conductor logs it and degrades to the next capable worker — never halts the run. |
| **Output-folder confinement** | The runner path-sanitizes every write against `../` traversal and absolute paths. The conductor does NOT need to scope a work-dir. Post-run, verify that the returned files land inside `--output-folder` only. |
| **Probe-pending status** | Both variants are `evidence_status: probe-pending` — not yet pilot-validated. Use only where the routing card explicitly allows unvalidated workers; flag the seam in the run-log. |
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

**Gemini return surface — standard envelope return (the only mode reachable today):**

The `_api/run.py` runner makes the API call in default JSON-envelope mode and writes its results into `--output-folder` using the standard two-layer return surface:

1. **`return.json`** in `--output-folder` — the runner's five-field structured return: `status`, `landed`, `validation`, `concerns`, `open_questions`. This is the machine-parseable contract the conductor reads after every dispatch.
2. **Model-emitted envelope files** in `--output-folder` — files the model's response directs the runner to write (raw model response, extracted content blocks). File list and format depend on the runner version and the task's output contract.

The conductor treats `return.json` as the primary return signal. Reconcile it against the envelope files on disk — on any disagreement between `return.json` and the on-disk files, disk wins. A missing `return.json` (runner crashed) means the dispatch status is `BLOCKED`; no recovery path exists for API workers (re-dispatch fresh).

**Forward context — grounded return surface (Phase 5, NOT reachable today):** once Phase 5 wires grounding into the runner (p5-3 pass-through + p5-4 web-research-leaf routing), a grounded dispatch will NOT produce a standard `return.json` envelope, because grounding is **mutually exclusive with JSON-envelope mode** in the client (`gemini.py`: setting `grounding` swaps `responseMimeType: application/json` for the `google_search` tool). When that mode ships it will return `DONE_WITH_NOTES` + a `raw-output.md` raw dump and the conductor will distinguish it by the future runner grounding parameter. **None of this is wired in the current runner** — no current dispatch can request grounding, so today every Gemini call returns the standard envelope above.
<!-- The model package delta names this worker's exact return surface (e.g., the CLI's final-message flag, the evidence-file convention) here. The fields above never change. -->

---

## Invocation — the exact command shape

The Gemini API dispatch manual — the exact runner invocation, variant selection, exit handling, and the gemini task contract. Sourced from `routing-matrix-reference.md` §4 (2026 estimates) + Google Gemini API docs.

**Re-verify model ids, context limits, and pricing against `https://ai.google.dev/gemini-api/docs` before the pilot.** This manual is `probe-pending` until a live pilot validates it.

**Grounding is DEFERRED to Phase 5 — there is no grounded dispatch in this manual.** The Gemini client supports search grounding, but the shared `run.py` runner exposes no grounding switch and passes no `extra_params`, so grounding is unreachable today. Every dispatch below runs in default JSON-envelope mode. (Phase 5 wires it: p5-3 adds the runner pass-through, p5-4 routes the web-research leaf.)

### Pre-flight (before any dispatch)

| Check | How | Gate |
|-------|-----|------|
| Runner present | `python orchestration/models/_api/run.py --help` | Absent → the package cannot dispatch; halt and surface |
| API key resolves | `$env:GEMINI_API_KEY` present, or `env_file` in `rbtv.json` carries the key | Absent → package unavailable; conductor degrades, does not halt the run |
| Model id current | Cross-check the id in the dispatch command against Google's live API docs | Stale id → update `--model <id>` before dispatch; never dispatch with an unverified id |

### Invocation shape

The runner is always non-interactive and runs in default JSON-envelope mode. The `--provider gemini` flag selects the Gemini client; the `--model` flag selects the variant.

```powershell
python orchestration/models/_api/run.py `
  --provider gemini `
  --model <gemini-api-model-id> `
  --prompt-file <path/to/prompt.md> `
  --output-folder <path/to/output-dir/>
```

| Flag | Required | Notes |
|------|----------|-------|
| `--provider gemini` | yes | Selects the Gemini client in `_api/clients/` |
| `--model <id>` | yes | Actual Gemini API model id — re-verify against provider docs; NOT the RBTV routing label |
| `--prompt-file <f>` | yes | Path to the prompt file written by the conductor (the composed header + payload) |
| `--output-folder <d>` | yes | Directory the runner writes results into; created by the runner if absent |

There is **no `--grounded` flag** on the current runner. Grounding arrives in Phase 5 (a generic `--grounded`/`--extra-params` pass-through); until then, do not attempt a grounded invocation.

### Variant selection

Route on the `(gemini, variant)` pair from the manifest; translate to a `--model <id>` argument at dispatch time.

| RBTV variant | Routing profile | Gemini API model id |
|--------------|-----------------|---------------------|
| `3.5-flash` | `cost_class: mid`, `reasoning_tier: top` — best intelligence; judgment-dense tasks | Re-verify at `https://ai.google.dev/gemini-api/docs/models` before dispatch |
| `3.1-flash-lite` | `cost_class: cheapest`, `reasoning_tier: mid` — volume processing; cost-critical tasks | Re-verify at `https://ai.google.dev/gemini-api/docs/models` before dispatch |

Both variants share identical `headless`, `tool_surface`, `confinement`, and `swarm_support` values and both carry `web_access: true`. They differ on `reasoning_tier` and `cost_class`, which is the routing-relevant distinction required by the schema's variant field-count discipline.

### Grounding (Phase 5 — not yet wired)

Search grounding is **deferred to Phase 5** and is NOT dispatchable through the current runner. The note below is forward context only — there is no grounded dispatch to route today.

| Dispatch type | Status today | Return surface (when Phase 5 ships) |
|---------------|--------------|-------------------------------------|
| Default JSON-envelope | The only reachable mode — text generation, reasoning, summarization, structured output | Standard: `return.json` + envelope files |
| Grounded (web-research leaf) | NOT wired — runner has no grounding switch; deferred to Phase 5 (p5-3 pass-through, p5-4 leaf routing) | Future: raw-dump — `DONE_WITH_NOTES` + `raw-output.md`, NO `return.json` (grounding is mutually exclusive with JSON-envelope mode in the client) |

Until Phase 5 lands, every Gemini dispatch runs in default JSON-envelope mode; do not attempt a grounded call and do not route the web-research leaf to Gemini.

### Exit handling

The runner exits 0 on success and non-zero on failure. There is no exit-75 retry convention for API workers.

| Runner exit | Meaning | Conductor action |
|-------------|---------|------------------|
| `0` | Success | Read `return.json` from `--output-folder`; reconcile against envelope files; proceed to verification |
| Non-zero | Runner or API failure | Halt; read runner stderr for the error class (auth/quota/network/bad-model-id); surface; re-dispatch fresh after resolution |

HTTP-level retries (429, 5xx) are the runner's responsibility — the conductor does not implement its own retry loop for API workers.

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| Stale model id dispatched | Always re-verify `--model <id>` against live Google docs before pilot; routing labels are NOT API ids |
| API key absent | Pre-flight key-resolution check; degrade gracefully, never halt the run |
| Web-research leaf routed to Gemini | Grounding is deferred to Phase 5 and not wired into the runner — Gemini cannot serve the web-research leaf today; route the leaf elsewhere until Phase 5 lands |
| Missing `return.json` after runner exits 0 | Runner bug or output-folder permission issue; treat as `BLOCKED`, re-dispatch fresh |
| No session resumption | A halted dispatch must be re-dispatched fresh with the resolution inlined; never attempt `--session` / `--continue` |
| max_output probe-pending | Batch sizes based on 8192 max_output are conservative estimates — re-verify before large batches |

### The gemini task contract

A gemini-executable task file extends the generic task-file contract with the following API-worker requirements. The conductor validates before dispatch; a missing required field = halt + report.

**Required frontmatter additions:**

```yaml
execution_kind: text   # API chat workers produce text/structured output
executor: gemini
variant: 3.5-flash | 3.1-flash-lite
output_folder: <path relative to the dispatch root — runner writes here>
doubt_policy: halt
# NOTE: no `grounded` field — grounding is deferred to Phase 5 and not wired into the runner.
# When Phase 5 ships the runner pass-through, a `grounded:` frontmatter field will be added here.
```

**Required body sections:** Goal (one bounded deliverable) · Context Snapshot (ALL context inlined — the worker cannot read the workspace) · Output Requirements (exact format the runner should write into `--output-folder`) · Return Format (five-field return schema in `return.json`).

### Recipes

```powershell
# 3.5-flash dispatch — mid-cost, top-reasoning (default JSON-envelope mode):
python orchestration/models/_api/run.py `
  --provider gemini `
  --model <gemini-3.5-flash-api-id> `
  --prompt-file dispatch/prompt.md `
  --output-folder dispatch/output/
```

```powershell
# 3.1-flash-lite dispatch — cheapest, mid-reasoning (volume processing, default JSON-envelope mode):
python orchestration/models/_api/run.py `
  --provider gemini `
  --model <gemini-3.1-flash-lite-api-id> `
  --prompt-file dispatch/prompt.md `
  --output-folder dispatch/output/
```

(No grounded recipe — grounding is deferred to Phase 5 and not reachable through the current runner.)
