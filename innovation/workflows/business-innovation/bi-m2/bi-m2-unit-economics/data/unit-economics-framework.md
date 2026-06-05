---
name: 'unit-economics-framework'
description: 'Reference methodology for Unit Economics framework'
---

# Unit Economics Framework Reference

## Overview

Unit economics reduces your entire business model to the economics of one customer (or one transaction, or one seat). If you cannot make money on one unit, you cannot make money on a million.

This framework produces six outputs:
1. **Unit Definition** — What "one unit" means and how revenue is generated
2. **LTV Estimate** — Customer lifetime value with ranges
3. **CAC Estimate** — Customer acquisition cost per channel and blended
4. **LTV:CAC Ratio** — Viability indicator with payback period
5. **Break-Even Analysis** — Customer count and timeline to sustainability
6. **Sensitivity Analysis** — Which assumptions matter most

---

## Core Formulas

### Customer Lifetime Value (LTV)

```
LTV = ARPU × Gross Margin × Average Customer Lifetime
```

Where:
- **ARPU** = Average Revenue Per User (monthly or annual)
- **Gross Margin** = (Revenue - COGS) / Revenue
- **Average Customer Lifetime** = 1 / Churn Rate

### Customer Acquisition Cost (CAC)

```
CAC = Total Acquisition Spend / New Customers Acquired
```

Include ALL costs: people, ads, tools, content, commissions, founder time.

### LTV:CAC Ratio Interpretation

| Ratio | Interpretation |
|-------|----------------|
| < 1:1 | Losing money on every customer — model is broken |
| 1:1 to 3:1 | Marginal — thin margins for error |
| 3:1 to 5:1 | Healthy — room to invest in growth |
| > 5:1 | May be under-investing in acquisition |

### Payback Period

```
Payback (months) = CAC / (Monthly ARPU × Gross Margin)
```

| Payback | Interpretation |
|---------|----------------|
| < 12 months | Strong — customer pays back quickly |
| 12-18 months | Acceptable for B2B with annual contracts |
| > 18 months | Dangerous — cash-negative for too long |

---

## Churn Benchmarks

Use these when you lack data (always tag as "benchmark"):

| Segment | Monthly Churn | Implied Lifetime |
|---------|---------------|------------------|
| SMB B2B SaaS | 3-7% | 14-33 months |
| Mid-market B2B SaaS | 0.8-1.2% | 7-10 years |
| Enterprise B2B SaaS | 0.4-0.8% | 10-20 years |
| Consumer subscription | 5-10% | 10-20 months |

Cap lifetime at 5 years for early-stage to avoid fantasy numbers.

---

## Scenario Modeling

Always produce three scenarios:

| Scenario | Description |
|----------|-------------|
| **Pessimistic** | Higher churn, lower ARPU, higher CAC, no expansion |
| **Base** | Best current assumptions with realistic ranges |
| **Optimistic** | Lower churn, higher ARPU, expansion included |

**Critical:** Evaluate viability on the pessimistic scenario, not the optimistic one.

---

## Assumption Tagging Convention

Tag every number with source and confidence:

| Tag | Source |
|-----|--------|
| DATA | Real data from your business or validated research |
| BENCH | Industry benchmark from credible source |
| HYPO | Pure hypothesis — no evidence yet |

| Confidence | Meaning |
|------------|---------|
| HIGH | Multiple data points support |
| MEDIUM | Some evidence, gaps remain |
| LOW | Single data point or pure guess |

---

## Break-Even Calculation

```
Break-Even Customers = Monthly Fixed Costs / Monthly Contribution Margin Per Customer
```

Where:
- **Monthly Fixed Costs** = Salaries + Office + Tools + Infrastructure (not per-customer)
- **Contribution Margin** = Monthly ARPU × Gross Margin

Include founder salaries at reasonable imputed rate — not zero.

---

## Integration Points

### Builds On

| Framework | What It Provides |
|-----------|------------------|
| TAM/SAM/SOM (M2) | Market size, segment count, average deal size |
| Lean Canvas (M1) | Revenue Streams, Cost Structure, Channels, Key Metrics |
| Working Backwards (M1) | Internal FAQ economics section, pricing constraints |

### Feeds Into

| Framework | What It Receives |
|-----------|------------------|
| Assumption Mapping (M2) | Critical economic assumptions for Test quadrant |
| Pre-mortem (M2) | Financial failure modes, break-even risks |
| M5 Market Validation | Pricing hypotheses, CAC benchmarks to validate |

---

## Common Pitfalls

1. **Point Estimates** — Never single numbers; always pessimistic/base/optimistic ranges
2. **Underloaded CAC** — Include ALL acquisition costs, not just ad spend
3. **Fantasy Churn** — Don't assume better than industry best without evidence
4. **Confusing Revenue/Cash** — CAC is immediate; revenue collection is delayed
5. **Skipping Break-Even** — "We'll raise more" is not a substitute for understanding capital needs
