---
name: planning
description: 'Create high-quality, self-executing plans with micro-step task files'
nextStep: ./steps-c/step-01-init.md
templateFile: ./templates/plan-template.md
microstepTemplateFile: ./templates/plan-task-microstep-template.md
decisionsTemplateFile: '{rbtv_path}/orchestration/workflows/_shared/templates/decisions-template.md'
deliverablesTemplateFile: ./templates/deliverables-template.md
---

# Plan Workflow

**Goal:** Create high-quality, self-executing plans with micro-step task files that contain complete execution instructions.

**Your Role:** Strategic planner who creates actionable plans with proper task granularity. Plans are self-executing via micro-step files — no separate execution workflow.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.

### Step Processing Rules

1. Read the complete step file before any action.
2. Follow the MANDATORY SEQUENCE exactly as written.
3. Present menu options and HALT. Wait for user selection.
4. On Continue: load the next step file.
5. On Exit: exit workflow.

### Critical Rules

- NEVER load multiple step files simultaneously
- ALWAYS read the entire step file before execution
- NEVER skip steps or optimize the sequence
- ALWAYS halt at menus and wait for user input
- NEVER pre-load or mentally plan future steps
- 🛑 NEVER generate content without user input

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Steps | Output |
|------|---------|-------------|-------|--------|
| Create | Build new plan from scratch | steps-c/step-01-init.md | 4 steps | Plan file (*-plan.md), decisions.md, deliverables.md, micro-step files, spec files (code work) |

**Create Mode Steps:**

| Step | File | Purpose |
|------|------|---------|
| 01 | step-01-init.md | Initialize, detect state, resolve output path |
| 02 | step-02-context.md | Gather context and scope |
| 03 | step-03-structure.md | Create phases, tasks, checkpoints |
| 04 | step-04-generate-artifacts.md | Write all files (plan, decisions, deliverables, task files, specs), validate, summary |

---

## Initialization

1. Load the first step file: `{nextStep}`.

---

## PLAN-SPECIFIC RULES

1. **Task granularity** — Describe WHAT to achieve, not HOW
2. **Single action per task** — Never combine actions
3. **Explicit file operations** — Use CREATE/UPDATE/DELETE/MOVE verbs
4. **Zero-context plans** — Plans must be self-contained
5. **Companion files** — Create decisions.md and deliverables.md alongside plan
6. **Micro-step files** — Generate task files with complete execution instructions
7. **Dependency ordering** — Validate dependencies before dependents
8. **Checkpoints required** — 3-6 checkpoints at inflection points
9. **Architectural constraints** — Document patterns that MUST be followed

---

## KNOWLEDGE FILES

Load these files as needed:

| File | Purpose | When to Load |
|------|---------|--------------|
| data/plan-creation-rules.md | Authoring core: task granularity, file operations, complexity-band-to-door mapping, spec-authoring trigger, decisions-file discipline wiring, checkpoints, plan linking. Loaded ONCE at step-03. | step-03 (single load; step-01 no longer pre-loads it) |
| data/orchestration-planning.md | Orchestration-only layer: DEEP/LIGHT modes, the router-pin pre-resolution set, worker-contract frontmatter, microstep orchestration frontmatter shape | **Orchestrated plans only** — loaded at step-02 §4a when `orchestrated: true`; never on a plain run |
| `{rbtv_path}/orchestration/workflows/_shared/authoring/` | The shared authoring core — the SINGLE SOURCE of authoring knowledge the workflow consumes: `complexity-rubric.md` (axes + bands), `task-file-contract.md` (zero-context task contract), `spec-template.md` (behavior spec + test plan for code work), `dependency-ordering.md` (ordering rules + serialization + validity checks), `decisions-discipline.md` (decisions.md entry-shape rules, size floor, reminder line, audit checklist) | During plan creation — read the core file the step needs; never duplicate its content into the plan |

## OUTPUT ARTIFACTS

Created during finalization in `{output-path}/{plan-name}/`:

| Artifact | Purpose |
|----------|---------|
| {plan-name}-plan.md | Main plan file with phases, tasks, and architectural constraints |
| decisions.md | Scope boundaries, constraints, shaping decisions, discoveries, and required execution references (worker-facing; entry-shape disciplined; harvest-worthy entries carry the one-word `compoundable` marker) |
| deliverables.md | Artifact index — one row per task: where its output lands, with status |
| {feature}-spec.md | Behavior spec + test plan per code feature (code-work plans only; from the shared spec template) |
| phase-N/ | Folders containing micro-step task files |
| pN-X.task.md | Micro-step files with complete execution instructions per task |
