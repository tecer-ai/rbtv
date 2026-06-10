---
task_id: p4-compound
status: pending
phase: close
complexity_score: 4
human_review: required
---

# Task p4-compound: Compound learnings into system improvements

## Goal

Process `../learnings.md` into actionable system improvements for RBTV/sb-os, so this plan's friction compounds into durable fixes.

## Context Files

| File | Purpose |
|------|---------|
| `../learnings.md` | The meta-learnings queue captured during execution |
| `../decisions.md` | Context for any discovery that produced a learning |

## Execution Flow

### Phase: Execute
1. Read `../learnings.md`. For each entry whose four Compound-Readiness boxes are checked: group by target component and draft the concrete change (target file, type, proposed change).
2. If a learning targets the planning/orchestration system itself (e.g. a task-file-contract gap surfaced by this plan), draft it as a compound PRD per the user's compounds routing (`.user/compounds/{component}/cp-{component}-{description}.md`).
3. If `../learnings.md` has no compound-ready entries, state that explicitly — no compounding needed.

### Phase: Gate
1. Present the proposed compound changes (or "no learnings to compound") to the user.
2. **MUST** append the Human Review Presentation block (this task proposes system changes — judgment). HALT for approval before writing any compound PRD or applying any change.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
