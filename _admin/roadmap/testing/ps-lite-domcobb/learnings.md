# Learnings - PS Lite Dom Cobb

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

### L1 — Checkpoint auto-continue violation

**Discovery:** Agent bypassed P1 checkpoint approval, moving directly to commit. The plan's inviolable rule "Checkpoints require human approval — never auto-continue" was insufficient to prevent this.
**Root cause:** The checkpoint rule exists in the plan body but is not reinforced at the point of execution. The agent treated verification as a self-assessment rather than a gate.
**Improvement:** Plan checkpoint tasks should include an explicit instruction: "PRESENT results to user. HALT. Do NOT proceed until user confirms."
**Target:** Plan template (`workflows/build-rbtv-component/templates/`) — checkpoint task format.
**Compound readiness:**
- [x] Root cause identified
- [x] Improvement is specific and actionable
- [x] Target component identified
- [x] No conflicting learnings

Compounded: 2026-02-12 → `_admin/roadmap/todos/compound-plan-checkpoint-halt.md`

### L2 — Compound PRD decision overridden by user preference for format consistency

**Discovery:** The compound PRD chose inline `<action>` over workflow. The user overrode this, preferring structural consistency (all menu items use the same format) over the latency benefit of inline actions.
**Root cause:** The PRD's option evaluation weighted technical factors (latency, overhead) but didn't evaluate format consistency as a user-facing quality.
**Improvement:** Compound PRD option evaluation should include a "consistency with existing patterns" criterion alongside technical factors.
**Target:** Compound workflow steps — option evaluation criteria.
**Compound readiness:**
- [x] Root cause identified
- [x] Improvement is specific and actionable
- [x] Target component identified
- [x] No conflicting learnings

Compounded: 2026-02-12 → `_admin/roadmap/todos/compound-prd-consistency-criterion.md`

---

## Compound Generation

When learnings accumulate, the final plan task (`p2-compound`) processes them:

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
