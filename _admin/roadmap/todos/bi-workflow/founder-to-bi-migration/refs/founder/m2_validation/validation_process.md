---
---

# Validation Process

**Purpose:** Detailed process guide for Milestone 2 (Validation) of the founder module. Stress-tests the assumptions, feasibility, and financial viability of the business concept produced in M1 Conception before committing resources to brand, prototype, or market validation.

**Goal:** Validate that the business concept is technically feasible, financially viable, and worth pursuing — or identify specific pivots, de-risking actions, or kill signals before investing further.

---

## Inputs

| Input | Source |
|-------|--------|
| Project memo (populated through M1) | `projects/[project]/founder/[project]_memo.md` |
| M1 applied frameworks (Working Backwards, JTBD, Problem-Solution Fit, Lean Canvas, 5 Whys) | `projects/[project]/founder/conception/` |
| M1 founder diary | `projects/[project]/founder/conception/m1_founder_diary.md` |
| Tagged assumptions from M1 frameworks | Lean Canvas assumptions list, Problem-Solution Fit critical assumptions, Internal FAQ |

---

## Outputs

| Output | Format |
|--------|--------|
| Leap of Faith analysis | Markdown document (applied framework in `projects/[project]/founder/validation/`) |
| Assumption Mapping | Markdown document (applied framework) |
| TAM/SAM/SOM analysis | Markdown document (applied framework) with inline citations and sources legend table |
| Unit Economics model | Markdown document (applied framework) with inline citations and sources legend table |
| Pre-mortem analysis | Markdown document (applied framework) |
| Technology Readiness assessment | Markdown document (applied framework) |
| Updated project memo (Validation progress) | Updated `[project]_memo.md` |
| M2 founder diary | Markdown table (`projects/[project]/founder/validation/m2_founder_diary.md`) |

---

## Steps Summary

| Step | Action | Framework | Output |
|------|--------|-----------|--------|
| 1 | Initialize validation folder and collect M1 assumptions | — | Validation folder, consolidated assumption inventory |
| 2 | Identify and prioritize leap-of-faith assumptions | Leap of Faith | Prioritized assumption list with value/growth hypothesis classification |
| 3 | Map assumptions by risk and uncertainty | Assumption Mapping | Visual assumption map with test-or-accept decisions |
| 4 | Size the market opportunity **[WEB RESEARCH MANDATORY]** | TAM/SAM/SOM | Market sizing document with segment-level estimates |
| 5 | Model unit economics and financial viability **[WEB RESEARCH MANDATORY]** | Unit Economics | Unit economics model with LTV, CAC, payback, break-even |
| 6 | Assess technical readiness | Technology Readiness Level | TRL assessment with de-risking plan |
| 7 | Run pre-mortem to surface hidden risks | Pre-mortem | Pre-mortem analysis with mitigation actions |
| 8 | Synthesize validation findings into project memo | — | Updated project memo (Progress > Validation, Open Questions, Next Steps) |
| 9 | Document key decisions, pivots, and assumptions | — | Updated M2 founder diary |

---

## Step 1: Initialize Validation and Collect Assumptions

**Inputs:** M1 applied frameworks, M1 founder diary, project memo

**Action:**
1. Create validation folder: `projects/[project]/founder/validation/`
2. Initialize M2 founder diary from the template: [founder_diary.md](../templates/founder_diary.md)
3. Consolidate all tagged assumptions from M1 into a single inventory:
   - Lean Canvas assumptions list (tagged P1, CS2, UVP1, etc.)
   - Problem-Solution Fit critical assumptions
   - Working Backwards Internal FAQ assumptions
   - 5 Whys targeted root cause hypotheses
4. For each assumption, note: source framework, category (behavioural/technical/economic), and initial confidence level
5. Update M2 founder diary Status section to reflect M2 start

**Output:** Validation folder with diary, consolidated assumption inventory

**Framework Reference:** None (structural setup)

---

## Step 2: Identify Leap-of-Faith Assumptions

**Inputs:** Consolidated assumption inventory from Step 1

**Action:**
1. Read Leap of Faith framework: [leap_of_faith.md](validation_frameworks/leap_of_faith.md)
2. Follow the framework tasks to:
   - Classify assumptions into Value Hypothesis (customers have this pain and will use our solution) and Growth Hypothesis (the business can acquire and retain customers profitably)
   - Identify which assumptions are truly "leap of faith" — if wrong, the entire concept fails
   - Prioritize by: impact if wrong × current uncertainty
   - Define observable signals that would validate or invalidate each assumption
   - Establish kill criteria: what evidence would make you stop

**Output:** Leap of Faith analysis document with prioritized assumptions and kill criteria

**Framework Reference:** [leap_of_faith.md](validation_frameworks/leap_of_faith.md)

---

## Step 3: Map Assumptions by Risk and Uncertainty

**Inputs:** Leap of Faith analysis

**Action:**
1. Read Assumption Mapping framework: [assumption_mapping.md](validation_frameworks/assumption_mapping.md)
2. Follow the framework tasks to:
   - Plot assumptions on an Importance × Uncertainty matrix
   - Decide for each: Test (high importance, high uncertainty), Accept (high importance, low uncertainty), Monitor (low importance, high uncertainty), Ignore (low importance, low uncertainty)
   - Design lightweight tests for "Test" assumptions
   - Define what evidence looks like for each test

**Output:** Assumption map with test-or-accept decisions and test designs

**Framework Reference:** [assumption_mapping.md](validation_frameworks/assumption_mapping.md)

---

## Step 4: Size the Market Opportunity

**Inputs:** Lean Canvas Customer Segments, Working Backwards customer definition, market observations

**Action:**
1. Read TAM/SAM/SOM framework: [tam_sam_som.md](validation_frameworks/tam_sam_som.md)
2. **Web research is MANDATORY for this step.** Read and follow [web-research/SKILL.md](../../../.cursor/skills/web-research/SKILL.md)
3. Follow the framework tasks to:
   - Calculate Total Addressable Market using both top-down and bottom-up methods
   - Define Serviceable Addressable Market based on your segment, geography, and go-to-market constraints
   - Estimate Serviceable Obtainable Market for year 1-3 based on realistic capture rates
   - Cross-reference with Lean Canvas Customer Segments and early adopter definitions
   - Document all data sources per web-research skill requirements

**Output:** TAM/SAM/SOM analysis with sourced estimates, methodology, and sources legend

**Framework Reference:** [tam_sam_som.md](validation_frameworks/tam_sam_som.md)

---

## Step 5: Model Unit Economics

**Inputs:** TAM/SAM/SOM analysis, Lean Canvas Revenue/Cost blocks, Working Backwards Internal FAQ economics

**Action:**
1. Read Unit Economics framework: [unit_economics.md](validation_frameworks/unit_economics.md)
2. **Web research is MANDATORY for this step.** Read and follow [web-research/SKILL.md](../../../.cursor/skills/web-research/SKILL.md)
3. Follow the framework tasks to:
   - Calculate Customer Lifetime Value (LTV) using revenue and retention assumptions
   - Estimate Customer Acquisition Cost (CAC) per channel using industry benchmarks
   - Benchmark LTV:CAC ratios for your industry/sector
   - Compute LTV:CAC ratio and payback period
   - Model break-even point (customer count and timeline)
   - Identify which assumptions most affect viability
   - Tag all figures as assumptions with ranges, not point estimates
   - Document all benchmark sources per web-research skill requirements

**Output:** Unit economics model with LTV, CAC, payback, break-even, sensitivity analysis, and sources legend

**Framework Reference:** [unit_economics.md](validation_frameworks/unit_economics.md)

---

## Step 6: Assess Technical Readiness

**Inputs:** Working Backwards Internal FAQ (technical questions), Problem-Solution Fit solution concept, any technical spike results

**Action:**
1. Read Technology Readiness Level framework: [technology_readiness_level.md](validation_frameworks/technology_readiness_level.md)
2. Follow the framework tasks to:
   - Assess current TRL (1-9) for each major technical component
   - Identify technical risks and unknowns
   - Define what must be proven technically before M4 prototypation
   - Design technical spikes or proof-of-concepts for high-risk areas
   - Estimate effort and timeline for de-risking

**Output:** TRL assessment with component-level ratings and de-risking plan

**Framework Reference:** [technology_readiness_level.md](validation_frameworks/technology_readiness_level.md)

---

## Step 7: Run Pre-mortem

**Inputs:** All M2 analyses (Leap of Faith, Assumption Mapping, TAM/SAM/SOM, Unit Economics, TRL)

**Action:**
1. Read Pre-mortem framework: [pre_mortem.md](validation_frameworks/pre_mortem.md)
2. Follow the framework tasks to:
   - Imagine the project has failed 12 months from now
   - Brainstorm all plausible reasons for failure across categories (market, product, team, financial, technical, competitive)
   - Rank failure modes by likelihood and severity
   - For each top failure mode, define a mitigation action or early warning signal
   - Cross-reference with Leap of Faith kill criteria

**Output:** Pre-mortem analysis with ranked failure modes and mitigation actions

**Framework Reference:** [pre_mortem.md](validation_frameworks/pre_mortem.md)

---

## Step 8: Synthesize into Project Memo

**Inputs:** All M2 framework documents from Steps 2-7

**Action:**
1. Update project memo Progress > Validation subsection with:
   - Narrative summary of validation findings
   - Completed frameworks with key insights and links
   - Key decisions made during validation
2. Update Open Questions with unresolved assumptions and risks
3. Update Next Steps with recommended actions for M3/M4/M5
4. Revise Problem and Solution sections if validation changed understanding

**Output:** Updated project memo with Validation progress

**Framework Reference:** Project Memo template ([project_memo.md](../templates/project_memo.md))

---

## Step 9: Document Key Decisions and Assumptions

**Inputs:** Insights from all M2 steps

**Action:**
1. Review all M2 framework documents for key decisions
2. Identify assumptions that were validated, invalidated, or remain uncertain
3. Note any pivots from M1 concept
4. Document in M2 founder diary with appropriate Type (Decision, Assumption Invalidated, Pivot, Learning)
5. Make explicit persevere/pivot/kill recommendation based on M2 evidence

**Output:** Updated M2 founder diary with validation decisions

**Framework Reference:** Founder Diary template ([founder_diary.md](../templates/founder_diary.md))

---

## Success Criteria

Validation milestone is complete when:

- [ ] Leap of Faith analysis exists with prioritized assumptions, value/growth hypothesis classification, and kill criteria
- [ ] Assumption map exists showing test-or-accept decisions for all M1 assumptions
- [ ] TAM/SAM/SOM analysis exists with sourced estimates using both top-down and bottom-up methods, inline citations, and sources legend table
- [ ] Unit economics model exists with LTV, CAC, payback period, break-even estimates, industry benchmarks with inline citations, and sources legend table
- [ ] TRL assessment exists with component-level ratings and de-risking plan for M4
- [ ] Pre-mortem analysis exists with ranked failure modes and mitigation actions
- [ ] Project memo Progress > Validation section is populated with key findings
- [ ] M2 founder diary exists with at least 3 entries documenting key validation decisions
- [ ] There is an explicit persevere/pivot/kill recommendation with supporting evidence
- [ ] All market facts and industry benchmarks have verified web sources (no training-data hallucinations)
- [ ] Founder can articulate: What must be true? What evidence supports it? What would change our mind?

---

## Next Milestone

Once Validation is complete, proceed to M3: Brand milestone ([brand_process.md](../m3_brand/brand_process.md)) to create a preliminary brand identity, or to M4: Prototypation if brand work is deferred.

---

