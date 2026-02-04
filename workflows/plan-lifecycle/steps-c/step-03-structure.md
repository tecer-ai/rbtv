---
stepNumber: 3
stepName: 'structure'
nextStepFile: ./step-04-finalize.md
outputFile: '{outputFolder}/{plan-name}/{plan-name}.plan.md'
dataFile: ../data/plan-creation-rules.md
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

### 10. Create Mermaid Workflow Diagram

Generate a Mermaid diagram showing:
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
- `[C] Continue` → Proceed to plan file creation (step-04)
- `[A] Add Tasks` → Add more tasks to the structure
- `[M] Modify` → Change existing tasks or phases
- `[X] Exit Workflow` → Cancel plan creation

---

## NEXT STEP

On Continue selection:
1. Store final structure in session memory
2. Load and execute: `./step-04-finalize.md`

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
- ✅ Mermaid workflow diagram generated
- ✅ User confirmed structure is correct
- ✅ Menu presented with explicit HALT
