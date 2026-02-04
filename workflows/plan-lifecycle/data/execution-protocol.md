# Plan Execution Protocol

Knowledge file for plan execution workflow. This defines the 3-step guardrail workflow.

---

## The 3-Step Guardrail Workflow

**MANDATORY:** Any agent executing plan tasks MUST follow this protocol.

### Step 1: Read Execution Decisions

Before starting work on any task:

1. Navigate to `.cursor/plans/{plan-name}/`
2. Read ALL `*_execution_decisions.md` files
3. Understand:
   - What decisions were made in prior tasks
   - What issues were encountered
   - What context carries forward

**Purpose:** Ensures continuity between tasks, prevents repeating mistakes.

### Step 2: Execute and Invoke Judge

1. Execute the work according to task requirements
2. **MANDATORY:** Invoke judge before marking complete
3. Provide required context to judge:
   - Task description
   - Work completed
   - Files modified
   - Decisions made
4. Handle judge response:
   - If approved → Proceed to Step 3
   - If rejected (attempts < 10) → Address feedback, retry
   - If rejected (attempts = 10) → Escalate to user

### Step 3: Write Execution Decisions

After judge approval OR escalation:

1. Create execution decisions file
2. Document:
   - Outcome
   - Key decisions with rationale
   - Issues encountered
   - Files modified
3. Update plan YAML (mark task completed)

---

## Execution Decisions File Format

**Location:** `.cursor/plans/{plan-name}/{task_id}_execution_decisions.md`

**Structure:**

```markdown
# Task {task_id} Execution Decisions

**Task:** {Description}
**Completed:** YYYY-MM-DD
**Attempts:** {N}
**Outcome:** {Approved/Blocked/Required escalation}

---

## Outcome

{Brief summary of what was delivered or why task couldn't be completed}

## Key Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| {Choice made} | {Why} | {Effect on future tasks} |

## Issues Encountered

- {Blocker or surprise that future agents should know}

## Files Modified

- {List of files changed}
```

---

## Dependency Validation

| Scenario | Behavior |
|----------|----------|
| Dependencies in range | Proceed normally |
| Dependencies outside range | Warn user: "(A) Expand, (B) Assume complete, (C) Cancel" |
| Circular dependencies | Error, ask user for resolution |

---

## Checkpoint Handling

Checkpoints require special handling:

1. Complete all preceding work
2. Mark checkpoint `in_progress`
3. Present completed work summary
4. **STOP and WAIT** for human approval
5. After approval: mark `completed`, proceed to next phase

**NEVER skip checkpoints.**

---

## Todo Integration

| Rule | Description |
|------|-------------|
| Use existing todos | Never recreate or duplicate |
| Mark in_progress | Before starting work on a task |
| One at a time | Only one `in_progress` task at a time |
| Mark completed | After judge approval and documentation |

---

## Escalation Protocol

When a task is rejected 10 times:

1. Stop execution immediately
2. Compile escalation report:
   - Full iteration history (all 10 attempts)
   - Rejection patterns (common issues across attempts)
   - Recommendations (what might help)
3. Present to user for guidance
4. Do NOT continue without user direction

---

## Tasks That Don't Create Separate Logs

| Task Type | What It Does | Documentation Behavior |
|-----------|--------------|------------------------|
| Phase condensation | Merges task logs into single phase file | The merged file IS the output |
| Checkpoint | Verifies phase/plan complete | If changes needed: append to phase file |
| File reference review | Updates cross-references | If changes made: append to phase file |
| Final condensation | Merges phase files into plan-level file | The merged file IS the output |

These tasks never create `{task_id}_execution_decisions.md` files for themselves.

---

## Condensation Rules

When condensing execution decisions:

1. **Same structure, fewer files** — Use identical format, just combined
2. **Preserve decisions, remove noise** — Keep key decisions, remove attempt details
3. **Delete source files** — After successful condensation
4. **Maintain chronological order** — Sort by task ID
