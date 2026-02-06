---
name: 'plan-workflow'
description: 'Create high-quality, self-executing plans with micro-step task files'
main_config: '	{project-root}/_bmad/rbtv/config.yaml'
nextStep: ./steps-c/step-01-init.md
templateFile: ./templates/plan-template.md
microstepTemplateFile: ./templates/plan-task-microstep-template.md
shapeTemplateFile: ./templates/shape-template.md
learningsTemplateFile: ./templates/learnings-template.md
outputFolder: '{project-root}/.cursor/plans'
---

# Plan Workflow

**Goal:** Create high-quality, self-executing plans with micro-step task files that contain complete execution instructions.

**Your Role:** Strategic planner who creates actionable plans with proper task granularity. Plans are self-executing via micro-step files—no separate execution workflow.

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

| Mode | Purpose | Entry Point | Steps | Output |
|------|---------|-------------|-------|--------|
| Create | Build new plan from scratch | steps-c/step-01-init.md | 6 steps | Plan file (*.plan.md), shape.md, learnings.md, micro-step files |

**Create Mode Steps:**
| Step | File | Mode Required | Purpose |
|------|------|---------------|---------|
| 01 | step-01-init.md | Any | Initialize, detect state |
| 02 | step-02-context.md | Any | Gather context and scope |
| 03 | step-03-structure.md | Any | Create phases, tasks, checkpoints |
| 04 | step-04-generate-artifacts.md | **Agent mode** | Write shape.md, learnings.md, task files |
| 05 | step-05-create-plan.md | **Agent mode** | CreatePlan tool writes .plan.md, then consolidate in artifact folder |
| 06 | step-06-complete.md | Any | Validate, summary, final menu |

---

## INITIALIZATION SEQUENCE

### 1. Load Module Config

Load `{main_config}` and store all variables.

### 2. Load First Step

Load, read completely, then execute the first step file: `{nextStep}`.

---

## PLAN-SPECIFIC RULES

1. **Task granularity** — Describe WHAT to achieve, not HOW
2. **Single action per task** — Never combine actions
3. **Explicit file operations** — Use CREATE/UPDATE/DELETE/MOVE verbs
4. **Zero-context plans** — Plans must be self-contained
5. **Companion files** — Create shape.md and learnings.md alongside plan
6. **Micro-step files** — Generate task files with complete execution instructions
7. **Dependency ordering** — Validate dependencies before dependents
8. **Checkpoints required** — 3-6 checkpoints at inflection points
9. **Architectural constraints** — Document patterns that MUST be followed
10. **Final compound task** — Last task is always pN-compound for learnings review

---

## KNOWLEDGE FILES

Load these files as needed:

| File | Purpose | When to Load |
|------|---------|--------------|
| data/plan-creation-rules.md | Task granularity, file operations, dependency ordering, complexity assessment | During plan creation |
| {project-root}/_bmad/rbtv/tools-manifest.csv | Canonical tool list: skills (read skill_path) and subagents (Task tool + subagent_type='id') | When task requires invoking a tool |

## OUTPUT ARTIFACTS

Created during plan finalization in `{outputFolder}/{plan-name}/`:

| Artifact | Purpose |
|----------|---------|
| {plan-name}.plan.md | Main plan file with phases, tasks, and architecture diagram |
| shape.md | Scope boundaries, constraints, shaping decisions, append-only execution log |
| learnings.md | System improvement queue for BMAD/RBTV meta-learnings |
| phase-N/ | Folders containing micro-step task files |
| pN-X.task.md | Micro-step files with complete execution instructions per task |
