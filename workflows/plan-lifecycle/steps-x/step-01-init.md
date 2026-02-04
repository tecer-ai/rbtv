---
stepNumber: 1
stepName: 'execute-init'
nextStepFile: ./step-02-execute.md
dataFile: ../data/execution-protocol.md
---

# Step 01: Initialize Plan Execution

**Purpose:** Load plan, identify current task, and read prior execution decisions.

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Load Execution Protocol

- Read `{dataFile}` from frontmatter
- Store the 3-step guardrail workflow rules in memory

### 2. Locate Plan File

Determine which plan to execute:
- If user referenced a specific `*.plan.md` file → Use that file
- If user said "continue plan" or similar → Search `.cursor/plans/` for recent plans
- If multiple plans found → Ask user to select

### 3. Load Plan

Read the plan file completely:
- Parse YAML frontmatter for `todos` array
- Identify task statuses: `pending`, `in_progress`, `completed`

### 4. Determine Current Task

Find the next task to execute:

1. If any task is `in_progress` → Resume that task
2. Otherwise → Find first `pending` task
3. If all tasks `completed` → Plan is done, exit

Display current state:

```
## Plan Execution Status

**Plan:** {plan-name}
**Progress:** {completed}/{total} tasks

**Completed Tasks:**
- [x] p1-1: {description}
- [x] p1-2: {description}

**Current Task:**
- [ ] p2-1: {description}

**Remaining Tasks:**
- [ ] p2-2: {description}
- [ ] p2-checkpoint: {description}
```

### 5. Read Prior Execution Decisions

**MANDATORY — This is Step 1 of the 3-step guardrail.**

- Scan `.cursor/plans/{plan-name}/` for all `*_execution_decisions.md` files
- Read each file to understand:
  - What decisions were made in prior tasks
  - What issues were encountered
  - What files were modified

Display summary:

```
## Prior Execution Context

**Decisions that affect this task:**
- [Decision from prior task]

**Issues to be aware of:**
- [Issue from prior task]
```

### 6. Load Files from Plan

Check the plan's "Files to Load" table:
- For current phase, identify required files
- Load files marked for this phase/task
- Summarize loaded context

### 7. Present Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**Options:**
- `[C] Continue` → Proceed to task execution (step-02)
- `[S] Select Different Task` → Choose a specific task to work on
- `[V] View Plan` → Display the complete plan
- `[X] Exit` → Exit plan execution

---

## NEXT STEP

On Continue selection:
1. Store current task in session memory
2. Load and execute: `./step-02-execute.md`

---

## SUCCESS CRITERIA

- ✅ Plan file loaded and parsed
- ✅ Current task identified correctly
- ✅ Prior execution decisions read (Step 1 of 3-step guardrail)
- ✅ Required context files loaded
- ✅ Execution status displayed to user
- ✅ Menu presented with explicit HALT
