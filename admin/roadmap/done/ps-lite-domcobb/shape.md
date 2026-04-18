# Shape - PS Lite Dom Cobb

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Adds a [PL] PS Lite menu item to Dom Cobb for lightweight, conversational problem structuring
- Implements Socratic questioning that organically introduces structure as complexity emerges
- Provides escalation path to [PS] when problems exceed conversational scope
- Resolves simple problems in 2-3 exchanges with a clean problem statement and next steps

**What this plan does NOT include:**
- Changes to other agents (PS Lite is Dom Cobb-specific)
- Modifications to the existing [PS] Problem Structuring workflow
- New workflow files or task files (implementation is inline in agent file)
- Changes to any configuration or installer files

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Implementation approach | Inline `<action>` in agent file | Fastest to reach, no file loading overhead, stays in Dom Cobb's context |
| Menu position | [PL] between [PS] and [PV] | Logical grouping — lightweight variant next to its full counterpart |
| Escalation mechanism | Context transfer to [PS] via exec handler | No new infrastructure needed; conversation history carries context |
| Action behavior | Conversational Socratic loop with complexity monitoring | Matches Dom Cobb's persona; avoids framework jargon upfront |
| Line budget | Allow exceeding 100-line agent max by 15-20 lines | User-approved relaxation of component pattern rule |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Inline action (not a workflow) | Compound PRD | Express mode must be fast; workflow overhead defeats the purpose |
| Persona consistency | Compound PRD | All PS Lite output must maintain Socratic, structured, warm tone |
| No duplication with [PS] | Compound PRD | PS Lite is entry point only; escalates when frameworks are needed |
| Agent file ~110 lines max | User-approved relaxation | Action block must be compact (~15-20 lines) |

### User Inputs (Maintained and Developed)

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Line budget relaxation | "It is okay to surpass 100 lines (and include 15-20 lines)." | Constraint allowing agent file to grow to ~110 lines for PS Lite addition |
| 2 | Original requirement | "PS but simpler. Not necessarily following the frameworks, and only do so if it gets more complex." (from shape.md of agent-general-help-modes plan) | Core PS Lite concept: conversational first, frameworks only on escalation |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Agent file line limit | User relaxed the 100-line max | AI flagged the tension: 90 existing lines + 15-20 new = over limit | User confirmed exceeding 100 is acceptable for this addition |

---

## Standards Applied

### RBTV Component Pattern Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Agent XML-in-markdown structure | Action block follows `<action id="...">` pattern |
| Menu item format | `<item cmd="..." action="...">` with fuzzy match triggers |
| Config loading in activation | Already present; no changes needed |
| WAIT instruction in menu | Already present; no changes needed |
| `{project-root}` path variables | Preserved in all file references |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Persona consistency | Action prompt must use Socratic questioning style matching existing persona |
| No framework jargon in PS Lite | Escalation triggers define when to introduce frameworks via [PS] |
| Context transfer on escalation | Prompt must instruct agent to carry conversation context to [PS] workflow |

### Tool Mode Selection

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior context | Skill | Preserves conversation history |
| Context saturated | Subagent | Fresh context window |
| Complex validation | Subagent | quality-review needs focused evaluation |
| Quick lookup | Skill | Minimal overhead |
| Already in subagent | Skill only | Subagents cannot nest |

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

### Entry 1 — Plan status discrepancy (p1-1, p1-2, p1-checkpoint)

**Type:** Discovery
**Context:** Tasks p1-1, p1-2, and p1-checkpoint were marked `completed` in YAML frontmatter, but agents/domcobb.md had no PS Lite content (still 90 lines, original state). Shape.md had no execution entries.
**Decision:** Re-executed all three tasks from scratch. Prior status was erroneous — likely from a failed previous session that updated YAML but didn't persist file changes.
**Impact:** None — work now completed correctly.

### Entry 2 — PS Lite action block design (p1-1)

**Type:** Decision
**Context:** Designed the `<action id="ps-lite">` block to fit ~19 lines: 4-step instruction (OPEN → CONVERSATION LOOP → ESCALATION → SIMPLE RESOLUTION). Escalation triggers consolidated into a single line with pipe separators to keep the block compact.
**Decision:** Used inline escalation trigger list (pipe-separated) instead of bullet list to save 3 lines.
**Rationale:** Agent file ended at 110 lines — well within the user-approved 15-20 line addition budget.

### Entry 3 — P1 Checkpoint result (initial)

**Type:** Decision
**Context:** Verified all 7 acceptance criteria from compound PRD. All pass. Line count is 110 (exceeds 100-line default but within approved relaxation).
**Decision:** P1 approved. Ready for Phase 2.

### Entry 4 — User override: inline action → workflow (post-P1)

**Type:** Decision (user-directed)
**Context:** User reviewed the inline `<action>` implementation and requested PS Lite follow the same format as other menu items — meaning a proper workflow file loaded via `exec=`, not an inline action.
**Decision:** Replaced inline `<action id="ps-lite">` with `workflows/ps-lite/workflow.md` + `steps-c/step-01-converse.md`. Menu item changed from `action="ps-lite"` to `exec="{project-root}/workflows/ps-lite/workflow.md"`. Agent file dropped from 110 to 91 lines (back under 100-line limit — no exception needed).
**Impact:** Overrides compound PRD decision "inline action" and plan shape decision "fastest to reach, no file loading overhead." User values structural consistency over latency optimization. All 7 acceptance criteria re-verified — still pass.

---

## References

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `_admin/roadmap/todos/compound-ps-lite-domcobb.md` | Complete specification: problem, goals, implementation details, acceptance criteria |
| `agents/domcobb.md` | Current agent structure (90 lines), menu layout, persona definition |
| `.cursor/plans/agent-general-help-modes/agent-general-help-modes.plan.md` | Original combined plan that PS Lite was separated from |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `agents/domcobb.md` | Target file for modification | p1-1, p1-2 |
| `_admin/roadmap/todos/compound-ps-lite-domcobb.md` | Complete behavior specification | p1-1 |
| `workflows/problem-structuring/workflow.md` | Understand [PS] entry point for escalation design | p1-1 |
