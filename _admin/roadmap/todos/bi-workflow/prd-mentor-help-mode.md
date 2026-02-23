---
title: 'Compound: Mentor Help Mode [H]'
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
  - .cursor/plans/agent-general-help-modes/shape.md
  - agents/mentor.md
  - workflows/bi-business-innovation/data/founder-process.md
  - workflows/bi-business-innovation/steps-c/step-02-milestone-select.md
outputPath: '_admin-output/planning-artifacts'
date: '2026-02-12'
yoloMode: false
---

# Mentor Help Mode [H]

**Type:** Agent Enhancement
**Priority:** Medium
**Tracker:**
**Status:** Backlog

---

## Overview

### Problem

Mentor guides founders through a 6-milestone lifecycle (Conception → Validation → Brand → Prototypation → Market Validation → MVP), each with 4-6 frameworks to complete. Founders lose track of where they are — which milestone, which frameworks are done, which are missing, and what workflows are available next. There is no orientation mechanism. The only way to check progress is to manually read the `project-memo.md` frontmatter, which is not user-friendly.

### Goals

- Add an [H] Help menu item to Mentor that displays a concise "you are here" orientation
- Show: current milestone, frameworks completed vs. missing within that milestone, and available workflows
- Available at the agent menu level and throughout any active workflow session
- Concise output — not a wall of text

### Constraints

- Data source must be `project-memo.md` frontmatter (currentMilestone, stepsCompleted) and `founder-process.md` (milestone framework lists)
- Must not load all step files to generate help display (violates micro-file architecture)
- Must work when no project is loaded (show general milestone overview without progress)
- Scoped to Mentor only — other RBTV agents (Ana, God, Dom Cobb) do not need [H]

---

## Self-Assessment

### Error Analysis

**Error type:** Missing UX feature

Mentor is the only RBTV agent with a persistent, multi-session lifecycle. A founder may return days or weeks later and need immediate orientation. The current flow (Continue Project → route to milestone) assumes the founder remembers where they left off. The `project-memo.md` frontmatter tracks state, but this is machine-readable metadata — no agent-side feature translates it into a human-readable "you are here" display. This gap is unique to Mentor because other RBTV agents are session-scoped (start task, complete task, leave).

### Context Source Evaluation

| File | Role | Gap |
|------|------|-----|
| `agents/mentor.md` | Agent definition — menu has [N], [C], [PM], [DA] | No [H] help or orientation option |
| `workflows/bi-business-innovation/data/founder-process.md` | Master navigation: 6 milestones, frameworks per milestone, output structure | Not surfaced to user — only read by agent for routing |
| `workflows/bi-business-innovation/templates/project-memo.md` | State tracking template with frontmatter | Contains currentMilestone, stepsCompleted — but no user-facing display |
| `workflows/bi-business-innovation/steps-c/step-02-milestone-select.md` | Routes to current milestone workflow | Routes silently — founder does not see a progress overview |

**Key gaps:**
- No menu option to view progress
- `founder-process.md` milestones/framework data is agent-internal, never shown to user
- `project-memo.md` state is tracked but not displayed in a human-readable summary
- No mechanism to show "what's available" within the current milestone

### Improvement Options

1. **Inline Action in Agent File**: Add `<action id="help">` that reads project-memo frontmatter + founder-process.md and displays a formatted progress summary
   - **Rationale:** Fast access from menu, follows existing action pattern, all data sources already exist
   - **Location:** `agents/mentor.md` — new `<action>` block + new `<item>` in `<menu>`

2. **Dedicated Help Task File**: Create `tasks/mentor-help.xml` that generates the progress display
   - **Rationale:** Keeps agent file lean, task file can have richer formatting logic
   - **Location:** `tasks/mentor-help.xml`

3. **Help Data File + Exec Handler**: Store help display template in `workflows/bi-business-innovation/data/help-display.md`, load via exec
   - **Rationale:** Separates display logic from agent definition
   - **Location:** `workflows/bi-business-innovation/data/help-display.md`

4. **Extend Project Memo Template**: Add a "progress summary" section to project-memo.md that agents update after each framework completion
   - **Rationale:** Summary is always available in the memo itself; no runtime generation needed
   - **Location:** `workflows/bi-business-innovation/templates/project-memo.md`

5. **Dashboard Workflow**: Create a `workflows/bi-progress-dashboard/` single-step workflow that generates a visual progress report
   - **Rationale:** Could produce a richer output with completion percentages, next recommended actions
   - **Location:** `workflows/bi-progress-dashboard/workflow.md`

---

## Proposed Solution

**Option 1: Inline Action in Agent File**

Add an [H] Help menu item with an inline `<action id="help">` that reads project state and displays a concise orientation.

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify | `agents/mentor.md` |
| Scope of change | Add 1 menu item + 1 action block (~20-25 lines) |
| Data sources | `project-memo.md` frontmatter + `founder-process.md` milestone data |

### Help Display Specification

**When no project is loaded ({project_detected}=false):**

```
📍 YOU ARE HERE: No project loaded

The founder journey has 6 milestones:
  M1: Conception — Structure idea into business concept
  M2: Validation — Validate technical and financial feasibility
  M3: Brand — Create preliminary brand book
  M4: Prototypation — Build working HTML prototype
  M5: Market Validation — Validate market demand
  M6: MVP — Create minimum viable product

→ Use [N] to start a new project or [C] to continue an existing one.
```

**When project is loaded ({project_detected}=true):**

```
📍 YOU ARE HERE: {projectName}

Milestone: {currentMilestone} ({N} of 6)

Frameworks in {currentMilestone}:
  ✅ Working Backwards
  ✅ Jobs-to-be-Done
  → Competitive Landscape (current)
  ○ Problem-Solution Fit
  ○ Lean Canvas
  ○ 5 Whys

Progress: 2/6 complete

Available workflows:
  [M{N}] Continue {currentMilestone}
  [PM] Party Mode
```

**Display rules:**
- ✅ = completed (in stepsCompleted array)
- → = current (currentFramework from frontmatter)
- ○ = pending
- Framework list comes from `founder-process.md` for the current milestone
- Available workflows shows only actions relevant to current state
- Total output: 10-15 lines maximum

### Action Behavior

1. Read `project-memo.md` frontmatter (if project loaded)
2. Read `founder-process.md` to get framework list for current milestone
3. Cross-reference stepsCompleted against milestone's framework list
4. Display formatted progress summary
5. Return to current menu (do not change agent state)

[H] must be available:
- At Mentor's main menu (agent-level)
- During any active milestone workflow (the action reads current state regardless of where in the workflow the user is)

---

## Rationale

Inline action is the correct choice because:
1. All data sources already exist (project-memo frontmatter + founder-process.md)
2. No new files needed — keeps the system lean
3. Follows Mentor's existing `<action>` pattern
4. The display logic is simple (read state, cross-reference, format) — does not warrant a separate task or workflow
5. Agent file stays within 100-line limit after addition
6. [H] is a read-only operation — it displays state, never modifies it

---

## Acceptance Criteria

- [ ] [H] Help appears in Mentor's menu (available alongside [N], [C], [PM], [DA])
- [ ] With no project loaded: displays general 6-milestone overview with descriptions
- [ ] With project loaded: displays current milestone, framework progress (done/current/pending), and available workflows
- [ ] Framework list for each milestone is derived from `founder-process.md`, not hardcoded
- [ ] Progress markers use ✅/→/○ convention for done/current/pending
- [ ] Total output is 15 lines or fewer
- [ ] [H] is also accessible during active milestone workflows (not just the top-level menu)
- [ ] Selecting [H] returns to the current menu after display — no state change
- [ ] Mentor's persona is maintained (direct, no fluff)

---

## Related Files

| File | Relationship |
|------|--------------|
| `agents/mentor.md` | Target file for modification |
| `workflows/bi-business-innovation/data/founder-process.md` | Data source — milestone framework lists |
| `workflows/bi-business-innovation/templates/project-memo.md` | State source — currentMilestone, stepsCompleted, currentFramework |
| `workflows/bi-business-innovation/steps-c/step-02-milestone-select.md` | Routing step — [H] provides the orientation this step lacks |

---

## References

- Original plan: `.cursor/plans/agent-general-help-modes/agent-general-help-modes.plan.md`
- Shape decisions: `.cursor/plans/agent-general-help-modes/shape.md` (User Input #2, #3, #4)
- Founder process knowledge: `workflows/bi-business-innovation/data/founder-process.md`

---

## Discussion Notes

- User confirmed [H] applies only to Mentor — other RBTV agents are session-scoped and don't need lifecycle orientation
- User specified: [H] must comment on workflows available for the current milestone, not just framework completion status
- Separated from the original combined plan (agent-general-help-modes) into a standalone Compound PRD
- Original plan proposed [H] for all 4 agents + 38 workflows; this PRD scopes it to Mentor only, dramatically reducing implementation cost
- The original plan's "workflow step-level [H]" (showing which step you're on in any workflow) is dropped — Mentor's [H] is domain-specific (milestone progress), not generic step orientation
