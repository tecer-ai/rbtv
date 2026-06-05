---
name: 'step-02-boundaries'
description: 'Define market boundaries and methodology'
nextStepFile: './step-03-tam.md'
outputFile: '{outputFolder}/tam-sam-som.md'
---

# Step 2: Define Market Boundaries

**Progress: Step 2 of 7** — Next: Calculate TAM

---

## STEP GOAL

Produce a precise market definition brief that fixes the product scope, customer segment, and geographic boundaries, and select concrete top-down and bottom-up methodologies.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for precise definitions. Reject vague segments. The market definition determines everything that follows.

### Step-Specific Rules
- Do NOT calculate TAM/SAM/SOM yet — that's for later steps
- Product category must be one outsiders would recognize
- Identify at least 2 top-down sources and 1 bottom-up approach

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/tam-sam-som.md` for current state
2. Read `{outputFolder}/lean-canvas.md` for Customer Segments, Revenue Streams
3. Read `{outputFolder}/working-backwards.md` for customer definition
4. Read `{outputFolder}/jobs-to-be-done.md` for segment selection

---

## MANDATORY SEQUENCE

### 1. Define Product Scope

> "First, let's be precise about what we're sizing. This must match your Lean Canvas scope.
>
> **What product or product slice does this sizing cover?**
> (One sentence. Do not size a broader market than what your product addresses.)"

Get founder input. Confirm alignment with Lean Canvas.

### 2. Define Customer Segment

> "Who exactly is the target customer? Pull from your Lean Canvas Customer Segments and Working Backwards customer definition:
>
> - **Role:** [Job title or decision-maker type]
> - **Company type/size:** [SMB, mid-market, enterprise, etc.]
> - **Industry vertical:** [Specific industries or 'horizontal']
> - **Geography:** [Countries or regions]
> - **Other qualifiers:** [Digital maturity, tech stack, etc.]"

Get founder input. Ensure precision.

### 3. Define Product Category

> "What category would an outsider (analyst, buyer) recognize?
>
> Examples:
> - 'Project management software for SMBs'
> - 'API-first payment processing for e-commerce'
> - 'Compliance automation for fintech startups'
>
> This is what buyers would search for or analysts would report on. Do NOT invent a new category label."

Get founder input. Challenge if category is too broad or too narrow.

### 4. Identify Top-Down Data Sources

> "For top-down market sizing, we need industry data. Which sources can we use?
>
> **Options:**
> - Analyst reports: Gartner, IDC, Forrester, Statista, Grand View Research
> - Public company filings and investor presentations (competitors or adjacent)
> - Government or trade association data (census, industry registers)
>
> **For each source, note:**
> - Publication date
> - Geographic scope
> - Definition used (may differ from yours)"

Identify at least 2 independent sources. Note limitations.

### 5. Design Bottom-Up Approach

> "For bottom-up market sizing, we count potential customers and multiply by ARPU.
>
> **Define the unit:** Individual users? Companies? Teams? Transactions? Seats?
>
> **Where will you get the count?**
> - LinkedIn data
> - Industry directories
> - Government registries
> - Existing databases
>
> **How will you estimate ARPU?**
> - From Lean Canvas Revenue Streams
> - From competitor pricing
> - From willingness-to-pay research"

Get founder input. Confirm unit definition matches Lean Canvas.

### 6. Document Market Definition Brief

Update tam-sam-som.md:

```markdown
## Market Definition Brief

**Date:** [YYYY-MM-DD]

### Product Scope

[One sentence defining what product/slice this sizing covers]

**In scope:** [What's included]

**Out of scope:** [What's excluded]

### Target Customer Segment

| Attribute | Definition |
|-----------|------------|
| Role | [Job title/decision-maker] |
| Company type/size | [SMB/mid-market/enterprise] |
| Industry vertical | [Specific industries or horizontal] |
| Geography | [Countries/regions] |
| Other qualifiers | [Digital maturity, tech stack, etc.] |

### Product Category

[Category label as outsiders would recognize it]

### Top-Down Data Sources

| Source | Date | Geography | Definition Notes |
|--------|------|-----------|------------------|
| [Source 1] | [Date] | [Scope] | [How definition differs from ours] |
| [Source 2] | [Date] | [Scope] | [How definition differs from ours] |

### Bottom-Up Methodology

**Unit:** [What we're counting]

**Count source:** [Where we'll get the count]

**ARPU estimation:** [How we'll estimate average revenue per unit]

### Known Limitations

- [Limitation 1]
- [Limitation 2]
```

### 7. Validation Check

Confirm with founder:
- "Can you answer in one sentence: 'This market sizing covers **[product category]** for **[segment]** in **[geography]**'?"
- "Is the product category one that industry analysts or buyers would recognize?"
- "Do we have at least two top-down sources and a concrete bottom-up unit?"
- "Does the segment definition match your Lean Canvas?"

### 8. Update Frontmatter

Update stepsCompleted:
```yaml
stepsCompleted: ['step-01-init', 'step-02-boundaries']
```

### 9. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Calculate TAM
- **[R] Revise** — adjust market definition

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify Market Definition Brief is complete
2. Verify at least 2 top-down sources identified
3. Verify bottom-up methodology defined
4. Verify `step-02-boundaries` is in `stepsCompleted`
5. Load `./step-03-tam.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Precise product scope, recognized category, 2+ top-down sources, clear bottom-up methodology

❌ **FAILURE:** Vague segments, invented category, single data source, no bottom-up approach defined
