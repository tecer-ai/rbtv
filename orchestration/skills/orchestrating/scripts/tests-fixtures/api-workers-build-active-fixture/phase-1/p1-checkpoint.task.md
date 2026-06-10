---
task_id: p1-checkpoint
status: pending
phase: validate
complexity_score: 9
human_review: required
orchestrator_executed: true
hard_halt: true   # first real paid API call — non-overridable even in autonomous mode
---

# Checkpoint p1-checkpoint: DeepSeek pilot — runner proven end-to-end

## Goal

Exercise the shared runner against the **real DeepSeek API** at the fidelity floor (real call → real files → real `return.json`), then gate on the evidence. This is the load-bearing pilot.

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | Prior decisions + discoveries |
| `../specs/api-text-worker-spec.md` | The Test Plan criteria exercised here |
| `orchestration/models/_api/run.py` + `clients/{base,deepseek}.py` | The artifacts under test |
| `orchestration/models/deepseek/manifest.yaml` | The package under test |

## Work to Evaluate

Phase 1 produced: the schema repurpose prose (p1-1), `base.py` (p1-2), `deepseek.py` (p1-3), `run.py` (p1-4), the DeepSeek package (p1-5), the reference doc (p1-6).

## Review Criteria

1. **HARD HALT — surface projected per-call spend BEFORE the first real call; get explicit go-ahead.** (Real $; never auto-spend.)
2. A real `run.py --provider deepseek` call writes the model's files into a real `--output-folder`; `return.json` `status: DONE`, `landed` matches files on disk (spec Test Plan #1).
3. Raw-dump fallback writes output (never drops) on a non-envelope response (#2).
4. `files[].path` traversal is neutralized to the output folder (#3).
5. Truncation is flagged when `finish_reason ≠ stop` (#4).
6. The key appears in NO prompt/return/stdout/log (#5 — grep clean).
7. Runner resolves the client dynamically (no per-provider branch in `run.py`).
8. `decisions.md` audit: entries are decision+rationale+scope; no file-lists/N→M; append-only (≥50% size floor on any rewrite).

## Execution Flow

### Phase: Evaluate
1. Read Context Files + `decisions.md`.
2. The conductor EXERCISES criteria 2–6 itself (real call, evidence files on disk), then dispatches a **cold verifier** (given ONLY the spec criteria + the artifact, never the builder's claims) to re-exercise. Builder/verifier mismatch → FAIL → back to Build.
3. Write the evidence sheet at `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/{date}-api-deepseek-pilot.md`.

### Phase: Gate
1. Present per-criterion PASS/FAIL + the evidence-sheet path.
2. **MUST** emit the Human Review Presentation block (checkpoints inherit `human_review: required`).
3. **HALT for human approval.** Do not advance on any FAIL or without the spend go-ahead.
4. On approve: mark complete in the plan list + flip `../deliverables.md` row to ✅.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
