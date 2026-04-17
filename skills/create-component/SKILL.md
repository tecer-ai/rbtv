---
name: rbtv-create-component
description: "Create a new RBTV component (agent, skill, workflow, rule, task). Use when adding to or extending the RBTV system."
---

# Create Component

**CRITICAL — Execute these steps in order. Load persona/workflow files FULLY before acting.**

1. Load persona from `{rbtv_path}/personas/fernando.md`.
2. Execute the workflow at `{rbtv_path}/workflows/component-creation/workflow.md`.
3. **Fernando's scope:**
   - If the user is modifying an existing RBTV component, write the changes to the RBTV source repo at `{rbtv_path}`.
   - If the user is creating a new component, ASK: "Should this be an RBTV component (bootstrapped to all instances via re-install), or a local component (only in this instance)?"
     - RBTV: write to `{rbtv_path}/<type>/<name>/`. User must re-run `install.py` to generate the loader.
     - Local: write directly to `.claude/<type>/<name>/` in the instance (no `rbtv-` prefix). Not touched by re-install.
