---
name: 'step-03-ltv-calculation'
description: 'Calculate ARPU, gross margin, churn, and LTV with ranges'
nextStepFile: './step-04-payback-period.md'
outputFile: '{outputFolder}/unit-economics.md'
---

# Step 3: LTV Calculation

**Progress: Step 3 of 5** — Next: Payback Period

---

## STEP GOAL

Calculate Customer Lifetime Value (LTV) using ARPU, gross margin, and churn/retention assumptions — with pessimistic/base/optimistic ranges for each component.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for realistic churn assumptions — SMB SaaS typically sees 3-7% monthly churn. Assuming 1% without data is dishonest modeling.

### Step-Specific Rules
- MUST produce three LTV estimates (pessimistic/base/optimistic)
- MUST cap customer lifetime at reasonable maximum (5 years for early-stage)
- MUST include all COGS in gross margin (hosting, APIs, support, payments)
- MUST tag every assumption with source and confidence

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/unit-economics.md` for Unit Definition and Revenue Assumptions
2. Review Lean Canvas Key Metrics for retention/churn
3. Review industry benchmarks from framework knowledge

---

## MANDATORY SEQUENCE

### 1. Calculate ARPU

From Step 2's Revenue Assumptions, calculate Average Revenue Per User:

> "Let's calculate your ARPU (Average Revenue Per User) per month."

| Component | Value | Source | Confidence |
|-----------|-------|--------|------------|
| Base price per unit/month | $[X] | [source] | [H/M/L] |
| Expansion revenue % | [X]% | [source] | [H/M/L] |
| Net Revenue Retention | [X]% | [source] | [H/M/L] |

**ARPU Calculation:**
- If NRR > 100%: Monthly ARPU = Base Price × (NRR / 100)
- If NRR ≤ 100%: Monthly ARPU = Base Price

| Scenario | Monthly ARPU |
|----------|--------------|
| Pessimistic | $[X] (lower price, no expansion) |
| Base | $[X] (current pricing, modest expansion) |
| Optimistic | $[X] (higher price, expansion included) |

### 2. Calculate Gross Margin

Identify all COGS (Cost of Goods Sold):

| COGS Item | Monthly Cost Per Customer | Notes |
|-----------|---------------------------|-------|
| Hosting/Infrastructure | $[X] | |
| Third-party APIs | $[X] | |
| Customer support | $[X] | |
| Payment processing | $[X] | |
| [Other] | $[X] | |
| **Total COGS** | $[X] | |

**Gross Margin Calculation:**
```
Gross Margin % = (ARPU - COGS per customer) / ARPU × 100
```

| Scenario | Gross Margin % | Reasoning |
|----------|----------------|-----------|
| Pessimistic | [X]% | Higher COGS, lower ARPU |
| Base | [X]% | Current estimates |
| Optimistic | [X]% | Lower COGS, higher ARPU |

### 3. Estimate Churn and Lifetime

Determine monthly churn rate:

**If you have data:** Use actual monthly churn
**If no data, use benchmarks:**

| Segment | Monthly Churn | Annual Churn | Implied Lifetime |
|---------|---------------|--------------|------------------|
| SMB B2B SaaS | 3-7% | 31-58% | 14-33 months |
| Mid-market SaaS | 0.8-1.2% | 9-14% | 7-10 years |
| Enterprise SaaS | 0.4-0.8% | 5-9% | 10-20 years |
| Consumer | 5-10% | 46-72% | 10-20 months |

> "Which segment matches your business? What's your source for churn?"

**Average Customer Lifetime:**
```
Lifetime (months) = 1 / Monthly Churn Rate
```

Cap at 60 months (5 years) for early-stage to prevent fantasy numbers.

| Scenario | Monthly Churn | Lifetime (months) | Source | Confidence |
|----------|---------------|-------------------|--------|------------|
| Pessimistic | [X]% | [Y] months | [source] | [H/M/L] |
| Base | [X]% | [Y] months | [source] | [H/M/L] |
| Optimistic | [X]% | [Y] months (capped at 60) | [source] | [H/M/L] |

### 4. Calculate LTV

Apply the LTV formula:
```
LTV = Monthly ARPU × Gross Margin % × Lifetime (months)
```

| Scenario | ARPU | Margin | Lifetime | LTV |
|----------|------|--------|----------|-----|
| Pessimistic | $[X] | [X]% | [X] mo | **$[X]** |
| Base | $[X] | [X]% | [X] mo | **$[X]** |
| Optimistic | $[X] | [X]% | [X] mo | **$[X]** |

### 5. Create LTV Assumptions Table

Consolidate all LTV assumptions:

| ID | Assumption | Base | Pessimistic | Optimistic | Source | Confidence |
|----|------------|------|-------------|------------|--------|------------|
| LTV-1 | Monthly ARPU | $X | $Y | $Z | [source] | [H/M/L] |
| LTV-2 | Gross Margin | X% | Y% | Z% | [source] | [H/M/L] |
| LTV-3 | Monthly Churn | X% | Y% | Z% | [source] | [H/M/L] |
| LTV-4 | Customer Lifetime | X mo | Y mo | Z mo | [source] | [H/M/L] |

### 6. Update Output Document

Update unit-economics.md with:
- ARPU calculation
- Gross Margin breakdown
- Churn and Lifetime estimates
- LTV calculation (three scenarios)
- LTV Assumptions Table

Update frontmatter: add `step-03-ltv-calculation` to `stepsCompleted`

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Payback Period
- **[R] Refine** — revisit LTV assumptions

ALWAYS halt and wait for user selection.

---

## VALIDATION CHECKLIST

Before proceeding, verify:
- [ ] LTV is expressed as a range (pessimistic/base/optimistic)
- [ ] Churn assumption is sourced (data, benchmark, or tagged as hypothesis)
- [ ] Gross margin includes all material COGS items
- [ ] Customer lifetime is capped at reasonable maximum
- [ ] Each LTV component has source and confidence tags

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all validation checklist items pass
2. Ensure unit-economics.md is updated with LTV sections
3. Load `./step-04-payback-period.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** LTV calculated with ranges, churn justified, margin includes all COGS

❌ **FAILURE:** Single LTV number, fantasy churn rates, hidden COGS
