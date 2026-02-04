---
stepNumber: 2
stepName: 'context'
nextStepFile: ./step-03-structure.md
outputFile: '{outputFolder}/{plan-name}/{plan-name}.plan.md'
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

Compile all gathered information into the plan's Context section:

```markdown
## Context

### Problem Statement
[User's description of the problem]

### User Goals
1. [Goal 1]
2. [Goal 2]

### Constraints
- [Constraint 1]
- [Constraint 2]

### Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| [What was decided] | [Choice made] | [Why] |

### Rejected Alternatives
- [Alternative 1]: [Why rejected]
- [Alternative 2]: [Why rejected]

---

## Files to Load

| File | Purpose | When to Load |
|------|---------|--------------|
| [path] | [Why this file matters] | [Phase/task that needs it] |
```

### 4. Create Spec Artifacts

Create structured artifacts that preserve planning decisions for executors:

**Create in `.cursor/plans/{plan-name}/`:**

**shape.md** — Shaping decisions:
```markdown
# Shape: {plan-name}

## Scope Boundaries
- IN: [What's included]
- OUT: [What's explicitly excluded]

## Key Constraints
- [Constraint 1]
- [Constraint 2]

## Shaping Decisions
| Decision | Choice | Why |
|----------|--------|-----|
| [What was decided] | [Choice] | [Rationale] |
```

**standards.md** — Which rules apply:
```markdown
# Standards: {plan-name}

## Applicable Rules
| Rule File | Why It Applies |
|-----------|----------------|
| [path to rule] | [Relevance to this plan] |

## Patterns to Follow
- [Pattern 1]: [How to apply]
- [Pattern 2]: [How to apply]
```

**references.md** — Key insights from research:
```markdown
# References: {plan-name}

## Documents Studied
| Document | Key Insight |
|----------|-------------|
| [path] | [What we learned] |

## Patterns Extracted
- [Pattern]: [Where it applies in this plan]
```

### 5. Present Summary

Display the compiled context to user:

```
Here's the complete context I've gathered for your plan:

[Display compiled Context section]

Spec artifacts created:
- shape.md (scope and constraints)
- standards.md (applicable rules)
- references.md (research insights)

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
- ✅ Spec artifacts created (shape.md, standards.md, references.md)
- ✅ User confirmed context is complete and accurate
- ✅ Context is detailed enough for zero-context execution (another agent could understand without additional context)
- ✅ Menu presented with explicit HALT
