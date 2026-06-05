---
name: 'step-01b-continue'
description: 'Resume workflow from previous session'

# File References
workflowFile: '../workflow.md'
outputFile: '{outputFolder}/conversion-optimization.md'
---

# Step 1B: Workflow Continuation

---

## STEP GOAL

Resume the workflow from where it was left off, ensuring smooth continuation without loss of context.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input
- READ the complete step file before taking any action
- CRITICAL: When loading next step with 'C', ensure entire file is read
- YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are a YC mentor. Continue your existing persona and communication style.

### Step-Specific Rules
- Focus ONLY on analyzing and resuming workflow state
- FORBIDDEN to modify content completed in previous steps
- Maintain continuity with previous sessions
- DETECT exact continuation point from `stepsCompleted` in `{outputFile}`

---

## MANDATORY SEQUENCE

### 1. Analyze Current State

Read `{outputFile}` frontmatter to determine:
- `stepsCompleted`: Which steps are done (last entry = last completed step)
- `lastStep`: Name of last completed step
- `date`: Original workflow start date
- `inputDocuments`: Documents loaded during initialization

### 2. Read Completed Step Files

For each step in `stepsCompleted` (excluding step-01-init):
1. Read the step file to understand what it accomplished
2. Find the `nextStepFile` reference — the last file's `nextStepFile` is where to resume

### 3. Review Previous Output

Read the complete `{outputFile}`:
- Content generated so far
- Sections completed vs pending
- User decisions and preferences

### 4. Determine Next Step

From the last completed step file:
1. Find its `nextStepFile` reference
2. Validate the file exists
3. Confirm the workflow is incomplete

### 5. Welcome Back Dialog

Present context-aware welcome:
- What steps are complete
- What was last worked on
- What the next step is
- Ask: "Has anything changed since our last session?"

### 6. Present Menu Options

**Resuming workflow — Select an Option:**
- **[C] Continue** — proceed to next step

**Menu handling:** When [C] is selected, add `lastContinued: {current date}` to `{outputFile}` frontmatter, then load the next step file determined in section 4.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update `{outputFile}` frontmatter with `lastContinued` timestamp
2. Load the next step file determined from the analysis
3. Do NOT modify any content in the output document during this step

---

## SUCCESS / FAILURE METRICS

SUCCESS: Correctly identified last step from `stepsCompleted`, user confirmed readiness, frontmatter updated with continuation timestamp, resumed at correct next step

FAILURE: Skipping state analysis, modifying previous step content, loading wrong next step, proceeding without user confirmation
