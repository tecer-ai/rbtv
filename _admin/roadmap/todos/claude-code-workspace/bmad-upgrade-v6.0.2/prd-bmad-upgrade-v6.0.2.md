---
type: prd
status: ready
created: 2026-02-23
target_bmad_version: "6.0.2"
from_bmad_version: "6.0.0-Beta.4"
---

# PRD: BMAD Upgrade from 6.0.0-Beta.4 to v6.0.2

## Summary

Upgrade the RBTV BMAD installation from 6.0.0-Beta.4 to v6.0.2 (stable release) without breaking any RBTV integration. This PRD covers every change needed in RBTV and its installer scripts so Henri can perform the upgrade confidently.

**Stable release significance:** v6.0.0 ended the beta cycle. This upgrade moves RBTV from beta to the first stable release series, gaining all Beta.5 through v6.0.2 improvements.

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
1. Download BMAD v6.0.2 release
2. Check each of the three paths in the downloaded release:
   - `_bmad/bmm/workflows/1-analysis/create-product-brief/workflow.md` — does `workflow.md` still exist or was it renamed?
   - `_bmad/bmm/workflows/2-plan-workflows/create-prd/workflow.md` — same check
   - `_bmad/bmm/workflows/2-plan-workflows/create-ux-design/workflow.md` — same check
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
1. Check BMAD v6.0.2 release for path `_bmad/core/workflows/advanced-elicitation/`
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
1. Download BMAD v6.0.2 and inspect `_bmad/_config/bmad-help.csv`
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
1. Download BMAD v6.0.2 and inspect `_bmad/bmm/config.yaml`
2. Verify the fields `output_folder`, `planning_artifacts`, `implementation_artifacts` still exist with the same names
3. If renamed: update `normalize_bmad_output_paths()` in `_config/install-rbtv.py`

---

### 5. `_bmad/_config/manifest.yaml` Format — LOW RISK

**What RBTV does:** The installer's pre-flight version check reads `_bmad/_config/manifest.yaml` and expects an `installation.version` field.

**What BMAD changed:** No documented change to manifest format between Beta.4 and v6.0.2, but it should be verified.

**Required action before upgrading:**
1. Inspect `_bmad/_config/manifest.yaml` in BMAD v6.0.2
2. Verify `installation.version` field exists
3. Verify the version format is still semver (e.g., `6.0.2`)
4. If format changed: update `check_bmad_version()` in `_config/install-rbtv.py`

---

### 6. `_bmad/` Directory Structure — LOW RISK

**What RBTV does:** The installer assumes these directories exist:
- `_bmad/_config/`
- `_bmad/core/`
- `_bmad/bmm/`

**What BMAD changed:** No core structural changes to `_bmad/core/` or `_bmad/bmm/`. The `_bmad/` naming convention (vs the earlier `.bmad/` hidden folder) was already established by Beta.4. SDET module was added in Beta.3 (but RBTV doesn't reference it).

**Required action before upgrading:**
1. Verify `_bmad/core/` and `_bmad/bmm/` still exist in v6.0.2
2. Verify no new required modules that RBTV should reference

---

### 7. TEA Module Dependency — MEDIUM RISK

**What RBTV does:** The BMAD mirror at `_admin/docs/BMAD-mirror/` includes the TEA module at version `0.1.1-beta.3`. RBTV's `bmad-compat.yaml` does not explicitly reference TEA paths, but it should be verified that no RBTV workflows or agents accidentally reference TEA tasks.

**What BMAD changed:** TEA module moved to external (not bundled in the main BMAD release) starting around Beta.3. This means in v6.0.2, TEA may not be present in the downloaded release package.

**Required action before upgrading:**
1. Search RBTV codebase for any references to `_bmad/tea/`:
   ```bash
   grep -r "_bmad/tea" agents/ workflows/ tasks/ --include="*.md" --include="*.xml"
   ```
2. If references are found: TEA must be installed separately as an external module before RBTV agents that reference it will work
3. If no references found: no action needed — TEA is not an RBTV dependency
4. Update `MIRROR-VERSION.md` to reflect that TEA is no longer in the base release (external module)

---

## Upgrade Procedure

### Step 1 — Download and inspect BMAD v6.0.2

Download from: `https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.0.2`

Inspect the following before touching anything:

```bash
# Check workflow paths that RBTV references
ls _bmad/bmm/workflows/1-analysis/create-product-brief/
ls _bmad/bmm/workflows/2-plan-workflows/create-prd/
ls _bmad/bmm/workflows/2-plan-workflows/create-ux-design/
ls _bmad/core/workflows/advanced-elicitation/

# Check config file field names
grep -E "output_folder|planning_artifacts|implementation_artifacts" _bmad/bmm/config.yaml
grep "output_folder" _bmad/core/config.yaml

# Check manifest format
cat _bmad/_config/manifest.yaml

# Check bmad-help.csv header
head -1 _bmad/_config/bmad-help.csv
```

### Step 2 — Fix RBTV before upgrading

Based on inspection findings, update RBTV files:

| If found | Then update |
|----------|-------------|
| BMM workflow paths changed | `agents/ana.md`, `bmad-compat.yaml` |
| `advanced-elicitation/workflow.xml` path changed | `workflows/doc-compound-learning/workflow.md`, `bmad-compat.yaml` |
| `bmad-help.csv` columns changed | `_config/install-rbtv.py::add_rbtv_to_help_catalog`, `bmad-compat.yaml` |
| `bmm/config.yaml` field names changed | `_config/install-rbtv.py::normalize_bmad_output_paths`, `bmad-compat.yaml` |
| `manifest.yaml` format changed | `_config/install-rbtv.py::check_bmad_version` |

### Step 3 — Update RBTV version declarations

After fixing any breaking changes:

**`_config/config.yaml`:**
```yaml
bmad_target_version: "6.0.2"
bmad_min_version: "6.0.0"   # Accept any stable 6.0.x
```

**`bmad-compat.yaml`:**
```yaml
bmad_target_version: "6.0.2"
bmad_min_version: "6.0.0"
```

### Step 4 — Update the BMAD mirror

Replace `_admin/docs/BMAD-mirror/` contents with v6.0.2 release files:

```bash
# Preserve RBTV-owned metadata before replacing
cp _admin/docs/BMAD-mirror/MIRROR-VERSION.md /tmp/mirror-version-backup.md
cp -r _admin/docs/BMAD-mirror/_bmad/rbtv /tmp/rbtv-slot-backup

# Replace mirror contents with v6.0.2
rm -rf _admin/docs/BMAD-mirror/*
# Extract v6.0.2 release contents here

# Restore RBTV-owned files
cp /tmp/mirror-version-backup.md _admin/docs/BMAD-mirror/MIRROR-VERSION.md
mkdir -p _admin/docs/BMAD-mirror/_bmad/rbtv
# (slot should remain empty — restore any RBTV-owned items only)
```

Update `_admin/docs/BMAD-mirror/MIRROR-VERSION.md`:
```markdown
| BMAD Version | 6.0.2 |
| Mirror Synced | YYYY-MM-DD |
| Source | https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.0.2 |
```

Update module versions table:
```markdown
| Module | Version |
|--------|---------|
| core   | 6.0.2   |
| bmm    | 6.0.2   |
| bmb    | (check v6.0.2 release) |
| cis    | (check v6.0.2 release) |
| tea    | (external — not in release) |
```

### Step 5 — Upgrade BMAD on VPS

Run the BMAD installer on the VPS with the new version, then re-run the RBTV sync installer to re-apply RBTV config patches:

```bash
# On VPS, after BMAD upgrade
sudo -u nanobot python3 /opt/robotville/BMAD/_bmad/rbtv/_config/install-rbtv.py --mode sync
sudo systemctl restart nanobot-gateway
```

### Step 6 — Run compatibility check

Use the check-bmad-compat task to validate all touchpoints:

```
# As an agent, run the compatibility check task
task: check-bmad-compat.xml
input: target_version=6.0.2
```

This will produce a report at `_admin-output/planning-artifacts/bmad-compat-report-6.0.2.md`.

### Step 7 — Smoke test on VPS

After upgrade, run `_mobile/_docs/smoke-checklist.md` to validate nanobot responds correctly and all agent routing works.

### Step 8 — Update CHANGELOG

Add an entry to `CHANGELOG.md` documenting the upgrade.

---

## What RBTV Does NOT Need to Change

These BMAD changes do not affect RBTV:

| BMAD Change | Why RBTV is Unaffected |
|------------|------------------------|
| 10 new CLI installer flags (Beta.8) | RBTV uses its own unified installer, not BMAD's CLI |
| Kiro IDE support (Beta.8) | RBTV does not integrate with Kiro |
| CodeBuddy support (v6.0.2) | RBTV does not integrate with CodeBuddy |
| OpenCode template consolidation (Beta.8) | RBTV does not use OpenCode |
| GitHub Copilot installer (v6.0.0) | RBTV does not integrate with Copilot |
| `disable-model-invocation` flag removed (Beta.8) | RBTV installer does not use this flag |
| Codex installer migrated to `.agents/skills` (v6.0.2) | RBTV does not use Codex |
| Excalidraw workflows removed (Beta.6) | RBTV does not use Excalidraw |
| PRD workflow steps 2b-2c added (v6.0.0) | RBTV business innovation uses its own PRD workflow |
| `bmad uninstall` command (v6.0.0) | RBTV install/uninstall is via its own installer |

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| BMM workflow paths broken | High | Medium | Verify paths before upgrade (Step 1) |
| advanced-elicitation path broken | High | High | Beta.7 changed .xml → .md format and split files |
| bmad-help.csv schema mismatch | Medium | Low | Verify header before upgrade |
| bmm/config.yaml field rename | Medium | Low | Verify fields before upgrade |
| TEA module not in v6.0.2 package | Medium | High | Search RBTV for `_bmad/tea/` refs; install TEA externally if needed |
| manifest.yaml format change | Low | Low | Verify field before upgrade |

**Most likely breaking changes:**
1. `advanced-elicitation/workflow.xml` path — BMAD converted from XML to Markdown format in Beta.7, this almost certainly changed
2. TEA module absent from v6.0.2 bundle — TEA moved external; if RBTV references TEA paths they'll be broken

---

## Success Criteria

- [ ] All 7 RBTV→BMAD touchpoint categories verified against v6.0.2 structure
- [ ] No broken path references in `agents/ana.md` or any RBTV workflow file
- [ ] Installer successfully patches `core/config.yaml`, `bmm/config.yaml`, and `bmad-help.csv`
- [ ] `bmad-target-version` updated to `6.0.2` in config.yaml and bmad-compat.yaml
- [ ] BMAD mirror updated to v6.0.2
- [ ] Smoke checklist passes on VPS after upgrade
- [ ] Compatibility check report shows COMPATIBLE verdict

---

## Files to Modify (Summary)

| File | Change | Conditional On |
|------|--------|----------------|
| `agents/ana.md` | Update BMM workflow paths | BMM workflow paths changed in v6.0.2 |
| `workflows/doc-compound-learning/workflow.md` | Update advanced-elicitation path | Path changed (likely) |
| `_config/install-rbtv.py` | Update field names / CSV schema | Schema changes found |
| `bmad-compat.yaml` | Update version + any changed paths | Always (version update) |
| `_config/config.yaml` | Update bmad_target_version to 6.0.2 | Always |
| `_admin/docs/BMAD-mirror/` | Replace with v6.0.2 content | Always |
| `_admin/docs/BMAD-mirror/MIRROR-VERSION.md` | Update version/date | Always |
| `CHANGELOG.md` | Document upgrade | Always |
