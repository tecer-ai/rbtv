# `deepseek` package delta

Per-model delta for the **deepseek** API chat worker — a stateless HTTP-call worker dispatched via the shared `_api/run.py` runner. This file fills the dispatch-wrapper template's INSERT points with deepseek-specific binding obligations and the deepseek return surface, plus the mandatory `invocation` section — the exact dispatch manual that the generic card explicitly does NOT carry (dispatch-wrapper §7).

The render script (`../render-manuals.py`) composes the generic wrapper (`{rbtv_path}/orchestration/skills/orchestrating/cards/dispatch-wrapper.md`) with the sections below into `./manual.md`. Edit deepseek behavior HERE; never in the rendered manual.

**Model-id caveat (applies everywhere a model id appears):** `v4-flash` and `v4-pro` are RBTV routing labels sourced from `routing-matrix-reference.md` (2026 estimates). The actual DeepSeek API model id is passed to the runner via `--model` at dispatch time and MUST be re-verified against DeepSeek's live API docs (`https://api-docs.deepseek.com`) before the pilot. Never treat a routing label as an authoritative API id.

<!-- RENDER:DELTA model-binding-delta -->
**DeepSeek-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What the deepseek worker is bound to |
|------------|--------------------------------------|
| **API chat worker — no filesystem access** | The runner calls the DeepSeek API and writes ONLY into `--output-folder`. The worker never reads the workspace, runs no shell commands, and executes no tools. All context it needs MUST be inlined into the prompt file at dispatch time. |
| **Stateless — no session resumption** | Every dispatch is an independent API call. A `DOUBT_ESCALATED` or `NEEDS_CONTEXT` halt triggers a fresh re-dispatch (with the resolution inlined into the prompt); there is no `--session` / `--continue` path. The conductor does NOT attempt to resume. |
| **Model id is a dispatch-time parameter** | The routing variant (`v4-flash` or `v4-pro`) selects the RBTV routing profile. The actual DeepSeek API model id is supplied via `--model <id>` at dispatch; re-verify the id against live provider docs before every pilot — the routing label is NOT an API id. |
| **Key-resolution availability** | The runner checks `DEEPSEEK_API_KEY` in the OS environment, then the `env_file` path in `rbtv.json`. If absent in both, the package is unavailable for this dispatch; the conductor logs it and degrades to the next capable worker — never halts the run. |
| **Output-folder confinement** | The runner path-sanitizes every write against `../` traversal and absolute paths. The conductor does NOT need to scope a work-dir. Post-run, verify that the returned files land inside `--output-folder` only. |
| **Probe-pending status** | Both variants are `evidence_status: probe-pending` — not yet pilot-validated. Use only where the routing card explicitly allows unvalidated workers; flag the seam in the run-log. |
<!-- RENDER:DELTA-END model-binding-delta -->

<!-- RENDER:DELTA model-transport-note -->
**DeepSeek return surface:** the `_api/run.py` runner makes the API call and writes its results into `--output-folder`. The return surface has two layers:

1. **`return.json`** in `--output-folder` — the runner's five-field structured return: `status`, `landed`, `validation`, `concerns`, `open_questions`. This is the machine-parseable contract the conductor reads after every dispatch.
2. **Model-emitted envelope files** in `--output-folder` — any files the model's response directs the runner to write (e.g. the raw model response, extracted content blocks, tool-call outputs if the runner supports them). File list and format depend on the runner version and the task's output contract.

The conductor treats `return.json` as the primary return signal. Reconcile it against the envelope files on disk — on any disagreement between `return.json` and the on-disk files, disk wins. A missing `return.json` (runner crashed) means the dispatch status is `BLOCKED`; no recovery path exists for API workers (re-dispatch fresh).
<!-- RENDER:DELTA-END model-transport-note -->

<!-- RENDER:DELTA invocation -->
The DeepSeek API dispatch manual — the exact runner invocation, variant selection, exit handling, and the deepseek task contract. Sourced from `routing-matrix-reference.md` §2 (2026 estimates) + DeepSeek API docs.

**Re-verify model ids, context limits, and pricing against `https://api-docs.deepseek.com` before the pilot.** This manual is `probe-pending` until a live pilot validates it.

### Pre-flight (before any dispatch)

| Check | How | Gate |
|-------|-----|------|
| Runner present | `python orchestration/models/_api/run.py --help` | Absent → the package cannot dispatch; halt and surface |
| API key resolves | `$env:DEEPSEEK_API_KEY` present, or `env_file` in `rbtv.json` carries the key | Absent → package unavailable; conductor degrades, does not halt the run |
| Model id current | Cross-check the id in the dispatch command against DeepSeek's live API docs | Stale id → update `--model <id>` before dispatch; never dispatch with an unverified id |

### Invocation shape

The runner is always non-interactive. All dispatch variants use the same shape — the `--model` flag selects the DeepSeek variant:

```powershell
python orchestration/models/_api/run.py `
  --provider deepseek `
  --model <deepseek-api-model-id> `
  --prompt-file <path/to/prompt.md> `
  --output-folder <path/to/output-dir/>
```

| Flag | Required | Notes |
|------|----------|-------|
| `--provider deepseek` | yes | Selects the DeepSeek client in `_api/clients/` |
| `--model <id>` | yes | Actual DeepSeek API model id — re-verify against provider docs; NOT the RBTV routing label |
| `--prompt-file <f>` | yes | Path to the prompt file written by the conductor (the composed header + payload) |
| `--output-folder <d>` | yes | Directory the runner writes `return.json` and envelope files into; created by the runner if absent |

### Variant selection

Route on the `(deepseek, variant)` pair from the manifest; translate to a `--model <id>` argument at dispatch time.

| RBTV variant | Routing profile | DeepSeek API model id |
|--------------|-----------------|----------------------|
| `v4-flash` | `cost_class: cheapest`, `reasoning_tier: mid` — best cost/benefit; partially-bounded tasks | Re-verify at `https://api-docs.deepseek.com` before dispatch |
| `v4-pro` | `cost_class: low`, `reasoning_tier: top` — max reasoning quality; judgment-dense tasks | Re-verify at `https://api-docs.deepseek.com` before dispatch |

Both variants share identical `headless`, `tool_surface`, `confinement`, and `swarm_support` values — they differ ONLY on `reasoning_tier` and `cost_class`, which is the routing-relevant distinction required by the schema's variant field-count discipline.

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
| Stale model id dispatched | Always re-verify `--model <id>` against live DeepSeek docs before pilot; routing labels are NOT API ids |
| API key absent | Pre-flight key-resolution check; degrade gracefully, never halt the run |
| Missing `return.json` after runner exits 0 | Runner bug or output-folder permission issue; treat as `BLOCKED`, re-dispatch fresh |
| Thinking-mode token cost surprise | V4-Flash has Thinking Mode on by default (routing-matrix §2) — confirm token budget before large batches; re-verify thinking toggle flags against provider docs |
| No session resumption | A halted dispatch must be re-dispatched fresh with the resolution inlined; never attempt `--session` / `--continue` |

### The deepseek task contract

A deepseek-executable task file extends the generic task-file contract with the following API-worker requirements. The conductor validates before dispatch; a missing required field = halt + report.

**Required frontmatter additions:**

```yaml
execution_kind: text   # or reasoning — API chat workers produce text/structured output, not code artifacts
executor: deepseek
variant: v4-flash | v4-pro
output_folder: <path relative to the dispatch root — runner writes here>
doubt_policy: halt
```

**Required body sections:** Goal (one bounded deliverable) · Context Snapshot (ALL context inlined — the worker cannot read the workspace) · Output Requirements (exact format the runner should write into `--output-folder`) · Return Format (five-field return schema in `return.json`).

### Recipes

```powershell
# V4-Flash dispatch — cheapest, mid-reasoning:
python orchestration/models/_api/run.py `
  --provider deepseek `
  --model <deepseek-v4-flash-api-id> `
  --prompt-file dispatch/prompt.md `
  --output-folder dispatch/output/
```

```powershell
# V4-Pro dispatch — max reasoning quality:
python orchestration/models/_api/run.py `
  --provider deepseek `
  --model <deepseek-v4-pro-api-id> `
  --prompt-file dispatch/prompt.md `
  --output-folder dispatch/output/
```
<!-- RENDER:DELTA-END invocation -->
