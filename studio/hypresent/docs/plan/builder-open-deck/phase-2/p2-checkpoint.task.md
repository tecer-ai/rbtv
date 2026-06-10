---
task_id: p2-checkpoint
status: done
phase: understand
complexity_score: 4
human_review: required
hard_halt: false
executor: claude
reviewer: claude-opus
---

# Checkpoint p2-checkpoint: Ingest Review — deck opens with correct thumbnails

## Goal

Evaluate the deck-open path against review criteria and present findings for human approval. Soft halt: may auto-pass in full-auto mode when every criterion PASSes.

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | Prior decisions and execution context |
| `../specs/deck-ingest-spec.md` | The acceptance contract this phase must satisfy |
| `app/js/builder/deck-load.js`, `app/js/builder/builder-main.js`, `app/builder.html`, `app/js/builder/tray.js`, `app/js/builder/previews.js` | Work to evaluate |
| `tests/e2e/test_pb8_deck_open.py` | Evidence of exercised behavior |

## Work to Evaluate

Phase 2 produced deck mode's entry: the "Open deck…" control, `?file=` arrival, the deck model, and deck-themed tray thumbnails.

## Review Criteria

1. **Open → full tray at the floor:** in a HEADED browser, clicking "Open deck…" on a real deck copy fills the tray with one row per section in document order — screenshot captured during the exercise.
2. **Thumbnails themed:** thumbnails visibly render slide content with the deck's styling (measured look, not just DOM presence).
3. **Rejection path:** a sectionless HTML file produces a status-bar error and leaves the tray unchanged.
4. **Cancel path:** cancelling the dialog changes nothing and shows no error.
5. **Assemble-mode regression:** `python -m pytest tests/e2e/test_pb2_library_load.py tests/e2e/test_pb3_previews.py -q` exits 0 — library mode untouched.
6. **decisions.md audit:** entries decision+rationale+scope shaped; no file-lists or N→M narratives; no sub-floor rewrite.

## Execution Flow

### Phase: Evaluate
1. Read Context Files; run `tests/e2e/test_pb8_deck_open.py` and the regression suites; perform criterion 1-2's headed exercise, capturing evidence to `phase-2/evidence/`.
2. Evaluate each criterion PASS/FAIL with evidence pointers.

### Phase: Gate
1. Present findings with per-criterion PASS/FAIL.
2. Append the Human Review Presentation block (template § Human Review Presentation).
3. HALT for human approval (auto-pass allowed ONLY in full-auto mode with all-PASS). If rejected: document feedback in `../decisions.md`, return to Build.
4. On approval: mark checkpoint complete in the plan task list and flip its row in `../deliverables.md`.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
