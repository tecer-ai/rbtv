# DISPATCH — p5-1 (kimi/default, bounded code)

You are a **non-reasoning bounded-code executor**. Implement the enumerated behavior in the TASK below EXACTLY. Do NOT reason about intent, redesign, generalize, or "fill in blanks" — every interface and edge case is pre-resolved. A decision left to you is a task bug: HALT and return `DOUBT_ESCALATED` with the precise question rather than guessing.

## Binding obligations (you are held to ALL of these on return)

- **Work-dir:** the rbtv repo root (passed via `--work-dir`). All allowlist paths are repo-relative.
- **Rule-loading:** Before any other action, inspect the work-dir for a `.agents/behavior-rules/` directory; if present, read your `AGENTS.md` + every file under it and treat them as binding. (This repo has `AGENTS.md` at root and NO `.agents/behavior-rules/` — read `AGENTS.md`, then proceed.)
- **Allowlist (CREATE ONLY this one file):** `orchestration/models/_api/clients/manus.py`. You MAY READ (not modify): `orchestration/models/_api/clients/base.py`, `orchestration/models/_api/clients/deepseek.py`, `orchestration/models/_api/clients/gemini.py`, `orchestration/models/_api/run.py`. Any create/modify/delete outside the allowlist is an out-of-allowlist write the conductor will flag — do not do it. No scratch/log/summary files anywhere.
- **Do NOT touch `run.py`** — this client rides the SAME shared runner unchanged. The runner integration (reading `structured_output`, the raw-dump path, `return.json`, the agentic timeout) is a SEPARATE later task (p5-3), NOT this one. This task creates ONLY the client class file.
- **No commit:** Do NOT `git commit`, `git add`, push, reset, or amend. Leave `manus.py` uncommitted on disk. The conductor reviews (opus) then commits.
- **No exploration beyond the named files:** everything you need is inlined below or in the four named readable files. Do NOT read the plan, other task files, or `decisions.md` at runtime.
- **Swarm disabled:** do NOT launch subagents.
- **Forbidden-ops are exhaustive:** no writes outside the work-dir, no push, no destructive git ops, **no network/API calls** (do NOT make a live Manus call — behavior is proven later at p5-checkpoint). NEVER read, store, print, or echo any API key VALUE; the client receives its key only via the base config object and sends it ONLY in the `Authorization` header.
- **Evidence on disk:** capture your validation command outputs; cite them in the `validation` field.

## Return — EXACTLY these five named fields (no rename, no extra, no prose-only)

- `status`: one of `DONE` · `DONE_WITH_NOTES` · `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT`
- `landed`: file created (path); you do NOT commit, so no hash
- `validation`: each command run + its `EXIT` + `WALL_MS` + `SKIPPED_COUNT` (0 if none; every skip needs a reason)
- `concerns`: anything the conductor should weigh
- `open_questions`: unresolved questions (the halting question for DOUBT_ESCALATED/NEEDS_CONTEXT)

The conductor reconciles your message against `git status`/`git diff` on disk — the message is a HINT, disk is truth.

## Worker-facing decisions in force (inlined — do NOT re-read decisions.md)

- **Architectural constraint (load-bearing):** the runner resolves its client dynamically by provider name (`clients/{provider}.py`). Adding a provider = add a client ONLY; NEVER edit `run.py`. A `run.py` edit in this task is a hard review failure.
- **structured_output discipline:** Manus declares `structured_output = False`. The shared runner reads that flag and routes Manus through its generic **raw-dump** path (no Manus-specific branch in `run.py`). Your job is ONLY to set the flag and return the agent output; the runner does the raw-dump.
- **Key handling:** the runner loads the API key and hands it to the client via the base config; the client sends it ONLY in the `Authorization: Bearer <key>` header — NEVER in a URL, query string, log, or exception message.

## Reference — files to READ in your work-dir (conform the class to THESE, not to the inlined source)

`[FULL READ]` these in the work-dir — they define the REAL current contract your class must match:
- `orchestration/models/_api/clients/base.py` — the base class you subclass (exact constructor, `chat()` signature, how `structured_output` is declared, how a `Response`/return value is shaped, how the key/config arrives).
- `orchestration/models/_api/clients/deepseek.py` AND `orchestration/models/_api/clients/gemini.py` — the two EXISTING sibling clients. Mirror their proven shape EXACTLY: **synchronous**, **`requests`** (NOT `aiohttp`/`asyncio`), explicit `structured_output` attribute, retry/backoff with exponential sleep, raise-on-failure, key in header only. Manus differs ONLY in its flow (task-create + poll instead of one chat call) and in `structured_output = False`.

## `[INLINED]` Manus worker spec — the behavior contract (source: `api-workers-build/specs/manus-worker-spec.md`)

> This is the authoritative behavior contract. The CLIENT's responsibility is the task-create → poll → return/​raise flow below; the runner (p5-3) does return.json/raw-dump/BLOCKED-mapping. Build ONLY the client.

**Manus is NOT chat-completion.** `base_url = https://api.manus.im/v1`. Flow:
- `POST /tasks` with `{description, autonomy_level: "high", timeout}` → `201` + `{task_id}`.
- **Poll** `GET /tasks/{task_id}` every ~2s until `status == "completed"` (returns `output`) or `"failed"` or timeout.
- Output is the agent's arbitrary task result — there is **no** `{files:[…]}` envelope. Client declares `structured_output = False`.
- **Adaptation:** make the client one-shot/synchronous for CLI use (reimplement the poll loop synchronously with `requests` — do NOT keep `aiohttp`/`asyncio`). Keep retry/backoff on task creation. Honor a long (minutes) timeout read from the base config (default to the source's behavior if config gives none).

**Client behavior the runner depends on (CLIENT side only):**
- On task `completed`: RETURN the agent output as the client's normal success result (the agent `output`, JSON-dumped if it is structured/dict, else as-is) so the runner can raw-dump it. Record/return the task wall-duration if the base contract exposes a slot for it; otherwise the runner times it.
- On task `status == "failed"`: RAISE with the Manus error message (the runner maps a raised exception to `status: BLOCKED` + the error). Do NOT echo the key.
- On poll exceeding the timeout (task never completes): RAISE a timeout error (never hang past the configured timeout). The runner maps it to `BLOCKED` + a timeout note.
- On task-creation `POST` failing after all retries: RAISE the HTTP error.
- If `MANUS_API_KEY` is unresolved: that is the runner's concern (it won't construct/credential the client) — the client just uses the key the base config gives it.

**Out of scope for this task:** parsing/structuring the agent output into multiple files (raw-dump is the only path — runner's job); any agent/tool-execution loop (Manus runs its own server-side); browser-driving (Manus does it); writing `return.json` or the BLOCKED envelope (runner/​p5-3).

## `[INLINED]` Source to adapt — FLOW reference ONLY (source: `manus-orchestation-scripts/providers/manus_client.py`)

> Use this ONLY for the Manus API FLOW (endpoints, payload keys, 201/poll/status logic, 2s poll interval, retry backoff). **Do NOT copy its async/`aiohttp` structure or its `ProviderName`/`Message`/`Response` imports** — those are from a DIFFERENT base. Conform the class structure to the work-dir `base.py` + the sibling `deepseek.py`/`gemini.py` instead.

```python
class ManusClient(ProviderClient):
    def __init__(self):
        self.base_url = "https://api.manus.im/v1"
        self.timeout = 300  # 5 minutes for autonomous tasks
        self.retries = 3

    # task description built by joining the messages
    # _execute_task: payload = {"description": <desc>, "autonomy_level": "high", "timeout": self.timeout}
    # _execute_with_retry:
    #   for attempt in range(retries):
    #     POST {base_url}/tasks  (timeout=30) -> expect 201 else raise "API error: {status} - {text}"
    #     task_id = data["task_id"]
    #     return _poll_task_result(task_id)
    #     on Exception: last_error = e; if attempt < retries-1: sleep(2**attempt)
    #   raise last_error
    # _poll_task_result(task_id):
    #   start = now; while now-start < self.timeout:
    #     GET {base_url}/tasks/{task_id}  (timeout=10) -> 200 else raise
    #     if data["status"] == "completed": return output (data.get("output", {}))
    #     if data["status"] == "failed": raise "Task failed: {data['error']}"
    #     sleep(2)
    #   raise "Task timeout"
    # headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
```

## Implementation pointers (binding — enumerated, do not redesign)

1. `class ManusClient(ProviderClient)` in `orchestration/models/_api/clients/manus.py`, conforming to the work-dir `base.py` contract and mirroring `deepseek.py`/`gemini.py` structure (sync, `requests`, retry/backoff, key-in-header).
2. Set `structured_output = False` the same way the siblings set theirs.
3. Implement the chat/entry method (whatever name + signature `base.py` defines) to: build the task `description` from the inbound prompt/messages → `POST /tasks` (retry/backoff) → synchronous poll `GET /tasks/{id}` every 2s until `completed`/`failed`/timeout → return the agent `output` on success (JSON-dump if structured), RAISE on failed/timeout/creation-failure.
4. `requests` only — NO `aiohttp`, NO `asyncio`. Per-request HTTP timeouts: 30s on create, 10s on each poll GET; the OVERALL task timeout (minutes) bounds the poll loop and comes from config (default 300s).
5. Key ONLY in the `Authorization: Bearer` header. No key in any URL/log/exception.
6. Do NOT write `return.json`, do NOT special-case anything in `run.py`, do NOT make a live network call.

---

# TASK (implement verbatim)

```
task_id: p5-1
executor: { model: kimi, variant: default }
reviewer: { model: claude, variant: opus }
allowlist.create: orchestration/models/_api/clients/manus.py   # rbtv repo root
```

# Task p5-1: CREATE the Manus agentic client

## Goal

CREATE `orchestration/models/_api/clients/manus.py` — a synchronous client that submits an autonomous **task** to Manus, polls to completion (up to a long timeout), and returns the agent output. Declares `structured_output: False` (no JSON envelope → the runner raw-dumps generically).

## Execution Flow

### Phase: Execute
1. Implement the entry method as: create task (`POST /tasks` with the prompt as `description`) → poll (`GET /tasks/{id}`) until `completed`/`failed`/timeout → return the agent output.
2. Make it synchronous/one-shot; keep retry/backoff on task creation; honor a long (minutes) timeout.
3. Set `structured_output = False`.

### Phase: Validate
1. `python -c "import ast,io; ast.parse(io.open('orchestration/models/_api/clients/manus.py',encoding='utf-8').read())"` → EXIT 0. (Behavior proven later at p5-checkpoint — no live call now.)

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Manus agentic client | `orchestration/models/_api/clients/manus.py` | Python |

## Validation (run exactly; report each in `validation`)

1. `python -c "import ast,io; ast.parse(io.open('orchestration/models/_api/clients/manus.py',encoding='utf-8').read())"` → EXIT 0.
2. Static self-check (grep your own file, report markers): confirm `class ManusClient` subclasses the base client; `structured_output` is set to `False`; NO `aiohttp` and NO `asyncio` imports; NO `import` of a key and no `api.manus.im` string carrying a key in a URL; `Authorization` header present. Print `STRUCTURE_OK` if all hold, else list what failed.
3. Confirm against the work-dir base: the entry method name + signature MATCH `base.py`'s abstract method (the same one `deepseek.py`/`gemini.py` implement). Print `BASE_CONFORMS_OK` or name the mismatch.

## Commit Rule

Do NOT commit. On validation pass, return the five fields; the conductor reviews (opus) then commits.

## Return Format

Return EXACTLY: `status`, `landed`, `validation`, `concerns`, `open_questions`.
