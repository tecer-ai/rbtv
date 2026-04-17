---
title: 'Compound: BI Workflow Default Structures — Canonical Assumptions + Folder Naming'
docType: 'compound'
mode: 'create'
priority: 'Medium'
tracker: ''
stepsCompleted: ['step-01-init.md', 'step-02-self-assessment.md', 'step-03-discussion.md', 'step-04-document.md']
inputDocuments:
  - 'projects/robotville-v4.0/founder/project-memo.md'
  - '_bmad/rbtv/workflows/bi-business-innovation/templates/project-memo.md'
  - '_bmad/rbtv/workflows/bi-business-innovation/steps-c/step-01-project-setup.md'
outputPath: 'projects/planning-artifacts'
date: '2026-02-13'
yoloMode: true
---

# BI Workflow Default Structures — Canonical Assumptions + Folder Naming

**Type:** Workflow
**Priority:** Medium
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

Two structural defaults in the Business Innovation (BI) workflow need correction:

**1. No Canonical Assumption Inventory in project-memo template.** Each framework maintains its own assumption list with its own numbering. The Party Mode cross-framework review for robotville-v4.0 identified this as a coherence risk — three overlapping, inconsistently numbered lists across WB, JTBD, and PSF. The fix was manually created during that session: a `## Canonical Assumption Inventory` section in project-memo.md with PSF IDs as canonical, tiered by priority (Existential / High / Lower), with a Founder Convictions sub-section. This structure should be standard for all BI projects, not a one-off manual addition.

**2. Output folder is named `founder/` — should be `business-innovation/`.** The BI workflow creates a project output folder at `projects/{project-name}/founder/`. The name "founder" is persona-specific (it's the mentor agent's framing), not function-specific. The folder contains business innovation artefacts — frameworks, project-memo, milestone outputs. `business-innovation/` is accurate regardless of which agent or persona runs the workflow.

### Goals

1. Add a `## Canonical Assumption Inventory` section to the project-memo template with the tiered structure and guidance text proven in robotville-v4.0
2. Rename the default output folder from `founder/` to `business-innovation/` in all BI workflow references

### Constraints

- Template change must not break existing projects (robotville-v4.0 already has `founder/` — this is for future projects only, or manual migration)
- The canonical assumption section should be empty in the template (populated as frameworks are completed), but must include the structure, tier definitions, and M2 guidance text
- Folder rename affects multiple files: workflow.md, step files, and potentially the project-memo template itself

---

## Self-Assessment

### Error Analysis

**Error Type:** Knowledge gap — workflow defaults were set during initial BI workflow creation without the benefit of a real project exercising them end-to-end. robotville-v4.0 is the first full run, and it exposed two structural defaults that should be improved.

### Context Source Evaluation

| File | Issue |
|------|-------|
| `_bmad/rbtv/workflows/bi-business-innovation/templates/project-memo.md` | Missing `## Canonical Assumption Inventory` section. Each framework's template has its own assumptions section, but the project-memo (the single source of truth for project state) has no consolidated view. |
| `_bmad/rbtv/workflows/bi-business-innovation/steps-c/step-01-project-setup.md` | Creates the output folder — currently uses `founder/` as the subfolder name. |
| `_bmad/rbtv/workflows/bi-business-innovation/workflow.md` | References `founder/` in output path documentation. |
| Framework synthesis step files | Each framework's completion step updates project-memo but has no instruction to merge assumptions into a canonical list. |

### Improvement Options

1. **New Rule**: Add canonical assumption inventory as a required project-memo section
   - **Rationale:** Ensures every BI project has a single source of truth for assumptions from day one
   - **Location:** project-memo template

2. **Modify Existing Rule**: Update framework synthesis steps to merge assumptions into the canonical list
   - **Rationale:** Assumptions are added to the canonical list at the moment they're produced, not retroactively
   - **Location:** Each framework's synthesis/completion step

3. **Update System File**: Rename `founder/` to `business-innovation/` in workflow defaults
   - **Rationale:** Function-specific naming is more accurate and stable than persona-specific naming
   - **Location:** step-01-project-setup.md, workflow.md, project-memo template

4. **Add Constraint**: Canonical assumption list must be updated before a framework can be marked complete
   - **Rationale:** Prevents the drift that occurred in robotville-v4.0 where three frameworks had independent assumption lists
   - **Location:** Framework completion gate

5. **Alternative Approach (SELECTED)**: Bundle options 1 + 3 as template/default changes; option 2 as a synthesis step enhancement
   - **Rationale:** The template change (option 1) and folder rename (option 3) are pure defaults — change once, applies to all future projects. The synthesis step update (option 2) is the mechanism that keeps the canonical list current. Option 4 (constraint) is unnecessary if option 2 is implemented well — the synthesis step naturally produces the merge.
   - **Location:** See implementation details below

---

## Proposed Solution

### Change 1: Add Canonical Assumption Inventory to project-memo template

Add the following section to `_bmad/rbtv/workflows/bi-business-innovation/templates/project-memo.md` after the Progress section:

```markdown
## Canonical Assumption Inventory

**Consolidated from:** [Updated automatically as frameworks are completed. The most recent framework's IDs are canonical.]

**M2 guidance:** Use the framework with the most rigorous falsification tests as the starting point for Leap of Faith and Assumption Mapping. Prefer concrete thresholds and measurable pass/fail criteria over qualitative framing.

### Existential (if any fails, there is no business)

| ID | Assumption | Category | Confidence | Falsification Test |
|-----|-----------|----------|------------|-------------------|
| | | | | |

### High Priority

| ID | Assumption | Category | Confidence | Falsification Test |
|-----|-----------|----------|------------|-------------------|
| | | | | |

### Lower Priority

| ID | Assumption | Category | Confidence | Falsification Test |
|-----|-----------|----------|------------|-------------------|
| | | | | |

### Founder Convictions

[Optional. For assumptions where founder conviction is high but formal validation is pending. Document the reasoning — this is intellectual honesty, not bypassing validation.]
```

**Additionally:** Each framework's synthesis/completion step should include an instruction: "Merge this framework's assumptions into the project-memo's Canonical Assumption Inventory. De-duplicate against existing entries. Use the current framework's IDs as canonical for any new or refined assumptions."

### Change 2: Rename output folder from `founder/` to `business-innovation/`

Update all references in the BI workflow from `founder/` to `business-innovation/`:

- `step-01-project-setup.md`: folder creation path
- `workflow.md`: output path documentation
- `project-memo.md` template: output location reference
- Any other step files that reference the output folder by name

The output structure becomes:
```
projects/{project-name}/business-innovation/
├── project-memo.md
├── m1-conception/
│   ├── working-backwards.md
│   ├── jobs-to-be-done.md
│   └── ...
├── m2-validation/
│   └── ...
└── ...
```

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | `_bmad/rbtv/workflows/bi-business-innovation/templates/project-memo.md` (add canonical assumptions section) |
| | `_bmad/rbtv/workflows/bi-business-innovation/steps-c/step-01-project-setup.md` (rename `founder/` → `business-innovation/`) |
| | `_bmad/rbtv/workflows/bi-business-innovation/workflow.md` (update output path references) |
| | Each framework's synthesis/completion step file (add assumption merge instruction) |
| Scope of change | Moderate — template addition + multi-file string replacement for folder name |
| Related files | Existing projects using `founder/` (robotville-v4.0) are NOT affected — this changes defaults for new projects only. Manual migration is optional. |

---

## Rationale

**Canonical Assumptions:** The robotville-v4.0 Party Mode review proved that three independent assumption lists with overlapping entries and inconsistent numbering create real confusion. The manually created canonical inventory in robotville-v4.0's project-memo is well-structured (tiered priorities, falsification tests, founder convictions section) and should be the default for every BI project. Making it a template section means it exists from the start; making the synthesis steps merge into it means it stays current without manual effort.

**Folder Naming:** `founder/` is accurate for the mentor persona but misleading as a folder name. The contents are business innovation artefacts — frameworks, canvases, analyses. If a different agent (or a future non-mentor workflow) produces BI outputs, `founder/` makes no sense. `business-innovation/` is descriptive, stable, and persona-independent.

---

## Acceptance Criteria

- [ ] project-memo template includes `## Canonical Assumption Inventory` section with Existential / High / Lower tiers, empty tables, M2 guidance text, and Founder Convictions sub-section
- [ ] Each framework's synthesis step includes instruction to merge assumptions into the canonical list in project-memo
- [ ] All BI workflow references to `founder/` are updated to `business-innovation/`
- [ ] New BI projects create output at `projects/{project-name}/business-innovation/`
- [ ] Existing projects (robotville-v4.0) are not broken by the change — `founder/` folder remains as-is unless manually migrated

---

## Related Files

| File | Relationship |
|------|--------------|
| `_bmad/rbtv/workflows/bi-business-innovation/templates/project-memo.md` | Primary target — template to modify |
| `_bmad/rbtv/workflows/bi-business-innovation/steps-c/step-01-project-setup.md` | Target — folder creation logic |
| `_bmad/rbtv/workflows/bi-business-innovation/workflow.md` | Target — output path documentation |
| `projects/robotville-v4.0/founder/project-memo.md` | Reference — contains the manually created canonical assumption inventory that serves as the model |
| `cp-workflow-bi-cross-framework-consistency-gate.md` | Related compound — the consistency gate PRD addresses the same root problem (cross-framework drift) from a different angle (review process vs. structural defaults) |

---

## References

- **Source of canonical assumption structure:** robotville-v4.0 project-memo.md lines 141-178, created during Party Mode cross-framework review session (2026-02-13)
- **Folder naming feedback:** Founder direction (2026-02-13)

---

## Discussion Notes

### Selected Improvement Option
Bundled approach: Option 1 (template section) + Option 2 (synthesis step merge instruction) + Option 3 (folder rename). Yolo mode — founder directed quick documentation.

### Implementation Preferences
- **File Location:** BI workflow templates and step files
- **Scope:** Moderate — template addition + multi-file folder name update
- **Priority:** Medium — applies to future projects; current project (robotville-v4.0) already has the manual fix

### Additional Context
- Founder confirmed `business-innovation/` as the correct folder name
- The canonical assumption inventory structure from robotville-v4.0 is the proven model — replicate it as template default
- robotville-v4.0's existing `founder/` folder does not need to be renamed retroactively
