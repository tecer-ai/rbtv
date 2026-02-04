---
stepNumber: 2
stepName: 'execute-work'
nextStepFile: ./step-03-document.md
dataFile: ../data/execution-protocol.md
judgeTask: '{project-root}/_bmad/rbtv/tasks/judge.xml'
---

# Step 02: Execute Task and Quality Gate

**Purpose:** Execute the current task and invoke judge for quality evaluation.

**This is Step 2 of the 3-step guardrail workflow.**

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Display Task

Show the current task clearly:

```
## Current Task

**ID:** {task-id}
**Description:** {task-description}
**Phase:** {phase-name}

---

Ready to begin work on this task.
```

### 2. Check Task Type

Determine if this is a special task:

| Task Type | Behavior |
|-----------|----------|
| Regular task | Execute work, invoke judge |
| Checkpoint | Stop and wait for human approval |
| Phase condensation | Merge execution decisions, skip judge |
| File reference review | Update references, append to phase file |
| Final condensation | Merge phase files, skip judge |

**If Checkpoint:**
1. Mark checkpoint `in_progress`
2. Present completed work summary
3. Display: "⏸️ CHECKPOINT - Waiting for human approval"
4. HALT and wait for approval
5. After approval: mark `completed`, proceed to next task

### 3. Execute Work

For regular tasks:
- Perform the work described in the task
- Follow task requirements exactly
- Make implementation decisions as needed (plans describe WHAT, agent decides HOW)

### 4. Invoke Judge (Mandatory Quality Gate)

**CRITICAL — Before marking any regular task complete, invoke judge.**

Use Task tool with `subagent_type='judge'`:

```
Provide to judge:
1. Task description: {task-description}
2. Work completed: {summary of what was done}
3. Files modified: {list of files}
4. Decisions made: {key decisions and rationale}
```

### 5. Handle Judge Response

**If APPROVED:**
- Proceed to step-03 (document execution decisions)

**If REJECTED (attempts < 10):**
- Review judge feedback
- Address specific issues raised
- Retry the work
- Invoke judge again
- Repeat until approved or max attempts

**If REJECTED (attempts = 10):**
- Stop execution
- Escalate to user with:
  - Full iteration history
  - Rejection patterns
  - Recommendations

Display escalation:

```
## ⚠️ Escalation Required

This task has been rejected 10 times. Human intervention needed.

**Task:** {task-description}

**Rejection History:**
- Attempt 1: {rejection reason}
- Attempt 2: {rejection reason}
...

**Patterns Observed:**
- {Pattern 1}
- {Pattern 2}

**Recommendations:**
- {Recommendation 1}
- {Recommendation 2}

Please review and provide guidance.
```

### 6. Track Attempts

Maintain attempt count for current task:
- Increment on each judge invocation
- Reset when moving to new task
- Use for escalation decision

### 7. Present Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**If approved:**
- `[C] Continue` → Document execution decisions (step-03)
- `[R] Review Work` → Show what was done before documenting
- `[X] Exit` → Save state and exit

**If rejected (attempts < 10):**
- `[F] Fix Issues` → Address feedback and retry
- `[E] Escalate` → Force escalation to user
- `[X] Exit` → Save state and exit

---

## NEXT STEP

On Continue selection (after approval):
1. Store judge approval in session memory
2. Load and execute: `./step-03-document.md`

---

## SUCCESS CRITERIA

- ✅ Task work executed per description
- ✅ Judge invoked with complete context
- ✅ Judge approval received (or escalation completed)
- ✅ Attempt tracking accurate
- ✅ Checkpoint handling correct (if applicable)
- ✅ Menu presented with explicit HALT
