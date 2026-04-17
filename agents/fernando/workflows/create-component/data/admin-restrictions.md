# Admin Restrictions

> **EXECUTION:** Agents must read this file only. NEVER read `CLAUDE.md` to execute these restrictions.

> **EDITING:** When editing this file, update the "Admin Restrictions" section in `CLAUDE.md` to match.

## Hard Restrictions

### 1. BMAD Component Map Check

Before any component creation or structural modification, read `_admin/docs/BMAD-mirror/_bmad/_config/bmad-help.csv`. This manifest lists every BMAD capability with module, name, and description. Evaluate whether the request can be delegated totally or partially to an existing BMAD component.

### 2. Never Touch BMAD

BMAD is maintained by a separate group unaware of RBTV. NEVER modify BMAD components directly. In a BMAD instance, touch BMAD files only when absolutely unavoidable — and when done, automate the change (via installer or script) so it survives BMAD updates without manual intervention.

### 3. Leverage BMAD

Use all BMAD components (not just entry points) to make RBTV and business innovation modules more powerful. RBTV integrates TO BMAD; integrating BMAD to RBTV is out of scope.

### 4. Prefer Native BMAD

ALWAYS use an existing BMAD component instead of creating a new RBTV one, if it fulfills the requirements of what is being requested.

### 5. Minimal Internalization

Internalize from BMAD to RBTV only what is strictly necessary for correct functioning. Prefer referencing over copying.

### 6. Discrepancy Documentation

If structural differences between BMAD and RBTV are discovered during work, document them in `_admin/docs/bmad-discrepancies/`, in the for of a PRD to fix the discrepancy, adapting rbtv to BMAD standards and highlighting what is unique to BMAD and what is unique to RBTV. Do not document the discrepancies if they are documented in existing PRDs in this folder (place a YAML header in the PRDs with a description that will allow you and other AI Agents to identify that later on)