# Use Case: Handoff for Planning Workflow - Adjustments Needed

**Type:** Use Case  
**Date:** 2026-02-01  
**Scenario:** Creating a handoff for plan development continuation revealed gaps in the planning workflow that need addressing

---

## 1. Overview

**Purpose:** Document the workflow adjustments needed when creating handoffs for plan development (as opposed to plan execution), based on a real session where a plan needed restructuring after judge rejection.

**Robotville Functions Showcased:**
- `/handoff` command - Context transfer for plan development continuation
- Planning workflow gaps identified through practical use

**Scenario Context:**
- Knowledge Manager v2 implementation plan rejected by judge twice
- Plan needed restructuring to comply with user's explicit requirements
- User requested handoff for agent to continue plan development
- Handoff creation revealed workflow gaps in planning process

**Success Metrics:**
- Identified specific workflow adjustments needed
- Documented plan development handoff pattern
- Captured learning for system improvement
- Clear recommendations for planning workflow skill updates

---

## 2. The Problem

### Initial State

The Knowledge Manager spec updates implementation plan (`km-spec-updates.plan.md`) had been rejected by the judge agent twice due to structural issues:

1. **Phase 6 Structure Violation**: Testing tasks violated document-per-phase rule
2. **Compound Tasks**: Tasks combined multiple objectives (not atomic)
3. **Review Task Clarity**: Review tasks lacked specific deliverable format
4. **Phase Labeling**: Phase 1 structure unclear (p1-1 is pre-phase setup)
5. **Phase Mislabeling**: Phase 7 ("Cleanup") should be "Post-Execution: Condensation"

The user wanted to hand off the plan development work to a fresh agent that would continue fixing these structural issues.

### Challenge

When creating the handoff, several workflow gaps became apparent:

1. **No clear pattern for "plan development" handoffs** - Most handoffs are for execution, not for continuing plan creation/modification
2. **Judge feedback integration unclear** - How should judge rejections be captured and communicated to the next agent?
3. **User requirements vs judge requirements** - How to distinguish between user's explicit requirements and judge's structural feedback?
4. **Plan iteration workflow missing** - No documented process for "plan rejected → fix → resubmit" cycle
5. **Handoff file location ambiguity** - Where should plan development handoffs be saved?

---

## 3. What Happened

### Session Timeline

**Agent:** Claude (handoff mode)  
**Duration:** ~5 minutes  
**Context:** Plan rejected twice, needs restructuring

**Workflow:**

1. **User invoked handoff:**
   ```
   /handoff for an agent that will continue developing the plan.
   ```

2. **Agent detected plan development context:**
   - Key phrase: "continue developing the plan" (not "execute the plan")
   - Recognized need for plan-focused handoff (not execution-focused)
   - Identified handoff should focus on: judge feedback, user requirements, plan structure issues

3. **Agent read planning resources:**
   - `.cursor/rules/jobs/guardrails/plan-creation.mdc`
   - `.cursor/commands/plan.md`
   - Found: Planning standards exist, but no guidance on plan iteration workflow

4. **Agent created handoff:**
   - Location: `.cursor/plans/km-spec-updates/km-spec-updates-handoff.md`
   - Structure: Problem → Goals → Constraints → Decisions → Gaps → Files → Judge Feedback → Next Steps
   - Content: 188 lines capturing full context for plan development continuation

5. **User requested documentation:**
   ```
   /doc, focusing on use case and on what i corrected you. put it on @robotville/docs/use_cases
   ```

6. **User refined focus:**
   ```
   this should be called and focused on handoff_planning_workflow_adjustments
   ```

### What This Revealed

The handoff creation process revealed that **planning workflow needs adjustments** for plan iteration scenarios:

- Handoff patterns exist for execution, but not for plan development
- Judge feedback loop not documented in planning workflow
- Plan iteration cycle (create → judge → reject → fix → resubmit) not formalized
- Handoff structure for plan development different from execution handoffs

---

## 4. Planning Workflow Gaps Identified

### Gap 1: Plan Development Handoff Pattern Missing

**Current state:** Planning workflow skill (`.cursor/skills/plan-workflow/SKILL.md`) documents:
- Part 1: Plan Creation (initial plan creation)
- Part 2: Plan Execution (task execution workflow)

**What's missing:** Part 1.5 or separate section for **Plan Iteration**:
- When plan is rejected by judge
- When user requests plan restructuring
- When plan needs continuation by different agent
- Handoff structure for plan development vs execution

**Impact:** Agents creating plan development handoffs have no template or guidance.

**Recommendation:** Add to `plan-workflow/SKILL.md`:

```markdown
## Part 1.5: Plan Iteration and Handoff

### When Plan Needs Iteration

Plans may need iteration when:
1. Judge rejects plan for structural issues
2. User requests plan restructuring
3. Plan development needs continuation by different agent
4. New requirements emerge during planning

### Plan Development Handoff Structure

When creating handoff for plan development continuation:

**Required sections:**
1. **Problem Being Solved** - What issues exist in current plan
2. **User Goals** - What user wants next agent to accomplish
3. **Constraints Gathered** - Technical, process, project constraints
4. **Decisions Already Made** - With rationale and alternatives (prevent re-deciding)
5. **Information Gaps Remaining** - What's unclear or needs resolution
6. **Judge Feedback Summary** - Status, issues, requirement coverage
7. **Files to Load** - Planning resources (SKILL.md, guardrails, spec)
8. **Next Steps** - Clear guidelines for plan fixes

**File location:** `.cursor/plans/[plan-name]/[plan-name]-handoff.md`

**Key differences from execution handoff:**
- Focus on plan structure, not implementation
- Include judge feedback prominently
- List planning resources, not code files
- Next steps focus on plan fixes, not task execution
```

---

### Gap 2: Judge Feedback Integration Not Documented

**Current state:** Judge agent exists (`.cursor/agents/judge.md`), but planning workflow doesn't document:
- How to capture judge feedback when plan is rejected
- How to communicate judge feedback to next agent
- How to structure plan fixes based on judge feedback
- When to invoke judge during plan creation (before execution? after restructuring?)

**What's missing:** Judge feedback loop in planning workflow:
1. Create plan
2. Invoke judge for plan review (optional? mandatory?)
3. If rejected: capture feedback, create handoff or fix directly
4. If approved: proceed to execution

**Impact:** Inconsistent judge usage during planning; no standard for capturing/communicating judge feedback.

**Recommendation:** Add to `plan-workflow/SKILL.md` Part 1:

```markdown
### Step 5: Plan Review (Optional but Recommended)

Before proceeding to execution, consider invoking judge to review plan structure:

**When to invoke judge:**
- Complex plans (>10 tasks, >3 phases)
- Plans with user-specified structure requirements
- Plans involving multiple agents or phases
- When uncertain about plan structure compliance

**Judge review criteria for plans:**
1. **Structure** - Phases organized correctly, tasks atomic
2. **Completeness** - All requirements covered, no gaps
3. **Clarity** - Task descriptions clear, deliverables specific
4. **Consistency** - Naming, numbering, format consistent
5. **Executability** - Tasks have clear success criteria

**If judge rejects plan:**
1. Capture judge feedback in structured format
2. Determine if fixes are quick (do immediately) or complex (create handoff)
3. If creating handoff: use Plan Development Handoff structure (see Part 1.5)
4. If fixing directly: address all judge feedback, then re-invoke judge

**Judge feedback capture format:**
```markdown
## Judge Feedback Summary

**Status:** REJECTED | APPROVED

**Key Issues:**
1. [Issue 1 with specific details]
2. [Issue 2 with specific details]

**Requirement Coverage:**
- [Requirement 1]: **Met** | **Partially Met** | **Not Met** - [explanation]
- [Requirement 2]: **Met** | **Partially Met** | **Not Met** - [explanation]
```
```

---

### Gap 3: User Requirements vs Judge Requirements Unclear

**Current state:** Planning workflow doesn't distinguish between:
- **User's explicit requirements** (e.g., "phases must contain all changes for same document")
- **Judge's structural feedback** (e.g., "compound tasks need splitting")
- **Planning workflow standards** (e.g., "tasks must be atomic")

**What's missing:** Hierarchy of requirements and how to handle conflicts:
1. User's explicit requirements (highest priority)
2. Planning workflow standards (from SKILL.md)
3. Judge's structural feedback (enforcement of standards)
4. Agent's implementation decisions (lowest priority)

**Impact:** Agents may prioritize judge feedback over user requirements, or vice versa.

**Recommendation:** Add to `plan-workflow/SKILL.md`:

```markdown
## Requirement Hierarchy

When creating or iterating on plans, follow this priority order:

1. **User's Explicit Requirements** (highest priority)
   - Direct user instructions about plan structure
   - User-specified constraints or preferences
   - Example: "phases must contain all changes for same document"
   - **Action:** Must comply exactly; ask for clarification if unclear

2. **Planning Workflow Standards** (from this SKILL.md)
   - Atomic tasks, clear deliverables, phase organization
   - Checkpoint and condensation patterns
   - Execution protocol references
   - **Action:** Follow unless conflicts with user requirements

3. **Judge's Structural Feedback** (enforcement of standards)
   - Judge enforces standards 1 and 2 above
   - Judge feedback indicates non-compliance
   - **Action:** Address all judge feedback; if conflicts with user requirements, ask user for clarification

4. **Agent's Implementation Decisions** (lowest priority)
   - Task naming, phase numbering, file organization
   - Mermaid diagram choices, formatting preferences
   - **Action:** Use best judgment; defer to standards and user requirements

**Conflict resolution:**
- If judge feedback conflicts with user requirements: Ask user which takes priority
- If standards conflict with user requirements: User requirements win
- If unclear: Ask user for clarification before proceeding
```

---

### Gap 4: Plan Iteration Cycle Not Formalized

**Current state:** Planning workflow assumes linear flow:
1. Create plan
2. Execute plan
3. Complete

**What's missing:** Iteration cycle for plan refinement:
1. Create plan
2. Review plan (self or judge)
3. **If issues found:** Fix → Review again (loop)
4. **If approved:** Execute plan
5. **During execution:** If plan needs changes → Update plan → Review → Continue

**Impact:** No clear process for "plan rejected → fix → resubmit" workflow.

**Recommendation:** Add to `plan-workflow/SKILL.md`:

```markdown
## Plan Iteration Cycle

Plans often require iteration before execution. Follow this cycle:

```
┌─────────────────────────────────────────────────────────┐
│                    CREATE PLAN                          │
│                  (Part 1: Steps 1-4)                    │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   REVIEW PLAN                           │
│              (Self-review or Judge)                     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │  Issues found? │
              └───────┬───────┘
                      │
         ┌────────────┴────────────┐
         │                         │
        YES                       NO
         │                         │
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│   FIX ISSUES    │       │  EXECUTE PLAN   │
│                 │       │  (Part 2)       │
│ Quick fixes:    │       └─────────────────┘
│ - Fix directly  │
│ - Re-review     │
│                 │
│ Complex fixes:  │
│ - Create handoff│
│ - New agent     │
│   continues     │
└────────┬────────┘
         │
         └──────────┐
                    │
                    ▼
            (back to REVIEW)
```

**Decision criteria:**

| Scenario | Action | Next Step |
|----------|--------|-----------|
| Quick fixes (<5 min) | Fix directly | Re-review (self or judge) |
| Complex fixes (>5 min) | Create handoff | New agent continues |
| Structural issues | Create handoff | New agent with fresh perspective |
| Minor tweaks | Fix directly | Proceed to execution |
```

---

### Gap 5: Handoff File Location Not Standardized

**Current state:** No documented standard for where handoffs should be saved.

**What's missing:** File location standards for different handoff types:
- Plan development handoffs
- Task execution handoffs
- Project handoffs

**Impact:** Inconsistent handoff locations, hard to discover.

**Recommendation:** Add to `.cursor/rules/documentation/product-documentation.mdc`:

```markdown
## Handoff File Locations

| Handoff Type | Location | Naming | Example |
|--------------|----------|--------|---------|
| **Plan development** | `.cursor/plans/[plan-name]/` | `[plan-name]-handoff.md` | `km-spec-updates-handoff.md` |
| **Task execution** | `.cursor/plans/[plan-name]/` | `[plan-name]-handoff.md` | `km-pipeline-v2-handoff.md` |
| **Project handoff** | Project root or `docs/` | `handoff.md` or `[project]-handoff.md` | `knowledge_manager-handoff.md` |

**Rationale:** Co-locate handoffs with the work they describe.

**File structure example:**
```
.cursor/plans/km-spec-updates/
├── km-spec-updates.plan.md          # The plan
├── km-spec-updates-handoff.md       # Handoff for plan development
├── p1-1_execution_decisions.md      # Task execution logs
└── p1_decisions.md                  # Condensed phase decisions
```
```

---

## 5. Handoff Structure Comparison

### Plan Development Handoff vs Execution Handoff

| Section | Plan Development | Execution Handoff |
|---------|------------------|-------------------|
| **Problem Being Solved** | Plan structure issues, judge feedback | Implementation requirements, technical challenges |
| **User Goals** | Fix plan structure, address judge feedback, prepare for execution | Complete tasks, deliver features, meet requirements |
| **Constraints** | Planning workflow standards, user structure requirements | Technical constraints, dependencies, environment |
| **Decisions** | Plan organization, phase structure, task granularity | Technical implementation, architecture, design |
| **Information Gaps** | Judge feedback issues, unclear requirements, questions | Missing specs, unclear dependencies, technical unknowns |
| **Files to Load** | Planning resources (SKILL.md, guardrails, plan.md) | Code files, config, spec, dependencies |
| **Judge Feedback** | **Prominent section** - Status, issues, coverage | Not applicable (judge reviews tasks, not execution) |
| **Next Steps** | Fix plan structure, address feedback, resubmit | Execute tasks, follow protocol, invoke judge per task |

### Example: Plan Development Handoff Structure

```markdown
# Plan Development Handoff: [Plan Name]

**Created:** YYYY-MM-DD
**Purpose:** Continue developing the [plan-name] implementation plan

---

## Problem Being Solved

[What issues exist in the current plan? Why does it need iteration?]

## User Goals

1. **Fix the implementation plan structure** to comply with user's requirements:
   - [Requirement 1]
   - [Requirement 2]

2. **Address judge's critical feedback**:
   - [Issue 1]
   - [Issue 2]

3. **Prepare plan for execution** once structure is corrected

## Constraints Gathered

- **Technical constraints:** [e.g., Google Apps Script environment]
- **Process constraints:** [e.g., Plan workflow compliance]
- **User requirements:** [e.g., Document-per-phase structure]

## Decisions Already Made

### Decision 1: [Decision Title]
- **Decision:** [What was decided]
- **Rationale:** [Why this decision was made]
- **Context:** [When/how this decision came up]
- **Alternatives Considered:** [What else was considered and why rejected]

[Repeat for each major decision]

## Information Gaps Remaining

### Critical Issues from Judge Feedback

[List specific issues judge identified, with details on what needs fixing]

### Questions Needing Resolution

- [Question 1 requiring user input]
- [Question 2 requiring clarification]

## Files to Load

| Document Name/Path | Purpose | Available |
|---|---|---|
| `[plan-file].plan.md` | Current plan needing correction | Yes |
| `[spec-file].md` | Requirements specification | Yes |
| `.cursor/skills/plan-workflow/SKILL.md` | Planning workflow standards | Yes |
| `.cursor/rules/jobs/guardrails/plan-creation.mdc` | Planning guardrails | Yes |

## Judge Feedback Summary

**Status:** REJECTED

**Key Issues:**
1. [Issue 1 with specific details]
2. [Issue 2 with specific details]

**Requirement Coverage:**
- [Requirement 1]: **Partially Met** - [explanation]
- [Requirement 2]: **Not Met** - [explanation]

## Next Steps (Guidelines)

**For the Agent Reading This Handoff:**

1. **Read planning resources:**
   - [List specific files and sections]

2. **Review the context** provided in this handoff, especially:
   - [Key context items]

3. **Determine approach:**
   - [Decision points for next agent]

4. **Apply fixes to plan:**
   - [Specific fixes needed]

5. **Verify compliance:**
   - [Checklist for verification]

6. **Follow plan creation protocol** from plan workflow skill

---
```

---

## 6. Key Decisions

### Decision 1: Handoff Type - Plan Development

**Context:** User said "for an agent that will continue developing the plan"

**Decision:** Create plan development handoff (not execution handoff)

**Rationale:**
- "developing the plan" indicates plan creation/modification work
- Plan development needs: judge feedback, user requirements, plan structure issues
- Execution handoff needs: task dependencies, implementation context, code

**Consequences:**
- ✅ Handoff focused on plan structure and judge feedback
- ✅ Included planning resources (not code files)
- ✅ Next steps focus on plan fixes (not task execution)

---

### Decision 2: Handoff File Location

**Context:** Creating handoff for km-spec-updates plan development

**Decision:** Place at `.cursor/plans/km-spec-updates/km-spec-updates-handoff.md`

**Rationale:**
- Plan-specific handoff belongs with plan
- Co-location aids discovery
- Naming convention: `[plan-name]-handoff.md`

**Consequences:**
- ✅ Handoff co-located with plan
- ✅ Clear naming pattern
- ✅ Easy to find and reference

---

### Decision 3: Judge Feedback as Prominent Section

**Context:** Plan rejected twice by judge

**Decision:** Create dedicated "Judge Feedback Summary" section in handoff

**Rationale:**
- Judge feedback is critical context for plan fixes
- Next agent needs to understand what judge rejected and why
- Structured format (Status, Issues, Coverage) aids comprehension

**Consequences:**
- ✅ Judge feedback clearly visible
- ✅ Specific issues documented
- ✅ Requirement coverage tracked

---

## 7. Lessons for System Improvement

### What Worked Well

1. **Handoff type detection** - Agent correctly identified plan development context
2. **Judge feedback capture** - Structured format made issues clear
3. **File location choice** - Co-location with plan was correct
4. **Context completeness** - 188 lines provided full context for continuation

### What Needs Adjustment

1. **Planning workflow skill** - Add Part 1.5 for plan iteration and handoff patterns
2. **Judge feedback integration** - Document judge review cycle in planning workflow
3. **Requirement hierarchy** - Clarify user requirements > standards > judge feedback
4. **Plan iteration cycle** - Formalize "create → review → fix → resubmit" workflow
5. **File location standards** - Document handoff locations in product-documentation.mdc

---

## 8. Recommended System Updates

### Update 1: Add to `plan-workflow/SKILL.md`

**Location:** After Part 1 (Plan Creation), before Part 2 (Plan Execution)

**New section:** Part 1.5: Plan Iteration and Handoff

**Content:**
- Plan iteration cycle diagram
- When to iterate vs proceed
- Plan development handoff structure
- Judge feedback integration
- Requirement hierarchy
- Quick fixes vs complex fixes decision criteria

**Impact:** Agents will have clear guidance for plan iteration scenarios.

---

### Update 2: Add to `product-documentation.mdc`

**Location:** After "Documentation Folder Structure" section

**New section:** Handoff File Locations

**Content:**
- Table of handoff types and locations
- Naming conventions
- File structure examples
- Rationale for co-location

**Impact:** Consistent handoff file locations across all plans.

---

### Update 3: Add to `plan-creation.mdc`

**Location:** After "Planning Standards" section

**New section:** Plan Review and Iteration

**Content:**
- When to invoke judge for plan review
- Judge review criteria for plans (not tasks)
- How to capture judge feedback
- Plan iteration workflow

**Impact:** Standardized judge usage during planning phase.

---

## 9. References

**Files Created:**
- `H:\repos\.cursor\plans\km-spec-updates\km-spec-updates-handoff.md` - Plan development handoff (188 lines)
- `H:\repos\robotville\docs\use_cases\handoff_planning_workflow_adjustments.md` - This use case

**Files Referenced:**
- `H:\repos\.cursor\plans\km-spec-updates\km-spec-updates.plan.md` - Plan needing iteration
- `H:\repos\.cursor\skills\plan-workflow\SKILL.md` - Planning workflow (needs Part 1.5)
- `H:\repos\.cursor\rules\jobs\guardrails\plan-creation.mdc` - Planning standards
- `H:\repos\.cursor\rules\documentation\product-documentation.mdc` - Documentation standards
- `H:\repos\.cursor\commands\plan.md` - Plan command definition

**Robotville Components Used:**
- `/handoff` command - Context transfer
- `/doc` command - Use case documentation

---
