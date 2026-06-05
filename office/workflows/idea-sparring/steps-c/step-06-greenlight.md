---
name: 'step-06-greenlight'
description: 'Run the three green-light signals and close with a verdict — BUILD with a light MVP brief, KILL with cause, or loop back to shrink.'
nextStepFile: null
altStepFile: './step-04-shrink.md'
---

# Step 6: The Green-Light Gate

**Progress: Step 6 of 6** — Final step

---

## STEP GOAL

Decide when to stop thinking and start building — with evidence, not enthusiasm. Close the memo with a verdict.

---

## MANDATORY EXECUTION RULES

- 🚦 The green light is evidence-based — enthusiasm, sunk thinking time, and "it feels ready" are NOT signals
- ⛔ NEVER green-light with an unresolved black box — signal 2 is binary
- 📄 The brief stays LIGHT — four sections only; full PRD authoring is out of scope (hand off to product-lifecycle plugins)
- 🔁 When frontmatter `shrinkRounds` ≥ 2, a third [S] is suspicious — say so and put [K] on the table

---

## MANDATORY SEQUENCE

### 1. Run the Three Signals

| # | Signal | Test | Pass? |
|---|--------|------|-------|
| 1 | The brief is boring | Every addition since Step 4 refines error states and edge cases — no new "cool features" | yes/no |
| 2 | No more black boxes | Every black box from Step 5 has a clear yes/no answer, or a defined ≤1-day spike to get one | yes/no |
| 3 | One-week test | Decompose the core loop into rough build days — total ≤ 1 week | yes/no |

Present the table filled, with one line of evidence per row.

### 2. Verdict Gate

| Signals | Verdict |
|---------|---------|
| 3/3 pass | **[B] Build** |
| Signal 2 or 3 fails | **[S] Shrink again** — back to Step 4 |
| Signal 1 fails | Strip the new features into NOT-doing, re-run the signals once; still failing → [S] |
| A fatal flaw resurfaced | **[K] Kill** |

State your recommended verdict with the failing evidence. The user decides.

### 3. Present Menu

| Option | Action |
|--------|--------|
| **[B] Build** | Green-lit — write the MVP brief and close |
| **[S] Shrink again** | Loop back to Step 4 with the failing signal as input |
| **[K] Kill idea** | Record the kill and close |

HALT and WAIT for user input.

---

## ON BUILD

1. Append the light MVP brief — four sections, pulled from the memo. Write nothing the sparring did not surface:

```markdown
## Verdict — BUILD

### Green-Light Evidence
{signals table}

## MVP Brief (light)

### The Problem
{plain human language — from the Reframe and Atomic Unit}

### The Non-Goals
{from the NOT-doing table}

### The User Flow
{core loop, step A to step Z}

### The Tech Stack
{each choice validated against the Architect Review constraints — name the constraint it satisfies}
```

2. Developer-clarity pass — read the brief as a developer:

> "Where would a developer have to stop and ask for clarification?"

List the stop-points; resolve each in one line or mark it as a named ≤1-day spike.

3. Update frontmatter: `verdict: build`, `status: complete`, add `step-06-greenlight` to `stepsCompleted`. Save.

4. Present handoffs:

> "💡 **Sparring complete — idea green-lit.** Natural next moves:
> - `/rbtv-innovator` (M1-M2) — validate the business around it: Lean Canvas, assumption mapping, unit economics
> - `/rbtv-product-discoverer` — structure competitor research into a V1 product definition
> - A product-lifecycle plugin (e.g., BMM `create-product-brief`) — turn the light brief into a full PRD
> - Or open the IDE — when the fear of not building outweighs the fear of building the wrong thing, build."

5. Return control to the domcobb agent menu.

## ON SHRINK

1. Update frontmatter: increment `shrinkRounds`, add `step-06-greenlight-round-{N}` to `stepsCompleted`. Save.
2. Load `./step-04-shrink.md` and follow it exactly, carrying the failing signal as the shrink target.

## ON KILL

1. Ask one line: "What killed it?"
2. Append to memo:

```markdown
## Verdict — KILL

- **Killed at:** step-06-greenlight
- **Cause:** {one sentence}
- **What would revive it:** {condition, or "nothing visible"}
```

3. Update frontmatter: `verdict: kill`, `killedAtStep: step-06-greenlight`, `status: complete`, add `step-06-greenlight` to `stepsCompleted`. Save.
4. Close in character: the gate did its job — a wrong build was stopped at the last door. Return control to the domcobb agent menu.
