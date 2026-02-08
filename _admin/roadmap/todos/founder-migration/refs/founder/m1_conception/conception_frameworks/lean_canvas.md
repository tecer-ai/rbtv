---
---

# Lean Canvas

**Purpose:** Build and iterate a Lean Canvas that encodes a digital startup's business model hypotheses.

**Context:** Use in M1 Conception, Step 5. MUST complete Working Backwards (PR/FAQ), JTBD analysis, and Problem-Solution Fit Canvas first.

---

## Framework Overview

Lean Canvas encodes business model hypotheses across nine blocks: Problem, Customer Segments, Unique Value Proposition, Solution, Channels, Revenue Streams, Cost Structure, Key Metrics, and Unfair Advantage. Treat as hypothesis map, not static plan.

---

## Task Structure

High-level view of framework execution:

| Task | Goal | Key Inputs | Key Outputs |
|------|------|------------|-------------|
| 1. Consolidate Inputs And Define Canvas Scope | Decide which product, customer segment, and use case this canvas describes, at what stage of maturity | Working Backwards PR/FAQ, JTBD analysis, Problem-Solution Fit Canvas, project memo | Canvas brief (scope, stage, version), initial assumptions list |
| 2. Populate Problem And Customer Segments | Translate upstream artefacts into precise Problem and Customer Segments blocks (including early adopters) | PR/FAQ, JTBD jobs and forces, Problem-Solution Fit problem blocks | Problem block, Customer Segments block, Early Adopters notes |
| 3. Craft Unique Value Proposition And Solution Hypotheses | Define the promise and high-level solution in terms that connect directly to jobs, pains, and alternatives | PR/FAQ, JTBD, Problem-Solution Fit solution block | Unique Value Proposition block, Solution block (top 3 features) |
| 4. Map Channels, Revenue Streams, And Cost Structure | Design digital-first acquisition/delivery channels and economic hypotheses consistent with segment and solution | JTBD behaviours and channels, PR/FAQ, early financial thinking | Channels block, Revenue Streams block, Cost Structure block |
| 5. Define Key Metrics And Unfair Advantage | Select a small set of stage-appropriate metrics and a credible unfair advantage hypothesis | Lean Canvas draft, founder strategy, M2/M5 process docs | Key Metrics block, Unfair Advantage block, metric-to-hypothesis links |
| 6. Finalise Canvas, Tag Assumptions, And Wire To Artefacts | Turn the canvas into a versioned hypothesis artefact connected to project memo, founder log, and validation backlogs | Completed blocks from Tasks 1–5, M1/M2/M5 process docs | Saved Lean Canvas v1+, assumption list, updated memo/log, validation backlog seeds |

---

## Task 1: Consolidate Inputs And Define Canvas Scope

**Goal:** Produce a clear Lean Canvas brief that fixes which product, customer segment, and situation this canvas covers, and at what level of maturity (idea, prototype, early revenue).

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Working Backwards PR/FAQ (Press Release + External/Internal FAQs) | `working_backwards.md` applied framework | Yes |
| JTBD analysis (primary job, forces, job map, priorities) | `jobs_to_be_done.md` applied framework | Yes |
| Problem-Solution Fit Canvas (for chosen segment/situation) | `problem_solution_fit.md` framework and project-level canvas | Yes |
| Project memo (Introduction, Problem, Solution drafts) | `project_memo.md` applied template | No |

**Action:**

1. From **Working Backwards**, extract:
   - The **primary customer archetype** (segment) and problem description.
   - Key **promises** and constraints in the PR and FAQs (for example, "no integration required", "priced for small teams").
2. From **JTBD**, extract:
   - The **primary job story** and 1–2 related jobs.
   - The most important **forces** (push, pull, anxieties, habits).
3. From **Problem-Solution Fit**, extract:
   - The **Problem** and **Our Solution** blocks.
   - **Constraints** and **Critical Assumptions** that affect adoption and economics.
4. Decide and write down the **canvas scope**:
   - Product or product slice this canvas describes (for example, "self-serve SaaS onboarding product, not services").
   - Primary **customer segment** (role, company type/size, geography) and **use case**.
   - Stage of maturity: **Idea**, **Pre-Product Prototype**, **Post-MVP With Early Users**, or **Growing Product**.
5. Create a short **Canvas Brief** (5–8 sentences) containing:
   - One-sentence description of the product.
   - One-sentence description of the primary segment and situation.
   - A pointer to the upstream artefacts (PR/FAQ, JTBD, Problem-Solution Fit).
   - A note on stage (for example, "Idea-stage digital B2B SaaS; no revenue yet").
6. Start an **Assumptions List** document or section where you will later add per-block hypotheses (to be completed in Tasks 2–6).

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Canvas Brief | Short narrative at top of Lean Canvas doc | Locks the canvas to one product, segment, and stage; avoids mixing contexts |
| Initial Assumptions List | Bulleted list or table | Placeholder to collect per-block hypotheses for M2/M5 validation |

**Validation:**

How to know you are done correctly:

- [ ] You can answer in one sentence: "This Lean Canvas describes **[product]** for **[segment]** in **[situation]** at **[stage]**."
- [ ] A neutral reader can restate the scope using only the Canvas Brief and without seeing other artefacts.
- [ ] The chosen segment and situation match those used in the relevant **Problem-Solution Fit Canvas**.
- [ ] You have decided how this canvas will be versioned (for example, "Lean Canvas v0.1 – Idea Stage").

---

## Task 2: Populate Problem And Customer Segments

**Goal:** Fill the **Problem** and **Customer Segments** blocks (including early adopters) using upstream artefacts, not fresh brainstorming.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Canvas Brief | Task 1 | Yes |
| Working Backwards PR/FAQ | Applied framework | Yes |
| JTBD analysis (job stories, forces, job map) | Applied framework | Yes |
| Problem-Solution Fit Canvas (Problem, Behaviours, Constraints) | `problem_solution_fit.md` | Yes |

**Action:**

1. Using JTBD and Problem-Solution Fit, list the **top three problems** you are solving for this segment in the chosen situation:
   - Express each problem in customer language, grounded in **situations and consequences**, not feature gaps.
   - Include "do nothing" as an implicit alternative where relevant.
2. For each problem, note:
   - The **frequency** with which it appears.
   - The **severity** and what happens if it is not solved.
3. Fill the **Problem** block:
   - Three bullet points, each a concise problem statement.
   - Optionally annotate each with a short note (for example, "high frequency, high severity").
4. Define the **Customer Segments** block:
   - Primary segment: role, organisation type/size, geography, digital maturity.
   - Secondary segments (if any) that may be served later; clearly mark them as **future**.
5. Within Customer Segments, explicitly define **Early Adopters**:
   - A narrower slice of the primary segment that feels the problems more acutely or has fewer internal constraints (for example, "seed-stage SaaS companies with <50 employees using 4+ tools for reporting").
6. Add to the **Assumptions List**:
   - Assumptions about problem frequency/severity.
   - Assumptions about how many organisations fit the early adopter description within your initial target markets.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Problem block | Lean Canvas section (3 bullet problems) | Encodes the core pains to be addressed in M1 and validated later |
| Customer Segments block (with Early Adopters) | Lean Canvas section | Clarifies whose jobs and behaviours you are optimising for first |
| Problem/Segment Assumptions | Entries in Assumptions List | Feed into TAM/SAM/SOM, Leap Of Faith, and validation experiments |

**Validation:**

- [ ] Each problem can be traced back to at least one **JTBD job story** and one **Problem-Solution Fit** situation.
- [ ] You can name at least **three real organisations or people** that fit the early adopter description.
- [ ] No problem statement mentions your product or specific features.
- [ ] If you changed the primary segment, at least one Problem or Early Adopter description would have to change meaningfully.

---

## Task 3: Craft Unique Value Proposition And Solution Hypotheses

**Goal:** Populate the **Unique Value Proposition (UVP)** and **Solution** blocks as sharp, testable hypotheses derived from prior work, not generic slogans.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Problem block, Customer Segments block | Task 2 | Yes |
| Working Backwards PR (headline, subheading, key paragraphs) | Applied framework | Yes |
| JTBD primary job and forces | Applied framework | Yes |
| Problem-Solution Fit "Our Solution" block | `problem_solution_fit.md` | Yes |

**Action:**

1. Re-read the **PR headline, subheading, and core paragraphs**. Underline:
   - Phrases that describe the **change in the customer's world** (not the product itself).
   - Claims that clearly differentiate you from alternatives.
2. Draft a **one-sentence UVP** of the form:
   - "For **[primary segment]** who struggle with **[top problems]**, **[product]** is a **[category]** that **[core benefit/outcome]**, unlike **[main alternatives]** which **[key shortcoming].**"
3. Optionally add a short **sub-UVP** for secondary segments if they differ meaningfully, clearly tagged as second-order.
4. Populate the **Solution** block with **three to five high-level features or capabilities**, each:
   - Directly linked to at least one Problem or job.
   - Expressed as **what changes for the customer**, not internal modules (for example, "single workspace that replaces four spreadsheets").
5. For digital startups, ensure Solution elements consider:
   - How the product integrates into existing digital workflows and tools.
   - How it supports self-serve vs sales-assisted adoption, depending on your GTM.
6. Add to the **Assumptions List**:
   - Assumptions that customers will perceive the UVP as meaningfully different.
   - Assumptions about willingness to switch from current alternatives to your Solution.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Unique Value Proposition block | Lean Canvas section (headline + optional sub-UVP) | Captures the core promise you will later validate with customers and metrics |
| Solution block | Lean Canvas section (3–5 capability bullets) | Describes how you intend to deliver on the UVP at a conceptual level |
| UVP/Solution Assumptions | Entries in Assumptions List | Feed into M2 Leap Of Faith, unit economics, and M5 market tests |

**Validation:**

- [ ] A member of the primary segment can read the UVP and immediately see themselves and their problems reflected.
- [ ] Each Solution bullet can be linked to a specific **Problem, job, or force**; nothing is "because it is cool".
- [ ] You can name at least **two mainstream alternatives** against which your UVP is clearly differentiated.
- [ ] If you removed one of the upstream artefacts (PR/FAQ, JTBD, Problem-Solution Fit), the UVP or Solution would become noticeably weaker or less precise.

---

## Task 4: Map Channels, Revenue Streams, And Cost Structure

**Goal:** Design initial **Channels**, **Revenue Streams**, and **Cost Structure** blocks that are coherent with your segment, behaviours, and digital business model, and clearly framed as hypotheses.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Canvas Brief, Problem, Customer Segments, UVP, Solution | Tasks 1–3 | Yes |
| JTBD behaviours and channels of behaviour | Applied framework | Yes |
| Problem-Solution Fit constraints and available solutions | Applied framework | Yes |
| Early financial thinking (if any) | Founder/team | No but recommended |

**Action:**

1. **Channels** (acquisition and delivery):
   - From JTBD and Problem-Solution Fit, list where your segment already spends time digitally (tools, platforms, communities, workflows).
   - Draft 3–5 primary **acquisition channels** that match your segment and stage (for example, content marketing for developers, outbound sales to mid-market, partner integrations, product-led virality).
   - Distinguish between **discovery channels** (how they first hear about you) and **activation channels** (how they experience value).
2. **Revenue Streams**:
   - List candidate **pricing models** suitable for your digital product (for example, per-seat SaaS, usage-based, freemium with paid tiers, transaction fees, revenue share).
   - For each, note:
     - How it maps to your segment's budget structure and buying process.
     - Whether it aligns with the job and value created (for example, "pay per report vs pay per seat").
   - Choose a primary model and, if needed, one backup to test later; record both as hypotheses.
3. **Cost Structure**:
   - List major **fixed costs** (founder salaries, engineering/design/product, core infrastructure, compliance, support tooling).
   - List major **variable costs** per unit of usage or customer (hosting, third-party APIs, support load, sales commissions, payment processing).
   - For early-stage digital startups, explicitly note any **step functions** (for example, "need to hire first CS person at 20 customers").
4. Add to the **Assumptions List**:
   - Assumptions about customer acquisition costs and scalability of chosen channels.
   - Assumptions about pricing power and elasticity.
   - Assumptions about cost drivers that matter for unit economics.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Channels block | Lean Canvas section | Describes how you expect to reach and activate your digital customers |
| Revenue Streams block | Lean Canvas section | Captures monetisation hypotheses tied to value and buying behaviour |
| Cost Structure block | Lean Canvas section | Frames the cost side needed for early unit economics and M2 work |
| Economics/Channels Assumptions | Entries in Assumptions List | Feed into Unit Economics, TAM/SAM/SOM, and validation plans |

**Validation:**

- [ ] Each proposed channel appears naturally in JTBD **behaviours and channels of behaviour** for your segment.
- [ ] The primary pricing model is plausible for the segment's budget and buying process (for example, enterprise vs SMB vs consumer).
- [ ] You can identify at least **one potential path to attractive unit economics** using these revenue and cost hypotheses.
- [ ] You can describe a realistic **first-year go-to-market strategy** consistent with these blocks (even if high level).

---

## Task 5: Define Key Metrics And Unfair Advantage

**Goal:** Select a small set of stage-appropriate **Key Metrics** and a credible **Unfair Advantage** hypothesis that fit your digital context and can be tested in later milestones.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| All existing Lean Canvas blocks (Problem, Segments, UVP, Solution, Channels, Revenue, Costs) | Tasks 1–4 | Yes |
| Working Backwards Internal FAQ (economics, feasibility, risks) | Applied framework | Yes |
| M2 Validation and M5 Market Validation process docs (for inspiration on metrics) | `validation_process.md`, `market_validation_process.md` | No but recommended |

**Action:**

1. **Key Metrics**:
   - Consider the classic digital-product lifecycle (acquisition, activation, retention, referral, revenue).
   - Choose **3–5 metrics** that:
     - Are tightly tied to your primary **job and UVP** (for example, "time to first value", "weekly active teams", "retention after 90 days").
     - Will be realistically measurable at your stage (instrumentation, data quality).
   - Classify metrics as:
     - **Leading indicators** (for example, % of signups who connect data sources within 7 days).
     - **Lagging indicators** (for example, net revenue retention after 12 months).
2. **Unfair Advantage**:
   - Brainstorm potential sources of advantage appropriate to digital startups, such as:
     - Proprietary data or models.
     - Distribution partnerships or existing communities.
     - Deep domain expertise plus embedded workflows.
     - Network effects or multi-sided marketplaces.
   - Reject advantages that are not truly hard to copy or buy (for example, "great team", "first mover").
   - Write a concise **Unfair Advantage** statement that:
     - Names the mechanism (for example, "proprietary dataset of X", "distribution through Y's ecosystem").
     - Explains why it will remain hard to copy for at least several years.
3. Add to the **Assumptions List**:
   - Assumptions that moving the chosen Key Metrics will actually drive funding, runway, or strategic options.
   - Assumptions that your claimed Unfair Advantage can be defended over time.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Key Metrics block | Lean Canvas section | Defines how you will judge early progress beyond vanity metrics |
| Unfair Advantage block | Lean Canvas section | Encodes a specific, testable thesis about defensibility |
| Metrics/Advantage Assumptions | Entries in Assumptions List | Feed into M2/M5 validation, investor narratives, and GTM planning |

**Validation:**

- [ ] You can explain for each metric **why it matters now** and which decision it will inform.
- [ ] None of the Key Metrics are pure vanity (for example, raw signups without activation/retention context).
- [ ] The Unfair Advantage statement would still be meaningful if a well-funded competitor copied your surface features.
- [ ] At least one planned M2 or M5 activity will produce evidence about your Unfair Advantage or its precursors.

---

## Task 6: Finalise Canvas, Tag Assumptions, And Wire To Artefacts

**Goal:** Turn the Lean Canvas into a versioned, actionable hypothesis artefact that is connected to your project memo, founder log, and validation backlogs.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Completed Lean Canvas blocks | Tasks 1–5 | Yes |
| Assumptions List | Tasks 1–5 | Yes |
| M1 Conception process doc | `conception_process.md` | Yes |
| Project memo | `project_memo.md` applied template | Yes |
| M1 founder diary | `m1_founder_diary.md` | Yes |
| M2/M5 process docs and frameworks (Leap Of Faith, TAM/SAM/SOM, Unit Economics, SPIN, Smoke Tests, etc.) | `validation_process.md`, `market_validation_process.md` and related frameworks | No but strongly recommended |

**Action:**

1. **Create/Update the Lean Canvas document**:
   - Save or update `[project]/docs/founder/conception/lean_canvas.md` (or your chosen naming).
   - Ensure all nine blocks plus the **Canvas Brief** and **Assumptions List** are present.
   - Tag the document with a clear version (for example, `Lean Canvas v0.1 – Idea Stage – 2025-12-21`).
2. **Tag assumptions per block**:
   - For each of the nine blocks, ensure that key hypotheses are present in the Assumptions List with labels (for example, `P1`, `CS2`, `UVP1`, `CH1`, `REV2`, `COST1`, `MET1`, `UA1`).
   - Mark each as **behavioural**, **technical**, or **economic** where relevant.
3. **Wire into M2 and M5**:
   - Map the most critical Lean Canvas assumptions into:
     - **Leap Of Faith / Assumption Mapping** (M2).
     - **TAM/SAM/SOM** and **Unit Economics** inputs.
     - **Market Validation** frameworks (SPIN, Smoke Tests, PMF surveys, pricing experiments) where appropriate.
4. **Update the project memo**:
   - Problem section: ensure it reflects the Problem and root-cause understanding implied by Lean Canvas and 5 Whys.
   - Solution section: align with UVP and Solution blocks.
   - Tenets section: add any principles implied by your Unfair Advantage, channels, or key constraints.
   - Progress > Conception subsection: record the existence and version of the Lean Canvas.
5. **Update the M1 founder log**:
   - Log the creation or major revision of the Lean Canvas with:
     - Version identifier and date.
     - Top 3–5 assumptions and what would make you revisit them.
     - Any deliberate trade-offs (for example, segments or revenue models you postponed).

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Project-level Lean Canvas doc | Markdown in `[project]/docs/founder/conception/` | Canonical record of M1 business model hypotheses for the digital startup |
| Tagged Assumptions List | Section in Lean Canvas doc or separate file | Direct input to M2/M5 validation and financial modelling |
| Updated project memo and M1 founder log | artefacts | Ensures narrative and decision trail match the canvas |

**Validation:**

- [ ] A Lean Canvas document exists at project level with all nine blocks, Canvas Brief, and a dated version tag.
- [ ] For each block, at least one key assumption is tagged and appears in a validation or modelling backlog.
- [ ] The project memo's Problem, Solution, and Tenets sections are consistent with the Lean Canvas.
- [ ] The M1 founder log has at least one entry summarising the current Lean Canvas version and main assumptions.

---

## Pitfalls

**Filling Lean Canvas Before Doing Upstream Work**

NEVER start with Lean Canvas. MUST complete Working Backwards PR/FAQ, JTBD analysis, and Problem-Solution Fit Canvas first.

**Mixing Multiple Segments In One Canvas**

NEVER cover multiple customer types in one canvas. MUST create separate canvases for different segments.

**Designing For Investors Instead Of Customers**

NEVER optimize for investor pitch. MUST write in operational language for truth-seeking.

**Treating Numbers As Decorative**

NEVER add figures without linking to unit economics or validation plans. MUST treat every economic figure as testable hypothesis.

**Never Updating The Canvas**

NEVER create once and forget. MUST version the canvas and update when assumptions are validated or falsified.

---

## Integration

**Prerequisites:** MUST complete Working Backwards PR/FAQ, JTBD analysis, Problem-Solution Fit Canvas, project memo, and M1 founder log.

**Builds On:**

| Framework | Output Used | How Used |
|-----------|-------------|----------|
| Working Backwards (PR/FAQ) | Customer and problem narratives, promises, internal assumptions | Seeds Problem, Customer Segments, UVP, Solution, and early economics/feasibility thinking |
| Jobs-To-Be-Done | Jobs, forces, job map, alternatives | Grounds Problem, Customer Segments, Channels, and Key Metrics in real behaviours |
| Problem-Solution Fit Canvas | Problem, behaviours, constraints, Our Solution, Critical Assumptions | Anchors Problem, Solution, Channels, and economic assumptions in a specific context |
| 5 Whys (if already run) | Root Cause Map, targeted root cause hypotheses | Refines Problem and Key Metrics to track changes at the right level |
| Project memo and M1 founder log | Narrative and decision history | Provide context for scope choices, trade-offs, and versioning |

**Feeds Into:**

| Framework | Output Provided | How Used |
|-----------|-----------------|----------|
| 5 Whys | Refined Problem and Key Metrics | Ensures root-cause analysis targets the right symptoms and metrics |
| M2 Leap Of Faith / Assumption Mapping | Tagged canvas assumptions | Seeds validation backlog with business model hypotheses |
| TAM/SAM/SOM & Unit Economics (M2) | Segments, revenue/cost hypotheses, metrics | Provide input structure and starting values for financial models |
| M5 Market Validation frameworks (SPIN, Smoke Tests, PMF, pricing experiments) | UVP, channels, revenue model, key metrics | Guide design of experiments and customer conversations |
| Project memo | Updated Problem, Solution, Tenets, Progress > Conception | Aligns narrative with the current business model hypothesis |
| M4/M6 product and GTM planning | Segments, channels, metrics, unfair advantage | Inform roadmap, go-to-market strategy, and prioritisation frameworks |

**Workflow Position:** Within M1 Conception, Lean Canvas sits after Working Backwards, JTBD, and Problem-Solution Fit, and before or alongside 5 Whys.

---

## Success Criteria

This framework is complete when:

- [ ] A project-level Lean Canvas document exists under `[project]/docs/founder/conception/` with all nine blocks populated and a clear scope and version tag.
- [ ] Problem and Customer Segments blocks can be traced directly to PR/FAQ, JTBD, and Problem-Solution Fit artefacts.
- [ ] Channels, Revenue Streams, and Cost Structure form a coherent, testable digital business model hypothesis.
- [ ] Key Metrics and Unfair Advantage are specific, plausible for your stage, and tied to later validation plans.
- [ ] A tagged Assumptions List exists and is referenced by M2/M5 frameworks and financial models.
- [ ] The project memo and M1 founder log have been updated to reflect the current Lean Canvas and its main assumptions.

---

## References

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1–10 | Threshold: TS ≥ 6

Sources consulted when designing this framework:

- [1] Lean Canvas — `https://en.wikipedia.org/wiki/Lean_Canvas` — Research Date: 2025-12-21 — Source Date: n/a — TS: 8 (AT: 7, TR: 8, TM: 9)
- [2] Lean Canvas Vs Business Model Canvas — `https://startupply.io/blog/lean-canvas-vs-bmc` — Research Date: 2025-12-21 — Source Date: n/a — TS: 6.7 (AT: 6, TR: 6, TM: 8; TR penalised −1 for marketing language)
- [3] How To Create A Lean Canvas — `https://xtensio.com/how-to-create-a-lean-canvas/` — Research Date: 2025-12-21 — Source Date: n/a — TS: 6.7 (AT: 6, TR: 6, TM: 8; TR penalised −1 for marketing language)

Additional conceptual references (books, not scored):

- Ash Maurya, *Running Lean: Iterate from Plan A to a Plan That Works* (O'Reilly, 2012).
- Alexander Osterwalder & Yves Pigneur, *Business Model Generation* (Wiley, 2010).

### Sources Discarded

The following sources were reviewed but not used because they did not meet the TS ≥ 6 threshold:

| Source | TS | Reason |
|--------|----|--------|
| [Lean Canvas Template – Canva](https://www.canva.com/online-whiteboard/lean-canvas/) | 5.3 (AT: 5, TR: 4, TM: 7; TR penalised −2 for marketing language) | Primarily promotional template page; limited additional conceptual depth |

---

## For AI Agents

**Execution Context:** When executing this framework with a user:

1. MUST confirm that Working Backwards, JTBD, and Problem-Solution Fit exist. If not, MUST create minimal versions before proceeding.
2. MUST read this framework and `conception_process.md` before starting. Track progress explicitly: "Currently in Task [N]: [Task Name]".
3. MUST treat every Lean Canvas block as hypothesis container. Push user to articulate explicit assumptions and tag them for M2/M5.
4. MUST keep Lean Canvas synchronized with project memo, Problem-Solution Fit, 5 Whys, and validation artefacts. Propose concrete updates when changing blocks.
5. MUST encourage user to version canvas and log major changes in M1 founder log.

**Working With Tasks:**

- MUST treat each task as atomic. NEVER skip validation criteria without recording explicit risks or TODOs.
- When user wants rapid snapshot only, MUST use separate Lean Canvas Quick framework first, then return to this deep framework.
- When significant new evidence appears in M2/M5, MUST propose new Lean Canvas version and guide user through updating affected blocks and assumptions.

---