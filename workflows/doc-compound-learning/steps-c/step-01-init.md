---
stepNumber: 1
stepName: 'init'
nextStepFile: ./step-02-self-assessment.md
templateFile: ../templates/compound-prd.md
outputFile: '{outputFolder}/{filename}.md'
advancedElicitationTask: '{project-root}/_bmad/core/workflows/advanced-elicitation/workflow.xml'
---

# Step 01: Initialize Workflow

**Purpose:** Detect workflow context, determine sub-mode (Create/Validate/Edit), create output document from template.

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Check for Yolo Flag

- Inspect the command invocation context
- If invoked with `:yolo` suffix → Set `yoloMode = true`
- Otherwise → Set `yoloMode = false`

### 2. Determine Sub-Mode

- Scan `{outputFolder}` for existing compound PRDs
- If no existing PRD found → Route to **Create** mode
- If existing PRD found → Ask user: "Resume existing workflow or start new?"
  - If resume → Load existing PRD, check `stepsCompleted`, route to continuation
  - If new → Continue with Create mode
- **Note:** For initial implementation, always route to Create mode. Validate/Edit modes are future additions.

### 3. Load Template

- Read `{templateFile}` from frontmatter
- If template not found → Display error, present Retry/Exit menu
- Store template content in memory

### 4. Create Output Document

- Generate filename suggestion based on conversation context
- Ask user for confirmation or override
- Create new document using template structure
- Populate frontmatter:

```yaml
---
title: 'Compound: {improvement-title}'
docType: 'compound'
mode: 'create'
stepsCompleted: []
inputDocuments: []
outputPath: '{outputFolder}'
date: '{current-date}'
yoloMode: {true|false}
---
```

### 5. Update State

- Add `step-01-init.md` to `stepsCompleted` array
- Save output document to memory (not yet to disk)

### 6. Present Menu

- Present the following menu and HALT
- Wait for user selection

---

## MENU

Present the following menu and HALT. Wait for user selection.

**Options:**
- `[C] Continue` → Load and execute `step-02-self-assessment.md`
- `[AE] Advanced Elicitation` → Load and execute `{advancedElicitationTask}`, then return and redisplay this step's menu
- `[X] Exit Workflow` → Save current state in frontmatter, exit agent

---

## NEXT STEP

On Continue selection:
1. Update output document frontmatter: add `step-01-init.md` to `stepsCompleted` array
2. Load and execute: `./step-02-self-assessment.md`

---

## ERROR HANDLING

**Missing Template File:**
```
❌ Template Error

Cannot load template: {templateFile}

This template is required to create the output document.

Options:
[R] Retry — Attempt to load template again
[X] Exit — Exit workflow
```

---

## SUCCESS CRITERIA

- ✅ Output document created with valid frontmatter (all required fields present)
- ✅ `yoloMode` flag correctly set based on invocation (true if `:yolo` suffix, false otherwise)
- ✅ `stepsCompleted` array contains exactly one entry: `step-01-init.md`
- ✅ Menu presented with explicit HALT and execution stopped
