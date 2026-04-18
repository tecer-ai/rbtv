---
name: 'compound-workflow'
description: 'Create backlog PRDs documenting system improvements'
nextStep: ./steps-c/step-01-init.md
editWorkflow: ./steps-e/step-01-init.md
templateFile: ./templates/compound-prd.md
outputFolder: 'RESOLVE-BY-ORIGIN'
---

# Compound Workflow

**Goal:** Create a backlog PRD that documents a system improvement, correction, or pattern for later implementation.

**Your Role:** Self-reflective analyst who examines what went wrong, evaluates context sources, and documents improvement proposals. You do NOT implement changes — you create specifications for future implementation.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After each step, update `stepsCompleted` in the output document's frontmatter.

### Step Processing Rules

1. Read the complete step file before any action.
2. Follow the MANDATORY SEQUENCE exactly as written.
3. Present menu options and HALT. Wait for user selection. (Note: Menu options vary per step based on step-specific needs)
4. On Continue: update frontmatter, then load the next step file.
6. On Exit: save current state in frontmatter, exit workflow.

### Critical Rules

- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read the entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update frontmatter after completing each step
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER pre-load or mentally plan future steps
- 🚫 NEVER implement changes — document only

---

## OUTPUT PATH RESOLUTION

The `outputFolder` is `RESOLVE-BY-ORIGIN` — resolved at runtime using component-origin inference.

During step-02 (self-assessment), the agent identifies which files need changing. Use the **primary affected file's path** to determine where the compound PRD belongs:

| Component lives under... | Output folder |
|---|---|
| `{rbtv_path}/` (RBTV source) | `{rbtv_path}/_admin/roadmap/todos/` |
| `_system/` or `.claude/` (non-rbtv vault components) | `_system/roadmap/todos/` |
| `5. Workbench/{project}/` (project repo) | Defer to that project's conventions — check its CLAUDE.md |
| Ambiguous / no specific file identified | Ask user: "Is this about RBTV behavior or vault/system behavior?" |

Create the output folder if it does not exist.

The resolved path MUST be confirmed with the user before writing the PRD to disk.

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Build new compound PRD from scratch | steps-c/step-01-init.md | Backlog PRD |
| Validate | Audit existing compound PRD (future) | steps-v/step-01-init.md | Validation report |
| Edit | Modify existing compound PRD (future) | steps-e/step-01-init.md | Updated PRD |

**Current focus:** Create mode only. Validate and Edit modes are future additions.

---

## Initialization

### 1. Preferences

- If `_system/user/profile/preferences.md` exists in the target, read user preferences for language and output conventions.

### 2. Check for Yolo Flag

- If invoked with `:yolo` suffix → Set `yoloMode = true`
- Standard invocation → Set `yoloMode = false`

### 3. Determine Sub-Mode

For now, always route to **Create** mode (steps-c/).

Future: Init step will check for existing PRD to determine Create vs Validate vs Edit.

### 4. Load First Step

Load, read completely, then execute `steps-c/step-01-init.md`.

---

## COMPOUND-SPECIFIC RULES

1. **Self-assessment required** — Agent must analyze what went wrong before documenting
2. **Context source evaluation** — Identify which files influenced behavior
3. **Five options pattern** — Generate 5 distinct improvement approaches
4. **Discussion step** — Discuss with user before documenting (skipped in yolo mode)
5. **Document only** — Create PRD specification, never implement changes
