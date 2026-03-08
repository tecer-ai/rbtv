---
type: prd
status: ready
created: 2026-02-23
updated: 2026-03-08
target_bmad_version: "6.0.4"
from_bmad_version: "6.0.0-Beta.4"
---

# PRD: BMAD Upgrade from 6.0.0-Beta.4 to v6.0.4

## Summary

Upgrade the RBTV BMAD installation from 6.0.0-Beta.4 to v6.0.4 (stable release) without breaking any RBTV integration. This PRD covers every change needed in RBTV and its installer scripts so Henri can perform the upgrade confidently.

**Stable release significance:** v6.0.0 ended the beta cycle. This upgrade moves RBTV from beta to the first stable release series, gaining all Beta.5 through v6.0.4 improvements.

---

## Scope

This PRD is the comprehensive inventory of ALL changes needed for full RBTV compatibility with BMAD v6.0.4. The plan built from this PRD will decide implementation priority and phasing.

**Excluded from this PRD:**

| Excluded Item | Reason |
|---------------|--------|
| `_mobile/` files | Henri will update manually |
| RBTV workflow structural conversion (monolithic → split `workflow-*.md`) | Separate concern — will be handled when RBTV becomes an official BMAD module via BMB |

---

## Changes Summary

| # | Change | Description | Reason | Cmplx | Crit |
|---|--------|-------------|--------|:-----:|:----:|
| 1 | Output folder name preservation | Installer hardcodes `_bmad-output` in regex replacements. Must read existing `output_folder` value and preserve the user-chosen folder name (e.g. `projects`) while still injecting `/{project-name}`. Affects `normalize_bmad_output_paths()`, `_config/config.yaml` path vars, and `.cursorignore` pattern | v6.0.4 instance uses `projects` not `_bmad-output`; installer would overwrite the user's choice on every run | 4 | 10 |
| 2 | BMM workflow path refs in ana.md | Verify three BMM workflow paths in `agents/ana.md` against v6.0.4. Beta.7 split monolithic `workflow.md` into `workflow-*.md`; if any of the three referenced paths no longer exist, the agent fails to load | Beta.7 workflow splitting likely renamed files RBTV references directly | 3 | 9 |
| 3 | Advanced elicitation path | `workflows/doc-compound-learning/workflow.md` references `workflow.xml`. Beta.7 converted `.xml` → `.md` and split files. Verify path in v6.0.4 and update reference | Format and path almost certainly changed; compound learning workflow would break | 3 | 8 |
| 4 | bmad-help.csv schema | Installer's `add_rbtv_to_help_catalog()` writes a 16-column row. Beta.8 enhanced bmad-help. Compare v6.0.4 header against expected columns; update if schema changed | Malformed CSV row would break bmad-help command display | 3 | 7 |
| 5 | bmm/config.yaml field names | Installer's `normalize_bmad_output_paths()` expects `output_folder`, `planning_artifacts`, `implementation_artifacts`. Verify fields still exist in v6.0.4 with same names | If fields renamed, installer silently fails to patch output paths | 2 | 7 |
| 6 | Mirror update | Replace `_admin/docs/BMAD-mirror/` with v6.0.4 content from `_admin/docs/BMAD-v6.0.4/`. Update `MIRROR-VERSION.md` with new versions | Admin mode path resolution uses mirror; stale mirror = broken cross-module refs | 2 | 7 |
| 7 | Version declarations | Update `bmad_target_version` to `6.0.4` in `_config/config.yaml` and `bmad-compat.yaml` | Version check would warn/fail on install | 1 | 6 |
| 8 | TEA references check | Search RBTV for `_bmad/tea/` refs. TEA jumped 0.1.1 → 1.5.2; internal structure likely changed. Only actionable if RBTV actually references TEA | Only breaks if RBTV has TEA path refs (unlikely but must verify) | 2 | 5 |
| 9 | manifest.yaml format | Verify `installation.version` field exists in v6.0.4 manifest. Update `check_bmad_version()` if format changed | Version pre-flight check would fail | 1 | 4 |
| 10 | bmad-compat.yaml update | Update all documented touchpoints, paths, and version refs in `bmad-compat.yaml` to reflect v6.0.4 reality | Compatibility check task relies on accurate compat metadata | 2 | 6 |
| 11 | Output folder in workflow/task files | 54 workflow files + 2 task files use literal `_bmad-output` (80+ occurrences, zero use of `{bmad_output}` variable). Must be updated to match the configured output folder or use a path variable | Workflows reference wrong output directory when BMAD is configured with a different folder name (e.g. `projects`) | 5 | 3 |
| 12 | build-rbtv-component architecture doc | `workflows/build-rbtv-component/data/bmad-architecture.md` documents BMAD architecture based on Beta.4 patterns. Must be updated to reflect v6.0.4 structure (e.g., updated frontmatter standards, new module versions) | Stale architecture doc causes new RBTV components to be built with outdated BMAD patterns | 4 | 3 |
| 13 | RBTV readme.md | `readme.md` references `_bmad-output`. Verify and update all path references to match v6.0.4 conventions | Documentation accuracy for developers reading the repo | 1 | 2 |
| 14 | CLAUDE.md path variables | `CLAUDE.md` path resolution table shows `{bmad_output}` → `{project-root}/_bmad-output`. Must match actual configured output folder | Claude Code uses wrong path variable values in admin mode | 2 | 5 |

---

## Execution Context

Claude Code executes this upgrade from the **RBTV repo root** (`_bmad/rbtv/`), NOT from the parent BMAD project root. Two reference directories provide the comparison basis:

| Directory | Contents | Purpose |
|-----------|----------|---------|
| `_admin/docs/BMAD-mirror/` | Read-only copy of BMAD v6.0.0-Beta.4 | **Current state** — what RBTV was built against |
| `_admin/docs/BMAD-v6.0.4/` | Full BMAD v6.0.4 installation | **Target state** — what RBTV must work with after upgrade |

**Upgrade approach:** Diff the mirror (current) against BMAD-v6.0.4 (target) to identify structural changes. Then update RBTV files so they work with the v6.0.4 structure. After RBTV is updated, replace the mirror contents with v6.0.4 to reflect the new baseline.

**Companion file:** `bmad_compare_6.0.0-Beta.4_to_v6.0.4_commits.csv` (same directory as this PRD) contains all 147 commits between the two versions. Use as a lookup resource when investigating specific touchpoints — search for keywords like `config`, `path`, `output`, `workflow`, `manifest` to trace granular changes the release notes summarize.

---

## BMAD Release History Since Beta.4

| Version | Date | Key Changes |
|---------|------|-------------|
| Beta.5 | 2026-02-01 | generate-project-context workflow; sharded market research |
| Beta.6 | 2026-02-04 | Cross-file reference validator; path standardization to `{project-root}/_bmad/`; removed Excalidraw workflows |
| Beta.7 | 2026-02-04 | **Workflow file splitting** — monolithic `workflow.md` → `workflow-*.md`; direct slash command invocation |
| Beta.8 | 2026-02-09 | 10 new CLI flags; CSV validation; Kiro IDE support; removed `workflow_path` variable |
| v6.0.0 | 2026-02-17 | **Stable release**; PRD workflow steps 2b-2c; `bmad uninstall` command; removed alias variables |
| v6.0.2 | 2026-02-23 | CodeBuddy support; LLM audit prompt; 104 path fixes; workflow naming standardization |
| v6.0.3 | 2026-02-23 | Root cause analysis skill; installer nesting guard; OpenCode fixes; CSV manifest double-escaping fix; workflow description standardization; rebranded to "Build More Architect Dreams" |
| v6.0.4 | 2026-03-01 | Edge case hunter review task; brainstorming session persistence fix; legacy `@` path prefixes → `{project-root}`; broken docs domain fixes. Modules: bmb 0.1.6, cis 0.1.8, tea 1.5.2 |

---

## RBTV→BMAD Touchpoints at Risk

These are the integration points in `bmad-compat.yaml` that may break during upgrade.

### 1. Workflow Path References in `agents/ana.md` — HIGH RISK

**What RBTV does:** `agents/ana.md` directly references three BMM module workflow files:

```
_bmad/bmm/workflows/1-analysis/create-product-brief/workflow.md
_bmad/bmm/workflows/2-plan-workflows/create-prd/workflow.md
_bmad/bmm/workflows/2-plan-workflows/create-ux-design/workflow.md
```

**What BMAD changed (Beta.7):** Monolithic `workflow.md` files were split into `workflow-*.md` files (e.g., `workflow-step-1.md`, `workflow-step-2a.md`). New slash commands (`/create-prd`, `/edit-prd`) replaced direct workflow invocation.

**Risk:** If any of the three BMM workflows referenced in `ana.md` were split in Beta.7, the paths no longer exist. The agent would fail to load the workflow.

**Required action before upgrading:**
1. Check each of the three paths in `_admin/docs/BMAD-v6.0.4/`:
   - `_bmad/bmm/workflows/1-analysis/create-product-brief/workflow.md` — does `workflow.md` still exist or was it renamed?
   - `_bmad/bmm/workflows/2-plan-workflows/create-prd/workflow.md` — same check
   - `_bmad/bmm/workflows/2-plan-workflows/create-ux-design/workflow.md` — same check
2. Compare against the same paths in `_admin/docs/BMAD-mirror/` to identify structural changes
3. If any are renamed/split:
   - Update `agents/ana.md` to use the new path(s)
   - Update `bmad-compat.yaml` agent_references entries

---

### 2. Advanced Elicitation Task Path — HIGH RISK

**What RBTV does:** `workflows/doc-compound-learning/workflow.md` references:

```
_bmad/core/workflows/advanced-elicitation/workflow.xml
```

**What BMAD changed:** Beta.7 converted workflows from `.xml` to `.md` format (slash command invocation) and split monolithic files. Beta.6 standardized path references across the codebase.

**Risk:** The `workflow.xml` file may have been renamed to `workflow.md` or split into `workflow-*.md`. The path and format may both be different.

**Required action before upgrading:**
1. Check `_admin/docs/BMAD-v6.0.4/_bmad/core/workflows/advanced-elicitation/`
2. If `workflow.xml` → `workflow.md`: update the reference in `workflows/doc-compound-learning/workflow.md`
3. If the file was removed or significantly restructured: reassess how compound learning uses advanced elicitation
4. Update `bmad-compat.yaml` task_references entry with the new path

---

### 3. `bmad-help.csv` Column Schema — MEDIUM RISK

**What RBTV does:** The installer's `add_rbtv_to_help_catalog()` function appends a row to `_bmad/_config/bmad-help.csv` with these columns:

```
module, phase, name, code, sequence, workflow-file, command, required,
agent-name, agent-command, agent-display-name, agent-title,
options, description, output-location, outputs
```

**What BMAD changed (Beta.8):** `bmad-help` was enhanced to read project-specific documentation and respect `communication_language`. This may have involved column additions.

**Risk:** If new columns were added or existing columns renamed, RBTV's installer writes a malformed row, which could cause the bmad-help command to fail or display incorrectly.

**Required action before upgrading:**
1. Inspect `_admin/docs/BMAD-v6.0.4/_bmad/_config/bmad-help.csv`
2. Compare columns to the 16 columns RBTV expects (listed above)
3. If columns changed:
   - Update `add_rbtv_to_help_catalog()` in `_config/install-rbtv.py` to match new schema
   - Update the `format_assumption` in `bmad-compat.yaml`

---

### 4. `_bmad/bmm/config.yaml` Field Names — MEDIUM RISK

**What RBTV does:** The installer's `normalize_bmad_output_paths()` function reads and rewrites three fields in `_bmad/bmm/config.yaml`:
- `output_folder`
- `planning_artifacts`
- `implementation_artifacts`

**What BMAD changed (v6.0.0):** "Remove alias variables from Phase 4 workflows, use canonical `{implementation_artifacts}` and `{planning_artifacts}`." This suggests these field names are canonical, but the alias variables that previously mapped to them were removed.

**Risk:** If the field names in `bmm/config.yaml` changed (e.g., renamed), the installer would either fail to find the fields (leaving old values) or create incorrect new fields.

**Required action before upgrading:**
1. Inspect `_admin/docs/BMAD-v6.0.4/_bmad/bmm/config.yaml`
2. Verify the fields `output_folder`, `planning_artifacts`, `implementation_artifacts` still exist with the same names
3. If renamed: update `normalize_bmad_output_paths()` in `_config/install-rbtv.py`

---

### 5. `_bmad/_config/manifest.yaml` Format — LOW RISK

**What RBTV does:** The installer's pre-flight version check reads `_bmad/_config/manifest.yaml` and expects an `installation.version` field.

**What BMAD changed:** No documented change to manifest format between Beta.4 and v6.0.4, but it should be verified.

**Required action before upgrading:**
1. Inspect `_admin/docs/BMAD-v6.0.4/_bmad/_config/manifest.yaml`
2. Verify `installation.version` field exists
3. Verify the version format is still semver (e.g., `6.0.4`)
4. If format changed: update `check_bmad_version()` in `_config/install-rbtv.py`

---

### 6. `_bmad/` Directory Structure — LOW RISK

**What RBTV does:** The installer assumes these directories exist:
- `_bmad/_config/`
- `_bmad/core/`
- `_bmad/bmm/`

**What BMAD changed:** No core structural changes to `_bmad/core/` or `_bmad/bmm/`. The `_bmad/` naming convention (vs the earlier `.bmad/` hidden folder) was already established by Beta.4. SDET module was added in Beta.3 (but RBTV doesn't reference it).

**Required action before upgrading:**
1. Verify `_bmad/core/` and `_bmad/bmm/` still exist in `_admin/docs/BMAD-v6.0.4/`
2. Verify no new required modules that RBTV should reference

---

### 7. TEA Module Dependency — MEDIUM RISK

**What RBTV does:** The BMAD mirror at `_admin/docs/BMAD-mirror/` includes the TEA module at version `0.1.1-beta.3`. RBTV's `bmad-compat.yaml` does not explicitly reference TEA paths, but it should be verified that no RBTV workflows or agents accidentally reference TEA tasks.

**What BMAD changed:** TEA jumped from `0.1.1-beta.3` to `1.5.2` — a major version leap. TEA is included in v6.0.4 as an external module (installed via npm). Internal paths, workflow structure, and task interfaces may have changed substantially.

**Required action before upgrading:**
1. Search RBTV codebase for any references to `_bmad/tea/`:
   ```bash
   grep -r "_bmad/tea" agents/ workflows/ tasks/ --include="*.md" --include="*.xml"
   ```
2. If references are found: compare the referenced paths between `_admin/docs/BMAD-mirror/_bmad/tea/` and `_admin/docs/BMAD-v6.0.4/_bmad/tea/` — the major version jump (0.1.1 → 1.5.2) likely changed internal structure
3. If no references found: no action needed — TEA is not an RBTV dependency
4. Update `MIRROR-VERSION.md` to reflect the new TEA version (1.5.2)

---

### 8. Output Folder Name Preservation — CRITICAL

**What RBTV does:** The installer's `normalize_bmad_output_paths()` function rewrites `output_folder`, `planning_artifacts`, and `implementation_artifacts` in `core/config.yaml` and `bmm/config.yaml` to inject `/{project-name}` for multi-project support. It hardcodes `_bmad-output` as the folder name in the replacement strings:

```python
'output_folder: "{project-root}/_bmad-output/{project-name}"'
'planning_artifacts: "{project-root}/_bmad-output/{project-name}/planning-artifacts"'
'implementation_artifacts: "{project-root}/_bmad-output/{project-name}/implementation-artifacts"'
```

Additionally, `_config/config.yaml` hardcodes `_bmad-output` in its own path variables:

```yaml
output_folder: "{project-root}/_bmad-output"
paths:
  bmad_output: "{project-root}/_bmad-output"
```

And the installer's `.cursorignore` pattern hardcodes `_bmad-output/archive/`.

**What changed:** BMAD lets users choose the output folder name during installation. The v6.0.4 instance uses `projects` instead of `_bmad-output`:

```yaml
# v6.0.4 core/config.yaml
output_folder: "{project-root}/projects"

# v6.0.4 bmm/config.yaml
output_folder: "{project-root}/projects"
planning_artifacts: "{project-root}/projects/planning-artifacts"
implementation_artifacts: "{project-root}/projects/implementation-artifacts"
```

**Risk:** The installer overwrites the user-chosen folder name (`projects`) with the hardcoded `_bmad-output` on every run. Outputs would go to the wrong directory. This is the highest-criticality change.

**Required action:**
1. Refactor `normalize_bmad_output_paths()` to read the existing `output_folder` value, extract the folder name from it, and preserve it while injecting `/{project-name}`. The function must not hardcode any folder name.
2. Update `_config/config.yaml` — change `output_folder` and `paths.bmad_output` to not hardcode `_bmad-output`. Either read from BMAD config at install time, or use a variable.
3. Update the `.cursorignore` pattern in the installer to use the correct folder name.
4. Update `bmad-compat.yaml` to document that the output folder name is user-configurable.

---

## Upgrade Procedure

### Step 1 — Inspect BMAD v6.0.4 and compare against mirror

BMAD v6.0.4 is at `_admin/docs/BMAD-v6.0.4/`. The current baseline (what RBTV was built against) is at `_admin/docs/BMAD-mirror/` (v6.0.0-Beta.4).

Inspect the v6.0.4 directory and compare against the mirror before touching anything:

```bash
# Check workflow paths that RBTV references (in v6.0.4)
ls _admin/docs/BMAD-v6.0.4/_bmad/bmm/workflows/1-analysis/create-product-brief/
ls _admin/docs/BMAD-v6.0.4/_bmad/bmm/workflows/2-plan-workflows/create-prd/
ls _admin/docs/BMAD-v6.0.4/_bmad/bmm/workflows/2-plan-workflows/create-ux-design/
ls _admin/docs/BMAD-v6.0.4/_bmad/core/workflows/advanced-elicitation/

# Compare against mirror (current baseline)
ls _admin/docs/BMAD-mirror/_bmad/bmm/workflows/1-analysis/create-product-brief/
ls _admin/docs/BMAD-mirror/_bmad/bmm/workflows/2-plan-workflows/create-prd/
ls _admin/docs/BMAD-mirror/_bmad/bmm/workflows/2-plan-workflows/create-ux-design/
ls _admin/docs/BMAD-mirror/_bmad/core/workflows/advanced-elicitation/

# Check config file field names (v6.0.4)
grep -E "output_folder|planning_artifacts|implementation_artifacts" _admin/docs/BMAD-v6.0.4/_bmad/bmm/config.yaml
grep "output_folder" _admin/docs/BMAD-v6.0.4/_bmad/core/config.yaml

# Check manifest format (v6.0.4)
cat _admin/docs/BMAD-v6.0.4/_bmad/_config/manifest.yaml

# Check output folder name (v6.0.4 vs mirror)
grep "output_folder" _admin/docs/BMAD-v6.0.4/_bmad/core/config.yaml
grep "output_folder" _admin/docs/BMAD-mirror/_bmad/core/config.yaml

# Check bmad-help.csv header (v6.0.4 vs mirror)
head -1 _admin/docs/BMAD-v6.0.4/_bmad/_config/bmad-help.csv
head -1 _admin/docs/BMAD-mirror/_bmad/_config/bmad-help.csv
```

### Step 2 — Fix RBTV before upgrading

Based on inspection findings, update RBTV files:

| If found | Then update |
|----------|-------------|
| Output folder name differs from `_bmad-output` | `_config/install-rbtv.py::normalize_bmad_output_paths` (refactor regex), `_config/config.yaml` (path vars), `.cursorignore` pattern, `bmad-compat.yaml` |
| BMM workflow paths changed | `agents/ana.md`, `bmad-compat.yaml` |
| `advanced-elicitation/workflow.xml` path changed | `workflows/doc-compound-learning/workflow.md`, `bmad-compat.yaml` |
| `bmad-help.csv` columns changed | `_config/install-rbtv.py::add_rbtv_to_help_catalog`, `bmad-compat.yaml` |
| `bmm/config.yaml` field names changed | `_config/install-rbtv.py::normalize_bmad_output_paths`, `bmad-compat.yaml` |
| `manifest.yaml` format changed | `_config/install-rbtv.py::check_bmad_version` |

### Step 3 — Update RBTV version declarations

After fixing any breaking changes:

**`_config/config.yaml`:**
```yaml
bmad_target_version: "6.0.4"
bmad_min_version: "6.0.0"   # Accept any stable 6.0.x
```

**`bmad-compat.yaml`:**
```yaml
bmad_target_version: "6.0.4"
bmad_min_version: "6.0.0"
```

### Step 4 — Update the BMAD mirror

Replace `_admin/docs/BMAD-mirror/` contents with v6.0.4 files from `_admin/docs/BMAD-v6.0.4/`:

```bash
# Preserve RBTV-owned metadata before replacing
cp _admin/docs/BMAD-mirror/MIRROR-VERSION.md /tmp/mirror-version-backup.md
cp -r _admin/docs/BMAD-mirror/_bmad/rbtv /tmp/rbtv-slot-backup

# Replace mirror contents with v6.0.4
rm -rf _admin/docs/BMAD-mirror/*
cp -r _admin/docs/BMAD-v6.0.4/* _admin/docs/BMAD-mirror/

# Restore RBTV-owned files
cp /tmp/mirror-version-backup.md _admin/docs/BMAD-mirror/MIRROR-VERSION.md
mkdir -p _admin/docs/BMAD-mirror/_bmad/rbtv
# (slot should remain empty — restore any RBTV-owned items only)
```

Update `_admin/docs/BMAD-mirror/MIRROR-VERSION.md`:
```markdown
| BMAD Version | 6.0.4 |
| Mirror Synced | 2026-03-08 |
| Source | https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.0.4 |
```

Update module versions table:
```markdown
| Module | Version |
|--------|---------|
| core   | 6.0.4   |
| bmm    | 6.0.4   |
| bmb    | 0.1.6   |
| cis    | 0.1.8   |
| tea    | 1.5.2   |
```

### Step 5 — Run compatibility check

Use the check-bmad-compat task to validate all touchpoints:

```
# As an agent, run the compatibility check task
task: check-bmad-compat.xml
input: target_version=6.0.4
```

This will produce a report at `_admin-output/planning-artifacts/bmad-compat-report-6.0.4.md`.

### Post-upgrade Steps (after RBTV changes are applied)

- **VPS upgrade** — Run BMAD installer on VPS, re-run `install-rbtv.py --mode sync`, restart nanobot-gateway
- **VPS smoke test** — Run `_mobile/_docs/smoke-checklist.md`

---

## What RBTV Does NOT Need to Change

These BMAD changes do not affect RBTV:

| BMAD Change | Why RBTV is Unaffected |
|------------|------------------------|
| 10 new CLI installer flags (Beta.8) | RBTV uses its own unified installer, not BMAD's CLI |
| Kiro IDE support (Beta.8) | RBTV does not integrate with Kiro |
| CodeBuddy support (v6.0.2+) | RBTV does not integrate with CodeBuddy |
| OpenCode template consolidation (Beta.8) | RBTV does not use OpenCode |
| GitHub Copilot installer (v6.0.0) | RBTV does not integrate with Copilot |
| `disable-model-invocation` flag removed (Beta.8) | RBTV installer does not use this flag |
| Codex installer migrated to `.agents/skills` (v6.0.2+) | RBTV does not use Codex |
| Excalidraw workflows removed (Beta.6) | RBTV does not use Excalidraw |
| PRD workflow steps 2b-2c added (v6.0.0) | RBTV business innovation uses its own PRD workflow |
| `bmad uninstall` command (v6.0.0) | RBTV install/uninstall is via its own installer |

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Output folder name overwritten | Critical | Certain | Installer hardcodes `_bmad-output`; v6.0.4 uses `projects`. Must refactor regex. |
| BMM workflow paths broken | High | Medium | Verify paths before upgrade (Step 1) |
| advanced-elicitation path broken | High | High | Beta.7 changed .xml → .md format and split files |
| bmad-help.csv schema mismatch | Medium | Low | Verify header before upgrade |
| bmm/config.yaml field rename | Medium | Low | Verify fields before upgrade |
| TEA major version jump (0.1.1 → 1.5.2) | Medium | Medium | Search RBTV for `_bmad/tea/` refs; compare TEA paths between mirror and v6.0.4 |
| manifest.yaml format change | Low | Low | Verify field before upgrade |

**Most likely breaking changes:**
1. Output folder name — installer will overwrite `projects` with `_bmad-output` on every run. Certain to break.
2. `advanced-elicitation/workflow.xml` path — BMAD converted from XML to Markdown format in Beta.7, this almost certainly changed
3. BMM workflow paths — Beta.7 split monolithic files; referenced paths may no longer exist

---

## Success Criteria

- [ ] All 8 RBTV→BMAD touchpoint categories verified against v6.0.4 structure
- [ ] Installer preserves user-chosen output folder name (does not hardcode `_bmad-output`)
- [ ] No broken path references in `agents/ana.md`
- [ ] Installer successfully patches `core/config.yaml`, `bmm/config.yaml`, and `bmad-help.csv`
- [ ] `bmad-target-version` updated to `6.0.4` in config.yaml and bmad-compat.yaml
- [ ] BMAD mirror updated to v6.0.4
- [ ] Compatibility check report shows COMPATIBLE verdict

---

## Files to Modify (Summary)

| File | Change | Conditional On |
|------|--------|----------------|
| `_config/install-rbtv.py` | Refactor `normalize_bmad_output_paths()` to preserve user-chosen folder name; update `.cursorignore` pattern; update CSV schema if changed | Always (output folder fix) + conditional (schema) |
| `_config/config.yaml` | Update `bmad_target_version`, `output_folder`, and `paths.bmad_output` to not hardcode `_bmad-output` | Always |
| `agents/ana.md` | Update BMM workflow paths | BMM workflow paths changed in v6.0.4 |
| `workflows/doc-compound-learning/workflow.md` | Update advanced-elicitation path | Path changed (likely) |
| `bmad-compat.yaml` | Update version, paths, and document output folder is user-configurable | Always |
| `CLAUDE.md` | Update `{bmad_output}` path variable value in resolution table | Always |
| `_admin/docs/BMAD-mirror/` | Replace with v6.0.4 content (from `_admin/docs/BMAD-v6.0.4/`) | Always |
| `_admin/docs/BMAD-mirror/MIRROR-VERSION.md` | Update version/date | Always |
| 54 workflow files | Replace literal `_bmad-output` with configured output folder or variable | Always |
| 2 task files (`update-bmad-config.xml`, `restore-bmad-config.xml`) | Replace literal `_bmad-output` references | Always |
| `workflows/build-rbtv-component/data/bmad-architecture.md` | Update BMAD architecture reference to v6.0.4 patterns | Always |
| `readme.md` | Update `_bmad-output` path references | Always |
