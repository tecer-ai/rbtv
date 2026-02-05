---
name: 'step-03-risk-ranking'
description: 'Score failure modes by likelihood x severity, identify top 5-8 risks'
nextStepFile: './step-04-mitigations.md'
outputFile: '{outputFolder}/pre-mortem.md'
---

# Step 3: Risk Ranking

**Progress: Step 3 of 5** — Next: Mitigations

---

## STEP GOAL

Score each failure mode on Likelihood (1-5) and Severity (1-5), compute Risk Score = L × S, and identify the top 5-8 failures that demand mitigation.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor forcing honest risk assessment. Challenge every low uncertainty score. If nothing scores above 15, push back: "Are you being honest about likelihood and severity?"

### Step-Specific Rules
- MUST score every failure mode from Step 2
- MUST challenge optimistic scoring — the most dangerous risks are the ones we downplay
- MAY merge truly duplicative failure modes NOW (not during brainstorming)
- At least one failure mode should score 15+ (if none do, challenge honesty)

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/pre-mortem.md` for Raw Failure Mode Inventory
2. Reference M2 framework outputs for evidence to inform scoring

---

## MANDATORY SEQUENCE

### 1. Present Scoring Scales

Display the Likelihood and Severity scales:

**Likelihood Scale (1-5)**

| Score | Meaning |
|-------|---------|
| 5 | **Near certain** — Multiple signals already point to this. Would be surprising if it did NOT happen. |
| 4 | **Probable** — More likely than not given current evidence. |
| 3 | **Possible** — Could go either way. Evidence is mixed or absent. |
| 2 | **Unlikely** — Would require several things to go wrong simultaneously. |
| 1 | **Remote** — Theoretically possible but requires extreme bad luck or negligence. |

**Severity Scale (1-5)**

| Score | Meaning |
|-------|---------|
| 5 | **Fatal** — Project dies. No recovery path. |
| 4 | **Crippling** — Major pivot required. Months of work lost. |
| 3 | **Serious** — Significant setback. Recovery possible but expensive. |
| 2 | **Moderate** — Noticeable impact. Can be managed with effort. |
| 1 | **Minor** — Inconvenience. Normal course correction. |

**Risk Score = Likelihood × Severity** (range 1-25)

### 2. Merge Duplicates (Optional)

Review the failure mode inventory for true duplicates:
- If two modes describe the same underlying cause, combine them
- Take the higher scores from each
- Document the merge: "Merged modes X and Y → combined as Z"

Do NOT over-merge. Different symptoms of the same root cause should remain separate if they have different severity profiles.

### 3. Score Each Failure Mode

For each failure mode:
1. Assess Likelihood (1-5) with brief justification
2. Assess Severity (1-5) with brief justification
3. Compute Risk Score = L × S

Present scoring proposals to user for confirmation/adjustment:

> "**[Category]: [Failure mode summary]**
> - Likelihood: [score] — [justification]
> - Severity: [score] — [justification]
> - Risk Score: [L × S]"

### 4. Challenge Low Scores

If a failure mode was derived from a Leap of Faith kill criterion but scores low:
> "This failure mode maps to a kill criterion you identified as existential. Are you sure about the low score?"

If no failure mode scores above 15:
> "No failure modes score above 15. Either we missed critical risks in brainstorming, or we're being optimistic. Let's revisit: which of these could actually kill the project?"

### 5. Build Ranked Failure Table

Sort all failure modes by Risk Score descending:

```markdown
## Ranked Failure Table

| Rank | Category | Failure Mode | L | S | Risk |
|------|----------|--------------|---|---|------|
| 1 | [cat] | [mode summary] | 5 | 5 | 25 |
| 2 | [cat] | [mode summary] | 4 | 5 | 20 |
| ... | ... | ... | ... | ... | ... |
```

### 6. Draw Cutoff Line

Identify the top failures that account for the majority of total risk:
- Typically top 5-8 failures
- These become the "must mitigate" list for Step 4

Present:
> "**Top Failures (Cutoff Line)**
>
> These [N] failure modes represent the highest existential risk:
> [list top failures with scores]
>
> These will receive mitigation cards in the next step."

### 7. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — revisit scores for specific failure modes
- **[P] Party Mode** — get multi-agent perspectives on risk prioritization
- **[C] Continue** — proceed to Mitigations

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update pre-mortem.md with Ranked Failure Table and top failures shortlist
2. Update frontmatter: add `step-03-risk-ranking` to `stepsCompleted`
3. Load `./step-04-mitigations.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All failure modes scored with justifications, sorted by Risk Score, top 5-8 identified for mitigation, at least one mode scores 15+

❌ **FAILURE:** Scoring without justification, no modes above 15 without challenge, fewer than 5 or more than 10 in top failures list
