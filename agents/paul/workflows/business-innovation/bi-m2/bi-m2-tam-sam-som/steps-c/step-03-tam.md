---
name: 'step-03-tam'
description: 'Calculate Total Addressable Market using top-down and bottom-up methods'
nextStepFile: './step-04-sam.md'
outputFile: '{outputFolder}/tam-sam-som.md'
---

# Step 3: Calculate TAM

**Progress: Step 3 of 7** — Next: Define SAM

---

## STEP GOAL

Estimate the entire revenue opportunity for your product category using BOTH top-down and bottom-up methods, then reconcile the results.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for both methods. Reject single-source estimates. Demand ranges not point estimates. Investigate discrepancies.

### Step-Specific Rules
- MUST use both top-down AND bottom-up methods
- Express all figures as ranges, not point estimates
- Every number must have a source and date
- If methods diverge by >2x, investigate why

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/tam-sam-som.md` for Market Definition Brief
2. Read `{outputFolder}/lean-canvas.md` for Revenue Streams (ARPU)
3. Use Data Source Inventory from Step 2

---

## MANDATORY SEQUENCE

### 1. Top-Down Calculation

> "Let's start with top-down. We'll use your identified industry sources and narrow to your product category."

For each source from the Data Source Inventory:

**Source 1: [Name]**
> "What does [Source] say about the total market for [product category]?
>
> - Published figure: $[X]
> - Geography covered: [Scope]
> - Definition used: [Their definition]
> - Adjustment needed: [If their definition is broader/narrower]
> - Adjusted figure: $[Y]"

Repeat for Source 2.

**Top-Down TAM Range:**
> "Based on [N] sources, the top-down TAM range is:
>
> - Low estimate: $[X] (from [source], because [reason])
> - High estimate: $[Y] (from [source], because [reason])
>
> **Top-Down TAM: $[X]–$[Y] per year**"

### 2. Bottom-Up Calculation

> "Now let's build from the ground up. We count potential customers and multiply by ARPU."

**Unit count:**
> "How many [units] exist in your broadest relevant geography?
>
> - Source: [Where you got this count]
> - Count: [N] units
> - Geography: [Scope]"

**ARPU estimation:**
> "What's your average revenue per [unit] per year?
>
> - From Lean Canvas Revenue Streams: $[X]
> - From competitor pricing: $[Y]
> - Working range: $[low]–$[high] per year"

**Bottom-Up TAM:**
> "Bottom-up calculation:
>
> - [N] units × $[ARPU low] = $[X] per year (low)
> - [N] units × $[ARPU high] = $[Y] per year (high)
>
> **Bottom-Up TAM: $[X]–$[Y] per year**"

### 3. Method Comparison

Compare top-down and bottom-up:

| Method | Low | High |
|--------|-----|------|
| Top-Down | $[X] | $[Y] |
| Bottom-Up | $[A] | $[B] |

Calculate ratio of high estimates:
- **If within 2x:** "Good convergence. The methods agree within reasonable bounds."
- **If >2x divergence:** "These diverge significantly. Common reasons:
  - Different product category definitions
  - Stale data in one source
  - Geographic mismatch
  - Incorrect unit count or ARPU
  
  What's the most likely explanation? Which method do you trust more?"

### 4. Working TAM Range

> "Based on both methods, our working TAM range is:
>
> **Working TAM: $[low]–$[high] per year**
>
> - Lower bound driven by: [assumption/source]
> - Upper bound driven by: [assumption/source]
> - Confidence: [High/Medium/Low]"

### 5. Market Assumptions

Identify assumptions embedded in the TAM:
> "These assumptions are built into our TAM:
>
> 1. [Assumption about market size or growth]
> 2. [Assumption about category definition]
> 3. [Assumption about ARPU]
>
> Flag these for Assumption Mapping."

### 6. Document TAM

Update tam-sam-som.md:

```markdown
## Total Addressable Market (TAM)

### Top-Down Calculation

**Source 1: [Name]**
- Published figure: $[X]
- Date: [Date]
- Geography: [Scope]
- Definition: [Their definition]
- Adjustment: [If needed, and why]
- Adjusted figure: $[Y]

**Source 2: [Name]**
- Published figure: $[X]
- Date: [Date]
- Geography: [Scope]
- Definition: [Their definition]
- Adjustment: [If needed, and why]
- Adjusted figure: $[Y]

**Top-Down TAM Range:** $[low]–$[high] per year

### Bottom-Up Calculation

**Unit Count:**
- Unit: [What we're counting]
- Count: [N]
- Source: [Where we got this]
- Geography: [Scope]

**ARPU:**
- Low estimate: $[X] per year (from [source])
- High estimate: $[Y] per year (from [source])

**Calculation:**
- Low: [N] × $[ARPU low] = $[X]
- High: [N] × $[ARPU high] = $[Y]

**Bottom-Up TAM Range:** $[low]–$[high] per year

### Method Comparison

| Method | Low | High |
|--------|-----|------|
| Top-Down | $[X] | $[Y] |
| Bottom-Up | $[A] | $[B] |

**Divergence:** [Within 2x / >2x, with explanation]

### Working TAM

**Working TAM Range:** $[low]–$[high] per year

- Lower bound driver: [Source/assumption]
- Upper bound driver: [Source/assumption]
- Confidence: [High/Medium/Low]

### Embedded Assumptions

1. [Assumption 1]
2. [Assumption 2]
3. [Assumption 3]
```

### 7. Update Frontmatter

Update stepsCompleted:
```yaml
stepsCompleted: ['step-01-init', 'step-02-boundaries', 'step-03-tam']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Define SAM
- **[R] Revise** — adjust TAM calculations

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify both top-down AND bottom-up TAM calculated
2. Verify all figures have sources and dates
3. Verify divergence is documented and explained
4. Verify `step-03-tam` is in `stepsCompleted`
5. Load `./step-04-sam.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Both methods used, ranges provided, sources cited, divergence explained

❌ **FAILURE:** Single method only, point estimates, unsourced figures, unexplained divergence
