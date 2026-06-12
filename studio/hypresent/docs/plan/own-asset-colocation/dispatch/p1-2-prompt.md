---
execution_kind: code
executor: codex
allowed_workdir: 3-resources/tools/rbtv/studio/hypresent
allowlist:
  - tests/test_deck_api.py
  - tests/test_recompose.py
sandbox: workspace-write
commit_policy: none
test_command: python -m pytest tests/test_deck_api.py tests/test_recompose.py -q
forbidden_ops:
  - git push
  - git commit / git add (the conductor commits via rbtv-commit)
  - destructive git reset / amend
  - writes outside the allowlist (the two test files) — plus the single validation evidence file named below
  - running stamp.py or editing deliverables.md, the plan checkbox, or decisions.md
  - editing server/deck_api.py or server/recompose.py (the implementation is DONE — tests only)
  - external production API calls
  - "--dangerously-bypass-approvals-and-sandbox"
doubt_policy: halt
reviewer: claude-opus
---

# Dispatch — Task p1-2: Unit tests for own-asset colocation (codex worker)

Your working directory (`--cd`) is the hypresent app dir `3-resources/tools/rbtv/studio/hypresent/`.
All `server/…`, `tests/…` paths resolve from there. `pytest` runs from there.

The implementation (p1-1) is ALREADY DONE and on disk in `server/deck_api.py` + `server/recompose.py`
(own-asset copy, collision rename via `_unique_asset_path`/`_rewrite_referenced_assets`, the `existing.html`
override in recompose, and the `assets_renamed` response field). Your job is TESTS ONLY — do NOT edit the
implementation.

## Run-binding header

### CRITICAL — how to run the test suite (read this first)

Run the suite with the GLOBAL python, NOT `uv run`:

```
python -m pytest tests/test_deck_api.py tests/test_recompose.py -q
```

The global Python has `pytest 9.0.3` installed; `uv run pytest` uses an isolated env that LACKS pytest and
has NO network to install it (that is why a `uv run` attempt fails with EXIT 2 — that is an environment
artifact, NOT a code problem). Your sandbox permits `python -m pytest` (it reads site-packages and writes
temp files to `/tmp`/`$TMPDIR`). You MUST get the suite to EXIT 0 with your new tests before returning.

### Worker obligations (BINDING — imperative)

1. **Return-schema compliance.** Final message MUST be the five-field schema in "Return format" below — every field, none renamed.
2. **Allowlist boundary.** Create / modify ONLY `tests/test_deck_api.py` and `tests/test_recompose.py`. Do NOT edit `server/*` — the implementation is frozen for this task.
3. **Doubt policy = HALT.** On any ambiguity the task + spec do not resolve, STOP and return `status: DOUBT_ESCALATED` with the question in `open_questions`. NEVER guess.
4. **Tests MUST pass.** Run `python -m pytest tests/test_deck_api.py tests/test_recompose.py -q` and get EXIT 0 INCLUDING your new tests. Write the full pytest output to `docs/plan/own-asset-colocation/dispatch/p1-2-validation.txt` (the evidence file). If a new test FAILS and you believe it reveals an implementation bug (not a test bug), do NOT edit the implementation — STOP and return `DOUBT_ESCALATED` describing the failing assertion and the spec row it tests.
5. **NO commit / NO state writes.** Do NOT run `git add/commit/push`, `stamp.py`, or edit `deliverables.md` / plan checkbox / `decisions.md`. Any decision/discovery → put it in the `concerns` return field; the conductor logs it.
6. **Sandbox = workspace-write.** Temp decks/assets for fixtures go to an OS temp dir (`tempfile`), never into the repo.
7. **Allowed evidence-file exception to the allowlist:** you MAY also write ONLY `docs/plan/own-asset-colocation/dispatch/p1-2-validation.txt`. Nothing else outside the two test files.

### Path-resolution note (the task body uses plan-folder-relative refs — map to your cwd)

| Task body ref | Read it at (relative to your `--cd`) |
|---------------|--------------------------------------|
| `../specs/own-asset-colocation-spec.md` | `docs/plan/own-asset-colocation/specs/own-asset-colocation-spec.md` |
| `tests/test_deck_api.py`, `tests/test_recompose.py` | same, under `tests/` |
| `server/deck_api.py` | `server/deck_api.py` (READ ONLY — to see the `assets_renamed` field + behavior to assert) |

**Ignore the task's "Phase: Close" stamping step** (the `--status in_progress` / `stamp.py` / "mark complete" lines) — those are the conductor's job. Do Understand / Execute / Validate, then return the schema.

Follow disciplined coding practice (`rbtv-coding-discipline`, `.claude/skills/rbtv-coding-discipline/`): extend the existing test conventions, minimal additions, no refactor of the existing suite.

### Return format — return EXACTLY these five fields as your final message

- **`status`**: one of `DONE` · `DONE_WITH_NOTES` · `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT`.
- **`landed`**: test files modified + a one-line list of the test functions added.
- **`validation`**: each command run, its `EXIT`, its `WALL_MS`, `SKIPPED_COUNT` (0 if none; reason per skip). Cite `dispatch/p1-2-validation.txt`. The required command `python -m pytest tests/test_deck_api.py tests/test_recompose.py -q` MUST show EXIT 0.
- **`concerns`**: risks, smells, anything for the conductor to log; spec rows you could NOT cover and why.
- **`open_questions`**: unresolved questions (the doubt, if `DOUBT_ESCALATED`).

---

## Payload — Task p1-2 (verbatim)

# Task p1-2: Unit tests for own-asset colocation

## Goal

Unit tests prove the spec's Test Plan rows 1-5 at the handler level: own-asset colocated on save-to-new-dir, dropped-slide asset skipped, same-dir no-op, collision rename+rewrite, multi-section consistency. Tests source of truth: `../specs/own-asset-colocation-spec.md` § Test Plan.

**Path anchor:** `tests/…` relative to the hypresent app dir `3-resources/tools/rbtv/studio/hypresent/`. Run `pytest` from there.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `../specs/own-asset-colocation-spec.md` | Test Plan rows 1-5 + Edge Cases — what each test must assert |
| `tests/test_deck_api.py` | Conventions; extend `test_deck_save_fragment_and_blank_with_assets` + `test_deck_save_asset_collision_skip` patterns (tmp_path, `REAL_DECK_SRC`, building temp libraries/assets) |
| `tests/test_recompose.py` | If p1-1 added a recompose override, add its unit coverage here |
| `server/deck_api.py` | The implemented behavior + the `assets_renamed` response field to assert against |

## Execution Flow

### Phase: Understand
1. Read every Context File.
2. Note the test fixtures: a source deck needs an OWN `assets/*` ref — craft a minimal conforming source (`<section>` containing `<img src="assets/own.png">`) with the file beside it, or inject a ref into a `REAL_DECK_SRC` copy's section; do NOT rely on the real deck already referencing assets.

### Phase: Execute
1. Add unit tests covering spec Test Plan rows 1-5:
   - own-asset copied to a new out_dir (`assets_copied`, bytes match);
   - two own-assets, one section dropped → only the kept section's asset copied;
   - same-dir save → no copy/rename, section byte-identical;
   - collision (pre-existing different `out_dir/assets/logo.png`) → own copied as `logo-1.png`, kept section's ref rewritten, `assets_renamed` lists it, pre-existing file unchanged;
   - own-asset referenced by a section AND its duplicate, colliding → one renamed copy, both refs rewritten to the same name.
2. Add the boundary-safe-replacement and `url(...)`-form assertions from Edge Cases where cheap. (Recommended: a test that a section referencing BOTH `assets/x.png` and `assets/x.png.bak`, where `x.png` collides, rewrites only `x.png` and leaves `x.png.bak` intact.)

### Phase: Validate
1. `python -m pytest tests/test_deck_api.py tests/test_recompose.py -q` → expected EXIT 0, including the new tests.

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Own-asset + collision unit tests | `tests/test_deck_api.py` (and `tests/test_recompose.py` if override used) | pytest |
