---
name: 'step-04-sam'
description: 'Define Serviceable Addressable Market with narrowing waterfall'
nextStepFile: './step-05-som.md'
outputFile: '{outputFolder}/tam-sam-som.md'
---

# Step 4: Define SAM

**Progress: Step 4 of 7** — Next: Estimate SOM

---

## STEP GOAL

Narrow TAM to the portion of the market you could realistically serve given your geographic reach, customer segment focus, channel capabilities, and product constraints.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for honest narrowing. Reject hand-waving like "about half." Every filter must be named, quantified, and justified.

### Step-Specific Rules
- Apply filters sequentially from TAM
- Every filter must have a percentage/absolute reduction with rationale
- SAM must be meaningfully smaller than TAM
- Distinguish hard constraints from soft constraints

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/tam-sam-som.md` for Working TAM
2. Read `{outputFolder}/lean-canvas.md` for Customer Segments, Channels
3. Read `{outputFolder}/working-backwards.md` for customer definition
4. Read `{outputFolder}/jobs-to-be-done.md` for segment selection

---

## MANDATORY SEQUENCE

### 1. Start from Working TAM

> "Starting from your Working TAM of $[low]–$[high], let's apply narrowing filters one by one."

### 2. Apply Narrowing Filters

**Filter 1: Geography**

> "Which countries or regions will you serve in the medium term (3-5 years)?
>
> - Serving: [Countries/regions]
> - Excluding: [Rest of world]
> - Reduction: [X]% of TAM is in target geographies
> - Evidence: [Source for geographic breakdown]
>
> **After geography:** $[range]"

**Filter 2: Customer Segment**

> "Which company sizes, industries, or roles does your product serve?
>
> - Serving: [Segment definition from Lean Canvas]
> - Excluding: [Segments outside your focus]
> - Reduction: [X]% of remaining market fits your segment
> - Evidence: [Source for segment breakdown]
>
> **After segment:** $[range]"

**Filter 3: Product Fit**

> "Does your product only serve a sub-use-case within the broader category?
>
> - Your product addresses: [Specific use case]
> - Broader category includes: [Other use cases you don't serve]
> - Reduction: [X]% of segment has this specific use case
> - Evidence: [Source or reasoning]
>
> **After product fit:** $[range]"

**Filter 4: Channel Constraints**

> "Which distribution channels can you realistically operate?
>
> - Your channels: [From Lean Canvas]
> - Excluded segments: [e.g., enterprise requiring field sales you can't build]
> - Reduction: [X]% reachable through your channels
> - Evidence: [Source or reasoning]
>
> **After channel:** $[range]"

**Filter 5: Technical/Regulatory Constraints**

> "Does your product require specific infrastructure, integrations, or regulatory clearance?
>
> - Requirements: [Technical or regulatory prerequisites]
> - Excluded market: [Who doesn't meet requirements]
> - Reduction: [X]% meets technical/regulatory requirements
> - Evidence: [Source or reasoning]
>
> **After technical/regulatory:** $[range]"

### 3. Narrowing Waterfall Summary

Build the waterfall:

```
TAM: $[X]–$[Y]
  ↓ Geography (-[X]%): $[range]
  ↓ Segment (-[X]%): $[range]
  ↓ Product fit (-[X]%): $[range]
  ↓ Channel (-[X]%): $[range]
  ↓ Technical/Regulatory (-[X]%): $[range]
SAM: $[low]–$[high]
```

### 4. Bottom-Up Cross-Check

> "Let's verify with a bottom-up count:
>
> How many [units] actually pass ALL your filters?
> - Count: [N] units
> - Source: [How you got this count]
> - × ARPU: $[range]
> - **Bottom-up SAM:** $[range]
>
> Does this match the waterfall SAM?"

If significant discrepancy, investigate.

### 5. Constraint Classification

Classify each filter as hard or soft:

| Filter | Type | Rationale |
|--------|------|-----------|
| Geography | [Hard/Soft] | [Could expand with investment?] |
| Segment | [Hard/Soft] | [Product changes needed?] |
| Product fit | [Hard/Soft] | [Roadmap expansion?] |
| Channel | [Hard/Soft] | [Investment required?] |
| Technical/Regulatory | [Hard/Soft] | [Timeline to clear?] |

### 6. Document SAM

Update tam-sam-som.md:

```markdown
## Serviceable Addressable Market (SAM)

### Narrowing Waterfall

| Stage | Reduction | Remaining Market | Rationale |
|-------|-----------|------------------|-----------|
| TAM | - | $[X]–$[Y] | Starting point |
| After Geography | -[X]% | $[range] | Serving [regions], [source] |
| After Segment | -[X]% | $[range] | [Segment def], [source] |
| After Product Fit | -[X]% | $[range] | [Use case], [source] |
| After Channel | -[X]% | $[range] | [Channels], [source] |
| After Technical/Regulatory | -[X]% | $[range] | [Requirements], [source] |
| **SAM** | - | **$[low]–$[high]** | - |

### Bottom-Up Cross-Check

- Units passing all filters: [N]
- ARPU range: $[low]–$[high]
- Bottom-up SAM: $[range]
- Waterfall SAM: $[range]
- Match: [Yes / No, with explanation]

### Constraint Classification

| Constraint | Type | Expansion Notes |
|------------|------|-----------------|
| Geography | [Hard/Soft] | [Notes] |
| Segment | [Hard/Soft] | [Notes] |
| Product Fit | [Hard/Soft] | [Notes] |
| Channel | [Hard/Soft] | [Notes] |
| Technical/Regulatory | [Hard/Soft] | [Notes] |

### Working SAM

**Working SAM Range:** $[low]–$[high] per year

- Confidence: [High/Medium/Low]
- Key uncertainty: [What could change this most]
```

### 7. Update Frontmatter

Update stepsCompleted:
```yaml
stepsCompleted: ['step-01-init', 'step-02-boundaries', 'step-03-tam', 'step-04-sam']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Estimate SOM
- **[R] Revise** — adjust SAM filters

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all filters are named, quantified, and justified
2. Verify SAM is meaningfully smaller than TAM
3. Verify bottom-up cross-check performed
4. Verify constraints classified as hard/soft
5. Verify `step-04-sam` is in `stepsCompleted`
6. Load `./step-05-som.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All filters quantified with rationale, bottom-up cross-check done, constraints classified

❌ **FAILURE:** Hand-waving reductions, SAM equals TAM, no cross-check, constraints not classified
