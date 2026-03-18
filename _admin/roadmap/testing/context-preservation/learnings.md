# Learnings - Context Preservation

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

### L1 — High-stakes agent behaviors need forceful framing, not table rows

**Source:** P1 post-checkpoint discovery — agent failed to write self-correction despite rule being active.

**Learning:** When a behavior is critical (must-not-skip), placing it as one row in a trigger table makes it easy to overlook. Reframing as a named subsection with a mandatory sequence (attempt → fail → retry → succeed → **write**) prevents skipping.

**Compound status:** Already applied — memory system rule was updated in P1. No further system change needed. This is a **rule design principle** for future rule creation: critical behaviors get their own subsection with explicit completion criteria, not just a table row.

### L2 — Plan execution must write to canonical source only

**Source:** P2 execution created CP rule in both canonical and workspace locations, doubling file operations and drift risk.

**Learning:** Replication to workspace locations (`.cursor/rules/`, `.cursor/skills/`) is an installer/bootstrap responsibility. Plan tasks must write only to the canonical source (`_bmad/rbtv/_config/claude/rules/`, etc.).

**Compound status:** Compounded: 2026-03-17. Added "Canonical source only" rule to `plan-creation-rules.md` Task Granularity table.

### L3 — Verify created files match planned paths

**Source:** P3 discovery — universal template was placed at `workflows/_shared/templates/` (by P2 executor) but shape.md Key Decisions said `_shared/templates/`. Three files referenced the planned path, not the actual path.

**Learning:** When a task creates a file at a path different from what was planned (even for good reasons), all downstream references must be verified immediately. The p4-refs task caught this, but it could have been caught earlier with a post-creation verification step.

**Compound status:** No rule change needed — the pN-refs task in the final phase serves this purpose. **Observation:** The existing validation mechanism worked as designed.

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
