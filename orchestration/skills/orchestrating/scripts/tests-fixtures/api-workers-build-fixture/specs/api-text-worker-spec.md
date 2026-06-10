# Spec — API Text-Worker (shared runner + chat clients)

> Build paths are relative to the **rbtv repo root** (`3-resources/tools/rbtv/`). Worker work-dir = that repo.

## Goal

The owner can run `python orchestration/models/_api/run.py --provider deepseek --model <id> --prompt-file <f> --output-folder <dir>` and the runner resolves the provider's API key, calls the provider in structured-output (JSON) mode, writes the model's emitted files into `<dir>`, and writes a `return.json` carrying the five-field return — **without the key ever appearing in any prompt, log, or output.**

## Context Snapshot

**Provider base interface** (adapt from `manus-orchestation-scripts/providers/base.py`, made **synchronous** for one-shot CLI use — `requests`/`httpx`, not `aiohttp`):
- `Message{role, content}`, `Response{content, model, usage, raw_response}`, `ProviderConfig{api_key, base_url, timeout, retries}`, `RequestOptions{model, temperature, max_tokens, …}`.
- Abstract `ProviderClient` with `name`, `initialize(config)`, `chat(messages, options) -> Response`. (Drop `call_with_tools`/`stream` — no tool loops, no streaming, per scope.)
- Each client declares `structured_output: True` (chat clients emit the JSON envelope).

**The output envelope** the runner instructs the model to emit (native JSON mode):
```json
{ "files": [ {"path": "<relative>", "content": "<text>"} ], "concerns": [], "open_questions": [] }
```
The **model** supplies `files`/`concerns`/`open_questions`; the **runner** computes `status`, `landed` (paths it actually wrote), `validation` (its own checks).

**`return.json` — the five-field return** (dispatch-wrapper §3 schema): `status` · `landed` · `validation` · `concerns` · `open_questions`. `status` ∈ `DONE`/`DONE_WITH_NOTES`/`BLOCKED`/`NEEDS_CONTEXT`.

**Key discovery** (design §9): walk up from the runner's location (or CWD) to the first ancestor containing `rbtv.json`; read its `env_file` field. Resolve each key **OS-env first** (`DEEPSEEK_API_KEY`/`GEMINI_API_KEY`/`OPENAI_API_KEY`), then the `env_file` fallback.

**Client shapes:** DeepSeek + OpenAI are OpenAI-compatible (JSON/structured-output mode; the kimi client is a close template). Gemini uses its own REST shape + JSON mode + optional search-grounding.

**Dynamic client resolution:** `run.py` imports `clients/{provider}.py` by the `--provider` value — adding a provider never edits `run.py`.

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | `run.py --provider deepseek --model <id> --prompt-file f --output-folder d` with a valid key resolvable | The runner calls DeepSeek in JSON mode, writes each `files[].path` under `d/`, writes `d/return.json` with `status: DONE` and `landed` listing the written paths |
| 2 | The prompt references a `--target-file <path>` | The runner **reads that path and inlines its content** into the API request (an API worker has no filesystem at the model) |
| 3 | The model returns a valid envelope with N files | The runner writes exactly N files under the output folder; `landed` lists them; `validation` reports `finish_reason == stop`, file count, envelope-valid=true |
| 4 | Key resolvable only via the `env_file` (no OS env var) | The runner loads it from the file and proceeds; behavior identical to the OS-env case |

## Edge Cases & Error Behavior

| Condition | Required behavior |
|-----------|-------------------|
| Model ignores the envelope / JSON mode unavailable | **Raw-dump fallback**: write the full raw response as ONE file under the output folder; `status: DONE_WITH_NOTES` + a concern naming the fallback. Output is NEVER dropped |
| `files[].path` contains `..`, an absolute path, or a drive letter | **Sanitize**: reject traversal; reduce to a safe basename / shallow relative under the output folder. A rejected path is noted in `validation` |
| Provider `finish_reason` ≠ `stop` (hit `max_output`) | Flag truncation in `validation`; do NOT silently accept a half file |
| API error after the client's retry/backoff (rate-limit/5xx) | `status: BLOCKED` + the error in `open_questions`; write `return.json` anyway (the conductor must see the block) |
| Key cannot be resolved (no OS env, no `env_file`, or missing entry) | Exit non-zero with a clear stderr message naming the missing key var; **never** echo any key value |
| `--output-folder` does not exist | Create it (parents included) before writing |

## Out of Scope

- Code execution, repo writes outside `--output-folder`, commits, running tests.
- Tool-execution loops (the clients do not execute tool-calls).
- Streaming, async batch use (one-shot synchronous per dispatch; async only if ever needed for intra-dispatch parallel calls).
- Cohere, Manus (Manus is its own spec).

## Test Plan

> Fidelity floor: a **real provider API call** writing **real files** to a **real output folder**; evidence = the written files + `return.json` + captured un-piped exit code, on disk during the exercise.

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | A real DeepSeek call writes the model's files | `run.py --provider deepseek --model <id> --prompt-file <real> --output-folder <dir>` against the live API | Files appear under `<dir>`; `return.json` `status: DONE`, `landed` matches the files on disk | `<dir>/` listing + `return.json` + stdout/exit-code capture |
| 2 | Raw-dump fallback never drops output | Run a prompt the model answers WITHOUT the envelope | One file written with the raw response; `status: DONE_WITH_NOTES` + fallback concern | the written file + `return.json` |
| 3 | Path traversal is neutralized | Feed a crafted envelope with `path: "../escape.txt"` (fixture) through the writer path | File lands inside the output folder, not the parent; `validation` notes the rejection | before/after dir listing + `return.json` |
| 4 | Truncation is flagged, not hidden | Force `max_output` small enough to truncate | `validation` flags truncation; `finish_reason` ≠ stop recorded | `return.json` |
| 5 | The key never leaks | Grep the prompt file, `return.json`, stdout, and any run-log for the key value after a real call | Zero matches | grep-output capture |

## Return Expectations

The runner writes `return.json` with `status`/`landed`/`validation`/`concerns`/`open_questions`. `landed` = the paths actually written (the conductor reconciles file existence + non-emptiness against this list, deliverable-scoped). `validation` = envelope-valid? JSON-parsed? `finish_reason == stop`? file count > 0? The return message/stdout is a hint; the output folder + `return.json` are the truth.
