---
name: Component Creation
description: Create new RBTV components — skills, workflows, personas, rules, tasks.
---

# Component Creation

## Scope

- **Modifying an existing RBTV component:** write changes to the RBTV source repo at `{rbtv_path}`.
- **Creating a new component:** ask the user: "Should this be an RBTV component (bootstrapped to all instances via re-install), or a local component (only in this instance)?"
  - **RBTV:** write to `{rbtv_path}/<type>/<name>/`. User must re-run `install.py` to generate the loader.
  - **Local:** write directly to `.claude/<type>/<name>/` in the instance (no `rbtv-` prefix). Not touched by re-install.

## Procedure

1. Read `{rbtv_path}/workflows/component-creation/data/component-patterns.md` — internalize naming standards, size limits, and structural requirements.
2. Identify the component type the user wants to create.
3. Load the appropriate template from `{rbtv_path}/workflows/component-creation/templates/`.
4. Walk the user through the template, filling in their requirements.
5. Write the component to the resolved destination (per Scope above).
6. If RBTV-published: remind the user to re-run `python install.py` to generate the loader.
