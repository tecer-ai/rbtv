---
name: {plan-name}
overview: "{One-sentence summary of what this plan accomplishes}"
---

# {Plan Name}

> Read `shape.md` for full context, decisions, and constraints.
> Task files (`→ path`) contain per-task execution instructions.

## Architectural Constraints

Patterns and principles that MUST be followed during execution.

| Principle | Enforcement |
|-----------|-------------|
| {Plan-specific pattern} | {How violations are detected} |

**Execution Rules:**
1. Read shape.md before starting any task
2. One task in progress at a time
3. Dependencies are sacred — never skip prerequisite tasks
4. Checkpoints: evaluate work against review criteria in checkpoint task file, present findings, HALT for human approval
5. Append to shape.md after each task — never modify previous entries
6. Internal links use file-relative paths (`./`, `../`); external links use project-root-relative paths

## Revolving Plan Rules

- Simple discovery (<5 min): resolve immediately, document in shape.md
- Complex discovery: add new task to plan, document in shape.md, notify user

## Execution Workflow

{Mermaid diagram — ONLY if plan has branching or parallel phases. Omit for linear sequential plans.}

## Tasks

### Phase 1: {Phase Name} — {Goal}

- [ ] `p1-1` {Complex task description} → `phase-1/p1-1.task.md`
- [ ] `p1-2` {Simple task description}
- [ ] `p1-checkpoint` **CHECKPOINT** — {What to verify} → `phase-1/p1-checkpoint.task.md`

### Phase 2: {Phase Name} — {Goal}

- [ ] `p2-1` {Task description} → `phase-2/p2-1.task.md`
- [ ] `p2-checkpoint` **CHECKPOINT** — {What to verify} → `phase-2/p2-checkpoint.task.md`

### Final Phase: Validation and Completion

- [ ] `pN-refs` Verify all internal links resolve and comply with Plan Linking Standard
- [ ] `pN-compound` Process learnings.md entries into system improvements
- [ ] `pN-checkpoint` **FINAL CHECKPOINT** — User approval to complete plan → `phase-N/pN-checkpoint.task.md`
