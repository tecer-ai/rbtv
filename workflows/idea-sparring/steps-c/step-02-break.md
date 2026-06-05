---
name: 'step-02-break'
description: 'Break the idea, not build it — probe wrong assumptions, the non-problem case, and the hidden psychology; force a reframe.'
nextStepFile: './step-03-eliminate.md'
---

# Step 2: Break the Idea, Not Build It

**Progress: Step 2 of 6** — Next: Research to Eliminate

---

## STEP GOAL

Find the "why" behind the friction — probe the psychology of the problem until the real problem surfaces, or the idea dissolves.

---

## MANDATORY EXECUTION RULES

- 🥊 Argue AGAINST the idea genuinely — no strawman counter-cases, no token pushback
- 🗣️ ONE probe at a time — conversational pacing, never a wall of questions
- 🛑 The user answers; you propose candidates and challenge — NEVER answer your own probes
- ✅ The reframe MUST be falsifiable — "people want X" is not a finding; "users do A because B, so the real problem is C" is

---

## MANDATORY SEQUENCE

Work the three probes IN ORDER, one at a time. Record findings after each before moving on.

### 1. Probe — Wrong Assumptions

> "What assumptions are you making here that might be wrong?"

Propose the 3-5 riskiest assumptions you detect in the Idea Dump. For each, the user confirms, corrects, or adds. Record: assumption | confidence (low/med/high) | what would falsify it.

### 2. Probe — The Non-Problem Case

> "Why might this be a non-problem for most people?"

Make the strongest genuine case that nobody needs this — current behavior is fine, workarounds are cheap, the pain is momentary. The user must beat the case with specifics, not enthusiasm.

### 3. Probe — Hidden Psychology

> "What is the hidden cognitive load here? What does the current behavior actually give people?"

Dig for the psychological payoff of the status quo (example: taking a screenshot grants cognitive closure — the brain files the item as "handled" and stops thinking about it). The real problem usually hides here.

### 4. Force the Reframe

Compress the findings into a one-sentence shift:

> **Old framing:** {what the user thought the problem was}
> **New framing:** {what the probing revealed}

If no reframe survives — the problem dissolved under probing — say so plainly and recommend **[K] Kill**.

### 5. Append to Memo

```markdown
## Break Findings

### Assumptions at Risk
| Assumption | Confidence | What would falsify it |
|------------|------------|----------------------|

### The Non-Problem Case
{strongest case against, and how — or whether — the user beat it}

### Hidden Psychology
{the payoff of the status quo}

### Reframe
- **Old:** {old framing}
- **New:** {new framing}
```

### 6. Present Menu

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 3: Research to Eliminate |
| **[K] Kill idea** | The problem dissolved — record the kill |

HALT and WAIT for user input.

---

## ON CONTINUE

1. Update memo frontmatter: add `step-02-break` to `stepsCompleted`
2. Save the memo
3. Load `./step-03-eliminate.md` and follow it exactly

## ON KILL

1. Ask one line: "What killed it?"
2. Append to memo:

```markdown
## Verdict — KILL

- **Killed at:** step-02-break
- **Cause:** {one sentence}
- **What would revive it:** {condition, or "nothing visible"}
```

3. Update frontmatter: `verdict: kill`, `killedAtStep: step-02-break`, `status: complete`, add `step-02-break` to `stepsCompleted`. Save.
4. Close in character: a kill this early saved weeks of building. Return control to the domcobb agent menu.
