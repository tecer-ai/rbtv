---
title: 'Compound: Install Scripts Standardize BMAD Output Folder Paths'
docType: 'compound'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted: ['step-01-init.md', 'step-02-self-assessment.md', 'step-03-discussion.md', 'step-04-document.md']
inputDocuments: []
outputPath: '{project-root}/_bmad/rbtv/_admin/roadmap/todos'
date: '2026-02-13'
yoloMode: false
---

# Install Scripts Standardize BMAD Output Folder Paths

**Type:** Workflow  
**Priority:** High  
**Tracker:**  
**Status:** Backlog

---

## Overview

### Problem

RBTV currently allows output-path behavior to drift across installation paths and workflow defaults. The requested behavior is that both RBTV installers (admin and normal) update BMAD core config so outputs resolve to `projects/{project-name}/`, while compound outputs continue to use RBTV roadmap/todos location conventions. Existing defaults still point to legacy planning-artifacts routing in some paths, creating inconsistent destinations.

### Goals

- Ensure both install scripts apply the same output-path normalization to BMAD config.
- Standardize BMAD output base to `projects/{project-name}/` for project-scoped artifacts.
- Keep compound PRD location behavior aligned with roadmap/todos expectations.
- Remove ambiguity so users do not need manual path fixes after installation.

### Constraints

- Must update all installer modes of the unified installer (`_config/install-rbtv.py` — IDE, admin, and sync modes) consistently.
- Should reuse already established PRD-location decisions where applicable; avoid redundant scope.
- Compound output-location correction remains in scope and must not regress.
- Changes should be moderate and targeted; avoid broad refactors unrelated to output-path behavior.

---

## Self-Assessment

### Error Analysis

**Error Type:** Execution failure.

The requested behavior was specific: when both RBTV install scripts run (admin and normal), they should update BMAD core config output paths to `projects/{project-name}/`, and the prior backlog item should be partially superseded (PRD-location part absorbed, compound-output part still required). The current behavior still depends on legacy output conventions and does not enforce the requested normalized destination across both installer paths.

**Expectation vs actual:**
- **Expected:** Both installers consistently rewrite output path fields in BMAD config to the new canonical pattern.
- **Actual:** Output location logic remains split across old assumptions, and compound workflow output location remains separately misaligned from roadmap/todos conventions.

**Impact:**
- Agents and workflows can write docs/PRDs into inconsistent directories.
- Additional manual correction is required after install.
- Repeated confusion across sessions because path resolution appears valid but targets wrong folders.

### Context Source Evaluation

Files that influenced behavior and observed gaps:

- `.cursor/rules/admin-rbtv-bmad-mirror.mdc`
  - Clear on path mirroring and installer responsibilities, but does not explicitly enforce the new `projects/{project-name}/` convention across both installers.
- `agents/ana.md`
  - Correctly routes to doc workflows; no direct defect, but it inherits output behavior from downstream workflows and config.
- `workflows/doc-compound-learning/workflow.md`
  - Declares `outputFolder: '{project-root}/projects/planning-artifacts'`, which conflicts with RBTV backlog convention (`_admin/roadmap/todos`).
- `_admin/roadmap/todos/prd-standardize-main-config-frontmatter.md`
  - Highlights config declaration consistency concerns; useful supporting signal for centralizing path behavior.
- `_config/install-rbtv.py` (unified installer, all 3 modes — target implementation file)
  - Need aligned config mutation logic so both installation paths converge on identical output-folder behavior.

Missing/ambiguous context:
- No single authoritative rule file currently enforces that all unified installer modes must apply identical output-folder normalization.
- Existing workflow defaults still embed legacy output destinations.

### Improvement Options

1. **New Rule**: Add an RBTV rule that mandates installer parity for output-path rewriting and defines canonical target pattern `projects/{project-name}/`.
   - **Rationale:** Makes future regressions detectable and prevents one installer drifting from the other.
   - **Location:** `.cursor/rules/bmad-rbtv-output-path-governance.mdc` (new file) or existing RBTV rules file.

2. **Modify Existing Rule**: Extend admin mirror rule text to explicitly require that both installers mutate BMAD core config output paths using the same canonical mapping.
   - **Rationale:** Reuses established admin rule loading behavior and keeps path governance discoverable in one high-priority rule.
   - **Location:** `.cursor/rules/admin-rbtv-bmad-mirror.mdc` under installation and boundaries sections.

3. **Update System File**: Refactor install logic into a shared helper for config path rewriting, called by both `_config/install-rbtv.py` and `_admin/install-admin-rbtv.py`, and update compound workflow output default.
   - **Rationale:** Fixes behavior at source and enforces code-level parity instead of relying only on instructions.
   - **Location:** `_config/install-rbtv.py`, `_admin/install-admin-rbtv.py`, and `workflows/doc-compound-learning/workflow.md`.

4. **Add Constraint**: Add a post-install validation gate that fails with actionable error if required output paths are not rewritten to the canonical format.
   - **Rationale:** Converts silent misconfiguration into explicit failure, reducing hidden drift.
   - **Location:** End of both installer scripts as shared validation routine; optionally mirrored in test/check task.

5. **Alternative Approach**: Move output path configuration into a single declarative mapping file consumed by installers and doc workflows.
   - **Rationale:** Central configuration reduces duplication and keeps workflow + installer outputs synchronized by design.
   - **Location:** New config file under `_config/` with loader updates in installer scripts and affected workflow frontmatter resolution.

---

## Proposed Solution

Implement a system-level fix (implementation-first approach) by updating all modes of the unified installer to enforce the same BMAD output-path rewrite rule and updating compound workflow output routing.

### Specification

1. **Installer parity update**
   - Update the unified installer (`_config/install-rbtv.py`) so all modes (IDE, admin, sync) mutate BMAD core config output fields to the same canonical base pattern: `projects/{project-name}/`.
   - Ensure any relevant `planning_artifacts`/`implementation_artifacts`-style paths derive from this normalized base.

2. **Compound workflow output correction**
   - Update `workflows/doc-compound-learning/workflow.md` output-folder configuration so compound PRDs are created in RBTV roadmap todos location (instead of generic planning-artifacts path).

3. **Scope boundary**
   - Do not include broader config-frontmatter standardization in this PR.
   - Keep this change focused on output-path correctness and installer consistency.

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify/create | `_config/install-rbtv.py` (all 3 modes); `workflows/doc-compound-learning/workflow.md` |
| Scope of change | Moderate (targeted config rewrite and workflow output-path adjustment only) |
| Related files | `_bmad/bmm/config.yaml`; `_config/config.yaml`; `workflows/doc-compound-learning/workflow.md` |

---

## Rationale

This directly addresses the execution-failure root cause from Self-Assessment: behavior is inconsistent because output resolution is controlled in multiple places without a single enforced implementation path. Updating all modes of the unified installer guarantees parity where config mutation actually occurs, and adjusting compound workflow output folder removes a known mismatch between intended and actual location. Compared to rule-only options, this approach fixes runtime behavior immediately and reduces recurring manual correction.

---

## Acceptance Criteria

- [ ] Running the unified installer (`_config/install-rbtv.py`) in any mode (IDE, admin, sync) rewrites BMAD output-related config values to use `projects/{project-name}/` base pattern.
- [ ] All three installer modes apply identical output-path rewrite logic (no divergence between modes).
- [ ] Compound workflow config routes output to RBTV roadmap todos location rather than generic planning-artifacts path.
- [ ] Existing PRD-location logic referenced in prior backlog work is reused where applicable; no duplicate conflicting behavior introduced.
- [ ] Manual post-install path correction is no longer required for the covered output fields.

---

## Related Files

| File | Relationship |
|------|--------------|
| `_config/install-rbtv.py` | Unified installer (3 modes: IDE, admin, sync); primary implementation point for BMAD config rewrite |
| `workflows/doc-compound-learning/workflow.md` | Contains compound output folder config that must be corrected |
| `_bmad/bmm/config.yaml` | Defines path templates consumed by planning workflows |
| `_config/config.yaml` | RBTV module config context that influences output defaults |

---

## References

- `_admin/roadmap/todos/prd-standardize-main-config-frontmatter.md` (related but out-of-scope for this PR)
- `workflows/doc-compound-learning/workflow.md`
- `_config/install-rbtv.py` (unified installer, 3 modes)

### Supersession

- This compound supersedes the previously overlapping output-location compound (now removed to prevent duplicate scope).

---

## Discussion Notes

### Selected Improvement Option
Change actual implementation (system-file updates), without adding extra rule-only scope at this stage.

### Implementation Preferences
- **File Location:** `_config/install-rbtv.py` (unified installer, all 3 modes), `workflows/doc-compound-learning/workflow.md`
- **Scope:** Moderate (touch only files required for correct output path behavior)
- **Priority:** High

### Additional Context
- Apply installer behavior consistently across all three modes (IDE, admin, sync) of the unified installer.
- Ensure output paths are rewritten to `projects/{project-name}/` in BMAD core config updates.
- Reuse prior PRD-location work context where applicable; no separate PRD-location-only scope needed.
- Keep compound output-location correction in scope (compound outputs remain a valid part of this PR).
