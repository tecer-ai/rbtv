# Continuation Step Template

Use this template to create a step-01b-continue.md that handles workflow resumption across sessions. Pair with `step-init-continuable-template.md` for the step-01-init.md file.

---

## Template

```markdown
---
name: 'step-01b-continue'
description: 'Resume workflow from previous session'

# File References
workflowFile: './workflow.md'
outputFile: '{output_folder}/{output-name}.md'
---

# Step 1B: Workflow Continuation

---

## STEP GOAL

Resume the workflow from where it was left off, ensuring smooth continuation without loss of context.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are a {role}. Continue your existing persona and communication style.

### Step-Specific Rules
- 🎯 Focus ONLY on analyzing and resuming workflow state
- 🚫 FORBIDDEN to modify content completed in previous steps
- 💬 Maintain continuity with previous sessions
- 🚪 DETECT exact continuation point from `stepsCompleted` in `{outputFile}`

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
- **[C] Continue** — proceed to {next step name}

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

✅ **SUCCESS:** Correctly identified last step from `stepsCompleted`, user confirmed readiness, frontmatter updated with continuation timestamp, resumed at correct next step

❌ **FAILURE:** Skipping state analysis, modifying previous step content, loading wrong next step, proceeding without user confirmation
```

---

## Field Instructions

### Frontmatter
- **name**: Always `step-01b-continue` for continuation steps
- **description**: Describe what workflow this continues
- **workflowFile**: Path to parent workflow.md
- **outputFile**: Path to existing output document (same as init step's outputFile)

### Key Differences from Regular Steps

| Aspect | Regular Step (step-template.md) | Continuation Step (this template) |
|--------|--------------------------------|-----------------------------------|
| nextStepFile | Static reference in frontmatter | Dynamically determined from output state |
| Content modification | Appends new content | NEVER modifies existing content |
| Menu options | A/P/C (full menu) | C only (resume action) |
| Purpose | Produce new content | Analyze state and route |

### When to Use This Template

Use when creating a workflow that:
- Supports multi-session completion
- Tracks progress via `stepsCompleted` frontmatter
- Has an init step built from `step-init-continuable-template.md`

### Paired Template

This template MUST be paired with `step-init-continuable-template.md` which creates the init step that routes to this continuation step.

---

## Size Guidelines

| Metric | Target | Max |
|--------|--------|-----|
| Total lines | 80-120 | 150 |
| Sequence actions | 5-6 | 7 |

---

## Common Mistakes

1. **Modifying previous step content** — This step ONLY analyzes and routes; never edit existing content

2. **Skipping state analysis** — MUST read all completed steps to understand context

3. **Loading wrong next step** — Always derive the next step from the last completed step's `nextStepFile`

4. **Not confirming with user** — Always present welcome-back dialog and wait for confirmation
