---
task_id: p4-refs
status: pending
phase: validate
complexity_score: 3
human_review: optional
---

# Task p4-refs: Plan-artifact link audit

## Goal

Verify every reference inside the plan folder complies with the Plan Linking Standard so the plan folder stays relocatable: internal links file-relative (`./`, `../`); external links project-root-relative; no brittle self-references.

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | The Plan Linking Standard summary (Standards Applied) |
| all files under `docs/plan/shortcuts-copypaste/` | The artifacts to audit |

## Execution Flow

### Phase: Execute
1. Search every file in the plan folder for a path violation:
   - No file contains an absolute or project-root-relative path that points at the plan folder ITSELF (self-reference must be `./`/`../`).
   - Internal references (between plan files: `decisions.md`, `learnings.md`, `deliverables.md`, `specs/*`, `phase-*/*`) use `./` or `../`.
   - External references (to repo files like `runtime/js/*`, `tests/e2e/*`, the done-gate evidence path) are project-root-relative (no `../../../` traversal out of the plan folder).
2. Fix any violation in place (surgical — only the offending path).

### Phase: Validate
1. Re-scan; confirm zero violations.

### Phase: Close
1. If standalone: report the audit result (clean, or the list of fixes) to the user; mark complete after approval. Under orchestration: the reviewer dispatch verifies; flip `../deliverables.md` row to ✅.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
