# Plan Creation Rules

Knowledge file for plan creation workflow. These rules ensure consistent, high-quality plans.

---

## Macro Workflow for Plan Creation

The 8-step process for creating any plan:

| Step | Action | Output |
|------|--------|--------|
| 1 | Gather requirements from user | Clear understanding of goals and constraints |
| 2 | Assess complexity (5 dimensions) | Complexity score and task sizing guidance |
| 3 | Draft plan structure | Phase breakdown with task IDs |
| 4 | Apply dependency ordering | Tasks ordered by prerequisites |
| 5 | Create plan file | `{plan-name}-plan.md` from template |
| 6 | Create or merge shape.md | Check for existing shape.md (from context preservation rule); merge planning context if exists, create from universal template if not |
| 7 | Create learnings.md | System improvement queue |
| 8 | Generate micro-step files | `.task.md` file per complex task and per checkpoint |

---

## Complexity Assessment

Assess each plan across 5 dimensions. Score 1-3 per dimension.

### Dimension Scoring

| Dimension | 1 (Low) | 2 (Medium) | 3 (High) |
|-----------|---------|------------|----------|
| Context Size | <50k tokens | 50-100k tokens | >100k tokens |
| Dependencies | Linear, clear | Some branching | Complex graph |
| Tool Usage | 0-2 tools | 3-5 tools | 6+ tools |
| Decision Density | Few decisions | Moderate decisions | Many architectural decisions |
| Human Review | None needed | Optional checkpoints | Required approvals |

### Scoring Thresholds

| Total Score | Complexity Level | Task Guidance |
|-------------|------------------|---------------|
| 5-7 | Simple | Single-step tasks OK, fewer micro-step files |
| 8-11 | Moderate | Standard task granularity, full micro-step files |
| 12-15 | Complex | Fine-grained tasks, research-first pattern |

### Complexity Impact

| Score Range | Implications |
|-------------|--------------|
| 5-7 | May skip some micro-step files for trivial tasks |
| 8-11 | Standard micro-step file per task |
| 12-15 | Consider research phase, split large tasks |

---

## Task Granularity

| Rule | Description | Example |
|------|-------------|---------|
| WHAT, not HOW | Describe WHAT to achieve; only include HOW if user explicitly decided | ✅ "Implement login form with validation" ❌ "Add email field, then password field, then validation" |
| Single action per task | Each task = one discrete, independently completable action | ✅ "Create component" ✅ "Write tests" ❌ "Create and test component" |
| No compound tasks | Never combine actions with "and" | ✅ Two tasks ❌ "Create file and update imports" |
| Room for judgment | Leave implementation decisions to executing agent unless user specified | ✅ "Implement caching" ❌ "Implement Redis caching with 5-minute TTL" (unless user specified) |
| Explicit file operations | Use CREATE/UPDATE/DELETE/MOVE verbs for file tasks | ✅ "CREATE src/auth.ts with login logic" ❌ "Add authentication" |
| Canonical source only | Tasks must write to canonical source of truth only — replication to workspace locations is an installer responsibility | ✅ "CREATE `_config/claude/rules/rule.md`" ❌ "CREATE rule in both `_config/` and `.claude/rules/`" |

---

## Explicit File Operations

**MANDATORY:** Task descriptions involving files MUST use explicit operation verbs.

| Verb | When to Use | Example |
|------|-------------|---------|
| CREATE | New file that doesn't exist | `CREATE src/components/Button.tsx with props interface and styled component` |
| UPDATE | Modify existing file | `UPDATE src/api/auth.ts to add token refresh logic` |
| DELETE | Remove file | `DELETE src/legacy/oldAuth.ts (replaced by new auth module)` |
| MOVE | Relocate or rename file | `MOVE src/utils/helpers.ts to src/shared/helpers.ts` |

**Format:** `[ACTION] [file-path] [with/to/containing] [content description]`

---

## Plan Linking Standard

**MANDATORY:** All references within plan artifacts follow a linking contract to ensure plan folders can be moved without breaking links.

### Internal Links (within plan folder)

References between files inside the same plan folder MUST use file-relative paths.

| Rule | Example | Anti-pattern |
|------|---------|--------------|
| Use `./` or `../` relative to the referencing file | `../shape.md`, `./phase-1/p1-1.task.md` | ❌ Absolute or root-relative path to own plan folder |
| Task file path references are relative to the plan folder | `phase-1/p1-1.task.md` | ❌ Full path from project root |
| NEVER embed the plan folder's absolute or root-relative path | `../learnings.md` | ❌ `{project-root}/plans/my-plan/learnings.md` |

### External Links (from plan files to outside)

References from plan files to files outside the plan folder MUST use project-root-relative paths.

| Rule | Example | Anti-pattern |
|------|---------|--------------|
| Path from project root, no leading `./` | `workflows/planning/workflow.md` | ❌ `../../../workflows/planning/workflow.md` |
| NEVER traverse up out of the plan folder | `workflows/planning/workflow.md` | ❌ `../../../../workflows/planning/workflow.md` |

### Inbound Links (from outside referencing a plan)

Documents outside a plan folder that reference plan files MUST use root-relative paths to the plan's current location. When a plan folder moves, update these references via search-and-replace on the old path.

### Validation (pN-refs task)

The `pN-refs` task in every plan's final phase MUST verify:
1. No file inside the plan folder contains a self-reference using an absolute or root-relative path to the plan folder
2. All internal links use `./` or `../` relative paths
3. All external links from plan files use project-root-relative paths

---

## Micro-step File Generation

Rules for creating task files during plan creation.

### When to Generate

| Scenario | Generate Micro-step File? | Instead |
|----------|---------------------------|---------|
| **Complex task:** multi-step, needs context loading, phased execution | **YES** — full microstep file | — |
| **Standard task:** clear scope, single action, no special context | **NO** — inline description is sufficient | Markdown task line contains complete instructions |
| **Checkpoint** | **YES** — contains review criteria and gate instructions | — |

### Decision Criteria

Generate a micro-step file when ANY of these apply:
- Task requires loading 2+ context files
- Task uses specialized RBTV tools (skills, sub-agents)
- Task has 3+ distinct substeps
- Task requires a phased execution flow (understand → execute → validate)
- Task is a checkpoint (review criteria must be documented)

Use inline Markdown task description when ALL of these apply:
- Task is self-explanatory from its description
- Single action, completable in one step
- No special context files or tools needed
- No phased execution flow required

### File Location

```
{output-path}/{plan-name}/phase-{N}/{task-id}.task.md
```

### Generation Rules

1. One file per complex non-checkpoint task (per decision criteria above)
2. One file per checkpoint (contains review criteria)
3. Use `plan-task-microstep-template.md` as base
4. Fill required sections: Goal, Context Files, Execution Flow, Output Requirements
5. Include Tools section ONLY if task requires specialized RBTV skills/sub-agents (not for basic Read/Write/Bash)
6. Include revolving plan rules section
7. Set appropriate complexity_score in frontmatter
8. Link the task file from the Markdown task list: `→ phase-N/task-id.task.md`

---

## Task Ordering

| Rule | Description |
|------|-------------|
| High-value first | Complex, critical tasks at beginning |
| Low-value last | Routine, administrative tasks at end |
| Critical path first | Blocking tasks before non-blocking |
| Dependencies respected | Task B depending on A means A comes first |

---

## Task IDs

| Rule | Description |
|------|-------------|
| Format | `p[phase]-[number]` or `p[phase]-[name]` (e.g., `p1-3`, `p2-auth`) |
| Sync with body | Task IDs in task list must match section headers in plan body |
| Checkpoints | Use `p[N]-checkpoint` with description prefix `CHECKPOINT —` |
| Final tasks | Use `pN-refs`, `pN-compound`, `pN-checkpoint` for final phase |

---

## Plan Body Minimalism

**MANDATORY:** The plan body must not repeat content from shape.md, micro-step files, or the task list. Reference companion files; do not duplicate them.

| Principle | Enforcement |
|-----------|-------------|
| No content repetition | Context, decisions, constraints live in shape.md — not the plan body |
| Task list is the execution index | Phase sections state phase goal; task details are in the task list with `→ path` for micro-step files |
| Per-task context in microsteps | Files-to-load tables belong in `.task.md` files, not the plan body |
| Folder structure is discoverable | Agents navigate the filesystem — no need to diagram it in the plan |

## Plan Structure

The plan file uses minimal YAML frontmatter (`name`, `overview`) and a Markdown body:

1. **YAML Frontmatter**: `name`, `overview` only
2. **Reference directive**: Pointers to shape.md and task files
3. **Architectural Constraints**: Plan-specific patterns and inviolable rules
4. **Revolving Plan Rules**: Discovery handling, task modification (keep brief)
5. **Execution Workflow** *(conditional)*: Mermaid diagram — only for non-linear plans (branching or parallel phases)
6. **Tasks**: Markdown checkbox list grouped by phase, with `→ path` suffix for tasks with micro-step files

---

## Revolving Plan Rules

Plans adapt during execution based on discoveries.

### Discovery Categories

| Type | Action |
|------|--------|
| Simple discovery (<5 min) | Resolve immediately, document in shape.md |
| Complex discovery (>5 min) | Add new task to plan, document in shape.md |
| Contradiction with shaping | Document in shape.md Execution Discoveries, proceed with resolution |

### Task Addition

When adding a task during execution:

1. Choose appropriate phase and task ID
2. Add to the task list in the plan body
3. Create micro-step file in correct phase folder if needed
4. Append discovery entry to shape.md
5. Notify user: `PLAN MODIFIED: Added: {task-id} - {description}`

### Task Removal

When removing a task during execution:

1. Mark task with ~~strikethrough~~ in the task list (don't delete)
2. Append discovery entry explaining removal
3. Notify user: `PLAN MODIFIED: Removed: {task-id} - {reason}`

---

## Zero-Context Plans

Plans executed by different agents must be self-contained:

| Rule | Description |
|------|-------------|
| No references to "as discussed" | Another agent won't know what was discussed |
| Include all context | Everything needed is in the plan + shape.md + microstep files |
| Per-task file references | Each `.task.md` lists its own Context Files table |
| Explain WHY | Document rationale for significant decisions in shape.md |

---

## Checkpoint Rules

- **Quantity:** 3-6 checkpoints total
- **Placement:** At phase transitions, critical decisions, major deliverables
- **Format:** `p[N]-checkpoint` → `CHECKPOINT — [Description]`
- **Behavior:** Agent evaluates work against review criteria in checkpoint task file, presents findings, then STOPS for human approval
- **Task files:** Every checkpoint gets a `.task.md` file containing specific review criteria composed during planning

### Checkpoint Task File Content

Each checkpoint task file contains:
- **Review criteria** — 3-7 specific criteria derived from the phase's task descriptions, architectural constraints, and acceptance criteria
- **Work to evaluate** — summary of what the phase produced (files created/modified, artifacts delivered)
- **Gate behavior** — present evaluation findings to user, HALT for human approval, do not advance if user rejects

The plan creator composes these review criteria at plan creation time, when full phase context is available.

---

## Dependency Ordering

**MANDATORY:** Tasks must be ordered so dependencies complete before dependents.

| Rule | Description |
|------|-------------|
| Dependencies first | If task B depends on task A's output, A must come before B |
| CREATE before UPDATE | Can't UPDATE a file that hasn't been CREATEd |
| Layer by dependency depth | Group tasks by how many dependencies they have |
| Validate during creation | Check for circular dependencies and ordering violations |

**Validation Checks:**
1. No task references output from a later task
2. No circular dependencies (A→B→C→A)
3. CREATE operations precede UPDATE operations for same file
4. Shared dependencies grouped together when possible

---

## Context Budgeting

**Guidance for task sizing:**

| Context Size | Action |
|--------------|--------|
| < 50k tokens | Single task, proceed normally |
| 50-100k tokens | Consider splitting, document reasoning |
| > 100k tokens | MUST split into research + execution phases |

**Research-First Pattern:**
1. Research phase produces summary (~10-20k tokens)
2. Downstream tasks consume summary, not raw sources
3. Reduces context load from ~200k+ to ~20k

---

## Final Phase Tasks

Every plan includes these final phase tasks:

| Task ID | Purpose |
|---------|---------|
| `pN-refs` | File reference review - verify all markdown links resolve and comply with Plan Linking Standard (internal = file-relative, external = root-relative) |
| `pN-compound` | Compound learnings - process learnings.md entries into actionable changes |
| `pN-checkpoint` | Final checkpoint - user approval to complete plan |
