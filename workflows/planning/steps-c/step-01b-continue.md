---
stepNumber: 1
stepId: continue
workflowFile: '../workflow.md'
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

### Step-Specific Rules
- Focus ONLY on analyzing and resuming workflow state
- FORBIDDEN to modify content completed in previous steps
- Maintain continuity with previous sessions

---

## MANDATORY SEQUENCE

### 1. Locate Plan Artifacts

Search the output path for the plan folder. Look for:
- `{plan-name}-plan.md` — the main plan file
- `shape.md` — companion file with execution context
- Phase folders with task files

### 2. Analyze Current State

Read the plan file and shape.md to determine:
- Which tasks are completed (checked `[x]` in task list)
- Which task was last worked on
- Any decisions or discoveries logged in shape.md

### 3. Review Completed Work

Read shape.md Decisions and Discoveries section to understand:
- What was done in prior sessions
- Any direction changes or discoveries
- Current execution context

### 4. Determine Next Task

From the plan's task list:
1. Find the first unchecked (`[ ]`) task
2. If it has a task file (`→ path`), note the path
3. Confirm the workflow is incomplete

### 5. Welcome Back Dialog

Present context-aware welcome:
- What tasks are complete
- What was last worked on
- What the next task is
- Ask: "Has anything changed since our last session?"

### 6. Present Menu Options

**Resuming workflow — Select an Option:**
- **[C] Continue** — proceed to next task

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Load the next task's micro-step file (if it has one) or present the inline task description
2. Do NOT modify any content during this step
