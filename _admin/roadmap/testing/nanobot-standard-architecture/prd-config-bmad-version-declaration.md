---
title: 'Compound: BMAD Version Declaration for RBTV'
docType: 'compound'
mode: 'create'
priority: 'Medium'
tracker: ''
stepsCompleted:
  - step-01-init.md
  - step-02-self-assessment.md
  - step-03-discussion.md
  - step-04-document.md
inputDocuments: []
outputPath: '_admin-output/planning-artifacts'
date: '2026-02-12'
yoloMode: false
---

# BMAD Version Declaration for RBTV

**Type:** System File + Documentation  
**Priority:** Medium  
**Tracker:**  
**Status:** Backlog

---

## Overview

### Problem

RBTV has no explicit declaration of which BMAD version it targets. The BMAD mirror (`_admin/docs/BMAD-mirror/`) is pinned to Beta.4 via `manifest.yaml`, but RBTV never reads or exposes this. RBTV's own version (`1.0.0` in `_config/config.yaml`) exists with no link to BMAD. Two developers currently run different BMAD versions (Beta.4 and Beta.7) with no shared baseline, and Beta.8 is already available. RBTV also lacks its own version tracking discipline — no changelog, no release notes, no mechanism to correlate RBTV changes with BMAD versions.

### Goals

- RBTV declares which BMAD version it was built and tested against (machine-readable + human-readable)
- The BMAD mirror includes metadata stating what it represents
- RBTV has its own version tracking with a changelog
- The RBTV-to-BMAD version relationship is documented and discoverable
- Future tooling (compatibility checks, installers) can consume these declarations

### Constraints

- Must not modify anything under `_admin/docs/BMAD-mirror/` content (read-only BMAD content) — exception: RBTV-owned metadata files about the mirror
- Must not modify BMAD components directly (Admin Restriction #2)
- Must be backward-compatible with existing RBTV tooling (installers, config loading)
- `{project-root}` placeholders must be preserved in all edited files

---

## Self-Assessment

### Error Analysis

**Error type:** Knowledge gap

RBTV was built against BMAD `6.0.0-Beta.4` but this relationship is implicit — inferred only by examining the mirror's `manifest.yaml`. No RBTV-owned file declares the target BMAD version. Two developers run different BMAD versions (Beta.4, Beta.7) with no declared baseline. The risk is real: BMAD Beta.7 introduced workflow file splitting (`workflow.md` → `workflow-*.md`) which could break RBTV's product submenu references to BMAD workflows. Without version tracking, such breakage is discovered accidentally, not systematically.

### Context Source Evaluation

| File | Role | Gap |
|------|------|-----|
| `_config/config.yaml` | RBTV module config — has RBTV version `1.0.0` | No `bmad_target_version` field |
| `_admin/docs/BMAD-mirror/_bmad/_config/manifest.yaml` | BMAD installation manifest — version `6.0.0-Beta.4` | Inside read-only mirror; RBTV never reads this |
| `_config/install-rbtv.py` | Installs RBTV into BMAD project | No version check before installation |
| `_admin/install-admin-rbtv.py` | Sets up standalone dev environment | No version check or mirror version extraction |
| `CLAUDE.md` | Repo identity and boundaries | Mentions BMAD mirror but no version info |
| `agents/ana.md` | Doc orchestrator — product submenu references BMAD workflows | Paths may break if BMAD splits workflow files |

### Improvement Options

1. **New Rule**: Add `bmad-rbtv-version-compat.mdc` instructing agents to check BMAD version before structural modifications
   - **Rationale:** Agents would be version-aware during changes
   - **Location:** `_config/.cursor/rules/bmad-rbtv-version-compat.mdc`

2. **Modify Existing Config**: Add `bmad_target_version` and `bmad_min_version` fields to `_config/config.yaml`
   - **Rationale:** Central, machine-readable declaration; extends existing config pattern
   - **Location:** `_config/config.yaml`

3. **Update System File**: Add `MIRROR-VERSION.md` to mirror folder as RBTV metadata about what the mirror represents
   - **Rationale:** Makes the mirror self-documenting; anyone inspecting it knows what BMAD version it reflects
   - **Location:** `_admin/docs/BMAD-mirror/MIRROR-VERSION.md`

4. **Add Constraint**: Installer pre-flight version check — compare target BMAD's manifest against RBTV's declared version
   - **Rationale:** Prevents silent installation into incompatible BMAD versions
   - **Location:** `_config/install-rbtv.py`

5. **Alternative Approach**: Standalone `bmad-compat.yaml` as comprehensive compatibility manifest with tested versions, breaking changes, migration notes
   - **Rationale:** Single source of truth for version relationships; extensible for companion compatibility-check PRD
   - **Location:** New file at RBTV root

---

## Proposed Solution

**Selected options: 2 + 3, plus RBTV version tracking and changelog.**

### A. Add BMAD version fields to `_config/config.yaml`

Add the following fields to the existing config:

```yaml
# BMAD Compatibility
bmad_target_version: "6.0.0-Beta.8"
bmad_min_version: "6.0.0-Beta.4"
```

- `bmad_target_version` — the exact BMAD version RBTV was built and tested against
- `bmad_min_version` — the oldest BMAD version that is expected to work (best-effort, no guarantee)

### B. Add `MIRROR-VERSION.md` to mirror folder

Create `_admin/docs/BMAD-mirror/MIRROR-VERSION.md`:

```markdown
# BMAD Mirror Version

This folder contains a read-only copy of BMAD for RBTV development reference.

| Field | Value |
|-------|-------|
| BMAD Version | 6.0.0-Beta.8 |
| Mirror Synced | 2026-02-XX |
| Source | https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.0.0-Beta.8 |

**Do not modify files in this folder.** This is RBTV metadata about the mirror, not BMAD content.
```

This file is RBTV-owned metadata (not BMAD content), so it does not violate the read-only boundary.

### C. RBTV Version Tracking

Formalize RBTV's own version in `_config/config.yaml` (already has `version: 1.0.0`) and create a `CHANGELOG.md` at RBTV root:

```markdown
# RBTV Changelog

All notable changes to the RBTV module are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- BMAD version declaration in `_config/config.yaml` (`bmad_target_version`, `bmad_min_version`)
- `MIRROR-VERSION.md` for BMAD mirror metadata
- This changelog

### Changed
- BMAD mirror updated from 6.0.0-Beta.4 to 6.0.0-Beta.8

## [1.0.0] - 2026-02-05

### Added
- Initial RBTV module release
- Agents: ana, domcobb, god, mentor
- Workflows: doc-compound-learning, doc-context-handoff, build-rbtv-component
- Tasks: context-distill, design-validation, git-commit, mermaid-conversion, plan-creation, playwright-browser-automation, quality-review, tone-extraction, update-bmad-config, visual-design-extraction, web-research
- Installer: `_config/install-rbtv.py`
- Admin tooling: `_admin/install-admin-rbtv.py`
```

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | `_config/config.yaml` (add bmad version fields) |
| File(s) to create | `_admin/docs/BMAD-mirror/MIRROR-VERSION.md`, `CHANGELOG.md` |
| Scope of change | Moderate — 1 modified file, 2 new files, mirror update |
| Related files | `_admin/install-admin-rbtv.py` (may read config version), `_config/install-rbtv.py` (future: pre-flight check in PRD 2), `CLAUDE.md` (may mention version tracking) |
| Prerequisite action | Update BMAD mirror from Beta.4 to Beta.8 before declaring Beta.8 as target |

---

## Rationale

The root cause is that RBTV's relationship with BMAD is entirely implicit. The mirror folder acts as an informal version pin, but no metadata declares what version it represents, and RBTV's config has no field linking to BMAD. This means:

1. **Developers drift apart** — Henrique on Beta.4, kenu on Beta.7, with no shared baseline
2. **Breakage is discovered accidentally** — Beta.7's workflow splitting could break RBTV's product submenu, but nothing flags this
3. **No audit trail** — When the mirror is updated, there's no record of what changed or why

Adding explicit version fields to config.yaml (Option 2) makes the declaration machine-readable and consumable by future tooling. Adding MIRROR-VERSION.md (Option 3) makes the mirror self-documenting for human developers. Adding a CHANGELOG creates the audit trail RBTV needs as it matures. Together, these form the foundation for the companion PRD's compatibility checking mechanism.

---

## Acceptance Criteria

- [ ] `_config/config.yaml` contains `bmad_target_version: "6.0.0-Beta.8"` and `bmad_min_version: "6.0.0-Beta.4"` fields
- [ ] `_admin/docs/BMAD-mirror/MIRROR-VERSION.md` exists with BMAD version, sync date, and source URL
- [ ] `CHANGELOG.md` exists at RBTV root following Keep a Changelog format
- [ ] BMAD mirror is updated from Beta.4 to Beta.8 content
- [ ] `MIRROR-VERSION.md` version matches `manifest.yaml` version inside the mirror
- [ ] `bmad_target_version` in config matches `MIRROR-VERSION.md` version
- [ ] Existing RBTV tooling (installers, agents, workflows) continues to function after changes

---

## Related Files

| File | Relationship |
|------|--------------|
| `_config/config.yaml` | Primary target — add BMAD version fields |
| `_admin/docs/BMAD-mirror/_bmad/_config/manifest.yaml` | Source of current BMAD version (read-only) |
| `_admin/docs/BMAD-mirror/` | Folder to receive MIRROR-VERSION.md and Beta.8 content update |
| `_config/install-rbtv.py` | Future consumer of version fields (PRD 2: compatibility check) |
| `_config/install-rbtv.py` (admin mode) | Admin mode may need to read/display version info |
| `agents/ana.md` | References BMAD workflow paths that may change between BMAD versions |
| `CLAUDE.md` | May reference version tracking once implemented |
| `prd-config-bmad-compatibility-check.md` | Companion PRD — consumes the declarations created here |

---

## References

- [BMAD-METHOD Releases](https://github.com/bmad-code-org/BMAD-METHOD/releases?page=1)
- BMAD Beta.8 release (2026-02-09): Non-interactive install, CSV validation, Party Mode Return Protocol, `workflow_path` removal
- BMAD Beta.7 release (2026-02-05): Workflow file splitting (`workflow-*.md`), direct workflow invocation via slash commands
- [Keep a Changelog](https://keepachangelog.com/) — format standard for RBTV changelog

---

## Discussion Notes

### Selected Improvement Option

Option 2 (Add `bmad_target_version` to `_config/config.yaml`) + Option 3 (Add `MIRROR-VERSION.md` to mirror folder) as the foundation, plus RBTV version tracking and changelog.

Options 1, 4, and 5 are deferred to companion PRD (prd-config-bmad-compatibility-check).

### Implementation Preferences

- **File Location:** `_config/config.yaml` (version field), `_admin/docs/BMAD-mirror/MIRROR-VERSION.md` (mirror metadata), `CHANGELOG.md` (root)
- **Scope:** Moderate — config field + mirror metadata + RBTV version tracking + changelog
- **Priority:** Medium

### Additional Context

- **Current state:** Henrique (RBTV creator) runs BMAD Beta.4, kenu runs Beta.7, Beta.8 is latest
- **Decision:** Target Beta.8 as declared version. Mirror must be updated from Beta.4 to Beta.8.
- **Two PRDs confirmed:** This PRD creates the declarations; companion PRD creates the checking mechanism.

### BMAD Changes Relevant to RBTV (Beta.5 → Beta.8)

| Version | Change | RBTV Impact |
|---------|--------|-------------|
| Beta.5 | Fix leaked source paths → `{project-root}/_bmad/core/` | RBTV uses same path pattern — confirms alignment |
| Beta.5 | Fix party-mode workflow file extension | RBTV references party mode via `advancedElicitationTask` |
| Beta.6 | Cross-File Reference Validator (483 refs across 217 files) | RBTV adds to `bmad-help.csv` — could be validated |
| Beta.6 | Centralized `BMAD_FOLDER_NAME` constant | RBTV hardcodes `_bmad` in paths |
| Beta.7 | **Workflow file splitting** (`workflow.md` → `workflow-*.md`) | **Structural change** — RBTV's product submenu points to BMAD workflow files that may have been split |
| Beta.7 | Installer picks up `workflow-*.md` pattern | RBTV installer may need to follow same pattern |
| Beta.8 | **Forbidden variable removal** (`workflow_path` from 16 files) | RBTV already forbids this in component patterns — confirms RBTV was ahead |
| Beta.8 | CSV reference validation | RBTV writes to `bmad-help.csv` — would be caught by this validator |
| Beta.8 | Party Mode Return Protocol | RBTV workflows reference party mode — may need the return protocol |
| Beta.8 | Non-interactive installation CLI flags | RBTV installer could leverage these for CI/CD |

**Highest risk — Beta.7 workflow splitting:** RBTV's `agents/ana.md` product submenu references these BMAD paths:
- `{project-root}/_bmad/bmm/workflows/1-analysis/create-product-brief/workflow.md`
- `{project-root}/_bmad/bmm/workflows/2-plan-workflows/create-prd/workflow.md`
- `{project-root}/_bmad/bmm/workflows/2-plan-workflows/create-ux-design/workflow.md`

If Beta.7 split these into `workflow-create.md` / `workflow-edit.md` / `workflow-validate.md`, those references are broken. This is exactly the kind of breakage version tracking would catch.

**Recommendation:** Target Beta.8. The mirror is stale at Beta.4 with 4 betas of accumulated changes including structural ones. "Working fine" on Beta.4 and Beta.7 likely means the split workflow paths aren't being exercised yet. Update mirror to Beta.8 simultaneously with implementing this PRD.
