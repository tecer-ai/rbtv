---
name: 'plan-workflow'
description: 'Create high-quality plans and execute them following structured protocol with quality gates'
main_config: '{project-root}/_bmad/core/config.yaml'
nextStep: ./steps-c/step-01-init.md
executeWorkflow: ./steps-x/step-01-init.md
templateFile: ./templates/plan-template.md
outputFolder: '{project-root}/.cursor/plans'
---

# Plan Workflow

**Goal:** Create high-quality plans OR execute plan tasks following a structured protocol with quality gates.

**Your Role:** Strategic planner who creates actionable plans with proper task granularity, or disciplined executor who follows the 3-step guardrail workflow when executing plan tasks.

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
5. On Exit: save current state in frontmatter, exit workflow.

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
| Create | Build new plan from scratch | steps-c/step-01-init.md | Plan file (*.plan.md) |
| Execute | Execute tasks in existing plan | steps-x/step-01-init.md | Execution decisions logs |

---

## INITIALIZATION SEQUENCE

### 1. Load Module Config

Load `{main_config}` and store all variables.

### 2. Determine Mode

- If user invokes `/plan` or "create plan" → Route to **Create** mode
- If user references a `*.plan.md` file and says "execute task" or "execute plan" → Route to **Execute** mode
- If ambiguous → Ask user: "Do you want to [C] Create a new plan or [E] Execute tasks in an existing plan?"

### 3. Load First Step

Load, read completely, then execute the appropriate first step file.

---

## PLAN-SPECIFIC RULES

### For Creation Mode

1. **Task granularity** — Describe WHAT to achieve, not HOW
2. **Single action per task** — Never combine actions
3. **Explicit file operations** — Use CREATE/UPDATE/DELETE/MOVE verbs
4. **Zero-context plans** — Plans must be self-contained
5. **Spec artifacts** — Create shape.md, standards.md, references.md
6. **Dependency ordering** — Validate dependencies before dependents
7. **Checkpoints required** — 3-6 checkpoints at inflection points
8. **Architectural constraints** — Document patterns that MUST be followed

### For Execution Mode

1. **3-step guardrail** — Read decisions → Execute with Judge → Write decisions
2. **Quality gates** — Invoke judge before marking tasks complete
3. **State tracking** — Write execution decisions after each task
4. **Context budgeting** — Split tasks exceeding ~100k tokens

---

## KNOWLEDGE FILES

Load these files as needed:

| File | Purpose | When to Load |
|------|---------|--------------|
| data/plan-creation-rules.md | Task granularity, file operations, dependency ordering, context budgeting | Create mode |
| data/execution-protocol.md | 3-step guardrail, judge invocation, condensation rules | Execute mode |
| {project-root}/_bmad/rbtv/subagents-manifest.csv | Available subagent ids for Task tool (subagent_type); use id column | When task requires invoking a subagent |

## SPEC ARTIFACTS

Created during step-02-context in `{outputFolder}/{plan-name}/`:

| Artifact | Purpose |
|----------|---------|
| shape.md | Scope boundaries, constraints, shaping decisions |
| standards.md | Applicable rules and patterns |
| references.md | Key insights from research |
