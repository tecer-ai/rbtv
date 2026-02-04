---
name: {plan-name}
overview: "{One-sentence summary of what this plan accomplishes}"
todos:
  - id: p1-1
    content: "p1-1: Create plan folder and initial execution decisions file"
    status: pending
  # Phase 1 tasks
  - id: p1-2
    content: "p1-2: {Task description}"
    status: pending
  - id: p1-checkpoint
    content: "P1 CHECKPOINT - {Phase 1 checkpoint description}"
    status: pending
  # Phase 2 tasks
  - id: p2-1
    content: "p2-1: {Task description}"
    status: pending
  - id: p2-checkpoint
    content: "P2 CHECKPOINT - {Phase 2 checkpoint description}"
    status: pending
  # Final phase tasks
  - id: pN-condensation
    content: "pN-condensation: Phase condensation - merge all execution decisions"
    status: pending
  - id: pN-refs
    content: "pN-refs: File reference review - verify all internal links"
    status: pending
  - id: pN-final
    content: "pN-final: Final condensation"
    status: pending
  - id: pN-checkpoint
    content: "PN FINAL CHECKPOINT - User approval to complete plan"
    status: pending
isProject: false
---

# {Plan Name}

## Context

### Problem Statement

{What problem does this solve? Describe the current state and desired state.}

### User Goals

1. {Goal 1}
2. {Goal 2}
3. {Goal 3}

### Constraints

- {Constraint 1}
- {Constraint 2}

### Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| {What was decided} | {Choice made} | {Why} |

### Rejected Alternatives

- {Alternative 1}: {Why rejected}
- {Alternative 2}: {Why rejected}

---

## Architectural Constraints

Patterns and principles that MUST be followed during execution.

| Principle | Implementation | Enforcement |
|-----------|----------------|-------------|
| {Pattern name} | {How to apply in this plan} | {How violations are detected} |
| {Coding standard} | {Specific application} | {Review criteria} |
| {Design pattern} | {Where/how to use} | {What breaks if ignored} |

**Inviolable Rules:**
1. Read all prior execution decisions before starting any task
2. Only one task `in_progress` at a time
3. Dependencies are sacred — never skip prerequisite tasks
4. Checkpoints require human approval — never auto-continue

---

## Files to Load

| File | Purpose | When to Load |
|------|---------|--------------|
| {path} | {Why this file matters} | {Phase/task that needs it} |

---

## Execution Workflow

```mermaid
flowchart TD
    subgraph P1[Phase 1: Name]
        p1-1[p1-1: Create plan folder]
        p1-2[p1-2: Task]
        p1-chk{P1 Checkpoint}
    end
    
    subgraph P2[Phase 2: Name]
        p2-1[p2-1: Task]
        p2-chk{P2 Checkpoint}
    end
    
    subgraph Final[Final Phase]
        pn-cond[Condensation]
        pn-refs[Reference Review]
        pn-final[Final Condensation]
        pn-chk{Final Checkpoint}
    end
    
    p1-1 --> p1-2 --> p1-chk
    p1-chk --> p2-1 --> p2-chk
    p2-chk --> pn-cond --> pn-refs --> pn-final --> pn-chk
```

---

## Phase 1: {Phase Name}

**Goal:** {What this phase accomplishes}

### Tasks

- `p1-1`: Create plan folder and initial execution decisions file
- `p1-2`: {Task description}
- `p1-checkpoint`: **P1 CHECKPOINT** - {Checkpoint description}

---

## Phase 2: {Phase Name}

**Goal:** {What this phase accomplishes}

### Tasks

- `p2-1`: {Task description}
- `p2-checkpoint`: **P2 CHECKPOINT** - {Checkpoint description}

---

## Final Phase: Validation and Cleanup

**Goal:** Condense execution logs, verify references, complete plan.

### Tasks

- `pN-condensation`: Phase condensation - merge all execution decisions into single file
- `pN-refs`: File reference review - verify all internal markdown links resolve
- `pN-final`: Final condensation
- `pN-checkpoint`: **FINAL CHECKPOINT** - User approval to complete plan

---

## Notes

{Any additional notes or context for executing agents}
