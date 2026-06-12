# Plan Task Microstep Template

Use this template to generate micro-step task files during plan creation. Each complex task and checkpoint in a plan gets its own `.task.md` file with complete execution instructions.

---

## Template

```yaml
---
task_id: {task-id}
status: pending | in_progress | completed | cancelled
complexity_score: {N}
human_review: required | optional | none
# Orchestration pre-resolution fields (executor / reviewer / allowlist) — ONLY when orchestrated: true and step-03 §6c resolved them. Shape + rules: data/orchestration-planning.md § Orchestration Pre-Resolution Frontmatter Shape (microstep template). Omitted on a plain interactive plan.
---
```

**Orchestration pre-resolution shape:** orchestrated plans only — READ `../data/orchestration-planning.md` § Orchestration Pre-Resolution Frontmatter Shape (microstep template) for the `executor`/`reviewer`/`allowlist` field shapes and the router-pin / scaffold-derivation rules. A plain (non-orchestrated) plan omits all three blocks.

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
2. Mark this task in progress — ONE stamp call, NEVER three hand-edits:
   `python {rbtv_path}/orchestration/skills/orchestrating/scripts/stamp.py --plan-dir {plan-folder} --task {task-id} --status in_progress --scope worker`
   (`{plan-folder}` = the folder holding the plan file and `../deliverables.md` — this file's parent's parent; resolve it at runtime, never hard-code it.) The stamp is the single authority for all three bookkeeping surfaces: plan checkbox `[~]`, this file's `status:` frontmatter, and the `../deliverables.md` row — whose Path cell is where your output must land. The call is idempotent; a non-zero exit means the transition did NOT happen — STOP and surface it, never hand-edit around a failed stamp.
3. Review decisions.md Decisions and Discoveries for prior task context.
4. Confirm task requirements are clear.
5. {Task-specific understanding steps}

### Phase: Execute

1. {Primary execution step}
2. {Secondary execution step}
3. {Additional steps as needed}

**Discovery Handling:**
- If simple discovery (<5 min to resolve): Resolve immediately, document in decisions.md
- If complex discovery: Add new task to plan, notify user of task addition

### Phase: Validate

1. Verify deliverable meets goal statement
2. {Task-specific validation criteria}

### Phase: Close

**If executing under orchestration mode** (dispatched via `rbtv-orchestrating`):

1. Mark this task complete — ONE stamp call, NEVER three hand-edits:
   `python {rbtv_path}/orchestration/skills/orchestrating/scripts/stamp.py --plan-dir {plan-folder} --task {task-id} --status completed --scope worker`
   (add `--artifact "{path}"` if your output landed somewhere other than the deliverables row's Path cell). Worker scope writes exactly the three worker surfaces — plan checkbox `[x]`, this file's `status:`, the `../deliverables.md` row; the run-log and state-capsule are the CONDUCTOR's surfaces (its own conductor-scope stamp), never yours. On a non-zero exit, report the failure in your return — never hand-edit around it.
2. Reviewer dispatch (orchestration step-04) handles verification and user summary. Do NOT append to decisions.md and do NOT wait for user approval — both are handled at the orchestrator layer.
3. **If `human_review: required`:** include the Human Review Presentation block in the executor's return paragraph so the orchestrator can surface it to the user. Block format and flag criteria: see `{rbtv_path}/orchestration/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation, and `{rbtv_path}/orchestration/workflows/_shared/authoring/human-review-criteria.md`. The block is the executor's contribution to user review — the orchestrator and reviewer carry it forward, not replace it.

**If executing standalone** (no orchestrator):

1. Append a decisions.md entry ONLY if this task produced a decision, discovery, or constraint that changes future work (never modify existing entries; routine completions are NOT logged — Decisions Discipline below).
2. **MUST** present a brief summary to the user (max 2000 characters) of what was done. Do not mark complete until the user approves.
3. **If `human_review: required`:** the summary MUST end with the Human Review Presentation block. Block format and flag criteria: see `{rbtv_path}/orchestration/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation, and `{rbtv_path}/orchestration/workflows/_shared/authoring/human-review-criteria.md`. This block drives the user's review by pointing to specific items and surfacing the executor's risk assessment.
4. After user approval, mark this task complete — ONE stamp call, NEVER three hand-edits:
   `python {rbtv_path}/orchestration/skills/orchestrating/scripts/stamp.py --plan-dir {plan-folder} --task {task-id} --status completed --scope worker`
   (add `--artifact "{path}"` if your output landed somewhere other than the deliverables row's Path cell). The stamp writes the plan checkbox `[x]`, this file's `status:`, and the `../deliverables.md` row in one idempotent call. On a non-zero exit, surface the error — never hand-edit around it.
5. Notify user of completion and any plan changes.

---

## Output Requirements

| Output | Location | Format |
|--------|----------|--------|
| {Deliverable} | {Path or destination} | {File type or structure} |

---

## Revolving Plan Rules

**When discoveries occur:**
- Append discovery to decisions.md Decisions and Discoveries section
- If work is complex (>5 min), add new task to plan with next available ID
- If work is simple, perform immediately and document
- **MANDATORY**: In output message, clearly state any tasks added or removed

**Task change notification format:**
```
PLAN MODIFIED:
- Added: {task-id} - {description}
- Removed: {task-id} - {reason}
```

---

## Decisions Discipline

> `decisions.md` entries: decision + rationale + scope ONLY (+ optional one-word `compoundable` marker for harvest-worthy findings) — never file-lists or N→M narratives; supersede by appending, never rewrite.
```

---

## Human Review Presentation

**Audience:** Executors completing a task whose `.task.md` frontmatter sets `human_review: required` (and reviewers under orchestration mode handling phases that contain such tasks). Phase: Close (standard template) and Phase: Gate (checkpoint variant) reference this section by path.

**Purpose:** Drive the user's review of the task's output. The block names what to look at first AND surfaces the executor's evidence-based risk assessment so the user reviews with priorities, not from scratch.

### Hard rule — no false alarms

Flag ONLY items backed by concrete evidence in this task's output. If no concrete evidence triggers a flag, write `None identified.` and add a one-line rationale stating which checks ran clean. Generic "consider future X" or "watch for edge cases" hypotheticals are NOT flags. Use the Flag Criteria in `{rbtv_path}/orchestration/workflows/_shared/authoring/human-review-criteria.md` — do NOT free-associate.

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
| What to review | 2-5 items. Each item names a concrete artifact (file path, decision in decisions.md, output value) — not an abstraction. Order by what the human should open first. |
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
| ../decisions.md | Prior decisions and execution context |
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
2. Review decisions.md for decisions and discoveries from this phase
3. Evaluate deliverables against each review criterion
4. Prepare findings summary with per-criterion assessment

### Phase: Gate

1. Present findings summary to user with clear PASS/FAIL per criterion
2. **MUST** append the Human Review Presentation block — checkpoints inherit `human_review: required` semantics. Block format and flag criteria: see `{rbtv_path}/orchestration/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation, and `{rbtv_path}/orchestration/workflows/_shared/authoring/human-review-criteria.md`. The block points the user at specific phase artifacts and surfaces red/yellow flags drawn from phase execution evidence (executor returns, decisions.md Discoveries, criterion FAILs). If no flags fire, write "None identified" with a one-line rationale.
3. **HALT for human approval** — do not advance regardless of findings
4. If user rejects: document feedback in decisions.md, do not advance to next phase
5. If user approves: mark the checkpoint complete via the single-authority stamp — `python {rbtv_path}/orchestration/skills/orchestrating/scripts/stamp.py --plan-dir {plan-folder} --task {task-id} --status completed --scope worker` (plan checkbox + this file's `status:` + the `../deliverables.md` row in one call; never hand-edit them)
```

---

## Naming and Location

File naming and location follow `plan-creation-rules.md` § Micro-step File Generation → File Location: `{output-path}/{plan-name}/phase-{N}/{task-id}.task.md`.
