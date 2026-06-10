# DISPATCH — p1-2 (kimi executor) — CREATE `_api/clients/base.py`

## You are a NON-REASONING bounded code executor
Implement EXACTLY the enumerated behavior below. Do NOT design, decide, interpret intent, or "fill in blanks" — every decision is pre-resolved here. If you hit genuine ambiguity or a contradiction, STOP and return `status: DOUBT_ESCALATED` with the precise question. Never guess.

## Work-dir
Your work-dir is the rbtv repo root (passed via `--work-dir`). All paths below are relative to it. Each shell command is an independent subprocess — never rely on `cd`.

## Allowlist — your ENTIRE write universe
- ✚ CREATE: `orchestration/models/_api/clients/base.py`

Create NOTHING else. NEVER write scratch notes, logs, or summary files anywhere in the repo (stray-file ban — the post-run diff treats any such file as an out-of-allowlist write). Do NOT read other task files, the plan, or `decisions.md` — everything you need is inlined below.

## Forbidden ops
- NO `git` operations (no commit, push, reset). The conductor commits separately.
- NO writes outside the allowlist. NO network calls. NO subagents (swarm disabled).

## Goal
CREATE `orchestration/models/_api/clients/base.py` — the **synchronous** provider abstraction the shared runner (`run.py`) and every API client (DeepSeek, Gemini, Manus) build on. Adapt from the Manus async `base.py` (inlined below): make it **one-shot / synchronous** (`requests`/`httpx`, NEVER `aiohttp`), DROP the tool-loop and streaming methods, and ADD a `structured_output: bool` attribute.

## Implementation Requirements (exact — build to these, nothing more)

1. **Module docstring**: one line describing it as the synchronous provider base for the API runner.
2. **Imports**: standard library + `typing` + `abc` + `dataclasses` + `enum` ONLY. NO `aiohttp`, NO `async`/`await`, NO `AsyncIterator`.
3. **`ProviderName(str, Enum)`** — KEEP it, with members: `DEEPSEEK = "deepseek"`, `GEMINI = "gemini"`, `OPENAI = "openai"`, `MANUS = "manus"`, `KIMI = "kimi"`, `QWEN = "qwen"`, `ANTHROPIC = "anthropic"`, `COHERE = "cohere"`. (Harmless roster; `name` returns one of these.)
4. **Dataclasses (keep these four + TokenUsage):**
   - `Message{ role: str, content: Union[str, List[Dict[str, Any]]] }`
   - `TokenUsage{ input_tokens: int, output_tokens: int, total_tokens: int }`
   - `Response{ content: str, model: Optional[str] = None, usage: Optional[TokenUsage] = None, raw_response: Optional[Dict[str, Any]] = None }`  ← NOTE: DROP the `tool_calls` field (no tool loops).
   - `ProviderConfig{ api_key: str, base_url: Optional[str] = None, timeout: Optional[int] = None, retries: Optional[int] = None, extra_params: Optional[Dict[str, Any]] = None }`
   - `RequestOptions{ model: Optional[str] = None, temperature: Optional[float] = None, top_p: Optional[float] = None, max_tokens: Optional[int] = None, stop_sequences: Optional[List[str]] = None, extra_params: Optional[Dict[str, Any]] = None }`
5. **DROP entirely** (do NOT include): `ToolDefinition`, `ToolCall` dataclasses; `call_with_tools`, `stream` methods; `validate_api_key`, `get_models` abstract methods. (No tool surface, no streaming, no model-listing — out of scope.)
6. **`class ProviderClient(ABC)`** — the abstract base, with EXACTLY this abstract surface (all SYNCHRONOUS — `def`, never `async def`):
   - class attribute `structured_output: bool = True`  ← chat clients keep True; the future Manus client sets it False. This attribute is how the runner's raw-dump path is selected generically.
   - `@property @abstractmethod def name(self) -> ProviderName: ...`
   - `@abstractmethod def initialize(self, config: ProviderConfig) -> None: ...`
   - `@abstractmethod def chat(self, messages: List[Message], options: Optional[RequestOptions] = None) -> Response: ...`
   - No other abstract methods.

### [INLINED] Authoritative contract — api-text-worker-spec.md → "Context Snapshot" (source: api-workers-build/specs/api-text-worker-spec.md)
> Provider base interface (adapt from the Manus `base.py`, made **synchronous** for one-shot CLI use — `requests`/`httpx`, not `aiohttp`):
> - `Message{role, content}`, `Response{content, model, usage, raw_response}`, `ProviderConfig{api_key, base_url, timeout, retries}`, `RequestOptions{model, temperature, max_tokens, …}`.
> - Abstract `ProviderClient` with `name`, `initialize(config)`, `chat(messages, options) -> Response`. (Drop `call_with_tools`/`stream` — no tool loops, no streaming.)
> - Each client declares `structured_output: True` (chat clients emit the JSON envelope).

### [INLINED] Source to adapt — manus-orchestation-scripts/providers/base.py (ASYNC original — convert to sync, trim per requirements above)
```python
"""
Base classes and types for all AI providers.
Provides common interfaces and data structures.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from enum import Enum


class ProviderName(str, Enum):
    """Enum of all supported providers."""
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    KIMI = "kimi"
    GEMINI = "gemini"
    OPENAI = "openai"
    COHERE = "cohere"
    MANUS = "manus"
    QWEN = "qwen"


@dataclass
class Message:
    """Standard message format."""
    role: str  # "user", "assistant", "system"
    content: Union[str, List[Dict[str, Any]]]


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass
class Response:
    content: str
    model: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
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
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    thinking_enabled: Optional[bool] = None
    reasoning_effort: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None


class ProviderClient(ABC):
    @property
    @abstractmethod
    def name(self) -> ProviderName: ...
    @abstractmethod
    async def initialize(self, config: ProviderConfig) -> None: ...
    @abstractmethod
    async def validate_api_key(self) -> bool: ...
    @abstractmethod
    async def get_models(self) -> List[str]: ...
    @abstractmethod
    async def chat(self, messages, options=None) -> Response: ...
    @abstractmethod
    async def call_with_tools(self, messages, tools, options=None) -> Response: ...
    @abstractmethod
    async def stream(self, messages, options=None): ...
```

## Validation (RUN before returning; capture each command + EXIT code in the `validation` field)
1. `python -c "import ast; ast.parse(open('orchestration/models/_api/clients/base.py').read())"` → must EXIT 0.
2. Confirm by grep/read that the file contains NO `async`, NO `await`, NO `aiohttp`, NO `AsyncIterator`; that `structured_output` is a class attribute on `ProviderClient`; and that abstract `name` / `initialize` / `chat` are present and `call_with_tools` / `stream` are ABSENT.

## Return — provide EXACTLY these five fields as your final message:
- **status:** DONE | DONE_WITH_NOTES | BLOCKED | DOUBT_ESCALATED | NEEDS_CONTEXT
- **landed:** `orchestration/models/_api/clients/base.py` created + one-line description (NO commit — conductor commits)
- **validation:** each command run + its EXIT code + WALL_MS; `SKIPPED_COUNT` (0, or >0 with a per-skip reason)
- **concerns:** anything the conductor should weigh
- **open_questions:** unresolved questions (the precise doubt, if escalated)
