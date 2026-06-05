---
name: 'step-04-shrink'
description: 'Aggressively shrink the problem to its atomic unit and commit to what v1 is NOT doing.'
nextStepFile: './step-05-architect.md'
---

# Step 4: Aggressively Shrink the Problem

**Progress: Step 4 of 6** — Next: Senior Architect Review

_Re-entry point for [S] Shrink-again loops from Step 6 — each pass appends a new Shrink Round._

---

## STEP GOAL

Find the atomic unit — the single irreducible loop that delivers the value — and commit, in writing, to what v1 is NOT doing.

---

## MANDATORY EXECUTION RULES

- ✂️ Every pass through this step MUST remove something concrete — a shrink round that removes nothing is a failed round
- 🚫 NEVER add features here — a new feature mid-shrink goes to the NOT-doing list or dies
- 📏 The NOT-doing list is the deliverable, not a side note — the brief is a commitment to exclusion

---

## MANDATORY SEQUENCE

### 1. State the Problem at Current Size

One sentence, from the memo's current state (Reframe + Surviving Gap). On a shrink-loop re-entry, also state the failing signal Step 6 sent you back with.

### 2. Force the Atomic Unit

> "What is the atomic unit here — the smallest reframing that still contains the value?"

Drive old-problem → new-problem reductions until irreducible (example: "help people manage their digital lives" → "screenshots represent intent without follow-through" — and a gallery app becomes a reminder engine). Then define the **core loop** in 3-5 numbered steps.

### 3. Commit to NOT Doing

| Excluded from v1 | Why | Revisit when |
|------------------|-----|--------------|

Pull candidates from: parked solutions (Step 1), graveyard rule-outs (Step 3), and every "cool feature" mentioned so far. Each exclusion is a commitment, not a maybe.

### 4. One-Week Smell Test (pre-check)

Eyeball the core loop: does it smell buildable in about a week? If it is obviously bigger, shrink AGAIN within this step before continuing — never carry known fat into the architect review. (The formal one-week test runs at Step 6.)

### 5. Append to Memo

First pass appends `## Atomic Unit`. Loop re-entries append `## Atomic Unit — Shrink Round {N}` and increment frontmatter `shrinkRounds`. NEVER rewrite earlier rounds.

```markdown
## Atomic Unit{ — Shrink Round {N}}

- **Problem at entry:** {one sentence}
- **Atomic unit:** {the irreducible problem}
- **What this makes the product:** {e.g., "a reminder engine for visual intent, not a gallery app"}

### Core Loop
1. {step}

### NOT Doing (v1 commitments)
{table}
```

### 6. Present Menu

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 5: Senior Architect Review |
| **[K] Kill idea** | Shrinking revealed there is no atomic unit — record the kill |

HALT and WAIT for user input.

---

## ON CONTINUE

1. Update memo frontmatter: add `step-04-shrink` to `stepsCompleted` (append `-round-{N}` on loop re-entries)
2. Save the memo
3. Load `./step-05-architect.md` and follow it exactly

## ON KILL

1. Ask one line: "What killed it?"
2. Append to memo:

```markdown
## Verdict — KILL

- **Killed at:** step-04-shrink
- **Cause:** {one sentence}
- **What would revive it:** {condition, or "nothing visible"}
```

3. Update frontmatter: `verdict: kill`, `killedAtStep: step-04-shrink`, `status: complete`, add `step-04-shrink` to `stepsCompleted`. Save.
4. Close in character: an idea with no atomic unit was never buildable — weeks saved. Return control to the domcobb agent menu.
