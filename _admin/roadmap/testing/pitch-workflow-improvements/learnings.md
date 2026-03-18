# Learnings - Pitch Workflow Improvements

> **Purpose:** This document captures system improvement opportunities for BMAD/RBTV discovered during plan execution. These are META-learnings about how the system could be improved, NOT project-specific learnings.

---

## What Belongs Here

| Include | Exclude |
|---------|---------|
| User corrections to agent behavior | Project-specific decisions |
| Missing rules or unclear instructions | Implementation details |
| Workflow gaps or friction points | Task-specific context |
| Tool limitations discovered | Bug fixes (those go in code) |
| Better patterns identified | Feature requests (those go elsewhere) |

---

## Learning Entries

> **APPEND-ONLY:** Add entries as learnings are discovered. Never modify or delete previous entries.

### Entry Format

```markdown
### Learning [N]: {Brief Title}

**Source:** Task {task-id} | Date: YYYY-MM-DD

**Trigger:** {What happened that revealed this learning}
- [ ] User correction
- [ ] User suggestion
- [ ] Unexpected friction
- [ ] Tool limitation
- [ ] Pattern discovery

**Category:**
- [ ] Missing rule in BMAD/RBTV
- [ ] Unclear instruction that caused confusion
- [ ] Workflow gap or missing step
- [ ] Tool capability gap
- [ ] Better pattern than current approach

**User's Exact Words:**
> "{Quote the user if applicable}"

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | {Which BMAD/RBTV file or component} |
| Type | {Add rule | Clarify instruction | New template | Tool enhancement} |
| Proposed Change | {Specific change to make} |

**Compound Readiness:**
- [ ] Self-contained (no dependencies on other learnings)
- [ ] Clear implementation path
- [ ] Validated by user feedback
- [ ] Ready for compound generation
```

<!-- Learning entries will be appended below this line -->

### Result: No Compound-Ready Learnings

**Date:** 2026-03-17

No meta-learnings were captured during plan execution. Three discoveries were logged in shape.md (step-09 stale references, progress line updates, path discrepancy in shape.md references table), but all were project-specific observations, not system-level improvements:

- **Step-09 stale references:** Pre-existing content inconsistencies in step-09's summary sections (cosmetic, not systemic)
- **Progress line updates:** Expected mechanical side effect of adding a new step — no workflow gap
- **Shape.md path discrepancy:** Error in the plan's own reference table, not a repeatable system issue; task files and compound docs had correct paths

**Compound output:** None. No system changes warranted.

---

## Compound Generation

When learnings accumulate, the final plan task (`pN-compound`) processes them:

### Compound Criteria

A learning is compound-ready when:
1. All four checkboxes in Compound Readiness are checked
2. Implementation path is clear and specific
3. No conflicting learnings exist

### Compound Process

1. Review all learnings marked compound-ready
2. Group related learnings by target component
3. Generate compound documents for implementation
4. Mark processed learnings (append "Compounded: YYYY-MM-DD" line)

### Compound Output

For each group of related learnings:

```markdown
## Compound: {Component Name} Improvements

**Source Learnings:** L1, L5, L8
**Target:** {File path}

### Changes

1. {Change 1 from L1}
2. {Change 2 from L5}
3. {Change 3 from L8}

### Implementation Notes

{How to apply these changes together}
```
