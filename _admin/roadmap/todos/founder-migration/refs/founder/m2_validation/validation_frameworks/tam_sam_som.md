---
---

# TAM/SAM/SOM (Market Sizing)

**Purpose:** Size the market opportunity using both top-down (industry reports, market data) and bottom-up (customer count x ARPU) methods to produce grounded, stress-tested estimates that inform investment decisions, unit economics, and go-to-market planning.

**Context:** Use in M2 Validation, Step 4. MUST complete Leap of Faith and Assumption Mapping first. Use Lean Canvas Customer Segments, Revenue Streams, and Channels blocks as inputs. Use Working Backwards customer definitions and JTBD segment selection to anchor market boundaries.

---

## Framework Overview

Market sizing is not a pitch exercise. It is a discipline for quantifying how many people have the problem you solve, how many you can realistically reach, and how many you can capture given your resources and competitive position. Every number is a hypothesis. Treat it that way: document sources, use ranges instead of point estimates, and flag where your reasoning is weakest.

TAM/SAM/SOM breaks the market into three concentric layers. Total Addressable Market (TAM) represents the entire revenue opportunity if every potential customer in the world bought your type of product. Serviceable Addressable Market (SAM) narrows TAM by the geographic, segment, channel, and capability constraints that limit what you can actually serve. Serviceable Obtainable Market (SOM) projects what you can realistically capture in years one through three, given your go-to-market capacity, competitive dynamics, and sales cycle length.

The framework demands two independent approaches: top-down (starting from published industry data and narrowing) and bottom-up (counting customers and multiplying by average revenue per customer). When these approaches diverge significantly, the gap itself is the most valuable finding — it reveals where your assumptions are weakest and where you need better data before committing resources.

---

## Task Structure

High-level view of framework execution:

| Task | Goal | Key Inputs | Key Outputs |
|------|------|------------|-------------|
| 1. Define Market Boundaries And Methodology | Decide which product/segment this sizing covers and choose top-down and bottom-up approaches | Lean Canvas (Customer Segments, Revenue Streams, Channels), Working Backwards customer definition, JTBD segment selection | Market definition brief, methodology plan, data source inventory |
| 2. Calculate Total Addressable Market (TAM) | Estimate the entire market for your product category using top-down and bottom-up methods | Market definition brief, industry reports, public data, Lean Canvas Revenue Streams | TAM estimate with range, methodology notes, source log |
| 3. Define Serviceable Addressable Market (SAM) | Narrow TAM by geographic, segment, channel, and capability constraints | TAM estimate, Lean Canvas (Customer Segments, Channels), Working Backwards customer definition | SAM estimate with range, constraint rationale, narrowing waterfall |
| 4. Estimate Serviceable Obtainable Market (SOM) | Project realistic capture for years 1-3 based on go-to-market capacity and competitive dynamics | SAM estimate, Lean Canvas (Channels, Revenue Streams, Cost Structure), competitive landscape | SOM estimate with year 1-3 projections, capture rate assumptions |
| 5. Cross-Reference And Stress-Test Estimates | Compare top-down vs bottom-up, check against Lean Canvas economics, identify fragile assumptions | TAM/SAM/SOM estimates, Lean Canvas, Leap of Faith assumptions | Reconciliation analysis, fragile assumption list, confidence ratings |
| 6. Document And Wire Into M2 Artefacts | Save analysis, update project memo, feed into Unit Economics and Assumption Mapping | All estimates from Tasks 1-5, project memo, M2 founder diary | Saved TAM/SAM/SOM document, updated memo and diary, downstream input notes |

---

## Task 1: Define Market Boundaries And Methodology

**Goal:** Produce a precise market definition brief that fixes the product scope, customer segment, and geographic boundaries for this sizing exercise, and select concrete top-down and bottom-up methodologies.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Lean Canvas (Customer Segments, Revenue Streams, Channels) | M1 applied framework | Yes |
| Working Backwards customer definition and PR/FAQ | M1 applied framework | Yes |
| JTBD analysis (primary job, segment selection) | M1 applied framework | Yes |
| Leap of Faith analysis (market-related assumptions) | M2 Step 2 | Yes |
| Assumption Mapping (market assumptions flagged for testing) | M2 Step 3 | No but recommended |

**Action:**

1. State the **product or product slice** this sizing covers in one sentence. Use the same scope as your Lean Canvas. Do not size a broader market than what your product addresses.
2. State the **customer segment** precisely: role, company type/size, industry vertical, geography, digital maturity. Pull directly from Lean Canvas Customer Segments and Working Backwards customer definition.
3. Define the **product category** as an outsider would recognise it. Name the category buyers would search for or analysts would report on (for example, "project management software for SMBs", "API-first payment processing for e-commerce", "compliance automation for fintech startups").
4. Identify **top-down data sources** you will use:
   - Industry analyst reports (Gartner, IDC, Forrester, Statista, Grand View Research, etc.).
   - Public company filings and investor presentations of competitors or adjacent players.
   - Government or trade association data (census data, industry registers).
   - Note the publication date and geographic scope of each source.
5. Design your **bottom-up approach**:
   - Define the unit: individual users, companies, teams, transactions, or seats.
   - Identify where you will get the count of potential units (LinkedIn data, industry directories, government registries, existing databases).
   - Define how you will estimate average revenue per unit (ARPU) from Lean Canvas Revenue Streams, competitor pricing, or willingness-to-pay research.
6. Document a **Market Definition Brief** (half-page max) containing:
   - Product scope (what is in, what is out).
   - Target segment definition.
   - Product category label.
   - Chosen top-down sources (with dates and scope).
   - Bottom-up unit and ARPU logic.
   - Known limitations and gaps in available data.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Market Definition Brief | Half-page narrative at top of TAM/SAM/SOM document | Locks the sizing exercise to one product, segment, and methodology before calculations begin |
| Data Source Inventory | Table listing each source, date, scope, and reliability | Enables traceability and future updates when new data appears |

**Validation:**

- [ ] You can answer in one sentence: "This market sizing covers **[product category]** for **[segment]** in **[geography/scope]**."
- [ ] The product category is one that industry analysts or buyers would recognise, not an invented label.
- [ ] You have at least **two independent top-down sources** and a concrete bottom-up unit definition.
- [ ] The segment definition matches what is used in your Lean Canvas Customer Segments block.

---

## Task 2: Calculate Total Addressable Market (TAM)

**Goal:** Estimate the entire revenue opportunity for your product category assuming every potential customer worldwide (or in your broadest relevant geography) bought a solution like yours.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Market Definition Brief | Task 1 | Yes |
| Industry analyst reports and public market data | Data Source Inventory from Task 1 | Yes |
| Lean Canvas Revenue Streams (pricing model, ARPU range) | M1 applied framework | Yes |
| Competitor pricing and public revenue data | Desk research, public filings | No but strongly recommended |

**Action:**

1. **Top-down calculation:**
   - Start with the broadest credible published figure for your product category's total market size (annual revenue or spend).
   - Note the source, date, geography, and definition used. If the report's definition is broader than your product category, note the delta and adjust.
   - If multiple analyst reports exist, record each estimate and compute the range. Do not cherry-pick the most flattering number.
   - Express TAM (top-down) as an annual revenue figure with a range: "TAM (top-down): [low]–[high] per year."
2. **Bottom-up calculation:**
   - Count the **total number of potential customers** (companies, users, or other units) in the broadest relevant geography. Use the unit definition from Task 1.
   - Multiply by your estimated **average revenue per customer per year** (ARPU). Use the pricing logic from Lean Canvas Revenue Streams. If pricing is uncertain, use a range.
   - Express TAM (bottom-up) as: "[total units] x [ARPU range] = [low]–[high] per year."
3. **Compare the two TAM figures:**
   - If they are within 2x of each other, record both and use the overlap range as your working TAM.
   - If they diverge by more than 2x, investigate why. Common reasons: different product category definitions, stale data, geographic mismatch, or incorrect unit count. Document the discrepancy and your best explanation.
4. Record the **working TAM range** you will carry forward, with explicit notes on which assumptions drive the upper and lower bounds.
5. Add any market-level assumptions to your **Assumptions List** (for example, "We assume the compliance software market grows at 12% CAGR through 2028 per Gartner 2025 report").

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| TAM estimate (top-down) | Annual revenue range with source citations | Provides industry-validated ceiling for the market opportunity |
| TAM estimate (bottom-up) | Annual revenue range with unit count and ARPU | Provides ground-level reality check against top-down data |
| Working TAM range | Reconciled range with methodology notes | Serves as input to SAM narrowing in Task 3 |

**Validation:**

- [ ] You have **both** a top-down and a bottom-up TAM figure. Never rely on only one.
- [ ] Every number is sourced and dated. No number appears without a traceable origin.
- [ ] If top-down and bottom-up diverge by more than 2x, you have documented **why** and which you trust more.
- [ ] The TAM figure represents the **entire market** for your product category, not just the portion you can serve. That narrowing happens in Task 3.

---

## Task 3: Define Serviceable Addressable Market (SAM)

**Goal:** Narrow TAM to the portion of the market you could realistically serve given your geographic reach, customer segment focus, channel capabilities, and product constraints.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Working TAM range | Task 2 | Yes |
| Lean Canvas (Customer Segments, Channels) | M1 applied framework | Yes |
| Working Backwards customer definition | M1 applied framework | Yes |
| JTBD analysis (segment selection, primary job) | M1 applied framework | Yes |
| Competitive landscape observations | Desk research | No but recommended |

**Action:**

1. Start from the working TAM and apply **narrowing filters** one by one. For each filter, record the percentage or absolute reduction and the reasoning:
   - **Geography:** Which countries or regions will you serve in the medium term (3-5 years)? Remove the rest. Cite the portion of global market in your target geographies.
   - **Customer segment:** Which company sizes, industries, or roles does your product serve? Remove segments outside your Lean Canvas Customer Segments definition. Use industry breakdowns to estimate.
   - **Product fit:** Does your product only serve a sub-use-case within the broader category? For example, if the TAM covers all project management software but you only serve agile development teams, estimate that sub-segment.
   - **Channel constraints:** Which distribution channels can you realistically operate? If you are self-serve only, exclude enterprise segments that require field sales you cannot build in the medium term.
   - **Technical or regulatory constraints:** Does your product require specific infrastructure, integrations, or regulatory clearance that limits the addressable set?
2. Build a **narrowing waterfall** that shows TAM at the top and each filter reducing it step by step down to SAM. Use a table or bullet list:
   - TAM: [range]
   - After geography filter: [range] (rationale)
   - After segment filter: [range] (rationale)
   - After product fit filter: [range] (rationale)
   - After channel filter: [range] (rationale)
   - After technical/regulatory filter: [range] (rationale)
   - **SAM: [range]**
3. Cross-check the SAM bottom-up:
   - Count the actual number of companies or users that pass **all** your filters.
   - Multiply by ARPU.
   - Compare this bottom-up SAM with the waterfall SAM. Investigate discrepancies.
4. Record the **working SAM range** with explicit notes on which constraints are hard (regulatory, geographic) versus soft (could be expanded later with investment).

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| SAM estimate | Annual revenue range with narrowing waterfall | Defines the realistic market you can serve with your current product and go-to-market design |
| Narrowing waterfall | Step-by-step table showing each filter applied to TAM | Makes every constraint visible and debatable |
| Constraint classification | Hard vs soft labels for each narrowing filter | Identifies which constraints could be relaxed with investment or pivots |

**Validation:**

- [ ] Every narrowing filter is **named, quantified, and justified** — no hand-waving "we estimate about half."
- [ ] The SAM is meaningfully smaller than the TAM. If SAM equals TAM, you have not done real narrowing.
- [ ] You have a bottom-up cross-check of SAM using actual unit counts, not just percentages applied to top-down TAM.
- [ ] Hard constraints (geography, regulation) are distinguished from soft constraints (channel, segment) that could change over time.

---

## Task 4: Estimate Serviceable Obtainable Market (SOM)

**Goal:** Project the realistic revenue you can capture in years one through three, given your go-to-market capacity, competitive dynamics, sales cycle length, and ramp-up trajectory.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Working SAM range | Task 3 | Yes |
| Lean Canvas (Channels, Revenue Streams, Cost Structure) | M1 applied framework | Yes |
| Competitive landscape (number of competitors, their market share, positioning) | Desk research, Lean Canvas Unfair Advantage | Yes |
| Working Backwards Internal FAQ (go-to-market and resources) | M1 applied framework | No but recommended |
| Leap of Faith growth hypothesis | M2 Step 2 | No but recommended |

**Action:**

1. Estimate your **Year 1 go-to-market capacity**:
   - How many leads can you generate per month through your planned channels?
   - What is a realistic conversion rate for your segment and channel type? Use industry benchmarks if you have no data. Cite the benchmark.
   - What is the average sales cycle length (days from first touch to revenue)?
   - How many customers can you onboard and support per month with your current or planned team?
   - Compute: (monthly leads x conversion rate x 12 months) x ARPU = Year 1 revenue estimate.
2. Estimate **Year 2 and Year 3** by modelling growth:
   - What additional channels or capacity will you add?
   - What organic growth drivers exist (referrals, virality, expansion revenue)?
   - Apply a growth rate that is justified by comparable companies at your stage. Do not assume 10x growth without explaining the mechanism.
   - Express each year as a range: "[low]–[high] customers, [low]–[high] revenue."
3. Calculate your **implied market share** (SOM / SAM) for each year. Sanity-check:
   - Year 1 market share above 1-2% of SAM is aggressive for most startups. Justify if you claim more.
   - Year 3 market share above 5-10% of SAM requires a strong competitive moat or a small SAM.
4. Factor in **competitive dynamics**:
   - How many direct competitors exist? What share do the top 2-3 hold?
   - Are incumbents entrenched, or is this a new category with fragmented adoption?
   - What switching costs exist for customers moving from current solutions to yours?
5. Factor in **churn and expansion**:
   - What is your assumed annual churn rate? Use segment-appropriate benchmarks.
   - What expansion revenue do you expect (upsells, seat growth, usage growth)?
   - SOM should reflect net revenue after churn, not just gross new bookings.
6. Record **SOM as a year-by-year table** with customer count, ARPU, gross revenue, churn adjustment, and net revenue for each year.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| SOM estimate (Year 1-3) | Year-by-year table with customer count, revenue, and market share | Projects what you can realistically capture, grounding fundraising and planning |
| Capture rate assumptions | Documented conversion rates, growth rates, churn rates with sources | Makes every growth assumption explicit and testable |
| Competitive context summary | Short narrative on competitive dynamics affecting capture | Explains why your capture rate is plausible given the competitive landscape |

**Validation:**

- [ ] Year 1 SOM is computed from **specific go-to-market inputs** (leads, conversion, cycle length, capacity), not a top-down percentage of SAM.
- [ ] Year 1 implied market share is below 2% of SAM unless you have a compelling structural reason documented.
- [ ] Growth from Year 1 to Year 3 is explained by **named mechanisms** (new channels, expansion revenue, virality), not an arbitrary multiplier.
- [ ] Churn is explicitly modelled. SOM reflects net revenue, not just new bookings.
- [ ] You can name at least **two competitors** and explain why your capture rate is achievable alongside them.

---

## Task 5: Cross-Reference And Stress-Test Estimates

**Goal:** Compare top-down and bottom-up results across all three layers, check internal consistency with Lean Canvas economics, identify the most fragile assumptions, and assign confidence ratings.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| TAM, SAM, SOM estimates (all methods) | Tasks 2-4 | Yes |
| Lean Canvas (Revenue Streams, Cost Structure, Key Metrics) | M1 applied framework | Yes |
| Leap of Faith assumptions (market-related) | M2 Step 2 | Yes |
| Assumption Mapping (market assumptions flagged as high-uncertainty) | M2 Step 3 | No but recommended |

**Action:**

1. **Top-down vs bottom-up reconciliation:**
   - For each layer (TAM, SAM, SOM), compare the top-down-derived figure with the bottom-up-derived figure.
   - Record the gap as a ratio and a narrative explanation.
   - If any gap exceeds 2x, mark it as a **critical discrepancy** and list the most likely causes.
2. **Internal consistency check against Lean Canvas:**
   - Does the SOM Year 1 revenue align with the revenue needed for the Lean Canvas Cost Structure to work? If SOM Year 1 cannot cover basic costs, how long is the runway gap?
   - Does the implied ARPU in your bottom-up calculation match your Lean Canvas Revenue Streams pricing model?
   - Does the customer count implied by SOM match the capacity in your Lean Canvas Channels?
3. **Identify fragile assumptions:**
   - List every assumption that, if wrong by 2x in either direction, would change the SOM by more than 50%.
   - Rank them by: (a) impact on SOM, (b) current confidence level (high/medium/low).
   - For the top 3-5 fragile assumptions, propose how they could be validated (customer interviews, competitor benchmarking, pilot data, channel experiments).
4. **Assign confidence ratings** to each layer:
   - TAM: High/Medium/Low confidence, with one-sentence justification.
   - SAM: High/Medium/Low confidence, with one-sentence justification.
   - SOM: High/Medium/Low confidence, with one-sentence justification.
   - SOM will almost always be Low at pre-revenue stage. That is expected. The value is in knowing what drives the uncertainty.
5. **Cross-reference with Leap of Faith:**
   - Check if any Leap of Faith assumptions directly affect your market sizing (for example, "customers will pay $X/month", "there are Y thousand companies in this segment").
   - If so, ensure the TAM/SAM/SOM document uses the same assumption values and flags them consistently.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Reconciliation analysis | Narrative comparing top-down and bottom-up at each layer | Surfaces where your two methods agree (good) and disagree (investigate) |
| Fragile assumption list | Ranked table with impact, confidence, and validation method | Feeds directly into Assumption Mapping and validation experiment design |
| Confidence ratings | One-line rating per layer (TAM, SAM, SOM) | Gives stakeholders honest signal about estimate reliability |

**Validation:**

- [ ] You have explicitly compared top-down and bottom-up figures at **every layer**, not just TAM.
- [ ] Every gap greater than 2x has a documented explanation and a plan to resolve.
- [ ] The top 3-5 fragile assumptions are named, ranked, and linked to a validation method.
- [ ] SOM Year 1 has been checked against Lean Canvas Cost Structure for financial plausibility.
- [ ] Confidence ratings are honest. Claiming "high confidence" on SOM at pre-revenue stage is a red flag.

---

## Task 6: Document And Wire Into M2 Artefacts

**Goal:** Save the TAM/SAM/SOM analysis as a versioned artefact, update the project memo, feed estimates into Unit Economics and Assumption Mapping, and log key decisions.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| All estimates and analyses from Tasks 1-5 | Tasks 1-5 | Yes |
| Project memo | `projects/[project]/founder/[project]_memo.md` | Yes |
| M2 founder diary | `projects/[project]/founder/validation/m2_founder_diary.md` | Yes |
| Assumption Mapping document | M2 Step 3 | No but recommended |
| Unit Economics framework (if started) | M2 Step 5 | No |

**Action:**

1. **Save the TAM/SAM/SOM document:**
   - Save to `projects/[project]/founder/validation/tam_sam_som.md`.
   - Include all sections: Market Definition Brief, TAM (top-down + bottom-up), SAM (with narrowing waterfall), SOM (year 1-3 table), reconciliation analysis, fragile assumptions, and confidence ratings.
   - Tag with version and date (for example, "TAM/SAM/SOM v1.0 — Pre-Revenue — 2026-01-30").
2. **Feed into Unit Economics:**
   - Extract from this analysis: SOM Year 1-3 customer counts, ARPU, and churn rate.
   - These become direct inputs to LTV, CAC, and break-even calculations. Note the linkage explicitly in both documents.
3. **Feed into Assumption Mapping:**
   - Add any new fragile assumptions identified in Task 5 to the Assumption Map.
   - For assumptions already on the map, update their uncertainty and importance ratings based on the market sizing work.
4. **Update the project memo:**
   - Progress > Validation subsection: add a one-paragraph summary of market sizing findings with key numbers and confidence levels.
   - Open Questions: add any unresolved market questions (for example, "Exact count of target companies in DACH region not yet validated").
5. **Update the M2 founder diary:**
   - Log the creation of the TAM/SAM/SOM analysis with version and date.
   - Record the top 3 insights or surprises from the analysis.
   - Record any decisions triggered by market sizing (for example, "Narrowed initial geography to UK only based on SAM analysis").
6. **Feed into Pre-mortem:**
   - Flag any market risk scenarios that emerged from this analysis (for example, "Market too small to support venture returns", "TAM shrinking due to regulatory change").
   - These become candidate failure modes for the Pre-mortem exercise.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Saved TAM/SAM/SOM document | Versioned markdown in `projects/[project]/founder/validation/` | Canonical market sizing record for the project |
| Unit Economics input notes | Extracted figures with cross-references | Ensures financial model uses the same market assumptions |
| Updated Assumption Mapping entries | New or revised entries in Assumption Map | Keeps the assumption inventory current with market sizing findings |
| Updated project memo and M2 founder diary | Revised sections in existing documents | Maintains narrative continuity and decision trail |

**Validation:**

- [ ] A TAM/SAM/SOM document exists at project level with all sections populated and a dated version tag.
- [ ] The SOM Year 1-3 figures are explicitly referenced in Unit Economics inputs (or noted as pending if Unit Economics has not started).
- [ ] Fragile assumptions from Task 5 appear in the Assumption Map.
- [ ] The project memo Progress > Validation section mentions market sizing findings.
- [ ] The M2 founder diary has at least one entry documenting the market sizing analysis and key takeaways.

---

## Pitfalls

**Using TAM As Your Pitch Number**

NEVER present TAM as "the market opportunity" to investors or yourself. TAM is a ceiling, not a target. SOM is what matters for planning. Investors who know what they are doing will discount your TAM immediately and ask about SOM.

**Relying On A Single Data Source**

NEVER base your entire sizing on one analyst report or one database. MUST use at least two independent approaches (top-down and bottom-up) and cross-reference. Single-source estimates have no error correction.

**Using Point Estimates Instead Of Ranges**

NEVER write "TAM = $2.4B" as if it were a known fact. MUST express every figure as a range and document what drives the upper and lower bounds. Fake precision destroys credibility and hides uncertainty.

**Sizing The Market You Wish Existed**

NEVER define your product category to inflate the market. If you build a niche compliance tool, do not size the entire GRC (governance, risk, compliance) market. Size the segment where your product actually competes for budget.

**Ignoring Competitive Reality In SOM**

NEVER compute SOM as a percentage of SAM without modelling your actual go-to-market capacity. SOM must be built from leads, conversion rates, sales cycles, and support capacity. A 5% SAM capture assumption with no mechanism behind it is fiction.

**Treating Market Sizing As A One-Time Exercise**

NEVER create market sizing once and forget it. MUST update when you gain real data (early customers, pricing experiments, channel tests) or when market conditions shift. Version the document and log updates in the founder diary.

---

## Integration

**Prerequisites:** MUST complete Leap of Faith analysis (M2 Step 2). Assumption Mapping (M2 Step 3) strongly recommended. MUST have M1 artefacts available: Lean Canvas, Working Backwards PR/FAQ, JTBD analysis.

**Builds On:**

| Framework | Output Used | How Used |
|-----------|-------------|----------|
| Lean Canvas | Customer Segments, Revenue Streams, Channels, Cost Structure | Provides segment definition, pricing model, and channel assumptions that anchor the sizing exercise |
| Working Backwards (PR/FAQ) | Customer definition, Internal FAQ economics | Supplies the primary customer archetype and early economic thinking that frame market boundaries |
| Jobs-To-Be-Done | Primary job, segment selection, alternatives | Grounds segment definition in real customer behaviour and identifies which segments to include or exclude |
| Leap of Faith | Market-related assumptions (value and growth hypotheses) | Ensures market sizing addresses the most critical assumptions about market existence and growth |
| Assumption Mapping | Market assumptions flagged as high-uncertainty | Identifies which market assumptions most need testing and stress-testing in this framework |

**Feeds Into:**

| Framework | Output Provided | How Used |
|-----------|-----------------|----------|
| Unit Economics | SOM customer counts, ARPU, churn rate, revenue projections | Provides the revenue base for LTV, CAC, payback, and break-even calculations |
| Assumption Mapping | New or updated market assumptions with confidence ratings | Enriches the assumption map with market-specific uncertainties and validation needs |
| Pre-mortem | Market risk scenarios (too small, shrinking, wrong segment) | Supplies candidate failure modes related to market size and market dynamics |
| Project memo | Market sizing summary, confidence levels, open questions | Updates the validation narrative with concrete market evidence |
| M5 Market Validation | Target segment size, capture assumptions to test | Provides quantitative hypotheses that customer conversations and experiments can validate |

**Workflow Position:** TAM/SAM/SOM sits in M2 Validation as Step 4, after Leap of Faith (Step 2) and Assumption Mapping (Step 3), and before Unit Economics (Step 5). Market sizing provides the revenue foundation that Unit Economics requires.

---

## Success Criteria

This framework is complete when:

- [ ] A TAM/SAM/SOM document exists under `projects/[project]/founder/validation/` with a dated version tag and all sections populated.
- [ ] TAM has been calculated using **both** top-down and bottom-up methods, with sources cited for every figure.
- [ ] SAM includes a narrowing waterfall with each constraint named, quantified, and classified as hard or soft.
- [ ] SOM includes year 1-3 projections built from go-to-market capacity inputs (leads, conversion, cycle length, churn), not arbitrary percentages of SAM.
- [ ] Top-down and bottom-up estimates have been compared at every layer, with discrepancies documented and explained.
- [ ] The top 3-5 fragile assumptions are identified, ranked, and linked to validation methods.
- [ ] SOM Year 1 has been checked against Lean Canvas Cost Structure for financial plausibility.
- [ ] Unit Economics inputs (customer counts, ARPU, churn) are explicitly extracted and cross-referenced.
- [ ] The project memo and M2 founder diary have been updated with market sizing findings and key decisions.

---

## References

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS >= 6

Sources consulted when designing this framework:

- [1] TAM SAM SOM — `https://en.wikipedia.org/wiki/Total_addressable_market` — Research Date: 2026-01-30 — Source Date: n/a — TS: 7.7 (AT: 7, TR: 8, TM: 8)
- [2] How To Calculate TAM, SAM, and SOM — `https://www.bdc.ca/en/articles-tools/blog/tam-sam-som` — Research Date: 2026-01-30 — Source Date: n/a — TS: 7 (AT: 7, TR: 7, TM: 7)
- [3] Market Sizing For Startups — `https://www.sequoiacap.com/article/market-sizing/` — Research Date: 2026-01-30 — Source Date: n/a — TS: 8 (AT: 9, TR: 8, TM: 7)
- [4] Bottom-Up Market Sizing — `https://visible.vc/blog/tam-sam-som/` — Research Date: 2026-01-30 — Source Date: n/a — TS: 6.7 (AT: 6, TR: 7, TM: 7)
- [5] TAM SAM SOM Analysis For Startups — `https://fi.co/insight/tam-sam-som` — Research Date: 2026-01-30 — Source Date: n/a — TS: 6.3 (AT: 6, TR: 6, TM: 7; TR penalised -1 for marketing language)

Additional conceptual references (books, not scored):

- Bill Aulet, *Disciplined Entrepreneurship: 24 Steps to a Successful Startup* (Wiley, 2013) — Chapter on market sizing.
- Steve Blank & Bob Dorf, *The Startup Owner's Manual* (K&S Ranch, 2012) — Market type and sizing methodology.

### Sources Discarded

The following sources were reviewed but not used because they did not meet the TS >= 6 threshold:

| Source | TS | Reason |
|--------|----|--------|
| [TAM SAM SOM Template — Slidebean](https://slidebean.com/templates/tam-sam-som) | 5 (AT: 4, TR: 5, TM: 6; AT penalised -2 for template-only content) | Primarily a pitch deck template; no substantive methodology guidance |

---

## For AI Agents

**Execution Context:** When executing this framework with a user:

1. MUST confirm that Lean Canvas, Working Backwards PR/FAQ, and JTBD analysis exist from M1. If not, MUST flag and help the user create minimal versions or retrieve relevant inputs before proceeding.
2. MUST confirm that Leap of Faith analysis (M2 Step 2) is complete. If Assumption Mapping (Step 3) is also done, use it. If not, proceed but note that fragile assumptions from Task 5 will need to be fed back into Assumption Mapping later.
3. MUST read this framework and `validation_process.md` before starting. Track progress explicitly: "Currently in Task [N]: [Task Name]".
4. MUST insist on both top-down and bottom-up methods. If the user wants to skip one, explain that single-method sizing has no error correction and push for at least a rough second estimate.
5. MUST enforce ranges instead of point estimates. If the user gives a single number, ask: "What is the low end? What is the high end? What drives each?"
6. MUST flag any SOM calculation that is a simple percentage of SAM without go-to-market capacity justification. Push the user to model from leads, conversion, and capacity instead.

**Working With Tasks:**

- MUST treat each task as atomic. NEVER skip validation criteria without recording explicit risks or TODOs.
- When data sources are unavailable or outdated, document the gap and propose alternative approaches (proxy markets, analogous companies, government data).
- When the user has no competitive data, help them identify competitors through product directories, review sites, and LinkedIn searches before accepting "no competition" as an answer.
- When significant new data appears (first customers, pricing tests, channel experiments), MUST propose an updated version of the TAM/SAM/SOM document and guide the user through revising affected estimates.

---

