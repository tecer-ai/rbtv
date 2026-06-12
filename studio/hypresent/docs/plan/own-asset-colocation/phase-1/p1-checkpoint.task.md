---
task_id: p1-checkpoint
status: pending
complexity_score: 6
human_review: required
---

# Checkpoint p1-checkpoint: Phase 1 (Build) Review

## Goal

Evaluate the Phase 1 implementation + unit tests against the spec and the plan's invariants, and present findings for human approval.

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | Locked decisions, constraints, and any Phase 1 discoveries |
| `../specs/own-asset-colocation-spec.md` | Behavior rows + Invariants to evaluate against |
| `server/deck_api.py`, `server/recompose.py` | The implementation to review |
| `tests/test_deck_api.py`, `tests/test_recompose.py` | The unit coverage to review |

**Path anchor:** `server/…`/`tests/…` relative to `3-resources/tools/rbtv/studio/hypresent/`.

## Work to Evaluate

Phase 1 produced: the own-asset copy + collision-safe rename/rewrite in `handle_deck_save` (and any `recompose` `existing`-override), plus unit tests for spec Test Plan rows 1-5.

## Review Criteria

Evaluate each; note PASS / FAIL / needs-attention:

1. Own-asset colocation works on save-to-new-dir; collisions rename the own-asset + rewrite its ref ONLY in the owning source section (spec Behavior rows 1-3).
2. Invariants hold: library/blank sections never rewritten; with no collision, preserved sections + separators are byte-identical to source; one source asset → one new name.
3. Edge cases handled: same-dir no-op, missing source asset tolerated, boundary-safe replacement, `url(...)` form, 1:1 mapping refusal, unique-name generation.
4. The full existing suite is green — no regression: `pytest tests/test_deck_api.py tests/test_recompose.py -q` EXIT 0 (re-run; do not trust a stale log; reject implausibly fast timings).
5. Reuse, not parallel machinery — the change builds on `_find_referenced_assets` + skip-if-exists; the diff is minimal (no speculative options — honors "don't overengineer").
6. `decisions.md` audit: entries are decision + rationale + scope only — no file-lists, no N→M narratives, append-only (UPDATE-not-REWRITE); a full-file rewrite needs explicit sanction + ≥50% size floor.

## Execution Flow

### Phase: Evaluate
1. Read all Context Files; read `decisions.md` Decisions and Discoveries.
2. Re-run the validation command yourself; evaluate each criterion.
3. Prepare a findings summary with per-criterion PASS/FAIL.

### Phase: Gate
1. Present findings with clear PASS/FAIL per criterion.
2. Append the Human Review Presentation block (checkpoints inherit `human_review: required`) — point the user at specific artifacts (diff in `deck_api.py`, the collision tests) and surface red/yellow flags from evidence; if none, write "None identified" + a one-line rationale.
3. **HALT for human approval** — do not advance regardless of findings.
4. If rejected: document feedback in `decisions.md`; do not advance.
5. If approved: stamp complete (run from the vault root; `<plan-dir>` = this plan's folder, holding the plan file + `deliverables.md`):
   `python 3-resources/tools/rbtv/orchestration/skills/orchestrating/scripts/stamp.py --plan-dir <plan-dir> --task p1-checkpoint --status completed --scope worker`

> `decisions.md` entries: decision + rationale + scope ONLY (+ optional one-word `compoundable` marker for harvest-worthy findings) — never file-lists or N→M narratives; supersede by appending, never rewrite.
