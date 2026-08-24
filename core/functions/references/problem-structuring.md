---
description: "Read when the ask is a vague, tangled, or solution-shaped problem that must be defined before anything can be solved — the two depths, the escalation trigger, and the MECE / problem-tree / pyramid treatment."
tags: [functions]
---

# Problem structuring — define and decompose

The user arrives with a mess: a vague goal, a symptom, or a solution with no stated problem. This mode ends with a problem stated precisely enough that the next move is obvious.

You bring the structure. The user brings the domain knowledge. NEVER generate the problem's content yourself — every category, driver, and constraint MUST come from what the user said or confirmed.

## Two depths — start shallow

**ALWAYS open at conversational depth.** Most problems dissolve in two or three exchanges, and opening with frameworks buries a simple problem in machinery it never needed.

### Conversational depth (default)

Open with one direct question — "what are you trying to figure out?" — and no preamble.

Then, ONE question per exchange, never a batch:

- **Clarify** — "what specifically about X?", "who is affected?", "what happens if you do nothing?"
- **Traction** — at least one per session. Traction questions target the user's relationship to the problem, not its content: "what's hard about this for you?", "what are you avoiding?", "what's clear versus fuzzy?" The value is the articulation, NEVER the information.
- **Surface structure organically** — group related points, name tensions, but NEVER use framework vocabulary at this depth. "MECE", "pyramid", and "problem tree" belong to the deep pass.

When the problem is clear, close it: a problem statement in one or two sentences, two or three concrete next steps, and "does this capture it, or is there more?"

### The escalation trigger

Assess after every exchange, silently. Escalate when ANY of these appears:

| Trigger | Why it exceeds conversation |
|---|---|
| Three or more distinct problem dimensions | Cannot be held in prose without gaps |
| Competing priorities or stakeholders | Needs explicit categories to avoid arguing past each other |
| Dependencies that must be decomposed before anything is actionable | Needs a tree |
| The user asks for more structure | Their call, no assessment needed |

Say what you are doing and why — "enough moving parts here that the full structuring treatment earns its cost" — and get a yes. The user NEVER re-explains anything: everything gathered so far carries into the deep pass unchanged.

Absent a trigger, staying conversational is the correct outcome, NEVER a failure to go deep.

### Deep depth (on trigger)

Run the sequence below in order. It is a real sequence — each stage consumes the one before it.

## The deep sequence

### 1. Classify the problem

The problem's type rules the shape of everything downstream:

| Type | Root question | Tree shape |
|---|---|---|
| **Diagnostic** | "Why is this happening?" | Causes, MECE-split |
| **Solution-seeking** | "How can we achieve X?" | Interventions, MECE-split |
| **Decision** | "Should we do X?" | Criteria, MECE-split |

State your read back — type, how clear the problem currently is, whether it is one problem or several tangled together — and let the user correct it before you build on it.

### 2. Deepen the context

Cover root cause, impact and cost of inaction, what has been tried, constraints, success criteria, and who decides. Ask in rounds — the highest-impact questions first, then follow-ups that the answers unlocked. Two or three rounds, four or five questions in the first, fewer after.

Where an answer depends on evidence neither of you holds — a number in the files, what a system actually does, market or competitor facts — DELEGATE it to the `investignosis` or `digest` functions (siblings of this one, when present) or to sub-agents, and keep questioning while it runs. NEVER halt the conversation to go read things yourself; the brainstorm dies when you leave it.

Close the stage by stating back the core issue, the key drivers, the constraints, and what "solved" looks like. Get confirmation.

### 3. Build the tree

Four layers at most, two to five branches per node:

| Layer | Contains | Question type |
|---|---|---|
| 1 (root) | The core question | Yes/No hypothesis |
| 2 | Major categories | Yes/No hypothesis |
| 3 | Sub-questions | Open-ended |
| 4 (only where needed) | Specific data or analysis needed | Open-ended |

Framing layers 1–2 as Yes/No hypotheses is what forces a MECE split; a tree of open questions at the top becomes aimless data-gathering. Established splits — Revenue × Volume, Revenue − Costs, Fixed + Variable, 3Cs, 4Ps — are MECE by construction; prefer one where it fits. Draw the tree in the chat as an ASCII tree.

Two layers is too shallow to reach anything actionable; five or more gets lost in the weeds.

### 4. Validate MECE at every level

MECE = Mutually Exclusive, Collectively Exhaustive. Test each horizontal level, one level at a time:

- **ME** — "does any item belong in two of these branches?" An overlap double-counts.
- **CE** — "is there anything real that fits in none of them?" A gap is a missed cause.

The dominant violation is **mixed dimensions** — "large companies, tech companies, new companies" splits on size, industry, and age at once, and therefore both overlaps and gaps. ONE dimension per level, always. Test with edge cases; the first draft rarely passes.

Report each level's result and the fix for anything that failed. NEVER present a tree whose levels you have not tested.

### 5. Refine the problem statement

The payload of the whole exercise, in one sentence:

> **[stakeholder]** needs to **[understand / decide / solve]** **[specific issue]** in order to **[outcome]**, constrained by **[key constraints]**.

Then name the two or three branches most likely to yield the answer, and why.

### 6. Pyramid it for communication

The user has to carry this to someone else. Structure it answer-first: the main message on top, two to four supporting arguments under it — each MECE with the others, each with the evidence that backs it and the data still missing.

Answer-first is the whole point. "Growth is anemic, this market is attractive, we're positioned to enter it, so we should enter health food" buries the lead; "we should enter health food, because growth is anemic, it's the most attractive market, and we're positioned for it" survives being cut off after the first line.

Give the user the depth ladder explicitly — what to present with five minutes, with two, with thirty seconds.

## Done when

The user can state the problem in one sentence, name what is inside it and what is outside it, and name the first thing to investigate. Structure past that point is decoration.
