---
name: {plan-name}
overview: "{One-sentence summary of what this plan accomplishes}"
todos:
  # Phase 1 tasks
  - id: p1-1
    content: "p1-1: {Complex task description}"
    taskFile: "phase-1/p1-1.task.md"
    status: pending
  - id: p1-2
    content: "p1-2: {Simple task description}"
    # inline — no micro-step file
    status: pending
  - id: p1-checkpoint
    content: "P1 CHECKPOINT - {Phase 1 checkpoint description}"
    status: pending
  # Phase 2 tasks
  - id: p2-1
    content: "p2-1: {Task description}"
    taskFile: "phase-2/p2-1.task.md"
    status: pending
  - id: p2-checkpoint
    content: "P2 CHECKPOINT - {Phase 2 checkpoint description}"
    status: pending
  # Final phase tasks
  - id: pN-refs
    content: "pN-refs: File reference review - verify all internal links"
    status: pending
  - id: pN-compound
    content: "pN-compound: Compound learnings - process learnings.md entries"
    status: pending
  - id: pN-checkpoint
    content: "PN FINAL CHECKPOINT - User approval to complete plan"
    status: pending
isProject: false
---

# {Plan Name}

> Read `shape.md` for full context, decisions, and constraints.
> Read individual `.task.md` files (referenced via `taskFile`) for per-task execution instructions.

## Architectural Constraints

Patterns and principles that MUST be followed during execution.

| Principle | Enforcement |
|-----------|-------------|
| {Plan-specific pattern} | {How violations are detected} |

**Inviolable Rules:**
1. Read shape.md execution log before starting any task
2. Only one task `in_progress` at a time
3. Dependencies are sacred — never skip prerequisite tasks
4. Checkpoints require quality-review subagent execution before user-facing gate decision — never skip the review
5. Checkpoints require human approval — never auto-continue, even after `APPROVED` verdict
6. `REJECTED` checkpoints cannot advance — address feedback before re-evaluation
7. Append to shape.md after each task — never modify previous entries
8. Internal links use file-relative paths (`./`, `../`); external links use project-root-relative paths — see Plan Linking Standard

## Checkpoint Execution Protocol

Every checkpoint has a **"Checkpoint Review Prompt"** subsection in its phase body (marked with `####` heading and a blockquote containing the full prompt). At each checkpoint:

1. Locate the checkpoint's review prompt in the phase body section (e.g. "P1 Checkpoint Review Prompt")
2. Fire Task tool with `subagent_type='quality-review'`, passing the blockquoted prompt content
3. Present the `APPROVED` / `REJECTED` verdict to user
4. **HALT for human approval regardless of verdict**
5. If `REJECTED`, do not advance to the next phase — address feedback first

**Why body, not YAML:** Cursor's plan YAML serializer only preserves `id`, `content`, and `status` on todo items. Custom fields are silently stripped when the executor updates task status.

## Revolving Plan Rules

- Simple discovery (<5 min): resolve immediately, document in shape.md
- Complex discovery: add new task to plan, document in shape.md, notify user

## Execution Workflow

{Mermaid diagram — ONLY if plan has branching or parallel phases. Omit for linear sequential plans.}

## Phase 1: {Phase Name}

**Goal:** {What this phase accomplishes}

#### P1 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> {Summary of phase 1 deliverables — files created/modified, artifacts produced, with specific paths}
>
> ## Quality Criteria
> 1. {Criterion derived from phase 1 task acceptance criteria}
> 2. {Criterion derived from phase 1 task acceptance criteria}
> 3. {Criterion derived from architectural constraints}

## Phase 2: {Phase Name}

**Goal:** {What this phase accomplishes}

#### P2 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> {Summary of phase 2 deliverables}
>
> ## Quality Criteria
> 1. {Criterion from phase 2 tasks}
> 2. {Criterion from phase 2 tasks}

## Final Phase: Validation and Completion

**Goal:** Verify references, compound learnings, complete plan.

#### PN Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> {Summary of all plan deliverables across all phases}
>
> ## Quality Criteria
> 1. All internal markdown links resolve correctly
> 2. Learnings have been compounded into actionable system improvements
> 3. {Plan-wide quality criterion}
