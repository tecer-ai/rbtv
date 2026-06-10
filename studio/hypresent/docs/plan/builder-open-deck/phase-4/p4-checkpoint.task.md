---
task_id: p4-checkpoint
status: pending
phase: understand
complexity_score: 4
human_review: required
hard_halt: false
executor: claude
reviewer: claude-opus
---

# Checkpoint p4-checkpoint: Bridge Review — round trip without losing work

## Goal

Evaluate the save-and-switch bridge against review criteria and present findings for human approval. Soft halt: may auto-pass in full-auto mode when every criterion PASSes.

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | Prior decisions and execution context |
| `../specs/bridge-spec.md` | The acceptance contract this phase must satisfy |
| `app/js/builder/builder-main.js`, `app/builder.html`, `app/js/main.js`, `app/index.html`, `app/js/shell/file-controls.js` | Work to evaluate |
| `tests/e2e/test_pb12_bridge.py` | Evidence of exercised behavior |

## Work to Evaluate

Phase 4 produced the two crossing controls and their Save-As gates, reusing the `?file=` handoff in both directions.

## Review Criteria

1. **Round trip at the floor:** in a HEADED browser — open a real deck copy in the builder, reorder, "Switch to editor" (real native dialog or injected launcher per the e2e seam), edit a text in the editor, "Open in builder": the final tray shows the reorder AND the thumbnail shows the edited text. Screenshots captured during the exercise.
2. **New-file guarantee:** each crossing wrote a DISTINCT new file; no crossing overwrote its source (compare file lists before/after).
3. **Cancel semantics:** cancelling either dialog leaves the current view fully intact — no navigation, no write, no error.
4. **Disabled states:** "Switch to editor" disabled with an empty tray; "Open in builder" disabled with no document open.
5. **Editor regression:** `python -m pytest tests/e2e/test_g2_save_with_comments.py tests/e2e/test_exit_smoke.py -q` exits 0 — editor save/exit untouched.
6. **decisions.md audit:** entries decision+rationale+scope shaped; no file-lists or N→M narratives; no sub-floor rewrite.

## Execution Flow

### Phase: Evaluate
1. Read Context Files; run the bridge suite + regressions; perform criterion 1's headed round trip, capturing evidence to `phase-4/evidence/`.
2. Evaluate each criterion PASS/FAIL with evidence pointers.

### Phase: Gate
1. Present findings with per-criterion PASS/FAIL.
2. Append the Human Review Presentation block (template § Human Review Presentation).
3. HALT for human approval (auto-pass allowed ONLY in full-auto mode with all-PASS). If rejected: document feedback in `../decisions.md`, return to Build.
4. On approval: mark checkpoint complete in the plan task list and flip its row in `../deliverables.md`.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
