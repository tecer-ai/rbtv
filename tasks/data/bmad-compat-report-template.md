---
type: bmad-compat-report
rbtv_version: "{rbtv_version}"
current_bmad_version: "{current_bmad_version}"
target_bmad_version: "{target_bmad_version}"
evaluation_date: "{evaluation_date}"
verdict: "{COMPATIBLE | BREAKING CHANGES | PARTIALLY VERIFIED}"
---

# BMAD Compatibility Report

**Evaluation Date:** {evaluation_date}
**RBTV Version:** {rbtv_version}
**Current BMAD Version:** {current_bmad_version}
**Target BMAD Version:** {target_bmad_version}
**Verification Method:** {Direct (mirror updated) | Release notes + GitHub (mirror not yet updated)}

---

## Overall Verdict

> **{COMPATIBLE | BREAKING CHANGES | PARTIALLY VERIFIED}**

{One-sentence summary of the verdict and what it means for the upgrade decision.}

---

## Touchpoint Results

### Installer Writes

| Touchpoint | Path | Result | Notes |
|------------|------|--------|-------|
| core/config.yaml output_folder | `_bmad/core/config.yaml` | {Compatible \| Breaking \| Unknown} | |
| bmm/config.yaml output paths | `_bmad/bmm/config.yaml` | {Compatible \| Breaking \| Unknown} | |
| bmad-help.csv schema | `_bmad/_config/bmad-help.csv` | {Compatible \| Breaking \| Unknown} | |
| .cursor/mcp.json merge | `.cursor/mcp.json` | {Compatible \| Breaking \| Unknown} | |
| .claude/.mcp.json merge | `.claude/.mcp.json` | {Compatible \| Breaking \| Unknown} | |
| .cursor/ config copy | `.cursor/` | {Compatible \| Breaking \| Unknown} | |
| .claude/commands/ replication | `.claude/commands/` | {Compatible \| Breaking \| Unknown} | |
| .cursorignore patterns | `.cursorignore` | {Compatible \| Breaking \| Unknown} | |

### Agent References

| Touchpoint | Path | Result | Notes |
|------------|------|--------|-------|
| Product Brief workflow (ana.md) | `_bmad/bmm/workflows/1-analysis/create-product-brief/workflow.md` | {Compatible \| Breaking \| Unknown} | |
| PRD workflow (ana.md) | `_bmad/bmm/workflows/2-plan-workflows/create-prd/workflow.md` | {Compatible \| Breaking \| Unknown} | |
| UX Design workflow (ana.md) | `_bmad/bmm/workflows/2-plan-workflows/create-ux-design/workflow.md` | {Compatible \| Breaking \| Unknown} | |

### Task References

| Touchpoint | Path | Result | Notes |
|------------|------|--------|-------|
| Advanced elicitation (doc-compound-learning) | `_bmad/core/workflows/advanced-elicitation/workflow.xml` | {Compatible \| Breaking \| Unknown} | |

### Structure Assumptions

| Assumption | Path | Result | Notes |
|------------|------|--------|-------|
| bmad-help.csv column schema | `_bmad/_config/bmad-help.csv` | {Compatible \| Breaking \| Unknown} | |
| manifest.yaml version field | `_bmad/_config/manifest.yaml` | {Compatible \| Breaking \| Unknown} | |
| core/config.yaml output_folder field | `_bmad/core/config.yaml` | {Compatible \| Breaking \| Unknown} | |
| bmm/config.yaml output path fields | `_bmad/bmm/config.yaml` | {Compatible \| Breaking \| Unknown} | |
| _bmad/ directory structure | `_bmad/` | {Compatible \| Breaking \| Unknown} | |

---

## Summary Counts

| Status | Count |
|--------|-------|
| Compatible | {n} |
| Breaking | {n} |
| Unknown | {n} |
| **Total** | {n} |

---

## Breaking Changes Detail

> *(Remove this section if verdict is COMPATIBLE)*

{For each Breaking touchpoint, document:}

### {Touchpoint Name}

- **What changed in BMAD {target_bmad_version}:** {description}
- **Impact on RBTV:** {what breaks}
- **Required RBTV fix:** {specific change needed, file path, line reference}
- **Effort:** {Low | Medium | High}

---

## Unknown Items (Manual Verification Required)

> *(Remove this section if no Unknown items)*

| Touchpoint | Why Unknown | Suggested Verification |
|------------|-------------|------------------------|
| {touchpoint} | {reason} | {what to do} |

---

## Recommended Actions

### If proceeding with upgrade:

1. {Action 1}
2. {Action 2}
3. Re-run RBTV installer: `python _config/install-rbtv.py`
4. Update `bmad_target_version` to `{target_bmad_version}` in:
   - `_config/config.yaml`
   - `bmad-compat.yaml`
   - `_admin/docs/BMAD-mirror/MIRROR-VERSION.md` (after updating mirror)

### If deferring upgrade:

- Document reason for deferral
- Recheck when: {condition or next BMAD release}

---

## Notes

{Any additional context, observations, or open questions discovered during evaluation.}
