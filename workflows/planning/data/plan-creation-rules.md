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
| 6 | Create or merge shape.md | Check for existing shape.md (from context preservation rule); merge planning context if exists, create from universal template if not |
| 7 | Create learnings.md | System improvement queue |
| 8 | Generate micro-step files | `.task.md` file per complex task; append `[path]` to todo `content` |

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
| Canonical source only | Tasks must write to canonical source of truth only — replication to workspace locations (`.cursor/`, `.claude/`) is an installer responsibility | ✅ "CREATE `_config/claude/rules/rule.md`" ❌ "CREATE rule in both `_config/` and `.cursor/rules/`" |

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

## Plan Linking Standard

**MANDATORY:** All references within plan artifacts follow a three-part linking contract to ensure plan folders can be moved without breaking links.

### Internal Links (within plan folder)

References between files inside the same plan folder MUST use file-relative paths.

| Rule | Example | Anti-pattern |
|------|---------|--------------|
| Use `./` or `../` relative to the referencing file | `../shape.md`, `./phase-1/p1-1.task.md` | ❌ `.cursor/plans/my-plan/shape.md` |
| `[path]` values in todo content are relative to the plan folder | `[phase-1/p1-1.task.md]` | ❌ `[.cursor/plans/my-plan/phase-1/p1-1.task.md]` |
| NEVER embed the plan folder's absolute or root-relative path | `../learnings.md` | ❌ `{project-root}/.cursor/plans/my-plan/learnings.md` |

### External Links (from plan files to outside)

References from plan files to files outside the plan folder MUST use project-root-relative paths.

| Rule | Example | Anti-pattern |
|------|---------|--------------|
| Path from project root, no leading `./` | `workflows/planning/workflow.md` | ❌ `../../../workflows/planning/workflow.md` |
| NEVER traverse up out of the plan folder | `_bmad/rbtv/workflows/planning/workflow.md` | ❌ `../../../../_bmad/rbtv/workflows/planning/workflow.md` |

### Inbound Links (from outside referencing a plan)

Documents outside a plan folder that reference plan files MUST use root-relative paths to the plan's current location. When a plan folder moves, update these references via search-and-replace on the old path.

| Rule | Example |
|------|---------|
| Use root-relative path to plan file | `_bmad/rbtv/_admin/roadmap/testing/my-plan/my-plan.plan.md` |
| Reference companion files the same way | `_bmad/rbtv/_admin/roadmap/testing/my-plan/shape.md` |

### Validation (pN-refs task)

The `pN-refs` task in every plan's final phase MUST verify:
1. No file inside the plan folder contains a self-reference using an absolute or root-relative path to the plan folder
2. All internal links use `./` or `../` relative paths
3. All external links from plan files use project-root-relative paths

---

## Tool Mode Selection

When tasks require tools, specify the mode explicitly.

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior conversation context | Skill | Preserves conversation history, same context window |
| Context window saturated | Subagent | Fresh context window |
| Complex validation needed | Subagent | quality-review needs focused evaluation |
| Quick lookup or search | Skill | Minimal overhead |
| Already running as subagent | Skill only | Subagents cannot invoke other subagents |

### Tool Declaration Format

In micro-step files, declare tools explicitly:

```markdown
| Tool | Mode | Purpose |
|------|------|---------|
| quality-review | subagent | Validate deliverable meets requirements |
| context-distill | subagent | Distill targeted knowledge from referenced files |
```

---

## Agent Invocation in Tasks

When a task requires invoking an agent:

| Rule | Description |
|------|-------------|
| Use explicit mechanism | Subagent: write "use Task tool with `subagent_type='<id>'`"; Skill: write "Read `{skill_path}`" |
| Available tools | Reference skills under `_bmad/rbtv/skills/` and subagents under `_bmad/rbtv/subagents/` directly by path |
| Avoid ambiguous verbs | NEVER use "invoke", "call", "run" without specifying the tool mechanism |
| Specify mode | Always indicate whether tool runs as skill or subagent |

**Invocation methods:**
- **Skill:** Read skill_path from manifest in current context (no separate API)
- **Subagent:** Use Task tool with `subagent_type='<id>'` (id from manifest)

**Examples:**
- ❌ Ambiguous: "invoke quality-review after completing work"
- ✅ Explicit: "use Task tool with `subagent_type='quality-review'` to evaluate deliverables"

---

## Micro-step File Generation

Rules for creating task files during plan creation.

### When to Generate

| Scenario | Generate Micro-step File? | Instead |
|----------|---------------------------|---------|
| **Complex task:** multi-step, needs context loading, tool declarations, phased execution | **YES** — full microstep file | — |
| **Standard task:** clear scope, single action, no special context | **NO** — inline content is sufficient | YAML `content` field contains complete instructions |
| **Checkpoint** | **NO** | Pause point only |

### Decision Criteria

Generate a micro-step file when ANY of these apply:
- Task requires loading 2+ context files
- Task uses specialized RBTV tools (subagents, skills)
- Task has 3+ distinct substeps
- Task requires a phased execution flow (understand → execute → validate)
- Task produces output that needs quality review

Use inline YAML content when ALL of these apply:
- Task is self-explanatory from its description
- Single action, completable in one step
- No special context files or tools needed
- No phased execution flow required

### Inline Content Examples

```yaml
# Simple task — NO micro-step file needed (no [path] suffix)
- id: p1-2
  content: "p1-2: UPDATE src/config.ts to add the new API endpoint URL from the design doc"
  status: pending

# Complex task — micro-step file generated, path embedded in content
- id: p2-1
  content: "p2-1: Implement authentication flow with OAuth2 integration [phase-2/p2-1.task.md]"
  status: pending
```

### File Location

```
.cursor/plans/{plan-name}/phase-{N}/{task-id}.task.md
```

### Generation Rules

1. One file per complex non-checkpoint task (per decision criteria above)
2. Use `plan-task-microstep-template.md` as base
3. Fill required sections: Goal, Context Files, Execution Flow, Output Requirements
4. Include Tools section ONLY if task requires specialized RBTV skills/subagents (not for basic Read/Write/Shell)
5. Include revolving plan rules section
6. Set appropriate complexity_score in frontmatter
7. Append task file path in `[brackets]` to the corresponding YAML todo's `content` field (path relative to plan folder)

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

## Plan Body Minimalism

**MANDATORY:** The plan body must not repeat content from shape.md, micro-step files, or YAML frontmatter. Reference companion files; do not duplicate them.

| Principle | Enforcement |
|-----------|-------------|
| No content repetition | Context, decisions, constraints live in shape.md — not the plan body |
| YAML is the task list | Phase sections state phase goal only — task details are in YAML `content` (with `[path]` suffix for micro-step files) |
| Per-task context in microsteps | Files-to-load tables belong in `.task.md` files, not the plan body |
| Folder structure is discoverable | Agents navigate the filesystem — no need to diagram it in the plan |

## Plan Structure

Required sections in order:

1. **YAML Frontmatter**: `name`, `overview`, `todos` array (only `id`, `content`, `status` per item — task file paths embedded in `content` as `[path]` suffix)
2. **Architectural Constraints**: Plan-specific patterns and inviolable rules
3. **Revolving Plan Rules**: Discovery handling, task modification (keep brief)
4. **Execution Workflow** *(conditional)*: Mermaid diagram — only for non-linear plans (branching or parallel phases)
5. **Phase Sections**: Phase name + goal + checkpoint review prompt subsection; task details read from YAML `content` field

> **Reference directive:** The plan body opens with: "Read `shape.md` for full context, decisions, and constraints. Read individual `.task.md` files (path in `[brackets]` at end of todo content) for per-task execution instructions."

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
| Include all context | Everything needed is in the plan + shape.md + microstep files |
| Per-task file references | Each `.task.md` lists its own Context Files table |
| Explain WHY | Document rationale for significant decisions in shape.md |

---

## Checkpoint Rules

- **Quantity:** 3-6 checkpoints total
- **Placement:** At phase transitions, critical decisions, major deliverables
- **Format:** `p[N]-checkpoint` → `P[N] CHECKPOINT - [Description]`
- **Behavior:** Agent must STOP and wait for human approval
- **No micro-step files:** Checkpoints are pause points, not work items

### Mandatory Quality-Review at Checkpoints

Every checkpoint MUST include a `quality-review` subagent evaluation before presenting the gate decision to the user.

**Checkpoint YAML entry** (YAML carries only `id`, `content`, `status` — no custom fields):

```yaml
- id: p1-checkpoint
  content: "P1 CHECKPOINT - Review phase deliverables before proceeding"
  status: pending
```

**Checkpoint review prompt in plan body:**

Each checkpoint's review prompt is embedded in the plan body as a `####` subsection under its phase, using a blockquote. This placement survives Cursor's YAML serializer, which silently strips custom fields when task status changes.

```markdown
#### P1 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> {Summary of phase deliverables — files created/modified, artifacts produced, with specific paths}
>
> ## Quality Criteria
> 1. {Criterion derived from phase task acceptance criteria}
> 2. {Criterion from architectural constraints}
> 3. {Criterion from phase tasks}
```

**Why body, not YAML:** Cursor's plan YAML serializer only preserves `id`, `content`, and `status` on todo items. Custom fields (like `reviewAgent`, `reviewPrompt`) are silently dropped when the executor updates task status. Embedding review prompts in the markdown body keeps them safe from YAML rewriting.

**Generation rules for review prompts:**

1. **Work to Evaluate** — summarize what the phase produced (files created/modified, artifacts delivered), referencing specific paths
2. **Quality Criteria** — derive 3-7 criteria from the phase's task descriptions, architectural constraints, and explicit acceptance criteria
3. The prompt must be self-contained — the quality-review agent runs in a fresh context and cannot see the plan's prior execution history

**Executor behavior at checkpoints:**

1. Locate the checkpoint's review prompt in the phase body section (heading format: `#### P{N} Checkpoint Review Prompt`)
2. Use Task tool with `subagent_type='quality-review'`, passing the blockquoted prompt content
3. Present the `APPROVED` or `REJECTED` verdict to the user
4. If `REJECTED`, do not advance to the next phase
5. HALT for human approval regardless of verdict

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

**Note:** Condensation tasks have been eliminated. Execution context is maintained via append-only shape.md.
