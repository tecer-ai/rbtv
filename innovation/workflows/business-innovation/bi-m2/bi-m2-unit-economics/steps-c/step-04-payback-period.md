---
name: 'step-04-payback-period'
description: 'Compute LTV:CAC ratio, payback period, and cash implications'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/unit-economics.md'
---

# Step 4: Payback Period

**Progress: Step 4 of 5** — Next: Synthesis

---

## STEP GOAL

Calculate the LTV:CAC ratio and payback period, interpret what they mean for viability and cash flow, and identify fundraising implications.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Evaluate viability on the PESSIMISTIC scenario, not the optimistic one. If the pessimistic ratio is below 1:1, surface this immediately.

### Step-Specific Rules
- MUST calculate ratio for pessimistic AND base scenarios
- MUST also check pessimistic LTV against optimistic CAC (true worst case)
- MUST state fundraising implications explicitly
- MUST interpret payback in context of cash flow

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/unit-economics.md` for LTV and CAC values
2. Review LTV Assumptions Table from Step 3
3. Review CAC Assumptions Table from Step 2

---

## MANDATORY SEQUENCE

### 1. Calculate LTV:CAC Ratios

Using values from Steps 2 and 3:

| Scenario | LTV | CAC | LTV:CAC Ratio |
|----------|-----|-----|---------------|
| Pessimistic | $[X] | $[X] | [X]:1 |
| Base | $[X] | $[X] | [X]:1 |
| Optimistic | $[X] | $[X] | [X]:1 |
| **True Worst Case** | $[Pess LTV] | $[Opt CAC] | [X]:1 |

### 2. Interpret the Ratio

Present interpretation:

| Ratio | Interpretation |
|-------|----------------|
| **< 1:1** | ❌ Losing money on every customer — model is broken |
| **1:1 to 3:1** | ⚠️ Marginal — thin margins for error |
| **3:1 to 5:1** | ✅ Healthy — room to invest in growth |
| **> 5:1** | 🤔 May be under-investing in acquisition |

> "Your base-case ratio is [X]:1. This means [interpretation]."

**If pessimistic ratio < 1:1:**
> "⚠️ **Critical Finding:** Your pessimistic LTV:CAC ratio is below 1:1. This means if your worst-case assumptions prove true, you lose money on every customer.
>
> Before proceeding, identify which variable must improve:
> - Increase price (higher ARPU)?
> - Reduce churn (longer lifetime)?
> - Lower CAC (cheaper acquisition)?
>
> By how much must it improve to reach 3:1?"

**If base ratio < 3:1:**
> "⚠️ Your base-case ratio is below the healthy 3:1 threshold. Which assumption must improve, and by how much?"

### 3. Calculate Payback Period

Apply the formula:
```
Payback (months) = CAC / (Monthly ARPU × Gross Margin %)
```

| Scenario | CAC | Monthly Contribution | Payback |
|----------|-----|----------------------|---------|
| Pessimistic | $[X] | $[X] | [X] months |
| Base | $[X] | $[X] | [X] months |
| Optimistic | $[X] | $[X] | [X] months |

### 4. Interpret Payback Period

Present interpretation:

| Payback | Interpretation |
|---------|----------------|
| **< 12 months** | ✅ Strong — customer pays back quickly |
| **12-18 months** | ⚠️ Acceptable for B2B with annual contracts |
| **> 18 months** | ❌ Dangerous — cash-negative for too long |

> "Your base-case payback is [X] months. This means [interpretation]."

### 5. Calculate Cash Flow Implications

Model the cash dynamics:

> "If you acquire [N] customers per month:
> - Monthly CAC outflow: N × $[CAC] = $[X]
> - Monthly gross margin inflow per customer: $[X]
> - Months until first customer pays back: [X]
> - Cumulative cash needed before break-even: $[X]"

**Cash Gap Analysis:**

| Growth Rate | Monthly Acquisitions | Monthly CAC | Payback Gap | Cumulative Cash Need |
|-------------|---------------------|-------------|-------------|---------------------|
| Conservative | [N] | $[X] | [X] months | $[X] |
| Moderate | [N] | $[X] | [X] months | $[X] |
| Aggressive | [N] | $[X] | [X] months | $[X] |

### 6. State Fundraising Implications

Be explicit:

**If payback < 12 months:**
> "Your unit economics support self-funded growth or modest capital. Each customer pays back within a year."

**If payback 12-18 months:**
> "You need external capital to fund growth. Each customer is cash-negative for [X] months, meaning aggressive growth requires runway."

**If payback > 18 months:**
> "⚠️ **Warning:** Aggressive growth with >18 month payback requires significant external capital. Each customer acquired today won't pay back until [date]. You need $[X] to fund [Y] customers through payback."

### 7. Update Output Document

Update unit-economics.md with:
- LTV:CAC ratio table (all scenarios)
- Ratio interpretation
- Payback period table
- Cash flow implications
- Fundraising statement

Update frontmatter: add `step-04-payback-period` to `stepsCompleted`

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Synthesis (break-even, sensitivity)
- **[R] Refine** — revisit assumptions to improve ratio

ALWAYS halt and wait for user selection.

---

## VALIDATION CHECKLIST

Before proceeding, verify:
- [ ] LTV:CAC ratio calculated for pessimistic AND base scenarios
- [ ] True worst case (pessimistic LTV / optimistic CAC) is stated
- [ ] Payback uses gross-margin-adjusted revenue, not raw ARPU
- [ ] Cash flow implications are explicit (not hand-waved)
- [ ] Fundraising need is stated honestly

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all validation checklist items pass
2. Ensure unit-economics.md is updated with ratio and payback sections
3. Load `./step-05-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Ratio calculated for multiple scenarios, implications stated honestly

❌ **FAILURE:** Only optimistic scenario, ignoring <3:1 ratio, no fundraising statement
