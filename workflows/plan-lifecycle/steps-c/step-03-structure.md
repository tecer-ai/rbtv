---
stepNumber: 3
stepName: 'structure'
nextStepFile: ./step-04-generate-artifacts.md
outputFile: '{outputFolder}/{plan-name}/{plan-name}.plan.md'
dataFile: ../data/plan-creation-rules.md
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 03: Create Plan Structure

**Purpose:** Generate phases, tasks, and checkpoints following task granularity rules.

---

## MANDATORY SEQUENCE

Follow these instructions in exact order. Do NOT skip, reorder, or optimize.

### 1. Reload Knowledge

- Read `{dataFile}` from frontmatter if not already in memory
- Focus on: Task granularity rules, Task ID format, Checkpoint rules

### 2. Analyze Scope

Based on the context from step-02, identify:
- Major phases of work (logical groupings)
- Key deliverables per phase
- Dependencies between phases
- Natural checkpoint locations (phase transitions, critical decisions)

### 3. Generate Phase Breakdown

Create phases following these rules:
- 2-6 phases typical
- Each phase has a clear goal
- Phases are ordered by dependency (critical path first)

### 4. Generate Tasks Per Phase

For each phase, generate tasks following granularity rules:

| Rule | Application |
|------|-------------|
| WHAT, not HOW | "Implement login form with validation" not "Add email field, add password field, add validation" |
| Single action per task | Each task is one discrete action |
| No compound tasks | "Create and validate" → two separate tasks |
| Room for judgment | Leave HOW decisions to executing agent unless user specified |

### 5. Assess Task Complexity

For each task, assess complexity across 5 dimensions:

| Dimension | Low (1) | Medium (2) | High (3) |
|-----------|---------|------------|----------|
| Context size | Few files | Multiple files | Many files across folders |
| Dependencies | Standalone | Some dependencies | Complex dependency chain |
| Tool usage | Single tool | 2-3 tools | Multiple tools with coordination |
| Decision density | Routine | Some judgment | Many design decisions |
| Human review need | None | Optional | Required |

**Scoring thresholds:**
- 5-7: Simple task
- 8-11: Moderate task
- 12-15: Complex task (consider splitting)

### 6. Add Final Compound Task

**MANDATORY:** The last task of the final phase MUST be:

```yaml
- id: pN-compound
  content: "pN-compound: Review learnings.md and compound into system improvements"
  status: pending
```

This reviews meta-learnings captured during execution and proposes BMAD/RBTV improvements.

### 7. Generate Checkpoints

Add 3-6 checkpoints at inflection points:
- Use ID format: `p[N]-checkpoint`
- Content format: `P[N] CHECKPOINT - [Description]`
- Place at: Phase transitions, critical decisions, major deliverables

**Mandatory checkpoint review prompt:** Each checkpoint MUST have a corresponding review prompt in the plan body (not in YAML — Cursor strips custom YAML fields on status updates).

**YAML entry** (only standard fields):

```yaml
- id: p1-checkpoint
  content: "P1 CHECKPOINT - {description}"
  status: pending
```

**Plan body section** (under the phase, after the task list):

For each checkpoint, compose a review prompt subsection in the phase body:

```markdown
#### P1 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> {Phase deliverables summary with file paths}
>
> ## Quality Criteria
> 1. {Criterion from phase tasks}
> 2. {Criterion from phase tasks}
```

Compose the review prompt by:
1. **Work to Evaluate** — summarize what the preceding phase produced (files created/modified, artifacts delivered), referencing specific paths
2. **Quality Criteria** — derive 3-7 criteria from the phase's task descriptions, architectural constraints, and acceptance criteria
3. The prompt must be self-contained — the quality-review agent runs in a fresh context

### 8. Format Task IDs

Apply ID format rules:
- Format: `p[phase]-[number]` or `p[phase]-[name]`
- Examples: `p1-1`, `p1-2`, `p2-auth`, `p2-checkpoint`
- IDs in YAML must match section headers in plan body

### 9. Validate Dependency Ordering

**MANDATORY:** Check for dependency violations before finalizing structure.

**Validation Checks:**

1. **Dependencies before dependents:**
   - If task B uses output from task A → A must come before B
   - Flag any violations: "⚠️ Task p2-3 depends on p3-1 output but comes before it"

2. **CREATE before UPDATE:**
   - If task says "UPDATE file.ts" → a prior task must "CREATE file.ts"
   - Flag violations: "⚠️ p2-2 UPDATEs auth.ts but no prior CREATE"

3. **No circular dependencies:**
   - A→B→C→A is invalid
   - Flag: "⚠️ Circular dependency detected: p1-2 → p2-1 → p1-2"

4. **Shared dependency grouping:**
   - Tasks reading same file should be adjacent when possible
   - Suggest: "💡 Tasks p2-1, p2-3, p2-4 all read config.yaml — consider grouping"

**If violations found:**
- Display all violations
- Propose reordering
- Ask user to confirm fix or override

### 10. Create Mermaid Workflow Diagram (Conditional)

**Complexity check — only generate a diagram when the plan has non-linear flow:**

| Plan Shape | Generate Diagram? | Rationale |
|------------|-------------------|-----------|
| All phases sequential, no branching | **No** | Linear A→B→C is self-evident from phase ordering |
| Parallel phases, branching dependencies, or complex inter-task dependencies | **Yes** | Visual aid for non-obvious flow |

**If generating a diagram**, show:
- Phases as subgraphs
- Key tasks as nodes
- Checkpoints as decision diamonds
- Flow between phases

### 11. Present Structure

Display the proposed structure:

```
## Proposed Plan Structure

### Phases
- Phase 1: [Name] — [Goal]
- Phase 2: [Name] — [Goal]
...

### Tasks by Phase

**Phase 1: [Name]**
- p1-1: Create plan folder and initial execution decisions file
- p1-2: [Task description]
- p1-checkpoint: P1 CHECKPOINT - [Description]

**Phase 2: [Name]**
- p2-1: [Task description]
...

### Workflow Diagram
[Mermaid diagram]

Does this structure look correct? Any tasks to add, remove, or reorder?
```

### 12. Present Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**Options:**
- `[C] Continue` → Proceed to artifact generation (step-04-generate-artifacts); Switch to plan mode before selecting this option
- `[A] Add Tasks` → Add more tasks to the structure
- `[M] Modify` → Change existing tasks or phases
- `[X] Exit Workflow` → Cancel plan creation

---

## NEXT STEP

On Continue selection:
1. Store final structure in session memory
2. Load and execute: `./step-04-generate-artifacts.md`

---

## SUCCESS CRITERIA

- ✅ Phases defined with clear goals
- ✅ Tasks follow granularity rules (WHAT not HOW, single action each)
- ✅ Tasks use explicit file operations (CREATE/UPDATE/DELETE/MOVE)
- ✅ Task complexity assessed (5-dimension scoring)
- ✅ Final compound task included (pN-compound)
- ✅ 3-6 checkpoints at inflection points
- ✅ Task IDs follow format rules and sync with headers
- ✅ Dependency ordering validated (no violations or user-approved overrides)
- ✅ Mermaid workflow diagram generated (only for non-linear plans)
- ✅ Each checkpoint has a review prompt subsection in the plan body (`#### P{N} Checkpoint Review Prompt`)
- ✅ User confirmed structure is correct
- ✅ Menu presented with explicit HALT
