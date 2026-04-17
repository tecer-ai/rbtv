# Learnings - Align Skills with Anthropic Spec

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

### Learning 1: Plan Mode CreatePlan Bypasses Plan Workflow

**Source:** Pre-planning | Date: 2026-03-10

**Trigger:** Plan was created via Cursor's CreatePlan tool in Plan mode, completely bypassing the plan-lifecycle workflow
- [x] Unexpected friction

**Category:**
- [x] Workflow gap or missing step

**User's Exact Words:**
> "I WANT U TO REVIEW THE PLAN CRETED AS IT DID NOT FOLLOW THIS WORKFLOW AND ADAPT IT"

**Recommended System Change:**

| Aspect | Value |
|--------|-------|
| Target | Plan workflow documentation or plan skill |
| Type | Clarify instruction |
| Proposed Change | Document that `/bmad-rbtv-plan` must be used for plan creation, not Cursor's native CreatePlan tool in Plan mode. The native tool produces flat task lists without phases, checkpoints, companion files, or micro-steps. |

**Compound Readiness:**
- [x] Self-contained (no dependencies on other learnings)
- [x] Clear implementation path
- [x] Validated by user feedback
- [ ] Ready for compound generation

<!-- Learning entries will be appended below this line -->
