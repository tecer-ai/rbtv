---
---

# Template Instructions: Project Memo

**Purpose:** This template creates Amazon 6-pager style narrative memos for documenting project progress across all founder milestones. The memo serves as the single source of truth for project vision, progress, and current state.

**Naming Convention:** `[project]_memo.md` (e.g., `robotville_memo.md`)

**Location:** `[project]/docs/founder/[project]_memo.md`

---

## Format Inspiration

This template is inspired by Amazon's 6-pager memo format:
- **Narrative prose**, not bullet points
- **Natural language**, minimal markdown (only use `##` for section headers)
- **Dense with information**, but clear and readable
- **Customer-focused**, not feature-focused

---

## Section Length Guidance

| Section | Maximum Length |
|---------|----------------|
| Introduction | 2 pages |
| Problem | 2 pages |
| Solution | 2 pages |
| Tenets | 2 pages |
| Progress (entire section) | No limit |
| Open Questions | 1 page |
| Next Steps | 1 page |
| Appendix | No limit |

**Special Rule:** Problem, Solution, and Tenets MUST fit on the same page together (total ~1 page combined) during early stages. They grow as frameworks are applied.

**Philosophy:** No bullshitting to fill space. If a section is short during conception, that's fine. Content grows organically as frameworks are applied and milestones progress.

---

## AI Navigation Instructions

Include this in the Status section of every instance:

**Template reference:** This document was created from [`project_memo.md`](../../../system/founder/templates/project_memo.md). Agents MUST read the template before making updates.

**Understanding the process:** To understand this project's process, first read [`system/founder/founder_process.md`](../../../system/founder/founder_process.md), then navigate via [`system/map/index.md`](../../../system/map/index.md) to find milestone process documents and applicable frameworks.

**Working instructions:** All agents working on this project must read the current milestone's founder log before performing any task related to the project and update it after work sessions.

---

## Status Section Template

Include this table at the top of every instance, immediately after the title and before the AI Navigation Instructions:

| Current Milestone | Current Focus | Next Step | Last Updated |
|-------------------|---------------|-----------|--------------|
| [Milestone name] | [What we're working on now] | [Immediate next action] | YYYY-MM-DD |

---

## Document Body Sections

The following sections form the body of the project memo:

### 1. Introduction

**What to include:**
- Project vision in 2-3 sentences
- Origin story: Why does this project exist?
- Target customer in one sentence
- Current stage and progress summary

**Tone:** Compelling, clear, sets context for everything that follows.

---

### 2. Problem

**What to include:**
- Customer problem in narrative form
- Why existing solutions fail
- Evidence this problem matters (qualitative, not quantitative yet)
- Scope: what's in/out of scope

**Tone:** Customer-centric, empathetic, specific.

**Guidance:** Start short during conception. Grows richer as validation and customer discovery progress.

---

### 3. Solution

**What to include:**
- Solution approach in narrative form
- Why this solution addresses the problem
- Key differentiators vs. alternatives
- High-level capabilities (not feature list)

**Tone:** Clear, confident, focused on customer value.

**Guidance:** Start high-level during conception. Becomes more specific as prototyping and validation progress.

---

### 4. Tenets

**What to include:**
- 3-7 core principles guiding all project decisions
- Each tenet should be:
  - Non-obvious (not "quality matters")
  - Opinionated (creates trade-offs)
  - Enduring (won't change milestone to milestone)

**Format:** Short statement + 1-2 sentence explanation per tenet.

**Example:**
> **Start with the end-user, not the administrator.** We optimize for the person doing the work, even if it means more setup for IT. This trade-off is intentional.

---

### 5. Progress

**What to include:** Subsection per milestone documenting completed work, key insights, and links to framework documents.

**Subsections:**
- Conception
- Validation
- Brand
- Prototypation
- Market Validation
- MVP

**Format per subsection:**
```
### [Milestone Name]

[Narrative summary of work completed, 1-3 paragraphs]

**Completed Frameworks:**
- [Framework Name] — [Key insight in one sentence] — [Link to applied framework doc]

**Key Decisions:** [Reference to founder log entries if significant decisions were made]
```

**Guidance:** Only populate subsections for completed or in-progress milestones. Leave future milestones empty or with placeholder text.

---

### 6. Open Questions

**What to include:**
- Unresolved strategic questions
- Assumptions that need testing
- Trade-offs that need decisions
- External dependencies pending resolution

**Format:** Numbered list with 1-sentence context per question.

**Guidance:** Prune resolved questions. Keep this section current.

---

### 7. Next Steps

**What to include:**
- Immediate next actions (next 1-4 weeks)
- Clear owners (if applicable)
- Dependencies that must be resolved first

**Format:** Numbered list of concrete, actionable items.

**Guidance:** Keep tactical and near-term. Long-term roadmap lives elsewhere.

---

### 8. Appendix

**What to include:**
- Supporting data that's too detailed for main sections
- Links to external resources
- Historical decisions that no longer apply but provide context

**Guidance:** Use sparingly. If it's important, it belongs in main sections.

---

---

<!-- DOCUMENT CONTENT BELOW — Copy from here -->

# [Project Name] Project Memo

| Current Milestone | Current Focus | Next Step | Last Updated |
|-------------------|---------------|-----------|--------------|
| [Milestone] | [Focus] | [Next Step] | YYYY-MM-DD |

---

## For AI Agents

**Template reference:** This document was created from [`project_memo.md`](../../../system/founder/templates/project_memo.md). Agents MUST read the template before making updates.

**Understanding the process:** To understand this project's process, first read [`system/founder/founder_process.md`](../../../system/founder/founder_process.md), then navigate via [`system/map/index.md`](../../../system/map/index.md) to find milestone process documents and applicable frameworks.

**Working instructions:** All agents working on this project must read the current milestone's founder log before performing any task related to the project and update it after work sessions.

---

## Introduction

[Project vision, origin story, target customer, current stage]

---

## Problem

[Customer problem description, why existing solutions fail, evidence, scope]

---

## Solution

[Solution approach, why it addresses the problem, key differentiators, high-level capabilities]

---

## Tenets

**[Tenet 1 Name]**
[Explanation of tenet 1]

**[Tenet 2 Name]**
[Explanation of tenet 2]

**[Tenet 3 Name]**
[Explanation of tenet 3]

---

## Progress

### Conception

[Work completed during conception milestone]

**Completed Frameworks:**
- [Framework] — [Key insight] — [Link]

### Validation

[Work completed during validation milestone]

### Brand

[Work completed during brand milestone]

### Prototypation

[Work completed during prototypation milestone]

### Market Validation

[Work completed during market validation milestone]

### MVP

[Work completed during MVP milestone]

---

## Open Questions

1. [Question 1]
2. [Question 2]
3. [Question 3]

---

## Next Steps

1. [Action 1]
2. [Action 2]
3. [Action 3]

---

## Appendix

[Supporting materials, external links, historical context]

---