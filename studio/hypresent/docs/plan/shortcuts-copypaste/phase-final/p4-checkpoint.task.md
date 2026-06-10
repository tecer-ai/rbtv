---
task_id: p4-checkpoint
status: pending
phase: close
complexity_score: 4
human_review: required
orchestrator_executed: true
---

# Checkpoint p4-checkpoint: Final approval

## Goal

Final gate: confirm the whole feature is done at the fidelity floor and get the owner's approval to complete the plan.

---

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md`, `../deliverables.md` | The plan's decisions + artifact index |
| `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/2026-06-08-shortcuts-copypaste.md` | The consolidated C1–C9 evidence sheet (from p4-1) |

## Work to Evaluate

All three phases plus the cold-verifier done-gate (`p4-1`), link audit (`p4-refs`), and compounding (`p4-compound`).

## Review Criteria

1. **C1–C9 all `held`** on the independent cold-verifier sheet (any `held-surprising`/`unexercisable`/`failed` row surfaced explicitly for the owner to accept or reject).
2. **Compat regression green** — `test_r3_delete` (incl. `test_no_keyboard_delete`), `test_r8_font_size_repeat`, `test_r7_alignment`, serializer units.
3. **Plan hygiene** — `p4-refs` clean (links comply); `docs/spec/03-module-map.md` truthful (4 new modules listed); `decisions.md` entry-shape disciplined.
4. **deliverables.md** — every task row ✅; every artifact at its recorded path.

## Execution Flow

### Phase: Evaluate
1. Read the consolidated evidence sheet, `../deliverables.md`, and the p4-refs / p4-compound results.
2. Confirm each review criterion; note any open `held-surprising`/`unexercisable` row.

### Phase: Gate
1. Present the final summary: evidence-sheet path, the C1–C9 verdict line, compat result, and any row needing the owner's acceptance.
2. **MUST** append the Human Review Presentation block.
3. **HALT for human approval** — the plan is complete ONLY on the owner's approval. If rejected, document in `../decisions.md` and re-open the relevant phase.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
