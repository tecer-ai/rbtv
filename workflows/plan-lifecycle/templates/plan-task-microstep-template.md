# Plan Task Microstep Template

Use this template to generate micro-step task files during plan creation. Each task in a plan gets its own `.task.md` file with complete execution instructions.

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

| File | Purpose |
|------|---------|
| {path} | {Why this file is needed} |

---

## Tools

**IMPORTANT:** Only include this section if the task requires specialized skills or subagents from the RBTV manifest. Do NOT list basic agent tools like Read, Write, Shell, or Grep.

**Available tools:** Read `_bmad/rbtv/tools-manifest.csv` — id, skill_path, subagent_path, description columns.

**Include this section when:**
- Task requires quality validation (quality-review)
- Task needs research capabilities (web-research, context-search)
- Task needs codebase exploration (explore subagent)
- Task uses specialized RBTV workflows (compound-learning, etc.)

**Omit this section when:**
- Task only uses standard agent tools (Read, Write, Shell, Grep, etc.)
- Task is straightforward file operations without specialized tooling

**If specialized tools are required, list them below:**

| Tool | Mode | Purpose |
|------|------|---------|
| {tool-id} | skill \| subagent | {What it does in this task} |

**Mode Selection Rules:**
- **skill**: Use when prior context needed, quick lookup, or already in subagent
- **subagent**: Use when context is saturated, complex validation needed, or fresh evaluation required
- **CRITICAL**: Subagents cannot invoke other subagents; only skills

---

## Execution Flow

### Phase: Understand

1. **MUST** read every file in the Context Files table above. Do not continue until all are read.
2. In the plan file (the `.plan.md` in this plan's directory), set this task's todo to `status: in_progress`. Match the todo `id` to this task's `task_id`.
3. Review shape.md execution log for prior task context.
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
3. If using quality-review tool: Invoke with mode specified in Tools section

### Phase: Close

1. Append execution entry to shape.md (never modify existing entries).
2. **MUST** present a brief summary to the user (max 2000 characters) of what was done. Do not mark complete until the user approves.
3. After user approval, set this task's todo to `status: completed` in the plan file.
4. Notify user of completion and any plan changes.

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| {Deliverable} | {Path or destination} | {File type or structure} |

---

## Revolving Plan Rules

**When discoveries occur:**
- Append discovery to shape.md Execution Discoveries section
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

## Field Instructions

### YAML Frontmatter

| Field | Description | Values |
|-------|-------------|--------|
| task_id | Matches plan YAML ID | `p[phase]-[number]` |
| status | Current state | `pending`, `in_progress`, `completed`, `cancelled` |
| phase | Current execution phase | `understand`, `execute`, `validate`, `close` |
| complexity_score | Assessed complexity | 1-15 (see complexity assessment) |
| human_review | Review requirement | `required` (checkpoint), `optional`, `none` |

### Sections

| Section | Purpose |
|---------|---------|
| Goal | Single deliverable statement |
| Context Files | Documents agent MUST read before any phase; include mandatory read instruction above table |
| Tools | (Optional) Only include if task requires specialized RBTV skills/subagents |
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

**Location:** `.cursor/plans/{plan-name}/phase-{N}/`

**Examples:**
- `phase-1/p1-1.task.md`
- `phase-2/p2-3.task.md`
- `phase-final/pN-compound.task.md`
