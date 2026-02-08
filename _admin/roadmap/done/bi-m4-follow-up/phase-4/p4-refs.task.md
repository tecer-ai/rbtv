---
task_id: p4-refs
status: pending
phase: validate
complexity_score: 5
human_review: none
---

# Task p4-refs: File Reference Review for bi-m4 and Bridge

## Goal

Verify all internal links and references in bi-m4, bi-m4-user-flow-ia, and bi-m4-design-context: workflow paths, nextStep, nextStepFile, parentWorkflow, outputFolder, and any cross-references between milestone, framework, and bridge. Fix broken or inconsistent references.

---

## Context Files

| File | Purpose |
|------|---------|
| _bmad/rbtv/workflows/bi-m4/workflow.md | Routing table, nextStep, paths |
| _bmad/rbtv/workflows/bi-m4-user-flow-ia/workflow.md | parentWorkflow, steps |
| _bmad/rbtv/workflows/bi-m4-design-context/workflow.md | parentWorkflow, steps, BMAD path |
| _bmad/rbtv/workflows/bi-m4-user-flow-ia/steps-c/*.md | nextStepFile, return-to-milestone text |
| _bmad/rbtv/workflows/bi-m4-design-context/steps-c/*.md | nextStepFile, BMAD path, return-to-milestone text |

---

## Execution Flow

### Phase: Understand

1. List all workflow and step files under bi-m4, bi-m4-user-flow-ia, bi-m4-design-context
2. Identify every frontmatter path (nextStep, nextStepFile, parentWorkflow, outputFolder) and in-body links (e.g. ../bi-m4-build-prototype/workflow.md)

### Phase: Execute

1. For each workflow: verify nextStep points to existing file (or document that milestone steps-c/ is deferred to business-innovation-migration_v3 p3-8/p4-8/p5-8/p6-10)
2. For each step: verify nextStepFile points to existing step
3. Verify parentWorkflow paths resolve (bi-m4 → bi-business-innovation; bi-m4-user-flow-ia and bi-m4-design-context → bi-m4)
4. Verify routing table paths in bi-m4: bi-m4-user-flow-ia, bi-m4-design-context exist; bi-m4-build-prototype, bi-m4-conversion-centered-design, bi-m4-heuristic-evaluation, bi-m4-testing-prep do not exist yet — either remove those rows or mark as "to be created" per shape
5. Fix any broken or inconsistent references; if removing rows, update Recommended Sequence and Success Criteria to match

### Phase: Validate

1. No broken relative paths
2. Return-to-milestone instructions in synthesis steps reference correct codes ([D] or [DD], [B], etc.) and milestone workflow

### Phase: Close

1. Append execution entry to shape.md Execution Log
2. Mark task completed in plan YAML if updating plan state

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| Fixes | bi-m4, bi-m4-user-flow-ia, bi-m4-design-context | In-place fixes; document any deferred refs in shape |

---

## Revolving Plan Rules

- If non-existent workflow refs (build-prototype, etc.) are kept as placeholders: document in shape and ensure no runtime load of missing files
- **MANDATORY:** In output message, state any tasks added or removed
