# Plan Creation Rules

Knowledge file for plan creation workflow. These rules ensure consistent, high-quality plans.

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

## Agent Invocation in Tasks

When a task requires invoking an agent:

| Rule | Description |
|------|-------------|
| Use explicit mechanism | Write "use Task tool with `subagent_type='judge'`" not just "invoke judge" |
| Available subagent types | `judge`, `generalPurpose`, `explore` |
| Avoid ambiguous verbs | NEVER use "invoke", "call", "run" without specifying the tool mechanism |

**Examples:**
- ❌ Ambiguous: "invoke judge.md after completing work"
- ✅ Explicit: "use Task tool with `subagent_type='judge'` to evaluate deliverables"

---

## Task Ordering

| Rule | Description |
|------|-------------|
| First task creates log infrastructure | **MANDATORY:** First task must create plan folder and initial execution decisions file |
| High-value first | Complex, critical tasks at beginning |
| Low-value last | Routine, administrative tasks at end |
| Critical path first | Blocking tasks before non-blocking |

---

## Task IDs

| Rule | Description |
|------|-------------|
| Format | `p[phase]-[number]` or `p[phase]-[name]` (e.g., `p1-3`, `p2-auth`) |
| Sync with body | Task IDs in YAML must match section headers in plan body |
| Checkpoints | Use `p[N]-checkpoint` with content prefix `P[N] CHECKPOINT - Description` |

---

## Plan Structure

Required sections in order:

1. **YAML Frontmatter**: `name`, `overview`, `todos` array
2. **Context Section**: Problem, Goals, Constraints, Decisions, Rejected Alternatives
3. **Files to Load Table**: Path, Purpose, When to load
4. **Workflow Diagram**: Mermaid diagram showing phases and flow
5. **Phase Sections**: Phase goal + task breakdown
6. **Checkpoints**: 3-6 at inflection points (phase transitions, critical decisions)

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

## Automatic Condensation Tasks

Plans MUST include these tasks automatically:

| Type | When | Purpose |
|------|------|---------|
| Phase condensation | Before each milestone checkpoint | Condense all task logs from the phase into single file |
| File reference review | Second-to-last task before final checkpoint | Review and update all file references |
| Final condensation | Last task before final checkpoint | Condense all phase files into plan-level file |

---

## Checkpoint Rules

- **Quantity:** 3-6 checkpoints total
- **Placement:** At phase transitions, critical decisions, major deliverables
- **Format:** `p[N]-checkpoint` → `P[N] CHECKPOINT - [Description]`
- **Behavior:** Agent must STOP and wait for human approval

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
