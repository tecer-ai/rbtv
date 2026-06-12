---
task_id: p2-checkpoint
status: in_progress
complexity_score: 6
human_review: required
---

# Checkpoint p2-checkpoint: Final Review

## Goal

Evaluate the whole feature against the spec — done-gate evidence sufficiency, full test suite green, plan links valid, decisions audit — and obtain user approval to complete the plan.

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | All decisions + discoveries; the audit target |
| `../deliverables.md` | Artifact index — confirm every row delivered at its Path |
| `../specs/own-asset-colocation-spec.md` | The full Behavior + Test Plan to evaluate against |
| `./done-gate-evidence/` | The p2-1 headed evidence to judge for sufficiency |

**Path anchor:** `server/…`/`tests/…` relative to `3-resources/tools/rbtv/studio/hypresent/`.

## Work to Evaluate

The complete feature: own-asset copy + collision rename/rewrite (`server/deck_api.py`, maybe `server/recompose.py`), unit tests, the headed done-gate evidence, and the e2e regression assertion.

## Review Criteria

Evaluate each; note PASS / FAIL / needs-attention:

1. Done-gate evidence proves spec Test Plan row 7: a real deck copy's own images render in the builder reopen AND the editor, and the collision case shows the correct image — each backed by an evidence file on disk (not prose); timings plausible.
2. Full suite green, re-run now (not a stale log): `pytest tests/test_deck_api.py tests/test_recompose.py tests/e2e/test_pb11_deck_save.py -q` EXIT 0.
3. Spec invariants intact: library behavior unchanged; non-colliding sections + separators byte-identical (existing faithfulness tests green); collisions never render the wrong image.
4. `p2-refs` validated: all internal plan links resolve; intra-plan refs are file-relative; `server/…`,`tests/…` are app-relative; no absolute/root-relative self-reference to the plan folder.
5. Scope held — no library-ref rewriting, no full-asset-tree copy, no speculative options ("don't overengineer" honored); diff is proportionate.
6. `decisions.md` audit: entries are decision + rationale + scope only — no file-lists, no N→M narratives, append-only; any rewrite carried explicit sanction + the ≥50% size floor. Checkpoint entries record the ruling only.

## Execution Flow

### Phase: Evaluate
1. Read all Context Files; read `decisions.md` end-to-end and `deliverables.md`.
2. Re-run the full suite yourself; inspect the done-gate evidence files; run the `p2-refs` link checks.
3. Prepare a findings summary with per-criterion PASS/FAIL.

### Phase: Gate
1. Present findings with clear PASS/FAIL per criterion.
2. Append the Human Review Presentation block — point the user at the done-gate evidence and the `deck_api.py` collision logic; surface red/yellow flags from evidence (criterion FAILs, implausible timings, any `unexercisable` claim). If none, write "None identified" + a one-line rationale.
3. **HALT for human approval** — do not advance regardless of findings.
4. If rejected: document feedback in `decisions.md`; do not complete.
5. If approved: stamp complete (run from the vault root; `<plan-dir>` = this plan's folder, holding the plan file + `deliverables.md`):
   `python 3-resources/tools/rbtv/orchestration/skills/orchestrating/scripts/stamp.py --plan-dir <plan-dir> --task p2-checkpoint --status completed --scope worker`
   Then remove `#wip` from this task's line in `2-areas/rbtv/rbtv-tasks.md` and mark the source task done.

> `decisions.md` entries: decision + rationale + scope ONLY (+ optional one-word `compoundable` marker for harvest-worthy findings) — never file-lists or N→M narratives; supersede by appending, never rewrite.
