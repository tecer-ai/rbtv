---
description: Standardize main_config declaration across all RBTV workflows - frontmatter vs body inconsistency
---

# PRD: Standardize main_config Declaration Pattern

## Problem Statement

4 utility workflows declare `main_config` in frontmatter while all BI workflows load config in body text. No single pattern exists across the codebase, creating inconsistency and reduced discoverability.

## Current State

**Frontmatter approach (4 utility workflows):**
```yaml
---
main_config: {project-root}/_config/config.yaml
---
```

**Body text approach (BI workflows):**
- Config loading logic embedded in markdown body
- Varies in placement and visibility
- Less discoverable for tooling and agents

## Root Cause

No established standard when workflows were initially created. Pattern evolved organically without enforcement.

## Proposed Solution

**Standardize on frontmatter declaration** for all workflows that require config:

1. All workflows MUST declare `main_config` in YAML frontmatter if they use config
2. Remove body text config loading logic where frontmatter exists
3. Update component pattern documentation to require frontmatter approach
4. Audit all 38 workflows and migrate to frontmatter pattern

## Scope Boundary

- This PRD governs **config declaration format** only (frontmatter vs body text).
- Output destination normalization and installer parity for `-bmad-output/{project-name}/` are tracked in `_admin/roadmap/todos/cp-install-scripts-standardize-bmad-output-folder.md`.
- Avoid introducing duplicate or conflicting requirements about output-path semantics in this PRD.

## Benefits

| Benefit | Description |
|---------|-------------|
| Discoverability | Agents and tooling can detect config requirements by parsing frontmatter |
| Consistency | Single pattern across all workflows |
| Maintainability | Config path changes require only frontmatter updates |
| Documentation | Self-documenting through structured metadata |

## Implementation Checklist

- [ ] Update `_config/.cursor/rules/bmad-rbtv-component-patterns.mdc` to mandate frontmatter approach
- [ ] Audit all 38 workflows for config usage
- [ ] Migrate BI workflows to frontmatter pattern
- [ ] Remove redundant body text config loading where applicable
- [ ] Validate no functionality breaks during migration

## Success Criteria

- 100% of workflows using config declare it in frontmatter
- Zero workflows use body text config loading
- Component patterns documentation updated
- All workflows tested post-migration

## Priority

Medium — Improves consistency but not blocking functionality

## Effort Estimate

Low — Straightforward migration, 38 files to check, ~10 to modify
