---
name: 'step-05-som'
description: 'Estimate Serviceable Obtainable Market with Year 1-3 projections'
nextStepFile: './step-06-stress-test.md'
outputFile: '{outputFolder}/tam-sam-som.md'
---

# Step 5: Estimate SOM

**Progress: Step 5 of 7** — Next: Stress Test & Reconciliation

---

## STEP GOAL

Project the realistic revenue you can capture in Years 1-3, built from go-to-market capacity, competitive dynamics, and churn — NOT arbitrary percentages of SAM.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Reject any SOM that's just "5% of SAM." Push for capacity-based calculations. Challenge aggressive growth assumptions.

### Step-Specific Rules
- SOM must be built from go-to-market capacity, not percentages
- Year 1 market share >2% of SAM is aggressive — demand justification
- Growth from Y1 to Y3 must have named mechanisms
- Model churn explicitly — SOM is net revenue, not gross bookings

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/tam-sam-som.md` for Working SAM
2. Read `{outputFolder}/lean-canvas.md` for Channels, Revenue Streams, Cost Structure
3. Read `{outputFolder}/competitive-landscape.md` for competitive context (if exists)
4. Read `{outputFolder}/leap-of-faith.md` for growth hypothesis (if exists)

---

## MANDATORY SEQUENCE

### 1. Year 1 Go-to-Market Capacity

> "Let's build Year 1 SOM from your actual capacity, not a wishful percentage."

**Monthly Lead Generation:**
> "Through your planned channels, how many leads can you generate per month?
>
> - Channel 1: [N] leads/month
> - Channel 2: [N] leads/month
> - Total: [N] leads/month
> - Source: [How you estimated this]"

**Conversion Rate:**
> "What's a realistic conversion rate for your segment and channel type?
>
> - Your estimate: [X]%
> - Industry benchmark: [Y]% (from [source])
> - Working rate: [Z]%"

**Sales Cycle:**
> "What's the average sales cycle (days from first touch to revenue)?
>
> - Your estimate: [N] days
> - Industry benchmark: [N] days (for [segment])
> - Working estimate: [N] days"

**Onboarding Capacity:**
> "How many customers can you onboard and support per month with your current or planned team?
>
> - Current capacity: [N] customers/month
> - Bottleneck: [What limits this]"

**Year 1 Calculation:**
```
Monthly leads: [N]
× Conversion rate: [X]%
× 12 months
= [N] customers Year 1

× ARPU: $[X]
= $[Y] gross revenue Year 1
```

### 2. Year 2 and Year 3 Projections

> "What changes between Year 1 and Year 3?"

**Growth Mechanisms:**
> "What specifically will drive growth from Year 1 to Year 3?
>
> - New channels: [What and when]
> - Capacity increases: [Hiring plans]
> - Organic growth: [Referrals, virality, expansion revenue]
> - Product expansion: [New segments or use cases]"

**Year 2 Projection:**
> "Based on [mechanisms], Year 2 looks like:
>
> - Customer count: [N]
> - Revenue: $[range]
> - Growth rate from Y1: [X]%
> - Justification: [Named mechanism]"

**Year 3 Projection:**
> "Based on [mechanisms], Year 3 looks like:
>
> - Customer count: [N]
> - Revenue: $[range]
> - Growth rate from Y2: [X]%
> - Justification: [Named mechanism]"

### 3. Churn and Expansion

> "Now let's make these projections realistic with churn and expansion."

**Churn Rate:**
> "What's your assumed annual churn rate?
>
> - Your estimate: [X]%
> - Industry benchmark for [segment]: [Y]%
> - Working rate: [Z]%
> - Source: [Benchmark source]"

**Expansion Revenue:**
> "What expansion revenue do you expect per customer?
>
> - Upsells: [X]%/year
> - Seat/usage growth: [X]%/year
> - Net revenue retention: [X]%"

**Net Revenue Calculation:**
> "Adjusting for churn and expansion:
>
> | Year | Gross Revenue | - Churn | + Expansion | Net Revenue |
> |------|---------------|---------|-------------|-------------|
> | Y1 | $[X] | -$[Y] | +$[Z] | $[N] |
> | Y2 | $[X] | -$[Y] | +$[Z] | $[N] |
> | Y3 | $[X] | -$[Y] | +$[Z] | $[N] |"

### 4. Market Share Sanity Check

Calculate implied market share:

| Year | SOM | SAM | Market Share |
|------|-----|-----|--------------|
| Y1 | $[X] | $[SAM] | [X]% |
| Y2 | $[X] | $[SAM] | [X]% |
| Y3 | $[X] | $[SAM] | [X]% |

**Sanity checks:**
- **Y1 > 2%:** "Your Year 1 market share is [X]%. That's aggressive for most startups. What structural advantage justifies this?"
- **Y3 > 10%:** "Your Year 3 market share is [X]%. That requires a strong competitive moat. What's yours?"

### 5. Competitive Context

> "Let's factor in competitive reality:
>
> - How many direct competitors exist? [N]
> - What share do top 2-3 hold? [X]%
> - Are incumbents entrenched or is this a new category?
> - What switching costs exist?
>
> Given this, is your capture rate still achievable?"

### 6. Document SOM

Update tam-sam-som.md:

```markdown
## Serviceable Obtainable Market (SOM)

### Year 1 Capacity Build-Up

**Lead Generation:**
| Channel | Leads/Month | Source |
|---------|-------------|--------|
| [Channel 1] | [N] | [Source] |
| [Channel 2] | [N] | [Source] |
| **Total** | **[N]** | - |

**Conversion Assumptions:**
- Conversion rate: [X]% (benchmark: [Y]% from [source])
- Sales cycle: [N] days
- Onboarding capacity: [N] customers/month

**Year 1 Calculation:**
- ([N] leads × [X]% × 12 months) = [N] customers
- × $[ARPU] = $[X] gross revenue

### Year 2-3 Growth

| Year | Customers | Gross Revenue | Growth Rate | Growth Mechanism |
|------|-----------|---------------|-------------|------------------|
| Y1 | [N] | $[X] | - | Baseline |
| Y2 | [N] | $[X] | [X]% | [Mechanism] |
| Y3 | [N] | $[X] | [X]% | [Mechanism] |

### Churn and Expansion

**Assumptions:**
- Annual churn: [X]% (benchmark: [Y]% from [source])
- Expansion revenue: [X]%/year
- Net revenue retention: [X]%

**Net Revenue:**
| Year | Gross | - Churn | + Expansion | Net |
|------|-------|---------|-------------|-----|
| Y1 | $[X] | $[Y] | $[Z] | $[N] |
| Y2 | $[X] | $[Y] | $[Z] | $[N] |
| Y3 | $[X] | $[Y] | $[Z] | $[N] |

### Market Share Check

| Year | SOM (Net) | SAM | Market Share |
|------|-----------|-----|--------------|
| Y1 | $[X] | $[SAM] | [X]% |
| Y2 | $[X] | $[SAM] | [X]% |
| Y3 | $[X] | $[SAM] | [X]% |

### Competitive Context

- Direct competitors: [N]
- Top 2-3 share: [X]%
- Category maturity: [New/Fragmented/Consolidated]
- Switching costs: [High/Medium/Low]
- Capture rate justification: [Why achievable]
```

### 7. Update Frontmatter

Update stepsCompleted:
```yaml
stepsCompleted: ['step-01-init', 'step-02-boundaries', 'step-03-tam', 'step-04-sam', 'step-05-som']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Stress Test & Reconciliation
- **[R] Revise** — adjust SOM calculations

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify SOM built from capacity, not percentages
2. Verify growth has named mechanisms
3. Verify churn modeled explicitly
4. Verify market share sanity check done
5. Verify `step-05-som` is in `stepsCompleted`
6. Load `./step-06-stress-test.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Capacity-based SOM, named growth mechanisms, churn modeled, market share checked

❌ **FAILURE:** SOM as % of SAM, arbitrary growth multipliers, no churn, unrealistic market share unchallenged
