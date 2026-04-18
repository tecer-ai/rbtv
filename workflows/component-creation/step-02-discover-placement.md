---
name: Discover Placement
description: Determine where the component files will be written.
nextStepFile: step-03-scaffold.md
---

# Step 2: Discover Placement

**Goal:** Resolve the full file paths for all component files before any scaffolding begins.

---

## Mandatory Sequence

### 1. Identify Target System

Ask: "Is this an RBTV component or a component for your local system?"

- **RBTV** → apply RBTV Standard Placement (table below), skip to Step 4
- **Non-RBTV** → continue to Step 2

### 2. Read Workspace Conventions (Non-RBTV only)

Read the workspace root `CLAUDE.md`. Look for a "Component Placement" section or equivalent (may also appear under headings like "Skill Dispatch", "Directory Layout", or "System Files").

- If conventions found → apply them in Step 3
- If no conventions found → continue to Step 3b

### 3a. Apply Workspace Conventions

Map each file to be created to its destination per the workspace conventions. Present the mapping for review before proceeding.

### 3b. Ask User (no conventions found)

Ask two targeted questions:

1. "Where do workflows and system logic files go in your project?"
2. "Where do thin loaders (skills or commands) go?"

Record the answers. These become the placement for this component.

### 4. Confirm File Paths

Present a complete file path table:

| File | Destination path |
|------|-----------------|
| [file name] | [full resolved path] |
| ... | ... |

Wait for user confirmation. Do not proceed until paths are approved.

---

## RBTV Standard Placement

| Component | Destination |
|-----------|-------------|
| Workflow | `{rbtv_path}/workflows/{name}/` |
| Agent/Persona | `{rbtv_path}/personas/{name}.md` |
| Rule | `{rbtv_path}/rules/{name}.md` |
| Task | `{rbtv_path}/tasks/{name}.xml` |
| Skill (thin loader) | `{rbtv_path}/skills/{name}/SKILL.md` |
| Knowledge/Data | `{rbtv_path}/workflows/{parent}/data/` |

---

## Thin Loader Invariant

Skills and commands are ALWAYS thin loaders — zero logic in the loader file itself.

| Component | Where logic lives |
|-----------|------------------|
| Skill | Logic lives in the workflow or task the skill delegates to |
| Command | Logic lives in the workflow, task, or agent the command loads |

If the skill or command has no backing file yet, that backing file must be designed (Step 1) and placed (this step) before the loader can be resolved.

---

## Step Menu

| Option | Action |
|--------|--------|
| [C] Continue | Proceed to Step 03 — Scaffold |
| [X] Exit | Stop workflow |

HALT and WAIT for user input.
