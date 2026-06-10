---
task_id: p1-checkpoint
status: done
phase: understand
complexity_score: 5
human_review: required
hard_halt: true
executor: claude
reviewer: claude-opus
---

# Checkpoint p1-checkpoint: Save Core Review — the heart, proven on a real deck

## Goal

Evaluate the recompose engine and deck API against review criteria and present findings for human approval. **HARD HALT — never auto-passed in autonomous mode.**

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | Prior decisions and execution context |
| `../specs/deck-save-spec.md` | The acceptance contract this phase must satisfy |
| `server/recompose.py`, `server/deck_api.py`, `server/server.py` | Work to evaluate |
| `tests/test_recompose.py`, `tests/test_deck_api.py` | Evidence of exercised behavior |

## Work to Evaluate

Phase 1 produced the non-assembler save path: the byte-range recompose engine (`server/recompose.py`), the deck API endpoints (`server/deck_api.py` + routes in `server/server.py`), and their test suites.

## Review Criteria

1. **Byte-fidelity:** a reorder of a real deck copy leaves every untouched span byte-identical to the source — verified by an actual slice-comparison test run, not by reading the code.
2. **No re-serialization:** `server/recompose.py` contains no whole-document HTML parser usage (`html.parser`, `BeautifulSoup`, `lxml`, regex-rewrite of the full document).
3. **Real-deck proof at the floor:** a recomposed copy of `tecer-gsmm-introduction-test-v3.html` (reorder + remove + duplicate + blank + one fixture-library fragment) opens in a HEADED browser rendering correctly with zero recompose-attributable console errors — screenshot + console log captured during the exercise.
4. **Asset copy:** the fragment's referenced assets exist in the output folder; collisions reported, originals untouched.
5. **Clean output:** the saved file contains no `hyp-` classes and no `data-hyp-*` attributes introduced by the save.
6. **Owner-data safety:** root `tecer-gsmm-introduction*.html` files are bit-identical to their pre-phase state (`git status` clean on them).
7. **decisions.md audit:** entries (if any) are decision+rationale+scope shaped; no file-lists, no N→M narratives; no rewrite below the ≥50% size floor.

## Execution Flow

### Phase: Evaluate
1. Read all Context Files; run both test suites; perform criterion 3's headed-browser exercise yourself, capturing evidence files to `phase-1/evidence/`.
2. Evaluate each criterion PASS/FAIL with evidence pointers.

### Phase: Gate
1. Present findings with per-criterion PASS/FAIL.
2. Append the Human Review Presentation block (`{rbtv_path}/orchestration/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation).
3. **HALT for human approval — hard halt, no autonomous override.** If rejected: document feedback in `../decisions.md`, return to Build.
4. On approval: mark complete in the plan task list and flip the row in `../deliverables.md`.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
