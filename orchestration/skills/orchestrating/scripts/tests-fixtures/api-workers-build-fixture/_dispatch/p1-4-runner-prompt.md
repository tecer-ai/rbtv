# DISPATCH — p1-4 (kimi executor) — CREATE `_api/run.py` (the shared runner — ARCHITECTURAL CORE)

## You are a NON-REASONING bounded code executor
This is the architectural core — build EXACTLY to the spec below. Every behavior is enumerated; do NOT design or improvise. On genuine ambiguity/contradiction, STOP and return `status: DOUBT_ESCALATED`. Never guess.

## Work-dir
Your work-dir is the rbtv repo root (passed via `--work-dir`). Paths below are relative to it.

## Allowlist — your ENTIRE write universe
- ✚ CREATE: `orchestration/models/_api/run.py`
Create NOTHING else (the `clients/base.py` and `clients/deepseek.py` already exist — do NOT modify them). NEVER write scratch/log files (stray-file ban). Do NOT read other files — the base interface and the full spec are inlined below.

## Forbidden ops
- NO `git`. NO writes outside the allowlist. NO real API call during the build (validation is ast.parse + `--help` only — the real call happens later at the pilot). NO subagents.

## Goal
CREATE `orchestration/models/_api/run.py` — the single CLI entry point the conductor invokes via Bash. It resolves the provider's API key, calls the provider in JSON mode via the dynamically-resolved client, writes the model's emitted envelope files into `--output-folder`, and writes `return.json` (the five-field return). **The key NEVER appears in any prompt, log, stdout, or output file.**

## Implementation Requirements (exact — pre-resolved; build to these)

### CLI
`argparse` with: `--provider` (req), `--model` (req), `--prompt-file` (req), `--output-folder` (req), `--target-file` (optional). `python run.py --help` MUST exit 0 and show these flags.

### Dynamic client resolution (NO per-provider branch — this is an architectural constraint)
- `_API_DIR = pathlib.Path(__file__).resolve().parent`; `sys.path.insert(0, str(_API_DIR))`.
- `import importlib`; `mod = importlib.import_module(f"clients.{args.provider}")`.
- Import the base: `from clients.base import ProviderClient, ProviderConfig, RequestOptions, Message`.
- Find the client class: scan `vars(mod).values()` for a `class` that is `issubclass(obj, ProviderClient)` AND `obj is not ProviderClient`; instantiate it (`client = cls()`). If none found → stderr error + `sys.exit(1)`.
- This MUST work for `deepseek`, `gemini`, `manus`, … with ZERO edits to run.py. Adding a provider = add `clients/{provider}.py` only.

### Key discovery (design §9 — key NEVER printed)
- Walk up from `_API_DIR` through parents to the first dir containing `rbtv.json`. Read it as JSON; get the `env_file` field (may be absent/None).
- Key var name: `KEY = f"{args.provider.upper()}_API_KEY"` (e.g. `DEEPSEEK_API_KEY`).
- Resolve: `os.environ.get(KEY)` FIRST. If falsy and `env_file` present: resolve `env_file` relative to the dir containing `rbtv.json`; parse it as simple `.env` lines (`KEY=VALUE`, skip blanks/`#`, split on the FIRST `=`, strip surrounding quotes/whitespace); use the value for `KEY`.
- If still unresolved → print to **stderr** `f"ERROR: missing API key {KEY} (not in OS env, not in env_file)"` and `sys.exit(1)`. NEVER print the key value anywhere.

### Build the request
- Read `--prompt-file` (UTF-8). If `--target-file` given, read it and append to the user content as: `f"\n\n--- TARGET FILE: {target_path} ---\n{target_content}"` (an API worker has no filesystem at the model — inline it).
- Compose `messages` (list of `Message`):
  - A **system** message instructing the envelope (this string MUST contain the word "JSON" — DeepSeek/OpenAI json_object mode requires it):
    `Respond ONLY with a single JSON object of the exact shape: {"files": [{"path": "<relative path>", "content": "<file text>"}], "concerns": [], "open_questions": []}. Each file you want written goes in "files". Use relative paths only. Do not wrap the JSON in markdown fences.`
  - A **user** message = the prompt-file content (+ the appended target-file block if any).
- `client.initialize(ProviderConfig(api_key=key))`.
- `response = client.chat(messages, RequestOptions(model=args.model))` — wrap in try/except (see Error below).

### Output handling — envelope vs raw-dump (GENERIC, keyed on `client.structured_output`)
- Ensure `--output-folder` exists (`os.makedirs(..., exist_ok=True)`).
- Compute `finish_reason`: `response.raw_response.get("choices", [{}])[0].get("finish_reason")` if `response.raw_response` else `None`.
- **If `client.structured_output` is True** (chat workers): attempt envelope parse:
  - `try: env = json.loads(response.content)` — on success AND `isinstance(env, dict)` AND `"files" in env` AND `isinstance(env["files"], list)`:
    - For each `f` in `env["files"]`: `safe = sanitize_path(f["path"], output_folder)` (see below); write `f["content"]` to `output_folder/safe` (create parent dirs); append `safe` to `landed`. Record any rejected/sanitized path in `validation["rejected_paths"]`.
    - `concerns = env.get("concerns", [])`; `open_questions = env.get("open_questions", [])`.
    - `envelope_valid = True`; `status = "DONE"`.
  - On `json.loads` failure OR not a valid envelope → **raw-dump fallback** (below).
- **If `client.structured_output` is False** (agentic/Manus — generic path): go straight to raw-dump fallback (no envelope expected).
- **Raw-dump fallback:** write `response.content` to `output_folder/raw-output.md` (one file); `landed = ["raw-output.md"]`; `envelope_valid = False`; `status = "DONE_WITH_NOTES"`; append concern `"model did not return the {files:...} envelope — raw response dumped to raw-output.md"`. Output is NEVER dropped.
- **Truncation:** if `finish_reason` is not None and `finish_reason != "stop"` → append to `concerns` a truncation note and set `status = "DONE_WITH_NOTES"` (do not silently accept a half file).

### `sanitize_path(p, output_folder)` (path-traversal neutralization)
- If `p` contains `..`, or `os.path.isabs(p)`, or has a drive (`":" in p` / a Windows drive): reduce to `os.path.basename(p)` (a shallow safe name). Then verify the final resolved path is INSIDE `output_folder` (`os.path.realpath(join)` startswith `os.path.realpath(output_folder)`); if not, fall back to basename under `output_folder`. Return the safe relative path; the caller records the rejection.

### Error behavior
- Any exception from `client.initialize`/`client.chat` (API error after the client's own retries, network, etc.): set `status = "BLOCKED"`, `open_questions = [str(error)]` (do NOT include the key), write `return.json` anyway, then `sys.exit(1)`.
- Missing key (above): stderr + `sys.exit(1)` (no return.json needed — never reached the call).

### Write `return.json` (into `--output-folder`)
`{"status":..., "landed":[...], "validation":{"envelope_valid":bool,"json_parsed":bool,"finish_reason":finish_reason,"file_count":len(landed),"rejected_paths":[...]}, "concerns":[...], "open_questions":[...]}`. Pretty-print (indent=2). For `DONE`/`DONE_WITH_NOTES` → `sys.exit(0)`; for `BLOCKED` → `sys.exit(1)`.
- stdout: print a SHORT one-line summary (status + file count) — never the prompt, never the key, never full content.

### [INLINED] The client interface (from `clients/base.py` — already on disk; shown so you call it correctly)
```python
class ProviderName(str, Enum): DEEPSEEK="deepseek"; GEMINI="gemini"; OPENAI="openai"; MANUS="manus"; KIMI="kimi"; QWEN="qwen"; ANTHROPIC="anthropic"; COHERE="cohere"
@dataclass
class Message: role: str; content: Union[str, List[Dict[str,Any]]]
@dataclass
class Response: content: str; model: Optional[str]=None; usage: Optional[TokenUsage]=None; raw_response: Optional[Dict[str,Any]]=None
@dataclass
class ProviderConfig: api_key: str; base_url: Optional[str]=None; timeout: Optional[int]=None; retries: Optional[int]=None; extra_params: Optional[Dict]=None
@dataclass
class RequestOptions: model: Optional[str]=None; temperature: ...; max_tokens: ...; extra_params: Optional[Dict]=None
class ProviderClient(ABC):
    structured_output: bool = True
    @property @abstractmethod
    def name(self) -> ProviderName: ...
    @abstractmethod
    def initialize(self, config: ProviderConfig) -> None: ...
    @abstractmethod
    def chat(self, messages: List[Message], options: Optional[RequestOptions]=None) -> Response: ...
```
(The DeepSeek client `clients/deepseek.py` already subclasses this — `DeepSeekClient`, `structured_output=True`, puts the full provider JSON in `raw_response`.)

### [INLINED] Spec behavior + edge cases (api-text-worker-spec.md — authoritative)
| # | When | Then |
|---|------|------|
| 1 | valid key + envelope | call in JSON mode, write each file under output-folder, return.json status DONE + landed |
| 2 | `--target-file` given | read it, inline its content into the request |
| 3 | model ignores envelope / not parseable | raw-dump fallback: ONE file, status DONE_WITH_NOTES + concern; never drop |
| 4 | `files[].path` has `..`/abs/drive | sanitize to safe basename under output-folder; note in validation |
| 5 | finish_reason != stop | flag truncation in validation/concerns; don't silently accept |
| 6 | API error after client retries | status BLOCKED + error in open_questions; write return.json anyway; exit 1 |
| 7 | key unresolvable | stderr naming the missing var; exit non-zero; NEVER echo key |
| 8 | output-folder absent | create it (parents) before writing |

## Validation (RUN before returning; capture command + EXIT)
1. `python -c "import ast; ast.parse(open('orchestration/models/_api/run.py').read())"` → EXIT 0.
2. `python orchestration/models/_api/run.py --help` → EXIT 0 and shows `--provider --model --prompt-file --output-folder` (+ `--target-file`).
3. Confirm by read: dynamic import (no per-provider `if provider==` branch); key never printed (no `print(key)` / key in any f-string that is logged); `return.json` written in all envelope/raw/BLOCKED paths.

## Return — provide EXACTLY these five fields as your final message:
- **status:** DONE | DONE_WITH_NOTES | BLOCKED | DOUBT_ESCALATED | NEEDS_CONTEXT
- **landed:** `orchestration/models/_api/run.py` created + one-line description (NO commit)
- **validation:** each command + EXIT + WALL_MS; SKIPPED_COUNT (reasons if >0)
- **concerns:** anything the conductor should weigh
- **open_questions:** unresolved questions
