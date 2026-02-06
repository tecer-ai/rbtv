---
name: 'step-03-value-solution'
description: 'Populate Unique Value Proposition and Solution blocks'
nextStepFile: './step-04-channels-revenue.md'
outputFile: '{outputFolder}/lean-canvas.md'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Step 3: Value & Solution Blocks

**Progress: Step 3 of 6** — Next: Channels & Revenue Blocks

---

## STEP GOAL

Populate the **Unique Value Proposition (UVP)** and **Solution** blocks as sharp, testable hypotheses derived from prior work.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Reject vague slogans. Push for specificity. The UVP must differentiate from named alternatives. Each solution element must trace to a problem.

### Step-Specific Rules
- UVP describes **change in customer's world**, not product features
- Every Solution element maps to a Problem from Step 2
- Must name at least 2 alternatives for differentiation
- Generic promises like "save time" are insufficient

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/lean-canvas.md` — Problem and Customer Segments from Step 2
2. Read `{outputFolder}/working-backwards.md` — PR headline, subheading, solution paragraph
3. Read `{outputFolder}/problem-solution-fit.md` — Our Solution block
4. Read `./data/lean-canvas-framework.md` — UVP and Solution guidance

---

## MANDATORY SEQUENCE

### 1. Extract UVP Inputs

From prior frameworks, gather:

**From Working Backwards:**
- PR headline and subheading
- Solution paragraph
- Key promises and constraints

**From PSF:**
- Our Solution block
- How it connects to problems

Present: "Here's what we've said about our solution..."

### 2. Draft Unique Value Proposition

Present the UVP formula:

> "For **[primary segment]** who struggle with **[top problems]**, **[product]** is a **[category]** that **[core benefit/outcome]**, unlike **[main alternatives]** which **[key shortcoming]**."

Ask:
> "Let's build your UVP. Fill in each part:
> 1. **Primary Segment**: Who from Step 2?
> 2. **Top Problems**: Which 1-2 problems matter most?
> 3. **Product**: What do you call it?
> 4. **Category**: What type of product is it?
> 5. **Core Benefit**: What changes in their world?
> 6. **Main Alternatives**: Name 2 they use today
> 7. **Alternative Shortcoming**: Why are those insufficient?"

Challenge:
- "That benefit is generic — what specifically changes?"
- "Why would someone switch from [alternative]?"

### 3. Validate UVP

Ask:
> "Imagine showing this UVP to your Early Adopters:
> - Would they immediately see themselves and their problems?
> - Would they understand why you're different from [alternatives]?
>
> If not, what needs sharpening?"

### 4. Finalize UVP Block

```markdown
## 3. Unique Value Proposition

**One-Sentence UVP:**
For [segment] who struggle with [problems], [product] is a [category] that [benefit], unlike [alternatives] which [shortcoming].

**Differentiation Basis:**
- vs [Alternative 1]: [How you're different]
- vs [Alternative 2]: [How you're different]

**High-Concept Pitch (optional):**
[X] for [Y] — e.g., "Uber for groceries"
```

### 5. Map Solution Elements

Ask:
> "Now let's define your **top 3-5 solution elements**. For each:
> - What capability or feature?
> - Which Problem does it solve (from Step 2)?
> - How does it change things for the customer?
>
> Remember: express as **what changes for the customer**, not internal modules."

Create mapping table:

| Solution Element | Problem Solved | Customer Change |
|------------------|----------------|-----------------|
| 1. ... | P1 | ... |
| 2. ... | P2 | ... |
| 3. ... | P3 | ... |

### 6. Draft Solution Block

```markdown
## 4. Solution

**Top 3 Features/Capabilities:**

| # | Solution Element | Solves | Customer Change |
|---|------------------|--------|-----------------|
| 1 | [Feature] | P1 | [What changes] |
| 2 | [Feature] | P2 | [What changes] |
| 3 | [Feature] | P3 | [What changes] |

**Integration Considerations:**
- [How it fits existing workflows]
- [Self-serve vs sales-assisted adoption]
```

### 7. Traceability Check

Ask:
> "Let's verify traceability:
> - Does each Solution element connect to a Problem?
> - Is the UVP consistent with your PR headline?"

If gaps exist, iterate before proceeding.

### 8. Tag Assumptions

Add to Assumptions List:

```markdown
### UVP/Solution Assumptions
- **UVP1**: Customers will perceive us as meaningfully different from [alternatives]
- **SOL1**: [Feature 1] will solve [Problem 1] as hypothesized
- **SOL2**: [Feature 2] adoption requires [X] — needs validation
- **SOL3**: Customers will switch from [alternative] because [Y]
```

### 9. Update Output Document

Update lean-canvas.md with completed UVP and Solution blocks.

### 10. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine UVP or solution mapping
- **[P] Party Mode** — get multi-perspective challenge on differentiation
- **[C] Continue** — proceed to Channels & Revenue blocks

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Update lean-canvas.md with UVP and Solution sections
2. Update frontmatter: add `step-03-value-solution` to `stepsCompleted`
3. Load `./step-04-channels-revenue.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** UVP differentiates from named alternatives, each Solution element maps to a Problem, traceability confirmed, assumptions tagged

❌ **FAILURE:** Generic UVP, solution elements without problem mapping, no named alternatives, "save time/money" as only benefit
