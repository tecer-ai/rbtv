# DISPATCH — p1-3 (kimi executor) — CREATE `_api/clients/deepseek.py`

## You are a NON-REASONING bounded code executor
Implement EXACTLY the enumerated behavior below. Do NOT design or improvise — every decision is pre-resolved here. On genuine ambiguity/contradiction, STOP and return `status: DOUBT_ESCALATED`. Never guess.

## Work-dir
Your work-dir is the rbtv repo root (passed via `--work-dir`). Paths below are relative to it. Each shell command is an independent subprocess — never rely on `cd`.

## Allowlist — your ENTIRE write universe
- ✚ CREATE: `orchestration/models/_api/clients/deepseek.py`
Create NOTHING else. NEVER write scratch/log/summary files anywhere (stray-file ban). Do NOT read other files — everything is inlined below (the base class you subclass is inlined verbatim).

## Forbidden ops
- NO `git`. NO writes outside the allowlist. NO network calls DURING THE BUILD (you are writing code, not running it — do NOT make a real API call; validation is ast.parse only). NO subagents.

## Goal
CREATE `orchestration/models/_api/clients/deepseek.py` — a **synchronous** DeepSeek client (OpenAI-compatible, JSON/structured-output mode) that subclasses the `ProviderClient` base (inlined below), declares `structured_output = True`, and has retry/backoff on rate-limit/5xx. Adapt the Manus async client (inlined below) to synchronous one-shot use.

## Implementation Requirements (exact — pre-resolved decisions; build to these)
1. **Module docstring** + imports: use `requests` for HTTP (synchronous), `json`, `time` (for backoff), `typing`. NO `aiohttp`, NO `async`/`await`. Import the base types from `.base` (relative import): `Message, ProviderClient, ProviderConfig, ProviderName, RequestOptions, Response, TokenUsage`.
2. **`class DeepSeekClient(ProviderClient)`**:
   - Class attribute **`structured_output: bool = True`** (declare it EXPLICITLY on the subclass — do not rely only on inheritance; the spec wants each client to declare it).
   - `__init__(self)`: set `self.api_key=None`, `self.base_url="https://api.deepseek.com/v1"`, `self.timeout=60`, `self.retries=3`.
   - `@property def name(self) -> ProviderName: return ProviderName.DEEPSEEK`
   - **`def initialize(self, config: ProviderConfig) -> None`** (SYNCHRONOUS): store `self.api_key = config.api_key`; if `config.base_url`/`config.timeout`/`config.retries` set, override. Do NOT make any network call here (no key-validation ping — the runner owns key resolution; the chat call surfaces auth errors).
   - **`def chat(self, messages: List[Message], options: Optional[RequestOptions] = None) -> Response`** — EXACT signature (must match the base; no extra positional params). Behavior:
     a. `options = options or RequestOptions()`.
     b. Build the OpenAI-compatible payload: `model` = `options.model` (REQUIRED — if `options.model` is falsy, raise `ValueError("DeepSeek: options.model is required (pass --model)")`); `messages` = `[{"role": m.role, "content": m.content} for m in messages]`; add `temperature`/`top_p`/`max_tokens`/`stop` from options when set.
     c. **JSON mode:** if `self.structured_output` is True, set `payload["response_format"] = {"type": "json_object"}`. (DeepSeek/OpenAI-compatible JSON mode. The runner's prompt contains the word "JSON" as required.)
     d. **Extensibility:** if `options.extra_params` is a dict, merge it into `payload` (caller can override/add fields).
     e. POST to `f"{self.base_url}/chat/completions"` with headers `{"Content-Type":"application/json","Authorization":f"Bearer {self.api_key}"}`, JSON body = payload, `timeout=self.timeout`, using `requests.post`.
     f. **Retry/backoff:** wrap the POST in a loop up to `self.retries` attempts. Retry ONLY on HTTP 429 or 5xx (`resp.status_code == 429 or 500 <= resp.status_code < 600`) and on `requests.exceptions.RequestException` (network). Backoff `time.sleep(2 ** attempt)` between attempts. On a 4xx that is not 429, do NOT retry — raise immediately. After exhausting retries, raise the last error.
     g. On a non-2xx final response, raise `Exception(f"DeepSeek API error: {status} - {text}")` (the RUNNER catches this and writes status BLOCKED — your job is just to raise cleanly).
     h. On success: parse `data = resp.json()`. Build and return `Response(content=data["choices"][0]["message"].get("content","") , model=data.get("model"), usage=TokenUsage(input_tokens=usage.get("prompt_tokens",0), output_tokens=usage.get("completion_tokens",0), total_tokens=usage.get("total_tokens",0)) if data.get("usage") else None, raw_response=data)`. **`raw_response` MUST be the full `data` json** — the runner reads `raw_response["choices"][0]["finish_reason"]` for its truncation check, so do not strip it.
   - Do NOT implement `call_with_tools`, `stream`, `validate_api_key`, `get_models` (the base no longer declares them; they are out of scope).
3. NO module-level network calls, NO `if __name__` block needed.

### [INLINED] The base class you subclass — `orchestration/models/_api/clients/base.py` (verbatim, do NOT edit it)
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

### [INLINED] Manus async source to adapt (DROP async/aiohttp/tools/stream; keep the payload + parse shape, make sync with `requests`)
```python
# async original (adapt to sync):
class DeepSeekClient(ProviderClient):
    def __init__(self):
        self.api_key=None; self.base_url="https://api.deepseek.com/v1"; self.timeout=60; self.retries=3
    # _build_payload: {"model": options.model or default, "messages": [{role,content}...]}; add max_tokens/temperature/top_p when set
    # _execute_with_retry: for attempt in range(retries): POST {base_url}/chat/completions; if status!=200 raise; data=resp.json(); return _parse_response(data); except: backoff 2**attempt
    # _parse_response: choice=data["choices"][0]; content=choice["message"]["content"]; usage from data["usage"] (prompt_tokens/completion_tokens/total_tokens)
    # _get_headers: {"Content-Type":"application/json","Authorization":f"Bearer {api_key}"}
```
(Note: the Manus version added `thinking={"type":"enabled"}` by default and parsed `tool_calls` — DROP both. No thinking auto-toggle, no tool_calls. Honor `options.extra_params` if a caller wants to add `thinking`.)

## Validation (RUN before returning; capture command + EXIT in `validation`)
1. `python -c "import ast; ast.parse(open('orchestration/models/_api/clients/deepseek.py').read())"` → must EXIT 0.
2. By read/grep confirm: subclass of `ProviderClient`; `structured_output = True` declared; `chat` signature matches the base exactly; uses `requests` (no `aiohttp`/`async`); `response_format` json_object set when structured_output; `raw_response` holds full `data`; retry only on 429/5xx; NO `call_with_tools`/`stream`.

## Return — provide EXACTLY these five fields as your final message:
- **status:** DONE | DONE_WITH_NOTES | BLOCKED | DOUBT_ESCALATED | NEEDS_CONTEXT
- **landed:** `orchestration/models/_api/clients/deepseek.py` created + one-line description (NO commit)
- **validation:** each command run + EXIT + WALL_MS; SKIPPED_COUNT (with reasons if >0)
- **concerns:** anything the conductor should weigh (e.g., the real DeepSeek model id to pass via --model at the pilot, if you know it)
- **open_questions:** unresolved questions
