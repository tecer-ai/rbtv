# DISPATCH — p5-3 (kimi/default, bounded code)

You are a **non-reasoning bounded-code executor**. Implement the enumerated changes in the TASK below EXACTLY. Do NOT reason about intent, redesign, generalize, or "fill in blanks" — every change is pre-resolved. A decision left to you is a task bug: HALT and return `DOUBT_ESCALATED` with the precise question.

## Binding obligations (held to ALL on return)
- **Work-dir:** the rbtv repo root (passed via `--work-dir`). Allowlist paths are repo-relative.
- **Rule-loading:** inspect the work-dir for `.agents/behavior-rules/`; this repo has `AGENTS.md` at root and NO `.agents/behavior-rules/` — read `AGENTS.md`, then proceed.
- **Allowlist (MODIFY ONLY this one file):** `orchestration/models/_api/run.py`. You MAY READ (not modify): `orchestration/models/_api/clients/base.py`, `clients/manus.py`, `clients/gemini.py`. Any other create/modify/delete is an out-of-allowlist write the conductor will flag.
- **No commit:** do NOT `git commit`/`add`/push/reset/amend. Leave run.py modified-uncommitted; the conductor commits after opus review.
- **No exploration beyond the named files.** Do NOT read the plan, other task files, or `decisions.md`.
- **Swarm disabled;** no subagents. **No network/API calls** (do NOT run a live model call — behavior is proven at p5-checkpoint).
- **Forbidden-ops are exhaustive:** no writes outside the work-dir, no push, no destructive git ops. NEVER read/print/echo any API key value.
- **Evidence on disk:** capture your validation command outputs; cite them in `validation`.

## Return — EXACTLY these five named fields (no rename, no extra, no prose-only)
- `status`: `DONE` · `DONE_WITH_NOTES` · `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT`
- `landed`: `run.py` modified (you do NOT commit, so no hash)
- `validation`: each command + `EXIT` + `WALL_MS` + `SKIPPED_COUNT` (0 if none; every skip needs a reason)
- `concerns` · `open_questions`

The conductor reconciles your message against `git diff` on disk — the message is a HINT, disk is truth.

## Worker-facing decisions in force (inlined — do NOT re-read decisions.md)
- **The `structured_output` → raw-dump routing ALREADY EXISTS and WORKS** (verified): `run.py` line ~228 `if client.structured_output:` skips the envelope parse for `False` clients, and line ~256 `if not envelope_valid:` raw-dumps them to `raw-output.md` with `DONE_WITH_NOTES`. Manus (`structured_output = False`) already flows through it correctly. **Do NOT add, duplicate, or modify this routing.** Your change is ONLY the two new flags below.
- **GENERIC, never provider-specific (architectural rule):** adding a provider NEVER puts a provider-name (`manus`/`deepseek`/`gemini`) branch in `run.py`. The two new flags are driven by argparse + the client's own fields, never by the provider name. A provider-name special-case in the dispatch logic is a hard review failure.
- **ADX-1 (grounding pass-through):** `gemini.py` already reads `RequestOptions.extra_params["grounding"]` to enable search-grounding (grounded responses come back non-JSON → the EXISTING raw-dump fallback handles them — no extra handling needed). You only wire the flag → `extra_params`.

## Reference — files to READ in your work-dir
`[FULL READ]` `orchestration/models/_api/run.py` (the file you edit — note `_build_parser()` ~line 108, the `args = parser.parse_args()` in `main()` ~line 120, `client.initialize(ProviderConfig(api_key=key))` ~line 196, `client.chat(messages, RequestOptions(model=args.model))` ~line 197). `clients/base.py` confirms `ProviderConfig(api_key, base_url, timeout, retries, extra_params)` and `RequestOptions(model, …, extra_params)` both accept the fields you set.

## Implementation Requirements (exact — implement verbatim, do not redesign)

### A. `_build_parser()` — add THREE arguments after the existing `--target-file` line
```python
parser.add_argument("--timeout", type=int, default=None,
    help="Per-call timeout in seconds passed to the client (e.g. minutes-scale for the Manus agentic worker). Omit to use the client's own default.")
parser.add_argument("--grounded", action="store_true",
    help="Enable web/search grounding via extra_params['grounding']=True (gemini.py reads this). Generic — never provider-specific.")
parser.add_argument("--extra-params", type=str, default=None,
    help="A JSON object merged into RequestOptions.extra_params (advanced pass-through).")
```

### B. In `main()`, AFTER `args = parser.parse_args()` (and before the client call), build the extra_params dict
```python
extra_params: Dict[str, Any] = {}
if args.grounded:
    extra_params["grounding"] = True
if args.extra_params:
    try:
        parsed = json.loads(args.extra_params)
    except (json.JSONDecodeError, TypeError):
        print("ERROR: --extra-params must be a JSON object", file=sys.stderr)
        sys.exit(1)
    if not isinstance(parsed, dict):
        print("ERROR: --extra-params must be a JSON object", file=sys.stderr)
        sys.exit(1)
    extra_params.update(parsed)
extra_params_arg: Optional[Dict[str, Any]] = extra_params or None
```
(Place this block where `args` is available and before `client.initialize(...)`/`client.chat(...)` — e.g. right after dynamic client resolution, or immediately before the `try: client.initialize(...)` call. `json`, `sys`, `Dict`, `Any`, `Optional` are already imported.)

### C. Pass the timeout to `ProviderConfig` — change the existing line
`client.initialize(ProviderConfig(api_key=key))`  →  `client.initialize(ProviderConfig(api_key=key, timeout=args.timeout))`
(When `--timeout` is omitted, `args.timeout` is `None`, and the client keeps its own default — verified in each client's `initialize`. So this is safe for every provider.)

### D. Pass extra_params to `RequestOptions` — change the existing line
`response = client.chat(messages, RequestOptions(model=args.model))`  →  `response = client.chat(messages, RequestOptions(model=args.model, extra_params=extra_params_arg))`

### E. DO NOT touch anything else
No change to the `structured_output`/envelope/raw-dump/sanitize_path/truncation/return.json logic. NO provider-name branch. The diff must be ONLY the three new argparse args + the extra_params build block + the two single-line changes (C, D).

---

# TASK (implement verbatim)

```
task_id: p5-3
executor: { model: kimi, variant: default }
reviewer: { model: claude, variant: opus }
allowlist.modify: orchestration/models/_api/run.py   # SHARED FILE (created p1-4; this is the only later edit)
```

# Task p5-3: UPDATE run.py — agentic-profile handling (minimal)

## Goal
UPDATE `orchestration/models/_api/run.py` to handle the agentic profile generically: a **per-client timeout** (Manus needs minutes) and reading the client's `structured_output` flag to route `False` clients through the **existing raw-dump path**. NO Manus-specific branch — the flag drives it. (NOTE: the `structured_output`→raw-dump routing ALREADY EXISTS and works — confirm it, do NOT re-add it. Your change is the timeout + the ADX-1 grounding flags.)

## ADX-1 (per D-exec-6) — ALSO wire a generic grounding / extra-params pass-through
ADD a **generic** grounding pass-through: a `--grounded` flag (and `--extra-params <json>`) that populates `RequestOptions.extra_params` (e.g. `{"grounding": true}`) on the `client.chat(...)` call. `gemini.py` ALREADY reads `extra_params["grounding"]`. GENERIC (flag → `extra_params`), NEVER provider-specific.

## Validation (run exactly; report each in `validation`)
1. `python -c "import ast,io; ast.parse(io.open('orchestration/models/_api/run.py',encoding='utf-8').read()); print('AST_OK')"` → EXIT 0.
2. `python orchestration/models/_api/run.py --help` → EXIT 0 and output contains `--timeout`, `--grounded`, `--extra-params`.
3. `git diff orchestration/models/_api/run.py` → shows ONLY: the 3 new argparse args + the extra_params build block + the `ProviderConfig(..., timeout=args.timeout)` change + the `RequestOptions(..., extra_params=extra_params_arg)` change. Report a one-line confirmation that the `structured_output`/envelope/raw-dump block is UNCHANGED and there is NO provider-name special-case. (Behavior proven at p5-checkpoint.)

## Commit Rule
Do NOT commit. On validation pass, return the five fields; the conductor reviews (opus) then commits.

## Return Format
Return EXACTLY: `status`, `landed`, `validation`, `concerns`, `open_questions`.
