---
stepNumber: 2
stepName: 'context'
nextStepFile: ./step-03-structure.md
---

# Step 02: Gather Context

**Purpose:** Collect complete context required for a zero-context, self-contained plan.

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Context Gap Analysis

Review what is known vs. what is needed. Plans require:

| Section | Status | Details |
|---------|--------|---------|
| Problem Statement | [Known/Missing] | What problem does this solve? |
| User Goals | [Known/Missing] | What does success look like? |
| Constraints | [Known/Missing] | What limitations exist? |
| Decisions Made | [Known/Missing] | What has already been decided? |
| Rejected Alternatives | [Known/Missing] | What approaches were considered but rejected? |
| Files to Load | [Known/Missing] | What files must executing agents read? |

### 2. Fill Gaps with Targeted Questions

For each **Missing** section, ask ONE targeted question:

**Problem Statement** (if missing):
"What specific problem are you trying to solve? Describe the current state and desired state."

**User Goals** (if missing):
"What does success look like? What should be true when this plan is complete?"

**Constraints** (if missing):
"Are there any constraints I should know about? (Technical limitations, time constraints, dependencies, etc.)"

**Decisions Made** (if missing):
"Have you already made any decisions about the approach? (Technology choices, scope decisions, etc.)"

**Rejected Alternatives** (if missing):
"Have you considered and rejected any approaches? (Helps future agents understand why not.)"

**Files to Load** (if missing):
"What files should agents read before working on this plan? (Documentation, related code, etc.)"

Ask questions one at a time. Wait for response before next question.

### 3. Document Context

Compile all gathered information — this will be written to shape.md during step-04.

### 4. Prepare Companion Files Content

Gather content for companion files that will be created during finalization.

**shape.md content** — Scope and shaping decisions:
- Scope boundaries (IN/OUT)
- Key decisions made during planning with rationale
- Constraints identified
- User inputs captured verbatim
- Standards that apply to this plan

**learnings.md content** — System improvement queue:
- This file captures meta-learnings about BMAD/RBTV
- NOT for project-specific learnings
- Will be populated during execution when user provides corrections/suggestions

### 5. Present Summary

Display the compiled context to user:

```
Here's the complete context I've gathered for your plan:

[Display compiled Context section]

Companion files will be created during finalization:
- shape.md (scope, constraints, shaping decisions, append-only execution log)
- learnings.md (system improvement queue for BMAD/RBTV meta-learnings)

Is this complete and accurate?
```

Wait for confirmation.

### 6. Present Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**Options:**
- `[C] Continue` → Proceed to plan structure creation (step-03)
- `[R] Refine` → Modify or add to the context
- `[X] Exit Workflow` → Cancel plan creation

---

## NEXT STEP

On Continue selection:
1. Store compiled context in session memory
2. Load and execute: `./step-03-structure.md`

---

## SUCCESS CRITERIA

- ✅ All six context sections populated (problem, goals, constraints, decisions, rejected, files)
- ✅ Content prepared for shape.md and learnings.md companion files
- ✅ User confirmed context is complete and accurate
- ✅ Context is detailed enough for zero-context execution (another agent could understand without additional context)
- ✅ Menu presented with explicit HALT
