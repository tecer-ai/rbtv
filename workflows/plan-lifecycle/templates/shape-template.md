# Shape Template

Use this template to create the `shape.md` companion file for each plan. Shape captures planning decisions and accumulates execution context.

---

## Template

```markdown
# Shape - {Plan Name}

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- {Primary goal}
- {Secondary goal}
- {Additional goals}

**What this plan does NOT include:**
- {Explicit exclusion}
- {Out of scope item}

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| {What was decided} | {Choice made} | {Why this choice} |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| {Limitation} | {Where it comes from} | {How it affects execution} |

### User Inputs (Maintained and Developed)

> **Purpose:** Capture all user requirements and comments that were maintained and developed into the plan. This enables another agent to understand the user's intent and how it was translated into concrete plan elements.

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | {Topic} | "{User's exact words or paraphrase}" | {How this input shaped the plan — specific tasks, constraints, or decisions} |

### Collaborative Decisions

> **Purpose:** Capture decisions made together with the AI agent that helped shape the plan. This prevents re-deciding settled matters and provides rationale for plan structure.

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | {Decision topic} | {What user proposed or requested} | {What AI suggested, refined, or added} | {Final choice and why} |

---

## Standards Applied

### {Standard Category} Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| {Standard name} | {How it applies} |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| {Rule name} | {How violations are detected} |

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

> **APPEND-ONLY RULES:**
> 1. After completing each task, append an entry below
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Use the exact format shown

### Entry Format

\`\`\`markdown
### Task [id]: [Title]
**Completed:** YYYY-MM-DD
**Outcome:** [Brief summary of what was delivered]
**Decisions:**
- [Decision]: [Rationale]
**Issues:** [Any blockers or surprises encountered]
**Files Modified:** [List of files created/updated/deleted]
\`\`\`

<!-- Execution entries will be appended below this line -->

---

## Execution Discoveries

> **DISCOVERY RULES:**
> 1. When execution reveals contradictions or unforeseen work, append entry
> 2. If work is simple (<5 min), do it immediately and mark checkbox
> 3. If work is complex, add new task to plan and note the task ID
> 4. NEVER modify Original Shaping - discoveries explain divergence

### Entry Format

\`\`\`markdown
### Discovery [N] (from task [id])
**Date:** YYYY-MM-DD
**Finding:** [What was discovered]
**Contradicts:** [Reference to original shaping section, if any]
**Resolution:**
- [ ] Simple fix applied immediately
- [ ] New task added: [task-id]
**Details:** [Explanation]
\`\`\`

<!-- Discovery entries will be appended below this line -->

---

## References

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| {Document path} | {What was learned} |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| {Path} | {Why needed} | {Task ID} |
```

---

## Usage Instructions

### Creating shape.md

1. Create during plan creation (step-02-context.md)
2. Fill Original Shaping section from user discussions
3. Fill Standards Applied from applicable BMAD/RBTV rules
4. Leave Execution Log and Discoveries sections empty (template markers only)

### During Execution

1. **Before each task:** Read Execution Log for prior context
2. **After each task:** Append entry to Execution Log
3. **On discovery:** Append entry to Execution Discoveries
4. **NEVER:** Modify Original Shaping or previous entries

### Append-Only Enforcement

The append-only pattern serves critical purposes:

| Purpose | Why |
|---------|-----|
| Audit trail | Full history of execution decisions |
| Context recovery | Any agent can understand execution state |
| No condensation needed | Eliminates condensation tasks from plans |
| Immutable planning record | Original decisions preserved for comparison |

---

## Size Guidelines

| Section | Target | Max |
|---------|--------|-----|
| Original Shaping | 50-100 lines | 150 lines |
| Standards Applied | 30-50 lines | 80 lines |
| Per execution entry | 8-12 lines | 20 lines |
| Per discovery entry | 10-15 lines | 25 lines |

**Note:** Shape.md will grow during execution. This is expected and intentional.
