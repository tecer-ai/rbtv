---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-context.md
continueStepFile: './step-01b-continue.md'
templateFile: ../templates/plan-template.md
dataFile: ../data/plan-creation-rules.md
---

# Step 01: Initialize Plan Creation

**Purpose:** Detect context, determine plan scope, resolve output path, and create output structure.

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Load Knowledge

- Read `{dataFile}` from frontmatter
- Store task granularity rules, ID format rules, and plan structure requirements in memory

### 2. Context Discovery

Analyze conversation history to identify:
- What is the user trying to accomplish? (problem statement)
- What triggered the need for a plan?
- Are there any constraints mentioned?
- Have any decisions already been made?

### 3. Confirm Understanding

Present discovered context to user:

```
Based on our conversation, I understand you want to:
- [Problem statement]
- [Key goals identified]

Is this correct? Should I proceed with this understanding?
```

Wait for user confirmation before proceeding.

### 4. Generate Plan Name

- Suggest a kebab-case plan name based on the problem (e.g., `implement-auth-system`)
- Ask user: "I suggest the plan name `{suggested-name}`. Use this or provide a different name?"
- Wait for confirmation or alternative

### 5. Resolve Output Path

Follow the `rbtv-output-resolution` rule:
1. Use conversation context to determine the destination (project, area, workspace)
2. Read the relevant CLAUDE.md files for content-routing rules if needed
3. Propose the full resolved path: `{resolved-path}/{plan-name}/`
4. Wait for user confirmation or redirect

### 6. Create Plan Folder Structure

- Create folder: `{output-path}/{plan-name}/`

### 7. Present Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**Options:**
- `[C] Continue` → Proceed to context gathering (step-02)
- `[X] Exit Workflow` → Cancel plan creation

---

## NEXT STEP

On Continue selection:
1. Store plan name and output path in session memory
2. Load and execute: `./step-02-context.md`

---

## SUCCESS CRITERIA

- ✅ User confirmed understanding of problem/goals
- ✅ Plan name agreed upon (kebab-case format)
- ✅ Output path resolved and confirmed
- ✅ Plan folder created
- ✅ Menu presented with explicit HALT
