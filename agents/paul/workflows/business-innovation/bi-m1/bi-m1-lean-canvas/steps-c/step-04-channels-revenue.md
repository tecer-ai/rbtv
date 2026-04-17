---
name: 'step-04-channels-revenue'
description: 'Populate Channels, Revenue Streams, and Cost Structure blocks'
nextStepFile: './step-05-metrics-advantage.md'
outputFile: '{outputFolder}/lean-canvas.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: Channels & Revenue Blocks

**Progress: Step 4 of 6** — Next: Metrics & Advantage Blocks

---

## STEP GOAL

Populate the **Channels**, **Revenue Streams**, and **Cost Structure** blocks with coherent, testable economic hypotheses.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for realistic channel selection. Challenge pricing assumptions. Costs must support unit economics thinking.

### Step-Specific Rules
- Channels must appear in JTBD behaviours (where segment already spends time)
- Revenue model must match segment's buying process
- Cost structure must identify path to positive unit economics
- All economic figures are hypotheses to validate

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/lean-canvas.md` — Segments and Solution from Steps 2-3
2. Read `{outputFolder}/jobs-to-be-done.md` — behaviours and channels
3. Read `{outputFolder}/working-backwards.md` — Internal FAQ (economics thinking)
4. Read `{outputFolder}/problem-solution-fit.md` — constraints
5. Read `./data/lean-canvas-framework.md` — economic block guidance

---

## MANDATORY SEQUENCE

### 1. Identify Channel Candidates

From JTBD and PSF, list where segment already spends time:

> "Let's identify where your Early Adopters already are:
> - What tools do they use daily?
> - What communities or platforms do they visit?
> - How do they typically discover new solutions?
> - How do they evaluate and buy?"

### 2. Draft Channels Block

Ask:
> "Let's map your channels. Distinguish between:
> - **Discovery Channels**: How they first hear about you
> - **Activation Channels**: How they experience value
>
> What 3-5 channels make sense for your segment and stage?"

Consider:
- Content marketing (for developers, technical buyers)
- Outbound sales (for enterprise, high-ACV)
- Product-led virality (for self-serve products)
- Partner integrations (for ecosystem plays)
- Community (for developer tools, open source)

```markdown
## 5. Channels

**Discovery Channels:**
| Channel | Why It Fits | Effort |
|---------|-------------|--------|
| [Channel 1] | [Matches JTBD behaviour] | [Low/Med/High] |
| [Channel 2] | [Matches JTBD behaviour] | [Low/Med/High] |

**Activation Channels:**
| Channel | Purpose | Conversion Point |
|---------|---------|------------------|
| [Channel 1] | [How they experience value] | [Free trial → paid] |
| [Channel 2] | [How they experience value] | [Demo → contract] |

**Go-to-Market Model:**
[Self-serve / Sales-assisted / Hybrid] — because [rationale based on segment]
```

### 3. Revenue Model Selection

Present options suited to digital products:

> "For your segment and solution, which pricing model fits best?
>
> | Model | Best For | Example |
> |-------|----------|---------|
> | Per-seat SaaS | B2B teams | $X/user/month |
> | Usage-based | Variable consumption | $X per API call |
> | Freemium | High-volume, self-serve | Free tier → Pro |
> | Transaction fee | Marketplace/payments | X% per transaction |
> | Flat subscription | Simple B2B | $X/month unlimited |
>
> Consider your segment's budget and buying process."

Ask:
> "Which model makes sense? What price point are you hypothesizing?"

Challenge:
- "How does that price compare to alternatives?"
- "Does your segment have budget authority at that level?"

### 4. Draft Revenue Streams Block

```markdown
## 6. Revenue Streams

**Primary Pricing Model:**
[Model name] — [Price hypothesis]

**Rationale:**
- Matches segment buying process: [how]
- Aligns with value delivered: [how]
- Comparable to: [competitor/alternative pricing]

**Secondary Model (if any):**
[Alternative to test later]

**Key Revenue Assumptions:**
- Willingness to pay: $[X] per [unit]
- Expected conversion rate: [X]%
- Target ACV: $[X]
```

### 5. Map Cost Structure

Ask:
> "Let's identify your cost structure. Separate:
> - **Fixed Costs**: Salaries, core infrastructure, compliance
> - **Variable Costs**: Per-customer costs (hosting, support, API calls)
>
> What are your major costs at early stage?"

### 6. Draft Cost Structure Block

```markdown
## 7. Cost Structure

**Fixed Costs:**
| Cost | Monthly Estimate | Notes |
|------|------------------|-------|
| Founder salaries | $[X] | [Full-time / part-time] |
| Core infrastructure | $[X] | [Essential services] |
| [Other] | $[X] | [Description] |

**Variable Costs (per customer):**
| Cost | Per-Unit Estimate | Driver |
|------|-------------------|--------|
| Hosting/compute | $[X]/customer | [Usage-based] |
| Support load | $[X]/customer | [Ticket volume] |
| [Other] | $[X]/customer | [Driver] |

**Step Functions:**
- [E.g., "Need first CS hire at 20 customers"]
- [E.g., "Infrastructure upgrade at 1000 users"]

**Path to Positive Unit Economics:**
At $[price] with $[variable cost], gross margin is [X]%. Break-even at [N] customers.
```

### 7. Tag Assumptions

Add to Assumptions List:

```markdown
### Channel Assumptions
- **CH1**: [Channel 1] can deliver [N] leads/month at $[X] CAC
- **CH2**: Segment spends time on [platform] — needs validation

### Revenue Assumptions
- **REV1**: Customers will pay $[X] per [unit]
- **REV2**: Conversion rate will be [X]%

### Cost Assumptions
- **COST1**: Variable cost per customer will be $[X]
- **COST2**: Can reach positive unit economics at [N] customers
```

### 8. Unit Economics Sanity Check

Ask:
> "Quick sanity check on unit economics:
> - **LTV hypothesis**: [price × months retained]
> - **CAC hypothesis**: [acquisition cost estimate]
> - **LTV:CAC ratio**: [should be >3 for healthy business]
>
> Does this look plausible? What would break this model?"

### 9. Update Output Document

Update lean-canvas.md with completed Channels, Revenue Streams, and Cost Structure blocks.

### 10. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine economic model or channel strategy
- **[P] Party Mode** — get multi-perspective challenge on business model
- **[C] Continue** — proceed to Metrics & Advantage blocks

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update lean-canvas.md with Channels, Revenue, and Cost sections
2. Update frontmatter: add `step-04-channels-revenue` to `stepsCompleted`
3. Load `./step-05-metrics-advantage.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Channels match JTBD behaviours, revenue model suits segment, cost structure enables unit economics, assumptions tagged

❌ **FAILURE:** Channels not grounded in behaviour data, pricing plucked from air, costs ignored, no path to sustainability
