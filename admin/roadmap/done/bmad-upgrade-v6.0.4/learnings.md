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

### L1: Config path variables should not self-reference (2026-03-08)

**Context:** During p3-5, I initially set `_config/config.yaml` `paths.bmad_output` to `"{bmad_output}"` — a circular self-reference. The variable is supposed to PROVIDE the value, not reference itself.

**Learning:** Path variable configs that declare resolution values must contain concrete defaults, not variable references. The installer can update the default at install time, but the source file must always have a valid fallback.

**Compound Readiness:**
- [x] Clear root cause identified
- [x] Concrete fix implemented (set default + added installer update logic)
- [x] No conflicting patterns
- [x] Implementation path clear

### L2: Mirror mismatch is expected when mirror is not bulk-updated (2026-03-08)

**Context:** p4-refs flagged that `ana.md` references `workflow-create-prd.md` which doesn't exist in the BMAD mirror (Beta.4 baseline) but does exist in v6.0.4. This is expected because the plan deliberately skips bulk mirror replacement.

**Learning:** When upgrading BMAD compatibility without bulk-updating the mirror, agent references will point to v6.0.4 paths that don't exist in the mirror. This only affects admin mode (which resolves `{bmad_bmm}` to the mirror). In installed mode, the actual BMAD installation has the correct files.

**Compound Readiness:**
- [x] Clear root cause identified
- [x] Known limitation, not a bug
- [ ] No conflicting patterns — admin mode will see broken paths until mirror is updated
- [ ] Implementation path clear — future work: update mirror contents or add note to admin mode docs

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
