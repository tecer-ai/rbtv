---
---

# Competitive Landscape Analysis

**Purpose:** Task-based guide for mapping the competitive landscape to understand how the market currently addresses the customer's job-to-be-done, benchmark solutions across geographies and industries, and identify differentiation opportunities.

**Context:**  
Read `conception_process.md` before starting. Execute in M1 Conception Step 4: Map Competitive Landscape. MUST complete Working Backwards and JTBD analysis first.

---

## Framework Overview

Understanding competitors is not about copying features — it's about understanding **how the market currently addresses the customer's job**. This includes direct competitors, indirect alternatives, geographic benchmarks (how mature markets solve this), and cross-industry analogues (how similar problems are solved elsewhere).

**Core concept:** Before you can articulate why your solution fits better, you must understand what alternatives exist, what works, what doesn't, and where the gaps are.

---

## Mandatory Web Research Protocol

**⛔ Web search is REQUIRED for this framework.** If web search is unavailable, abort and inform the user.

Read and follow `.cursor/skills/web-research/SKILL.md` for all research standards.

---

## Task Structure

| Task | Goal | Key Inputs | Key Outputs |
|------|------|------------|-------------|
| 1. Identify Direct and Indirect Competitors | Map products/services addressing the same problem or job | JTBD analysis, Working Backwards customer definition | Competitor inventory with positioning |
| 2. Benchmark Geographic Markets | Understand how US, China, and other mature markets address this problem | Problem statement, job definition | Geographic benchmark with maturity assessment |
| 3. Identify Cross-Industry Analogues | Find solutions to similar problems in adjacent industries | Abstract problem pattern | Analogue inventory with transferable insights |
| 4. Analyze Competitor Strengths and Weaknesses | Deep-dive on key competitors' capabilities and gaps | Competitor inventory | SWOT-lite analysis per major player |
| 5. Map Competitive Positioning | Visualize competitive landscape on key dimensions | All competitor data | Positioning map and feature comparison |
| 6. Extract Threats and Opportunities | Identify competitive risks and differentiation opportunities | Full competitive analysis | Threat inventory and opportunity list |
| 7. Document Assumptions for Validation | Tag competitive assumptions for M2 stress-testing | All outputs | Assumption inventory with categories |

---

## Task 1: Identify Direct and Indirect Competitors

**Goal:** Map the current competitive landscape in your target market, including direct competitors, indirect alternatives, and non-consumption.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| JTBD analysis (primary job, alternatives) | M1 JTBD framework | Yes |
| Working Backwards customer definition | M1 Working Backwards framework | Yes |
| Problem statement | M1 Steps 2-3 | Yes |

**Action:**

1. **Web Search Required:** Search for direct competitors solving the same problem for the same customer segment.
   - Search queries: "[problem] software/solution", "[industry] [problem] tools", "alternatives to [known competitor]"
   - For each competitor found, capture: name, positioning, target customer, pricing model, key features
2. **Identify Indirect Competitors:** From JTBD analysis, identify what customers currently "hire" to get the job done:
   - Other product categories that address the same job
   - Workarounds (spreadsheets, email, manual processes)
   - Professional services or consultants
   - Internal solutions (shadow IT, custom builds)
3. **Map Non-Consumption:** Identify why some customers do nothing:
   - Awareness gaps
   - Cost/complexity barriers
   - Regulatory or organizational constraints
   - Inertia and habit strength
4. Create a structured competitor inventory.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Direct Competitors list | Table with name, positioning, pricing, key features, source URL | Maps primary competitive set |
| Indirect Competitors list | Table with category, how it addresses the job, limitations | Maps alternative solutions customers hire |
| Non-Consumption analysis | Bulleted list of reasons for non-adoption | Identifies potential market expansion opportunities |

**Validation:**

- [ ] You have identified at least **3-5 direct competitors** with verified current information
- [ ] You have identified at least **3-5 indirect alternatives** from JTBD "current hiring"
- [ ] Each competitor entry includes a **source URL** for verification
- [ ] You can explain why each competitor is or isn't satisfying the primary job

---

## Task 2: Benchmark Geographic Markets

**Goal:** Understand how the problem is addressed in mature markets (US, China) to identify proven models, lessons, and potential market trajectory.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Problem statement | M1 Steps 2-3 | Yes |
| Primary job definition | JTBD analysis | Yes |
| Direct competitors from Task 1 | Task 1 output | Yes |

**Action:**

1. **Benchmark United States Market:**
   - **Web Search Required:** Search for US market leaders, funding rounds, market size data
   - Search queries: "[problem] market USA", "[industry] software leaders US", "[problem] startup funding"
   - Capture for each dimension:

   | Dimension | What to Capture | Source |
   |-----------|-----------------|--------|
   | Leading Players | Top 3-5 companies, market share if available | [URL] |
   | Solution Maturity | Early/Growth/Mature stage, years ahead/behind your market | [URL] |
   | Business Models | Subscription, transaction, freemium, enterprise | [URL] |
   | Regulatory Environment | Key regulations shaping the market | [URL] |
   | Adoption Patterns | How did adoption happen? What drove growth? | [URL] |
   | Lessons/Failures | Notable failures, pivots, or market corrections | [URL] |

2. **Benchmark China Market:**
   - **Web Search Required:** Search for China market solutions, super-app integrations, unique approaches
   - Search queries: "[problem] China market", "[industry] solution China", "Chinese [problem] apps"
   - Capture for each dimension:

   | Dimension | What to Capture | Source |
   |-----------|-----------------|--------|
   | Leading Players | Top companies (consider BAT ecosystem, super-apps) | [URL] |
   | Solution Maturity | Stage, unique trajectory vs. Western markets | [URL] |
   | Business Models | Often different patterns — capture specifics | [URL] |
   | Regulatory Environment | Key regulations and their impact | [URL] |
   | Technology Stack | WeChat/Alipay ecosystem, mobile-first patterns | [URL] |
   | Scale Dynamics | How scale is achieved — often different from West | [URL] |

3. **Optional: Other Relevant Markets:**
   - If relevant, add sections for EU, India, Southeast Asia, Latin America
   - Focus on markets with unique approaches or regulatory environments

4. **Synthesize Geographic Insights:**
   - What can be imported directly?
   - What must be adapted to local conditions?
   - What mistakes can be avoided?
   - How many years ahead/behind is your market?

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| US Market Benchmark | Structured table with all dimensions + sources | Identifies proven models and trajectory |
| China Market Benchmark | Structured table with all dimensions + sources | Identifies alternative approaches and scale patterns |
| Geographic Synthesis | Summary table comparing markets + key lessons | Actionable insights for local strategy |

**Validation:**

- [ ] US benchmark has at least **3 leading players** with verified current data
- [ ] China benchmark captures at least **2-3 unique approaches** not seen in Western markets
- [ ] You have explicit **"lessons for our context"** documented
- [ ] All market data includes **source URLs** and approximate dates

---

## Task 3: Identify Cross-Industry Analogues

**Goal:** Find solutions to similar problems in adjacent industries to import innovation patterns and avoid reinventing wheels.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Primary job and problem statement | JTBD, Working Backwards | Yes |
| Understanding of core problem mechanics | Tasks 1-2 | Yes |

**Action:**

1. **Abstract the Core Problem Pattern:**
   - Strip away industry-specific language
   - Describe the fundamental problem mechanics
   - Example: "home equity loan" → "unlocking illiquid asset value for liquidity needs"

2. **Identify Analogous Industries:**
   - **Web Search Required:** Search for similar problem patterns in other industries
   - Brainstorm industries facing similar challenges:

   | Your Problem Pattern | Potential Analogous Industries |
   |---------------------|-------------------------------|
   | Asset liquidity | Auto finance, invoice factoring, art-backed lending, crypto collateral |
   | Matching/marketplace | Dating, job boards, real estate, freelance platforms |
   | Compliance/verification | KYC/AML, identity verification, background checks |
   | Subscription management | SaaS, media streaming, fitness, B2B software |

3. **Deep-Dive 2-3 Most Relevant Analogues:**
   - For each analogue, research:

   | Dimension | What to Capture | Source |
   |-----------|-----------------|--------|
   | Solution Mechanics | How does it work technically? | [URL] |
   | Customer Journey | How do customers discover/use it? | [URL] |
   | Risk Management | How is risk managed? (valuation, default, etc.) | [URL] |
   | Unit Economics | What makes it profitable? | [URL] |
   | Friction Points | Where does experience break down? | [URL] |
   | Innovations | What differentiates leaders? | [URL] |

4. **Extract Transferable Insights:**
   - What business model elements can be borrowed?
   - What risk management approaches apply?
   - What customer acquisition strategies worked?
   - What technology infrastructure is reusable?

5. **Identify Non-Transferable Elements:**
   - What is specific to that industry and won't work here?
   - What regulatory differences prevent direct transfer?

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Core Problem Pattern | Single sentence abstraction | Enables analogue identification |
| Analogue Inventory | Table with industry, problem, solution approach, source | Maps cross-industry solutions |
| Transferable Insights | Table with insight, source industry, applicability, how to apply | Actionable innovation import |
| Non-Transferable Elements | Bulleted list | Prevents inappropriate borrowing |

**Validation:**

- [ ] You have abstracted your problem to a **generic pattern** that applies across industries
- [ ] You have identified at least **3 analogous industries** with verified solutions
- [ ] You have deep-dived at least **1-2 analogues** with full dimension analysis
- [ ] You have explicit **transferable vs. non-transferable** distinctions

---

## Task 4: Analyze Competitor Strengths and Weaknesses

**Goal:** Deep-dive on key competitors to understand their capabilities, gaps, and strategic positions.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Direct competitors inventory | Task 1 | Yes |
| Geographic benchmark insights | Task 2 | No |

**Action:**

1. **Select Top 3-5 Competitors for Deep Analysis:**
   - Prioritize by: market share, funding, mindshare, or strategic threat
   
2. **For Each Competitor, Analyze:**
   - **Web Search Required:** Search for competitor reviews, feature comparisons, funding announcements
   
   | Dimension | What to Capture | Source |
   |-----------|-----------------|--------|
   | Strengths | What they do well — product, distribution, brand, team | [URL] |
   | Weaknesses | Where they underdeliver — product gaps, service issues, limitations | [URL] |
   | Target Customer | Who they optimize for — segment, size, geography | [URL] |
   | Pricing Model | How they charge — subscription tiers, usage-based, freemium | [URL] |
   | Go-to-Market | How they acquire customers — sales, PLG, partnerships | [URL] |
   | Technology | Known tech stack, integrations, platform dependencies | [URL] |
   | Funding/Stage | Investment raised, valuation if known, growth trajectory | [URL] |

3. **Identify Patterns Across Competitors:**
   - Common strengths (table stakes for the market)
   - Common weaknesses (opportunities)
   - Differentiation dimensions competitors use

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Competitor Deep-Dive | One section per competitor with all dimensions | Detailed competitive intelligence |
| Cross-Competitor Patterns | Summary of common strengths/weaknesses | Identifies table stakes and opportunities |

**Validation:**

- [ ] You have analyzed at least **3-5 key competitors** in depth
- [ ] Each analysis includes **both strengths and weaknesses** (no competitor is all-good or all-bad)
- [ ] You have identified **common patterns** across competitors
- [ ] All claims are backed by **source URLs**

---

## Task 5: Map Competitive Positioning

**Goal:** Visualize the competitive landscape on key dimensions and create a feature comparison for strategic planning.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| All competitor data | Tasks 1-4 | Yes |
| JTBD primary job | JTBD analysis | Yes |

**Action:**

1. **Select Positioning Dimensions:**
   - Choose 2 dimensions that matter most to customers making the primary job decision
   - Common axes:
     - Price vs. Feature Depth
     - Specialization vs. Breadth
     - Self-service vs. High-touch
     - SMB vs. Enterprise
     - Speed vs. Accuracy
     - Simplicity vs. Power

2. **Create Positioning Map:**
   - Plot all direct competitors on a 2x2 matrix
   - Include your hypothesized position
   - Identify "white space" (unoccupied quadrants)

3. **Create Feature/Capability Comparison:**

   | Capability | Us (Hypothesis) | Competitor A | Competitor B | Competitor C | Gap/Opportunity |
   |------------|-----------------|--------------|--------------|--------------|-----------------|
   | [Capability 1] | ... | ... | ... | ... | ... |
   | [Capability 2] | ... | ... | ... | ... | ... |

4. **Analyze Market Positioning and Messaging:**
   - How do competitors position themselves? (taglines, value propositions)
   - What customer segments do they target in messaging?
   - What pricing psychology do they use?

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Competitive Positioning Map | 2x2 matrix or multi-axis visual | Visualizes competitive landscape |
| Feature Comparison Table | Table with capability ratings | Identifies feature gaps and parity |
| Positioning Analysis | Narrative on messaging patterns | Informs differentiation strategy |

**Validation:**

- [ ] Positioning dimensions are **relevant to customer decision-making**, not internal metrics
- [ ] Positioning map shows at least **1-2 areas of white space** or opportunity
- [ ] Feature comparison covers at least **10 key capabilities**
- [ ] Your hypothesized position is **explicitly placed** on the map

---

## Task 6: Extract Threats and Opportunities

**Goal:** Synthesize all competitive analysis into actionable threats to defend against and opportunities to pursue.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| All outputs from Tasks 1-5 | Previous tasks | Yes |

**Action:**

1. **Identify Competitive Threats:**

   | Threat Category | Specific Threats |
   |-----------------|------------------|
   | Incumbent Advantages | Distribution, brand, switching costs, data moats |
   | Emerging Players | Well-funded startups, pivoting companies |
   | Platform Risk | Dependency on ecosystems (AWS, Apple, Google, etc.) |
   | Geographic Entry | Could US/China players enter your market? |
   | Cross-Industry Disruption | Could adjacent industry players expand into your space? |
   | Technology Shifts | Could new tech (AI, blockchain, etc.) commoditize your value? |
   | Regulatory Changes | Could regulation favor incumbents or new entrants? |

2. **Identify Differentiation Opportunities:**

   | Opportunity Source | Specific Opportunities |
   |--------------------|------------------------|
   | Competitor Weaknesses | Gaps all competitors share |
   | Underserved Segments | Customer segments competitors ignore |
   | Unmet Jobs | Jobs-to-be-done competitors don't address |
   | Geographic Lessons | Innovations from mature markets not yet applied |
   | Cross-Industry Patterns | Innovations from analogues not yet imported |
   | Positioning White Space | Unoccupied areas in positioning map |
   | Technology Arbitrage | New tech competitors haven't adopted |

3. **Prioritize Opportunities:**
   - Rate each opportunity on: Impact (high/medium/low) × Feasibility (high/medium/low)
   - Select top 3-5 opportunities to inform solution design

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Threat Inventory | Table with category, threat, severity, mitigation | Identifies risks to address |
| Opportunity Inventory | Table with source, opportunity, impact, feasibility | Identifies differentiation paths |
| Prioritized Opportunities | Top 3-5 ranked opportunities | Focuses solution design |

**Validation:**

- [ ] You have identified threats across at least **4 categories**
- [ ] You have identified opportunities from at least **4 sources**
- [ ] You have **prioritized opportunities** by impact and feasibility
- [ ] Threats and opportunities are **specific and actionable**, not generic

---

## Task 7: Document Assumptions for Validation

**Goal:** Tag all competitive assumptions for stress-testing in M2 Validation.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| All outputs from Tasks 1-6 | Previous tasks | Yes |

**Action:**

1. **Extract Assumptions Made During Analysis:**
   - Competitor capability claims (they lack X, they can't do Y)
   - Market maturity assessments
   - Customer behavior predictions
   - Technology feasibility
   - Differentiation hypotheses

2. **Tag Each Assumption:**

   | Assumption | Category | Confidence | Validation Method |
   |------------|----------|------------|-------------------|
   | Competitor X lacks Y capability | Competitive | Medium | Product trial, feature docs |
   | Segment Z is underserved | Market | Low | Customer interviews |
   | US model will work in our market | Geographic Transfer | Low | Market test, localization research |
   | Risk model from [industry] applies | Cross-Industry | Medium | Domain expert review |

3. **Categorize Assumptions:**
   - **Competitive:** About specific competitor capabilities or strategies
   - **Market:** About market structure, size, or dynamics
   - **Geographic Transfer:** About applicability of foreign market patterns
   - **Cross-Industry:** About transferability of analogue solutions
   - **Customer:** About customer behavior or preferences

4. **Prioritize for M2:**
   - Flag assumptions that, if wrong, would invalidate differentiation strategy
   - Connect to Leap of Faith and Assumption Mapping in M2

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Assumption Inventory | Table with all assumptions, categories, confidence, validation | Feeds M2 Validation |
| High-Risk Assumptions | Flagged subset requiring immediate validation | Prioritizes M2 work |

**Validation:**

- [ ] You have documented at least **10-15 assumptions** from the analysis
- [ ] Each assumption has a **category and confidence level**
- [ ] Each assumption has a **proposed validation method**
- [ ] You have flagged **3-5 high-risk assumptions** for priority validation

---

## Final Document Structure

The Competitive Landscape analysis document should be saved to `[project]/docs/founder/conception/competitive_landscape.md` with this structure:

```markdown
# Competitive Landscape Analysis

## Document Metadata
- **Date:** [date]
- **Author:** [user]
- **Primary Job:** [from JTBD]
- **Target Market:** [geography]

---

## 1. Current Alternatives Inventory

### 1.1 Direct Competitors
[Table with competitors, positioning, pricing, source URLs]

### 1.2 Indirect Competitors
[Table with alternatives, how they address the job, limitations]

### 1.3 Non-Consumption
[Why some customers do nothing]

---

## 2. Geographic Benchmarking

### 2.1 United States Market
[Dimension table with sources]

**Key Insights for Our Context:**
- ...

### 2.2 China Market
[Dimension table with sources]

**Key Insights for Our Context:**
- ...

### 2.3 Geographic Synthesis
[Comparison table + lessons]

---

## 3. Cross-Industry Analogues

### 3.1 Core Problem Pattern
[Abstract problem statement]

### 3.2 Analogue Inventory
[Table with industries, problems, solutions]

### 3.3 Deep-Dive: [Analogue 1]
[Full dimension analysis]

### 3.4 Transferable Insights
[Table with insights and applicability]

---

## 4. Competitor Deep-Dive

### 4.1 [Competitor A]
[Full dimension analysis]

### 4.2 [Competitor B]
[Full dimension analysis]

### 4.3 Cross-Competitor Patterns
[Common strengths/weaknesses]

---

## 5. Competitive Positioning

### 5.1 Positioning Map
[2x2 or multi-axis visual]

### 5.2 Feature Comparison
[Capability table]

### 5.3 Positioning Analysis
[Messaging patterns]

---

## 6. Threats and Opportunities

### 6.1 Threat Inventory
[Table with threats and mitigations]

### 6.2 Opportunity Inventory
[Table with opportunities and feasibility]

### 6.3 Prioritized Opportunities
[Top 3-5 ranked]

---

## 7. Assumptions for Validation

### 7.1 Full Assumption Inventory
[Table with all assumptions]

### 7.2 High-Risk Assumptions
[Flagged subset for M2]

---

## Summary

### Key Competitive Findings
- ...

### Strategic Implications
- ...

### Next Steps
- ...
```

---

## Pitfalls

**Relying on Training Data Alone**

NEVER fill competitive analysis from memory without web verification. MUST search for current competitor data, funding, features, and market dynamics.

**Ignoring Non-Traditional Competitors**

NEVER focus only on direct competitors. MUST include indirect alternatives, workarounds, and non-consumption in analysis.

**Ignoring Geographic Context**

NEVER assume your market is unique. MUST benchmark mature markets (US, China) to understand trajectory and import proven patterns.

**Surface-Level Competitor Analysis**

NEVER stop at "Competitor X exists." MUST analyze strengths, weaknesses, positioning, and strategic implications.

**Unverified Differentiation Claims**

NEVER assume competitors lack capabilities without verification. MUST tag claims as assumptions.

**Analysis Without Action**

NEVER produce competitive analysis without explicit opportunities and assumptions. MUST connect findings to differentiation strategy and M2 validation.

---

## Integration

**Prerequisites:**  
MUST complete Working Backwards (PR/FAQ) and JTBD analysis before starting. Web search capability is REQUIRED.

**Builds On:**

| Framework | Output Used | How Used |
|-----------|-------------|----------|
| Working Backwards (PR/FAQ) | Customer definition, problem statement | Defines who we're solving for and what problem |
| Jobs-To-Be-Done | Primary job, current alternatives, forces | Provides customer context and "hiring" behavior |

**Feeds Into:**

| Framework | Output Provided | How Used |
|-----------|-----------------|----------|
| Problem-Solution Fit Canvas | Available Solutions, Alternatives, Constraints | Grounds solution in competitive context |
| Lean Canvas | Unfair Advantage, Channels, Competition | Populates competitive blocks with verified data |
| Project Memo | Solution section, Tenets | Ensures solution is positioned against alternatives |
| M2 Leap of Faith | Competitive assumptions | Seeds validation backlog |
| M2 Pre-mortem | Competitive threats | Informs failure mode analysis |

**Workflow Position:**

Competitive Landscape sits in M1 directly after JTBD and before Problem-Solution Fit Canvas.

---

## Success Criteria

This framework is complete when:

- [ ] You have identified at least **5 direct competitors** and **5 indirect alternatives** with verified data
- [ ] You have benchmarked **US and China markets** with specific players and lessons
- [ ] You have identified at least **3 cross-industry analogues** with transferable insights
- [ ] You have a **positioning map** with your hypothesized position and identified white space
- [ ] You have documented at least **5 competitive threats** and **5 differentiation opportunities**
- [ ] You have tagged at least **10 assumptions** for M2 validation
- [ ] All factual claims include **source URLs**
- [ ] Problem-Solution Fit and Lean Canvas can reference competitive analysis for alternatives and positioning

---

## References

Framework design informed by:

- BMAD Method — Competitive Analysis workflow (`https://github.com/bmad-code-org/BMAD-METHOD`)
- Competitive Intelligence methodologies from strategy consulting literature
- Blue Ocean Strategy (Kim & Mauborgne) — for positioning and white space analysis
- Porter's Competitive Strategy — for competitive forces framework

---

## For AI Agents

**Execution Context:**

1. **CRITICAL:** Web search is MANDATORY for this framework. If unavailable, abort and inform user.
2. Read `conception_process.md`, Working Backwards, and JTBD analysis before starting.
3. Read and follow `.cursor/skills/web-research/SKILL.md` for all research standards.
4. Track progress: "Currently in Task [N]: [Task Name]".
5. Confirm each task's validation checklist before proceeding.
6. Record key competitive insights and assumptions in M1 founder log.

**Working With Tasks:**

- Complete each task atomically.
- If validation criterion cannot be met (e.g., no web access), surface risk and propose alternatives.
- When competitive assumption emerges, tag it clearly and suggest how it might be validated in M2.

---

