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

---

## Decisions and Discoveries

> **APPEND-ONLY RULES:**
> 1. Only capture decisions, discoveries, and unexpected constraints — NOT routine task completions
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Ask yourself: "Will this matter to a future agent executing this plan?" If no, don't log it. Shape's audience is in-flight executors — not post-mortem readers. (`learnings.md` is for META-learnings about the BMAD/RBTV system itself, not project post-mortems.)
>
> **What belongs here:** Decisions made during execution that change the plan or its direction, discoveries that contradict prior decisions, unexpected constraints future executors must know
> **What does NOT belong:** Routine task completions ("created file X", "updated config Y"), per-task outcome tables, file lists, commit hashes, "Phase N batch complete" summaries — orchestration state lives in `orchestration-state.md` (created and overwritten by the orchestrator), not here

### Decision Entry Format

\`\`\`markdown
### Decision [N] (from task [id])
**Date:** YYYY-MM-DD
**Decision:** [What was decided]
**Rationale:** [Why this choice was made]
**Impact:** [What tasks or files are affected]
\`\`\`

### Discovery Entry Format

\`\`\`markdown
### Discovery [N] (from task [id])
**Date:** YYYY-MM-DD
**Finding:** [What was discovered]
**Contradicts:** [Reference to original shaping section, if any]
**Resolution:**
- [ ] Simple fix applied immediately
- [ ] New task added: [task-id]

**Propagation Checklist:**
| Status | Task/File | Action Taken |
|--------|-----------|--------------|
| Completed | [task-id or file path] | Annotated with "⛔ SUPERSEDED — See Discovery N" |
| Pending | [task-id or file path] | Updated to reflect new decision |

**Details:** [Explanation]
\`\`\`

> **PROPAGATION IS MANDATORY:** When a discovery changes a prior decision, the agent MUST:
> 1. Annotate all affected **completed** tasks/files with "⛔ SUPERSEDED — See Discovery N" (do not modify the original content; append annotation)
> 2. Update all affected **pending** tasks to reflect the new decision
> 3. Fill in the Propagation Checklist above to record what was done

<!-- Decisions and discovery entries will be appended below this line -->

---

## References

> **Path format:** External files (outside this plan folder) use project-root-relative paths. Internal files (within this plan folder) use file-relative paths (`./`, `../`).

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

1. Create during plan creation (step-04)
2. Fill Original Shaping section from user discussions
3. Fill Standards Applied from applicable BMAD/RBTV rules
4. Leave Decisions and Discoveries section empty (template markers only)

### During Execution

1. **Before each task:** Read Decisions and Discoveries for prior context
2. **On significant decision:** Append a Decision entry — only if it passes the audience criterion in the APPEND-ONLY RULES (template body above)
3. **On discovery that changes prior work:** Append a Discovery entry AND complete the Propagation Checklist
4. **NEVER:** Modify Original Shaping or previous entries

### Discovery Propagation Protocol

When a Discovery contradicts or supersedes a prior decision:

1. **Document the discovery** in the Decisions and Discoveries section
2. **Annotate completed tasks/files** affected by the change with "⛔ SUPERSEDED — See Discovery N" (append; do not modify original content)
3. **Update pending tasks** affected by the change to reflect the new decision
4. **Fill in the Propagation Checklist** in the discovery entry to record what was propagated

### Append-Only Enforcement

The append-only pattern serves critical purposes:

| Purpose | Why |
|---------|-----|
| Audit trail | Full history of significant decisions |
| Context recovery | Any agent can understand execution state |
| Immutable planning record | Original decisions preserved for comparison |
| Propagation record | Discovery checklist tracks what was updated |

---

## Size Guidelines

| Section | Target | Max |
|---------|--------|-----|
| Original Shaping | 50-100 lines | 150 lines |
| Standards Applied | 30-50 lines | 80 lines |
| Per decision entry | 6-8 lines | 12 lines |
| Per discovery entry (with propagation) | 15-25 lines | 35 lines |

**Note:** Shape.md grows during execution ONLY through Decision and Discovery entries that pass the APPEND-ONLY RULES audience criterion. Growth from per-task outcomes, file lists, commit hashes, or batch-completion summaries indicates misuse — orchestration state belongs in `orchestration-state.md`, not here.
