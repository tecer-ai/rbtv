---
stepNumber: 1
stepId: init
nextStepFile: ./step-02-discover.md
continueStepFile: './step-01b-continue.md'
outputFile: "{output_folder}/structured-problem-{date}.md"
---

# Step 1: Initialize Problem Structuring

**Goal:** Establish context and create output document with initial problem statement.

---

## MANDATORY SEQUENCE

### 1. Context Capture

Ask the user to describe their problem or situation. Accept whatever level of clarity they have — vague is expected.

**Prompt:**
> "Describe the problem, challenge, or situation you want to structure. Don't worry about being precise — that's what we'll build together. What's on your mind?"

### 2. Initial Assessment

After user responds, assess:

| Dimension | Question | Note |
|-----------|----------|------|
| **Clarity** | How well-defined is the problem? | Scale: Vague → Emerging → Clear |
| **Scope** | Is this one problem or multiple? | May need to separate |
| **Type** | Diagnostic, Solution-seeking, or Decision? | Guides tree structure |
| **Stakeholders** | Who is affected? Who decides? | Important for framing |

### 3. Create Output Document

Create the output document with this structure:

```markdown
---
type: structured-problem
status: in-progress
stepsCompleted: []
created: {date}
problemType: {diagnostic|solution|decision}
---

# Problem Structuring: {Working Title}

## Initial Statement

{User's original description, captured verbatim}

## Context Assessment

| Dimension | Assessment |
|-----------|------------|
| Clarity | {rating} |
| Scope | {single/multiple} |
| Type | {diagnostic/solution/decision} |
| Key Stakeholders | {list} |

## Refined Problem Statement

{To be completed in Step 3}

## Problem Tree

{To be completed in Step 3}

## MECE Categories

{To be completed in Step 3}

## Pyramid Summary

{To be completed in Step 4}
```

### 4. Confirm Understanding

Present your initial assessment to the user:

> "Based on what you've shared, here's my initial read:
> - **Problem Type:** [Diagnostic/Solution/Decision]
> - **Clarity Level:** [Vague/Emerging/Clear]
> - **Scope:** [Single problem / Multiple intertwined problems]
>
> Does this feel right? Should we adjust anything before diving deeper?"

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 2: Framework Selection & Deep Discovery |
| **[R] Revise** | Adjust the initial assessment based on user feedback |
| **[AE] Advanced Elicitation** | Use Socratic questioning to surface hidden aspects |
| **[Q] Questions** | User has questions about the process |

---

## ON CONTINUE

1. Update output document frontmatter: add "step-01-init" to `stepsCompleted`
2. Save output document
3. Load `./step-02-discover.md`
