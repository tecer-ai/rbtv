---
title: 'Compound: Plan Lifecycle — taskFile YAML Field and Execution Protocol Gaps'
docType: 'compound'
mode: 'create'
priority: 'Medium'
tracker: ''
stepsCompleted: ['step-01-init.md', 'step-03-discussion.md', 'step-04-document.md']
inputDocuments:
  - '_admin/roadmap/_plans/ps-lite-domcobb/ps-lite-domcobb.plan.md'
  - 'workflows/plan-lifecycle/templates/plan-template.md'
  - 'workflows/plan-lifecycle/data/plan-creation-rules.md'
  - 'workflows/plan-lifecycle/steps-c/step-03-structure.md'
  - 'workflows/plan-lifecycle/steps-c/step-04-generate-artifacts.md'
  - 'workflows/plan-lifecycle/steps-c/step-06-complete.md'
outputPath: '_admin-output/planning-artifacts'
date: '2026-02-12'
yoloMode: false
---

# Plan Lifecycle — taskFile YAML Field and Execution Protocol Gaps

**Type:** Workflow
**Priority:** Medium
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

The plan lifecycle workflow creates micro-step `.task.md` files for complex tasks, but the YAML `todos` frontmatter — which is the primary task index agents read — contains no reference to these files. An agent executing a plan from the YAML todos would only see the `content` description and miss the detailed execution phases, context file lists, and validation criteria in the companion `.task.md` file.

Additionally, the plan template's "Self-Execution Instructions" section has two gaps:
1. It says "each task's micro-step file" as if ALL tasks have one, but only complex tasks do. There is no instruction telling agents to check for a `taskFile` field and conditionally load it.
2. It never mentions `learnings.md` — agents executing tasks have no guidance on when to append system-level learnings during execution.

**Observed in:** The `ps-lite-domcobb` plan, where task `p1-1` has a detailed `phase-1/p1-1.task.md` micro-step file, but its YAML todo `content` field only says what to do — never to read the micro-step file.

### Goals

1. Add an optional `taskFile` field to the YAML todo schema so agents always know when a companion micro-step file exists
2. Update the plan template's Self-Execution Instructions to give agents clear, conditional guidance: read `taskFile` if present, otherwise execute from `content`
3. Add concrete learnings.md guidance to the execution protocol so agents know when and what to append during task execution
4. Ensure step-06 validation cross-checks `taskFile` entries against actual `.task.md` files on disk (bidirectional)

### Constraints

- Must be backward-compatible — existing plans without `taskFile` fields still work (field is optional)
- Must not change when micro-step files are created — the existing step-04 criteria (2+ context files, 3+ substeps, tool usage, phased execution) are correct and sufficient
- The per-task complexity score (5-dimension, 1-3 each) should NOT be used as the micro-step decision threshold — the step-04 qualitative criteria are more actionable than a numeric score

---

## Self-Assessment

*Skipped — this improvement was identified by the user during review of an externally-created plan, not from an agent execution error.*

---

## Proposed Solution

A multi-file update to the plan lifecycle workflow that introduces the `taskFile` field, updates execution instructions, and adds validation.

### Change 1: Add `taskFile` field to YAML todo schema

**Files:** `templates/plan-template.md`, `data/plan-creation-rules.md`

Add an optional `taskFile` field to the todo item schema. Present only when a micro-step file was generated for that task.

```yaml
todos:
  # Complex task — has micro-step file
  - id: p1-1
    content: "p1-1: Implement authentication flow with OAuth2 integration"
    taskFile: "phase-1/p1-1.task.md"
    status: pending

  # Simple task — no micro-step file needed
  - id: p1-2
    content: "p1-2: UPDATE src/config.ts to add the new API endpoint URL"
    status: pending

  # Checkpoint — never has a micro-step file
  - id: p1-checkpoint
    content: "P1 CHECKPOINT - Verify auth flow works end-to-end"
    status: pending
```

The `taskFile` path is relative to the plan folder (e.g., `phase-1/p1-1.task.md`).

### Change 2: Update step-04 to populate `taskFile` when generating micro-step files

**File:** `steps-c/step-04-generate-artifacts.md`

In section 6 ("Generate Micro-Step Task Files"), after generating each `.task.md` file, also set the `taskFile` field in the corresponding YAML todo entry. The existing decision criteria for when to generate a micro-step file remain unchanged:

**Generate when ANY apply:**
- Task requires loading 2+ context files
- Task uses specialized RBTV tools (subagents, skills)
- Task has 3+ distinct substeps
- Task requires phased execution (understand → execute → validate)
- Task produces output that needs quality review

**Skip when ALL apply:**
- Task is self-explanatory from its `content` description
- Single action, completable in one step
- No special context files or tools needed

When a micro-step file IS generated → set `taskFile: "phase-{N}/{task-id}.task.md"` in the YAML todo.
When a micro-step file is NOT generated → omit the `taskFile` field entirely.

### Change 3: Fix step-06 validation to check `taskFile` bidirectionally

**File:** `steps-c/step-06-complete.md`

Replace the current validation rule ("one `.task.md` per non-checkpoint task") with bidirectional validation:

1. **YAML → Disk:** Every todo with a `taskFile` field → verify the referenced file exists on disk
2. **Disk → YAML:** Every `.task.md` file found on disk → verify a matching `taskFile` entry exists in the YAML

This catches both orphaned files (`.task.md` exists but no YAML reference) and broken references (`taskFile` points to a missing file).

### Change 4: Update Self-Execution Instructions in plan template

**File:** `templates/plan-template.md`

Replace the current "Self-Execution Instructions" section with updated language:

```markdown
## Self-Execution Instructions

Plans are self-executing. Complex tasks have companion micro-step files referenced via the `taskFile` field in the YAML frontmatter.

### Execution Protocol

1. **Before task:** Read shape.md Decisions and Discoveries for prior context
2. **During task:** If the task has a `taskFile` field, read that file and follow its execution phases (understand → execute → validate → close). If no `taskFile` is present, execute directly from the task's `content` description.
3. **After task:** Append entry to shape.md, mark task completed in YAML
4. **Learnings:** During any task, append to learnings.md when you encounter a system-level improvement opportunity:
   - User corrects your behavior or approach
   - You couldn't find a file or reference that should have been discoverable
   - You loaded context that turned out to be unnecessary
   - Instructions were ambiguous and you had to guess
   - A rule or constraint was missing that would have prevented a mistake
   - You discovered a reusable pattern that should be codified
```

### Change 5: Update inline content example in plan-creation-rules.md

**File:** `data/plan-creation-rules.md`

Update the "Inline Content Examples" section to show the `taskFile` field and remove the comment-based `# See:` workaround:

```yaml
# Simple task — NO micro-step file needed
- id: p1-2
  content: "p1-2: UPDATE src/config.ts to add the new API endpoint URL from the design doc"
  status: pending

# Complex task — micro-step file generated
- id: p2-1
  content: "p2-1: Implement authentication flow with OAuth2 integration"
  taskFile: "phase-2/p2-1.task.md"
  status: pending
```

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | `workflows/plan-lifecycle/templates/plan-template.md`, `workflows/plan-lifecycle/data/plan-creation-rules.md`, `workflows/plan-lifecycle/steps-c/step-04-generate-artifacts.md`, `workflows/plan-lifecycle/steps-c/step-06-complete.md` |
| Scope of change | Moderate — 4 files, all within plan-lifecycle workflow |
| Related files | `workflows/plan-lifecycle/templates/plan-task-microstep-template.md` (no change needed — task files themselves are fine), `workflows/plan-lifecycle/steps-c/step-03-structure.md` (no change needed — complexity scoring stays for task sizing, not micro-step decisions) |

---

## Rationale

The `taskFile` field is the cleanest solution because:

1. **Declarative over convention** — Agents reading the YAML immediately see whether a companion file exists, without needing to know the naming convention or scan the filesystem
2. **Backward-compatible** — Optional field; existing plans and simple tasks simply omit it
3. **Machine-readable** — Enables validation (step-06) and tooling, unlike prose references like "See: phase-1/p1-1.task.md"
4. **Clean separation** — `content` stays as a human-readable summary; `taskFile` carries the execution reference. No need to pollute `content` with "READ file X..." instructions

The learnings.md addition is necessary because the execution protocol is the only place agents look for "how to execute tasks" — if learnings.md isn't mentioned there with concrete triggers, agents won't use it, making the final compound task (`pN-compound`) operate on an empty file.

### Decisions Made During Discussion

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Micro-step decision mechanism | Keep step-04 qualitative criteria only | "2+ context files, 3+ substeps" is more actionable than "score > 7" |
| Complexity score role | Task sizing only, NOT micro-step threshold | Score helps decide whether to split a task, not whether to create a `.task.md` |
| `taskFile` path format | Relative to plan folder | Keeps paths short and portable (`phase-1/p1-1.task.md`) |
| Option 1 (content string prefix) | Rejected | Redundant if `taskFile` field exists; keeps `content` clean |
| Learnings triggers | Concrete observable events | Agent needs recognizable moments, not abstract "improvement radar" |

---

## Acceptance Criteria

- [ ] Plan template YAML schema includes optional `taskFile` field with example showing both present and absent cases
- [ ] Plan template Self-Execution Instructions reference `taskFile` conditionally ("if `taskFile` present, read it; otherwise execute from `content`")
- [ ] Plan template execution protocol includes learnings.md guidance with at least 5 concrete trigger conditions
- [ ] `plan-creation-rules.md` inline content examples updated to show `taskFile` field (replacing `# See:` comment pattern)
- [ ] `step-04-generate-artifacts.md` populates `taskFile` in YAML when generating a micro-step file, omits it when not
- [ ] `step-06-complete.md` validates bidirectionally: YAML `taskFile` → file exists on disk, and `.task.md` on disk → matching `taskFile` in YAML
- [ ] No changes to micro-step file creation criteria (step-04 qualitative criteria unchanged)
- [ ] No changes to complexity scoring dimensions or thresholds (used for task sizing only)
- [ ] Existing plans without `taskFile` fields remain valid (field is optional)

---

## Related Files

| File | Relationship |
|------|--------------|
| `workflows/plan-lifecycle/templates/plan-template.md` | Primary target — YAML schema + execution instructions |
| `workflows/plan-lifecycle/data/plan-creation-rules.md` | Target — inline examples, micro-step generation rules |
| `workflows/plan-lifecycle/steps-c/step-04-generate-artifacts.md` | Target — must populate `taskFile` during generation |
| `workflows/plan-lifecycle/steps-c/step-06-complete.md` | Target — must validate `taskFile` entries |
| `workflows/plan-lifecycle/steps-c/step-03-structure.md` | Related — complexity scoring stays unchanged (task sizing only) |
| `workflows/plan-lifecycle/templates/plan-task-microstep-template.md` | Related — no change needed; task file structure is fine |
| `_admin/roadmap/_plans/ps-lite-domcobb/ps-lite-domcobb.plan.md` | Reference — the plan that exposed this gap |

---

## References

- Conversation with Henri (2026-02-12) identifying the gap in `ps-lite-domcobb` plan YAML
- Plan lifecycle workflow source files in `workflows/plan-lifecycle/`

---

## Discussion Notes

### Selected Improvement Options
- **Option 3 (primary):** Add `taskFile` field to YAML schema — declarative, machine-readable, clean
- **Option 2 (guard):** Extend step-06 validation for bidirectional `taskFile` ↔ file checking
- **Additional:** Update execution protocol with `taskFile` conditional logic and learnings.md triggers

### Implementation Preferences
- **Scope:** Moderate — 4 workflow files
- **Priority:** Medium

### Key Decisions
- **Option 1 rejected:** Embedding "READ {file}" in `content` strings is redundant with `taskFile` field and pollutes the description
- **Complexity score decoupled:** Score is for task sizing (should I split this task?), NOT for micro-step file decisions. Step-04's qualitative criteria (2+ context files, 3+ substeps, etc.) are more actionable than a numeric threshold
- **Not all tasks get micro-step files:** Only complex tasks per step-04 criteria. Simple tasks execute from `content` alone. Checkpoints never have micro-step files
- **Learnings triggers must be concrete:** "User corrected you", "couldn't find a file", "loaded unnecessary context" — recognizable moments, not abstract improvement radar
