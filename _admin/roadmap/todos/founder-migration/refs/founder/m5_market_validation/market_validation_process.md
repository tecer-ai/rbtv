---
---

# Market Validation Process

**Purpose:** Detailed process guide for Milestone 5 (Market Validation) of the founder module. Tests the prototype with real potential customers to validate demand, pricing, channels, and product-market fit signals before committing to full MVP development.

**Goal:** Validate market demand and pricing with minimal spending by running structured customer conversations, smoke tests, and pricing research that produce empirical evidence for persevere/pivot/kill decisions.

---

## Inputs

| Input | Source |
|-------|--------|
| Working HTML prototype | M4 Prototypation |
| F&F test results and feedback | M4 Step 8 |
| Validated business concept | M1 Conception frameworks |
| Feasibility assessment | M2 Validation frameworks |
| Brand identity | M3 Brand frameworks |
| Assumption backlog | M2 Leap of Faith assumptions |

---

## Outputs

| Output | Format |
|--------|--------|
| SPIN selling conversation scripts | Markdown document (`[project]/docs/founder/market_validation/spin_selling.md`) |
| Mom Test interview notes | Markdown document (`[project]/docs/founder/market_validation/mom_test.md`) |
| Smoke test results | Markdown document (`[project]/docs/founder/market_validation/smoke_test.md`) |
| Pricing research (Van Westendorp) | Markdown document (`[project]/docs/founder/market_validation/van_westendorp.md`) with competitive pricing benchmarks, inline citations, and sources legend table |
| Channel prioritization (Bullseye) | Markdown document (`[project]/docs/founder/market_validation/bullseye.md`) with industry benchmarks, inline citations, and sources legend table |
| PMF signal assessment (Sean Ellis) | Markdown document (`[project]/docs/founder/market_validation/sean_ellis_pmf.md`) |
| M5 Founder Diary | Markdown table (`[project]/docs/founder/market_validation/m5_founder_diary.md`) |

---

## Steps Summary

| Step | Action | Framework | Output |
|------|--------|-----------|--------|
| 1 | Initialize M5 structure and prepare assumption backlog | — | M5 folder structure, prioritized assumptions |
| 2 | Conduct bias-free customer interviews | Mom Test | Interview notes, validated/refuted assumptions |
| 3 | Run hypothesis-testing sales conversations | SPIN Selling | Conversation evidence, value/growth hypothesis status |
| 4 | Launch smoke tests to measure real behavior | Smoke Test | Conversion data, behavioral evidence |
| 5 | Research pricing with structured methodology **[WEB RESEARCH MANDATORY]** | Van Westendorp PSM | Acceptable price range, optimal price point |
| 6 | Prioritize acquisition channels **[WEB RESEARCH MANDATORY]** | Bullseye Framework | Top 3 channels with test results |
| 7 | Measure product-market fit signal | Sean Ellis PMF Survey | PMF score and recommendation |
| 8 | Synthesize findings and make persevere/pivot/kill decision | — | Decision document, updated memo and diary |

---

## Step 1: Initialize M5 Structure

**Inputs:** Project name, M2 assumption backlog, M4 prototype

**Action:**
1. Create milestone folder: `[project]/docs/founder/market_validation/`
2. Initialize founder diary from the template: [founder_diary.md](../templates/founder_diary.md)
3. Review M2 Leap of Faith assumptions — identify which remain unvalidated
4. Prioritize assumptions by risk: which, if wrong, would kill the business?
5. Review M4 F&F test feedback for early signals
6. Update Session Status in m5_founder_diary.md

**Output:** M5 folder structure, prioritized assumption backlog

**Framework Reference:** None (structural setup)

---

## Step 2: Conduct Bias-Free Customer Interviews (Mom Test)

**Inputs:** Assumption backlog, target customer profile

**Action:**
1. Design interview guide using Mom Test principles:
   - Ask about their life, not your idea
   - Ask about specifics in the past, not hypotheticals about the future
   - Talk less, listen more
2. Prepare questions that test assumptions without revealing your solution:
   - "Tell me about the last time you dealt with [problem]..."
   - "What did you do? What happened next?"
   - "What have you tried to solve this? What did you spend?"
   - "How are you dealing with this today?"
3. Conduct 10-15 interviews with target customers
4. For each interview, document:
   - Specific past behaviors (not opinions)
   - Money/time already spent on the problem
   - Emotional intensity around the problem
   - Current solutions and workarounds
5. Map interview findings to assumptions: validated, refuted, or uncertain
6. Save to `[project]/docs/founder/market_validation/mom_test.md`

**Output:** Interview notes with assumption validation status

**Framework Reference:** Mom Test methodology

---

## Step 3: Run Hypothesis-Testing Conversations (SPIN Selling)

**Inputs:** Mom Test findings, M2 Value/Growth Hypotheses

**Action:**
1. Read SPIN Selling framework: [spin_selling.md](market_validation_frameworks/spin_selling.md)
2. Follow Tasks 1-6 to:
   - Map M2 assumptions to SPIN question types (Situation → Problem → Implication → Need-Payoff)
   - Execute structured conversations testing Value Hypothesis (do customers have this pain?) and Growth Hypothesis (will they pay to solve it?)
   - Quantify problem costs through Implication questions
   - Test buying intent through Need-Payoff questions
3. Conduct 10-15 SPIN conversations with target customers
4. Synthesize validation evidence against M2 assumptions
5. Save to `[project]/docs/founder/market_validation/spin_selling.md`

**Output:** SPIN conversation evidence, assumption validation synthesis

**Framework Reference:** [spin_selling.md](market_validation_frameworks/spin_selling.md)

---

## Step 4: Launch Smoke Tests

**Inputs:** Prototype, channel hypotheses, conversion goal

**Action:**
1. Design smoke test using the M4 prototype:
   - Landing page with email signup or waitlist
   - Fake door test (CTA for feature that does not yet exist — measures intent)
   - Pre-order page (strongest signal: money commitment)
2. Define success metrics before launching:
   - Target conversion rate (e.g., 5% email signup, 2% pre-order)
   - Minimum sample size for statistical relevance (100+ visitors minimum)
   - Time window for test (1-2 weeks typical)
3. Drive traffic to prototype through 1-2 channels (from Bullseye hypothesis)
4. Measure actual behavior, not stated intent:
   - Clicks, signups, purchases, time on page, scroll depth
   - Compare against success thresholds
5. Document results with actual numbers
6. Save to `[project]/docs/founder/market_validation/smoke_test.md`

**Output:** Smoke test results with conversion data

**Framework Reference:** Smoke Test methodology

---

## Step 5: Research Pricing (Van Westendorp PSM)

**Inputs:** Customer interview insights, competitive landscape, value proposition

**Action:**
1. **Web research is MANDATORY for this step.** Read and follow [web-research/SKILL.md](../../../.cursor/skills/web-research/SKILL.md)
2. Research competitor pricing, industry pricing models, and pricing trends
3. Design Van Westendorp Price Sensitivity Meter survey with 4 questions:
   - At what price would this product be so cheap you would doubt its quality? (Too Cheap)
   - At what price would this product be a bargain — a great buy for the money? (Cheap/Good Value)
   - At what price would this product be getting expensive but you would still consider it? (Expensive/High)
   - At what price would this product be too expensive to consider? (Too Expensive)
4. Collect responses from 30+ target customers (minimum for statistical reliability)
5. Plot cumulative frequency distributions for each price point
6. Identify key intersections:
   - Point of Marginal Cheapness (Too Cheap intersects Expensive)
   - Point of Marginal Expensiveness (Cheap intersects Too Expensive)
   - Optimal Price Point (Too Cheap intersects Too Expensive)
   - Indifference Price Point (Cheap intersects Expensive)
7. Define acceptable price range: between Marginal Cheapness and Marginal Expensiveness
8. Cross-reference with M2 Unit Economics: does the price support viable unit economics?
9. Validate against competitive pricing benchmarks
10. Document all pricing sources per web-research skill requirements
11. Save to `[project]/docs/founder/market_validation/van_westendorp.md`

**Output:** Acceptable price range, optimal price point, competitive pricing context, unit economics validation, and sources legend

**Framework Reference:** Van Westendorp Price Sensitivity Meter

---

## Step 6: Prioritize Acquisition Channels (Bullseye Framework)

**Inputs:** Smoke test data, customer interview insights, budget constraints

**Action:**
1. **Web research is MANDATORY for this step.** Read and follow [web-research/SKILL.md](../../../.cursor/skills/web-research/SKILL.md)
2. Research industry CAC by channel, conversion benchmarks, channel saturation, and emerging channels
3. Brainstorm all 19 traction channels:
   - Viral marketing, PR, unconventional PR, SEM, social/display ads, offline ads, SEO, content marketing, email marketing, engineering as marketing, targeting blogs, business development, sales, affiliate programs, existing platforms, trade shows, offline events, speaking engagements, community building
4. Categorize into three rings:
   - **Inner ring (3 channels):** Most promising based on evidence from Steps 2-4 and industry benchmarks
   - **Middle ring (6 channels):** Worth testing with small budget
   - **Outer ring (remaining):** Not pursuing now
5. For each inner ring channel, run a cheap test:
   - Budget: $100-500 per channel maximum
   - Duration: 1-2 weeks per test
   - Measure: cost per acquisition, conversion rate, volume potential
   - Compare results against industry benchmarks
6. Rank channels by: cost per acquisition, scalability, time to results
7. Select top 1-2 channels for M6 MVP launch
8. Document all channel benchmark sources per web-research skill requirements
9. Save to `[project]/docs/founder/market_validation/bullseye.md`

**Output:** Prioritized channel list with test results, industry benchmarks, top channels selected for MVP, and sources legend

**Framework Reference:** Bullseye Framework (Gabriel Weinberg)

---

## Step 7: Measure Product-Market Fit Signal (Sean Ellis PMF Survey)

**Inputs:** Smoke test users, interview participants, early users

**Action:**
1. Administer the Sean Ellis survey to people who experienced the prototype or concept:
   - Core question: "How would you feel if you could no longer use [product]?"
   - Answers: Very disappointed / Somewhat disappointed / Not disappointed / N/A
2. Collect minimum 30 responses from target customers (not friends/family)
3. Calculate PMF score: percentage who answer "Very disappointed"
4. Interpret results:
   - **40%+ "Very disappointed":** Strong PMF signal — proceed to MVP
   - **25-40%:** Moderate signal — iterate on positioning or features before MVP
   - **<25%:** Weak signal — revisit value proposition, consider pivot
5. If below 40%, segment responses: which customer type is most disappointed? Focus MVP on that segment.
6. Save to `[project]/docs/founder/market_validation/sean_ellis_pmf.md`

**Output:** PMF score with segmented analysis and recommendation

**Framework Reference:** Sean Ellis PMF Survey

---

## Step 8: Synthesize and Decide

**Inputs:** All M5 framework outputs

**Action:**
1. Create synthesis table mapping every M2 assumption to M5 evidence:
   - Assumption | Evidence Source | Status (Validated/Refuted/Uncertain) | Confidence
2. Evaluate persevere/pivot/kill criteria:
   - **Persevere:** Core value and growth assumptions validated, PMF signal ≥ 25%, viable pricing, channel identified
   - **Pivot:** Some assumptions refuted but viable alternative identified (different segment, different problem, different solution)
   - **Kill:** Critical assumptions refuted, no viable pivot, PMF signal < 15%
3. Make explicit recommendation with rationale
4. Update project memo:
   - Market Validation section with completed frameworks and key insights
   - Open Questions updated with unresolved items
   - Next Steps updated based on decision
5. Update m5_founder_diary.md with final Session Status and key decisions
6. Log persevere/pivot/kill decision to diary

**Output:** Decision document, updated project memo and diary

**Framework Reference:** None (synthesis)

---

## Success Criteria

Market Validation milestone is complete when:

- [ ] 10-15 Mom Test interviews conducted with documented findings
- [ ] 10-15 SPIN conversations completed with assumption validation synthesis
- [ ] Smoke test launched with measurable conversion data (100+ visitors)
- [ ] Van Westendorp pricing research completed (30+ responses) with acceptable price range identified, competitive pricing benchmarks with inline citations, and sources legend table
- [ ] Bullseye channel prioritization completed with top channels tested, industry CAC benchmarks with inline citations, and sources legend table
- [ ] Sean Ellis PMF survey administered (30+ responses) with PMF score calculated
- [ ] Synthesis table maps all M2 assumptions to M5 evidence with validation status
- [ ] Explicit persevere/pivot/kill decision documented with rationale
- [ ] All competitive pricing and channel benchmark claims have verified web sources (no training-data hallucinations)
- [ ] Project memo Progress > Market Validation section updated
- [ ] M5 founder diary has key decisions and validation findings logged

---

## Next Milestone

Once Market Validation is complete and the decision is to persevere, proceed to M6: MVP (mvp_process.md) to build a minimum viable product usable by real customers.

---

