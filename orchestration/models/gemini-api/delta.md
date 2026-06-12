# `gemini` package delta

Per-model delta for the **gemini** API chat worker — a stateless HTTP-call worker dispatched via the shared `_api/run.py` runner. This file fills the dispatch-wrapper template's INSERT points with gemini-specific binding obligations and the gemini return surface, plus the mandatory `invocation` section — the exact dispatch manual that the generic card explicitly does NOT carry (dispatch-wrapper §7).

The render script (`../render-manuals.py`) composes the generic wrapper (`{rbtv_path}/orchestration/skills/orchestrating/cards/dispatch-wrapper.md`) with the sections below into `./manual.md`. Edit gemini behavior HERE; never in the rendered manual.

**Model-id caveat (applies everywhere a model id appears):** `3.5-flash` and `3.1-flash-lite` are RBTV routing labels sourced from `routing-matrix-reference.md` (2026 estimates). The actual Google Gemini API model id is passed to the runner via `--model` at dispatch time and MUST be re-verified against Google's live API docs (`https://ai.google.dev/gemini-api/docs/models`) before the pilot. Never treat a routing label as an authoritative API id.

**Gemini distinguishing trait — search grounding (built into the client; NOT yet wired into the runner):** Gemini is the ONLY web-capable chat worker in the routing table, and search grounding (Google Search integration) is implemented in the Gemini client (`_api/clients/gemini.py` reads `extra_params["grounding"]`). However, the shared `_api/run.py` runner has **no grounding switch** and passes no `extra_params` — so grounding is **NOT reachable through the standard runner today**. Grounding is **DEFERRED to Phase 5** (p5-3 adds a generic `--grounded`/`--extra-params` → `extra_params` pass-through to the runner; p5-4 routes the web-research leaf onto it). Until Phase 5 lands, every Gemini dispatch via the standard runner runs in **DEFAULT JSON-envelope mode only**. The conceptual note that grounding is **mutually exclusive with JSON-envelope mode** is forward context for when it IS wired — see the Grounding (Phase 5) section below. No part of this delta should be read as enabling a grounded dispatch today.

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
**Gemini return surface — standard envelope return (the only mode reachable today):**

The `_api/run.py` runner makes the API call in default JSON-envelope mode and writes its results into `--output-folder` using the standard two-layer return surface:

1. **`return.json`** in `--output-folder` — the runner's five-field structured return: `status`, `landed`, `validation`, `concerns`, `open_questions`. This is the machine-parseable contract the conductor reads after every dispatch.
2. **Model-emitted envelope files** in `--output-folder` — files the model's response directs the runner to write (raw model response, extracted content blocks). File list and format depend on the runner version and the task's output contract.

The conductor treats `return.json` as the primary return signal. Reconcile it against the envelope files on disk — on any disagreement between `return.json` and the on-disk files, disk wins. A missing `return.json` (runner crashed) means the dispatch status is `BLOCKED`; no recovery path exists for API workers (re-dispatch fresh).

**Forward context — grounded return surface (Phase 5, NOT reachable today):** once Phase 5 wires grounding into the runner (p5-3 pass-through + p5-4 web-research-leaf routing), a grounded dispatch will NOT produce a standard `return.json` envelope, because grounding is **mutually exclusive with JSON-envelope mode** in the client (`gemini.py`: setting `grounding` swaps `responseMimeType: application/json` for the `google_search` tool). When that mode ships it will return `DONE_WITH_NOTES` + a `raw-output.md` raw dump and the conductor will distinguish it by the future runner grounding parameter. **None of this is wired in the current runner** — no current dispatch can request grounding, so today every Gemini call returns the standard envelope above.
<!-- RENDER:DELTA-END model-transport-note -->

<!-- RENDER:DELTA invocation -->
The Gemini API dispatch manual — the exact runner invocation, variant selection, exit handling, and the gemini task contract. Sourced from `routing-matrix-reference.md` §4 (2026 estimates) + Google Gemini API docs.

**Variant ids + pricing were live-confirmed 2026-06-09 (p6-1 pilot, D-exec-15); re-verify context limits and any post-refresh pricing against `https://ai.google.dev/gemini-api/docs`.** This manual is `validated`.

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
| `3.5-flash` | `cost_class: mid`, `reasoning_tier: top` — best intelligence; judgment-dense tasks | `gemini-3.5-flash` — live-confirmed 2026-06-09 (D-exec-15) |
| `3.1-flash-lite` | `cost_class: cheapest`, `reasoning_tier: mid` — volume processing; cost-critical tasks | `gemini-3.1-flash-lite` — live-confirmed 2026-06-09 (D-exec-15) |

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
<!-- RENDER:DELTA-END invocation -->
