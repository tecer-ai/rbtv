---
name: 'step-03-rate'
description: 'Rate each assumption on Importance and Uncertainty'
nextStepFile: './step-04-matrix.md'
outputFile: '{outputFolder}/assumption-mapping.md'
---

# Step 3: Rate Importance & Uncertainty

**Progress: Step 3 of 6** — Next: Plot Matrix & Assign Actions

---

## STEP GOAL

Score each assumption on Importance (1-5) and Uncertainty (1-5) using explicit, repeatable criteria.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for differentiation. Challenge if more than 30% are scored Importance 5. Demand justification for every score.

### Step-Specific Rules
- Use the defined anchors, not gut feel
- Leap of Faith kill criteria MUST be Importance 4-5
- Score each assumption independently — don't anchor on previous scores

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/assumption-mapping.md` for normalized inventory
2. Read `{outputFolder}/leap-of-faith.md` for kill criteria reference
3. Read `./data/assumption-mapping-framework.md` for scoring scales

---

## MANDATORY SEQUENCE

### 1. Present Scoring Scales

**Importance Scale (Y-axis):**

| Score | Label | Description |
|-------|-------|-------------|
| 5 | Fatal if wrong | Business model collapses. Matches Leap of Faith kill criteria. |
| 4 | Severe | Major pivot required. Revenue model or core value proposition breaks. |
| 3 | Significant | Important feature/channel/cost fails. Workaround possible but painful. |
| 2 | Moderate | Secondary assumption. Affects efficiency or timeline, not viability. |
| 1 | Minor | Nice-to-know. No material impact on go/no-go decision. |

**Uncertainty Scale (X-axis):**

| Score | Label | Description |
|-------|-------|-------------|
| 5 | No evidence | Pure guess. No data, no interviews, no analogies. |
| 4 | Weak signal | One anecdote, one data point, or founder intuition only. |
| 3 | Mixed signals | Some evidence supports, some contradicts. Or indirect evidence. |
| 2 | Moderate evidence | Multiple data points or interviews support. Minor gaps remain. |
| 1 | Strong evidence | Robust data, validated in adjacent markets, or already tested. |

### 2. Identify Kill Criteria

From Leap of Faith, identify assumptions marked as kill criteria:
> "These assumptions were flagged as kill criteria in Leap of Faith — if wrong, they kill the business. They MUST be scored Importance 4-5:
> - [Kill criterion 1]
> - [Kill criterion 2]
> - ..."

### 3. Score Each Assumption

For each assumption in the inventory, ask:

**Importance:**
> "For [AM-XX]: [Statement]
>
> If this assumption is wrong, what happens to the business?
> - Fatal (5): Business collapses
> - Severe (4): Major pivot required
> - Significant (3): Painful workaround needed
> - Moderate (2): Affects efficiency, not viability
> - Minor (1): No material impact
>
> What's your score and why?"

**Uncertainty:**
> "What evidence do we have for this assumption?
> - None (5): Pure guess
> - Weak (4): One data point or intuition
> - Mixed (3): Conflicting or indirect evidence
> - Moderate (2): Multiple supporting data points
> - Strong (1): Robust, validated data
>
> What's your score and why?"

Record both scores with one-sentence justifications.

### 4. Distribution Check

After scoring all assumptions:

Count Importance 5 scores:
- **If > 30%:** "You've rated [N]% as Importance 5. That's high — not everything can be fatal. Let's review which ones could really be 4 (severe but not fatal)."

Check kill criteria:
- **If any < 4:** "This was marked as a kill criterion in Leap of Faith but you scored it [X]. Can you explain why it's not at least Importance 4?"

Count high-risk (Importance 4+ AND Uncertainty 4+):
- **If < 2:** "You have fewer than 2 high-risk assumptions. Are you sure you're not being overconfident about your evidence?"

### 5. Document Scores

Update assumption-mapping.md Scored Assumptions section:

```markdown
## Scored Assumptions

| ID | Statement | Importance | Uncertainty | I Justification | U Justification |
|----|-----------|------------|-------------|-----------------|-----------------|
| AM-01 | We assume that... | 5 | 4 | [one sentence] | [one sentence] |
| AM-02 | We assume that... | 3 | 5 | [one sentence] | [one sentence] |
| ... | ... | ... | ... | ... | ... |

### Score Distribution

| Score | Importance Count | Uncertainty Count |
|-------|-----------------|-------------------|
| 5 | [N] | [N] |
| 4 | [N] | [N] |
| 3 | [N] | [N] |
| 2 | [N] | [N] |
| 1 | [N] | [N] |

**High-Risk (I ≥ 4 AND U ≥ 4):** [N] assumptions
```

### 6. Update Frontmatter

Update stepsCompleted:
```yaml
stepsCompleted: ['step-01-init', 'step-02-collect', 'step-03-rate']
```

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Plot Matrix & Assign Actions
- **[R] Revise** — adjust scores

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify every assumption has both scores with justifications
2. Verify kill criteria are scored Importance 4-5
3. Verify `step-03-rate` is in `stepsCompleted`
4. Load `./step-04-matrix.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All assumptions scored with justifications, kill criteria at 4-5, distribution reviewed

❌ **FAILURE:** Scores without justification, accepting gut feel, skipping distribution check, kill criteria under-scored
