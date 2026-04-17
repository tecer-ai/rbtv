---
stepNumber: 3
stepId: structure
nextStepFile: ./step-04-deliver.md
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 3: Structure the Problem

**Goal:** Build the problem tree, apply MECE validation, and refine the problem statement.

---

## MANDATORY SEQUENCE

### 1. Draft Problem Tree

Based on discovered context, build the problem tree:

**Layer 1 (Root):** Frame the core question as Yes/No hypothesis
- Diagnostic: "Why is [problem] occurring?"
- Solution: "How can we [achieve goal]?"
- Decision: "Should we [take action]?"

**Layer 2:** Identify 2-5 MECE categories
- Use established frameworks when applicable (Revenue/Cost, 3Cs, 4Ps)
- Frame as Yes/No hypotheses

**Layer 3:** Break each category into 2-4 sub-questions
- Transition to open-ended questions
- Connect to specific data needs

**Layer 4 (if needed):** Specific data points or analyses required

### 2. Present Draft Tree

Present the tree visually using text formatting:

```
[Root Question]
│
├── [Category 1 - Hypothesis]
│   ├── [Sub-question 1.1]
│   ├── [Sub-question 1.2]
│   └── [Sub-question 1.3]
│
├── [Category 2 - Hypothesis]
│   ├── [Sub-question 2.1]
│   └── [Sub-question 2.2]
│
└── [Category 3 - Hypothesis]
    ├── [Sub-question 3.1]
    └── [Sub-question 3.2]
```

### 3. MECE Validation

For each horizontal level, verify MECE:

| Level | ME Test | CE Test | Issues Found |
|-------|---------|---------|--------------|
| Layer 2 | No overlaps? | All covered? | {any gaps or overlaps} |
| Layer 3a | No overlaps? | All covered? | {any gaps or overlaps} |
| Layer 3b | No overlaps? | All covered? | {any gaps or overlaps} |
| ... | ... | ... | ... |

Present validation results:
> "I've tested each level for MECE compliance:
> - ✅ [Level]: Passes both tests
> - ⚠️ [Level]: [Issue found - gap/overlap] — suggested fix: [fix]"

### 4. Refine Problem Statement

Now that the structure is clear, craft a refined problem statement:

**Format:**
> "[Stakeholder] needs to [understand/decide/solve] [specific issue] in order to [achieve outcome], constrained by [key constraints]."

**Example:**
> "The leadership team needs to understand why customer churn increased 15% in Q3 in order to reduce it to historical levels (8%), constrained by a limited budget for retention initiatives."

### 5. Update Output Document

Add to output document:

```markdown
## Refined Problem Statement

{Refined problem statement}

## Problem Tree

{ASCII tree visualization}

## MECE Validation

| Level | Status | Notes |
|-------|--------|-------|
{validation results}

## Priority Branches

{List the 2-3 branches most likely to yield answers, with reasoning}
```

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 4: Deliver Summary |
| **[RT] Revise Tree** | Modify the problem tree structure |
| **[RS] Revise Statement** | Refine the problem statement |

**Menu handling:** When [PM] is selected, execute {partyModeWorkflow} then redisplay this menu.

---

## ON CONTINUE

1. Update output document frontmatter: add "step-03-structure" to `stepsCompleted`
2. Save output document
3. Load `./step-04-deliver.md`
