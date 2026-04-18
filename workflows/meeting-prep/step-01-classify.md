---
name: step-01-classify
description: Identify meeting type and sweep workspace for relevant context files
nextStepFile: step-02-discover.md
---

# Step 1: Classify & Context Sweep

**Progress: Step 1 of 3** — Next: Discover

---

## STEP GOAL

Determine the meeting type and find existing workspace files related to the other party — before any deep discovery begins.

---

## MANDATORY EXECUTION RULES

- NEVER classify without asking the user about the meeting first
- NEVER read workspace files without user approval — present what you found and ask
- NEVER proceed to discovery without a confirmed meeting type

---

## MANDATORY SEQUENCE

### 1. Capture Meeting Basics

Ask the user:

| Question | Purpose |
|----------|---------|
| What is this meeting about? | Core topic |
| Who is the other party? (person, company, or both) | Context sweep target |
| Why do you need a cheat sheet for this one? | Surfaces the real preparation need |

If the user provided some of this in their initial prompt, acknowledge what you already know and ask only for what's missing.

### 2. Classify Meeting Type

Based on the user's answers, classify into one of these types:

| Type | Primary signal |
|------|---------------|
| **Sales / Demo** | Presenting product or service to a potential buyer |
| **Investor** | Pitching to or meeting with a fund, angel, or advisor about funding |
| **Negotiation** | Terms, pricing, contracts, deal-making with known counterparty |
| **Partnership** | Exploring or formalizing collaboration between organizations |
| **Discovery** | Learning from someone — research, user interviews, expert consultation |
| **Advisory / Board** | Meeting with mentor, advisor, or board member for guidance |
| **Hiring / Interview** | Evaluating or being evaluated for a role |
| **Crisis / Damage Control** | Meeting after something went wrong — trust repair, incident response |

Present the classification:

> **Meeting type detected:** {type}
> **Why:** {1-2 sentences explaining the classification}
>
> Correct?

HALT. Wait for user confirmation. If they disagree, reclassify.

### 3. Context Sweep

Search the workspace for files related to the other party. Use the party's name, company name, and any aliases to search:

- File and folder names matching the other party
- Meeting notes, debriefs, or prior cheat sheets mentioning them
- Profile files, status files, or any structured entity data
- Prior correspondence or communications

**Present what you found — do NOT read the files yet:**

> **Files found related to {other party}:**
>
> | # | File | Why it might be relevant |
> |---|------|------------------------|
> | 1 | `{path}` | {brief reason} |
> | 2 | `{path}` | {brief reason} |
> | ... | ... | ... |
>
> Which of these should I read? (all / numbers / none)

HALT. Wait for user selection. Read ONLY the files the user approves.

If no files are found, inform the user: "No existing files found about {other party}. We'll build context from scratch in the discovery step."

### 4. Load Type Data File

Read `{rbtv_path}/workflows/meeting-prep/data/type-{classified-type}.md`. This file contains the discovery questions and output skeleton for the next steps.

### 5. Present Summary

> **Meeting:** {brief description}
> **Type:** {type}
> **Other party:** {name/company}
> **Context loaded:** {list of files read, or "none — building from scratch"}
>
> Ready to proceed to discovery?

---

## Step Menu

| Option | Action |
|--------|--------|
| [C] Continue | Proceed to Step 2 — Discover |
| [X] Exit | Stop workflow |

HALT and WAIT for user input.
