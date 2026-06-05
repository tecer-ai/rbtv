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
2. Mark this task as in progress in ALL locations (same turn):
   - In the plan file, change `[ ]` to `[~]` for this task's checkbox.
   - In this task file's YAML frontmatter, change `status: pending` to `status: in_progress`.
   - In `../deliverables.md`, set this task's row Status to `in-progress` — its Path cell is where your output must land.
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

**If executing under plan-orchestration** (the dispatching executor prompt declares orchestration mode):

1. Mark this task complete in ALL locations (same turn):
   - In the plan file, change `[~]` to `[x]` for this task's checkbox.
   - In this task file's YAML frontmatter, change `status: in_progress` to `status: completed`.
   - In `../deliverables.md`, flip this task's row Status to ✅ and confirm the Path matches what you produced.
2. Reviewer dispatch (orchestration step-04) handles verification and user summary. Do NOT append to shape.md and do NOT wait for user approval — both are handled at the orchestrator layer.
3. **If `human_review: required`:** include the Human Review Presentation block in the executor's return paragraph so the orchestrator can surface it to the user. Block format and flag criteria: see `{rbtv_path}/orchestration/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation, and `{rbtv_path}/orchestration/workflows/planning/data/plan-creation-rules.md` § Human Review Flag Criteria. The block is the executor's contribution to user review — the orchestrator and reviewer carry it forward, not replace it.

**If executing standalone** (no orchestrator):

1. Append execution entry to shape.md (never modify existing entries).
2. **MUST** present a brief summary to the user (max 2000 characters) of what was done. Do not mark complete until the user approves.
3. **If `human_review: required`:** the summary MUST end with the Human Review Presentation block. Block format and flag criteria: see `{rbtv_path}/orchestration/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation, and `{rbtv_path}/orchestration/workflows/planning/data/plan-creation-rules.md` § Human Review Flag Criteria. This block drives the user's review by pointing to specific items and surfacing the executor's risk assessment.
4. After user approval, mark this task as complete in ALL locations (same turn):
   - In the plan file, change `[~]` to `[x]` for this task's checkbox.
   - In this task file's YAML frontmatter, change `status: in_progress` to `status: completed`.
   - In `../deliverables.md`, flip this task's row Status to ✅ and confirm the Path matches what you produced.
5. Notify user of completion and any plan changes.

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

## Human Review Presentation

**Audience:** Executors completing a task whose `.task.md` frontmatter sets `human_review: required` (and reviewers under plan-orchestration handling phases that contain such tasks). Phase: Close (standard template) and Phase: Gate (checkpoint variant) reference this section by path.

**Purpose:** Drive the user's review of the task's output. The block names what to look at first AND surfaces the executor's evidence-based risk assessment so the user reviews with priorities, not from scratch.

### Hard rule — no false alarms

Flag ONLY items backed by concrete evidence in this task's output. If no concrete evidence triggers a flag, write `None identified.` and add a one-line rationale stating which checks ran clean. Generic "consider future X" or "watch for edge cases" hypotheticals are NOT flags. Use the Flag Criteria in `{rbtv_path}/orchestration/workflows/planning/data/plan-creation-rules.md` (§ Human Review Flag Criteria) — do NOT free-associate.

### Block format

Emit the block verbatim using this structure (replace `{...}` placeholders):

~~~
### Human Review — {task-id}

**What to review (evidence-anchored):**
- {Specific path, decision, or output the human should open first} — {why this needs human eyes}
- {Item 2}
- {Item 3}

**Risk Assessment:**

🔴 Red flags (high concern — review before approving):
- {Concrete flag with evidence pointer}
OR
- None identified.

🟡 Yellow flags (worth noting):
- {Concrete flag with evidence pointer}
OR
- None identified.

{If both lists are "None identified.": one-line rationale stating which checks ran clean — e.g., "No irreversible operations, no scope deviation, no architectural-constraint conflicts, no unilateral doubt resolutions."}
~~~

### Authoring guidance

| Section | Guidance |
|---------|----------|
| What to review | 2-5 items. Each item names a concrete artifact (file path, decision in shape.md, output value) — not an abstraction. Order by what the human should open first. |
| Red flags | Use Flag Criteria § Red Flag Triggers. Anchor each flag to specific evidence (file path + line range, decision name, command output). If unsure whether a concern qualifies, check the Anti-Flag Rules; when in doubt, omit. |
| Yellow flags | Use Flag Criteria § Yellow Flag Triggers. Same evidence requirement. |
| No-flag rationale | REQUIRED when both flag lists are empty. One line, naming which Flag Criteria checks ran clean (e.g., "No irreversible ops, no scope deviation, no new dependencies"). Without the rationale, the human cannot tell whether the executor checked or skipped the analysis. |

### Closing rule

The block ends the user-facing summary. Do NOT add meta-commentary, "let me know if you have questions" closers, or apologies after the block.

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
2. **MUST** append the Human Review Presentation block — checkpoints inherit `human_review: required` semantics. Block format and flag criteria: see `{rbtv_path}/orchestration/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation, and `{rbtv_path}/orchestration/workflows/planning/data/plan-creation-rules.md` § Human Review Flag Criteria. The block points the user at specific phase artifacts and surfaces red/yellow flags drawn from phase execution evidence (executor returns, shape.md Discoveries, criterion FAILs). If no flags fire, write "None identified" with a one-line rationale.
3. **HALT for human approval** — do not advance regardless of findings
4. If user rejects: document feedback in shape.md, do not advance to next phase
5. If user approves: mark checkpoint complete in plan task list and flip its row Status to ✅ in `../deliverables.md`
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
| human_review | Review requirement | `required` (executor MUST emit Human Review Presentation block at Phase: Close — see template), `optional`, `none` |

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

The Human Review Presentation block is RUNTIME content (emitted by the executor when the task closes). It does NOT count toward the task file's size budget — the file only references the block format.

---

## Naming Convention

**File naming:** `{task-id}.task.md`

**Location:** `{output-path}/{plan-name}/phase-{N}/`

**Examples:**
- `phase-1/p1-1.task.md`
- `phase-1/p1-checkpoint.task.md`
- `phase-2/p2-3.task.md`
- `phase-final/pN-compound.task.md`
