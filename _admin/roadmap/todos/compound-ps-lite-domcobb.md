---
title: 'Compound: PS Lite Mode for Dom Cobb'
docType: 'compound'
mode: 'create'
priority: 'Medium'
tracker: ''
stepsCompleted:
  - step-01-init.md
  - step-02-self-assessment.md
  - step-03-discussion.md
  - step-04-document.md
inputDocuments:
  - .cursor/plans/agent-general-help-modes/agent-general-help-modes.plan.md
  - .cursor/plans/agent-general-help-modes/phase-1/p1-2.task.md
  - .cursor/plans/agent-general-help-modes/shape.md
  - agents/domcobb.md
  - workflows/problem-structuring/workflow.md
outputPath: '_admin-output/planning-artifacts'
date: '2026-02-12'
yoloMode: false
---

# PS Lite Mode for Dom Cobb

**Type:** Agent Enhancement
**Priority:** Medium
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

Dom Cobb's [PS] Problem Structuring mode routes to a full multi-step workflow with formal frameworks (MECE, Pyramid Principle, Problem Trees). Users with simple or moderately complex problems must commit to this entire workflow even when a quick conversational exchange would suffice. There is no lightweight alternative — it's either the full framework workflow or nothing.

### Goals

- Add a [PL] PS Lite menu item to Dom Cobb for lightweight, conversational problem structuring
- Start with open-ended Socratic questioning — no framework jargon
- Organically introduce structure (categories, groupings, priorities) only as the conversation reveals the need
- Escalate to [PS] automatically when complexity warrants it, carrying gathered context forward
- Resolve simple problems in 2-3 exchanges with a clean problem statement and actionable next steps

### Constraints

- Must be an **inline action** in `domcobb.md`, NOT a separate workflow (express mode must be fast; a full workflow defeats the purpose)
- Must maintain Dom Cobb's persona (Socratic, structured, warm)
- Must not duplicate [PS] — PS Lite is a lightweight entry point that escalates to [PS] when needed
- Action prompt must fit within agent file size limits (agent max: 100 lines total)

---

## Self-Assessment

### Error Analysis

**Error type:** Design gap

Dom Cobb's current menu offers four modes: [PS], [PV], [PR], [AK]. All are full workflows or routed to external modules. There is no lightweight "just help me think through this" option. Users who want quick problem clarification must either use the full [PS] workflow (heavy) or leave Dom Cobb entirely. This creates unnecessary friction for the most common use case — someone with a vague idea who needs 2-3 minutes of structured conversation, not a full framework application.

### Context Source Evaluation

| File | Role | Gap |
|------|------|-----|
| `agents/domcobb.md` | Agent definition with menu and handlers | No lightweight mode; all menu items route to full workflows |
| `workflows/problem-structuring/workflow.md` | Full PS workflow with formal frameworks | Overkill for simple problems; no "lite" entry path |
| `workflows/problem-structuring/steps-c/step-01-init.md` | PS initialization — framework selection | Forces framework choice before problem is even articulated |

### Improvement Options

1. **Inline Action in Agent File**: Add `<action id="ps-lite">` with a conversational prompt that starts Socratic, monitors complexity, and escalates to [PS] if needed
   - **Rationale:** Fastest to reach, no file loading overhead, stays in Dom Cobb's context
   - **Location:** `agents/domcobb.md` — new `<action>` block + new `<item>` in `<menu>`

2. **Minimal Workflow (2 steps)**: Create a `workflows/ps-lite/` with just init + structure steps
   - **Rationale:** Follows existing workflow patterns; easier to extend later
   - **Location:** `workflows/ps-lite/workflow.md` + 2 step files

3. **Prompt Template in Data File**: Store the PS Lite prompt in `workflows/problem-structuring/data/ps-lite-prompt.md`, load via exec handler
   - **Rationale:** Keeps agent file lean; prompt can be longer
   - **Location:** `workflows/problem-structuring/data/ps-lite-prompt.md`

4. **Extend PS Workflow**: Add a "lite" sub-mode to the existing PS workflow that skips framework selection
   - **Rationale:** Reuses existing workflow infrastructure
   - **Location:** `workflows/problem-structuring/workflow.md` — add sub-mode routing

5. **Task File**: Create a `tasks/ps-lite.xml` task that Dom Cobb executes via exec handler
   - **Rationale:** Task files are designed for focused, single-purpose operations
   - **Location:** `tasks/ps-lite.xml`

---

## Proposed Solution

**Option 1: Inline Action in Agent File**

Add a [PL] PS Lite menu item with an inline `<action id="ps-lite">` that implements conversational problem structuring directly in Dom Cobb's agent file.

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | `agents/domcobb.md` |
| Scope of change | Add 1 menu item + 1 action block (~15-20 lines) |
| Related files | `workflows/problem-structuring/workflow.md` (escalation target) |

### Action Behavior Specification

**Entry:** User selects [PL]. Dom Cobb asks: "What are you trying to figure out?" — no framework jargon.

**Conversation loop:**
1. Listen to the user's response
2. Ask clarifying questions (Socratic style): "What specifically about X?", "Who is affected?", "What happens if you do nothing?"
3. Organically surface structure: group related points, identify categories, highlight tensions
4. After each exchange, assess complexity

**Simple resolution (2-3 exchanges):**
- Deliver a clean problem statement
- List 2-3 actionable next steps
- Ask: "Does this capture it, or is there more?"

**Escalation triggers (any of these):**
- 3+ distinct problem dimensions identified
- Competing priorities or stakeholders
- Dependencies that require decomposition
- User explicitly asks for more structure

**Escalation prompt:** "This is getting interesting — there are enough moving parts here that the full structuring toolkit would help. Want me to switch to [PS] with what we've gathered so far?"

**On escalation:** Context gathered during PS Lite conversation transfers to [PS] workflow as initial input. User does not re-explain.

---

## Rationale

Inline action is the correct choice because:
1. Express mode must be fast — no file loading, no workflow overhead
2. The prompt fits comfortably within an action block (~15-20 lines)
3. It follows Dom Cobb's existing `<action>` pattern (see `new-project` action pattern in Mentor)
4. Escalation to [PS] uses the existing `exec` handler — no new infrastructure needed
5. Agent file stays within 100-line limit

---

## Acceptance Criteria

- [ ] [PL] PS Lite appears in Dom Cobb's menu between [PS] and [PV]
- [ ] Selecting [PL] starts a conversational exchange with no framework jargon
- [ ] Simple problems resolve in 2-3 exchanges with a problem statement + next steps
- [ ] Complex problems trigger an escalation prompt to [PS]
- [ ] On escalation, context transfers to [PS] workflow — user does not re-explain
- [ ] Dom Cobb's persona is maintained throughout (Socratic, structured, warm)
- [ ] Agent file stays within 100-line limit after addition

---

## Related Files

| File | Relationship |
|------|--------------|
| `agents/domcobb.md` | Target file for modification |
| `workflows/problem-structuring/workflow.md` | Escalation target — [PS] full workflow |
| `workflows/problem-structuring/steps-c/step-01-init.md` | PS init step — PS Lite simplifies this |

---

## References

- Original plan: `.cursor/plans/agent-general-help-modes/agent-general-help-modes.plan.md`
- PS Lite task spec: `.cursor/plans/agent-general-help-modes/phase-1/p1-2.task.md`
- Shape decisions: `.cursor/plans/agent-general-help-modes/shape.md` (User Input #1: "PS but simpler. Not necessarily following the frameworks, and only do so if it gets more complex.")

---

## Discussion Notes

- User confirmed PS Lite applies only to Dom Cobb — no other agents need a lightweight problem structuring mode
- Separated from the original combined plan (agent-general-help-modes) into a standalone Compound PRD for independent implementation
- Original plan bundled PS Lite with [H] Help mode; these are now two independent PRDs
