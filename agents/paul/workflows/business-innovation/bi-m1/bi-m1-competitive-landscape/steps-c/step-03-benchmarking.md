---
name: 'step-03-benchmarking'
description: 'Benchmark US/China markets and identify cross-industry analogues'
nextStepFile: './step-04-positioning.md'
outputFile: '{outputFolder}/competitive-landscape.md'
---

# Step 3: Geographic & Cross-Industry Benchmarking

**Progress: Step 3 of 5** — Next: Competitor Analysis & Positioning

---

## STEP GOAL

Understand how mature markets (US, China) address the problem and identify cross-industry analogues with transferable insights — all verified via web research.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Demand specific player names, funding data, and lessons. Vague market descriptions are unacceptable.

### Step-Specific Rules
- MUST use web-research tool for all market data
- All market claims MUST include source URLs and approximate dates
- Abstract the problem pattern before searching for analogues
- Document both transferable AND non-transferable elements

---

## CONTEXT BOUNDARIES

**Available context:**
- Output document with competitor inventory (Step 2)
- Problem statement and job definition

**Out of scope:**
- Detailed competitor strengths/weaknesses (Step 4)
- Positioning map (Step 4)
- Threats and opportunities synthesis (Step 5)

---

## MANDATORY SEQUENCE

### 1. Benchmark United States Market

**WEB SEARCH REQUIRED:**

Execute searches:
- "[problem] market USA"
- "[industry] software leaders US"
- "[problem] startup funding"
- "[industry] market size trends"

Capture for each dimension:

| Dimension | Finding | Source |
|-----------|---------|--------|
| Leading Players | Top 3-5 companies, market share if available | [URL] |
| Solution Maturity | Early/Growth/Mature stage | [URL] |
| Business Models | Subscription, transaction, freemium, enterprise | [URL] |
| Regulatory Environment | Key regulations shaping the market | [URL] |
| Adoption Patterns | How did adoption happen? What drove growth? | [URL] |
| Lessons/Failures | Notable failures, pivots, or market corrections | [URL] |

**Key Insights for Our Context:** [What can be imported, adapted, or avoided]

### 2. Benchmark China Market

**WEB SEARCH REQUIRED:**

Execute searches:
- "[problem] China market"
- "[industry] solution China"
- "Chinese [problem] apps"
- "[category] WeChat mini-program"

Capture for each dimension:

| Dimension | Finding | Source |
|-----------|---------|--------|
| Leading Players | Top companies (consider BAT ecosystem, super-apps) | [URL] |
| Solution Maturity | Stage, unique trajectory vs. Western markets | [URL] |
| Business Models | Often different patterns — capture specifics | [URL] |
| Regulatory Environment | Key regulations and their impact | [URL] |
| Technology Stack | WeChat/Alipay ecosystem, mobile-first patterns | [URL] |
| Scale Dynamics | How scale is achieved — often different from West | [URL] |

**Key Insights for Our Context:** [Unique approaches to consider]

### 3. Geographic Synthesis

Create comparison table:

| Dimension | US | China | Lessons for Us |
|-----------|-----|-------|----------------|
| Leading Players | ... | ... | ... |
| Business Model | ... | ... | ... |
| Key Differentiator | ... | ... | ... |
| Maturity vs. Our Market | ... | ... | ... |

Present to founder: "Here's what we can learn from mature markets..."

### 4. Abstract Core Problem Pattern

Before searching for cross-industry analogues, abstract the problem:
- Strip away industry-specific language
- Describe fundamental problem mechanics
- Example: "home equity loan" → "unlocking illiquid asset value for liquidity needs"

Ask founder: "Does this abstraction capture the essence of what we're solving?"

### 5. Identify Cross-Industry Analogues

**WEB SEARCH REQUIRED:**

Based on the abstract pattern, search adjacent industries:
- "[abstract problem] solutions"
- "[similar problem] different industry"
- "how [industry] solved [problem pattern]"

Capture 3+ analogues:

| Industry | Problem | Solution Approach | Source |
|----------|---------|-------------------|--------|
| ... | ... | ... | [URL] |

Deep-dive 1-2 most relevant analogues:

| Dimension | Finding | Source |
|-----------|---------|--------|
| Solution Mechanics | How does it work technically? | [URL] |
| Customer Journey | How do customers discover/use it? | [URL] |
| Risk Management | How is risk managed? | [URL] |
| Innovations | What differentiates leaders? | [URL] |

### 6. Extract Transferable vs. Non-Transferable

**Transferable Insights:**

| Insight | Source Industry | How to Apply |
|---------|-----------------|--------------|
| ... | ... | ... |

**Non-Transferable Elements:**

| Element | Why It Won't Work | Source Industry |
|---------|-------------------|-----------------|
| ... | ... | ... |

### 7. Update competitive-landscape.md

Add Sections 2 and 3 content:

```markdown
## 2. Geographic Benchmarking

### 2.1 United States Market

| Dimension | Finding | Source |
|-----------|---------|--------|
| {dimension} | {finding} | [{source}](URL) |

**Key Insights for Our Context:**
- {insight}

### 2.2 China Market

| Dimension | Finding | Source |
|-----------|---------|--------|
| {dimension} | {finding} | [{source}](URL) |

**Key Insights for Our Context:**
- {insight}

### 2.3 Geographic Synthesis

| Dimension | US | China | Lessons for Us |
|-----------|-----|-------|----------------|
| {dimension} | {us} | {china} | {lesson} |

## 3. Cross-Industry Analogues

### 3.1 Core Problem Pattern

{Abstract problem statement}

### 3.2 Analogue Inventory

| Industry | Problem | Solution Approach | Source |
|----------|---------|-------------------|--------|
| {industry} | {problem} | {approach} | [{source}](URL) |

### 3.3 Deep-Dive: {Analogue Name}

| Dimension | Finding | Source |
|-----------|---------|--------|
| {dimension} | {finding} | [{source}](URL) |

### 3.4 Transferable Insights

| Insight | Source Industry | How to Apply |
|---------|-----------------|--------------|
| {insight} | {industry} | {application} |

### 3.5 Non-Transferable Elements

| Element | Why It Won't Work |
|---------|-------------------|
| {element} | {reason} |
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-competitor-id', 'step-03-benchmarking']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Competitor Analysis & Positioning

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append Sections 2 and 3 content to competitive-landscape.md
2. Update frontmatter: add `step-03-benchmarking` to `stepsCompleted`
3. Load `./step-04-positioning.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** US and China benchmarks with at least 3 leading players each, 3+ cross-industry analogues identified, 1-2 deep-dives completed, all with source URLs

❌ **FAILURE:** Vague market descriptions without specific players, no source URLs, skipping cross-industry analysis
