---
description: Reduce AI agent cognitive overhead when resolving {project-root} paths in admin mode by replacing conditional table lookup with direct path variables
---

# PRD: Reduce Path Resolution Hops for AI Agents

## Status: Proposed
## Priority: Medium
## Description: Replace conditional path resolution table with direct path variables to eliminate multi-hop reasoning

---

## Problem

AI agents resolving `{project-root}` paths must perform a multi-hop cognitive process:

1. Read the reference (e.g., `{project-root}/_bmad/bmm/workflows/create-prd/workflow.md`)
2. Load the path resolution table from CLAUDE.md or the admin mirror rule
3. Pattern-match against 3 rows to find which rule applies
4. Apply the substitution
5. Construct the final path

This process is error-prone (the table itself contained a bug: `_docs/` instead of `_admin/docs/`) and expensive (failed resolution triggers fallback searches via glob/grep, wasting tool calls and tokens).

### Observed Failure

When Ana's PRD workflow referenced `{project-root}/_bmad/bmm/workflows/2-plan-workflows/create-prd/workflow.md`, the agent:
1. Read the resolution table
2. Identified the "everything else" row
3. Constructed path using the (incorrect) documented resolution
4. Failed to find the file
5. Fell back to `Glob("**/create-prd/workflow.md")`
6. Found the actual path at `_admin/docs/BMAD-mirror/...`

That's 3 wasted tool calls and reasoning cycles.

### Scale of the Problem

| Path pattern | RBTV files referencing it |
|---|---|
| `{project-root}/_bmad/core/...` | ~55 files |
| `{project-root}/_bmad/bmm/...` | ~6 files |
| `{project-root}/_bmad/rbtv/...` (self-resolves) | Most files |
| `{project-root}/_bmad-output/...` | Config + workflows |

Every cross-module reference (core, bmm) requires the 5-step resolution process. Self-references (`_bmad/rbtv/`) are simpler but still require checking against the table to confirm the rule.

### Root Cause

`{project-root}` is a single variable that serves dual duty:
- **In installed BMAD:** Literal project root — no resolution needed
- **In admin mode:** Requires a conditional lookup table to map to the local mirror

The conditional table creates the cognitive overhead. One variable, three possible resolution rules, applied per-reference.

---

## Proposed Solution

### Replace conditional table with direct path variables

Add resolved path variables to `_config/config.yaml` that agents load once during activation. Each variable resolves directly — no table lookup needed.

**New config.yaml fields:**

```yaml
# Path aliases (resolved per context by installer)
paths:
  bmad_core: "{project-root}/_bmad/core"
  bmad_bmm: "{project-root}/_bmad/bmm"
  bmad_rbtv: "{project-root}/_bmad/rbtv"
  bmad_output: "{project-root}/_bmad-output"
```

## Scope Boundary

- This PRD targets **path-resolution ergonomics** for agents (fewer lookup hops).
- It does not define installer output-path canonicalization policy.
- Canonical output-folder behavior and installer parity for `-bmad-output/{project-name}/` are tracked in `_admin/roadmap/todos/cp-install-scripts-standardize-bmad-output-folder.md`.

**In admin mode**, the admin installer (or admin config overrides) would resolve these to:

```yaml
paths:
  bmad_core: "_admin/docs/BMAD-mirror/_bmad/core"
  bmad_bmm: "_admin/docs/BMAD-mirror/_bmad/bmm"
  bmad_rbtv: "."
  bmad_output: "_admin-output"
```

**In installed BMAD**, the RBTV installer sets them to:

```yaml
paths:
  bmad_core: "{project-root}/_bmad/core"
  bmad_bmm: "{project-root}/_bmad/bmm"
  bmad_rbtv: "{project-root}/_bmad/rbtv"
  bmad_output: "{project-root}/_bmad-output"
```

### How agents use them

Before (5-step conditional resolution):
```
exec="{project-root}/_bmad/core/workflows/party-mode/workflow.md"
→ check table → match row 3 → substitute → construct path
```

After (1-step direct substitution):
```
exec="{bmad_core}/workflows/party-mode/workflow.md"
→ substitute from loaded config → done
```

### Migration path

1. Add `paths:` section to config.yaml
2. Update admin config overrides to include resolved paths
3. Update RBTV installer to set paths in installed BMAD config
4. Migrate agent/workflow files to use new variables (`{bmad_core}`, `{bmad_bmm}`)
5. Simplify or remove the path resolution table from CLAUDE.md and admin mirror rule

### What stays unchanged

- `{project-root}` remains available for cases where the full BMAD root is needed
- Files within RBTV still use relative paths (`./steps-c/step-01-init.md`)
- The admin installer and RBTV installer still handle the context-specific resolution

---

## Alternatives Considered

| Alternative | Why Not |
|---|---|
| Fix the table and keep current system | Fixes the bug but not the 5-step overhead — agents still waste cycles on every cross-module reference |
| Pre-resolve paths in agent files during install | Breaks dual-context design; files would differ between admin and installed copies |
| Symlinks from `_docs/` to `_admin/docs/` | Platform-dependent (Windows symlinks need admin privileges); masks rather than solves the problem |

---

## Risks

- **Migration scope:** ~60 files reference cross-module paths — mechanical but labor-intensive
- **Installer changes:** Both installers (admin + RBTV) need updates to populate the paths section
- **Backwards compatibility:** Files using `{project-root}` must continue working during migration period

---

## Success Criteria

- AI agents resolve cross-module paths in 1 step (variable substitution from loaded config)
- No conditional table lookup required for standard path resolution
- Path resolution table in CLAUDE.md simplified to reference the config variables
- Both installers correctly populate path variables for their context
- Zero increase in config loading time (paths loaded with existing config read)
