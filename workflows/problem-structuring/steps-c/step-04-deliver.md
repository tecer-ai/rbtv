---
stepNumber: 4
stepId: deliver
nextStepFile: null
---

# Step 4: Deliver Summary

**Goal:** Create pyramid-structured summary and finalize the deliverable.

---

## MANDATORY SEQUENCE

### 1. Build Pyramid Summary

Using the Pyramid Principle, create a communication-ready summary:

**Top of Pyramid (Main Message):**
> "[One sentence capturing the refined problem statement]"

**Supporting Arguments (2-4 key points):**
Each supporting argument should:
- Connect directly to the main message
- Be backed by evidence from the problem tree
- Be MECE with other supporting arguments

**Evidence Layer:**
For each supporting argument, note:
- What data/analysis would prove or disprove
- What we already know
- What remains uncertain

### 2. Present Pyramid Summary

Format for output document:

```markdown
## Pyramid Summary

### Main Message
{One sentence problem statement}

### Supporting Arguments

**1. {Argument 1}**
- Evidence: {what supports this}
- Data needed: {what to investigate}

**2. {Argument 2}**
- Evidence: {what supports this}
- Data needed: {what to investigate}

**3. {Argument 3}**
- Evidence: {what supports this}
- Data needed: {what to investigate}

### Communication Guide

If you have **5 minutes:** Present Main Message + 3 Supporting Arguments
If you have **2 minutes:** Present Main Message + top 2 Arguments
If you have **30 seconds:** Present Main Message only
```

### 3. Identify Next Steps

Based on the structured problem, recommend next actions:

| Next Step | Purpose | Priority |
|-----------|---------|----------|
| {Action 1} | {What it will accomplish} | High/Medium/Low |
| {Action 2} | {What it will accomplish} | High/Medium/Low |
| {Action 3} | {What it will accomplish} | High/Medium/Low |

Add to output document:

```markdown
## Recommended Next Steps

| # | Action | Purpose | Priority |
|---|--------|---------|----------|
| 1 | {action} | {purpose} | {priority} |
| 2 | {action} | {purpose} | {priority} |
| 3 | {action} | {purpose} | {priority} |
```

### 4. Finalize Document

Update output document:
- Set `status: complete` in frontmatter
- Add "step-04-deliver" to `stepsCompleted`
- Add completion timestamp

### 5. Present Final Deliverable

Present summary to user:

> "**Problem Structuring Complete**
>
> **Problem Statement:** {refined statement}
>
> **Key Branches to Investigate:**
> 1. {priority branch 1}
> 2. {priority branch 2}
>
> **Recommended Next Step:** {highest priority action}
>
> Your complete structured problem document has been saved to: {output_file_path}"

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[PS] Problem Solving** | Offer two approaches and let user choose (see ON PROBLEM SOLVING) |
| **[R] Revise** | Go back and modify any section |
| **[E] Export** | Copy final document content to clipboard |
| **[N] New Problem** | Start fresh with a different problem |
| **[D] Done** | Return to domcobb agent menu |

---

## ON PROBLEM SOLVING

If user selects [PS]:

Present two approaches and let the user choose:

| Option | Skill | Best for |
|--------|-------|----------|
| **[AE] Advanced Elicitation** | `bmad-pro-skills:bmad-advanced-elicitation` | Deep critique, first-principles analysis, pre-mortem, red-teaming |
| **[BR] Brainstorming** | `bmad-pro-skills:bmad-brainstorming` | Creative ideation, divergent thinking, generating solution options |

Invoke the selected skill. Pass the output document as context.

---

## ON DONE

Return control to the domcobb agent menu.
