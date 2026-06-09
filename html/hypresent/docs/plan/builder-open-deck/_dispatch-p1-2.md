# DISPATCH — p1-2 (kimi executor) — builder-open-deck

You are a NON-REASONING code executor. Implement EXACTLY what the task below specifies. Do NOT design, do NOT "fill in the blanks", do NOT interpret intent. Every interface and edge case is pre-resolved in the task and its referenced specs. If anything is ambiguous or an anchor excerpt does not match the file on disk, HALT and return `DOUBT_ESCALATED` with the precise question — never guess.

## Binding obligations (you MUST obey)

- **Allowlist boundary:** touch ONLY these 3 files. Nothing else.
  - ✚ create `server/deck_api.py`
  - ✎ modify `server/server.py`
  - ✚ create `tests/test_deck_api.py`
- **No stray files:** NEVER write scratch/notes/log files into the repo root or anywhere outside the allowlist. Test temp files go through pytest `tmp_path` only.
- **READ-ONLY owner data:** the root decks `tecer-gsmm-introduction*.html` are the owner's real files. Tests copy them to `tmp_path` — NEVER modify, move, or write to the originals.
- **Validation before done:** run BOTH `python -m pytest tests/test_deck_api.py tests/test_recompose.py -q` AND `python -c "import server.server"`. All EXIT 0, no skips, before you commit or claim DONE.
- **Commit:** local-only on `master`, subject MUST start with `[p1-2]`, stage ONLY the 3 allowlist files (NEVER `git add -A` — this repo has unrelated uncommitted files). NEVER push/amend/force-reset.
- **Halt on doubt:** doubt_policy is halt. Do not improvise past ambiguity.
- **No subagents:** swarm_policy is disabled — do NOT launch any kimi subagent.

## Path mapping (the task body was authored in `docs/plan/builder-open-deck/phase-1/` — resolve its relative paths from your work-dir root as follows)

| Task-body path | Actual path from your work-dir root |
|----------------|--------------------------------------|
| `../specs/deck-save-spec.md` | `docs/plan/builder-open-deck/specs/deck-save-spec.md` — **READ THE ADX-2 ERRATUM at the bottom of the file: it CORRECTS the `recompose` contract (inter-slide separators are preserved); the engine in `server/recompose.py` already implements the corrected contract** |
| `../specs/deck-ingest-spec.md` | `docs/plan/builder-open-deck/specs/deck-ingest-spec.md` |
| `../decisions.md` | `docs/plan/builder-open-deck/decisions.md` |
| `../deliverables.md` | `docs/plan/builder-open-deck/deliverables.md` (do not write — see ADX-1 in the task) |
| `server/*.py`, `tests/e2e/fixtures/builder-lib/` | work-dir-relative as written |

## Required return — these five named fields, exactly (no renames, no prose-only)

- `status`: one of DONE · DONE_WITH_NOTES · BLOCKED · DOUBT_ESCALATED · NEEDS_CONTEXT
- `landed`: files created/modified + the commit hash (must match `git log`)
- `validation`: each command run + its EXIT code + WALL_MS; `SKIPPED_COUNT` and a reason per skip
- `concerns`: risks/smells/adjacent issues you noticed but did not fix
- `open_questions`: the precise blocker/doubt if you halted (else "none")

The return message is a HINT; your work on disk is the truth and will be reconciled against `git status` / `git log`. Capture validation output as evidence.

Decisions reference (already applied in the task; do not re-derive): `docs/plan/builder-open-deck/decisions.md`.

---

# TASK PAYLOAD (verbatim — implement this)

---
task_id: p1-2
status: pending
phase: understand
complexity_score: 7
human_review: optional
execution_kind: code
executor: kimi
reviewer: claude-opus
workspace: 3-resources/tools/rbtv
work_dir: html/hypresent
allowed_workdir: html/hypresent
branch: master
allowlist:
  - server/deck_api.py
  - server/server.py
  - tests/test_deck_api.py
commit_policy: local-only
test_command: python -m pytest tests/test_deck_api.py tests/test_recompose.py -q
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - modifying root-level *.html decks
doubt_policy: halt
swarm_policy: disabled
max_kimi_subagents: 0
# Human-readable allowlist (✚ create · ✎ modify):
#   ✚ server/deck_api.py
#   ✎ server/server.py
#   ✚ tests/test_deck_api.py
---

# Task p1-2: Deck API endpoints — load, save, path dialogs

## Goal

CREATE `server/deck_api.py` with handlers `handle_deck_load`, `handle_deck_save`, `handle_dialog_open_path`, `handle_dialog_save_path`, UPDATE `server/server.py` to route them, and CREATE `tests/test_deck_api.py`. Contracts: `../specs/deck-save-spec.md` (save, asset copy) and `../specs/deck-ingest-spec.md` (load, head extraction, path-only dialogs).

Serialization note: `server/server.py` is shared — this task is its only writer in this plan; build on the current file.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `../specs/deck-save-spec.md` | `/api/deck-save` payload/response, asset-copy rules, all-or-nothing error behavior |
| `../specs/deck-ingest-spec.md` | `/api/deck-load` payload/response (`head` without scripts), dialog-path endpoints |
| `server/recompose.py` | The engine these handlers call (built in p1-1) |
| `server/api.py` | Handler tuple style; `_launch_dialog` + `set_dialog_launcher` injection seam to REUSE (import, do not duplicate) |
| `server/builder_api.py` | `handle_library_asset` (how fragments are read); route-wiring style reference |
| `server/server.py` | `do_POST` dispatch table — add `/api/deck-load`, `/api/deck-save`, `/api/dialog-open-path`, `/api/dialog-save-path` following the existing `elif path ==` pattern |

## Execution Flow

### Phase: Understand
1. Read every Context File. Mark this task in progress in the plan file, this frontmatter, and `../deliverables.md` (same turn).

### Phase: Execute
1. CREATE `server/deck_api.py` — handlers return `(status, dict)` tuples like `server/api.py`. Reuse `api._launch_dialog` for the path-only dialogs so the existing `set_dialog_launcher` injection drives them in tests. `handle_deck_save` resolves `library` items by reading `slides/{id}.html` from the library folder (path-traversal-guarded like `handle_library_asset`), maps them to recompose `fragment` items, copies referenced assets per spec, writes all-or-nothing.
2. UPDATE `server/server.py` — add the four routes.
3. CREATE `tests/test_deck_api.py` — spec Test Plan rows 3 and 5 plus: load returns script-free `head` and ordered sections; non-conforming file errors; injected dialog launchers return paths/None. Use the e2e fixture library `tests/e2e/fixtures/builder-lib/` and temp copies of `tecer-gsmm-introduction-test-v3.html`.

### Phase: Validate
1. `python -m pytest tests/test_deck_api.py tests/test_recompose.py -q` — expected EXIT 0.
2. `python -c "import server.server"` — expected EXIT 0 (routes wired without import errors).

### Phase: Close
Standard orchestrated close: flip plan checkbox, frontmatter status, `../deliverables.md` row.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Deck API handlers | `server/deck_api.py` | Pure-handler Python module |
| Routes | `server/server.py` | Four new `do_POST` branches |
| API tests | `tests/test_deck_api.py` | pytest |

## Return Contract

Return `status` · `landed` · `validation` (commands + EXIT + WALL_MS + skips with reasons) · `concerns` · `open_questions`.

## Revolving Plan Rules

Simple discovery (<5 min): resolve, document in `../decisions.md`. Complex: add a task, notify. State `PLAN MODIFIED:` lines in your return when tasks change.

---

> **ADX-1 (run erratum, 2026-06-09):** The status-flip bookkeeping steps in this task (marking the task in progress / done in the plan file, this file's frontmatter, and `../deliverables.md`) are performed by the ORCHESTRATOR at verified return — NOT by the executor. Executor: skip those steps; write ONLY within your allowlist. All other instructions unchanged.

