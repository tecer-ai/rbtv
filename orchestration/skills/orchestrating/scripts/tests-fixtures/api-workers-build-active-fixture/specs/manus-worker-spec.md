# Spec — Manus Agentic Worker

> Build paths are relative to the **rbtv repo root** (`3-resources/tools/rbtv/`). Worker work-dir = that repo. This worker rides the SAME `run.py` as the chat clients (shared runner, dynamic client resolution) — it differs ONLY in its client and its manifest profile.

## Goal

The owner can run `python orchestration/models/_api/run.py --provider manus --model manus-autonomous --prompt-file <f> --output-folder <dir>` and the runner submits the prompt as an autonomous **task** to Manus, polls until the task completes (up to a long timeout), writes the agent's output into `<dir>`, and writes `return.json` — proving Manus works as an "assign-a-job" worker without crippling its autonomy.

## Context Snapshot

**Manus is NOT chat-completion** (validated live 2026-06-09 against `_api/clients/manus.py`): `base_url = https://api.manus.ai/v2`, auth header `x-manus-api-key: <key>` (NOT `Authorization: Bearer`). The flow is:
- `POST /v2/task.create` with `{"message":{"content":"<prompt>"}}` → `200` + `{"task_id":...}`.
- **Poll** `GET /v2/task.detail?task_id=<id>` every ~2s until `status == "stopped"` (completed) or `"error"` (failed) or timeout; `"running"`/`"waiting"` → keep polling.
- Output: `GET /v2/task.listMessages?task_id=<id>&order=asc` → agent text joined from `assistant_message.content` events.
- Output is the agent's message text/narration — there is **no** `{files:[…]}` JSON envelope. **NOTE (D-exec-14):** the client captures `assistant_message.content` (message text), NOT Manus file artifacts — for file-deliverable tasks the substantive output may be in an attachment the client does not yet fetch. Fetching file artifacts is a noted follow-on enhancement.

**Agentic profile:** the client declares `structured_output: False`. The shared runner reads that flag and routes Manus through its **raw-dump path** generically — no Manus-specific branch in `run.py` beyond a per-client timeout. (`run.py` change p5-3 is ONLY the per-client timeout + the `structured_output` flag read.)

**Adaptation:** make the client one-shot/synchronous for CLI use (wrap the async poll loop in a sync entry, or reimplement the poll synchronously). Keep the retry/backoff on task creation.

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | `run.py --provider manus … --prompt-file f --output-folder d` with a valid `MANUS_API_KEY` | The runner creates a Manus task from the prompt, polls to completion, writes the agent output as a file under `d/`, writes `d/return.json` `status: DONE_WITH_NOTES` (raw-dump is the only path) + a concern naming the raw-dump |
| 2 | Manus task completes with structured `output` | The runner writes that output (JSON-dumped or as-is) as one file; `landed` lists it; `validation` records the task duration (`WALL_MS`) |
| 3 | The `--target-file`/inlined context is present | Its content is inlined into the task `description` (Manus reads nothing from the local filesystem) |

## Edge Cases & Error Behavior

| Condition | Required behavior |
|-----------|-------------------|
| Task `status == "error"` | `status: BLOCKED` + the Manus error in `open_questions`; write `return.json` |
| Poll exceeds the timeout (task never completes) | `status: BLOCKED` + a timeout note; write `return.json` (never hang past the configured timeout) |
| Task-creation `POST` fails after retries | `status: BLOCKED` + the HTTP error |
| `MANUS_API_KEY` unresolved | Exit non-zero with a clear stderr message; never echo the key |

## Out of Scope

- Parsing/structuring the agent output into multiple files — Manus output is raw-dumped as one file (it is autonomous-agent output, not our envelope).
- Building an agent/tool-execution loop — Manus runs its own loop server-side; we only submit + poll.
- Browser-driving from our side — Manus does that itself.

## Test Plan

> Fidelity floor: a **real Manus task** against the live API writing a **real output file**; a real autonomous task may take minutes (a `WALL_MS` of seconds-to-minutes is plausible here, unlike a chat call).

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | A real Manus task writes its output | `run.py --provider manus … --prompt-file <real autonomous task> --output-folder <dir>` against the live API | One output file under `<dir>`; `return.json` `status: DONE_WITH_NOTES`, `landed` matches; `WALL_MS` reflects the real task duration | `<dir>/` listing + `return.json` + stdout/exit capture |
| 2 | A task with status `error` surfaces as BLOCKED, not silent | Submit a task crafted to fail (or simulate the error-status path) | `status: BLOCKED` + the error in `open_questions` | `return.json` |
| 3 | Timeout never hangs | Set a short timeout against a long task | The runner stops at the timeout with `status: BLOCKED` + timeout note | `return.json` + exit capture |
| 4 | Key never leaks | Grep prompt/return/stdout for the key after a real call | Zero matches | grep-output capture |

## Return Expectations

`return.json` carries the five fields; `landed` = the written output file(s); `validation` records the task `WALL_MS` and the raw-dump-fallback flag (always set for Manus). The conductor reconciles file existence against `landed`; a Manus return is **non-development** (no review-fix loop on code), reviewed by a Claude reviewer reading the content for quality.
