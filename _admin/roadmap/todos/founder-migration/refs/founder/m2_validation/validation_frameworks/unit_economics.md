---
---

# Unit Economics

**Purpose:** Model the financial viability of the business at the per-customer level. Answer definitively: can we make money serving this customer, and how long until we do?

**Context:** Use in M2 Validation, Step 5. MUST complete TAM/SAM/SOM first. Uses Lean Canvas Revenue Streams, Cost Structure, Key Metrics, and Channels blocks plus Working Backwards Internal FAQ economics as primary inputs.

---

## Framework Overview

Unit economics reduces your entire business model to the economics of one customer (or one transaction, or one seat). If you cannot make money on one unit, you cannot make money on a million. This framework forces you to quantify the revenue a customer generates over their lifetime, the cost of acquiring that customer, the ratio between the two, and the timeline to break-even. Every number is an assumption until validated, so every number gets tagged and wired into the Leap of Faith backlog.

Most early-stage founders skip unit economics because "we do not have data yet." That is exactly the point. Building the model now forces you to make your assumptions explicit, identify which ones most affect viability, and design experiments to test them before burning cash. A model built on explicit assumptions is infinitely more useful than no model at all. The model is a hypothesis container, not a forecast.

This framework produces six outputs: a defined unit and revenue model, an LTV estimate, a CAC estimate, an LTV:CAC ratio with payback period, a break-even analysis, and a sensitivity analysis with tagged assumptions. Together they form the economic backbone of your M2 validation work and feed directly into Assumption Mapping, Pre-mortem, and M5 pricing experiments.

---

## Task Structure

High-level view of framework execution:

| Task | Goal | Key Inputs | Key Outputs |
|------|------|------------|-------------|
| 1. Define The Unit And Revenue Model | Clarify what "one unit" means for your business and map the revenue model from Lean Canvas | Lean Canvas Revenue Streams and Customer Segments, Working Backwards Internal FAQ, TAM/SAM/SOM | Unit definition, revenue model description, revenue-per-unit assumptions |
| 2. Calculate Customer Lifetime Value (LTV) | Model average revenue per customer x gross margin x average customer lifetime using retention and churn assumptions | Unit definition, revenue model, Lean Canvas Key Metrics, retention/churn assumptions | LTV estimate with ranges, underlying assumption table |
| 3. Estimate Customer Acquisition Cost (CAC) | Model total acquisition spend / new customers acquired per channel | Lean Canvas Channels, go-to-market assumptions, TAM/SAM/SOM segment data | CAC estimate per channel, blended CAC, channel assumption table |
| 4. Compute LTV:CAC Ratio And Payback Period | Calculate the ratio and payback period, interpret implications for cash flow and fundraising | LTV estimate, CAC estimate, gross margin | LTV:CAC ratio, payback period in months, cash flow implications |
| 5. Model Break-Even Analysis | Calculate customer count and timeline to break-even given fixed costs, contribution margin, and growth rate | Fixed costs from Lean Canvas Cost Structure, contribution margin, growth rate assumptions | Break-even customer count, break-even timeline, monthly burn context |
| 6. Run Sensitivity Analysis And Tag Assumptions | Identify which inputs most affect viability, create scenarios, wire assumptions into Leap of Faith | All Task 1-5 outputs, Lean Canvas assumptions list | Sensitivity table, scenario models (optimistic/base/pessimistic), tagged assumption list for M2 backlog |

---

## Task 1: Define The Unit And Revenue Model

**Goal:** Establish an unambiguous definition of what "one unit" means for your business and map the revenue model so all subsequent calculations share a common base.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Lean Canvas Revenue Streams block | M1 Lean Canvas applied framework | Yes |
| Lean Canvas Customer Segments block | M1 Lean Canvas applied framework | Yes |
| Working Backwards Internal FAQ (economics section) | M1 Working Backwards applied framework | Yes |
| TAM/SAM/SOM analysis | M2 Step 4 applied framework | Yes |
| Lean Canvas Cost Structure block | M1 Lean Canvas applied framework | No but recommended |

**Action:**

1. Decide what **"one unit"** means for your business: per customer (B2B SaaS with annual contracts), per seat/user (collaboration tools), per transaction (marketplaces), or per usage unit (API calls, storage). If your model blends multiple (for example, base subscription plus usage overage), define the **primary unit** for LTV/CAC and note secondary streams separately.
2. From the Lean Canvas Revenue Streams block, extract the **pricing model**, **price point or range** per unit per period, **expansion revenue** mechanisms (upsell, add-ons, seat expansion), and **contraction risks** (downgrades, seasonal drops).
3. From TAM/SAM/SOM, extract the **number of potential customers** in your SOM for years 1-3 and the **average deal size** implied by your segment and pricing.
4. From the Working Backwards Internal FAQ, extract any stated or implied **revenue targets**, **pricing constraints**, and assumptions about **willingness to pay**.
5. Write a **Unit Definition Statement** (2-3 sentences): "One unit is [definition]. We charge [price] per [period] under a [model] pricing structure. Expansion revenue comes from [mechanism]."
6. Create a **Revenue Assumptions Table** listing each assumption with: Assumption ID (for example, REV-1), description, value or range, source (data/benchmark/hypothesis), and confidence level (high/medium/low).

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Unit Definition Statement | Short narrative at top of unit economics doc | Ensures all participants and downstream frameworks share the same base unit |
| Revenue Assumptions Table | Structured table | Makes every revenue input explicit and auditable; feeds into LTV calculation |

**Validation:**

- [ ] You can state in one sentence what "one unit" is and how you charge for it.
- [ ] The pricing model is consistent with the Lean Canvas Revenue Streams block and TAM/SAM/SOM segment.
- [ ] Every revenue number has a source tag (data, benchmark, or hypothesis) and a confidence level.
- [ ] A neutral reader can reconstruct your revenue-per-unit calculation from the assumptions table alone.

---

## Task 2: Calculate Customer Lifetime Value (LTV)

**Goal:** Produce a defensible LTV estimate expressed as a range, with every input assumption tagged and traceable.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Unit Definition Statement and Revenue Assumptions Table | Task 1 | Yes |
| Lean Canvas Key Metrics (retention, churn) | M1 Lean Canvas applied framework | Yes |
| Working Backwards Internal FAQ (customer behaviour assumptions) | M1 Working Backwards applied framework | No but recommended |
| Industry benchmarks for churn and retention | Desk research, SaaS benchmarks | No but recommended |

**Action:**

1. Define **Average Revenue Per Unit (ARPU)** per period. Use the price point from Task 1. Include expansion revenue as a percentage uplift if applicable (for example, "net revenue retention of 110% implies 10% annual expansion"). Use monthly ARPU for monthly models; annualise only when comparing to annual benchmarks.
2. Estimate **Gross Margin**: (Revenue - COGS) / Revenue. For SaaS, COGS typically includes hosting, third-party APIs, customer support, and payment processing. For marketplaces, include payment processing, fraud, and seller-side costs. Record what is included in COGS.
3. Estimate **Average Customer Lifetime**. If you have churn data: Lifetime = 1 / churn rate (monthly or annual). If no data, use industry benchmarks: SMB monthly churn 3-7% (lifetime 14-33 months), mid-market annual churn 10-15% (lifetime 6.7-10 years), enterprise annual churn 5-10% (lifetime 10-20 years). Cap lifetime at a reasonable maximum (for example, 5 years for early-stage) to avoid fantasy numbers.
4. Calculate **LTV**: LTV = ARPU x Gross Margin x Average Customer Lifetime (same time unit). If modelling net revenue retention above 100%, use: LTV = ARPU x Gross Margin / (Churn Rate - Net Expansion Rate), only when churn exceeds expansion. If net expansion exceeds churn, cap LTV and note the assumption.
5. Produce **three LTV estimates**: pessimistic (higher churn, lower ARPU, no expansion), base (best current assumptions), optimistic (lower churn, higher ARPU, expansion included).
6. Add all assumptions to the **Assumptions Table** with IDs (for example, LTV-1 through LTV-N), values, sources, and confidence levels.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| LTV estimate (pessimistic/base/optimistic) | Three figures with supporting calculation | Quantifies the revenue potential of one acquired customer |
| LTV Assumptions Table | Structured table | Makes retention, churn, ARPU, and margin assumptions explicit for validation |

**Validation:**

- [ ] LTV is expressed as a range (pessimistic/base/optimistic), not a single point estimate.
- [ ] The churn or retention assumption is sourced (data, benchmark, or tagged as pure hypothesis).
- [ ] Gross margin includes all material COGS items; nothing is hidden.
- [ ] Customer lifetime is capped at a reasonable maximum for your stage.
- [ ] You can explain to a sceptical investor how you arrived at each number.

---

## Task 3: Estimate Customer Acquisition Cost (CAC)

**Goal:** Model the fully loaded cost to acquire one new customer, broken down by channel, with all assumptions tagged.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Lean Canvas Channels block | M1 Lean Canvas applied framework | Yes |
| Lean Canvas Cost Structure block | M1 Lean Canvas applied framework | Yes |
| TAM/SAM/SOM analysis (segment size, reachability) | M2 Step 4 applied framework | Yes |
| Go-to-market assumptions (team, spend, timelines) | Founder/team early planning | No but recommended |
| Industry CAC benchmarks | Desk research | No but recommended |

**Action:**

1. List all **planned acquisition channels** from the Lean Canvas Channels block. For each, classify as paid (ads, sponsorships), organic (content, SEO, community), outbound (sales, partnerships), or product-led (virality, referrals). Note whether each is realistic at your current stage and budget.
2. For each channel, estimate **total spend per period**. Paid: ad spend + creative + tools. Outbound: salaries + commissions + tools. Content/SEO: creator costs + distribution. Product-led: engineering time + referral incentives. Include **people costs** allocated to acquisition (marketing salaries, founder time on sales).
3. For each channel, estimate **new customers acquired per period** using conversion funnel logic: impressions/leads x conversion rate = customers. If no data, use benchmarks: paid SaaS $50-500 CAC for SMB, $5K-50K for enterprise; content/inbound lower CAC but slower to scale; outbound B2B higher CAC but more predictable. Early channels are always less efficient than mature ones.
4. Calculate **CAC per channel**: Total channel spend / New customers from that channel.
5. Calculate **Blended CAC**: Total acquisition spend across all channels / Total new customers acquired.
6. Produce **three CAC estimates** (pessimistic/base/optimistic) by varying conversion rates and spend efficiency.
7. Add all assumptions to the **Assumptions Table** with IDs (for example, CAC-1 through CAC-N), values, sources, and confidence levels.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| CAC estimate per channel | Table with spend, customers, and CAC per channel | Shows which channels are economically viable and where to focus |
| Blended CAC estimate (pessimistic/base/optimistic) | Three figures with supporting calculation | Single number for LTV:CAC ratio and payback calculations |
| CAC Assumptions Table | Structured table | Makes spend, conversion, and efficiency assumptions explicit for validation |

**Validation:**

- [ ] CAC includes **all** acquisition costs, not just ad spend (people, tools, content, commissions).
- [ ] Each channel CAC is calculated independently before blending.
- [ ] Conversion rate assumptions are sourced (data, benchmark, or tagged as pure hypothesis).
- [ ] CAC estimates reflect your **current stage**, not a mature company's efficiency.
- [ ] You have not confused CAC (cost to acquire a paying customer) with CPL (cost per lead).

---

## Task 4: Compute LTV:CAC Ratio And Payback Period

**Goal:** Calculate the LTV:CAC ratio and CAC payback period, and interpret what they mean for your business viability, cash flow, and fundraising needs.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| LTV estimate (pessimistic/base/optimistic) | Task 2 | Yes |
| Blended CAC estimate (pessimistic/base/optimistic) | Task 3 | Yes |
| Gross margin percentage | Task 2 | Yes |
| ARPU per month | Task 2 | Yes |

**Action:**

1. Calculate **LTV:CAC ratio** for each scenario: pessimistic LTV / pessimistic CAC, base / base, optimistic / optimistic. For true worst case, also check pessimistic LTV against optimistic CAC (highest spend, lowest return).
2. Interpret the ratio: **below 1:1** means you lose money on every customer and the model is broken; **1:1 to 3:1** is marginal with thin margins for error; **3:1 or above** is healthy for SaaS with room to invest in growth; **above 5:1** suggests you may be under-investing in acquisition.
3. Calculate **CAC Payback Period**: Payback (months) = CAC / (monthly ARPU x Gross Margin). This is how many months of payments it takes to recover acquisition cost.
4. Interpret payback: **under 12 months** is strong; **12-18 months** is acceptable for B2B SaaS with annual contracts; **above 18 months** is dangerous for early-stage because you are cash-negative on each customer for over a year.
5. Calculate **cash implications**: if acquiring N customers per month, monthly cash outflow = N x CAC, not recovered for [payback period] months. Total cash needed = cumulative CAC spend during payback period minus cumulative gross margin collected.
6. Document the **fundraising implication**: if payback exceeds 12 months, you need external capital to fund new acquisition. State this explicitly.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| LTV:CAC ratio (three scenarios) | Table with interpretation | Core viability metric; determines whether the business model can work |
| Payback period (months) | Single figure per scenario with interpretation | Shows cash flow timing and capital requirements |
| Cash flow implications | Short narrative | Connects unit economics to fundraising and runway decisions |

**Validation:**

- [ ] LTV:CAC ratio is calculated for at least pessimistic and base scenarios, not just the optimistic case.
- [ ] Payback period uses **gross margin-adjusted** monthly revenue, not raw ARPU.
- [ ] You have explicitly stated whether the ratio and payback period require external funding to sustain growth.
- [ ] If the base-case ratio is below 3:1, you have identified which variable (price, churn, CAC) must improve and by how much.
- [ ] The interpretation is honest; you have not cherry-picked the optimistic scenario to declare viability.

---

## Task 5: Model Break-Even Analysis

**Goal:** Calculate how many customers and how much time you need to reach break-even, given fixed costs, contribution margin, and growth assumptions.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Lean Canvas Cost Structure block (fixed costs) | M1 Lean Canvas applied framework | Yes |
| Contribution margin per customer (ARPU x Gross Margin - variable costs per customer) | Tasks 1-2 | Yes |
| Growth rate assumptions (new customers per month) | TAM/SAM/SOM, go-to-market assumptions | Yes |
| Churn rate | Task 2 | Yes |
| CAC per new customer | Task 3 | Yes |

**Action:**

1. List all **monthly fixed costs**: founder and team salaries (including your own at a reasonable imputed cost), office, tools, infrastructure not tied to per-customer usage, legal, accounting, insurance. Total as **Monthly Fixed Costs (MFC)**.
2. Calculate **Contribution Margin Per Customer Per Month**: Monthly ARPU x Gross Margin. This is what each customer contributes toward covering fixed costs after variable costs.
3. Calculate **Break-Even Customer Count** (steady-state): Break-Even Customers = MFC / Monthly Contribution Margin Per Customer.
4. Model the **path to break-even over time**: start at 0 customers, each month add new customers (growth rate), subtract churned customers (existing x churn rate), subtract CAC spend from cash flow. Track **cumulative cash position**: starting capital - cumulative fixed costs - cumulative CAC + cumulative gross margin revenue. Identify cash-flow break-even (cumulative position stops declining) and operating break-even (monthly revenue covers monthly costs).
5. Produce **three break-even timelines** (pessimistic/base/optimistic) by varying growth rate and churn.
6. State the **total capital required** to reach break-even under each scenario: this is the maximum negative cumulative cash position (the deepest point of the cash curve).
7. Add growth rate and fixed cost assumptions to the **Assumptions Table**.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Break-even customer count | Single figure per scenario | Concrete target for sales and growth teams |
| Break-even timeline (months) | Three scenarios with month-by-month logic | Shows when the business becomes self-sustaining |
| Total capital required to break-even | Dollar/euro figure per scenario | Direct input to fundraising strategy and runway planning |

**Validation:**

- [ ] Fixed costs include **founder salaries** at a reasonable imputed rate, not zero.
- [ ] Break-even customer count passes a reality check against your SOM (for example, if break-even requires 50% of your SOM, the model is unrealistic).
- [ ] The timeline accounts for **churn** (net customer growth, not just gross additions).
- [ ] You have stated the total capital required to survive until break-even under the base scenario.
- [ ] The growth rate assumption is consistent with your channel strategy and CAC budget.

---

## Task 6: Run Sensitivity Analysis And Tag Assumptions

**Goal:** Identify which input assumptions most affect viability, build scenario models, and wire every assumption into the M2 validation backlog.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| All outputs from Tasks 1-5 | Tasks 1-5 | Yes |
| Lean Canvas Assumptions List | M1 Lean Canvas applied framework | Yes |
| Leap of Faith analysis (if completed) | M2 Step 2 applied framework | No but recommended |
| Assumption Mapping (if completed) | M2 Step 3 applied framework | No but recommended |

**Action:**

1. Consolidate all assumptions from Tasks 1-5 into a **Master Assumption Table** with columns: Assumption ID (for example, REV-1, LTV-3, CAC-2, BE-1), description, base value, pessimistic value, optimistic value, source (data/benchmark/hypothesis), confidence (high/medium/low), category (revenue/cost/retention/acquisition/growth).
2. Run a **one-at-a-time sensitivity analysis**: for each key assumption, vary from pessimistic to optimistic while holding all others at base. Record impact on LTV, CAC, LTV:CAC ratio, payback, and break-even. Rank by **impact magnitude**: which single assumption, if wrong, most changes the viability conclusion?
3. Identify the **top 3-5 assumptions that most affect viability**. These are your **critical economic assumptions**.
4. Build **three named scenarios**: pessimistic (all critical assumptions at worst values; does the business still work?), base (best current assumptions; is it viable?), optimistic (all at best values; what is the upside?).
5. For each critical assumption, define **validation evidence** (for example, "achieve <5% monthly churn in first 50 customers"), **invalidation evidence** (for example, "monthly churn exceeds 10% after 3 months"), and **when/how to test** (M5 pricing experiment, early cohort, sales pilot).
6. Wire critical economic assumptions into M2 frameworks: add to **Leap of Faith** as growth hypothesis assumptions, add to **Assumption Mapping** in the high-importance quadrant, flag for **Pre-mortem** as potential financial failure modes.
7. Update the unit economics document with all tables, calculations, and the Master Assumption Table.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Sensitivity analysis table | Table showing impact of each assumption on key metrics | Identifies which assumptions matter most and deserve testing first |
| Three named scenarios (pessimistic/base/optimistic) | Summary table with LTV, CAC, ratio, payback, break-even per scenario | Gives a complete picture of range of outcomes |
| Critical economic assumptions list | Tagged list with validation/invalidation criteria | Direct input to Leap of Faith, Assumption Mapping, and M5 experiments |
| Master Assumption Table | Comprehensive table of all unit economics assumptions | Single source of truth for all economic hypotheses |

**Validation:**

- [ ] Every assumption in the model is listed in the Master Assumption Table with an ID, value range, and source.
- [ ] The top 3-5 critical assumptions are explicitly identified and ranked by impact.
- [ ] Each critical assumption has defined validation and invalidation criteria.
- [ ] The pessimistic scenario clearly states whether the business is viable or not, and what breaks.
- [ ] Critical economic assumptions are wired into at least one other M2 framework (Leap of Faith or Assumption Mapping).
- [ ] You can explain to a co-founder or investor which single assumption, if wrong, kills the business.

---

## Pitfalls

**Using Point Estimates Instead Of Ranges**

NEVER present a single LTV, CAC, or break-even number. MUST use pessimistic/base/optimistic ranges for every figure. Point estimates create false confidence and hide the assumptions that matter most.

**Ignoring Fully Loaded CAC**

NEVER calculate CAC as ad spend alone. MUST include all acquisition costs: people (salaries, commissions), tools, content creation, events, and founder time. Underloading CAC is the most common way founders deceive themselves about viability.

**Using Fantasy Churn Rates**

NEVER assume churn rates better than industry best-in-class without evidence. MUST use realistic benchmarks for your stage and segment. Early-stage SMB SaaS typically sees 3-7% monthly churn; assuming 1% without data is dishonest modelling.

**Conflating Revenue With Cash**

NEVER forget that revenue recognition and cash collection are different. MUST account for payment terms, failed payments, and the timing gap between CAC spend (immediate) and revenue collection (delayed). Annual prepaid contracts help; monthly billing with late payments hurts.

**Skipping Break-Even Because "We Will Raise More"**

NEVER treat fundraising as a substitute for understanding break-even. MUST model break-even to know how much capital you need and how long it lasts. Investors ask this question; not knowing the answer is a red flag.

**Building The Model Once And Never Updating**

NEVER treat unit economics as a one-time M2 exercise. MUST update the model as you get real data from M5 market validation, pricing experiments, and early customers. Version the document and log changes in the M2 founder diary.

---

## Integration

**Prerequisites:** MUST complete TAM/SAM/SOM (M2 Step 4) before starting. MUST have M1 Lean Canvas with populated Revenue Streams, Cost Structure, Key Metrics, and Channels blocks.

**Builds On:**

| Framework | Output Used | How Used |
|-----------|-------------|----------|
| TAM/SAM/SOM | SOM estimates, segment sizes, average deal sizes | Provides the revenue base and customer count context for all calculations |
| Lean Canvas | Revenue Streams, Cost Structure, Key Metrics, Channels | Supplies the pricing model, cost categories, retention metrics, and acquisition channel list |
| Working Backwards Internal FAQ | Economics section, feasibility assumptions, pricing constraints | Seeds initial revenue, cost, and willingness-to-pay assumptions |
| Lean Canvas Assumptions List | Tagged economic assumptions (REV, COST, MET, CH labels) | Provides starting assumptions to refine and quantify in the unit economics model |
| Problem-Solution Fit Canvas | Critical assumptions about adoption and value delivery | Informs retention and churn assumptions (if customers do not get value, they churn) |

**Feeds Into:**

| Framework | Output Provided | How Used |
|-----------|-----------------|----------|
| Assumption Mapping | Critical economic assumptions ranked by impact | Seeds high-importance quadrant with financial viability assumptions |
| Leap of Faith | Growth hypothesis assumptions (CAC, retention, pricing) | Identifies which economic assumptions are true "leaps of faith" |
| Pre-mortem | Financial failure modes, break-even risk, cash flow gaps | Informs financial risk scenarios and mitigation planning |
| M5 Market Validation | Pricing hypotheses, willingness-to-pay assumptions, CAC benchmarks | Designs pricing experiments, channel tests, and conversion funnel measurements |
| Project memo | Validation progress, financial viability summary, open questions | Updates the narrative with economic evidence and fundraising implications |
| M2 founder diary | Key economic decisions, assumption changes, model versions | Documents the evolution of financial understanding |

**Workflow Position:** Unit Economics sits at M2 Step 5, after TAM/SAM/SOM (Step 4) and after Leap of Faith (Step 2) and Assumption Mapping (Step 3). It feeds forward into Pre-mortem (Step 7) and the project memo synthesis (Step 8). If Leap of Faith and Assumption Mapping are not yet complete, unit economics can still proceed but critical assumptions should be flagged for later integration.

---

## Success Criteria

This framework is complete when:

- [ ] A Unit Definition Statement exists that unambiguously defines what "one unit" is and how revenue is generated per unit.
- [ ] LTV is calculated as a range (pessimistic/base/optimistic) with every input assumption tagged, sourced, and assigned a confidence level.
- [ ] CAC is calculated per channel and as a blended figure, including all acquisition costs (people, tools, spend), not just ad budget.
- [ ] LTV:CAC ratio is computed for at least base and pessimistic scenarios, with explicit interpretation of what the ratio means for viability.
- [ ] Payback period is stated in months with an honest assessment of cash flow implications and fundraising needs.
- [ ] Break-even customer count and timeline are modelled with churn, growth rate, and total capital required to reach break-even.
- [ ] A sensitivity analysis identifies the top 3-5 critical assumptions and ranks them by impact on viability.
- [ ] Three named scenarios (pessimistic/base/optimistic) exist with clear viability conclusions for each.
- [ ] Every critical economic assumption has validation and invalidation criteria and is wired into at least one other M2 framework.
- [ ] The project memo and M2 founder diary have been updated with unit economics findings.

---

## References

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS >= 6

Sources consulted when designing this framework:

- [1] David Skok, "SaaS Metrics 2.0" — `https://www.forentrepreneurs.com/saas-metrics-2/` — Research Date: 2026-01-30 — Source Date: n/a — TS: 8.7 (AT: 9, TR: 9, TM: 8)
- [2] David Skok, "Startup Killer: the Cost of Customer Acquisition" — `https://www.forentrepreneurs.com/startup-killer/` — Research Date: 2026-01-30 — Source Date: n/a — TS: 8.3 (AT: 9, TR: 8, TM: 8)
- [3] Jason Lemkin / SaaStr, "The SaaS Adventure" and various SaaStr articles on LTV:CAC and payback — `https://www.saastr.com/` — Research Date: 2026-01-30 — Source Date: n/a — TS: 7.7 (AT: 8, TR: 7, TM: 8)
- [4] Unit Economics — `https://en.wikipedia.org/wiki/Unit_economics` — Research Date: 2026-01-30 — Source Date: n/a — TS: 7.0 (AT: 7, TR: 8, TM: 6)

Additional conceptual references (books, not scored):

- Eric Ries, *The Lean Startup* (Crown Business, 2011) — Leap of faith assumptions and validated learning applied to financial models.
- Ash Maurya, *Running Lean: Iterate from Plan A to a Plan That Works* (O'Reilly, 2012) — Lean Canvas economic blocks and hypothesis-driven modelling.
- Bill Aulet, *Disciplined Entrepreneurship* (Wiley, 2013) — Unit economics and customer lifetime value in startup methodology.

### Sources Discarded

The following sources were reviewed but not used because they did not meet the TS >= 6 threshold:

| Source | TS | Reason |
|--------|----|--------|
| Various VC blog posts on "ideal LTV:CAC ratios" | 5.0 (AT: 5, TR: 4, TM: 6; TR penalised -2 for survivorship bias and marketing language) | Generic prescriptions without methodology transparency; benchmarks stated without context |

---

## For AI Agents

**Execution Context:** When executing this framework with a user:

1. MUST confirm that TAM/SAM/SOM analysis exists and Lean Canvas Revenue Streams, Cost Structure, Channels, and Key Metrics blocks are populated. If TAM/SAM/SOM is missing, MUST complete it before proceeding. If Lean Canvas blocks are sparse, MUST extract what exists and flag gaps.
2. MUST read this framework and `validation_process.md` before starting. Track progress explicitly: "Currently in Task [N]: [Task Name]".
3. MUST treat every number as a hypothesis. Push the user to state ranges, not points. When a user says "our churn will be 2%", ask: "What is the source? What is the pessimistic case? What would make churn higher?"
4. MUST calculate LTV:CAC ratio for the pessimistic scenario, not just the optimistic one. If the pessimistic ratio is below 1:1, surface this immediately and discuss what must change.
5. MUST wire critical economic assumptions into Leap of Faith and Assumption Mapping. Do not treat unit economics as a standalone exercise disconnected from the validation backlog.
6. MUST update the project memo and M2 founder diary with unit economics findings, including the viability conclusion and top assumptions.

**Working With Tasks:**

- MUST treat each task as atomic. NEVER skip to LTV:CAC ratio without completing the unit definition, LTV, and CAC tasks first.
- When the user lacks data for an assumption, use industry benchmarks explicitly labelled as such and tagged with low confidence. NEVER invent numbers or let the user skip the assumption.
- When break-even analysis reveals unrealistic capital requirements, surface this as a key finding and recommend revisiting pricing, cost structure, or growth strategy before proceeding.
- When significant new data arrives from M5 market validation, MUST propose an updated unit economics version and guide the user through re-running affected calculations.

---

