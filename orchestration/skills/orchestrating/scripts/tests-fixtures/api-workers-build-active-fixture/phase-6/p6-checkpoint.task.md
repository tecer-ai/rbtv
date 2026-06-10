---
task_id: p6-checkpoint
status: completed
phase: validate
complexity_score: 6
human_review: required
orchestrator_executed: true
---

# Checkpoint p6-checkpoint: final approval

## Goal

Final gate: confirm the whole build is delivered and certified — all pilots held, the deterministic selector + Claude-collapse fix verified, docs synced, and the "earn their keep" verdict surfaced — then HALT for the owner's approval to complete the plan.

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` + `../learnings.md` + `../deliverables.md` | The full record + artifact index |
| `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/` | Every pilot's evidence sheet |

## Work to Evaluate

The whole plan: 3 chat workers + Manus agentic worker (pilots held), the deterministic `(model,variant)` selector + the Agent-tool Claude package (collapse fixed), the conductor wiring (cards/schema/install/docs), and the live orchestrated pilot.

## Review Criteria

1. Every phase checkpoint passed; every pilot evidence sheet shows `held` (or `held-surprising`/`unexercisable` surfaced for the owner's decision).
2. `deliverables.md` is fully ✅; every `→ path` resolves (p6-refs clean).
3. The deterministic selector + `models/claude/` demonstrably ended the "Claude as one entity" collapse (p3-checkpoint evidence).
4. The "earn their keep" verdict (p6-1) is surfaced honestly — including if an API/Manus worker did NOT win its leaf.
5. No API key appears anywhere in prompts/returns/logs/commits across the build.
6. `learnings.md` processed (p6-compound); any compound PRDs filed.

## Execution Flow

### Phase: Evaluate
1. Read Context Files + every evidence sheet.
2. Assemble the final per-criterion findings + the exit scorecard.

### Phase: Gate
1. Present per-criterion PASS/FAIL + the honest exit status (COMPLETE / COMPLETE PENDING USER ACTION — e.g. the USER-EXECUTED install run).
2. **MUST** emit the Human Review Presentation block (surface every `held-surprising`/`unexercisable` row + the earn-their-keep verdict + any 🔴).
3. **HALT for human approval.** Do not declare the plan complete without it.
4. On approve: mark the plan complete.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
