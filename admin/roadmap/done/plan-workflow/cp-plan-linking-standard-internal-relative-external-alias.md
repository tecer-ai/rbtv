---
title: 'Compound: Plan Linking Standard (Internal Relative, External Alias)'
docType: 'compound'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted: ['step-01-init.md', 'step-02-self-assessment.md', 'step-03-discussion.md', 'step-04-document.md']
inputDocuments:
  - '.cursor/plans/robotville-vps-nanobot-rbtv-integration/robotville-vps-nanobot-rbtv-integration.plan.md'
  - '.cursor/plans/robotville-vps-nanobot-rbtv-integration/phase-1/p1-1.task.md'
  - '.cursor/plans/robotville-vps-nanobot-rbtv-integration/phase-4/p4-compound.task.md'
  - 'workflows/doc-compound-learning/workflow.md'
  - 'workflows/doc-compound-learning/steps-c/step-02-self-assessment.md'
outputPath: '_bmad/rbtv/_admin/roadmap/todos'
date: '2026-02-14'
yoloMode: false
---

# Plan Linking Standard (Internal Relative, External Alias)

**Type:** Workflow  
**Priority:** High  
**Tracker:**  
**Status:** Done

---

## Overview

### Problem

Plan artifacts currently use mixed link styles. Internal references inside plan folders were historically written with repo-root paths that embed the plan folder name, making moves brittle. External references from outside plan folders also target concrete plan file paths directly, which creates broad break risk whenever a plan folder is relocated or renamed.

### Goals

- Standardize internal plan links so they remain valid when a plan folder is moved.
- Standardize external plan references through a single stable alias path.
- Reduce manual link-fix work during plan reorganization.
- Make link behavior deterministic for both humans and agents.

### Constraints

- Must preserve existing plan content semantics and task intent.
- Must be compatible with markdown files and current repository tooling.
- Must avoid changes under `_admin/docs/BMAD-mirror/`.

---

## Self-Assessment

### Error Analysis

**Error type:** Execution failure.

User intent was "move-safe linking inside plan folders." Initial execution included an incorrect intermediate rewrite pattern before correction. The final technical state for internal links is correct, but the conversation surfaced that external references still need a clear standard to avoid future breakage and repeated ad hoc fixes.

### Context Source Evaluation

| File | Issue |
|------|-------|
| `.cursor/plans/robotville-vps-nanobot-rbtv-integration/robotville-vps-nanobot-rbtv-integration.plan.md` | Previously contained folder-name-bound references in structure/context sections; now partially normalized. |
| `.cursor/plans/robotville-vps-nanobot-rbtv-integration/phase-*/**/*.task.md` | Historically used repo-root links to `shape.md`/`learnings.md`; now converted to relative in affected files, but no global policy codified. |
| `_admin/roadmap/todos/*.md` | External references still commonly point directly to concrete plan paths, increasing move fragility. |
| `workflows/doc-compound-learning/steps-c/step-02-self-assessment.md` | Requires explicit context-source analysis and options, but does not include a reusable plan-linking standard. |
| `.cursor/rules/*.mdc` (plan/rules set) | No explicit normative rule for internal-vs-external plan linking contracts. |

### Improvement Options

1. **New Rule**: Add a dedicated rule section that defines mandatory plan-linking contracts.
   - **Rationale:** Creates source-of-truth guidance for all future plan generation/editing.
   - **Location:** `.cursor/rules/bmad-rbtv-atomic-files.mdc` or a dedicated `bmad-rbtv-plan-linking.mdc`.

2. **Modify Existing Rule**: Extend current atomic/workflow rules with explicit wording for internal and external link handling.
   - **Rationale:** Lowest operational overhead if existing rule files are already authoritative.
   - **Location:** `.cursor/rules/bmad-rbtv-atomic-files.mdc`.

3. **Update System File (SELECTED)**: Update plan-lifecycle generation/editing workflow so emitted links follow the standard automatically.
   - **Rationale:** Prevents recurrence by enforcing behavior at generation time, not only via static guidance.
   - **Location:** `workflows/plan-lifecycle/` templates and generation instructions.

4. **Add Constraint**: Add a validation step that fails when plan-folder-internal files include `.cursor/plans/{plan-name}/` style self-references.
   - **Rationale:** Detects regressions quickly and blocks brittle links from landing.
   - **Location:** plan validation workflow or lint script.

5. **Alternative Approach**: Keep direct external paths but require mass-rewrite automation whenever folders move.
   - **Rationale:** Avoids alias abstraction, but remains reactive and error-prone compared to stable indirection.
   - **Location:** ad hoc maintenance scripts.

---

## Proposed Solution

Adopt a two-part linking contract and enforce it in plan generation/edit workflows:

1. **Internal contract (inside a plan folder):**
   - Always use file-relative paths (`./`, `../`).
   - Never include `.cursor/plans/{plan-name}/` in intra-folder references.
   - Examples:
     - `../shape.md`
     - `../learnings.md`
     - `./phase-6/p6-1.task.md`

2. **External contract (outside a plan folder):**
   - Reference a stable alias file, not the mutable concrete plan file path.
   - Alias pattern:
     - `.cursor/plans/{plan-name}.md` (stable entrypoint)
     - Alias file points to current canonical plan file location.
   - On folder moves, update only the alias target.

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify/create | `workflows/plan-lifecycle/...` (generation/edit rules), `.cursor/rules/...` (normative rule text), `.cursor/plans/{plan-name}.md` alias files |
| Scope of change | Moderate |
| Related files | Existing plan files under `.cursor/plans/**`, backlog docs under `_admin/roadmap/todos/`, any validator task for plan-link integrity |

---

## Rationale

The root cause is not a one-off bad replacement; it is absence of a formal link contract. Internal relative links remove dependence on plan folder naming and location. External alias indirection confines move impact to one file and removes broad search-and-replace risk. This combines low maintenance overhead with deterministic behavior.

---

## Acceptance Criteria

- [x] A documented rule explicitly requires file-relative links for references between files within the same plan folder. → Plan Linking Standard section in `plan-creation-rules.md` (loaded as knowledge file during plan creation)
- [x] Plan generation/edit workflows emit internal links using only `./` and `../` patterns. → `plan-creation-rules.md`, `step-04-generate-artifacts.md`, `plan-task-microstep-template.md` (pre-existing + strengthened)
- [x] A stable external reference convention is documented and adopted for plan references outside plan folders. → Root-relative inbound links convention (replaces alias approach — alias files add indirection without value given plans are organized by lifecycle stage, not `.cursor/plans/`)
- [x] Validation detects and flags `.cursor/plans/{plan-name}/` style self-references inside plan folders. → `step-06-complete.md` section 1c
- [x] At least one migrated plan demonstrates compliance with both internal and external contracts. → `align-skills-anthropic-spec` (5 task files migrated from `.cursor/plans/align-skills-anthropic-spec/shape.md` → `../shape.md`)

---

## Related Files

| File | Relationship |
|------|--------------|
| `.cursor/plans/robotville-vps-nanobot-rbtv-integration/robotville-vps-nanobot-rbtv-integration.plan.md` | Primary example plan that exposed and validated the internal-link pattern issue |
| `.cursor/plans/robotville-vps-nanobot-rbtv-integration/phase-1/p1-1.task.md` | Example of intra-plan reference that must stay relative |
| `.cursor/plans/robotville-vps-nanobot-rbtv-integration/phase-4/p4-compound.task.md` | Example with both `shape.md` and `learnings.md` intra-plan references |
| `_admin/roadmap/todos/cp-plan-checkpoint-quality-review-subagent-mandate.md` | External backlog document style reference that may need alias-based linking standard |
| `workflows/doc-compound-learning/workflow.md` | Compound process source used to derive structure and requirements |

---

## References

- Trigger context: user request to make plan-folder internal links move-safe and treat resulting link state as standard.
- Workflow source: `workflows/doc-compound-learning/steps-c/step-01-init.md` through `step-04-document.md`.

---

## Discussion Notes

### Selected Improvement Option

Option 3 selected (Update System File), with Option 1 as companion governance text.

### Implementation Preferences

- **File Location:** Workflow and rule files governing plan generation plus alias files in `.cursor/plans/`.
- **Scope:** Moderate.
- **Priority:** High.

### Additional Context

The desired standard is explicit: plan-folder-internal references must remain valid after folder relocation, and external references must not require widespread manual edits on moves.
