# Shape Template

Universal template for `shape.md` companion files. Captures shaping decisions and accumulates execution context across any workflow or freeform session.

---

## Naming Convention

| Context | Filename |
|---------|----------|
| Plan workflow | `shape.md` (in plan folder) |
| Workflow with named output | `{output-name}-shape.md` (alongside primary output) |
| Freeform session | `{YYYY-MM-DD}-{topic}-shape.md` (in output folder) |

---

## Template

```markdown
# Shape - {Name}

> **Purpose:** This document captures shaping decisions and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping

### Scope Definition

**What this accomplishes:**
- {Primary goal}
- {Secondary goal}

**What this does NOT include:**
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

### User Inputs

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | {Topic} | "{User's words}" | {How this shaped the output} |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | {Topic} | {What user proposed} | {What AI suggested} | {Final choice and why} |

---

<!-- CONDITIONAL: Include this section only for plan workflows -->
<!-- BEGIN PLAN-SPECIFIC -->
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
| Complex validation | Subagent | quality-review needs focused evaluation |
| Quick lookup | Skill | Minimal overhead |
| Already in subagent | Skill only | Subagents cannot nest |
<!-- END PLAN-SPECIFIC -->

---

## Decisions and Discoveries

> **APPEND-ONLY RULES:**
> 1. Only capture decisions, discoveries, and unexpected constraints — NOT routine task completions
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Ask yourself: "Will this matter in one month?" If no, don't log it
>
> **What belongs here:** Decisions made during execution (with rationale), discoveries that change prior decisions, unexpected constraints
> **What does NOT belong:** Routine task completions ("created file X", "updated config Y")

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
| {Path} | {Why needed} | {Task ID or session topic} |
```

---

## Usage Instructions

### Creating shape.md

1. Fill Original Shaping from user discussions and context gathered
2. Include plan-specific sections (Standards Applied, Tool Mode Selection) only for plan workflows — omit for freeform sessions
3. Leave Decisions and Discoveries empty (template markers only)

### During Execution

1. **Before each task:** Read Decisions and Discoveries for prior context
2. **On significant decision:** Append a decision entry (only if it matters in one month)
3. **On discovery that changes prior work:** Append a discovery entry with propagation record
4. **NEVER** modify Original Shaping or previous entries
5. **NEVER** defer writes to session end — write same turn as context emerges

### Append-Only Enforcement

| Purpose | Why |
|---------|-----|
| Audit trail | Full history of significant decisions |
| Context recovery | Any agent can understand execution state |
| No condensation needed | Eliminates condensation tasks |
| Immutable planning record | Original decisions preserved for comparison |

---

## Size Guidelines

| Section | Target | Max |
|---------|--------|-----|
| Original Shaping | 50-100 lines | 150 lines |
| Standards Applied (plan only) | 30-50 lines | 80 lines |
| Per decision entry | 6-8 lines | 12 lines |
| Per discovery entry | 15-25 lines | 35 lines |
