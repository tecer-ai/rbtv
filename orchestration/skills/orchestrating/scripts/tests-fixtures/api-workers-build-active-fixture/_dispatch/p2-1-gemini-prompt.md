# DISPATCH — p2-1 (kimi executor) — CREATE `_api/clients/gemini.py`

## You are a NON-REASONING bounded code executor
Implement EXACTLY the enumerated behavior below. Do NOT design or improvise — every decision is pre-resolved here. On genuine ambiguity/contradiction, STOP and return `status: DOUBT_ESCALATED`. Never guess.

## Work-dir
Your work-dir is the rbtv repo root (passed via `--work-dir`). Paths below are relative to it. Each shell command is an independent subprocess — never rely on `cd`.

## Allowlist — your ENTIRE write universe
- ✚ CREATE: `orchestration/models/_api/clients/gemini.py`
Create NOTHING else. NEVER write scratch/log/summary files anywhere (stray-file ban). Do NOT read other files — everything is inlined below (the base class you subclass is inlined verbatim; the source client to adapt is inlined verbatim).

## Forbidden ops
- NO `git` (no commit, no add). NO writes outside the allowlist. NO network calls DURING THE BUILD (you are writing code, not running it — do NOT make a real API call; validation is `ast.parse` only). NO subagents.

## Goal
CREATE `orchestration/models/_api/clients/gemini.py` — a **synchronous** Google Gemini client that subclasses the `ProviderClient` base (inlined below), declares `structured_output = True`, talks Gemini's own REST shape (`:generateContent`) with **JSON mode**, exposes **optional search-grounding**, has retry/backoff on 429/5xx, and **normalizes two things so the shared runner stays provider-agnostic (the runner MUST NOT be edited): the key goes in a header (never the URL), and the Gemini `finishReason` is mapped into the OpenAI-shaped `raw_response["choices"][0]["finish_reason"]` the runner reads.** Adapt the inlined async source to synchronous one-shot use with `requests`.

## Why these two normalizations are load-bearing (context — the runner you must fit, NOT edit)
The shared runner (`orchestration/models/_api/run.py`, already built, DO NOT TOUCH) consumes your `Response` like this:
- It reads the completion-stop signal as `response.raw_response.get("choices", [{}])[0].get("finish_reason")` and flags truncation when that value is present and `!= "stop"`. Gemini natively returns `candidates[0].finishReason` = `"STOP"` / `"MAX_TOKENS"` (uppercase, different key). If you return Gemini's native shape, the runner reads `None` and SILENTLY SKIPS the truncation guard. So you MUST inject an OpenAI-compat `choices` shim into `raw_response` (requirement 6).
- On any exception it puts `str(exc)` into the output `return.json`. The source client puts the API key in the URL (`?key=...`), so a failing request would leak the key into a traceback/return. So you MUST authenticate with the `x-goog-api-key` HEADER and keep the key out of the URL entirely (requirement 5).

## Implementation Requirements (exact — pre-resolved decisions; build to these; they OVERRIDE the inlined source wherever they differ)

1. **Module docstring + imports:** use `requests` (synchronous HTTP), `json`, `time` (backoff), `typing`. **NO `aiohttp`, NO `asyncio`, NO `async`/`await`.** Import the base types from `.base` (relative import): `Message, ProviderClient, ProviderConfig, ProviderName, RequestOptions, Response, TokenUsage`. **Do NOT import `ToolCall` / `ToolDefinition`** — the base does NOT export them; drop all tool-definition support.

2. **`class GeminiClient(ProviderClient)`:**
   - Class attribute **`structured_output: bool = True`** (declare EXPLICITLY on the subclass).
   - `__init__(self)`: `self.api_key=None`, `self.base_url="https://generativelanguage.googleapis.com/v1beta"`, `self.timeout=60`, `self.retries=3`. NO aiohttp session, no other state.
   - `@property def name(self) -> ProviderName: return ProviderName.GEMINI`
   - **`def initialize(self, config: ProviderConfig) -> None`** (SYNCHRONOUS): store `self.api_key = config.api_key`; if `config.base_url`/`config.timeout`/`config.retries` are set, override. **Make NO network call and NO key-validation ping** (drop the source's `validate_api_key` entirely — the runner owns key resolution; the chat call surfaces auth errors).
   - **`def chat(self, messages: List[Message], options: Optional[RequestOptions] = None) -> Response`** — EXACT signature (must match the base; no extra positional params).

3. **`def _build_payload(self, messages, options) -> Dict[str, Any]`:**
   - **System handling (Gemini has NO `system` role inside `contents`):** collect every message whose `role == "system"`; if any exist, join their text and set `payload["systemInstruction"] = {"parts": [{"text": "<joined system text>"}]}`.
   - **`contents`:** for each NON-system message append `{"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.content}]}`.
   - **`generationConfig`:** start `{"maxOutputTokens": options.max_tokens or 4096}`; add `"temperature"` (from `options.temperature`), `"topP"` (from `options.top_p`), `"stopSequences"` (from `options.stop_sequences`) ONLY when each is not None. **Do NOT reference `options.top_k`** — the base `RequestOptions` has no `top_k` field.
   - **JSON mode vs grounding — MUTUALLY EXCLUSIVE (Gemini rejects `responseMimeType: application/json` together with the `google_search` tool):**
     - Compute `grounding = bool(options.extra_params.get("grounding"))` when `options.extra_params` is a dict, else `False`.
     - If `grounding` is True: set `payload["tools"] = [{"google_search": {}}]` and do **NOT** set `responseMimeType` (the response will be grounded text; the runner's raw-dump fallback handles a non-JSON answer).
     - Else (default): set `payload["generationConfig"]["responseMimeType"] = "application/json"` (this is Gemini's structured-output / JSON mode — the equivalent of OpenAI's `response_format=json_object`; it makes the model emit the `{files:...}` envelope the runner parses).
   - **extra_params passthrough:** if `options.extra_params` is a dict, merge every key EXCEPT `"grounding"` into the top-level `payload` (caller extensibility, e.g. `safetySettings`).
   - Return `payload`.

4. **`chat`:** `options = options or RequestOptions()`. If `options.model` is falsy, `raise ValueError("Gemini: options.model is required (pass --model)")`. Build the payload via `_build_payload(messages, options)`; return `self._execute_with_retry(payload, options.model)`.

5. **`def _execute_with_retry(self, payload, model) -> Response`:**
   - `url = f"{self.base_url}/models/{model}:generateContent"` — **the key MUST NOT appear in this URL.**
   - **KEY SAFETY (load-bearing — the no-leak criterion): authenticate via the HEADER `x-goog-api-key`.** Headers = `{"Content-Type": "application/json", "x-goog-api-key": self.api_key}`. The source's `?key={api_key}` URL form is FORBIDDEN.
   - Retry loop up to `self.retries` attempts: `resp = requests.post(url, headers=<above>, json=payload, timeout=self.timeout)`.
     - Retry ONLY on HTTP 429 or 5xx (`resp.status_code == 429 or 500 <= resp.status_code < 600`) and on `requests.exceptions.RequestException`. Backoff `time.sleep(2 ** attempt)` between attempts. On a 4xx that is not 429, do NOT retry — raise immediately. After exhausting retries, raise the last error.
   - On a non-2xx final response: `raise Exception(f"Gemini API error: {resp.status_code} - {resp.text}")` (NO key in the message — the key lives only in the header, which you never echo).
   - On success: `data = resp.json()`; return `self._parse_response(data, model)`.

6. **`def _parse_response(self, data, model) -> Response`:**
   - **content:** concatenate the text of every part in `data["candidates"][0]["content"]["parts"]` that has a `"text"` key (guard all lookups with `.get(...)`/defaults; default to `""`).
   - **usage:** if `data.get("usageMetadata")` is present, build `TokenUsage(input_tokens=md.get("promptTokenCount",0), output_tokens=md.get("candidatesTokenCount",0), total_tokens=md.get("totalTokenCount",0))`; else `None`.
   - **finish_reason normalization (load-bearing):**
     - `gem_fr = (data.get("candidates") or [{}])[0].get("finishReason")`.
     - Map to an OpenAI-style lowercase value: `"STOP" -> "stop"`, `"MAX_TOKENS" -> "length"`, any other non-null value -> `gem_fr.lower()` (so e.g. `SAFETY -> "safety"`, which the runner correctly treats as `!= "stop"` and flags), `None -> None`.
     - Build `raw_response = dict(data)` (shallow copy of the full Gemini response), then **inject the shim**: `raw_response["choices"] = [{"finish_reason": <mapped value>}]`. This preserves every Gemini field AND satisfies the runner's `raw_response["choices"][0]["finish_reason"]` extraction WITHOUT any `run.py` edit.
   - Return `Response(content=<content>, model=data.get("modelVersion") or model, usage=<usage-or-None>, raw_response=raw_response)`.

7. Do NOT implement `call_with_tools`, `stream`, `validate_api_key`, `get_models`, `close`, `__aenter__`, `__aexit__` — all dropped (the base no longer declares tool/stream surfaces). NO module-level network calls. NO `if __name__` block needed.

### [INLINED] The base class you subclass — `orchestration/models/_api/clients/base.py` (verbatim; do NOT edit it, do NOT re-create it)
```python
"""Synchronous provider base for the API runner."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

class ProviderName(str, Enum):
    DEEPSEEK = "deepseek"; GEMINI = "gemini"; OPENAI = "openai"; MANUS = "manus"
    KIMI = "kimi"; QWEN = "qwen"; ANTHROPIC = "anthropic"; COHERE = "cohere"

@dataclass
class Message:
    role: str
    content: Union[str, List[Dict[str, Any]]]

@dataclass
class TokenUsage:
    input_tokens: int; output_tokens: int; total_tokens: int

@dataclass
class Response:
    content: str
    model: Optional[str] = None
    usage: Optional[TokenUsage] = None
    raw_response: Optional[Dict[str, Any]] = None

@dataclass
class ProviderConfig:
    api_key: str
    base_url: Optional[str] = None
    timeout: Optional[int] = None
    retries: Optional[int] = None
    extra_params: Optional[Dict[str, Any]] = None

@dataclass
class RequestOptions:
    model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    extra_params: Optional[Dict[str, Any]] = None

class ProviderClient(ABC):
    structured_output: bool = True
    @property
    @abstractmethod
    def name(self) -> ProviderName: ...
    @abstractmethod
    def initialize(self, config: ProviderConfig) -> None: ...
    @abstractmethod
    def chat(self, messages: List[Message], options: Optional[RequestOptions] = None) -> Response: ...
```

### [INLINED] Gemini async source to adapt (keep the payload/parse SHAPES; DROP async/aiohttp/tools/stream/validate/get_models/close; apply the Implementation Requirements above where they differ — they WIN)
```python
class GeminiClient(ProviderClient):
    def __init__(self):
        self.api_key=None
        self.base_url="https://generativelanguage.googleapis.com/v1beta"
        self.timeout=60; self.retries=3
    # name -> ProviderName.GEMINI
    # _build_payload: contents=[{"role":"model" if assistant else "user","parts":[{"text":content}]}];
    #   generationConfig={"maxOutputTokens": max_tokens or 4096}; +temperature/topP/stopSequences when set.
    #   (SOURCE PUT NO systemInstruction, NO responseMimeType, NO grounding — ADD them per reqs 3.)
    # _execute_with_retry: POST f"{base_url}/models/{model}:generateContent"  (SOURCE USED ?key= — FORBIDDEN; use x-goog-api-key header per req 5);
    #   default model "gemini-3.5-flash" (NOT needed — req 4 requires options.model); retry/backoff 2**attempt.
    # _parse_response: candidate=data["candidates"][0]; content=join parts[*]["text"];
    #   usage from data["usageMetadata"] (promptTokenCount/candidatesTokenCount/totalTokenCount);
    #   (SOURCE built tool_calls + raw_response=data — DROP tool_calls; raw_response MUST get the choices shim per req 6.)
```
(Note: the source defaulted the model and authed via `?key=`, parsed `tool_calls`, and created an aiohttp session in `initialize` + validated the key — DROP all of that. No tool_calls, no streaming, no key in URL, no validation ping, synchronous `requests` only.)

## Validation (RUN before returning; capture command + EXIT + WALL_MS in `validation`)
1. `python -c "import ast; ast.parse(open('orchestration/models/_api/clients/gemini.py').read())"` → must EXIT 0.
2. By read/grep confirm ALL of: subclass of `ProviderClient`; `structured_output = True` declared; `chat` signature matches the base exactly; uses `requests` (no `aiohttp`/`async`/`asyncio`); endpoint is `:generateContent` with the key in the `x-goog-api-key` HEADER and **no `key=` substring anywhere in the file**; `responseMimeType="application/json"` set in the default (non-grounding) path; `tools=[{"google_search": {}}]` set only when grounding; `systemInstruction` built from system-role messages; `raw_response["choices"]=[{"finish_reason": ...}]` shim present with the STOP->stop / MAX_TOKENS->length mapping; retry only on 429/5xx; NO `call_with_tools`/`stream`/`validate_api_key`/`get_models`; no `top_k` reference.
   - Quick self-grep: `python -c "s=open('orchestration/models/_api/clients/gemini.py').read(); assert 'key=' not in s, 'KEY IN URL'; assert 'x-goog-api-key' in s; assert 'choices' in s; assert 'responseMimeType' in s; print('SELFCHECK_OK')"` → must print SELFCHECK_OK, EXIT 0.

## Return — provide EXACTLY these five fields as your final message:
- **status:** DONE | DONE_WITH_NOTES | BLOCKED | DOUBT_ESCALATED | NEEDS_CONTEXT
- **landed:** `orchestration/models/_api/clients/gemini.py` created + one-line description (NO commit)
- **validation:** each command run + EXIT + WALL_MS; SKIPPED_COUNT (with reasons if >0)
- **concerns:** anything the conductor should weigh (e.g., real Gemini model id to pass via --model at the pilot, if you know it; any JSON-mode+grounding interaction note)
- **open_questions:** unresolved questions
