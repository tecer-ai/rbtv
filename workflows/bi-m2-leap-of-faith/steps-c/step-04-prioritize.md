---
name: 'step-04-prioritize'
description: 'Score assumptions by impact x uncertainty, identify top 5-10 leap-of-faith bets'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/leap-of-faith.md'
---

# Step 4: Prioritize Assumptions

**Progress: Step 4 of 5** — Next: Synthesis & Kill Criteria

---

## STEP GOAL

Score every assumption on Impact and Uncertainty, identify the top 5-10 true leap-of-faith assumptions, and articulate explicit Leap-of-Faith Statements for each.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Founders systematically underrate uncertainty on assumptions they care about most. Challenge every low uncertainty score. If nothing makes them uncomfortable, they haven't been honest enough.

### Step-Specific Rules
- MUST score ALL assumptions — no skipping
- Challenge any Uncertainty score of 1 or 2 if there's no direct evidence from target customers
- At least one assumption in the top 10 should make the founder uncomfortable to read aloud
- Top assumptions must include BOTH Value and Growth hypotheses

---

## CONTEXT BOUNDARIES

**Available context:**
- Classified Assumption Register from Step 3
- M1 artefacts for evidence review
- Framework methodology

**Out of scope:**
- Validation signal design (Step 5)
- Kill criteria definition (Step 5)

---

## MANDATORY SEQUENCE

### 1. Explain Scoring Framework

Present to founder:

> "We'll score each assumption on two dimensions:
>
> **Impact (1-5):** If this assumption is wrong, how severely does it damage the venture?
> - 5 = Concept collapses entirely, no viable business
> - 4 = Major pivot required
> - 3 = Significant redesign needed but path exists
> - 2 = Moderate adjustment required
> - 1 = Minor parameter change, easily adapted
>
> **Uncertainty (1-5):** How confident are you this is true today?
> - 5 = Pure speculation, founder intuition only
> - 4 = Indirect or analogical evidence only
> - 3 = Some evidence but not from our target segment
> - 2 = Direct evidence but limited sample size
> - 1 = Well-established with multiple data points
>
> **Priority Score** = Impact × Uncertainty
>
> High Impact + High Uncertainty = True leap-of-faith assumptions"

### 2. Score Each Assumption

For each assumption in the Classified Register:

1. Read statement aloud
2. Ask founder: "If this is wrong, what happens?" → Impact score
3. Ask founder: "What evidence do you have this is true?" → Uncertainty score
4. Calculate Priority Score

**Calibration challenges:**
- For any Impact = 5: "So if this is wrong, you're saying the entire business fails? Walk me through that."
- For any Uncertainty ≤ 2: "You're saying you have strong evidence. Show me. What data? From whom?"
- For any Uncertainty = 5: Confirm there's truly no evidence

### 3. Build Impact × Uncertainty Matrix

Create visual 2×2 matrix:

```markdown
## Impact × Uncertainty Matrix

|                    | Low Uncertainty (1-2) | Medium (3) | High Uncertainty (4-5) |
|--------------------|----------------------|------------|------------------------|
| **High Impact (4-5)** | Monitor | Test Soon | **LEAP OF FAITH** |
| **Medium (3)** | Accept | Monitor | Test if time permits |
| **Low Impact (1-2)** | Accept | Accept | Ignore |

### Quadrant Placement

**Top-Right: Leap of Faith (High Impact, High Uncertainty)**
- LOF-005 (5×5=25): [statement]
- LOF-012 (5×4=20): [statement]
- ...

**Top-Left: Monitor (High Impact, Low Uncertainty)**
- LOF-003 (4×2=8): [statement]
- ...

**Bottom-Right: Park (Low Impact, High Uncertainty)**
- LOF-018 (2×5=10): [statement]
- ...

**Bottom-Left: Accept (Low Impact, Low Uncertainty)**
- LOF-021 (1×1=1): [statement]
- ...
```

### 4. Identify Top 5-10

Select the highest Priority Score assumptions:

Validation check:
- [ ] Top 5-10 include assumptions from **BOTH** Value and Growth categories
- [ ] At least one assumption makes founder **uncomfortable to read aloud**
- [ ] Clear separation between top tier and rest (if everything clusters at same score, recalibrate)

If all top assumptions are Value or all Growth: "You're only stress-testing [one side]. What are your biggest unknowns about [the other]?"

### 5. Write Leap-of-Faith Statements

For each top assumption, write explicit statement:

> "We are betting that **[specific belief]**
> because **[reason/intuition]**,
> but we have **[level of evidence]**
> and if wrong, **[specific consequence]**."

Example:
> "We are betting that **product managers will pay $49/month for this tool**
> because **they currently spend 3+ hours on manual reporting**,
> but we have **founder intuition only, no pricing conversations**
> and if wrong, **the unit economics don't work at any plausible price point**."

### 6. Peer Review

If co-founder or advisor available: "Review these scores and challenge any you disagree with."

For solo founders: "Role-play a sceptic. Which scores would they challenge?"

Document any adjusted scores with rationale.

### 7. Update Output Document

Update leap-of-faith.md:

```markdown
## Impact × Uncertainty Matrix

[Matrix from Step 3]

## Ranked Assumption List

| Rank | ID | Statement | Impact | Uncertainty | Priority |
|------|-----|-----------|--------|-------------|----------|
| 1 | LOF-005 | We assume... | 5 | 5 | 25 |
| 2 | LOF-012 | We assume... | 5 | 4 | 20 |
| ... | ... | ... | ... | ... | ... |

## Top Leap-of-Faith Assumptions

### 1. [LOF-005] [Short title]
**Statement:** We are betting that **[belief]** because **[reason]**, but we have **[evidence level]** and if wrong, **[consequence]**.

### 2. [LOF-012] [Short title]
**Statement:** ...

[Continue for top 5-10]
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-harvest', 'step-03-classify', 'step-04-prioritize']
```

### 8. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — challenge or refine specific scores
- **[P] Party Mode** — get multi-agent perspectives on prioritization
- **[C] Continue** — proceed to Synthesis & Kill Criteria

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all assumptions are scored
2. Verify top 5-10 include both Value and Growth assumptions
3. Verify Leap-of-Faith Statements written for top assumptions
4. Update frontmatter with `step-04-prioritize` in `stepsCompleted`
5. Load `./step-05-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All assumptions scored, matrix built, top 5-10 identified with explicit statements, at least one uncomfortable assumption

❌ **FAILURE:** Skipping assumptions, accepting all low uncertainty scores without evidence, top list all from one category
