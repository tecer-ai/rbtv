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
| 5 | Create plan file | `{plan-name}.plan.md` from template |
| 6 | Create shape.md | Shaping decisions and execution log structure |
| 7 | Create learnings.md | System improvement queue |
| 8 | Generate micro-step files | `.task.md` file per task in phase folders |

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

**Benefits:**
- Eliminates ambiguity about whether to create or modify
- Makes file changes auditable
- Enables dependency validation (can't UPDATE before CREATE)

**Granularity Example:**
- Too micro: "Create login form → Add email field → Add password field → Add validation"
- Right level: "Implement login form with email/password fields and validation"

---

## Tool Mode Selection

When tasks require tools, specify the mode explicitly.

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior conversation context | Skill | Preserves conversation history, same context window |
| Context window saturated | Subagent | Fresh context window |
| Complex validation needed | Subagent | Judge needs focused evaluation |
| Quick lookup or search | Skill | Minimal overhead |
| Already running as subagent | Skill only | Subagents cannot invoke other subagents |

### Tool Declaration Format

In micro-step files, declare tools explicitly:

```markdown
| Tool | Mode | Purpose |
|------|------|---------|
| quality-review | subagent | Validate deliverable meets requirements |
| context-search | skill | Find relevant documentation |
```

---

## Agent Invocation in Tasks

When a task requires invoking an agent:

| Rule | Description |
|------|-------------|
| Use explicit mechanism | Write "use Task tool with `subagent_type='judge'`" not just "invoke judge" |
| Available subagent types | `judge`, `generalPurpose`, `explore`, and tool-specific types |
| Avoid ambiguous verbs | NEVER use "invoke", "call", "run" without specifying the tool mechanism |
| Specify mode | Always indicate whether tool runs as skill or subagent |

**Examples:**
- ❌ Ambiguous: "invoke judge.md after completing work"
- ✅ Explicit: "use Task tool with `subagent_type='judge'` to evaluate deliverables"

---

## Micro-step File Generation

Rules for creating task files during plan creation.

### When to Generate

| Scenario | Generate Micro-step File? |
|----------|---------------------------|
| Standard task | Yes |
| Checkpoint | No (checkpoints are pause points, not work items) |
| Trivial task (complexity <7) | Optional (can skip if self-explanatory) |

### File Location

```
.cursor/plans/{plan-name}/phase-{N}/{task-id}.task.md
```

### Generation Rules

1. One file per non-checkpoint task
2. Use `plan-task-microstep-template.md` as base
3. Fill required sections: Goal, Context Files, Execution Flow, Output Requirements
4. Include Tools section ONLY if task requires specialized RBTV skills/subagents (not for basic Read/Write/Shell)
5. Include revolving plan rules section
6. Set appropriate complexity_score in frontmatter

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
| Sync with body | Task IDs in YAML must match section headers in plan body |
| Checkpoints | Use `p[N]-checkpoint` with content prefix `P[N] CHECKPOINT - Description` |
| Final tasks | Use `pN-refs`, `pN-compound`, `pN-checkpoint` for final phase |

---

## Plan Structure

Required sections in order:

1. **YAML Frontmatter**: `name`, `overview`, `todos` array
2. **Context Section**: Problem, Goals, Constraints, Decisions, Rejected Alternatives
3. **Companion Files Table**: Reference to shape.md and learnings.md
4. **Folder Structure**: Directory layout showing micro-step file locations
5. **Architectural Constraints**: Patterns and inviolable rules
6. **Self-Execution Instructions**: Protocol, tool mode selection, quality gates
7. **Revolving Plan Rules**: Discovery handling, task modification
8. **Files to Load Table**: Path, Purpose, When to load
9. **Workflow Diagram**: Mermaid diagram showing phases and flow
10. **Phase Sections**: Phase goal + task breakdown
11. **Checkpoints**: 3-6 at inflection points (phase transitions, critical decisions)

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
2. Update YAML frontmatter todos array
3. Create micro-step file in correct phase folder
4. Append discovery entry to shape.md
5. Notify user: `PLAN MODIFIED: Added: {task-id} - {description}`

### Task Removal

When removing a task during execution:

1. Mark task as `cancelled` in YAML (don't delete)
2. Append discovery entry explaining removal
3. Notify user: `PLAN MODIFIED: Removed: {task-id} - {reason}`

---

## Zero-Context Plans

Plans executed by different agents must be self-contained:

| Rule | Description |
|------|-------------|
| No references to "as discussed" | Another agent won't know what was discussed |
| Include all context | Everything needed is IN the plan |
| List ALL files to read | Files to Load table is complete |
| Explain WHY | Document rationale for significant decisions |

---

## Checkpoint Rules

- **Quantity:** 3-6 checkpoints total
- **Placement:** At phase transitions, critical decisions, major deliverables
- **Format:** `p[N]-checkpoint` → `P[N] CHECKPOINT - [Description]`
- **Behavior:** Agent must STOP and wait for human approval
- **No micro-step files:** Checkpoints are pause points, not work items

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
| `pN-refs` | File reference review - verify all internal markdown links resolve |
| `pN-compound` | Compound learnings - process learnings.md entries into actionable changes |
| `pN-checkpoint` | Final checkpoint - user approval to complete plan |

**Note:** Condensation tasks have been eliminated. Execution context is maintained via append-only shape.md.
