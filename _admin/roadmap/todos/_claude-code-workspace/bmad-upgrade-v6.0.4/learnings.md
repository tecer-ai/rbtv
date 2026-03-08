# Learnings - BMAD Upgrade v6.0.4

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

<!-- Learning entries will be appended below this line -->

---

## Compound Generation

When learnings accumulate, the final plan task (`p4-compound`) processes them:

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
