# `gemini` package delta

Per-model delta for the **gemini** API chat worker — a stateless HTTP-call worker dispatched via the shared `_api/run.py` runner. This file fills the dispatch-wrapper template's INSERT points with gemini-specific binding obligations and the gemini return surface, plus the mandatory `invocation` section — the exact dispatch manual that the generic card explicitly does NOT carry (dispatch-wrapper §7).

The render script (`../render-manuals.py`) composes the generic wrapper (`{rbtv_path}/orchestration/skills/orchestrating/cards/dispatch-wrapper.md`) with the sections below into `./manual.md`. Edit gemini behavior HERE; never in the rendered manual.

**Model-id caveat (applies everywhere a model id appears):** `3.5-flash` and `3.1-flash-lite` are RBTV routing labels sourced from `routing-system.md` Part II — Gemini (2026 estimates). The actual Google Gemini API model id is passed to the runner via `--model` at dispatch time and MUST be re-verified against Google's live API docs (`https://ai.google.dev/gemini-api/docs/models`) before the pilot. Never treat a routing label as an authoritative API id.

**Gemini distinguishing trait — search grounding (shipped and routable):** Gemini is the ONLY web-capable chat worker in the routing table, and search grounding (Google Search integration) is wired end-to-end. The shared `_api/run.py` runner exposes a generic `--grounded` flag (which sets `extra_params["grounding"]=True`) plus an `--extra-params` JSON pass-through; the Gemini client (`_api/clients/gemini.py`) reads `extra_params["grounding"]` and swaps `responseMimeType: application/json` for the `google_search` tool. Both the p5-3 runner pass-through and the p5-4 web-research-leaf routing shipped, and grounding was first live-fired 2026-06-09 (p6-1 pilot). Gemini IS routable as the light-grounding web-research leaf today (routing §6). A grounded dispatch is **mutually exclusive with JSON-envelope mode** — see the Grounding section below for the raw-dump return surface it produces.

<!-- RENDER:DELTA model-binding-delta -->
**Gemini-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What the gemini worker is bound to |
|------------|-------------------------------------|
| **API chat worker — no filesystem access** | The runner calls the Gemini API and writes ONLY into `--output-folder`. The worker never reads the workspace, runs no shell commands, and executes no tools. All context it needs MUST be inlined into the prompt file at dispatch time. |
| **Stateless — no session resumption** | Every dispatch is an independent API call. A `DOUBT_ESCALATED` or `NEEDS_CONTEXT` halt triggers a fresh re-dispatch (with the resolution inlined into the prompt); there is no `--session` / `--continue` path. The conductor does NOT attempt to resume. |
| **Model id is a dispatch-time parameter** | The routing variant (`3.5-flash` or `3.1-flash-lite`) selects the RBTV routing profile. The actual Gemini API model id is supplied via `--model <id>` at dispatch; re-verify the id against live provider docs before every pilot — the routing label is NOT an API id. |
| **Key-resolution availability** | The runner checks `GEMINI_API_KEY` in the OS environment, then the `env_file` path in `rbtv.json`. If absent in both, the package is unavailable for this dispatch; the conductor logs it and degrades to the next capable worker — never halts the run. |
| **Output-folder confinement** | The runner path-sanitizes every write against `../` traversal and absolute paths. The conductor does NOT need to scope a work-dir. Post-run, verify that the returned files land inside `--output-folder` only. |
| **Validated status** | Both variants are `evidence_status: validated` — the worker path ran end-to-end on a real paid Gemini call at the p6-1 pilot (2026-06-09); variant ids + prices live-confirmed the same pilot (D-exec-15). Routable as a settled choice. |
<!-- RENDER:DELTA-END model-binding-delta -->

<!-- RENDER:DELTA model-transport-note -->
**Gemini return surface — two reachable modes (the dispatch picks one):**

The `_api/run.py` runner makes the API call and writes its results into `--output-folder`. The return surface depends on whether the dispatch passed `--grounded`:

**Default (JSON-envelope) mode — no `--grounded`:** the standard two-layer return surface:

1. **`return.json`** in `--output-folder` — the runner's five-field structured return: `status`, `landed`, `validation`, `concerns`, `open_questions`. This is the machine-parseable contract the conductor reads after every dispatch.
2. **Model-emitted envelope files** in `--output-folder` — files the model's response directs the runner to write (raw model response, extracted content blocks). File list and format depend on the runner version and the task's output contract.

The conductor treats `return.json` as the primary return signal. Reconcile it against the envelope files on disk — on any disagreement between `return.json` and the on-disk files, disk wins. A missing `return.json` (runner crashed) means the dispatch status is `BLOCKED`; no recovery path exists for API workers (re-dispatch fresh).

**Grounded mode — `--grounded` passed:** a grounded dispatch is a **raw-dump research path**. The runner asks the model for clean Markdown (NOT the `{files:...}` envelope) and writes the answer verbatim to `raw-output.md`, returning `status: DONE_WITH_NOTES` with `landed: ["raw-output.md"]`. `return.json` IS still written (every runner exit writes it) — read it for `status`/`concerns`, and read `raw-output.md` for the answer. The runner emits NO model-named envelope file in grounded mode. (At the API level, grounding is mutually exclusive with `responseMimeType: application/json` — `gemini.py` swaps it for the `google_search` tool — so the structured-JSON envelope is unavailable in grounded mode; the runner therefore skips envelope parsing entirely.) Grounded calls also run with a larger `maxOutputTokens` default than the JSON-envelope path: 3.x-flash extended thinking is billed against `maxOutputTokens`, so too small a budget starves the visible answer (the 2026-06-24 empty/truncated-output fix).
<!-- RENDER:DELTA-END model-transport-note -->

<!-- RENDER:DELTA invocation -->
The Gemini API dispatch manual — the exact runner invocation, variant selection, exit handling, and the gemini task contract. Sourced from `routing-system.md` Part II — Gemini (2026 estimates) + Google Gemini API docs.

**Variant ids + pricing were live-confirmed 2026-06-09 (p6-1 pilot, D-exec-15); re-verify context limits and any post-refresh pricing against `https://ai.google.dev/gemini-api/docs`.** This manual is `validated`.

**Grounding is SHIPPED and dispatchable.** The shared `run.py` runner exposes `--grounded` (sets `extra_params["grounding"]=True`) plus an `--extra-params` JSON pass-through, and the Gemini client honors it (search grounding via the `google_search` tool). p5-3 (runner pass-through) and p5-4 (web-research-leaf routing) both shipped; grounding was first live-fired 2026-06-09 (p6-1 pilot). A default dispatch (no `--grounded`) runs in JSON-envelope mode; a `--grounded` dispatch runs grounded with a raw-dump return — see the Grounding section.

### Pre-flight (before any dispatch)

| Check | How | Gate |
|-------|-----|------|
| Runner present | `python orchestration/models/_api/run.py --help` | Absent → the package cannot dispatch; halt and surface |
| API key resolves | `$env:GEMINI_API_KEY` present, or `env_file` in `rbtv.json` carries the key | Absent → package unavailable; conductor degrades, does not halt the run |
| Model id current | Cross-check the id in the dispatch command against Google's live API docs | Stale id → update `--model <id>` before dispatch; never dispatch with an unverified id |

### Invocation shape

The runner is always non-interactive. The `--provider gemini` flag selects the Gemini client; the `--model` flag selects the variant. Without `--grounded` the dispatch runs in default JSON-envelope mode.

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
| `--grounded` | no | Enables Google Search grounding (`extra_params["grounding"]=True`). Switches the call to the raw-dump research path → answer in `raw-output.md` (`DONE_WITH_NOTES`, `landed:[raw-output.md]`; `return.json` is still written). Use ONLY for the light-grounding web-research leaf. |
| `--extra-params <json>` | no | Advanced JSON pass-through merged into `extra_params`. Rarely needed; `--grounded` is the supported grounding switch. |

### Variant selection

Route on the `(gemini, variant)` pair from the manifest; translate to a `--model <id>` argument at dispatch time.

| RBTV variant | Routing profile | Gemini API model id |
|--------------|-----------------|---------------------|
| `3.5-flash` | `reasoning: 6`, `coding: 3`, `cost: 4` — best intelligence; judgment-dense reasoning/text-synthesis tasks | `gemini-3.5-flash` — live-confirmed 2026-06-09 (D-exec-15) |
| `3.1-flash-lite` | `reasoning: 2`, `coding: 1`, `cost: 2` — volume processing; cost-critical tasks | `gemini-3.1-flash-lite` — live-confirmed 2026-06-09 (D-exec-15) |

Both variants share identical `headless`, `tool_surface`, `confinement`, and `swarm_support` values and both carry `web_access: true`. They differ on `reasoning` and `coding` integers, which is the routing-relevant distinction required by the schema's variant field-count discipline.

### Grounding (shipped)

Search grounding is **wired end-to-end and dispatchable** via `--grounded`. Gemini is the routable light-grounding web-research leaf (routing §6). Pick the dispatch mode by the leaf the task needs.

| Dispatch type | When to use | Return surface |
|---------------|-------------|----------------|
| Default JSON-envelope (no `--grounded`) | Text generation, reasoning, summarization, structured output over inlined context | Standard: `return.json` + envelope files |
| Grounded (`--grounded`, web-research leaf) | A single light grounded lookup — one search-grounded call, NOT rigorous multi-source research | Raw-dump — answer (clean Markdown) in `raw-output.md` (`DONE_WITH_NOTES`, `landed:[raw-output.md]`); `return.json` still written, no envelope file |

The two modes are mutually exclusive on a single call: `--grounded` swaps `responseMimeType: application/json` for the `google_search` tool, so the runner skips the `{files:...}` envelope and dumps the answer raw. Grounded calls use a larger `maxOutputTokens` default than the JSON-envelope path because 3.x-flash extended thinking is billed against `maxOutputTokens` — too small a budget starves the visible answer (the 2026-06-24 fix). For rigorous multi-source research (source evaluation, citations, cross-checking), route to the `rbtv-web-searching` Agent-tool path instead — Gemini grounding is light single-call only.

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
| Grounded answer — where it lands | A `--grounded` call writes the answer to `raw-output.md` (`DONE_WITH_NOTES`, `landed:[raw-output.md]`); `return.json` IS also written (read it for status/concerns). The runner emits NO model-named envelope file in grounded mode — read `raw-output.md`, not an envelope |
| Grounded `raw-output.md` truncated or empty | The thinking budget consumed `maxOutputTokens` (3.x-flash bills extended thinking against it). The client's grounded default (`_GROUNDED_MAX_OUTPUT_TOKENS` in `gemini.py`) covers thinking + a full light-grounding answer; raise that constant if an unusually long grounded answer is ever needed |
| Rigorous multi-source research routed to Gemini | Gemini grounding is LIGHT single-call only — route rigorous multi-source research (source evaluation, citations, cross-checking) to the `rbtv-web-searching` Agent-tool path, not Gemini |
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
grounded: true | false   # optional; default false. true → conductor passes --grounded (light grounded lookup; raw-dump return — answer in raw-output.md, return.json still written). Set ONLY for the light-grounding web-research leaf.
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

```powershell
# Grounded dispatch — single light grounded lookup (web-research leaf).
# Returns the answer in raw-output.md (DONE_WITH_NOTES); return.json is also written.
# Grounded = raw-dump: the runner asks for clean Markdown and parses no {files:...} envelope:
python orchestration/models/_api/run.py `
  --provider gemini `
  --model <gemini-3.5-flash-api-id> `
  --grounded `
  --prompt-file dispatch/prompt.md `
  --output-folder dispatch/output/
```
<!-- RENDER:DELTA-END invocation -->
