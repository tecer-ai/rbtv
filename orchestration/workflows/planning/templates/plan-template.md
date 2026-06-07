---
name: {plan-name}
overview: "{One-sentence summary of what this plan accomplishes}"
---

# {Plan Name}

> Read `decisions.md` for full context, decisions, and constraints.
> Read `./deliverables.md` for the artifact index — where every task lands its output.
> Task files (`→ path`) contain per-task execution instructions.

## Architectural Constraints

Patterns and principles that MUST be followed during execution.

| Principle | Enforcement |
|-----------|-------------|
| {Plan-specific pattern} | {How violations are detected} |

**Execution Rules:**
1. Read ./deliverables.md before starting any task — it tells you the exact path your output must land at
2. Update ./deliverables.md after delivering — flip your task's Status, confirm the Path matches what you produced
3. Read decisions.md before starting any task
4. One task in progress at a time
5. Dependencies are sacred — never skip prerequisite tasks
6. Checkpoints: evaluate work against review criteria in checkpoint task file, present findings, HALT for human approval
7. decisions.md is append-only and reserved for Decision/Discovery entries per the decisions template — executors follow the executor-prompt's decisions rule (the live, canonical source) for the binding constraint at dispatch time. Never modify previous decisions entries.
8. Internal links use file-relative paths (`./`, `../`); external links use project-root-relative paths

## Revolving Plan Rules

- Simple discovery (<5 min): resolve immediately, document in decisions.md
- Complex discovery: add new task to plan, document in decisions.md, notify user

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
