---
task_id: p5-checkpoint
status: pending
phase: validate
complexity_score: 8
human_review: required
orchestrator_executed: true
hard_halt: true   # first real paid Manus task (per-task cost)
---

# Checkpoint p5-checkpoint: Manus pilot

## Goal

Exercise the Manus agentic worker against the **real Manus API** at the fidelity floor (a real autonomous task → real output file → `return.json`), proving the agentic profile rides the shared runner, then gate (probe-pending → validated).

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | Prior decisions + discoveries |
| `../specs/manus-worker-spec.md` | The Test Plan criteria |
| `orchestration/models/_api/clients/manus.py` + `run.py` | Artifacts under test |
| `orchestration/models/manus/manifest.yaml` | The package under test |

## Work to Evaluate

Phase 5 produced: `manus.py` (p5-1), the Manus package (p5-2), the run.py agentic handling (p5-3), the autonomous-web leaf (p5-4), the verification latency note (p5-5), docs-sync (p5-6), the Manus manual render (p5-7, inline).

## Review Criteria

1. **HARD HALT — surface the per-task projected spend before the first real Manus task; get go-ahead.**
2. A real `run.py --provider manus` task creates → polls → writes the agent output as a file; `return.json` `status: DONE_WITH_NOTES`, `landed` matches, `WALL_MS` reflects the real (minutes-scale) duration (spec Test Plan #1).
3. A failed task surfaces as `BLOCKED`, not silently (#2); a short timeout stops cleanly (#3).
4. **`run.py` change was minimal** — `git diff` shows only the timeout + `structured_output` flag-routing (no provider-name special-case).
5. The Manus key never appears in any prompt/return/stdout/log (#4 grep clean).
6. Manus routes to the autonomous-web leaf, never the code path (`code_competence: none`).

## Execution Flow

### Phase: Evaluate
1. Read Context Files + `decisions.md`.
2. Conductor exercises criteria 2–6 (real task, evidence on disk); a cold verifier re-exercises from the spec alone. Mismatch → FAIL. Flip the Manus manifest `evidence_status` to `validated` only on a held pilot.
3. Write the evidence sheet at `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/{date}-manus-pilot.md`.

### Phase: Gate
1. Present per-criterion PASS/FAIL + evidence-sheet path.
2. **MUST** emit the Human Review Presentation block.
3. **HALT for human approval.** Do not advance on FAIL or without the spend go-ahead.
4. On approve: mark complete + flip `../deliverables.md` rows to ✅.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
