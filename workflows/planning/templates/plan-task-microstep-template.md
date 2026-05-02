# Plan Task Microstep Template

Use this template to generate micro-step task files during plan creation. Each complex task and checkpoint in a plan gets its own `.task.md` file with complete execution instructions.

---

## Template

```yaml
---
task_id: {task-id}
status: pending | in_progress | completed | cancelled
phase: understand | execute | validate | close
complexity_score: {N}
human_review: required | optional | none
---
```

```markdown
# Task {task-id}: {Task Title}

## Goal

{What this task achieves. One clear deliverable statement.}

---

## Context Files

**MUST read every file in the table below before any execution phase.** Do not proceed to Phase: Understand until all are loaded and read.

**Path format:** External files (outside this plan folder) use project-root-relative paths. Internal files (within this plan folder) use file-relative paths (`./`, `../`).

| File | Purpose |
|------|---------|
| {path} | {Why this file is needed} |

---

## Tools

**IMPORTANT:** Only include this section if the task requires specialized skills or sub-agents from the RBTV manifest. Do NOT list basic agent tools like Read, Write, Bash, or Grep.

**Include this section when:**
- Task needs research capabilities (web-search, context-distill)
- Task needs codebase exploration (Explore sub-agent)
- Task uses specialized RBTV workflows (compound-learning, etc.)

**Omit this section when:**
- Task only uses standard agent tools (Read, Write, Bash, Grep, etc.)
- Task is straightforward file operations without specialized tooling

**If specialized tools are required, list them below:**

| Tool | Purpose |
|------|---------|
| {tool-id} | {What it does in this task} |

---

## Execution Flow

### Phase: Understand

1. **MUST** read every file in the Context Files table above. Do not continue until all are read.
2. Mark this task as in progress in BOTH locations (same turn):
   - In the plan file, change `[ ]` to `[~]` for this task's checkbox.
   - In this task file's YAML frontmatter, change `status: pending` to `status: in_progress`.
3. Review shape.md Decisions and Discoveries for prior task context.
4. Confirm task requirements are clear.
5. {Task-specific understanding steps}

### Phase: Execute

1. {Primary execution step}
2. {Secondary execution step}
3. {Additional steps as needed}

**Discovery Handling:**
- If simple discovery (<5 min to resolve): Resolve immediately, document in shape.md
- If complex discovery: Add new task to plan, notify user of task addition

### Phase: Validate

1. Verify deliverable meets goal statement
2. {Task-specific validation criteria}

### Phase: Close

1. Append execution entry to shape.md (never modify existing entries).
2. **MUST** present a brief summary to the user (max 2000 characters) of what was done. Do not mark complete until the user approves.
3. After user approval, mark this task as complete in BOTH locations (same turn):
   - In the plan file, change `[~]` to `[x]` for this task's checkbox.
   - In this task file's YAML frontmatter, change `status: in_progress` to `status: completed`.
4. Notify user of completion and any plan changes.

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| {Deliverable} | {Path or destination} | {File type or structure} |

---

## Revolving Plan Rules

**When discoveries occur:**
- Append discovery to shape.md Decisions and Discoveries section
- If work is complex (>5 min), add new task to plan with next available ID
- If work is simple, perform immediately and document
- **MANDATORY**: In output message, clearly state any tasks added or removed

**Task change notification format:**
```
PLAN MODIFIED:
- Added: {task-id} - {description}
- Removed: {task-id} - {reason}
```
```

---

## Checkpoint Task File Variant

For checkpoint tasks, use this adapted structure instead of the standard template:

```markdown
# Checkpoint {task-id}: {Phase Name} Review

## Goal

Evaluate phase deliverables against review criteria and present findings for human approval.

---

## Context Files

| File | Purpose |
|------|---------|
| ../shape.md | Prior decisions and execution context |
| {paths to phase deliverables} | {Work to evaluate} |

---

## Work to Evaluate

{Summary of what the phase produced — files created/modified, artifacts delivered, with specific paths}

## Review Criteria

Evaluate each criterion. Note whether it passes, fails, or needs attention.

1. {Criterion derived from phase task acceptance criteria}
2. {Criterion derived from phase task acceptance criteria}
3. {Criterion from architectural constraints}
4. {Additional criteria as needed, 3-7 total}

## Execution Flow

### Phase: Evaluate

1. Read all files listed in Context Files
2. Review shape.md for decisions and discoveries from this phase
3. Evaluate deliverables against each review criterion
4. Prepare findings summary with per-criterion assessment

### Phase: Gate

1. Present findings summary to user with clear PASS/FAIL per criterion
2. **HALT for human approval** — do not advance regardless of findings
3. If user rejects: document feedback in shape.md, do not advance to next phase
4. If user approves: mark checkpoint complete in plan task list
```

---

## Field Instructions

### YAML Frontmatter

| Field | Description | Values |
|-------|-------------|--------|
| task_id | Matches plan task list ID | `p[phase]-[number]` |
| status | Current state | `pending`, `in_progress`, `completed`, `cancelled` |
| phase | Current execution phase | `understand`, `execute`, `validate`, `close` |
| complexity_score | Assessed complexity | 1-15 (see complexity assessment) |
| human_review | Review requirement | `required` (checkpoint), `optional`, `none` |

### Sections

| Section | Purpose |
|---------|---------|
| Goal | Single deliverable statement |
| Context Files | Documents agent MUST read before any phase; include mandatory read instruction above table |
| Tools | (Optional) Only include if task requires specialized RBTV skills/sub-agents |
| Execution Flow | Phased steps (understand → execute → validate → close) |
| Output Requirements | What to produce and where |
| Revolving Plan Rules | Discovery handling instructions |

---

## Size Guidelines

| Metric | Target | Max |
|--------|--------|-----|
| Total lines | 60-100 | 150 |
| Context files | 2-5 | 10 |
| Execution steps per phase | 2-4 | 6 |

---

## Naming Convention

**File naming:** `{task-id}.task.md`

**Location:** `{output-path}/{plan-name}/phase-{N}/`

**Examples:**
- `phase-1/p1-1.task.md`
- `phase-1/p1-checkpoint.task.md`
- `phase-2/p2-3.task.md`
- `phase-final/pN-compound.task.md`
