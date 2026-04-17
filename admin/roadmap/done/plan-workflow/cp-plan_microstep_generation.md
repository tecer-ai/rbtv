---
title: 'Compound: Plan Microstep Generation'
docType: 'compound'
mode: 'create'
priority: ''
tracker: ''
stepsCompleted:
  - step-01-init.md
  - step-02-self-assessment.md
  - step-03-discussion.md
  - step-04-implementation.md
inputDocuments:
  - _bmad/rbtv/workflows/plan-lifecycle/workflow.md
  - _bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md
  - _bmad/rbtv/workflows/plan-lifecycle/templates/plan-template.md
  - _bmad/rbtv/workflows/plan-lifecycle/templates/plan-task-microstep-template.md
outputPath: '{project-root}/projects/planning-artifacts'
date: '2026-02-04'
yoloMode: false
---

# Plan Microstep Generation

**Type:** Workflow  
**Priority:** High  
**Tracker:**  
**Status:** Completed

---

## Overview

### Problem

When using the plan-lifecycle workflow, the agent created only the main plan file and failed to generate the required companion artifacts (shape.md, learnings.md) and micro-step task files (.task.md) for each task. This makes plans non-self-executing.

### Goals

Ensure that plan creation always produces the complete artifact set: main plan file, companion files, phase folders, and micro-step task files for every non-checkpoint task.

### Constraints

- CreatePlan tool only creates the main plan file; companion artifacts require separate file operations
- Micro-step template must be loaded and applied for each task
- Phase folders must exist before task files can be created in them

---

## Self-Assessment

### Error Analysis

**Error Type:** Execution failure

**Expected Behavior:** When using the plan-lifecycle workflow, after creating the main plan file, the agent should have:
1. Created `shape.md` companion file
2. Created `learnings.md` companion file  
3. Created phase folders (`phase-1/`, `phase-2/`, etc.)
4. Generated `.task.md` micro-step files for each non-checkpoint task using the template

**Actual Behavior:** Only created the main plan file via the `CreatePlan` tool and presented it as complete.

**Impact:** The plan is not self-executing. Agents resuming this plan lack the micro-step files containing detailed execution instructions for each task.

### Context Source Evaluation

| File | Loaded? | Evaluation |
|------|---------|------------|
| `_bmad/rbtv/workflows/plan-lifecycle/workflow.md` | Yes | Lines 77-80 clearly list "Micro-step files" as required output. Read but not executed. |
| `_bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md` | Yes | Lines 133-159 detail micro-step file generation rules. Read but stopped after main plan. |
| `_bmad/rbtv/workflows/plan-lifecycle/templates/plan-template.md` | Yes | Lines 83-95 show folder structure with phase folders. Structure documented but folders not created. |
| `_bmad/rbtv/workflows/plan-lifecycle/templates/plan-task-microstep-template.md` | No | **GAP**: Never loaded this template. Would have shown detailed structure required for each task file. |
| `_bmad/rbtv/workflows/plan-lifecycle/steps-c/*.md` | No | **GAP**: Did not follow the step files. Jumped directly to creating a plan using own understanding rather than following micro-file architecture. |

**Root Cause:** Bypassed the workflow's step files entirely. The workflow.md says to load `steps-c/step-01-init.md` and follow sequentially, but jumped directly to creating a plan rather than following the micro-file architecture.

### Improvement Options

1. **New Rule**: Plan Artifact Completion Checklist
   - **Rationale:** A checklist forces explicit verification of companion files and micro-step files before marking plan complete
   - **Location:** CREATE `.cursor/rules/jobs/guardrails/plan-artifact-completion.mdc`

2. **Modify Existing Rule**: Strengthen plan-creation.mdc
   - **Rationale:** The current rule may be too high-level; explicit artifact requirements would catch omissions
   - **Location:** UPDATE `.cursor/rules/jobs/guardrails/plan-creation.mdc`

3. **Update System File**: Add validation step to plan-lifecycle workflow
   - **Rationale:** Workflow-level enforcement catches the error before the user does
   - **Location:** UPDATE `_bmad/rbtv/workflows/plan-lifecycle/workflow.md` and CREATE `steps-c/step-05-validate-artifacts.md`

4. **Add Constraint**: CreatePlan tool post-condition
   - **Rationale:** The tool's output should trigger mandatory follow-up actions
   - **Location:** Document as behavioral constraint in plan-lifecycle workflow (CreatePlan tool itself is not editable)

5. **Alternative Approach**: Unified plan creation with artifact generation
   - **Rationale:** Atomic creation prevents partial completion; either all artifacts exist or none do
   - **Location:** CREATE `_bmad/rbtv/workflows/plan-lifecycle/steps-c/step-04-generate-artifacts.md` with explicit file creation for all components

---

## Proposed Solution

**Selected: Option 5 (Modified)** — Split workflow step-04 into three steps with explicit mode gating.

The CreatePlan tool is a Cursor-internal tool that ONLY creates `.plan.md` files. Companion artifacts (shape.md, learnings.md, micro-step files) require the Write tool, which requires Agent mode. The solution splits the monolithic step-04-finalize.md into three steps:

1. **step-04-generate-artifacts.md** — Requires Agent mode, creates all companion files via Write tool (shape.md, learnings.md, phase folders, micro-step files)
2. **step-05-create-plan.md** — Uses CreatePlan tool to write the .plan.md file
3. **step-06-complete.md** — Validates all artifacts exist, displays summary

### Implementation Details

| Aspect | Details |
|--------|---------|
| Files created | `steps-c/step-04-generate-artifacts.md`, `steps-c/step-05-create-plan.md`, `steps-c/step-06-complete.md` |
| Files modified | `steps-c/step-03-structure.md` (nextStepFile reference), `workflow.md` (mode overview table) |
| Files deleted | `steps-c/step-04-finalize.md` (replaced by split steps) |
| Scope of change | Workflow now has 6 steps instead of 4; step-05 enforces Agent mode before file creation |

---

## Rationale

1. **Root cause alignment** — The problem was the agent using CreatePlan and stopping. Splitting into separate steps makes artifact generation a mandatory continuation, not optional cleanup.

2. **Tool constraint acknowledgment** — CreatePlan only creates plan files. By separating plan creation (step-04) from artifact generation (step-05), the workflow explicitly handles this tool limitation.

3. **Mode gating** — Step-04 ends with explicit instruction to switch to Agent mode. Step-05 starts with mode check and halts if not in Agent mode. This prevents the "I can't write files" scenario.

4. **Micro-file architecture** — Smaller files with single responsibilities. Each step does one thing: create plan file, generate artifacts, validate and complete.

5. **Validation separation** — Step-06 validates all artifacts exist before declaring success. Missing artifacts trigger return to step-05.

---

## Acceptance Criteria

- [x] Step-04 uses CreatePlan tool and ends with mode-switch gate
- [x] Step-05 requires Agent mode and creates shape.md, learnings.md, phase folders, micro-step files
- [x] Step-06 validates all artifacts exist before completion summary
- [x] Step-03 nextStepFile updated to point to new step-04-create-plan.md
- [x] Workflow.md updated with 6-step table showing mode requirements
- [x] Old step-04-finalize.md deleted
- [ ] **Testing:** Run plan-lifecycle workflow end-to-end to verify all artifacts are created

---

## Related Files

| File | Relationship |
|------|--------------|
| `_bmad/rbtv/workflows/plan-lifecycle/workflow.md` | Parent workflow definition, updated with 6-step table |
| `_bmad/rbtv/workflows/plan-lifecycle/steps-c/step-03-structure.md` | Updated nextStepFile reference |
| `_bmad/rbtv/workflows/plan-lifecycle/steps-c/step-04-generate-artifacts.md` | NEW — Agent mode artifact generation |
| `_bmad/rbtv/workflows/plan-lifecycle/steps-c/step-05-create-plan.md` | NEW — CreatePlan step |
| `_bmad/rbtv/workflows/plan-lifecycle/steps-c/step-06-complete.md` | NEW — Validation and completion |
| `_bmad/rbtv/workflows/plan-lifecycle/templates/shape-template.md` | Used by step-05 for shape.md generation |
| `_bmad/rbtv/workflows/plan-lifecycle/templates/learnings-template.md` | Used by step-05 for learnings.md generation |
| `_bmad/rbtv/workflows/plan-lifecycle/templates/plan-task-microstep-template.md` | Used by step-05 for .task.md generation |

---

## References

- BMAD Architecture Decision Guide: `_bmad/rbtv/workflows/build-rbtv-component/data/bmad-architecture.md`
- Step Template: `_bmad/rbtv/workflows/build-rbtv-component/templates/step-template.md`

---

## Discussion Notes

**Key insight from user:** The CreatePlan tool is a Cursor-internal tool that ONLY creates `.plan.md` files. Companion artifacts require the Write tool, which requires Agent mode.

**Decision flow:**
1. User selected Option 5 (unified artifact generation step)
2. Discussion revealed CreatePlan tool limitation (only creates .plan.md files)
3. Refined to 3-step split with explicit mode gating
4. **Further refinement:** User requested order inversion — artifacts first, then plan file

**Final order (inverted):**
- Step-04: Agent mode, Write tool for artifacts (shape.md, learnings.md, phase folders, micro-step files)
- Step-05: CreatePlan tool writes .plan.md
- Step-06: Validation and summary

**Rationale for inversion:** Agent mode is needed for Write operations. By doing artifacts first, the workflow ensures Agent mode is active when file creation happens, then CreatePlan completes the plan file.
