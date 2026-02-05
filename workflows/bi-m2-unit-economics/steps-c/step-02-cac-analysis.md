---
name: 'step-02-cac-analysis'
description: 'Define the unit and estimate CAC per channel and blended'
nextStepFile: './step-03-ltv-calculation.md'
outputFile: '{outputFolder}/unit-economics.md'
---

# Step 2: CAC Analysis

**Progress: Step 2 of 5** — Next: LTV Calculation

---

## STEP GOAL

Define what "one unit" means for this business, map the revenue model, and estimate Customer Acquisition Cost (CAC) per channel and blended — with pessimistic/base/optimistic ranges.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for fully-loaded CAC — include people, tools, content, commissions, founder time. Ad spend alone is not CAC.

### Step-Specific Rules
- MUST use ranges (pessimistic/base/optimistic), never point estimates
- MUST tag every number with source (DATA/BENCH/HYPO) and confidence (HIGH/MEDIUM/LOW)
- Do NOT calculate LTV in this step — that's Step 3

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/unit-economics.md` for current progress
2. Review Lean Canvas Revenue Streams and Channels blocks
3. Review TAM/SAM/SOM for segment size and deal size

---

## MANDATORY SEQUENCE

### 1. Define The Unit

Work with user to define what "one unit" means:

> "First, we need to define what 'one unit' means for your business. Options:
> - **Per customer** — B2B SaaS with annual contracts
> - **Per seat/user** — Collaboration tools, per-user pricing
> - **Per transaction** — Marketplaces, per-sale fees
> - **Per usage unit** — API calls, storage, consumption
>
> If you blend models (e.g., base subscription + usage), define the **primary unit** for LTV/CAC."

Ask user: "What is one unit for your business?"

Create **Unit Definition Statement** (2-3 sentences):
> "One unit is [definition]. We charge [price] per [period] under a [model] pricing structure. Expansion revenue comes from [mechanism]."

### 2. Map Revenue Model

From Lean Canvas Revenue Streams, extract:
- Pricing model (subscription, transaction, usage, hybrid)
- Price point or range per unit per period
- Expansion revenue mechanisms (upsell, add-ons, seat expansion)
- Contraction risks (downgrades, seasonal drops)

Create **Revenue Assumptions Table**:

| ID | Assumption | Value/Range | Source | Confidence |
|----|------------|-------------|--------|------------|
| REV-1 | Price per unit per month | $X - $Y | [DATA/BENCH/HYPO] | [H/M/L] |
| REV-2 | Expansion revenue % | X% - Y% | [DATA/BENCH/HYPO] | [H/M/L] |
| ... | ... | ... | ... | ... |

### 3. List Acquisition Channels

From Lean Canvas Channels, list all planned acquisition channels:

| Channel | Type | Stage-Appropriate? |
|---------|------|-------------------|
| [Channel] | Paid/Organic/Outbound/Product-led | Yes/No |

For each channel, classify:
- **Paid:** Ads, sponsorships
- **Organic:** Content, SEO, community
- **Outbound:** Sales, partnerships
- **Product-led:** Virality, referrals

### 4. Estimate CAC Per Channel

For each channel, estimate:
- **Total spend per period:** Include people costs (salaries, commissions), tools, content creation, ad spend
- **New customers acquired per period:** Use conversion funnel logic

**Channel CAC Template:**

| Channel | Monthly Spend | Customers/Month | CAC | Source | Confidence |
|---------|---------------|-----------------|-----|--------|------------|
| [Channel 1] | $[range] | [range] | $[range] | [source] | [H/M/L] |
| [Channel 2] | $[range] | [range] | $[range] | [source] | [H/M/L] |

**If no data, use benchmarks:**
- Paid SaaS SMB: $50-500 CAC
- Paid SaaS Enterprise: $5K-50K CAC
- Content/Inbound: Lower CAC but slower scale
- Outbound B2B: Higher CAC but more predictable

Tag benchmarks as BENCH with LOW confidence.

### 5. Calculate Blended CAC

Sum all channels:
```
Blended CAC = Total Acquisition Spend / Total New Customers
```

Produce three estimates:

| Scenario | Blended CAC | Reasoning |
|----------|-------------|-----------|
| Pessimistic | $[X] | Lower conversion, higher spend |
| Base | $[X] | Current best estimates |
| Optimistic | $[X] | Higher conversion, channel efficiency |

### 6. Create CAC Assumptions Table

Consolidate all CAC assumptions:

| ID | Assumption | Base Value | Pessimistic | Optimistic | Source | Confidence |
|----|------------|------------|-------------|------------|--------|------------|
| CAC-1 | [Description] | $X | $Y | $Z | [source] | [H/M/L] |
| ... | ... | ... | ... | ... | ... | ... |

### 7. Update Output Document

Update unit-economics.md with:
- Unit Definition Statement
- Revenue Assumptions Table
- Channel CAC breakdown
- Blended CAC (three scenarios)
- CAC Assumptions Table

Update frontmatter: add `step-02-cac-analysis` to `stepsCompleted`

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to LTV Calculation
- **[R] Refine** — revisit CAC assumptions

ALWAYS halt and wait for user selection.

---

## VALIDATION CHECKLIST

Before proceeding, verify:
- [ ] Unit definition is unambiguous (one sentence explains what you're charging for)
- [ ] CAC includes ALL acquisition costs (people, tools, spend, founder time)
- [ ] Each channel CAC is calculated independently before blending
- [ ] All numbers have pessimistic/base/optimistic ranges
- [ ] Every number has source and confidence tags

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all validation checklist items pass
2. Ensure unit-economics.md is updated with CAC sections
3. Load `./step-03-ltv-calculation.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Unit defined, CAC estimated with ranges, all numbers tagged

❌ **FAILURE:** Point estimates, ad-spend-only CAC, missing founder time costs
