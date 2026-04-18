---
title: 'Compound: BMAD Compatibility Check Pipeline for RBTV'
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
  - _admin/roadmap/todos/prd-config-bmad-version-declaration.md
outputPath: '_admin/roadmap/todos'
date: '2026-02-12'
yoloMode: false
---

# BMAD Compatibility Check Pipeline for RBTV

**Type:** System File + Tooling + Workflow  
**Priority:** Medium  
**Tracker:**  
**Status:** Backlog  
**Depends on:** PRD 4 — prd-config-bmad-version-declaration.md (must be implemented first)

---

## Overview

### Problem

When a new BMAD release is published, RBTV has no structured process to evaluate whether to update. Every RBTV→BMAD touchpoint — installer path writes, agent workflow references, `bmad-help.csv` format, config structure — is a potential breakage point that goes unchecked. Compatibility is discovered accidentally (e.g., Beta.7's workflow file splitting could break `agents/ana.md`'s product submenu references, but this was only found during manual analysis, not by any systematic check). The installer (`install-rbtv.py`) blindly writes to BMAD structures without verifying the target BMAD version is compatible.

### Goals

- A `bmad-compat.yaml` manifest at RBTV root lists every RBTV→BMAD dependency (the data: what to check)
- A `tasks/check-bmad-compat.xml` task gives agents a structured process to evaluate new BMAD releases (the process: how to check)
- The installer (`install-rbtv.py`) performs a pre-flight version check before installation (the guardrail: enforce the result)
- Together, these form a full pipeline: data → process → enforcement

### Constraints

- Must not modify anything under `_admin/docs/BMAD-mirror/` content (read-only BMAD content)
- Must not modify BMAD components directly (Admin Restriction #2)
- Depends on PRD 4 (prd-config-bmad-version-declaration) being implemented first — needs `bmad_target_version` in config and `MIRROR-VERSION.md`
- The `bmad-compat.yaml` file must NOT be loaded by agents during normal sessions — it is consumed only by the installer and the compatibility check task
- `{project-root}` placeholders must be preserved in all edited files
- Installer check must warn, not hard-fail — BMAD is in beta, strict enforcement could block legitimate use

---

## Self-Assessment

### Error Analysis

**Error type:** Knowledge gap

RBTV was built against BMAD Beta.4, but BMAD has released Beta.5 through Beta.8 with changes relevant to RBTV (workflow splitting, `workflow_path` removal, CSV validation, Party Mode Return Protocol). None of these were systematically evaluated for RBTV impact. The current process is: someone notices something broke. There is no data file listing what RBTV depends on in BMAD, no task for agents to run a compatibility check, and no installer guardrail to catch version mismatches.

### Context Source Evaluation

| File | Role | Gap |
|------|------|-----|
| `_config/install-rbtv.py` | Writes to BMAD configs, `bmad-help.csv`, copies files | No pre-flight version check; assumes BMAD structure matches |
| `agents/ana.md` | Product submenu references 3 BMAD workflow paths | No validation these paths exist in target BMAD version |
| `workflows/build-rbtv-component/data/admin-restrictions.md` | Requires reading `bmad-help.csv` | No check that CSV format matches expectations |
| `_admin/docs/BMAD-mirror/` | Development reference | No diff mechanism against newer BMAD releases |
| `_config/config.yaml` | Will have `bmad_target_version` after PRD 4 | No list of specific BMAD touchpoints |
| `tasks/` | Contains RBTV task files | No compatibility check task exists |

### Improvement Options

1. **New Rule**: `bmad-rbtv-version-compat.mdc` — agents verify BMAD path references before structural changes
   - **Rationale:** Runtime awareness for agents
   - **Location:** `_config/.cursor/rules/`

2. **Modify Existing Config**: Add `bmad_touchpoints` array to `_config/config.yaml`
   - **Rationale:** Machine-readable dependency list
   - **Location:** `_config/config.yaml`

3. **Update System File**: Create `tasks/check-bmad-compat.xml` — structured agent task for evaluating BMAD releases
   - **Rationale:** Reusable process for every BMAD release evaluation
   - **Location:** `tasks/check-bmad-compat.xml`

4. **Add Constraint**: Installer pre-flight version check in `install-rbtv.py`
   - **Rationale:** Prevents silent installation into incompatible BMAD versions
   - **Location:** `_config/install-rbtv.py`

5. **Alternative Approach**: Standalone `bmad-compat.yaml` at RBTV root mapping all RBTV→BMAD dependencies
   - **Rationale:** Separates compatibility data from runtime config; consumed only at install/check time
   - **Location:** RBTV root: `bmad-compat.yaml`

---

## Proposed Solution

**Selected options: 5 (separate compat file) + 3 (task) + 4 (installer check) — full pipeline.**

### A. Create `bmad-compat.yaml` at RBTV root (Data Layer)

This file lists every RBTV→BMAD dependency. It is NOT loaded by agents during normal sessions — consumed only by the installer and the compatibility check task.

```yaml
# RBTV → BMAD Compatibility Manifest
# Consumed by: install-rbtv.py (pre-flight check), tasks/check-bmad-compat.xml
# NOT loaded during normal agent sessions

bmad_target_version: "6.0.0-Beta.8"
bmad_min_version: "6.0.0-Beta.4"

# Paths RBTV references in BMAD (relative to {project-root})
touchpoints:
  installer_writes:
    - path: "core/config.yaml"
      type: "modify"
      description: "Updates output_folder field"
    - path: "bmm/config.yaml"
      type: "modify"
      description: "Updates output paths"
    - path: "_config/bmad-help.csv"
      type: "modify"
      description: "Adds RBTV entry row"
    - path: ".cursor/mcp.json"
      type: "merge"
      description: "Merges RBTV MCP server config"

  agent_references:
    - path: "bmm/workflows/1-analysis/create-product-brief/workflow.md"
      source: "agents/ana.md"
      description: "Product brief workflow (submenu item)"
    - path: "bmm/workflows/2-plan-workflows/create-prd/workflow.md"
      source: "agents/ana.md"
      description: "PRD workflow (submenu item)"
    - path: "bmm/workflows/2-plan-workflows/create-ux-design/workflow.md"
      source: "agents/ana.md"
      description: "UX design workflow (submenu item)"

  task_references:
    - path: "core/workflows/advanced-elicitation/workflow.xml"
      source: "workflows/doc-compound-learning/workflow.md"
      description: "Advanced elicitation party mode"

  structure_assumptions:
    - item: "bmad-help.csv format"
      description: "CSV with module, name, description columns"
    - item: "_config/manifest.yaml"
      description: "BMAD installation manifest with version field"
    - item: "core/config.yaml structure"
      description: "YAML with output_folder field"
```

### B. Create `tasks/check-bmad-compat.xml` (Process Layer)

An agent task that evaluates a new BMAD release against RBTV's touchpoints.

**Task flow:**
1. Read `bmad-compat.yaml` to get current touchpoints and target version
2. Accept input: new BMAD version to evaluate (user provides release URL or version number)
3. For each touchpoint, check if the path/structure still exists in the new BMAD version:
   - If BMAD mirror is already updated → check file existence directly
   - If evaluating before mirror update → read BMAD release notes + GitHub for changes
4. For each `structure_assumption`, verify format compatibility
5. Produce a compatibility report:
   - **Compatible:** All touchpoints verified, safe to update
   - **Breaking changes found:** List specific touchpoints that need RBTV adaptation
   - **Unknown:** Could not verify (manual check needed)
6. Recommend action: update target version, update mirror, or defer with documented reasons

**Output:** Compatibility report saved to `_admin-output/planning-artifacts/bmad-compat-report-{version}.md`

### C. Installer Pre-Flight Check (Enforcement Layer)

Modify `_config/install-rbtv.py` to add a version check before installation:

**Pre-flight flow:**
1. Read `bmad-compat.yaml` from RBTV root
2. Read target BMAD project's `_config/manifest.yaml`
3. Extract BMAD installation version
4. Compare against `bmad_target_version` and `bmad_min_version`
5. Decision logic:
   - Version matches `bmad_target_version` → proceed silently
   - Version >= `bmad_min_version` but != `bmad_target_version` → warn, proceed
   - Version < `bmad_min_version` → warn strongly, ask for confirmation to proceed
   - `manifest.yaml` not found → warn (BMAD may not be installed), ask for confirmation
6. All warnings are non-blocking (beta software constraint) — user can override with `--skip-version-check` flag

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to create | `bmad-compat.yaml` (RBTV root), `tasks/check-bmad-compat.xml`, `tasks/data/bmad-compat-report-template.md` |
| File(s) to modify | `_config/install-rbtv.py` (add pre-flight function) |
| Scope of change | Moderate — 3 new files, 1 modified file |
| Related files | `_config/config.yaml` (reads `bmad_target_version` from PRD 4), `agents/ana.md` (touchpoint source), `_admin/docs/BMAD-mirror/MIRROR-VERSION.md` (from PRD 4) |
| Prerequisite | PRD 4 (prd-config-bmad-version-declaration) must be implemented first |

---

## Rationale

The root cause is that RBTV's dependencies on BMAD are undocumented and unchecked. The three-layer approach addresses this systematically:

1. **Data layer** (`bmad-compat.yaml`) — makes implicit dependencies explicit. Every path, format, and structure RBTV assumes about BMAD is listed in one file. When RBTV adds a new BMAD reference, it gets added here too.

2. **Process layer** (`tasks/check-bmad-compat.xml`) — provides a repeatable evaluation process. When BMAD publishes Beta.9, an agent runs this task and produces a report before anyone updates. No more accidental discovery.

3. **Enforcement layer** (installer pre-flight) — catches version mismatches at install time. Even if the evaluation process is skipped, the installer warns before writing to an incompatible BMAD project.

The separate `bmad-compat.yaml` file (instead of embedding in `config.yaml`) keeps compatibility data out of agent context during normal sessions. Agents don't need to know about BMAD touchpoints when writing documentation or running workflows — they only need it during explicit compatibility checks or installation. This respects the principle that `config.yaml` is loaded on every agent session and should stay lean.

---

## Acceptance Criteria

- [ ] `bmad-compat.yaml` exists at RBTV root with all current RBTV→BMAD touchpoints listed
- [ ] `bmad-compat.yaml` is NOT referenced in any agent, rule, or workflow file loaded during normal sessions
- [ ] `tasks/check-bmad-compat.xml` exists and follows RBTV task file conventions (XML with `<task>` root, `<objective>`, `<llm>`, `<flow>`)
- [ ] Running the compatibility check task against the current BMAD mirror produces a "Compatible" report
- [ ] `_config/install-rbtv.py` reads `bmad-compat.yaml` and performs version comparison before installation
- [ ] Installer warns (does not abort) when BMAD version < `bmad_min_version`
- [ ] Installer proceeds silently when BMAD version matches `bmad_target_version`
- [ ] Installer supports `--skip-version-check` flag to bypass the check
- [ ] All touchpoint paths in `bmad-compat.yaml` are verified to exist in the current BMAD mirror
- [ ] Compatibility report template exists at `tasks/data/bmad-compat-report-template.md`

---

## Related Files

| File | Relationship |
|------|--------------|
| `prd-config-bmad-version-declaration.md` | Prerequisite PRD — creates version fields and mirror metadata this PRD consumes |
| `_config/config.yaml` | Source of `bmad_target_version` (from PRD 4) |
| `_config/install-rbtv.py` | Modified — add pre-flight version check |
| `agents/ana.md` | Touchpoint source — product submenu BMAD workflow references |
| `workflows/doc-compound-learning/workflow.md` | Touchpoint source — advanced elicitation reference |
| `workflows/build-rbtv-component/data/admin-restrictions.md` | Touchpoint source — `bmad-help.csv` dependency |
| `_admin/docs/BMAD-mirror/_config/manifest.yaml` | Version source for mirror comparisons |
| `_admin/docs/BMAD-mirror/MIRROR-VERSION.md` | From PRD 4 — mirror version metadata |
| `tasks/` | Location for new compatibility check task |

---

## References

- [BMAD-METHOD Releases](https://github.com/bmad-code-org/BMAD-METHOD/releases?page=1)
- Companion PRD: `prd-config-bmad-version-declaration.md` (version declaration foundation)
- BMAD Beta.7: Workflow file splitting (`workflow.md` → `workflow-*.md`) — concrete example of breaking change
- BMAD Beta.8: `workflow_path` removal, CSV reference validation, Party Mode Return Protocol
- RBTV component patterns rule: already forbids `workflow_path` (ahead of BMAD Beta.8)

---

## Discussion Notes

### Selected Improvement Option

Full pipeline: Option 5 (separate `bmad-compat.yaml`) + Option 3 (task file) + Option 4 (installer check).

Options 1 (agent rule) and 2 (touchpoints in config.yaml) not selected.

### Implementation Preferences

- **File Location:** `bmad-compat.yaml` at RBTV root (separate from config.yaml), `tasks/check-bmad-compat.xml`, modify `_config/install-rbtv.py`
- **Scope:** Moderate — 3 new files, 1 modified file
- **Priority:** Medium

### Additional Context

- User explicitly chose separate file over config.yaml: "config.yaml is loaded on every agent" — compatibility data should not bloat agent context
- Installer check must warn, not hard-fail — BMAD is in beta, strict enforcement would be premature
- This PRD depends on PRD 4 being implemented first (needs version fields and mirror metadata)
- The touchpoints list must be maintained as RBTV evolves — when new BMAD references are added, `bmad-compat.yaml` must be updated
