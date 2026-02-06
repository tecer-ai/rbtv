---
title: 'Handoff: Plan Ecosystem Redesign'
docType: 'handoff'
mode: 'create'
handoffType: 'plan-development'
targetAgent: 'Agent continuing plan execution'
stepsCompleted:
  - step-01-init.md
  - step-02-location-selection.md
  - step-03-extraction.md
  - step-04-document.md
inputDocuments:
  - .cursor/plans/plan_ecosystem_redesign_26823711.plan.md
outputPath: '_bmad/rbtv/.rbtv-docs/system-documentation/plan-component-redesign/'
date: '2026-02-04'
---

# Handoff: Plan Ecosystem Redesign

**Type:** Plan Development  
**Created:** 2026-02-04  
**For:** Agent executing the plan or continuing plan refinement

---

## Context Summary

This conversation designed a comprehensive redesign of the RBTV plan ecosystem. Starting from reviewing 6 legacy planning documents, the user provided detailed requirements for how plans should work, which were refined through iterative discussion. The result is a structured plan with 17 tasks across 5 phases, ready for execution.

---

## Problem Being Solved

**Core Problem:** The current plan ecosystem is heavy on plan creation but lacks self-executing plans. Execution requires loading a separate workflow, and there's no unified access pattern for tools (commands, skills, subagents).

### Current State

- Plan file created at `.cursor/plans/plan_ecosystem_redesign_26823711.plan.md`
- Plan refined with all user clarifications incorporated
- Ready for execution (17 tasks across 5 phases)

### Root Cause

Plans and execution were designed as separate concerns. Tools (commands, skills, subagents) evolved independently without unified access patterns, creating inconsistency in how humans and AI agents access the same capabilities.

---

## User Goals

1. **Unified tool access** — Every RBTV tool must have all three entry points (command, skill, subagent) with matching names. AI agents have the same tools as humans.

2. **Self-executing plans** — Plans should be self-executing via micro-step task files. Eliminate the separate execution workflow.

3. **Simplified execution logging** — All execution context goes to shape.md (append-only). No condensation tasks, no separate execution_decisions files.

4. **System improvement capture** — Learnings.md captures BMAD/RBTV system improvements based on user corrections/suggestions, not project-specific learnings.

5. **Complexity assessment** — Implement complexity evaluation for tasks/phases using a 5-dimension scoring system.

6. **Revolving plans** — Plans can add/remove tasks during execution with clear user notification. Shape.md is append-only.

---

## Constraints Gathered

| Constraint | Type | Description |
|------------|------|-------------|
| Sequential execution | Process | Tasks are sequential, no parallelization |
| Checkpoint simplicity | Process | Checkpoints need no micro-step files (simple pause points) |
| Skill vs Subagent | Technical | Skills execute in same context window; subagents in new context window |
| No nested subagents | Technical | One subagent cannot invoke another subagent (only skills) |
| Shape.md append-only | Process | Never modify existing content, only append new sections |
| Task change notification | Process | When tasks added/removed, agent must clearly communicate changes to user |

---

## User Inputs (Maintained and Developed)

### Input 1: Plan Body and Accessory Documents
**User's input:** 
> "the plan body must contain only information relevant to all tasks"
> "the plan must have accessory documents, that give additional context to the agents who will execute the plan"

**Developed into:** Plan-level context vs task-level context separation. Shape.md, learnings.md, and standards.md as companion files.

---

### Input 2: Micro-Step Task Files
**User's input:**
> "every plan created must follow bmad's micro step files"
> "while the plan body contains information relevant to all tasks of the plan, when the plan is created, a series of micro step files are also created"
> "the plans yaml front matter only has a brief, 140 chars, description of what has to be performed, and the link to the respective micro step file"

**Developed into:** Each task gets a micro-step file containing:
- Task-specific context (documents specific to that task)
- Execution flow (read context → understand goal → understand tools → execute → review → document → mark complete)
- Tool declarations with explicit mode (skill vs subagent)

---

### Input 3: Skills vs Subagents Distinction
**User's input:**
> "tools are skills or subagents that the executing agent has"
> "the difference between both is that skills execute the flow in the same context window, while sub agents run it in a new context window, and will need inputs when ran"
> "one sub agent cannot invoke another subagent (that means, if the task is already being executed by a sub agent, the steps of its micro files steps cannot use sub agents as tools, only skills)"

**Developed into:** 
- Explicit `mode: skill | subagent` declaration in micro-step files
- Constraint: Subagents can only invoke skills, never other subagents

---

### Input 4: Unified Tools Entry Points
**User's input:**
> "every workflow that currently has a command entrypoint must also have a skill and a sub agent entry point"
> "the same above for workflows that currently have a skill or sub agent entry point, must have a entry point in the other 2 tools"
> "the names of the entry points must be the same"
> "this is what i meant when i said that the AI agents (skill and sub agents) must have the same tools as humans (commands)"

**Developed into:** 
- Unified `tools-manifest.csv` with columns: id, name, description, command_path, skill_path, subagent_path
- 13 RBTV tools identified, each needing all 3 entry points
- Tasks 1.2-1.4 in plan to create missing thin loaders

---

### Input 5: Condensation Eliminated
**User's input:**
> "condensation are not needed anymore, as all info will go exclusively on shape.md"
> "this system allows for no parallelization of tasks, they are all sequential, but can be executed on the same context window"
> "checkpoints need no micro step file"

**Developed into:**
- All execution context → shape.md (append-only)
- No separate execution_decisions files
- No condensation tasks
- Checkpoints are simple YAML entries that halt execution

---

### Input 6: Learnings.md Purpose
**User's input:**
> "learnings.md makes it clear that its purpose is not to capture the learnings of the specific plan execution, but to capture learnings of how bmad or rbtv could be improved given user corrections, suggestions and guidance"

**Developed into:**
- Learnings.md as system improvement queue
- Each learning entry includes: trigger, category, user's exact words, recommended system change, compound readiness
- Final task of every plan runs doc-compound on learnings.md

---

### Input 7: Complexity Evaluation
**User's input:**
> "suggest me a way (a step) so agents evaluate tasks or phases complexity"

**Developed into:** 5-dimension complexity assessment:
- Context size (1-3)
- Dependencies (1-3)
- Tool usage (1-3)
- Decision density (1-3)
- Human review need (1-3)

Scoring thresholds: 5-7 simple, 8-11 moderate, 12-15 complex

---

### Input 8: Revolving Plan Pattern
**User's input:**
> "i mean to update shape (appending, never updating old content) and, what is added to the plan, is the task to work on new documents/references not foreseen during the plan creation (only if this new work is complex - if work is simple, it is performed right away)"
> "this means the plan is revolving and reshaping itself while it is executed"

**Developed into:**
- Shape.md append-only rule (never modify existing content)
- Discovery handling: Simple (<5 min) → do immediately; Complex → add task to plan
- Task changes (add/remove) require clear notification to user in output message

---

### Input 9: Task Change Notification
**User's input:**
> "tasks can be added or removed. if that happen, in the output message to the user, the agent must make very clear what he has changed"

**Developed into:** Mandatory output format when tasks change:
```
⚠️ PLAN MODIFIED

Tasks ADDED:
- [task-id]: [description] — Reason: [why needed]

Tasks REMOVED:
- [task-id]: [description] — Reason: [why no longer needed]
```

---

### Input 10: Template Naming
**User's input:**
> "name it plan-task-microstep-template.md --> important to differentiate to other microstep templates"

**Developed into:** Template at `_bmad/rbtv/workflows/plan-lifecycle/templates/plan-task-microstep-template.md`

---

## Collaborative Decisions

| # | Decision | User Input | AI Contribution | Final Resolution |
|---|----------|------------|-----------------|------------------|
| 1 | Micro-step file structure | Must contain context, goal, tools, execution flow | Proposed 4-phase grouping (understand → execute → validate → close) | Adopted 4-phase structure with optional validate phase |
| 2 | Shape.md structure | Append-only, captures execution context | Proposed sections: Original Shaping, Standards Applied, Execution Log, Execution Discoveries | Adopted with execution discoveries capturing contradictions |
| 3 | Learnings.md format | Must be compound-ready, capture user corrections | Proposed structured entry with category checkboxes, user's exact words, recommended change | Adopted with compound readiness assessment |
| 4 | Complexity assessment | Need a way to evaluate complexity | Proposed 5-dimension scoring (context, dependencies, tools, decisions, human review) | Adopted with thresholds 5-7/8-11/12-15 |
| 5 | Tools manifest structure | Single manifest, all 3 entry points | Proposed CSV with id, name, description, command_path, skill_path, subagent_path | Adopted, identified 13 tools needing completion |
| 6 | Plan output location | User specified custom path | Suggested `.cursor/plans/` | User chose `_bmad/rbtv/.rbtv-docs/system-documentation/plan-component-redesign/` |

---

## Information Gaps

**None** — The plan is comprehensive with all requirements clarified. The receiving agent has full context to execute.

---

## Judge Feedback Summary

**Status:** Not Yet Reviewed

The plan was created but not submitted to judge for evaluation. The receiving agent may optionally invoke judge review before execution if validation is desired.

---

## Files to Load

| File | Purpose | Priority |
|------|---------|----------|
| `.cursor/plans/plan_ecosystem_redesign_26823711.plan.md` | The complete plan with 17 tasks across 5 phases | MUST READ FIRST |
| `_bmad/rbtv/workflows/plan-lifecycle/` | Current workflow structure to be modified | MUST READ |
| `.cursor/skills/bmad-rbtv-*/SKILL.md` | Current skill thin loaders (patterns to follow) | Reference |
| `.cursor/agents/bmad-rbtv-*.md` | Current subagent thin loaders (patterns to follow) | Reference |
| `.cursor/commands/bmad-rbtv-*.md` | Current command thin loaders | Reference |
| `_bmad/rbtv/subagents-manifest.csv` | Current manifest format (to be replaced) | Reference |

---

## For the Agent Reading This Handoff

### Immediate Next Steps

1. **Read the plan file** at `.cursor/plans/plan_ecosystem_redesign_26823711.plan.md` — this contains all 17 tasks organized into 5 phases
2. **Start with Phase 1** (Unified Tools Infrastructure) — this establishes the foundation for all other work
3. **Execute tasks sequentially** — tasks are ordered by dependency; do not skip or parallelize

### Guidelines

- Follow the revolving plan pattern: if you discover something that requires complex new work, add it as a task rather than doing it immediately
- When tasks are added or removed, clearly notify the user with the `⚠️ PLAN MODIFIED` format
- All execution context should be appended to shape.md, never modify existing content
- Use skills (not subagents) when executing within this context window

### What NOT to Do

- Do not revisit decisions already made (see Collaborative Decisions table above)
- Do not create separate execution_decisions files — all context goes to shape.md
- Do not invoke subagents from within a subagent context — use skills only
- Do not skip complexity assessment when creating micro-step files
- Do not modify existing content in shape.md — append only

---

## Self-Cleanup Instruction

After successfully completing the plan execution:

- If all tasks are completed and plan is closed → Delete this handoff file
- If execution pauses and will continue later → Update this handoff or create a new one for the next agent

---

## References

| Reference | Purpose |
|-----------|---------|
| `_bmad/rbtv/workflows/build-rbtv-component/data/bmad-architecture.md` | BMAD component architecture guide |
| `.cursor/rules/jobs/guardrails/plan-creation.mdc` | Plan creation guardrails |
| `_bmad-output/planning-artifacts/plan-ecosystem-improvements/` | Legacy documents reviewed (to be deleted after plan execution) |
