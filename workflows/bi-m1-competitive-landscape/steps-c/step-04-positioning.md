---
name: 'step-04-positioning'
description: 'Analyze competitor strengths/weaknesses and map competitive positioning'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/competitive-landscape.md'
partyModeWorkflow: '{project-root}/_bmad/core/workflows/party-mode/workflow.md'
---

# Step 4: Competitor Analysis & Positioning

**Progress: Step 4 of 5** — Next: Synthesis & Project Memo Update

---

## STEP GOAL

Deep-dive on key competitors to understand capabilities and gaps, then visualize the competitive landscape to identify positioning opportunities — all verified via web research.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. No competitor is all-good or all-bad. Find both strengths AND weaknesses. Challenge differentiation claims with evidence.

### Step-Specific Rules
- MUST use web-research tool for competitor analysis
- All competitor claims MUST include source URLs
- Analyze BOTH strengths AND weaknesses for each competitor
- Positioning dimensions must be relevant to customer decision-making

---

## CONTEXT BOUNDARIES

**Available context:**
- Output document with competitor inventory and benchmarks (Steps 2-3)
- JTBD primary job definition

**Out of scope:**
- Strategic recommendations (Step 5)
- Assumption documentation (Step 5)
- Project memo update (Step 5)

---

## MANDATORY SEQUENCE

### 1. Select Top Competitors for Deep Analysis

From Step 2 competitor inventory, prioritize by:
- Market share or mindshare
- Funding and growth trajectory
- Strategic threat level
- Customer overlap

Ask founder: "Which 3-5 competitors should we analyze deeply?"

### 2. Deep-Dive Each Selected Competitor

**WEB SEARCH REQUIRED:**

For each competitor, search:
- "[competitor] reviews"
- "[competitor] vs [alternative]"
- "[competitor] funding announcement"
- "[competitor] features pricing"

Capture for each:

| Dimension | Finding | Source |
|-----------|---------|--------|
| Strengths | What they do well — product, distribution, brand, team | [URL] |
| Weaknesses | Where they underdeliver — product gaps, service issues | [URL] |
| Target Customer | Who they optimize for — segment, size, geography | [URL] |
| Pricing Model | How they charge — subscription tiers, usage-based | [URL] |
| Go-to-Market | How they acquire — sales, PLG, partnerships | [URL] |
| Technology | Known tech stack, integrations, platform dependencies | [URL] |
| Funding/Stage | Investment raised, valuation if known | [URL] |

Present each competitor summary to founder for validation.

### 3. Identify Cross-Competitor Patterns

Analyze patterns across all competitors:

**Common Strengths (Table Stakes):**
- Features/capabilities all competitors have
- Minimum requirements to compete

**Common Weaknesses (Opportunities):**
- Gaps all competitors share
- Pain points customers mention consistently

**Differentiation Dimensions Used:**
- How do competitors distinguish themselves?
- What axes do they compete on?

### 4. Choose Positioning Dimensions

Select 2 dimensions that matter most to customers making the job decision:

| Potential Axis 1 | Potential Axis 2 | Customer Relevance |
|------------------|------------------|-------------------|
| Price | Feature Depth | ... |
| Specialization | Breadth | ... |
| Self-service | High-touch | ... |
| SMB | Enterprise | ... |
| Speed | Accuracy | ... |
| Simplicity | Power | ... |

Ask founder: "Which two dimensions matter most to your target customers?"

### 5. Create Positioning Map

Plot all direct competitors on chosen axes:

```
                    High [Dimension 2]
                           |
                     Comp A   Comp B
                           |
Low [Dim 1] ----+----------+----------+---- High [Dim 1]
                           |
                     Comp C   [Your Position?]
                           |
                    Low [Dimension 2]
```

Identify:
- **White space:** Unoccupied quadrants representing opportunities
- **Crowded zones:** Areas with many competitors
- **Your hypothesized position:** Where you plan to compete

### 6. Create Feature Comparison Table

| Capability | Our Hypothesis | Competitor A | Competitor B | Competitor C | Gap/Opportunity |
|------------|----------------|--------------|--------------|--------------|-----------------|
| [Capability 1] | ... | ... | ... | ... | ... |
| [Capability 2] | ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... |

Target: At least 10 key capabilities compared.

### 7. Analyze Positioning and Messaging

How do competitors position themselves?

| Competitor | Tagline/Value Prop | Target Segment | Pricing Psychology |
|------------|-------------------|----------------|-------------------|
| ... | ... | ... | ... |

### 8. Update competitive-landscape.md

Add Sections 4 and 5 content:

```markdown
## 4. Competitor Deep-Dive

### 4.1 {Competitor A}

| Dimension | Finding | Source |
|-----------|---------|--------|
| Strengths | {strengths} | [{source}](URL) |
| Weaknesses | {weaknesses} | [{source}](URL) |
| Target Customer | {segment} | [{source}](URL) |
| Pricing Model | {pricing} | [{source}](URL) |
| Go-to-Market | {gtm} | [{source}](URL) |
| Technology | {tech} | [{source}](URL) |
| Funding/Stage | {funding} | [{source}](URL) |

### 4.2 {Competitor B}

{Same structure}

### 4.3 Cross-Competitor Patterns

**Common Strengths (Table Stakes):**
- {strength}

**Common Weaknesses (Opportunities):**
- {weakness}

**Differentiation Dimensions:**
- {dimension}

## 5. Competitive Positioning

### 5.1 Positioning Map

**Axes:** {Dimension 1} vs. {Dimension 2}

{Text representation or description of map}

**White Space Identified:** {description}

**Our Hypothesized Position:** {description}

### 5.2 Feature Comparison

| Capability | Our Hypothesis | Comp A | Comp B | Comp C | Gap/Opportunity |
|------------|----------------|--------|--------|--------|-----------------|
| {capability} | {our} | {a} | {b} | {c} | {gap} |

### 5.3 Positioning Analysis

| Competitor | Value Proposition | Target Segment | Pricing Psychology |
|------------|-------------------|----------------|-------------------|
| {competitor} | {value prop} | {segment} | {pricing} |
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-competitor-id', 'step-03-benchmarking', 'step-04-positioning']
```

### 9. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — deeper analysis on specific competitors or positioning
- **[P] Party Mode** — get multi-agent perspectives on positioning strategy
- **[C] Continue** — proceed to Synthesis & Project Memo Update

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append Sections 4 and 5 content to competitive-landscape.md
2. Update frontmatter: add `step-04-positioning` to `stepsCompleted`
3. Load `./step-05-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 3-5 competitors analyzed in depth with strengths AND weaknesses, positioning map with white space identified, 10+ capabilities compared, all with source URLs

❌ **FAILURE:** One-sided competitor analysis, positioning dimensions not relevant to customers, no source URLs
