# `manus` package delta

Per-model delta for the **manus** agentic-web worker — an autonomous-agent task-API worker dispatched via the shared `_api/run.py` runner. Manus rides the SAME runner as the chat clients (shared runner, dynamic client resolution) and differs ONLY in its client and its manifest profile: it is NOT a chat worker — it submits a **task**, polls server-side until the agent completes, and retrieves the agent's output. This file fills the dispatch-wrapper template's INSERT points with manus-specific binding obligations and the manus return surface, plus the mandatory `invocation` section — the exact dispatch manual that the generic card explicitly does NOT carry (dispatch-wrapper §7).

The render script (`../render-manuals.py`) composes the generic wrapper (`{rbtv_path}/orchestration/skills/orchestrating/cards/dispatch-wrapper.md`) with the sections below into `./manual.md`. Edit manus behavior HERE; never in the rendered manual.

**Model-label caveat:** `manus-autonomous` is the single RBTV routing label for the one Manus operating profile. Manus is an autonomous agent, not a chat model with selectable model ids — `--model manus-autonomous` selects the routing profile; there is no alternate API model id to swap. Pricing validated live (2026-06-09): ~$0.01/credit, ~150 credits/task ≈ ~$1.50/task. Reference: `https://api.manus.ai/docs`.

**Manus distinguishing trait — autonomous server-side browser (always raw-dump):** Manus is the ONLY agentic-web worker in the routing table. The agent runs its OWN browser/tool loop **server-side** (navigate, click, fill, synthesize) — we do not drive it and we get no code artifact back, only the agent's task output. The client declares `structured_output: False` (`_api/clients/manus.py`), so the shared runner routes every Manus dispatch through its **raw-dump path** generically: one raw-dumped output file + `return.json` with `status: DONE_WITH_NOTES` and a concern naming the raw-dump. There is **no `{files:[…]}` JSON envelope** — the output is autonomous-agent output, not our structured envelope.

<!-- RENDER:DELTA model-binding-delta -->
**Manus-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What the manus worker is bound to |
|------------|------------------------------------|
| **Agentic-web worker — no local filesystem access** | The runner submits a task to the Manus API; the agent reads NOTHING from our workspace. ALL context the task needs MUST be inlined into the prompt file at dispatch time — it is inlined into the Manus task `description`. The runner writes ONLY into `--output-folder`. |
| **Server-side autonomous loop — not ours to constrain** | Manus runs its own browser/tool loop server-side. We do NOT pass an agent file, an MCP server, or a tool allowlist that constrains it; its autonomy is invisible to our topology and depth cap. Confinement is the runner's job (scoping the written OUTPUT), not a work-dir the conductor passes. |
| **Always raw-dump — no JSON envelope, no code cold-verify** | `structured_output` is False, so every dispatch returns `DONE_WITH_NOTES` + one raw-dumped output file + a concern naming the raw-dump. There is no structured `{files:[…]}` envelope. The return is **non-development** — verified by a Claude reviewer reading the content for quality, NOT by a code cold-verify (there is no code artifact). |
| **Per-task billing + minutes-scale latency** | Manus is billed PER TASK, not per token — forecast budget by task count. A real autonomous run can take minutes; a `WALL_MS` of seconds-to-minutes is normal and is NOT a hang. The dispatch never exceeds the configured timeout (default 300s / 5 minutes). |
| **No session resumption** | The poll loop is internal to a single dispatch. A `error`/`timeout`/`DOUBT_ESCALATED` halt triggers a fresh re-dispatch (resolution inlined into the prompt); there is no `--session` / `--continue` path. The conductor does NOT attempt to resume. |
| **Key-resolution availability** | The runner checks `MANUS_API_KEY` in the OS environment, then the `env_file` path in `rbtv.json`. If absent in both, the package is unavailable for this dispatch; the conductor logs it and degrades — never halts the run. The key is sent as `x-manus-api-key` header and never echoed. |
| **Validated status** | The single variant is `evidence_status: validated` — piloted live 2026-06-09 against Manus API v2 (`https://api.manus.ai/v2`). `context_window`/`max_output` remain unverified placeholders (Manus publishes no token limits) — do not size large inlined contexts on them. |
| **Message text only — not file artifacts (D-exec-14)** | The client captures `assistant_message.content` (the agent’s message text/narration), NOT Manus file artifacts. For file-deliverable tasks the substantive output may be in an attachment the client does not yet fetch. Fetching file artifacts is a noted follow-on enhancement. |
<!-- RENDER:DELTA-END model-binding-delta -->

<!-- RENDER:DELTA model-transport-note -->
**Manus return surface — always raw-dump (the only mode Manus has):**

The `_api/run.py` runner submits the task, polls to completion, and writes results into `--output-folder`. Because the client declares `structured_output: False`, the runner uses the **raw-dump path**, not the JSON-envelope path:

1. **`return.json`** in `--output-folder` — the runner's five-field structured return: `status`, `landed`, `validation`, `concerns`, `open_questions`. For Manus, `status` is `DONE_WITH_NOTES` on success (raw-dump is the only path), `landed` lists the single raw-dumped output file, `validation` records the task duration (`WALL_MS`) and the raw-dump-fallback flag (always set for Manus), and `concerns` names the raw-dump. This is the machine-parseable contract the conductor reads after every dispatch.
2. **One raw-dumped output file** in `--output-folder` — the agent's arbitrary task result, written as-is (or JSON-dumped if structured). This is NOT a parsed `{files:[…]}` envelope — it is the whole agent output as one file.

The conductor treats `return.json` as the primary return signal and reconciles it against the on-disk output file — on any disagreement, disk wins. A missing `return.json` (runner crashed) means the dispatch status is `BLOCKED`; no recovery path exists (re-dispatch fresh).

**Non-development verification path:** a Manus return carries no code artifact to cold-verify. The independent verifier is a Claude **reviewer** that reads the raw-dumped content for quality against the task contract — there is no build/test/lint cold-verify step, because Manus produced agent output, not code.
<!-- RENDER:DELTA-END model-transport-note -->

<!-- RENDER:DELTA invocation -->
The Manus API dispatch manual — the exact runner invocation, the single profile, exit/halt handling, and the manus task contract. Sourced from `routing-matrix-reference.md` §7 + Manus API docs + the built client (`_api/clients/manus.py`).

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
| `manus-autonomous` | `cost_class: high` (per-task), `reasoning_tier: top`, `web_access: true`, `code_competence: none` — the autonomous-web leaf; never the code path | `--model manus-autonomous` (no alternate API id) |

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
<!-- RENDER:DELTA-END invocation -->
