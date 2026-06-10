# DISPATCH — p4-4 (kimi/default, bounded code)

You are a **non-reasoning bounded-code executor**. Implement the enumerated behavior in the TASK below EXACTLY. Do NOT reason about intent, redesign, generalize, or "fill in blanks" — every interface and edge case is pre-resolved. A decision left to you is a task bug: HALT and return `DOUBT_ESCALATED` with the precise question rather than guessing.

## Binding obligations (you are held to ALL of these on return)

- **Work-dir:** the rbtv repo root (passed via `--work-dir`). All allowlist paths are repo-relative.
- **Rule-loading:** Before any other action, inspect the work-dir for a `.agents/behavior-rules/` directory; if present, read your `AGENTS.md` + every file under it and treat them as binding. (This repo has `AGENTS.md` at root and no `.agents/behavior-rules/` — read `AGENTS.md`, then proceed.)
- **Allowlist (modify ONLY these two files):** `admin/install/installer/state.py`, `admin/install/installer/cli.py`. You MAY read `state.py`, `cli.py`, `tui.py`. Any create/modify/delete outside the allowlist is an out-of-allowlist write the conductor will flag — do not do it. No scratch/log/summary files anywhere.
- **No commit:** `commit_policy: none`. Do NOT `git commit`, `git add`, push, reset, or amend. The conductor commits after review.
- **No exploration beyond the inlined context:** everything you need is inlined in the task. Do NOT read the plan, other task files, or `decisions.md` at runtime.
- **Swarm disabled:** do NOT launch subagents.
- **Forbidden-ops are exhaustive:** no writes outside the work-dir, no push, no destructive git ops, no network/API calls. NEVER read, store, print, or echo any API key VALUE — this task touches only the env_file PATH.
- **Evidence on disk:** capture your validation command outputs; cite them in the `validation` field.

## Return — EXACTLY these five named fields (no rename, no extra, no prose-only)

- `status`: one of `DONE` · `DONE_WITH_NOTES` · `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT`
- `landed`: files modified (paths); you do NOT commit, so no hash
- `validation`: each command run + its `EXIT` + `WALL_MS` + `SKIPPED_COUNT` (0 if none; every skip needs a reason)
- `concerns`: anything the conductor should weigh
- `open_questions`: unresolved questions (the halting question for DOUBT_ESCALATED/NEEDS_CONTEXT)

The conductor reconciles your message against `git status`/`git diff` on disk — the message is a HINT, disk is truth.

## Worker-facing decisions in force (pointer: `1-projects/rbtv-evolution/orchestration/api-workers/api-workers-build/decisions.md`)

Two load-bearing decisions this task implements (inlined — do not re-read):

- **D-exec-1:** `env_file` was pre-seeded into vault-root `rbtv.json` at intake; p4-4 must be **idempotent** — detect an already-present `env_file` and NOT duplicate, overwrite-without-confirm, or error on it.
- **D-exec-7 (CONFIRMED load-bearing):** a parallel `install.py` regenerated `rbtv.json` and DROPPED `env_file`, breaking ALL file-based key resolution (it broke the Gemini pilot). p4-4 MUST be idempotent AND **PRESERVE an existing `env_file` across re-installs (detect-and-keep; NEVER clobber).**

---

# TASK (implement verbatim)

# Task p4-4: installer records + PRESERVES the API-key `env_file` (idempotent)

allowed_workdir: `3-resources/tools/rbtv` (rbtv repo root — allowlist paths repo-relative)
allowlist (modify): `admin/install/installer/state.py`, `admin/install/installer/cli.py`
commit_policy: none · doubt_policy: halt · swarm_policy: disabled

## Goal

Make the installer (1) **preserve** an existing `env_file` field in `rbtv.json` across re-installs, and (2) **record** an `env_file` PATH supplied via a new `--env-file` flag (scripted) or an optional interactive prompt (orchestration + interactive only). The installer records the PATH only — it NEVER reads, stores, or echoes any key value.

## Context Snapshot (all inlined — do NOT explore other files)

**`state.py:write_state()` today** (note the `model_mirror` carry-forward you will mirror for `env_file`):

```python
def write_state(
    target_root: Path,
    *,
    rbtv_version: str,
    rbtv_relative: str,
    modules: tuple[str, ...],
    installed_files: list[str],
    excluded_components: set[str] | None = None,
    model_packages: list[str] | None = None,
    model_mirror: dict[str, Any] | None = None,
) -> Path:
    path = state_path(target_root)

    # Carry forward any existing model_mirror if the caller does not supply one.
    if model_mirror is None:
        existing = read_state(target_root)
        if existing is not None and "model_mirror" in existing:
            model_mirror = existing["model_mirror"]

    payload: dict[str, Any] = {
        "rbtv_version": rbtv_version,
        "installed_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "rbtv_path": rbtv_relative,
        "modules": list(modules),
        "installed_files": sorted(installed_files),
    }
    if excluded_components:
        payload["excluded_components"] = sorted(excluded_components)
    if model_packages is not None:
        payload["model_packages"] = list(model_packages)
    if model_mirror is not None:
        payload["model_mirror"] = model_mirror
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
```

**`cli.py` relevant points:** module constant `ORCHESTRATION_MODULE = "orchestration"`; argparse args added in `main()`; `existing_state = read_state(target_root)` (~line 571); `chosen_modules` resolved (~line 597); `_resolve_model_packages(...)` block ends (~line 621); final `write_state(...)` (~line 793) passes everything EXCEPT `env_file`.

**`tui.py:text_input` (keyword-only `default`/`validator`):**
```python
def text_input(prompt: str, *, default: str = "", validator: Callable[[str], str | None] | None = None) -> str
```
Import lazily: `from .tui import text_input`.

## Implementation Requirements (exact — implement verbatim, do not redesign)

### A. `admin/install/installer/state.py`

1. Add keyword-only param `env_file: str | None = None` to `write_state(...)`, AFTER `model_mirror`.
2. Immediately after the existing `model_mirror` carry-forward block, add:
   ```python
   # Carry forward any existing env_file if the caller does not supply one.
   if env_file is None:
       existing = read_state(target_root)
       if existing is not None and "env_file" in existing:
           env_file = existing["env_file"]
   ```
3. Insert this conditional immediately after the `installed_files` payload line and before `if excluded_components:`:
   ```python
   if env_file is not None:
       payload["env_file"] = env_file
   ```
4. Add a one-line `env_file` entry to the module docstring's key list.

### B. `admin/install/installer/cli.py`

1. Add an argparse argument next to `--model-packages`:
   ```python
   parser.add_argument(
       "--env-file",
       type=str,
       default=None,
       help=(
           "Path (workspace-relative or absolute) to the env file holding API keys "
           "for orchestration model workers. Recorded in rbtv.json as 'env_file' so "
           "the API-worker runner resolves keys via file-fallback. Omit to keep any "
           "previously-recorded value (re-installs preserve it). Only the PATH is "
           "recorded — keys are never read or stored."
       ),
   )
   ```
2. Add a module-level helper next to `_resolve_model_packages`:
   ```python
   def _resolve_env_file(
       requested_flag: str | None,
       existing_state: dict[str, Any] | None,
       chosen_modules: tuple[str, ...],
       non_interactive: bool,
       used_modules_flag: bool,
   ) -> str | None:
       """Resolve the env_file PATH to record in rbtv.json (path only — never keys).

       Precedence: --env-file flag > interactive prompt (orchestration + interactive
       only) > None. Returning None lets write_state carry forward any previously
       recorded value, so re-installs preserve env_file (D-exec-1 / D-exec-7).
       """
       if requested_flag is not None:
           return requested_flag.strip() or None

       existing_value = None
       if existing_state is not None and isinstance(existing_state.get("env_file"), str):
           existing_value = existing_state["env_file"]

       # Scripted path, no flag: keep whatever exists (write_state carries it forward).
       if non_interactive or used_modules_flag:
           return None

       # Interactive prompt only when the orchestration module is being installed.
       if ORCHESTRATION_MODULE not in chosen_modules:
           return None

       from .tui import text_input
       entered = text_input(
           "Path to your env file with API keys for model workers "
           "(optional — blank to skip / keep current)",
           default=existing_value or "",
       ).strip()
       return entered or None
   ```
3. In `main()`, AFTER the `_resolve_model_packages(...)` block (~line 621) and BEFORE the install loop, add:
   ```python
   env_file_value = _resolve_env_file(
       requested_flag=args.env_file,
       existing_state=existing_state,
       chosen_modules=chosen_modules,
       non_interactive=args.non_interactive,
       used_modules_flag=bool(args.modules),
   )
   ```
4. In the final `write_state(...)` call (~line 793), add the keyword argument `env_file=env_file_value,`.

Do NOT touch `orchestration.py`, `install.py`, `generator.py`, `manifest.py`, `context.py`, or `tui.py`. Change NO behavior other than the above. NEVER handle, read, or print any key VALUE — only the env_file PATH.

## Validation (run exactly; report each in `validation`)

1. `python -c "import ast,io; ast.parse(io.open('admin/install/installer/state.py',encoding='utf-8').read())"` → EXIT 0.
2. `python -c "import ast,io; ast.parse(io.open('admin/install/installer/cli.py',encoding='utf-8').read())"` → EXIT 0.
3. `python install.py --help` → EXIT 0 and output contains `--env-file`.
4. **Preserve self-test** (prove the load-bearing fix): create a temp dir; write a `rbtv.json` there = `{"rbtv_version":"x","rbtv_path":"p","modules":[],"installed_files":[],"env_file":"KEEPME/.env"}`; put `admin/install/installer` on `sys.path`; `from state import write_state`; call `write_state(Path(tmp), rbtv_version="x", rbtv_relative="p", modules=(), installed_files=[], env_file=None)`; re-read; assert `env_file == "KEEPME/.env"`; print `PRESERVE_OK`. Report EXIT + marker.
5. **Record self-test**: same temp setup but seed JSON has NO `env_file`; call `write_state(..., env_file="NEW/.env")`; assert written `env_file == "NEW/.env"`; print `RECORD_OK`. Report EXIT + marker.

## Commit Rule

Do NOT commit. On validation pass, return the five fields; the conductor reviews (opus) then commits.

## Return Format

Return EXACTLY: `status`, `landed`, `validation`, `concerns`, `open_questions`.
