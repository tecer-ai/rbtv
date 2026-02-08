---
---

# Template Instructions: Founder Diary

**Purpose:** Primary project tracking document per milestone. Combines session status, file navigation, framework tracking, and decision/event logging in a single file. This is the starting point for users and agents initiating a working session.

**Naming Convention:** `m[x]_founder_diary.md` (e.g., `m1_founder_diary.md`, `m2_founder_diary.md`)

**Location:** `[project]/docs/founder/[milestone]/m[x]_founder_diary.md`

---

## AI Navigation Instructions

Include at the top of every founder_diary.md instance:

**Current Framework**: [Which milestone, step, and framework is active. What specific section or task within the framework is in progress (max 280 characters).]
**Last Work Performed**: [What was accomplished in the most recent session. Concrete outputs: sections written, decisions made, documents created(max 280 characters).]
**Next Steps**: [What needs to happen next based on current progress. Specific enough that an agent can resume work without additional context(max 280 characters).]

**Template reference:** This document was created from [`founder_diary.md`](../../../../robotville/system/founder/templates/founder_diary.md). Agents MUST read the template before making updates.

**Understanding the process:** Read [`system/founder/founder_process.md`](../../../../robotville/system/founder/founder_process.md) for module structure, milestone navigation, and applicable frameworks.

**Example:**

> Working on M1 Conception, Step 4: Problem-Solution Fit Canvas. Currently completing the solution articulation section after mapping problem triggers and emotional responses in previous sessions.

> Completed the problem-triggers-emotions mapping in the Problem-Solution Fit Canvas. Identified 3 core trigger scenarios and mapped emotional responses for each. Logged decision to focus on HR managers as primary persona.

> Complete solution articulation by mapping proposed solution to each trigger scenario. Then extract critical assumptions and tag them for M2 validation. Update project memo Problem section with synthesized findings.

---

## File Map Section

ASCII tree showing the `docs/founder/` folder structure with inline short descriptions. Placed immediately after the session status paragraphs.

**Example:**
```
docs/founder/
├── acme_memo.md                    # Project vision, progress, current state
├── conception/
│   ├── m1_founder_diary.md         # THIS FILE — session tracking + decisions
│   ├── working_backwards.md        # Customer-centric product vision
│   └── problem_solution_fit.md     # Problem-solution validation
└── validation/
    └── m2_founder_diary.md         # (not yet started)
```

---

## Framework Status Section

Table showing framework execution status across milestones.

**Columns:** Framework | Status

**Format:**
| Framework | Status |
|---|---|
| [Working Backwards](conception/working_backwards.md) | Done |
| [Problem-Solution Fit](conception/problem_solution_fit.md) | WIP |
| [5 Whys](conception/5_whys.md) | To-do |

**Rows:**
- All completed frameworks from past milestones (Status: Done)
- All frameworks from current milestone (Status: WIP or To-do)

---

## Log Table

Single table for all milestone events: decisions, pivots, blockers, learnings, and ideas for future exploration.

### When to Log

Use the filtering test before adding an entry:

> **"In 3 months, will an agent need this to understand why the project is in its current state, or to avoid repeating a mistake?"**

- **YES** — Log with full context
- **NO** — Skip

### What to Log

| Type | What to Log |
|------|-------------|
| **Decision** | Major choices that shape direction + rationale + alternatives rejected |
| **Pivot** | Change in direction + trigger + what was abandoned |
| **Blocker** | Impediment that stopped progress + resolution + time cost |
| **Assumption Invalidated** | Tested belief that proved false + evidence + consequence |
| **External Shift** | Market/competitor/regulatory change affecting project |
| **Learning** | Insight from customer/data that changes understanding |
| **Idea** | Future exploration topic captured during focus checks — outside current scope, preserved for later |

### What NOT to Log

- Task completions — goes in project memo Progress section
- Progress updates — status belongs in Session Status paragraphs
- Raw framework outputs — lives in applied framework doc
- Routine activities — "Updated roadmap", "Fixed typo"

### Table Structure

| Column | Content |
|--------|---------|
| **Date** | YYYY-MM-DD format |
| **Type** | Decision, Pivot, Blocker, Assumption Invalidated, External Shift, Learning, Idea |
| **Title** | Short summary (5-10 words), scannable headline |
| **Stage** | Milestone, step, and framework at the moment it happened |
| **Context** | What was happening? What prompted this? |
| **What** | Specific details: what was decided/changed/learned/imagined? |
| **Why** | Rationale or cause |
| **Implication** | Impact on project: next steps, timeline, scope, or strategy |

### Writing Guidelines

| Guideline | Description |
|-----------|-------------|
| **Be specific** | "Target HR managers at 50-500 person companies" not "Decided on target market" |
| **Include alternatives** | For Decisions, note what was considered and rejected |
| **Quantify** | "2 weeks," "18/20 interviews," "$500/mo," "4 weeks saved" |
| **Link to evidence** | Reference interviews, data sources, or framework docs |
| **Write for strangers** | Assume reader has no context about the project |

---

<!-- DOCUMENT CONTENT BELOW — Copy from here -->

# [Milestone Name] Founder Diary

**Project:** [Project Name]
**Milestone:** M[X] [Milestone Name]

---

## For AI Agents

**Template reference:** This document was created from [`founder_diary.md`](../../../../robotville/system/founder/templates/founder_diary.md). Agents MUST read the template before making updates.

**Understanding the process:** Read [`system/founder/founder_process.md`](../../../../robotville/system/founder/founder_process.md) for module structure, milestone navigation, and applicable frameworks.

---

## Session Status

[Current Framework paragraph — 280 chars max. Which milestone, step, and framework is active. What specific section or task is in progress.]

[Last Work Performed paragraph — 280 chars max. What was accomplished in the most recent session. Concrete outputs: sections written, decisions made, documents created.]

[Next Steps paragraph — 280 chars max. What needs to happen next. Specific enough that an agent can resume without additional context.]

---

## File Map

```
docs/founder/
├── [project]_memo.md               # [Brief description]
├── [milestone]/
│   ├── m[x]_founder_diary.md       # THIS FILE
│   └── [framework].md              # [Brief description]
└── [other_milestone]/
    └── m[y]_founder_diary.md       # [Brief description]
```

---

## Framework Status

| Framework | Status |
|---|---|
| [Framework name with link] | [Done/WIP/To-do] |

---

## Log

| Date | Type | Title | Stage | Context | What | Why | Implication |
|------|------|-------|-------|---------|------|-----|-------------|
| YYYY-MM-DD | [Type] | [Title] | [Stage] | [Context] | [What] | [Why] | [Implication] |

---