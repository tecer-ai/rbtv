---
title: 'Compound: Shape Discovery Propagation'
docType: 'compound'
mode: 'create'
priority: 'Medium'
tracker: ''
stepsCompleted:
  - step-01-init.md
  - step-02-self-assessment.md
  - step-03-discussion.md
  - step-04-document.md
inputDocuments:
  - _bmad/rbtv/workflows/plan-lifecycle/templates/shape-template.md
  - .cursor/plans/business innovation migration/business-innovation-migration_v3/shape.md
outputPath: '{project-root}/projects/planning-artifacts'
date: '2026-02-05'
yoloMode: false
---

# Shape Discovery Propagation

**Type:** Workflow Template  
**Priority:** Medium  
**Tracker:**  
**Status:** Backlog

---

## Overview

### Problem

When an agent documents a Discovery in shape.md that changes prior decisions, the agent correctly appends the Discovery entry but fails to propagate annotations to affected locations. Completed tasks and pending tasks that reference the superseded decision remain stale, causing confusion when future agents or users read them.

Additionally, the current "Execution Log" section encourages logging routine task completions ("task completed, document created") which adds noise without lasting value.

### Goals

1. When a Discovery is documented, require the agent to annotate all affected completed tasks and update all affected pending tasks
2. Rename "Execution Log" to "Decisions and Discoveries" to clarify intent
3. Remove routine task status entries — only capture decisions and discoveries that matter in one month

### Constraints

- Changes must be made only within BMAD workflow files (no cursor rules)
- Completed tasks must be annotated, not modified (preserve audit trail)
- Pending tasks must be updated to reflect new decisions

---

## Self-Assessment

### Error Analysis

**Error Type:** Execution Failure + Knowledge Gap

When Discovery 1 (founder-diary elimination) was documented in shape.md:
- ✅ Discovery entry appended correctly
- ✅ Template file deleted
- ✅ Step files updated
- ❌ Plan file output structure not annotated
- ❌ Task files (p1-4, p2-4, p2-5) not annotated/updated
- ❌ User had to manually add "⛔ CANCELLED — See Discovery 1" annotation

### Context Source Evaluation

| File | Issue |
|------|-------|
| `shape-template.md` | Discovery entry format lacks propagation requirements |
| `plan-execution.mdc` | No enforcement of propagation (user wants no cursor rule changes) |

### Improvement Options

1. **New Rule**: Create shaping-decision-propagation.mdc — REJECTED (user wants no cursor rules)
2. **Modify Existing Rule**: Add to plan-execution.mdc — REJECTED (user wants no cursor rules)
3. **Update System File**: Modify shape-template.md — SELECTED
4. **Add Constraint**: Global constraint file — REJECTED (user wants no cursor rules)
5. **Alternative Approach**: Bi-directional links — More complex than needed

---

## Proposed Solution

Update `_bmad/rbtv/workflows/plan-lifecycle/templates/shape-template.md`:

### Change 1: Rename Section

| Current | New |
|---------|-----|
| `## Execution Log` | `## Decisions and Discoveries` |

### Change 2: Simplify Entry Format

Remove routine task completion logging. Only capture:
- Decisions made during execution (with rationale)
- Discoveries that change prior decisions
- Unexpected constraints or context

### Change 3: Add Propagation Checklist to Discovery Format

```markdown
### Discovery [N] (from task [id])
**Date:** YYYY-MM-DD
**Finding:** [What was discovered]
**Contradicts:** [Reference to original shaping section, if any]
**Resolution:**
- [ ] Simple fix applied immediately
- [ ] New task added: [task-id]

**Propagation Checklist:**
| Status | Task/File | Action Taken |
|--------|-----------|--------------|
| Completed | [task-id or file path] | Annotated with "⛔ SUPERSEDED — See Discovery N" |
| Pending | [task-id or file path] | Updated to reflect new decision |

**Details:** [Explanation]
```

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | `_bmad/rbtv/workflows/plan-lifecycle/templates/shape-template.md` |
| Scope of change | Moderate — rename section, update entry format, add propagation checklist |
| Related files | Existing shape.md files in active plans may optionally be updated to new format |

---

## Rationale

The template itself becomes the enforcement mechanism. Agents are required to follow the template format when adding entries. By including the propagation checklist in the Discovery entry format:

1. Agents cannot complete a Discovery entry without addressing affected tasks
2. The checklist creates an explicit record of what was propagated
3. No additional cursor rules are needed — the workflow template is self-enforcing
4. Renaming to "Decisions and Discoveries" clarifies that routine status should not be logged

---

## Acceptance Criteria

- [ ] "Execution Log" renamed to "Decisions and Discoveries" in shape-template.md
- [ ] Entry format updated to exclude routine task completion status
- [ ] Discovery entry format includes Propagation Checklist with Status/Task/Action columns
- [ ] Template instructions clarify: only capture decisions, discoveries, and unexpected constraints
- [ ] Usage Instructions section updated to reflect new behavior

---

## Related Files

| File | Relationship |
|------|--------------|
| `_bmad/rbtv/workflows/plan-lifecycle/templates/shape-template.md` | Primary file to modify |
| `.cursor/plans/business innovation migration/business-innovation-migration_v3/shape.md` | Example of current format; may optionally migrate |
| `projects/planning-artifacts/compound-audit_trail_invalidation_protocol.md` | Related compound about decision documentation |

---

## References

- Conversation context: Business Innovation Migration plan execution
- Discovery 1 in shape.md: founder-diary elimination (propagation done manually by user)
- Discovery 2 in shape.md: output folder structure change

---

## Discussion Notes

### Selected Improvement Option
Update shape-template.md only (no cursor rules)

### Implementation Preferences
- **File Location:** `_bmad/rbtv/workflows/plan-lifecycle/templates/shape-template.md`
- **Scope:** Moderate
- **Priority:** Medium

### Additional Context
- User manually added "⛔ CANCELLED — See Discovery 1" — this should be automatic
- "Execution Log" name implies logging everything; rename clarifies intent
- Only capture what matters in one month, not routine status
