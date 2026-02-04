# Plan Execution

**Type:** Architecture  
**Date:** 2026-01-29  
**Conversation:** Generic agent workflow for plan execution with judge quality gate and execution decisions logging for institutional memory.

---

## 1. Overview

**Purpose:** Enable any agent to execute plan tasks with quality verification and persistent institutional memory across agents and sessions.

**Implementation Status:** ✅ **Complete** - Judge agent implemented, execution protocol documented, workflow operational.

**Scope:**
- **Included:** Generic agent execution protocol, judge quality gate, execution decisions logging, condensation workflow, error handling
- **Excluded:** Plan creation (covered by `/plan` command), automatic invocation mechanisms, specific agent implementations

**Success Metrics:**
- ✅ Any agent can execute plan tasks following documented protocol
- ✅ Judge provides independent quality verification
- ✅ Execution decisions preserve institutional memory
- ✅ Different agents can continue execution with full context via logs
- ✅ Logs are condensed at phase and plan completion to maintain clean structure

---

## 2. System Architecture

### High-Level Design

Any agent executing plan tasks follows a **three-step protocol**: read execution decisions for context, execute the work, and invoke judge for quality verification before marking complete. Execution decisions are written after final approval or maximum retry attempts.

![Diagram 01](plan_execution_mmdc/diagram_01.png)

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| **Judge** | Independent evaluator for work quality; invoked by any agent or user | `.cursor/agents/judge.md` |
| **Execution decisions logs** | Persistent institutional memory of key decisions and outcomes | `.cursor/plans/[plan-name]/` |

### The Three-Step Protocol

Any agent executing plan tasks must follow this protocol:

| Step | Action |
|------|--------|
| 1. Before starting | Read all `*_execution_decisions.md` files in plan folder for context |
| 2. Before marking complete | Invoke judge with context (plan file path, task description) |
| 3. After final approval OR max attempts | Write `[task_id]_execution_decisions.md` with key decisions and outcome |

---

## 3. Design Decisions

### Decision: Remove Orchestrator Layer

**Status:** Approved  
**Context:** The orchestrator-executor-judge system added complexity without sufficient value. The orchestrator layer coordinated work that agents can handle directly.

**Decision:** Delete orchestrator agent. Agents execute tasks directly following a documented three-step protocol.

**Rationale:**
- Simpler architecture with fewer moving parts
- Agents already capable of reading context, executing work, and invoking judge
- Protocol is generic and applicable to any agent
- Reduces cognitive overhead for understanding the system

**Alternatives Considered:**
- **Keep orchestrator:** Rejected because it added complexity without clear benefit
- **Keep executor separate:** Rejected for plan workflow; executor remains as optional standalone utility

**Consequences:**
- ✅ Positive: Simpler system with clear protocol
- ✅ Positive: Any agent can execute plan tasks
- ✅ Positive: Reduced abstraction layers
- ⚠️ Negative: Agents must follow protocol voluntarily (documentation-based)

**Implementation Notes:** Orchestrator deleted, documentation updated to describe generic three-step protocol.

---

### Decision: Execution Decisions Only (No Task Logs)

**Status:** Approved  
**Context:** Previous design had two-level logging: transient task logs for iterations and persistent execution decisions. Task logs added complexity.

**Decision:** Single logging level - execution decisions written after task completion (approval or max attempts).

**Rationale:**
- Simpler architecture with one log type
- Execution decisions capture what matters: outcomes and key decisions
- No transient files to manage and delete
- Agents handle iterations in working memory

**Alternatives Considered:**
- **Keep two-level logging:** Rejected as unnecessarily complex
- **No logging:** Rejected because institutional memory is critical

**Consequences:**
- ✅ Positive: Simpler file structure
- ✅ Positive: No cleanup tasks needed
- ✅ Positive: Focus on outcomes, not process
- ⚠️ Negative: Iteration details not persisted (acceptable tradeoff)

**Implementation Notes:** Agents write execution decisions only after final outcome determined.

---

### Decision: Judge as Independent Quality Gate

**Status:** Approved  
**Context:** Need quality verification before work marked complete, but judge should be generic and not tied to specific workflow.

**Decision:** Judge is standalone agent invocable by any agent or user. Uses generic language ("the agent", "the work").

**Rationale:**
- Reusable across different workflows
- Clear separation of concerns (evaluation vs execution)
- Can be invoked directly by users for reviews
- No coupling to specific agents or workflows

**Alternatives Considered:**
- **Merge judge into agent prompts:** Rejected because external verification needed
- **Tie judge to executor:** Rejected because limits reusability

**Consequences:**
- ✅ Positive: Reusable quality gate
- ✅ Positive: Clear independent evaluator role
- ✅ Positive: User can invoke directly

**Implementation Notes:** Judge receives context from invoker (plan path, task description, work output).

---

### Decision: Per-Plan Folder Structure

**Status:** Approved  
**Context:** Multiple plans could have tasks with same IDs (e.g., both have `p1-1`), causing file collisions.

**Decision:** Create folder per plan: `.cursor/plans/[plan-name]/` containing all execution files for that plan.

**Rationale:**
- Eliminates naming collisions between plans
- Keeps plan artifacts organized together
- Easy to clean up (delete folder when plan complete)
- Clear ownership of files

**Alternatives Considered:**
- **Prefix files with plan name:** Rejected because still clutters plans folder
- **Single shared folder:** Rejected because of collision risk

**Consequences:**
- ✅ Positive: No collisions, clean organization
- ⚠️ Negative: More folders in `.cursor/plans/`

**Implementation Notes:** Folder created when first task starts execution, not at plan creation.

---

### Decision: Phase and Plan-Level Condensation

**Status:** Approved  
**Context:** Per-task decision files would accumulate, need periodic consolidation.

**Decision:** Auto-include condensation tasks in plans:
- Before each phase milestone: condense all phase task files into `phase_[N]_execution_decisions.md`
- Before final checkpoint: condense all phase files into `[plan_name]_execution_decisions.md`

**Rationale:**
- Maintains clean file structure
- Reduces cognitive load for agents reading logs
- Creates clear phase and plan-level summaries
- Automated through plan structure (not manual)

**Alternatives Considered:**
- **No condensation (keep all files):** Rejected because too many files accumulate
- **Condense only at plan end:** Rejected because phase boundaries are natural consolidation points
- **Manual condensation:** Rejected because would be forgotten

**Consequences:**
- ✅ Positive: Self-maintaining clean structure
- ✅ Positive: Natural summaries at each phase
- ⚠️ Negative: Adds tasks to every plan (minimal overhead)

**Implementation Notes:** `/plan` command and `plan-workflow/SKILL.md` must auto-include these tasks.

---

### Decision: Maximum 10 Attempts with Judge Debugger Mode

**Status:** Approved  
**Context:** Execution could loop forever on difficult tasks. Need reasonable retry limit with escape hatch.

**Decision:** Maximum 10 iterations. After 5 consecutive rejections with same failure pattern, judge switches to "debugger mode" for root cause analysis.

**Rationale:**
- 10 attempts provides runway for genuinely fixable issues
- Debugger mode surfaces systematic problems (task spec issues, missing context)
- Pattern detection prevents wasting attempts on unfixable problems
- Human intervention at escalation can redirect effort

**Alternatives Considered:**
- **5 attempts (original):** Rejected as potentially too few for complex tasks
- **Unlimited (until approved):** Rejected as risk of infinite loop
- **No debugger mode:** Rejected because pattern failures indicate systematic issues

**Consequences:**
- ✅ Positive: More attempts for complex tasks
- ✅ Positive: Debugger mode provides actionable diagnostics
- ⚠️ Negative: Could take longer to reach escalation

**Implementation Notes:** Agent detects 5 rejections with same criterion failing, invokes judge in debugger mode.

---

### Cross-Decision Impact

| Decision | Impacts |
|----------|---------|
| Remove orchestrator | Simplifies to generic three-step protocol |
| Execution decisions only | Eliminates transient file management |
| Judge as quality gate | Provides independent verification for any workflow |
| Per-plan folders | Enables clean organization and condensation |
| Condensation | Keeps folders clean, makes logging sustainable |
| Max 10 + debugger | Prevents endless loops while maximizing success |

---

## 4. Execution Protocol

### The Three-Step Protocol

Any agent executing plan tasks must follow this workflow:

**Step 1: Read execution decisions for context**

Before starting work, read all `*_execution_decisions.md` files in the plan folder (`.cursor/plans/[plan-name]/`). These provide:
- Decisions from completed tasks
- Context about what's been done
- Patterns and constraints discovered during execution

**Step 2: Execute and invoke judge**

Do the work, then before marking the task complete:
1. Invoke judge agent (`.cursor/agents/judge.md`)
2. Provide: plan file path, task description, work output
3. Judge evaluates against quality criteria
4. If rejected and attempts < 10: address feedback and retry
5. If rejected 5 times with same pattern: invoke judge in debugger mode
6. If rejected and attempts = 10: escalate to user

**Step 3: Write execution decisions**

After final approval OR reaching maximum attempts, write `[task_id]_execution_decisions.md` containing:
- Task outcome summary
- Key decisions made
- Issues encountered
- Files modified

Location: `.cursor/plans/[plan-name]/[task_id]_execution_decisions.md`

### Retry Logic

| Scenario | Behavior |
|----------|----------|
| First rejection | Address judge feedback, retry (attempt 2) |
| Subsequent rejections | Continue addressing feedback up to 10 attempts |
| 5 same-pattern rejections | Invoke judge in debugger mode for root cause analysis |
| 10th rejection | Write execution decisions, escalate to user |

### Error Handling

**Pattern Detection:**

If judge rejects 5 consecutive attempts with the same criterion failing, agent should invoke judge in debugger mode. Judge analyzes:
1. Is the task achievable as specified?
2. What critical context is missing?
3. Is this a capability limitation?

Judge provides recommendation:
- (A) Task needs redefinition
- (B) Missing context: [specific info needed]
- (C) Capability limitation: [what can't be done]

**Escalation at Maximum Attempts:**

After 10 failed attempts:
1. Write execution decisions with final outcome and all attempt details
2. Mark task as blocked or requiring user guidance
3. Present summary to user with:
   - What was attempted
   - Pattern of failures
   - Debugger analysis (if available)
   - Recommendation for next steps

---

## 5. Logs and Artifacts

### Folder Structure

```
.cursor/plans/
├── my-refactor.plan.md
└── my-refactor/                              ← Folder per plan
    ├── p1-1_execution_decisions.md           ← Per-task decisions
    ├── p1-2_execution_decisions.md
    ├── p1-3_execution_decisions.md
    ├── phase_1_execution_decisions.md        ← Condensed at phase end
    ├── p2-1_execution_decisions.md
    ├── ...
    ├── phase_2_execution_decisions.md        ← Condensed at phase end
    └── my-refactor_execution_decisions.md    ← Final condensed (plan end)
```

### Execution Decisions Structure

When task completes (approval or max attempts), write execution decisions:

```markdown
# Task [task_id] Execution Decisions

**Task:** [Description]
**Completed:** YYYY-MM-DD
**Attempts:** [N]
**Outcome:** [Approved/Blocked/Required escalation]

---

## Outcome

[Brief summary of what was delivered or why task couldn't be completed]

## Key Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| [Choice made] | [Why] | [Effect on future tasks] |

## Issues Encountered

- [Blocker or surprise that future agents should know]

## Files Modified

- [List of files changed]
```

---

## 6. Condensation Workflow

### Automatic Condensation Tasks

Plans must include automatic condensation tasks:

| When | Task | What It Does |
|------|------|--------------|
| Before each phase milestone | `p[N]-cond` | Merge all `p[N]-*_execution_decisions.md` into `phase_[N]_execution_decisions.md` |
| Second-to-last before final checkpoint | File references review | Review and adjust all file references in readme.md, how_it_works.md, docs/README.md, and any other documentation for created/deleted/renamed files |
| Last before final checkpoint | `p[final]-cond` | Merge all `phase_*_execution_decisions.md` into `[plan_name]_execution_decisions.md` |

### Condensation Rules

1. **Same structure, fewer files** - Condensed files use identical format, just combined
2. **Preserve decisions, remove noise** - Keep key decisions, remove attempt-by-attempt details
3. **Delete source files** - After successful condensation, delete the per-task files
4. **Maintain chronological order** - Entries sorted by task ID within each section

---

## 7. Judge Specification

### Judge Agent (`.cursor/agents/judge.md`)

**Description:** Evaluates work against quality criteria. Invoked by agents or users before marking tasks complete.

**Responsibilities:**
- Evaluate against 5 quality criteria
- Provide verdict (APPROVED or REJECTED)
- Give specific, actionable feedback if rejecting
- Switch to debugger mode after 5 same-pattern failures

**Quality Criteria:**
1. **Completeness** - All aspects addressed?
2. **Accuracy** - Factually correct?
3. **Clarity** - Understandable, logical structure?
4. **Consistency** - Aligns with plan context?
5. **Quality** - Meets professional standards?

**Invocation:**

Agents invoke judge by providing:
- Plan file path
- Task description
- Work output (what was produced/modified)
- Optional: prior attempt context

Judge returns verdict in response/chat.

**Modes:**

| Mode | When | Behavior |
|------|------|----------|
| **Normal** | Default | Evaluate against criteria, provide verdict |
| **Debugger** | After 5 same-pattern rejections | Diagnostic root cause analysis |

**Constraints:**
- Critical by default (rigorous standards)
- Evaluator only (doesn't do the work)
- Uses generic language (not tied to specific workflow)

---

## 8. Checkpoint Handling

When agent reaches a checkpoint task:

1. Complete all preceding tasks
2. Mark checkpoint `in_progress`
3. Present summary of completed work
4. **Stop and wait** for human approval
5. On approval: mark `completed`, proceed to next phase
6. On rejection: follow human guidance

**Never skip checkpoints.**

---

## 9. Constraints and Assumptions

**Technical Constraints:**
- Manual invocation of judge required
- Sequential task execution (one at a time)
- Maximum 100 todos per plan (Cursor limit)

**Assumptions:**
- Agents will follow three-step protocol voluntarily
- 10 iterations sufficient for most fixable tasks
- Judge criteria applicable to text/documentation work
- Agents can handle retry logic in working memory

**Known Limitations:**
- Protocol relies on agent compliance with documentation
- No rollback mechanism if human rejects approved work
- Concurrent execution not supported

---

## 10. Implementation Status

| Component | Status | Date Completed |
|-----------|--------|----------------|
| Generic three-step protocol | ✅ Complete | 2026-01-29 |
| Judge agent | ✅ Complete | 2026-01-28 |
| Execution decisions logging | ✅ Complete | 2026-01-29 |
| Condensation workflow | ✅ Complete | 2026-01-29 |
| Documentation updated | ✅ Complete | 2026-01-29 |

---

## 11. References

**Internal Files:**
- `.cursor/commands/plan.md` - Plan creation command
- `.cursor/rules/jobs/plan-creation.mdc` - Plan creation rule with standards
- `.cursor/skills/plan-workflow/SKILL.md` - Plan workflow protocols
- `system/ai_pro/my_cursor/plan_execution_decisions.md` - Execution decisions template
- `.cursor/agents/judge.md` - Judge agent specification

---

*Last updated: 2026-01-29*  
*Implementation completed: 2026-01-29*
