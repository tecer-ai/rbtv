---
name: 'step-03-eliminate'
description: 'Research to eliminate, not validate — map the graveyard of similar attempts and find reasons to quit early.'
nextStepFile: './step-04-shrink.md'
---

# Step 3: Research to Eliminate, Not Validate

**Progress: Step 3 of 6** — Next: Shrink to the Atomic Unit

---

## STEP GOAL

Use research to find reasons to QUIT — map what already exists, where it stops being useful, and what already died. Surviving this step requires a specific gap, not optimism.

---

## MANDATORY EXECUTION RULES

- 🪦 You research to eliminate — finding a reason to quit early is a SUCCESS, not a setback
- 🔎 You MUST invoke the `rbtv-web-searching` skill (Research mode) for the graveyard scan and follow it exactly — no unsourced market claims
- 🤖 If you dispatch sub-agents for research, every sub-agent prompt MUST instruct: "Invoke the `rbtv-web-searching` skill before any web work and follow it exactly."
- ❓ The behavior-vs-tooling question MUST be answered explicitly before leaving this step

---

## MANDATORY SEQUENCE

### 1. Frame the Graveyard Queries

From the reframed problem (Step 2), derive the research questions:

- "What have other tools, products, or attempts in this space already tried?"
- "Where do they stop being useful?"
- "Is this actually a behavior problem or just a tooling problem?"

### 2. Run the Research

Invoke the `rbtv-web-searching` skill (Research mode) on the graveyard queries. Target existing tools, abandoned products, prior attempts, and post-mortems — not success stories.

### 3. Build the Graveyard Map

```markdown
| Attempt / tool | What it does | Where it stops | Status (thrives/limps/dead) |
|----------------|--------------|----------------|------------------------------|
```

### 4. Rule Things Out

List approaches that die NOW based on the map — example: anything that demands discipline from a user already under cognitive load is dead on arrival. Each rule-out: approach + why it is dead.

### 5. The Survival Question

> "Given this graveyard, why does this still deserve to exist?"

The answer MUST name a specific gap the existing tools leave open (example: "they all stop at retrieval — nothing closes the loop between captured intent and action"). "We'll do it better" is NOT a gap. If no specific gap survives, recommend **[K] Kill**.

### 6. Append to Memo

```markdown
## Elimination Research

### Graveyard Map
{table}

### Ruled Out Now
- {approach} — {why dead}

### Behavior or Tooling?
{explicit answer + one line of reasoning}

### The Surviving Gap
{the specific gap, or the kill recommendation}
```

### 7. Present Menu

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 4: Shrink to the Atomic Unit |
| **[K] Kill idea** | The graveyard won — record the kill |

HALT and WAIT for user input.

---

## ON CONTINUE

1. Update memo frontmatter: add `step-03-eliminate` to `stepsCompleted`
2. Save the memo
3. Load `./step-04-shrink.md` and follow it exactly

## ON KILL

1. Ask one line: "What killed it?"
2. Append to memo:

```markdown
## Verdict — KILL

- **Killed at:** step-03-eliminate
- **Cause:** {one sentence}
- **What would revive it:** {condition, or "nothing visible"}
```

3. Update frontmatter: `verdict: kill`, `killedAtStep: step-03-eliminate`, `status: complete`, add `step-03-eliminate` to `stepsCompleted`. Save.
4. Close in character: the graveyard saved you weeks. Return control to the domcobb agent menu.
