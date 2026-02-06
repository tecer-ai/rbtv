---
name: 'handoff-workflow'
description: 'Create context transfer summaries for agent continuity'
main_config: '	{project-root}/_bmad/rbtv/config.yaml'
nextStep: ./steps-c/step-01-init.md
validateWorkflow: ./steps-v/step-01-init.md
editWorkflow: ./steps-e/step-01-init.md
templateFiles:
  plan-development: '{project-root}/_bmad/rbtv/workflows/plan-lifecycle/templates/shape-template.md'
  execution: ./templates/handoff-execution.md
  project: ./templates/handoff-project.md
outputFolder: '{project-root}/_bmad-output/handoffs'
advancedElicitationTask: '{project-root}/_bmad/core/workflows/advanced-elicitation/workflow.xml'
---

# Handoff Workflow

**Goal:** Create a context transfer summary that enables seamless continuation by a new agent.

**Your Role:** Context curator collaborating with the user as a peer. You extract decisions, constraints, and instructions from the conversation and structure them for the receiving agent.

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
3. Present menu options and HALT. Wait for user selection.
4. On Continue: update frontmatter, then load the next step file.
5. On Advanced Elicitation: load and execute `{advancedElicitationTask}`, then redisplay the current step's menu.

### Critical Rules

- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read the entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update frontmatter after completing each step
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER pre-load or mentally plan future steps

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Build new handoff summary from scratch | steps-c/step-01-init.md | Handoff summary |
| Validate | Audit existing handoff for completeness | steps-v/step-01-init.md | Validation report |
| Edit | Modify sections of existing handoff | steps-e/step-01-init.md | Updated handoff |

**Current focus:** Create mode only. Validate and Edit modes are future additions.

---

## HANDOFF TYPES

| Type | Purpose | Output | Key Sections |
|------|---------|--------|--------------|
| **Plan Development** | Continue plan creation/modification | `shape.md` | User Inputs, Collaborative Decisions, Scope, Constraints |
| **Execution** | Execute tasks from approved plan | Handoff file | Problem, Goals, Decisions, Files to Load, Task Instructions |
| **Project** | General project context transfer | Handoff file | Context Summary, Current State, Decisions, References |

**Note:** Plan Development type creates/updates `shape.md` (the plan's companion file) rather than a separate handoff file. Shape.md serves as both the shaping document and the context transfer artifact.

---

## INITIALIZATION SEQUENCE

### 1. Check for Type Flag

- If invoked with `:plan` suffix → Set `handoffType = plan-development`
- If invoked with `:exec` suffix → Set `handoffType = execution`
- Standard invocation → Set `handoffType = project` (default)

### 2. Determine Sub-Mode

For now, always route to **Create** mode (steps-c/).

Future: Init step will check for existing handoff to determine Create vs Validate vs Edit.

### 3. Load First Step

Load, read completely, then execute `steps-c/step-01-init.md`.

---

## HANDOFF-SPECIFIC RULES

1. **Context extraction required** — Extract all decisions, constraints, and goals from conversation
2. **Location selection** — Ask user where to save the handoff before creating
3. **Type-appropriate sections** — Include type-specific sections based on handoff type
4. **Cleanup instruction** — Include self-delete prompt for receiving agent
5. **Document only** — Create handoff specification, never execute the work