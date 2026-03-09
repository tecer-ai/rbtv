---
name: 'step-06-stress-test'
description: 'Cross-reference methods, identify fragile assumptions, assign confidence'
nextStepFile: './step-07-synthesis.md'
outputFile: '{outputFolder}/tam-sam-som.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 6: Stress Test & Reconciliation

**Progress: Step 6 of 7** — Next: Synthesis

---

## STEP GOAL

Compare top-down and bottom-up results across all layers, check internal consistency with Lean Canvas, identify fragile assumptions, and assign honest confidence ratings.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for honesty. "High confidence" on pre-revenue SOM is a red flag. Celebrate identifying fragile assumptions — that's the value.

### Step-Specific Rules
- Compare top-down and bottom-up at EVERY layer
- Gaps >2x are critical discrepancies requiring explanation
- Identify top 3-5 fragile assumptions with validation methods
- SOM confidence is almost always Low at pre-revenue stage

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/tam-sam-som.md` for all estimates
2. Read `{outputFolder}/lean-canvas.md` for Revenue Streams, Cost Structure
3. Read `{outputFolder}/leap-of-faith.md` for market-related assumptions (if exists)
4. Read `{outputFolder}/assumption-mapping.md` for flagged assumptions (if exists)

---

## MANDATORY SEQUENCE

### 1. Top-Down vs Bottom-Up Reconciliation

For each layer (TAM, SAM, SOM):

**TAM Reconciliation:**
| Method | Low | High |
|--------|-----|------|
| Top-Down | $[X] | $[Y] |
| Bottom-Up | $[A] | $[B] |

> "Gap ratio: [X]
>
> [If within 2x]: Good convergence.
> [If >2x]: Critical discrepancy. Most likely cause: [explanation]"

**SAM Reconciliation:**
| Method | Low | High |
|--------|-----|------|
| Waterfall (from TAM) | $[X] | $[Y] |
| Bottom-Up (unit count) | $[A] | $[B] |

> "Gap ratio: [X]
>
> [If within 2x]: Good convergence.
> [If >2x]: Critical discrepancy. Most likely cause: [explanation]"

**SOM Reconciliation:**
> "SOM is capacity-based, so there's no top-down equivalent. But let's check:
>
> - Does SOM Year 1 pass the 2% market share threshold?
> - Does the implied customer count match your capacity analysis?"

### 2. Internal Consistency with Lean Canvas

**Revenue Check:**
> "Does SOM Year 1 revenue align with what Lean Canvas Cost Structure needs?
>
> - SOM Year 1: $[X]
> - Lean Canvas costs (estimated): $[Y]
> - Gap: [Surplus/Deficit of $Z]
> - Runway implication: [How long before costs are covered?]"

**ARPU Check:**
> "Does the ARPU in your bottom-up match Lean Canvas Revenue Streams?
>
> - Market sizing ARPU: $[X]
> - Lean Canvas pricing: $[Y]
> - Match: [Yes/No, with notes]"

**Capacity Check:**
> "Does the customer count in SOM match Lean Canvas Channels capacity?
>
> - SOM Year 1 customers: [N]
> - Lean Canvas channel capacity: [M]
> - Match: [Yes/No, with notes]"

### 3. Identify Fragile Assumptions

> "Which assumptions, if wrong by 2x in either direction, would change SOM by more than 50%?"

For each fragile assumption:
- **Assumption:** [Statement]
- **Impact if 2x wrong:** [How SOM changes]
- **Current confidence:** [High/Medium/Low]
- **Validation method:** [How to test this]

Rank by impact:
1. [Most impactful assumption]
2. [Second most impactful]
3. [Third most impactful]
4. [Fourth most impactful]
5. [Fifth most impactful]

### 4. Leap of Faith Cross-Reference

If Leap of Faith exists:
> "Checking Leap of Faith market assumptions:
>
> - [LoF assumption 1]: Used in TAM/SAM/SOM as [how]. Consistent? [Yes/No]
> - [LoF assumption 2]: Used in TAM/SAM/SOM as [how]. Consistent? [Yes/No]
>
> Flag any inconsistencies for resolution."

### 5. Confidence Ratings

Assign confidence to each layer:

**TAM Confidence:**
> "[High/Medium/Low]
>
> Justification: [One sentence — e.g., 'Two independent sources agree within 20%' or 'Single source with broad category definition']"

**SAM Confidence:**
> "[High/Medium/Low]
>
> Justification: [One sentence — e.g., 'Narrowing filters are well-sourced' or 'Segment breakdown estimated, not validated']"

**SOM Confidence:**
> "[High/Medium/Low — almost always Low at pre-revenue]
>
> Justification: [One sentence — e.g., 'Pre-revenue, capacity assumptions untested' or 'Based on adjacent market experience']"

### 6. Document Stress Test

Update tam-sam-som.md:

```markdown
## Stress Test & Reconciliation

### Method Comparison

**TAM:**
| Method | Low | High | Gap |
|--------|-----|------|-----|
| Top-Down | $[X] | $[Y] | - |
| Bottom-Up | $[A] | $[B] | [ratio] |

**Discrepancy Analysis:** [Explanation if >2x]

**SAM:**
| Method | Low | High | Gap |
|--------|-----|------|-----|
| Waterfall | $[X] | $[Y] | - |
| Bottom-Up | $[A] | $[B] | [ratio] |

**Discrepancy Analysis:** [Explanation if >2x]

### Lean Canvas Consistency

| Check | Market Sizing | Lean Canvas | Match |
|-------|---------------|-------------|-------|
| Year 1 Revenue | $[X] | Costs: $[Y] | [Yes/Deficit] |
| ARPU | $[X] | $[Y] | [Yes/No] |
| Customer Count | [N] | Capacity: [M] | [Yes/No] |

### Fragile Assumptions

| Rank | Assumption | Impact if 2x Wrong | Confidence | Validation Method |
|------|------------|-------------------|------------|-------------------|
| 1 | [Statement] | [Impact] | [H/M/L] | [Method] |
| 2 | [Statement] | [Impact] | [H/M/L] | [Method] |
| 3 | [Statement] | [Impact] | [H/M/L] | [Method] |
| 4 | [Statement] | [Impact] | [H/M/L] | [Method] |
| 5 | [Statement] | [Impact] | [H/M/L] | [Method] |

### Leap of Faith Cross-Reference

| LoF Assumption | Used In | Consistent |
|----------------|---------|------------|
| [Assumption 1] | [Where] | [Yes/No] |
| [Assumption 2] | [Where] | [Yes/No] |

### Confidence Ratings

| Layer | Confidence | Justification |
|-------|------------|---------------|
| TAM | [H/M/L] | [One sentence] |
| SAM | [H/M/L] | [One sentence] |
| SOM | [H/M/L] | [One sentence] |
```

### 7. Update Frontmatter

Update stepsCompleted:
```yaml
stepsCompleted: ['step-01-init', 'step-02-boundaries', 'step-03-tam', 'step-04-sam', 'step-05-som', 'step-06-stress-test']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Synthesis
- **[R] Revise** — revisit earlier steps to address discrepancies

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify top-down/bottom-up compared at all layers
2. Verify Lean Canvas consistency checked
3. Verify 3-5 fragile assumptions identified with validation methods
4. Verify honest confidence ratings assigned
5. Verify `step-06-stress-test` is in `stepsCompleted`
6. Load `./step-07-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All layers compared, discrepancies explained, fragile assumptions identified, honest confidence ratings

❌ **FAILURE:** Skipping layer comparisons, ignoring discrepancies, no fragile assumptions, "high confidence" on pre-revenue SOM
