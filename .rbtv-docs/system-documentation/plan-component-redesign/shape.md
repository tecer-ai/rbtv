# Shape - Plan Ecosystem Redesign

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Redesign the RBTV plan ecosystem to be self-executing (no separate execution workflow)
- Implement micro-step task files with complete execution instructions per task
- Unify tool access patterns so AI agents have the same tools as humans (command/skill/subagent parity)
- Establish append-only execution logging in shape.md (eliminating condensation)
- Capture system improvement learnings for BMAD/RBTV evolution

**What this plan does NOT include:**
- Changes to non-RBTV BMAD modules (bmm, bmb, tea, cis)
- Changes to the core BMAD config or installer
- Implementation of the plan template instantiation (founder patterns)
- Migration of existing plans to new format

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Execution workflow | Eliminated | Plans become self-executing via micro-step files; reduces complexity and context overhead |
| Context logging | Append-only shape.md | Eliminates condensation tasks; single file for all execution context |
| Tool access parity | All 3 entry points required | AI agents (skills/subagents) must have same capabilities as humans (commands) |
| Micro-step file naming | `plan-task-microstep-template.md` | Differentiates from other potential microstep templates in the system |
| Learnings purpose | System improvement only | Not for project-specific learnings; captures meta-learnings about BMAD/RBTV |
| Task sequential execution | No parallelization | Tasks execute one at a time, but can share context window when grouped |
| Checkpoint files | No micro-step files | Checkpoints are simple pause points, not work items |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Micro-file architecture | BMAD principle | Each file under 200 lines; split if larger |
| Thin loader pattern | BMAD principle | Entry points contain zero logic, only load instructions |
| Sequential enforcement | BMAD principle | Explicit halt instructions to prevent AI optimization/skipping |
| Append-only shape | User requirement | Never modify original shaping; always append new sections |
| Same context execution | User requirement | Skills execute in same context window; subagents in new context |
| Subagent nesting prohibited | User requirement | Subagents cannot invoke other subagents; only skills |

### User Inputs Captured

**Tool inventory requirement:**
> "Every workflow that currently has a command entrypoint must also have a skill and sub agent entry point... the names of the entry points must be the same... this is what I meant when I said that the AI agents (skill and sub agents) must have the same tools as humans (commands)"

**Learnings purpose:**
> "Learnings.md makes it clear that its purpose is not to capture the learnings of the specific plan execution, but to capture learnings of how BMAD or RBTV could be improved given user corrections, suggestions and guidance"

**Revolving plan behavior:**
> "Update shape (appending, never updating old content) and, what is added to the plan, is the task to work on new documents/references not foreseen during the plan creation (only if this new work is complex - if work is simple, it is performed right away). This means the plan is revolving and reshaping itself while it is executed"

**Task change notification:**
> "In the output message to the user, the agent must make very clear what he has changed" (when tasks are added or removed)

---

## Standards Applied

### BMAD Architecture Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Micro-file architecture | All new templates under 200 lines; thin loaders under 20 lines |
| Text files are the runtime | Templates contain explicit instructions AI will follow literally |
| Sequential enforcement | Step files include explicit STOP/WAIT instructions |
| Configuration over hardcoding | Use `{project-root}` variables in all paths |
| Persona-driven interaction | Not applicable (no new agents in this plan) |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| WHAT not HOW | Task descriptions state outcomes, not implementation steps |
| Single action per task | Each todo is one discrete, completable action |
| Explicit file operations | All file tasks use CREATE/UPDATE/DELETE/MOVE verbs |
| Zero-context plans | Plan is self-contained; no references to "as discussed" |
| Dependency ordering | CREATE before UPDATE; no circular dependencies |

### Tool Mode Selection

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior context | Skill | Preserves conversation history |
| Context saturated | Subagent | Fresh context window |
| Complex validation | Subagent | Judge needs focused evaluation |
| Quick lookup | Skill | Minimal overhead |
| Already in subagent | Skill only | Subagents cannot nest |

---

## Execution Log

> **Instructions:** After completing each task, append an entry below using this format. Never modify previous entries.

```markdown
### Task [id]: [Title]
**Completed:** YYYY-MM-DD
**Outcome:** [Brief summary of what was delivered]
**Decisions:**
- [Decision]: [Rationale]
**Issues:** [Any blockers or surprises encountered]
**Files Modified:** [List of files created/updated/deleted]
```

<!-- Execution entries will be appended below this line -->

---

## Execution Discoveries

> **Instructions:** When execution reveals something that contradicts original shaping or requires unforeseen work, append an entry below. If work is simple (<5 min), do it immediately. If complex, add a new task to the plan.

```markdown
### Discovery [N] (from task [id])
**Date:** YYYY-MM-DD
**Finding:** [What was discovered]
**Contradicts:** [Reference to original shaping section, if any]
**Resolution:**
- [ ] Simple fix applied immediately
- [ ] New task added: [task-id]
**Details:** [Explanation]
```

<!-- Discovery entries will be appended below this line -->

---

## References

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `plan_abstraction.md` | 3-component plan system, task metadata schema, context levels |
| `plan_execution.md` | 3-step guardrail, judge retry logic, execution decisions format |
| `plan_evolution_and_execution_optimization.md` | Revolving plan pattern, dependency-first ordering |
| `handoff_planning_workflow_adjustments.md` | Plan development vs execution handoffs, iteration cycle |
| `todo-context-optimization.md` | Spec artifacts pattern, workflow I/O contracts |
| `todo-founder-template-plans.md` | Template→Instance model, framework reference separation |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `_bmad/rbtv/workflows/build-rbtv-component/templates/ide-command-template.md` | Template for creating command thin loaders | Task 1.4 |
| `_bmad/rbtv/workflows/build-rbtv-component/templates/task-template.md` | Reference for task file structure | Task 2.1 |
| `.cursor/skills/bmad-rbtv-web-research/SKILL.md` | Example skill thin loader format | Task 1.2 |
| `.cursor/agents/bmad-rbtv-context-search.md` | Example subagent thin loader format | Task 1.3 |
| `_bmad/rbtv/workflows/plan-lifecycle/workflow.md` | Current workflow to update | Task 4.1 |
| `_bmad/rbtv/workflows/plan-lifecycle/data/plan-creation-rules.md` | Current rules to update | Task 3.1 |
