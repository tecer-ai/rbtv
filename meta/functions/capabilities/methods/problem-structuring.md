# Problem structuring

The result: the problem is stated precisely enough that the next move is obvious. The user can state it in one sentence, name what is inside it and what is outside it, and name the first thing to investigate.

Inputs: what the user brought, which is a vague goal, a symptom, or a solution with no stated problem. When the user has not yet said what they are trying to figure out, the opening question below asks for it.

You supply the structure and the user supplies the domain knowledge. Every category, driver and constraint comes from what the user said or confirmed; do not generate the problem's content yourself.

There are two depths. Open at conversational depth every time: most problems are settled in two or three exchanges. Go to deep depth only on a trigger.

## Conversational depth

Open with one direct question, "what are you trying to figure out?", and no preamble. Then ask one question per exchange, not a batch:

- Clarifying questions: "what specifically about X?", "who is affected?", "what happens if you do nothing?"
- Traction questions, at least one per session. A traction question is about the user's relationship to the problem, not its content: "what's hard about this for you?", "what are you avoiding?", "what's clear versus fuzzy?" Its value is that the user articulates the answer, not the information in it.

Group related points and name tensions as they appear, in ordinary words. Do not use the words "MECE", "pyramid" or "problem tree" at this depth.

When the problem is clear, close: a problem statement of one or two sentences, two or three concrete next steps, and the question "does this capture it, or is there more?"

## The escalation trigger

After every exchange, assess whether one of these has appeared, without telling the user:

| Trigger | Why conversation no longer holds it |
|---|---|
| Three or more distinct dimensions of the problem | Prose cannot hold them without gaps |
| Competing priorities or stakeholders | Explicit categories are needed for the parties to discuss the same thing |
| Dependencies that must be decomposed before anything is actionable | A tree is needed |
| The user asks for more structure | The user decides; no assessment is needed |

When one appears, tell the user that you propose the deep sequence and which trigger led to it, and get a yes. Everything gathered so far carries into the deep sequence unchanged; do not ask the user to explain any of it again.

When no trigger appears, staying at conversational depth is the correct result.

## The deep sequence

Run the six stages in order: each uses the result of the one before it.

### 1. Classify the problem

| Type | Root question | Tree shape |
|---|---|---|
| Diagnostic | "Why is this happening?" | Causes, MECE-split |
| Solution-seeking | "How can we achieve X?" | Interventions, MECE-split |
| Decision | "Should we do X?" | Criteria, MECE-split |

State your reading to the user: the type, how clear the problem is now, and whether it is one problem or several mixed together. Let the user correct it before you continue.

### 2. Deepen the context

Cover the root cause, the impact and the cost of doing nothing, what has been tried, the constraints, the success criteria, and who decides. Ask in two or three rounds: four or five questions in the first, the ones with the highest impact; fewer in each later round, the follow-ups those answers opened.

Close the stage by stating back the core issue, the key drivers, the constraints and what "solved" looks like, and get the user's confirmation.

### 3. Build the tree

Build three or four layers, with two to five branches per node. Two layers do not reach anything actionable; five or more lose the question.

| Layer | Contains | Question type |
|---|---|---|
| 1 (root) | The core question | Yes/No hypothesis |
| 2 | Major categories | Yes/No hypothesis |
| 3 | Sub-questions | Open-ended |
| 4 (only where needed) | The specific data or analysis needed | Open-ended |

Write layers 1 and 2 as Yes/No hypotheses: that framing forces a MECE split, and open questions at the top lead to gathering data without a direction. Where an established split fits (Revenue × Volume, Revenue − Costs, Fixed + Variable, 3Cs, 4Ps), use it; these are MECE by construction. Draw the tree in the chat as an ASCII tree.

### 4. Validate MECE at every level

MECE means mutually exclusive, collectively exhaustive. Test each horizontal level of the tree, one level at a time, with edge cases:

- Mutually exclusive: "does any item belong in two of these branches?" An overlap counts the item twice.
- Collectively exhaustive: "is there anything real that fits in none of them?" A gap is a missed cause.

Split each level on one dimension. The most frequent violation is mixed dimensions: "large companies, tech companies, new companies" splits on size, industry and age at once, so it has both overlaps and gaps.

Report the result of each level and the fix for each level that failed. Do not present a tree with a level you have not tested.

### 5. Refine the problem statement

Write the problem in one sentence of this form:

> **[stakeholder]** needs to **[understand / decide / solve]** **[specific issue]** in order to **[outcome]**, constrained by **[key constraints]**.

Then name the two or three branches most likely to yield the answer, and why.

### 6. Pyramid it for communication

The user will present this to someone else. Structure it answer-first: the main message on top, and under it two to four supporting arguments that are MECE with one another, each with the evidence that backs it and the data still missing.

Answer-first means the conclusion is the first clause. "Growth is anemic, this market is attractive, we're positioned to enter it, so we should enter health food" puts the conclusion last; "we should enter health food, because growth is anemic, it's the most attractive market, and we're positioned for it" still delivers it when the listener stops after the first line.

Give the user the three versions explicitly: what to present with five minutes, with two minutes, and with thirty seconds.

## Done when

The user can state the problem in one sentence, name what is inside it and what is outside it, and name the first thing to investigate. Add no structure past that point.
