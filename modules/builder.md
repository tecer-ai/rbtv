# Builder

## Purpose

The RBTV-native module — for building RBTV itself. Install it in workspaces where you create or modify RBTV components: it ships the guided component-creation workflow and the source-of-truth rule that keeps edits flowing to the repo instead of to the generated `.claude/` copies.

---

## Components

### `rbtv-create-component`

- **What**: Guided builder for any RBTV or vault AI component — skills, workflows, rules, commands, personas, tasks. Acts as a design partner: it challenges assumptions and forces key decisions before writing any file. Handles both RBTV-standard components (placed in the RBTV source repo, module-first) and workspace-native components (placed per that workspace's CLAUDE.md conventions).
- **When to use**: Creating a new skill, workflow, or rule from scratch. Modifying an existing component. Trying to understand how a component is structured before editing it. Use this instead of manually exploring component directories — the workflow handles discovery.
- **How to invoke**: "Create a new skill for X" or "build a workflow for Y" — or invoke by name: `rbtv-create-component`.
- **Inputs / outputs**:
  - Input: component type, description of what it should do, target system (RBTV or workspace-native)
  - Output: correctly placed and structured component file(s) with compliant naming and size
- **Example**: "I need a skill that runs our weekly competitor scan" → Claude identifies the right component type, drafts the structure, confirms placement, writes the files.

---

### `source-of-truth` rule

- **What**: An always-on rule stating that RBTV components installed into `.claude/` (skills, commands, rules, subagents) are generated thin loaders or copies, overwritten on every re-install — edits go to the RBTV source repo (module-first paths), then `python install.py` propagates them.
- **When to use**: Always active once the builder module is installed. Recovered from retirement for this module: in workspaces where you BUILD RBTV components, the edit-source-not-installed-copies discipline is load-bearing, not redundant.
- **How to invoke**: Automatic. No trigger — passive context.
- **What it produces**: Changed agent behavior — component edits land in `{rbtv_path}/<module>/...` source paths, never in `.claude/`.

---

## How They Fit Together

`rbtv-create-component` places and structures new components module-first; the `source-of-truth` rule keeps every subsequent edit pointed at the repo. Together they make the repo's hard rule (every component change updates README + `modules/` + `module-manifest.json` in the same change) executable by agents.
