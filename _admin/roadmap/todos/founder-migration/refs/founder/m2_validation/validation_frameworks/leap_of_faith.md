---
---

# Leap of Faith

**Purpose:** Task-based guide for harvesting, classifying, and prioritising assumptions from M1 Conception into Value and Growth Hypotheses, then defining observable validation signals, kill criteria, and a wired validation backlog for M2 Validation.

**Context:**
Use in M2 Validation, Step 2. MUST complete all M1 Conception frameworks (Working Backwards, JTBD, Problem-Solution Fit, Lean Canvas, 5 Whys) first. Read `validation_process.md` before starting.

---

## Framework Overview

Every new product rests on a stack of untested beliefs. Most founders know this, but they treat assumptions as a diffuse cloud rather than an explicit, ranked inventory. Leap of Faith forces you to surface every assumption hiding inside your M1 artefacts, classify each one as either a **Value Hypothesis** (customers experience this pain and will use our solution to make progress) or a **Growth Hypothesis** (the business can acquire, activate, retain, and monetise customers profitably), and then rank them by **impact x uncertainty** so you work on the ones that matter most and know the least about.

The output is not a plan to be right. It is a plan to **learn fast and fail cheaply**. For each high-priority assumption you define concrete, observable signals that would validate or invalidate it, establish explicit kill criteria that tell you when to stop or pivot, and wire everything into specific downstream validation activities across M2 (Assumption Mapping, TAM/SAM/SOM, Unit Economics, Pre-mortem) and M5 (SPIN Selling, Smoke Tests, PMF surveys, pricing experiments).

Treat the Leap of Faith analysis as a **living document**. Every time a downstream experiment produces evidence, return here to update confidence levels, re-rank assumptions, and retire validated beliefs. If you are not uncomfortable with at least three of your top assumptions, you have not been honest enough.

---

## Task Structure

| Task | Goal | Key Inputs | Key Outputs |
|------|------|------------|-------------|
| 1. Harvest Assumptions From M1 Artefacts | Extract all tagged and implicit assumptions from Working Backwards, JTBD, Problem-Solution Fit, Lean Canvas, 5 Whys | M1 applied frameworks, tagged assumption lists, Internal FAQ | Consolidated Assumption Inventory with source traceability |
| 2. Classify Into Value And Growth Hypotheses | Sort each assumption into Value Hypothesis or Growth Hypothesis and tag its category | Consolidated Assumption Inventory | Classified Assumption Register (Value vs Growth, with sub-categories) |
| 3. Prioritize By Impact And Uncertainty | Score each assumption on impact and uncertainty, identify the true leap-of-faith assumptions | Classified Assumption Register, founder judgement, any available data | Impact x Uncertainty Matrix, ranked assumption list, top 5-10 leap-of-faith assumptions |
| 4. Define Observable Validation Signals | For each high-priority assumption, define what evidence would validate or invalidate it | Ranked assumption list, M2/M5 process docs | Validation Signal Spec per assumption (metric, threshold, method, timeline) |
| 5. Establish Kill Criteria And Decision Rules | Define what would make you stop, pivot, or persevere for the venture as a whole | Top leap-of-faith assumptions, Validation Signal Specs, founder risk tolerance | Kill/Pivot/Persevere Decision Framework with explicit thresholds |
| 6. Create Validation Backlog And Connect To M2/M5 | Wire assumptions into specific validation activities and downstream frameworks | Full Leap of Faith analysis, M2/M5 process docs and frameworks | Validation Backlog, updated M2 founder diary, seeds for downstream frameworks |

---

## Task 1: Harvest Assumptions From M1 Artefacts

**Goal:** Produce a single, comprehensive inventory of every assumption embedded in M1 Conception artefacts, whether explicitly tagged or implicitly embedded in narratives and models.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Working Backwards PR/FAQ (Press Release + External/Internal FAQs) | M1 applied framework | Yes |
| JTBD analysis (job stories, forces, job map, priorities) | M1 applied framework | Yes |
| Problem-Solution Fit Canvas (all blocks, especially Critical Assumptions) | M1 applied framework | Yes |
| Lean Canvas (all nine blocks + tagged Assumptions List) | M1 applied framework | Yes |
| 5 Whys analysis (Root Cause Map, Targeted Root Cause Hypotheses) | M1 applied framework | Yes |
| M1 founder diary | `projects/[project]/founder/conception/m1_founder_diary.md` | Yes |

**Action:**

1. Open each M1 artefact in turn and extract **explicitly tagged assumptions**:
   - Lean Canvas Assumptions List (labelled P1, CS2, UVP1, CH1, REV2, COST1, MET1, UA1, etc.).
   - Problem-Solution Fit Critical Assumptions block.
   - Working Backwards Internal FAQ answers marked as assumptions.
   - 5 Whys chain links labelled "Hypothesis" and Targeted Root Cause Hypotheses.
2. Re-read each M1 artefact looking for **implicit assumptions** that were never explicitly tagged:
   - Working Backwards Press Release: claims about customer behaviour, adoption triggers, willingness to switch, and competitive positioning.
   - Working Backwards External FAQ: answers that assert customer preferences or market conditions without evidence.
   - JTBD: assumed frequency of the job situation, assumed forces (push, pull, anxieties, habits), assumed relative importance of functional vs emotional vs social jobs.
   - Problem-Solution Fit: assumed behaviours, assumed constraints, assumed mechanism by which the solution replaces current workarounds.
   - Lean Canvas: assumed channel effectiveness, assumed pricing acceptance, assumed cost structure, assumed metric targets.
   - 5 Whys: any "Fact" labels that rest on founder intuition rather than hard data.
3. For each assumption (explicit or implicit), capture in a table:
   - **ID** (sequential, e.g., LOF-001).
   - **Statement** ("We assume that...").
   - **Source artefact and block** (e.g., "Lean Canvas > Revenue Streams > REV1").
   - **Category**: behavioural, technical, or economic.
   - **Current evidence**: what you know today (data, quotes, observations, or "founder intuition only").
4. Scan the **M1 founder diary** for decisions and pivots that rest on unstated beliefs. Add any new assumptions found.
5. Remove duplicates. When multiple artefacts contain the same assumption with different wording, merge them and note all source references.
6. Produce a **Consolidated Assumption Inventory** as a single table or document section.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Consolidated Assumption Inventory | Table with columns: ID, Statement, Source, Category, Current Evidence | Single source of truth for every belief underlying the M1 concept |

**Validation:**

- [ ] You have reviewed **all five M1 frameworks** plus the founder diary, not just the ones with explicit assumption tags.
- [ ] You have at least **15-30 distinct assumptions** (fewer suggests you have not been thorough; more than 50 suggests you need to merge duplicates).
- [ ] Every assumption is traceable to a **specific artefact and block**.
- [ ] At least one-third of the assumptions came from **implicit extraction** (not already tagged in M1).
- [ ] A neutral reader can understand each assumption statement without seeing the source artefact.

---

## Task 2: Classify Into Value And Growth Hypotheses

**Goal:** Sort every assumption into one of two fundamental categories and tag its sub-category so that validation activities can be designed with the right lens.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Consolidated Assumption Inventory | Task 1 | Yes |
| JTBD primary job stories and forces | M1 applied framework | Yes |
| Lean Canvas (Problem, Customer Segments, Channels, Revenue Streams, Key Metrics) | M1 applied framework | Yes |

**Action:**

1. Define the two hypothesis types for your team:
   - **Value Hypothesis:** An assumption that, if true, means customers experience the stated pain, will hire your solution to make progress, and will derive enough value to keep using it. Covers problem existence, problem severity, solution fit, usability, switching willingness, and retention.
   - **Growth Hypothesis:** An assumption that, if true, means the business can acquire, activate, and retain customers at a cost and rate that sustains the venture. Covers channels, acquisition cost, conversion rates, pricing acceptance, revenue per customer, viral or referral mechanics, and market size.
2. For each assumption in the Inventory, assign:
   - **Primary classification**: Value or Growth.
   - **Sub-category** within Value: Problem Existence, Problem Severity, Solution Fit, Willingness to Switch, Retention and Habit Formation.
   - **Sub-category** within Growth: Channel Effectiveness, Acquisition Cost, Conversion Rate, Pricing and Willingness to Pay, Revenue Model, Retention Economics, Referral and Virality, Market Size.
3. Handle **boundary cases** explicitly:
   - Assumptions about willingness to pay sit at the intersection. Classify as Growth if the question is "will they pay this price?" and as Value if the question is "is the value large enough that any price is plausible?"
   - Assumptions about retention: classify as Value if the question is "does the product deliver ongoing value?" and as Growth if the question is "does our pricing and engagement model sustain renewals?"
   - When in doubt, duplicate the assumption under both classifications and note the different angles.
4. Create a **Classified Assumption Register** by reorganising the Inventory into two major sections (Value, Growth), each with sub-category groupings.
5. For each sub-category, write a one-sentence **summary hypothesis** that captures the collective belief, e.g., "We believe that product managers at B2B SaaS companies (50-200 employees) experience painful, manual end-of-month reporting at least monthly (LOF-003, LOF-007, LOF-012)."

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Classified Assumption Register | Structured document with Value and Growth sections, sub-categories, and summary hypotheses | Enables targeted validation: Value assumptions need customer evidence, Growth assumptions need market and economic evidence |

**Validation:**

- [ ] Every assumption from the Inventory is classified; **none are left unassigned**.
- [ ] You have assumptions in **both** Value and Growth categories (if all assumptions are Value, you have not examined your business model; if all are Growth, you have not examined customer-problem fit).
- [ ] Each sub-category contains at least one assumption; **empty sub-categories** are explicitly noted as either "not applicable" or "gap to investigate."
- [ ] Summary hypotheses are specific enough that a stranger could design a test without reading the underlying artefacts.
- [ ] Boundary cases are documented with reasoning, not silently shoved into one category.

---

## Task 3: Prioritize By Impact And Uncertainty

**Goal:** Rank assumptions so you invest validation effort where it matters most: high impact if wrong, high uncertainty about whether it is true.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Classified Assumption Register | Task 2 | Yes |
| Founder and team judgement | Discussion, prior experience | Yes |
| Any available quantitative or qualitative evidence | Analytics, interviews, market data | No but strongly recommended |

**Action:**

1. Define the two scoring dimensions:
   - **Impact** (1-5): If this assumption is wrong, how severely does it damage the venture? 5 = concept collapses entirely; 1 = minor inconvenience, easily adapted.
   - **Uncertainty** (1-5): How confident are you that this assumption is true today? 5 = pure speculation, no evidence; 1 = well-established fact with multiple data points.
2. Score each assumption in the Register on both dimensions. Use these calibration anchors:
   - Impact 5: "If wrong, we have no viable business." (e.g., the problem does not exist, or the market is too small to sustain any business.)
   - Impact 3: "If wrong, we must significantly redesign our solution or business model but could still find a path."
   - Impact 1: "If wrong, we adjust a parameter and continue."
   - Uncertainty 5: "We have zero evidence; this is founder intuition or hope."
   - Uncertainty 3: "We have indirect or analogical evidence but nothing specific to our segment and context."
   - Uncertainty 1: "We have direct, specific evidence from our target customers or market."
3. Compute a **Priority Score** = Impact x Uncertainty for each assumption.
4. Plot assumptions on a **2x2 Impact x Uncertainty Matrix**:
   - **Top-right (High Impact, High Uncertainty):** These are your **leap-of-faith assumptions**. Validate first.
   - **Top-left (High Impact, Low Uncertainty):** Monitor but accept for now; revisit if new evidence weakens confidence.
   - **Bottom-right (Low Impact, High Uncertainty):** Park; learn incidentally during other validation work.
   - **Bottom-left (Low Impact, Low Uncertainty):** Accept and move on.
5. Select the **top 5-10 assumptions** by Priority Score. These are the true leap-of-faith assumptions that will drive your validation agenda.
6. For each top assumption, write a concise **Leap-of-Faith Statement**:
   - "We are betting that **[specific belief]** because **[reason/intuition]**, but we have **[level of evidence]** and if wrong, **[specific consequence]**."
7. Review the ranked list with at least one other person (co-founder, advisor, domain expert) and challenge the scores. Adjust if challenged scores reveal bias (founders systematically underrate uncertainty on their favourite assumptions).

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Impact x Uncertainty Matrix | 2x2 grid with assumptions plotted by quadrant | Visual overview of where risk concentrates |
| Ranked Assumption List | Table sorted by Priority Score descending | Drives the order of validation activities |
| Top 5-10 Leap-of-Faith Statements | Short narrative per assumption | Forces explicit articulation of the biggest bets and their consequences |

**Validation:**

- [ ] Every assumption in the Register has been scored; **no assumptions were skipped**.
- [ ] At least **two people** have reviewed and challenged the scores (or, for solo founders, you have explicitly role-played a sceptic and documented the challenge).
- [ ] The top 5-10 include assumptions from **both** Value and Growth categories.
- [ ] At least one assumption makes you **uncomfortable to read aloud**; if none do, you have scored too generously on uncertainty.
- [ ] Priority Scores produce a clear separation between the top tier and the rest; if everything clusters at the same score, refine your calibration.

---

## Task 4: Define Observable Validation Signals

**Goal:** For each high-priority assumption, specify exactly what evidence would validate it, what evidence would invalidate it, and how you will collect that evidence.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Top 5-10 Leap-of-Faith Statements | Task 3 | Yes |
| M2 Validation process doc | `validation_process.md` | Yes |
| M5 Market Validation process doc (if available) | `market_validation_process.md` | No but recommended |
| Available data sources and research methods | Team capabilities, budget, timeline | Yes |

**Action:**

1. For each top assumption, create a **Validation Signal Spec** with these fields:
   - **Assumption ID and Statement** (from Task 3).
   - **Validation Signal**: What observable, measurable outcome would increase your confidence that this assumption is true? Be specific: name a metric, a behaviour, a quote pattern, or a data point.
   - **Invalidation Signal**: What observable outcome would decrease your confidence or prove the assumption false? This must be equally specific.
   - **Signal Threshold**: What quantity or quality of evidence is "enough"? Define a minimum bar (e.g., "At least 7 out of 10 interviewed customers independently describe this pain without prompting" or "Smoke test landing page converts above 5% of targeted traffic").
   - **Collection Method**: How will you gather this signal? Name a specific method: customer interviews (JTBD or SPIN), surveys, smoke tests, landing page experiments, desk research, financial modelling, expert consultation, prototype testing.
   - **Timeline**: By when must you have this signal? Tie to your M2/M5 schedule.
   - **Owner**: Who is responsible for collecting and interpreting this signal?
2. Ensure that validation and invalidation signals are **asymmetric and honest**:
   - The invalidation signal must be something you could actually observe, not a condition you have defined to be practically impossible.
   - Avoid confirmation bias: define invalidation signals before validation signals for each assumption.
3. Cross-reference signals against **available M2 and M5 frameworks**:
   - TAM/SAM/SOM can validate market size assumptions.
   - Unit Economics can validate pricing, LTV, CAC, and payback assumptions.
   - SPIN Selling interviews can validate problem existence, severity, and willingness to change.
   - Smoke Tests can validate demand, channel effectiveness, and conversion assumptions.
   - Pre-mortem can surface failure modes related to growth assumptions.
4. For assumptions where no clean signal exists, document this gap explicitly and propose a **proxy signal** with a note on why it is imperfect.
5. Compile all Validation Signal Specs into a single section or table in the Leap of Faith document.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Validation Signal Specs | Table or structured list per assumption: Signal, Threshold, Method, Timeline, Owner | Turns abstract assumptions into concrete, testable propositions with clear pass/fail criteria |

**Validation:**

- [ ] Every top assumption has **both** a validation signal and an invalidation signal defined.
- [ ] Signal thresholds are **specific and measurable**, not vague ("customers like it" is not a threshold; "7/10 unprompted mentions" is).
- [ ] Each collection method maps to a **real capability** you have or can acquire within the M2/M5 timeline.
- [ ] Invalidation signals are **genuinely reachable**; you have not defined them as logically impossible outcomes.
- [ ] At least one signal is designed to return results within **two weeks** of starting validation.

---

## Task 5: Establish Kill Criteria And Decision Rules

**Goal:** Define in advance what evidence would make you stop the venture, pivot the concept, or persevere with increased confidence, so that sunk-cost bias cannot override data.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Top 5-10 Leap-of-Faith Statements | Task 3 | Yes |
| Validation Signal Specs | Task 4 | Yes |
| Founder risk tolerance and resource constraints | Founder/team discussion | Yes |
| Working Backwards Internal FAQ ("Is it worth doing?" answer) | M1 applied framework | Yes |

**Action:**

1. Define **three decision outcomes** and what triggers each:
   - **Kill:** Stop the venture entirely. What combination of invalidated assumptions would lead here? Be explicit. Example: "If the primary job does not exist for at least 3 of 10 interviewed early adopters AND the addressable market is below EUR 50M, we kill."
   - **Pivot:** Change a fundamental element of the concept (customer segment, problem, solution mechanism, business model, channel). What evidence triggers a pivot vs a kill? Example: "If the problem exists but our solution mechanism is wrong, we pivot to a different approach. If the problem does not exist, we kill."
   - **Persevere:** Continue with the current concept into M4/M5. What minimum evidence is required? Example: "At least 7/10 value signals validated AND unit economics model shows plausible path to LTV:CAC > 3."
2. For each top assumption, assign a **decision rule**:
   - If validated (signal threshold met): mark as "Accepted (pending further evidence)" and reduce validation priority.
   - If invalidated (invalidation signal threshold met): trigger the pre-defined response (kill, pivot, or investigate further).
   - If inconclusive (neither threshold met): define what additional evidence to seek and by when.
3. Define **aggregate kill criteria** that consider the portfolio of assumptions:
   - How many Value Hypothesis assumptions can be invalidated before the venture is not worth pursuing?
   - How many Growth Hypothesis assumptions can be invalidated before the business model must change?
   - What is the maximum time and money you will invest in validation before requiring a go/no-go decision?
4. Write a **Decision Review Schedule**:
   - When will you formally review accumulated evidence against kill criteria? (e.g., after completing each M2 framework, at end of M2, at end of M5.)
   - Who participates in the review?
   - What is the decision-making protocol? (e.g., founder decides, but must address all dissenting views in writing.)
5. Record the kill criteria and decision rules in the Leap of Faith document and cross-reference them in the M2 founder diary.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Kill/Pivot/Persevere Decision Framework | Structured section with per-assumption rules and aggregate thresholds | Pre-commits you to rational responses to evidence, defeating sunk-cost bias |
| Decision Review Schedule | Short calendar with dates, participants, and protocol | Ensures evidence is formally reviewed, not ignored |

**Validation:**

- [ ] There is an **explicit kill condition** that is reachable, not defined to be practically impossible.
- [ ] There is an **explicit pivot trigger** that distinguishes "wrong solution" from "wrong problem."
- [ ] The persevere condition requires **positive evidence**, not just absence of negative evidence.
- [ ] Aggregate criteria address the **portfolio** of assumptions, not just individual ones in isolation.
- [ ] At least one other person (co-founder, advisor) has reviewed the kill criteria and confirmed they are honest, not performative.

---

## Task 6: Create Validation Backlog And Connect To M2/M5

**Goal:** Wire every high-priority assumption into a specific downstream validation activity so that nothing falls through the cracks, and the entire M2 and M5 validation agenda is assumption-driven.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Ranked Assumption List and Leap-of-Faith Statements | Task 3 | Yes |
| Validation Signal Specs | Task 4 | Yes |
| Kill/Pivot/Persevere Decision Framework | Task 5 | Yes |
| M2 Validation process doc | `validation_process.md` | Yes |
| M5 Market Validation process doc (if available) | `market_validation_process.md` | No but recommended |
| M2/M5 framework references (Assumption Mapping, TAM/SAM/SOM, Unit Economics, Pre-mortem, SPIN Selling, Smoke Test) | Respective framework docs | No but strongly recommended |

**Action:**

1. Create a **Validation Backlog** table with columns:
   - Assumption ID and short statement.
   - Priority Score (from Task 3).
   - Assigned M2/M5 framework or activity.
   - Specific task or experiment within that framework.
   - Expected output and timeline.
   - Status (Not Started, In Progress, Validated, Invalidated, Inconclusive).
2. Map assumptions to downstream frameworks:
   - **Assumption Mapping (M2):** All assumptions flow here for visual plotting and test-or-accept triage. The Leap of Faith Classified Register is the primary input.
   - **TAM/SAM/SOM (M2):** Market size assumptions (Growth sub-categories: Market Size, Channel Effectiveness).
   - **Unit Economics (M2):** Pricing, LTV, CAC, retention economics, and cost structure assumptions (Growth sub-categories: Pricing and Willingness to Pay, Revenue Model, Retention Economics, Acquisition Cost).
   - **Pre-mortem (M2):** Top leap-of-faith assumptions become explicit failure mode candidates. Kill criteria feed directly into pre-mortem mitigation planning.
   - **SPIN Selling (M5):** Problem existence, severity, and willingness-to-switch assumptions (Value sub-categories: Problem Existence, Problem Severity, Solution Fit, Willingness to Switch).
   - **Smoke Test (M5):** Demand, channel, conversion, and early adoption assumptions (Growth sub-categories: Channel Effectiveness, Conversion Rate; Value sub-categories: Solution Fit).
3. For each mapping, write a **one-sentence handoff note** explaining what the downstream framework should test and what signal to return, e.g., "TAM/SAM/SOM must validate LOF-004 (addressable market > EUR 100M for segment X) using both top-down and bottom-up methods; return estimate with confidence range."
4. Identify **gaps**: assumptions that do not map cleanly to any existing M2/M5 framework. For each gap:
   - Define a lightweight ad-hoc validation activity (desk research, expert interview, proxy data analysis).
   - Assign an owner and timeline.
5. Update the **M2 founder diary** with:
   - The creation of the Leap of Faith analysis and its key outputs.
   - The top 5 leap-of-faith assumptions and their assigned validation paths.
   - The kill criteria and decision review schedule.
6. Ensure the **project memo** Progress > Validation section references the Leap of Faith analysis and lists the top assumptions being tested.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Validation Backlog | Table mapping assumptions to frameworks, experiments, timelines, and statuses | Operational backbone of M2/M5 validation; ensures every critical assumption has a plan |
| Updated M2 founder diary | Diary entries | Captures the Leap of Faith analysis and its implications for the validation agenda |
| Handoff notes to downstream frameworks | One-sentence directives per mapping | Ensures downstream frameworks know exactly which assumptions to test and what to return |

**Validation:**

- [ ] Every top 5-10 assumption has at least one **assigned validation activity** with an owner and timeline.
- [ ] At least one assumption maps to each of: **Assumption Mapping, TAM/SAM/SOM, Unit Economics, and Pre-mortem** in M2.
- [ ] At least one assumption maps to a **customer-facing validation** method (SPIN Selling, Smoke Test, or equivalent) in M5.
- [ ] Gaps are documented with **ad-hoc plans**, not left as "TBD."
- [ ] The M2 founder diary contains a dated entry summarising the Leap of Faith analysis, top assumptions, and kill criteria.

---

## Pitfalls

**Harvesting Only Explicit Assumptions**

The most dangerous assumptions are the ones nobody wrote down. Spend at least as much time on implicit extraction (re-reading M1 artefacts with a sceptic's eye) as on collecting tagged assumptions. If your Inventory has fewer than 15 assumptions, you have not looked hard enough.

**Conflating Value And Growth**

A product that solves a real problem but cannot be sold profitably will fail just as surely as one that solves a non-existent problem. Force yourself to populate both categories. If your entire list is Value Hypotheses, you have ignored the business model. If it is all Growth, you have assumed away customer-problem fit.

**Scoring Impact And Uncertainty To Avoid Discomfort**

Founders systematically underrate uncertainty on assumptions they care about most. Before scoring, write down the assumption you are most emotionally attached to, then deliberately score its uncertainty one point higher than your gut says. Have a sceptical co-founder or advisor challenge every score of 1 or 2 on uncertainty.

**Defining Unfalsifiable Kill Criteria**

Kill criteria that can never be triggered are not criteria; they are theatre. If your kill condition requires "zero customers show any interest," you have not written a real kill condition. Define thresholds you could actually hit within your validation timeline and budget.

**Treating The Backlog As A Static Document**

The Validation Backlog must be updated every time a downstream framework produces results. After each M2 or M5 activity, return to this document, update the Status column, revise confidence levels, and re-rank if necessary. A stale backlog is worse than no backlog because it gives false confidence.

**Skipping Kill Criteria Entirely**

Many founders complete tasks 1-4 enthusiastically but skip Task 5 because it forces them to contemplate failure. Task 5 is the most important task in this framework. Without pre-committed kill criteria, you will rationalise every piece of negative evidence and waste months on a dead concept.

---

## Integration

**Prerequisites:**
Read `validation_process.md`. MUST complete all M1 Conception frameworks: Working Backwards, JTBD, Problem-Solution Fit, Lean Canvas, 5 Whys.

**Builds on:**

| Framework | Output Used | How Used |
|-----------|-------------|----------|
| Working Backwards (PR/FAQ) | Internal FAQ assumptions, claims in Press Release, External FAQ gaps | Provides explicitly tagged assumptions from feasibility/economics review, plus implicit claims about customer behaviour and competitive positioning |
| Jobs-To-Be-Done | Job hypotheses, assumed forces (push, pull, anxieties, habits), assumed frequency and severity | Supplies Value Hypothesis assumptions about whether the job exists, how important it is, and what forces govern switching behaviour |
| Problem-Solution Fit Canvas | Critical Assumptions block, assumed behaviours, constraints, solution mechanism | Provides the most concentrated set of problem-solution level assumptions, especially about willingness to switch and constraint compatibility |
| Lean Canvas | Tagged assumptions per block (P1, CS2, UVP1, CH1, REV2, COST1, MET1, UA1) | Supplies structured, per-block business model assumptions spanning both Value and Growth categories |
| 5 Whys | Targeted Root Cause Hypotheses, chain links tagged as Hypothesis | Provides assumptions about why the problem exists structurally and which root causes the solution must address |

**Feeds into:**

| Framework | Output Provided | How Used |
|-----------|-----------------|----------|
| Assumption Mapping (M2) | Classified Assumption Register, Impact x Uncertainty scores | Primary input; Assumption Mapping plots these on its own matrix and designs test-or-accept decisions |
| TAM/SAM/SOM (M2) | Market size and segment assumptions with validation signals | Directs which market sizing questions to prioritise and what thresholds to apply |
| Unit Economics (M2) | Pricing, LTV, CAC, retention, and cost assumptions with validation signals | Seeds the economic model with explicit hypotheses and defines what ranges are acceptable |
| Pre-mortem (M2) | Top leap-of-faith assumptions, kill criteria | Failure modes in the pre-mortem should map directly to the highest-priority assumptions |
| SPIN Selling (M5) | Value Hypothesis assumptions about problem existence, severity, and willingness to change | Drives the design of situation, problem, implication, and need-payoff questions in customer interviews |
| Smoke Test (M5) | Growth Hypothesis assumptions about demand, channels, conversion, and early adoption | Determines which smoke test designs to run, what to measure, and what thresholds to set |

**Workflow Position:**

Leap of Faith is the first analytical framework in M2 Validation. It processes the raw assumptions from M1 Conception into a structured, prioritised validation agenda that drives every subsequent M2 and M5 activity.

---

## Success Criteria

- [ ] A **Consolidated Assumption Inventory** exists with at least 15-30 distinct, traceable assumptions harvested from all five M1 frameworks.
- [ ] Every assumption is classified as **Value Hypothesis or Growth Hypothesis** with a sub-category.
- [ ] An **Impact x Uncertainty Matrix** exists with assumptions scored and plotted.
- [ ] The **top 5-10 leap-of-faith assumptions** are identified with explicit Leap-of-Faith Statements.
- [ ] Each top assumption has a **Validation Signal Spec** with observable validation and invalidation signals, thresholds, methods, timelines, and owners.
- [ ] **Kill, pivot, and persevere criteria** are defined with specific, reachable thresholds and a Decision Review Schedule.
- [ ] A **Validation Backlog** maps every top assumption to a specific M2 or M5 framework or ad-hoc activity.
- [ ] The **M2 founder diary** contains at least one entry documenting the Leap of Faith analysis and its key outputs.
- [ ] The **project memo** Progress > Validation section references the Leap of Faith analysis.

---

## References

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS >= 6

Sources consulted when designing this framework:

- [1] Eric Ries, *The Lean Startup: How Today's Entrepreneurs Use Continuous Innovation to Create Radically Successful Businesses* (Crown Business, 2011) — Research Date: 2025-12-21 — Source Date: 2011 — TS: 9.3 (AT: 10, TR: 9, TM: 9)
- [2] Steve Blank, *The Four Steps to the Epiphany: Successful Strategies for Products that Win* (K&S Ranch, 2005) — Research Date: 2025-12-21 — Source Date: 2005 — TS: 9.0 (AT: 10, TR: 9, TM: 8)
- [3] Lean Startup Methodology — `https://en.wikipedia.org/wiki/Lean_startup` — Research Date: 2025-12-21 — Source Date: n/a — TS: 8.0 (AT: 7, TR: 8, TM: 9)
- [4] Ash Maurya, *Running Lean: Iterate from Plan A to a Plan That Works* (O'Reilly, 2012) — Research Date: 2025-12-21 — Source Date: 2012 — TS: 8.3 (AT: 8, TR: 8, TM: 9)
- [5] Leap of Faith Assumptions — `https://www.productplan.com/glossary/leap-of-faith-assumption/` — Research Date: 2025-12-21 — Source Date: n/a — TS: 6.7 (AT: 6, TR: 7, TM: 7; AT penalised -1 for glossary format)

Additional conceptual references (books, not scored):

- David J. Bland & Alexander Osterwalder, *Testing Business Ideas* (Wiley, 2020).
- Alberto Savoia, *The Right It: Why So Many Ideas Fail and How to Make Sure Yours Succeed* (HarperOne, 2019).

---

## For AI Agents

**Execution Context:**

1. Read `validation_process.md` and confirm all M1 Conception frameworks exist before starting. If any M1 framework is missing, MUST flag and help user create a minimal version first.
2. Track progress: "Currently in Task [N]: [Task Name]".
3. When harvesting assumptions (Task 1), systematically open each M1 artefact and extract both explicit and implicit assumptions. Do not rely only on tagged items.
4. When scoring Impact and Uncertainty (Task 3), push the user to justify scores and challenge any assumption scored below 3 on uncertainty if there is no direct evidence from target customers.
5. When defining kill criteria (Task 5), ensure the user commits to at least one reachable kill condition. Do not accept "we would kill if nobody in the world wanted this" as a real criterion.
6. Record key decisions and outputs in the M2 founder diary as they emerge.

**Working With Tasks:**

- Complete each task atomically. NEVER skip Task 5 (Kill Criteria).
- When the user resists defining invalidation signals or kill criteria, name the resistance explicitly and explain sunk-cost bias.
- When downstream M2/M5 activities produce results, prompt the user to return to this document and update assumption statuses, confidence levels, and rankings.
- Treat the Leap of Faith analysis as a living artefact; suggest re-ranking whenever major new evidence arrives.

---

