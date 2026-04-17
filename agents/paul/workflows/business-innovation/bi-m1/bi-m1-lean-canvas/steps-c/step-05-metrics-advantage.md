---
name: 'step-05-metrics-advantage'
description: 'Populate Key Metrics and Unfair Advantage blocks'
nextStepFile: './step-06-synthesis.md'
outputFile: '{outputFolder}/lean-canvas.md'
---

# Step 5: Metrics & Advantage Blocks

**Progress: Step 5 of 6** — Next: Synthesis

---

## STEP GOAL

Populate the **Key Metrics** and **Unfair Advantage** blocks with stage-appropriate metrics and a defensible advantage thesis.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Reject vanity metrics. Push for metrics tied to job and value. Unfair Advantage must be truly hard to copy — reject "great team" and "first mover."

### Step-Specific Rules
- Metrics must be measurable at current stage
- Metrics must connect to job/UVP, not just activity counts
- Unfair Advantage must survive the "well-funded competitor" test
- Competitive Landscape analysis should inform Unfair Advantage

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/lean-canvas.md` — all blocks from Steps 2-4
2. Read `{outputFolder}/working-backwards.md` — Internal FAQ (metrics, strategy)
3. Read `{outputFolder}/competitive-landscape.md` — if exists, for advantage analysis
4. Read `./data/lean-canvas-framework.md` — metrics and advantage guidance

---

## MANDATORY SEQUENCE

### 1. Review Current State

Summarize the canvas so far:
> "Let's review your Lean Canvas before adding the final blocks:
> - **Problem**: [summary of top 3]
> - **Customer Segments**: [primary + early adopters]
> - **UVP**: [one-sentence]
> - **Solution**: [top 3 elements]
> - **Channels/Revenue/Costs**: [quick summary]"

### 2. Define Key Metrics

Present the pirate metrics framework (AARRR):

> "For digital products, metrics often follow this funnel:
>
> | Stage | Question | Example Metric |
> |-------|----------|----------------|
> | Acquisition | How do they find us? | Signups, leads |
> | Activation | Do they experience value? | % completing onboarding |
> | Retention | Do they come back? | Weekly/monthly active |
> | Referral | Do they tell others? | NPS, invite rate |
> | Revenue | Do they pay? | Conversion, MRR |
>
> Which 3-5 metrics matter most for your stage and job?"

Ask:
> "For your Early Adopters and your UVP:
> 1. What's your **North Star metric** — the one number that best captures value delivered?
> 2. What **leading indicators** would predict success?
> 3. What **lagging indicators** confirm success?"

Challenge:
- "That's a vanity metric — what would you actually decide based on it?"
- "How will you measure that at your current stage?"

### 3. Draft Key Metrics Block

```markdown
## 8. Key Metrics

**North Star Metric:**
[Metric name] — measures [what value delivered]

**Leading Indicators (early signals):**
| Metric | Target | Measures |
|--------|--------|----------|
| [Metric 1] | [X%] | [What it predicts] |
| [Metric 2] | [X%] | [What it predicts] |

**Lagging Indicators (outcomes):**
| Metric | Target | Measures |
|--------|--------|----------|
| [Metric 1] | [X%] | [What success looks like] |
| [Metric 2] | [X%] | [What success looks like] |

**Stage Context:**
At [Idea/Pre-product/MVP] stage, we'll focus on [which metrics] before investing in [which others].
```

### 4. Analyze Competitive Position

If Competitive Landscape exists, reference it:
> "Let's look at your Competitive Landscape analysis:
> - What gaps did you identify in competitor offerings?
> - What would prevent a well-funded competitor from copying you?"

If not yet complete:
> "We'll inform Unfair Advantage with general analysis. Consider revisiting after Competitive Landscape framework."

### 5. Define Unfair Advantage

Present valid sources of advantage:

> "Unfair Advantage must be **hard to copy or buy**. Valid sources include:
>
> | Type | Example | Why Hard to Copy |
> |------|---------|------------------|
> | Proprietary data | Training dataset, usage data | Takes time to accumulate |
> | Network effects | Users attract users | Winner-take-most dynamic |
> | Distribution | Integration in popular tool | Requires relationship |
> | Deep expertise | 10+ years domain knowledge | Can't hire overnight |
> | Community | Engaged user base | Built over years |
>
> Invalid: 'Great team', 'First mover', 'Better UX' (all easily copied)"

Ask:
> "What could give you an advantage that survives a well-funded competitor entering?
> - Is it something you have now, or something you're building toward?
> - How long would it take a competitor to replicate?"

Challenge:
- "A competitor with $10M could hire that team — what else?"
- "First mover advantage disappears in months — what's the moat?"

### 6. Draft Unfair Advantage Block

```markdown
## 9. Unfair Advantage

**Primary Advantage:**
[Clear statement of what can't be easily copied]

**Type:**
[Proprietary data / Network effects / Distribution / Expertise / Community]

**Defensibility Thesis:**
- Takes [X months/years] to replicate because [reason]
- Competitor would need [specific requirement] to match
- Advantage compounds over time because [mechanism]

**Honest Assessment:**
- **Current state**: [Do we have it now, or building toward it?]
- **Time to moat**: [How long until this becomes defensible?]
- **Vulnerability**: [What could erode this advantage?]

**Competitive Landscape Connection:**
[How this addresses gaps identified in competitor analysis]
```

### 7. Tag Assumptions

Add to Assumptions List:

```markdown
### Metrics Assumptions
- **MET1**: [North Star metric] accurately measures value delivered
- **MET2**: [Leading indicator] predicts [lagging outcome]
- **MET3**: Can measure [metric] at current stage with [instrumentation]

### Unfair Advantage Assumptions
- **UA1**: [Advantage mechanism] will remain hard to copy for [timeframe]
- **UA2**: [Advantage] creates compounding returns because [reason]
- **UA3**: Competitors lack [specific requirement] to replicate
```

### 8. Update Output Document

Update lean-canvas.md with completed Key Metrics and Unfair Advantage blocks.

### 9. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Synthesis

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update lean-canvas.md with Key Metrics and Unfair Advantage sections
2. Update frontmatter: add `step-05-metrics-advantage` to `stepsCompleted`
3. Load `./step-06-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Metrics tied to job/UVP and measurable at stage, Unfair Advantage passes "well-funded competitor" test, assumptions tagged

❌ **FAILURE:** Vanity metrics only, "great team" as advantage, no competitive landscape consideration, unmeasurable metrics
