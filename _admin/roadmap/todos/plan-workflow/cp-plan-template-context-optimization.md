---
title: 'Compound: Plan Template Context Optimization'
docType: 'compound'
mode: 'create'
priority: 'Medium'
tracker: ''
stepsCompleted:
  - step-01-init.md
  - step-02-self-assessment.md
  - step-03-discussion.md
  - step-04-document.md
inputDocuments:
  - .cursor/plans/nanobot-standard-architecture/nanobot-standard-architecture.plan.md
outputPath: '_admin/roadmap/todos'
date: '2026-02-22'
yoloMode: true
---

# Plan Template Context Optimization

**Type:** Workflow + Template  
**Priority:** Medium  
**Tracker:**  
**Status:** Backlog

---

## Overview

### Problem

The plan template (`workflows/plan-lifecycle/templates/plan-template.md`) produces plan files with systematic content duplication. The `nanobot-standard-architecture.plan.md` generated from this template is 543 lines, with significant portions repeating content that already exists in companion files (shape.md, microstep task files, YAML frontmatter). Agents executing the plan load all this redundant context, wasting tokens and crowding the context window.

Specific duplication patterns:

| Duplicated Content | In Plan Body | Already In |
|----|----|----|
| Task descriptions | Phase sections re-list every task with description | YAML `content` field in frontmatter |
| Decisions, constraints, rejected alternatives | Context section | `shape.md` Original Shaping |
| Per-task file dependencies | Files to Load table | Microstep `Context Files` table per task |
| Execution protocol, tool mode selection, quality gates | Self-Execution Instructions section | Standard boilerplate; partially in `shape.md` |
| Plan folder layout | Folder Structure section | Discoverable via filesystem |
| Workflow diagram | Always generated | Adds no value for linear sequential plans |

### Goals

- Plan body contains only information not already in companion files
- Executing agents load minimal context from the plan file
- Phase sections reference YAML tasks rather than repeating them
- Mermaid diagrams are conditional on plan complexity
- Files to Load is per-task (in microstep files), not duplicated at plan level

### Constraints

- Plans must remain self-executing without requiring agents to read multiple files to understand the plan's purpose
- YAML frontmatter (the task list) is the primary execution data — this must remain complete
- Architectural constraints section is plan-specific and must stay in the plan body
- Shape.md and microstep files are the correct homes for context and per-task instructions
- Must not break the plan-lifecycle workflow's step sequence

---

## Self-Assessment

### Error Analysis

**Error type:** Execution failure (structural)

The plan-creation workflow was followed correctly — the agent populated every section the template mandates. The template itself causes the duplication. Each mandatory section is individually reasonable, but together they create a plan body that largely restates what companion files and YAML frontmatter already contain.

**Expectation vs actual:**
- **Expected:** Plan body is a lean execution index — YAML has the task list, shape.md has context/decisions, microstep files have per-task instructions.
- **Actual:** Plan body re-narrates the YAML tasks in Phase sections, re-presents decisions/constraints from shape.md, re-lists per-task file dependencies from microstep files, and includes boilerplate execution instructions.

**Impact:** The `nanobot-standard-architecture.plan.md` is 543 lines. An optimized version retaining only unique, non-duplicated content would be roughly 150-200 lines — a ~65% reduction in plan-body token cost.

### Context Source Evaluation

| File | Role | Issue |
|------|------|-------|
| `workflows/plan-lifecycle/templates/plan-template.md` | Plan body template | Mandates 11 sections; ~5 duplicate companion files |
| `workflows/plan-lifecycle/data/plan-creation-rules.md` | Plan structure rules | "Plan Structure" section lists 11 required sections without de-duplication guidance |
| `workflows/plan-lifecycle/steps-c/step-03-structure.md` | Structure creation step | Step 10 always generates Mermaid diagram — no complexity conditional |
| `workflows/plan-lifecycle/steps-c/step-05-create-plan.md` | Plan file creation step | Compiles body from template without filtering duplicated content |
| `workflows/plan-lifecycle/templates/plan-task-microstep-template.md` | Microstep template | Already has per-task Context Files table — plan-level Files to Load is redundant |
| `workflows/plan-lifecycle/templates/shape-template.md` | Shape template | Already has constraints, decisions, standards — duplicated in plan body Context section |

### Improvement Options

1. **New Rule**: Add "No Content Repetition in Plans" to `plan-creation-rules.md`
   - **Rationale:** Codifies the atomic files principle for plans — plan body must not repeat content from shape.md, microstep files, or YAML frontmatter
   - **Location:** `workflows/plan-lifecycle/data/plan-creation-rules.md`

2. **Modify Existing Rule**: Slim `plan-template.md` by removing sections that duplicate companions
   - **Rationale:** Remove Folder Structure, Context section (in shape.md), Files to Load (in microstep files), most Self-Execution Instructions (boilerplate). Keep YAML, Architectural Constraints, lean Phase headers, conditional Mermaid.
   - **Location:** `workflows/plan-lifecycle/templates/plan-template.md`

3. **Update System File**: Make Mermaid diagram conditional in `step-03-structure.md`
   - **Rationale:** Linear plans (A→B→C) gain nothing from a diagram. Reserve for branching/parallel workflows.
   - **Location:** `workflows/plan-lifecycle/steps-c/step-03-structure.md`

4. **Add Constraint**: Phase sections must not re-narrate YAML `content` fields
   - **Rationale:** YAML frontmatter IS the task list. Phase sections provide phase-level goal only; agents read YAML for task details.
   - **Location:** `workflows/plan-lifecycle/templates/plan-template.md`, `plan-creation-rules.md`

5. **Alternative Approach**: Restructure plan as YAML-first thin index
   - **Rationale:** Plan body = YAML (full task list) + Architectural Constraints + Revolving Plan Rules + conditional Mermaid. All context/decisions in shape.md, per-task instructions in microstep files. ~65% token reduction.
   - **Location:** Restructure `plan-template.md`, `plan-creation-rules.md`, `step-03-structure.md`, `step-05-create-plan.md`

---

## Proposed Solution

**Selected: Option 5 (thin index) + Option 2 (slim template) + Option 3 (conditional diagram).**

### A. Restructure `plan-template.md` as thin execution index

**Remove these sections entirely:**

| Section | Reason |
|---------|--------|
| Context (Problem, Goals, Constraints, Decisions, Rejected Alternatives) | Already in `shape.md` Original Shaping |
| Companion Files table | Boilerplate — agents know companion files exist |
| Folder Structure | Discoverable via filesystem |
| Files to Load table | Already in microstep `Context Files` per task |
| Self-Execution Instructions (most of it) | Standard boilerplate; move essential items to Inviolable Rules |

**Keep these sections (slim):**

| Section | What Stays |
|---------|------------|
| YAML frontmatter | Full task list with `taskFile` references — unchanged |
| Architectural Constraints | Plan-specific patterns and inviolable rules (merged into one lean section) |
| Revolving Plan Rules | Discovery handling, task modification — keep brief |
| Execution Workflow (Mermaid) | **Conditional** — only for non-linear plans |
| Phase headers | Phase name + goal only; task details read from YAML `content` field |

**Proposed slim plan body structure:**

```markdown
# {Plan Name}

> Read `shape.md` for full context, decisions, and constraints.
> Read individual `.task.md` files (referenced via `taskFile`) for per-task execution instructions.

## Architectural Constraints

| Principle | Enforcement |
|-----------|-------------|
| {Plan-specific rule} | {How violations are detected} |

**Inviolable Rules:**
1. Read shape.md before starting any task
2. Only one task `in_progress` at a time
3. Dependencies are sacred — never skip prerequisites
4. Checkpoints require human approval
5. Append to shape.md after each task

## Revolving Plan Rules

- Simple discovery (<5 min): resolve immediately, document in shape.md
- Complex discovery: add new task, document in shape.md, notify user

## Execution Workflow

{Mermaid diagram — ONLY if plan has branching or parallel phases}

## Phases

### Phase 1: {Name} — {Goal}
### Phase 2: {Name} — {Goal}
...
```

### B. Make Mermaid diagram conditional in `step-03-structure.md`

Add complexity check before diagram generation:

| Plan Shape | Diagram? | Rationale |
|------------|----------|-----------|
| All phases sequential, no branching | No | Linear A→B→C→D is self-evident from phase ordering |
| Any parallel phases, branching dependencies, or complex inter-task dependencies | Yes | Visual aid for non-obvious flow |

### C. Update `plan-creation-rules.md`

Add rule:

> **Plan Body Minimalism:** The plan body must not repeat content from shape.md, microstep files, or YAML frontmatter. Reference companion files; do not duplicate them. Phase sections state phase goal only — task details are in YAML `content` and `taskFile`.

Update "Plan Structure" section to reflect the reduced required sections (from 11 to ~5).

### D. Update `step-05-create-plan.md`

Adjust compilation instructions to produce the slim body format instead of the current comprehensive format.

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | `workflows/plan-lifecycle/templates/plan-template.md`, `workflows/plan-lifecycle/data/plan-creation-rules.md`, `workflows/plan-lifecycle/steps-c/step-03-structure.md`, `workflows/plan-lifecycle/steps-c/step-05-create-plan.md` |
| Scope of change | Moderate — 4 files, primarily template restructuring and rule updates |
| Related files | `workflows/plan-lifecycle/templates/shape-template.md` (no changes — already correct), `workflows/plan-lifecycle/templates/plan-task-microstep-template.md` (no changes — already correct) |

---

## Rationale

The root cause is that the plan template was designed as a standalone comprehensive document, but the plan-lifecycle workflow also produces companion files (shape.md, microstep files) that contain the same information. The template predates the companion file architecture — it was never pruned after shape.md and microstep files took over the context and per-task instruction roles.

The atomic files rule already requires "No Content Repetition" and "Each file MUST be interpretable independently." Applying this principle to the plan template means the plan body should contain only what is unique to the plan file (architectural constraints, revolving plan rules, phase goals) and reference companion files for everything else.

The estimated token reduction is ~65% of plan body content (from ~543 lines to ~150-200 lines), directly reducing context window pressure for executing agents.

---

## Acceptance Criteria

- [ ] `plan-template.md` does not contain Context, Folder Structure, Files to Load, or Self-Execution Instructions sections
- [ ] Plan body references shape.md for decisions/constraints instead of repeating them
- [ ] Phase sections contain phase goal only — no task re-listing beyond YAML frontmatter
- [ ] Mermaid diagram generation is conditional on plan complexity (non-linear only)
- [ ] `plan-creation-rules.md` includes "Plan Body Minimalism" rule prohibiting duplication
- [ ] `step-05-create-plan.md` generates slim body format
- [ ] A plan generated with the updated template is ≤200 lines (excluding YAML frontmatter)
- [ ] Executing agents can still understand plan purpose and constraints from the plan file alone (with shape.md reference)

---

## Related Files

| File | Relationship |
|------|--------------|
| `workflows/plan-lifecycle/templates/plan-template.md` | Primary target — restructure to thin index |
| `workflows/plan-lifecycle/data/plan-creation-rules.md` | Add minimalism rule, update required sections |
| `workflows/plan-lifecycle/steps-c/step-03-structure.md` | Conditional Mermaid diagram |
| `workflows/plan-lifecycle/steps-c/step-05-create-plan.md` | Update compilation instructions |
| `workflows/plan-lifecycle/templates/shape-template.md` | Already correct — no changes needed |
| `workflows/plan-lifecycle/templates/plan-task-microstep-template.md` | Already correct — no changes needed |
| `.cursor/plans/nanobot-standard-architecture/nanobot-standard-architecture.plan.md` | Concrete example of the bloat problem |

---

## References

- Atomic Files Rule (`.cursor/rules/bmad-rbtv-atomic-files.mdc`) — "No Content Repetition" principle
- `nanobot-standard-architecture.plan.md` — 543-line plan demonstrating the duplication patterns
- Plan-lifecycle workflow — the creation pipeline that produces bloated plans

---

## Discussion Notes

### Selected Improvement Option
Option 5 (thin index) + Option 2 (slim template) + Option 3 (conditional diagram). Combined approach: restructure plan as YAML-first execution index, remove sections duplicating companion files, make Mermaid conditional.

### Implementation Preferences
- **File Location:** `workflows/plan-lifecycle/` (4 files)
- **Scope:** Moderate (template restructuring + rule updates)
- **Priority:** Medium

### Additional Context
- User identified the problem after generating the first plan with the current template — direct observation of ~543 lines of output with significant redundancy.
- User explicitly noted: "information should not be repeated, unless necessary" and "files to load should be in the microstep files, not in the plan body."
- User confirmed Mermaid diagrams add value for complex workflows but not for linear ones.
- The plan-lifecycle companion files (shape.md, microstep files) are already well-designed — the plan template simply hasn't been updated to defer to them.
