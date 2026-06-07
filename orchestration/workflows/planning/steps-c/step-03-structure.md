---
stepNumber: 3
stepName: 'structure'
nextStepFile: ./step-04-generate-artifacts.md
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

Score the work with the **shared widened complexity rubric** — the single source for axes, bands, and doors: `{rbtv_path}/orchestration/workflows/_shared/authoring/complexity-rubric.md`. Apply it directly (Context Size / Tool Usage / Human Review at 1-3; Dependencies at 1-4; Decision Density at 1-5; summed over 5-18 → Simple 5-8 / Moderate 9-13 / Complex 14-18). Use the band to size tasks per `../data/plan-creation-rules.md` § Complexity Assessment.

**Human review need maps directly to the task file's `human_review` frontmatter** (None → `none`, Optional → `optional`, Required → `required`). When set to `required`, the executor MUST emit a Human Review Presentation block at Phase: Close — see `step-04-generate-artifacts.md` § Setting `human_review` for the criteria. Set this dimension deliberately: under-setting hides risks; over-setting trains the user to skim flag blocks.

### 6. Add Final Compound Task

**MANDATORY:** The last task of the final phase MUST be a compound learnings task:

```
- [ ] `pN-compound` Review learnings.md and compound into system improvements
```

### 6b. Identify Spec Features (code work)

If step-02 flagged the plan code-bearing, identify the **features** — each a bounded owner-observable behavior. One spec backs each feature (one spec MAY back several task files). Plan a spec artifact per feature now; step-04 authors each from the shared spec template (`{rbtv_path}/orchestration/workflows/_shared/authoring/spec-template.md`) per `../data/plan-creation-rules.md` § Spec Authoring. Each backing task will REFERENCE its spec, never restate it. Docs-only / research plans skip this step.

### 6c. DEEP-mode Pre-Resolution (orchestrated plans)

If step-02 set `orchestrated: true` with **DEEP** mode, resolve the pre-resolution set WITH the user and plan where each field lands so the router reads fields, never re-derives them (`../data/plan-creation-rules.md` § Orchestration-Aware Modes — DEEP-mode pre-resolution set):

- Per-task **executor (model, variant)** and **reviewer pin** → task frontmatter
- Per-task **file allowlist** (✚/✎/✗) and **validation commands** (+ expected EXIT) → task frontmatter/body
- **Batching / serialization order** per shared file and parallel-wave grouping → plan body
- **Hard-halt registry** (checkpoints non-overridable in autonomous mode) → plan body

**LIGHT** mode resolves only the critical subset the user chooses; the rest stay model-bound-at-routing-time. A plain (non-orchestrated) plan skips this step. HALT discipline is mode-independent in every case.

### 7. Generate Checkpoints

Add 3-6 checkpoints at inflection points:
- Use ID format: `p[N]-checkpoint`
- Content format: `CHECKPOINT — [Description]`
- Place at: Phase transitions, critical decisions, major deliverables

**Compose review criteria for each checkpoint:**

For each checkpoint, prepare the content that will go into its `.task.md` file:

1. **Work to Evaluate** — summarize what the preceding phase produced (files created/modified, artifacts delivered), referencing specific paths
2. **Review Criteria** — derive 3-7 specific criteria from the phase's task descriptions, architectural constraints, and acceptance criteria; INCLUDE the decisions.md audit checklist (`../data/plan-creation-rules.md` § Decisions-File Discipline) — the checkpoint enforces UPDATE-not-REWRITE and the ≥50% size floor
3. **Gate behavior** — evaluate against criteria, present findings, HALT for human approval

### 8. Format Task IDs

Apply ID format rules:
- Format: `p[phase]-[number]` or `p[phase]-[name]`
- Examples: `p1-1`, `p1-2`, `p2-auth`, `p2-checkpoint`

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

Display the proposed structure as a Markdown task list:

```markdown
## Proposed Plan Structure

### Phase 1: {Name} — {Goal}

- [ ] `p1-1` {Task description} → task file
- [ ] `p1-2` {Simple task description}
- [ ] `p1-checkpoint` **CHECKPOINT** — {Description} → task file

### Phase 2: {Name} — {Goal}

- [ ] `p2-1` {Task description} → task file
...

Does this structure look correct? Any tasks to add, remove, or reorder?
```

### 12. Present Menu

Present the following menu and HALT. Wait for user selection.

---

## MENU

**Options:**
- `[C] Continue` → Proceed to artifact generation (step-04)
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
- ✅ 3-6 checkpoints at inflection points with review criteria composed
- ✅ Task IDs follow format rules
- ✅ Dependency ordering validated (no violations or user-approved overrides)
- ✅ Mermaid workflow diagram generated (only for non-linear plans)
- ✅ User confirmed structure is correct
- ✅ Menu presented with explicit HALT
