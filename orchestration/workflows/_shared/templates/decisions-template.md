# Decisions Template

Universal template for `decisions.md` companion files. Captures shaping decisions, discoveries, constraints, and references that future agents need.

---

## Naming Convention

| Context | Filename |
|---------|----------|
| Plan workflow | `decisions.md` (in plan folder) |
| Workflow with named output | `{output-name}-decisions.md` (alongside primary output) |
| Freeform session | `{YYYY-MM-DD}-{topic}-decisions.md` (in output folder) |

---

## Template

```markdown
# Decisions - {Name}

> **Purpose:** This document captures shaping decisions, discoveries, constraints, and references that future agents need. The Original Shaping section is immutable. Other sections are append-only during routine execution.

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

## Entry-Shape Discipline (HARD TEXT — enforced)

`decisions.md` is the WORKER-FACING file: workers read it (alongside their own task file) to pick up decisions, discoveries, and errata that affect future work. It carries SIGNAL that changes future work — never an execution log. These rules bind every entry; the canonical single source is `{rbtv_path}/orchestration/workflows/_shared/authoring/decisions-discipline.md`.

| Rule | Statement |
|------|-----------|
| Decision / rationale / scope only | Each entry carries exactly three things: the decision, its rationale, and its scope (which queued work it affects). Nothing else. |
| Never file-lists | An entry NEVER enumerates files changed. Files-changed is audit-log content, not decision content. |
| Never N→M narratives | An entry NEVER narrates a count change ("went from 4 files to 3", "merged 12 rows into 5"). The decision and its rationale carry the meaning; the arithmetic is noise. |
| UPDATE, not REWRITE | When a later decision changes an earlier one, APPEND an entry that supersedes it — never rewrite or delete the earlier entry. The append-only history is the audit trail. |
| Routine completions excluded | "Created file X", "updated config Y" never belong here. Ask: will this change future work in one month? If no, it does not go in `decisions.md`. |

**Size floor on rewrites.** Routine maintenance is append-only — a full-file rewrite is NOT a routine operation. If a rewrite is ever genuinely needed, it requires explicit user sanction AND MUST preserve at least 50% of the prior file's size. A rewrite that drops below the ≥50% floor is presumed to have discarded signal — it is rejected, and the original is kept. Decisions, findings, constraints, unresolved questions, and required references must all survive any rewrite.

**Reminder line** (generated plans and task files carry this verbatim):

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

---

## Usage Instructions

### Creating decisions.md

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
| Decision audit | Significant decisions retain their rationale |
| Context recovery | Any agent can understand execution-shaping context |
| Low-noise continuity | Routine work logs stay out of the decisions document |
| Immutable planning record | Original decisions preserved for comparison |

---

## Size Guidelines

| Section | Target | Max |
|---------|--------|-----|
| Original Shaping | 50-100 lines | 150 lines |
| Standards Applied (plan only) | 30-50 lines | 80 lines |
| Per decision entry | 6-8 lines | 12 lines |
| Per discovery entry | 15-25 lines | 35 lines |
