---
name: 'step-04-matrix'
description: 'Plot assumptions on 2x2 matrix and assign actions'
nextStepFile: './step-05-tests.md'
outputFile: '{outputFolder}/assumption-mapping.md'
---

# Step 4: Plot Matrix & Assign Actions

**Progress: Step 4 of 6** — Next: Design Test Cards

---

## STEP GOAL

Place each assumption on the Importance x Uncertainty matrix and assign one of four actions: Test, Accept, Monitor, or Ignore.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Enforce the matrix logic consistently. Challenge borderline assumptions. Push for clear action assignments.

### Step-Specific Rules
- Use score 3 as the dividing line for quadrants
- Borderline assumptions default to the more cautious action
- Kill criteria MUST be in Test or Accept (never Monitor or Ignore)

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/assumption-mapping.md` for scored assumptions
2. Read `{outputFolder}/leap-of-faith.md` for kill criteria reference

---

## MANDATORY SEQUENCE

### 1. Define Quadrant Boundaries

Present the matrix structure:

> "We'll use score 3 as the dividing line. Here's how actions map:
>
> ```
>                    UNCERTAINTY
>              Low (1-2)    High (3-5)
>            ┌────────────┬────────────┐
>     High   │            │            │
>     (3-5)  │   ACCEPT   │    TEST    │
> I          │            │            │
> M          ├────────────┼────────────┤
> P          │            │            │
>     Low    │   IGNORE   │   MONITOR  │
>     (1-2)  │            │            │
>            └────────────┴────────────┘
> ```
>
> - **TEST:** High importance + high uncertainty — must validate
> - **ACCEPT:** High importance + low uncertainty — working assumption
> - **MONITOR:** Low importance + high uncertainty — track passively
> - **IGNORE:** Low importance + low uncertainty — no action needed"

### 2. Place Assumptions

For each assumption, determine quadrant:

```
IF Importance >= 3 AND Uncertainty >= 3 → TEST
IF Importance >= 3 AND Uncertainty <= 2 → ACCEPT
IF Importance <= 2 AND Uncertainty >= 3 → MONITOR
IF Importance <= 2 AND Uncertainty <= 2 → IGNORE
```

**Borderline Handling (score = 3 on one axis):**
> "For borderline assumptions, default to the more cautious action:
> - Borderline between Test and Accept → Test
> - Borderline between Monitor and Ignore → Monitor"

### 3. Rank Test Quadrant

Within the Test quadrant, rank by combined score (Importance + Uncertainty):
> "These are your Test assumptions, ranked by priority (highest combined score = test first):
>
> 1. [AM-XX]: Combined score [N] — [Statement]
> 2. [AM-YY]: Combined score [N] — [Statement]
> 3. ..."

### 4. Kill Criteria Verification

Check all kill criteria assumptions:
- **If any in Monitor or Ignore:** "⚠️ [AM-XX] was a kill criterion but landed in [Monitor/Ignore]. This seems wrong — kill criteria should be Test or Accept. Should we revisit the scoring?"

### 5. Quadrant Distribution Check

Count assumptions per quadrant:

| Quadrant | Count | Percentage | Target Range |
|----------|-------|------------|--------------|
| Test | [N] | [X]% | 20-40% |
| Accept | [N] | [X]% | 20-30% |
| Monitor | [N] | [X]% | 15-25% |
| Ignore | [N] | [X]% | 10-25% |

**Warning triggers:**
- **Test > 50%:** "You have [X]% in Test. That's a lot of unknowns. Consider whether some could be Accept with existing evidence, or whether you need more foundational work before proceeding."
- **Ignore > 40%:** "You have [X]% in Ignore. Are you sure these are truly unimportant and certain?"

### 6. Document Matrix

Update assumption-mapping.md:

```markdown
## Assumption Matrix

### Visual Matrix

```
                   UNCERTAINTY
             Low (1-2)    High (3-5)
           ┌────────────┬────────────┐
    High   │   ACCEPT   │    TEST    │
    (3-5)  │ AM-03      │ AM-01      │
I          │ AM-07      │ AM-02      │
M          │ AM-12      │ AM-05      │
P          ├────────────┼────────────┤
    Low    │   IGNORE   │   MONITOR  │
    (1-2)  │ AM-08      │ AM-04      │
           │ AM-11      │ AM-09      │
           └────────────┴────────────┘
```

### Action Assignment

| ID | Statement | Importance | Uncertainty | Action | Rank (if Test) |
|----|-----------|------------|-------------|--------|----------------|
| AM-01 | ... | 5 | 4 | TEST | 1 |
| AM-02 | ... | 4 | 5 | TEST | 2 |
| AM-03 | ... | 4 | 2 | ACCEPT | - |
| ... | ... | ... | ... | ... | ... |

### Quadrant Summary

| Quadrant | Count | Percentage |
|----------|-------|------------|
| Test | [N] | [X]% |
| Accept | [N] | [X]% |
| Monitor | [N] | [X]% |
| Ignore | [N] | [X]% |
```

### 7. Update Frontmatter

Update stepsCompleted:
```yaml
stepsCompleted: ['step-01-init', 'step-02-collect', 'step-03-rate', 'step-04-matrix']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Design Test Cards
- **[R] Revise** — adjust action assignments

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify every assumption has an action assignment
2. Verify kill criteria are in Test or Accept
3. Verify Test quadrant is ranked
4. Verify `step-04-matrix` is in `stepsCompleted`
5. Load `./step-05-tests.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All assumptions placed, actions assigned, Test quadrant ranked, distribution reviewed

❌ **FAILURE:** Kill criteria in Monitor/Ignore, missing action assignments, unranked Test quadrant
