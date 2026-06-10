# DISPATCH — p5-checkpoint-fix (kimi/default, bounded code) — rewrite manus.py to the Manus API v2

You are a **non-reasoning bounded-code executor**. The Manus client targets a WRONG/OUTDATED API; rewrite its API integration to the REAL Manus API **v2** per the EXACT contract inlined below. Implement verbatim; do not invent fields. A decision the task does not resolve → HALT and return `DOUBT_ESCALATED`.

## Binding obligations
- **Work-dir:** the rbtv repo root (`--work-dir`). Allowlist paths are repo-relative.
- **Rule-loading:** inspect for `.agents/behavior-rules/`; this repo has `AGENTS.md` at root and NO `.agents/behavior-rules/` — read `AGENTS.md`, then proceed.
- **Allowlist (MODIFY ONLY):** `orchestration/models/_api/clients/manus.py`. You MAY READ `orchestration/models/_api/clients/base.py`, `deepseek.py`, `gemini.py`, `run.py`. Any other create/modify/delete is out-of-allowlist.
- **No commit** (conductor commits after opus review). **No network/API calls** (do NOT make a live Manus call — the conductor re-tests). **No exploration beyond the named files.** Swarm disabled. NEVER read/print/echo any API key value.
- **Evidence on disk:** capture your validation outputs; cite them in `validation`.

## Return — EXACTLY these five named fields (no rename, no prose-only)
`status` · `landed` (manus.py, no hash) · `validation` (each cmd + EXIT + WALL_MS + SKIPPED_COUNT) · `concerns` · `open_questions`. The conductor reconciles vs `git diff` — message is a HINT, disk is truth.

## Why (inlined — do NOT re-read): the current manus.py uses `api.manus.im/v1` + `Authorization: Bearer` + REST `/tasks` + `completed`/`failed` status. That is WRONG (it hit Manus's web backend → 401). The REAL Manus developer API is **v2** (official docs `open.manus.ai/docs/v2`). Keep the class STRUCTURE (subclass `ProviderClient`, `structured_output = False`, synchronous, `requests`, retry/backoff, key-in-header-only, the configurable timeout) — rewrite ONLY the API specifics below.

## `[INLINED]` Manus API v2 — the EXACT contract (authoritative; from official docs)

**Base URL:** `https://api.manus.ai/v2`
**Auth header:** `x-manus-api-key: <api_key>` — NOT `Authorization: Bearer`. (Content-Type: application/json.)

**Create a task —** `POST https://api.manus.ai/v2/task.create`
- Request body (JSON): `{"message": {"content": "<the full prompt/task text as a string>"}}` (the `message` object is required; `message.content` carries the prompt). Optionally `"agent_profile"` may be omitted (Manus defaults).
- Success: **HTTP 200** with body `{"ok": true, "request_id": "...", "task_id": "...", "task_title": "...", "task_url": "...", ...}`. **The task id is `task_id`.**

**Poll task status —** `GET https://api.manus.ai/v2/task.detail?task_id=<task_id>`
- Response: `{"ok": true, "request_id": "...", "task": {"id": "...", "status": "running|stopped|waiting|error", "credit_usage": <int>, ...}}`. **The status is `task.status`** (i.e. `data["task"]["status"]`).
- Status meanings: `running` = working (keep polling); `stopped` = FINISHED/COMPLETED (success — go fetch the output); `waiting` = paused for input (treat as still-in-progress: keep polling until the timeout); `error` = failed (raise).

**Fetch the agent output —** `GET https://api.manus.ai/v2/task.listMessages?task_id=<task_id>&order=asc`
- Response: `{"ok": true, "messages": [<TaskEvent>...], "has_more": <bool>, "next_cursor": "..."}`. Each event has an event type; **the agent's text answer is in events whose payload is `assistant_message`, at `assistant_message.content`.** (An error event is `error_message.content`.) The event shape is `{"type"/"event_type": "assistant_message", "assistant_message": {"content": "..."}}` — be tolerant of the exact key for the type discriminator; collect every event that carries an `assistant_message` object and concatenate its `.content` (in `order=asc` chronological order) into one string. That concatenated string is the agent's output.

## Implementation Requirements (exact — rewrite manus.py's API methods to the above)

1. `self.base_url = "https://api.manus.ai/v2"` (replace the old `api.manus.im/v1`). Keep `self.timeout` (default 300), `self.retries` (default 3), `self.api_key`.
2. Headers: `{"Content-Type": "application/json", "x-manus-api-key": self.api_key}` (replace the `Authorization: Bearer` header). The key appears ONLY here — never in a URL/log/exception.
3. **Create:** `POST {base_url}/task.create` with json `{"message": {"content": description}}`, per-request `timeout=30`. Retry/backoff (`2**attempt`) on `requests.exceptions.RequestException` and on HTTP 429/5xx; on **HTTP 200** → parse `task_id = data["task_id"]`; on other non-retryable 4xx → raise `Exception(f"Manus API error: {status} - {resp.text}")` (resp.text is the server body, NOT the key); after retries exhausted → raise the last error (guard the unbound case as gemini.py does: `last_error: Optional[Exception] = None` + an explicit fallback raise).
4. **Poll:** loop `while time.time() - start < self.timeout`: `GET {base_url}/task.detail?task_id={task_id}` (per-request `timeout=10`); on a `RequestException` sleep 2s + continue; on a non-ok HTTP status raise; else `status = data["task"]["status"]` → if `"stopped"` → break to fetch output; if `"error"` → raise `Exception("Task failed: " + <error detail if available>)`; if `"running"` or `"waiting"` → sleep 2s + continue. On loop exhaustion → raise `Exception("Task timeout")`.
5. **Output (after `stopped`):** `GET {base_url}/task.listMessages?task_id={task_id}&order=asc` (timeout=10) → from `data["messages"]`, collect every event carrying an `assistant_message` (use `.get("assistant_message")`), take its `.get("content","")`, join the non-empty ones with `"\n"` → `output_text`. Return `Response(content=output_text, model=None, usage=None, raw_response={"task_id": task_id, "messages": data.get("messages")})`. (If no assistant_message content found, return the whole listMessages JSON-dumped as content so nothing is lost.)
6. Keep `structured_output = False`; keep sync + `requests` (NO aiohttp/asyncio); keep the `chat(messages, options)` signature conforming to base.py. Build `description` from the messages exactly as the current manus.py does. Do NOT touch `run.py`.

## Validation (run exactly; report each in `validation`)
1. `python -c "import ast,io; ast.parse(io.open('orchestration/models/_api/clients/manus.py',encoding='utf-8').read()); print('AST_OK')"` → EXIT 0.
2. Static self-check (grep your file, report markers): `api.manus.ai/v2` present; `api.manus.im` ABSENT; `x-manus-api-key` present; `Authorization` / `Bearer` ABSENT; `task.create`, `task.detail`, `task.listMessages` present; `assistant_message` present; NO `aiohttp`/`asyncio`; `structured_output` set False; key only in the header (no `key=` in a URL). Print `V2_OK` if all hold, else list failures.
3. Base-conformance: the entry method name + signature still MATCH base.py's abstract method. Print `BASE_CONFORMS_OK` or the mismatch.

## Commit Rule
Do NOT commit. On validation pass, return the five fields; the conductor reviews (opus) then commits.

## Return Format
Return EXACTLY: `status`, `landed`, `validation`, `concerns`, `open_questions`.
