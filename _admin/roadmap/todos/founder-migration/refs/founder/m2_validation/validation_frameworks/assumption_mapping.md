---
---

# Assumption Mapping

**Purpose:** Plot all business assumptions on an Importance x Uncertainty matrix and decide for each: Test, Accept, Monitor, or Ignore. Produces a prioritized validation backlog with lightweight test designs for the highest-risk assumptions.

**Context:** Use in M2 Validation, Step 3. MUST complete Leap of Faith (Step 2) first. Leap of Faith provides the prioritized assumption inventory; Assumption Mapping gives each assumption a spatial position and an action decision.

---

## Framework Overview

Assumption Mapping converts a flat list of assumptions into a visual decision tool. Every assumption from Leap of Faith is rated on two axes: how important it is to the business model (if wrong, how much damage?) and how uncertain it currently is (how little evidence do we have?). The intersection determines what you do next. High importance + high uncertainty assumptions must be tested immediately. High importance + low uncertainty assumptions can be accepted with a note to revisit. Low importance + high uncertainty assumptions should be monitored passively. Low importance + low uncertainty assumptions can be safely ignored.

The power of the matrix is triage speed. Founders waste months testing assumptions that do not matter or accepting assumptions that could kill the business. By forcing a two-dimensional rating before designing any test, you prevent both over-engineering validation (testing things you already know) and under-engineering it (accepting things you should not). The output is a concrete backlog of lightweight tests, each with a clear hypothesis, method, success signal, and timeline.

This framework bridges the gap between Leap of Faith's prioritized list and the specific validation work done in TAM/SAM/SOM, Unit Economics, TRL, and Pre-mortem. Those downstream frameworks consume the "Test" assumptions and produce evidence that updates the map over time.

---

## Task Structure

High-level view of framework execution:

| Task | Goal | Key Inputs | Key Outputs |
|------|------|------------|-------------|
| 1. Collect and Normalize Assumptions | Build a single, deduplicated assumption inventory with consistent metadata | Leap of Faith analysis, all M1 framework assumptions | Normalized assumption inventory with source, category, and initial confidence |
| 2. Rate Importance and Uncertainty | Score each assumption on both axes using structured criteria | Normalized assumption inventory, Leap of Faith priority rankings | Scored assumption table (importance 1-5, uncertainty 1-5) |
| 3. Plot Matrix and Assign Actions | Place assumptions on the 2x2 matrix and decide Test/Accept/Monitor/Ignore | Scored assumption table | Visual matrix, action assignment per assumption |
| 4. Design Lightweight Tests | Create a test card for each "Test" assumption with hypothesis, method, signal, and timeline | "Test" assumptions from matrix, M2 framework references | Test cards with success/failure criteria, validation backlog |
| 5. Document and Wire into Validation Backlog | Finalize the assumption map artifact and connect to downstream frameworks and project memo | Complete matrix, test cards, project memo, M2 founder diary | Saved assumption map document, updated project memo, validation backlog entries |

---

## Task 1: Collect and Normalize Assumptions

**Goal:** Build a single, deduplicated assumption inventory from Leap of Faith and all M1 sources, with consistent metadata for scoring.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Leap of Faith analysis (prioritized assumptions, value/growth hypothesis classification) | M2 Step 2 output | Yes |
| Lean Canvas tagged assumptions (P1, CS2, UVP1, CH1, REV2, COST1, etc.) | M1 Lean Canvas | Yes |
| Problem-Solution Fit critical assumptions | M1 Problem-Solution Fit Canvas | Yes |
| Working Backwards Internal FAQ assumptions | M1 Working Backwards | Yes |
| 5 Whys root cause hypotheses | M1 5 Whys | No |
| Consolidated assumption inventory from M2 Step 1 | M2 initialization | Yes |

**Action:**

1. Start from the consolidated assumption inventory created in M2 Step 1. This is your base list.
2. Cross-reference with Leap of Faith output. Add any assumptions that emerged during Leap of Faith classification but were not in the original inventory.
3. Deduplicate. Merge assumptions that say the same thing in different words. Keep the clearest phrasing. Note all source frameworks in metadata.
4. For each assumption, record:
   - **ID:** Short label (e.g., AM-01, AM-02).
   - **Statement:** One sentence starting with "We assume that..."
   - **Category:** Behavioural, Technical, or Economic.
   - **Leap of Faith class:** Value Hypothesis, Growth Hypothesis, or Neither.
   - **Source frameworks:** Which M1/M2 frameworks surfaced this assumption.
   - **Current evidence:** What you already know (interviews, data, logic, nothing).
   - **Initial confidence:** High, Medium, or Low based on current evidence.
5. Sort the inventory by Leap of Faith priority first, then by category.
6. Count total assumptions. If more than 25, consolidate related assumptions into clusters. If fewer than 8, go back to M1 frameworks and check for hidden assumptions.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Normalized assumption inventory | Table with ID, statement, category, LoF class, sources, evidence, confidence | Single source of truth for all assumptions entering the matrix |

**Validation:**

- [ ] Every assumption from Leap of Faith appears in the inventory (no orphans).
- [ ] Each assumption has exactly one category (Behavioural, Technical, or Economic) and one Leap of Faith class.
- [ ] Duplicates are merged, and merged entries note all source frameworks.
- [ ] Total assumption count is between 8 and 25. If outside this range, you consolidated or expanded.
- [ ] A neutral reader can understand each assumption statement without referring to source documents.

---

## Task 2: Rate Importance and Uncertainty

**Goal:** Score each assumption on Importance (1-5) and Uncertainty (1-5) using explicit, repeatable criteria.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Normalized assumption inventory | Task 1 | Yes |
| Leap of Faith priority rankings and kill criteria | M2 Leap of Faith | Yes |
| Founder domain knowledge and any existing evidence | Founder, research notes | Yes |

**Action:**

1. Define the **Importance** scale (use these anchors consistently):
   - **5 — Fatal if wrong:** Business model collapses. Matches Leap of Faith kill criteria.
   - **4 — Severe:** Major pivot required. Revenue model or core value proposition breaks.
   - **3 — Significant:** Important feature, channel, or cost assumption fails. Workaround possible but painful.
   - **2 — Moderate:** Secondary assumption. Affects efficiency or timeline, not viability.
   - **1 — Minor:** Nice-to-know. No material impact on go/no-go decision.
2. Define the **Uncertainty** scale (use these anchors consistently):
   - **5 — No evidence:** Pure guess. No data, no interviews, no analogies.
   - **4 — Weak signal:** One anecdote, one data point, or founder intuition only.
   - **3 — Mixed signals:** Some evidence supports, some contradicts. Or evidence is indirect.
   - **2 — Moderate evidence:** Multiple data points or interviews support. Minor gaps remain.
   - **1 — Strong evidence:** Robust data, validated in adjacent markets, or already tested.
3. Score each assumption independently. Do not anchor on previous scores.
4. For assumptions tagged as Leap of Faith kill criteria, importance MUST be 4 or 5. If you scored lower, re-examine.
5. Record scores in the assumption inventory table. Add columns for Importance and Uncertainty.
6. Flag any assumption where Importance and Uncertainty are both 4 or 5. These are your highest-priority test targets.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Scored assumption table | Extended inventory table with Importance (1-5) and Uncertainty (1-5) columns | Input to matrix plotting in Task 3 |

**Validation:**

- [ ] Every assumption has both an Importance and Uncertainty score.
- [ ] Scores use the defined anchors, not gut feel. You can justify each score in one sentence.
- [ ] Leap of Faith kill criteria assumptions are scored Importance 4-5.
- [ ] At least two assumptions scored Importance 4+ and Uncertainty 4+. If not, you may be overconfident.
- [ ] No more than 30% of assumptions are scored Importance 5. If more, you have not differentiated enough.

---

## Task 3: Plot Matrix and Assign Actions

**Goal:** Place each assumption on the Importance x Uncertainty matrix and assign one of four actions: Test, Accept, Monitor, Ignore.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Scored assumption table | Task 2 | Yes |

**Action:**

1. Draw a 2x2 matrix with Importance on the Y-axis (low to high) and Uncertainty on the X-axis (low to high).
2. Define quadrant boundaries. Use the midpoint (score 3) as the dividing line:
   - **Top-right (Importance 3-5, Uncertainty 3-5): TEST.** Design and run a validation experiment.
   - **Top-left (Importance 3-5, Uncertainty 1-2): ACCEPT.** Treat as working assumption. Revisit if new contradictory evidence appears.
   - **Bottom-right (Importance 1-2, Uncertainty 3-5): MONITOR.** Track passively. If importance increases, move to Test.
   - **Bottom-left (Importance 1-2, Uncertainty 1-2): IGNORE.** No action needed. Remove from active tracking.
3. Place each assumption in its quadrant. Use the ID labels for readability.
4. Within the TEST quadrant, rank assumptions by combined score (Importance + Uncertainty). Highest combined score = test first.
5. For borderline assumptions (score 3 on one axis), default to the more cautious action: Test over Accept, Monitor over Ignore.
6. Record the action assignment in the assumption table. Add an "Action" column.
7. Count assumptions per quadrant. A healthy distribution for an early-stage startup: 20-40% Test, 20-30% Accept, 15-25% Monitor, 10-25% Ignore. If Test exceeds 50%, you have too many unknowns to proceed without significant de-risking.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Assumption matrix visualization | 2x2 grid with assumption IDs placed in quadrants | Visual overview of assumption risk landscape |
| Action-assigned assumption table | Extended table with Action column (Test/Accept/Monitor/Ignore) | Decision record for each assumption |
| Quadrant summary | Counts and percentages per quadrant | Health check on overall assumption risk profile |

**Validation:**

- [ ] Every assumption has exactly one action assignment.
- [ ] All Leap of Faith kill criteria assumptions are in the Test or Accept quadrant (never Monitor or Ignore).
- [ ] The TEST quadrant is rank-ordered by combined score.
- [ ] Quadrant distribution is plausible. If 80% are in Test, the concept may need more foundational work before proceeding.
- [ ] Borderline assumptions defaulted to the more cautious action.

---

## Task 4: Design Lightweight Tests

**Goal:** Create a test card for each "Test" assumption with a clear hypothesis, method, success/failure signal, and timeline.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| "Test" assumptions from matrix (ranked) | Task 3 | Yes |
| M2 downstream framework references (TAM/SAM/SOM, Unit Economics, TRL, Pre-mortem) | M2 validation_process.md | Yes |
| Leap of Faith observable signals and kill criteria | M2 Leap of Faith | Yes |

**Action:**

1. For each "Test" assumption (in rank order), create a **test card** containing:
   - **Assumption ID and statement.**
   - **Hypothesis:** Rewrite as "If [assumption] is true, then [observable outcome]."
   - **Test method:** Choose the lightest-weight method that produces credible evidence. Options include:
     - Desk research (market data, competitor analysis, public data).
     - Customer interviews (5-10 targeted conversations).
     - Landing page or smoke test (measure intent before building).
     - Technical spike or proof-of-concept (for technical assumptions).
     - Financial modeling with sensitivity analysis (for economic assumptions).
     - Expert consultation (for domain-specific unknowns).
   - **Success signal:** What specific evidence would validate the assumption? Be concrete. "3 of 5 interviewees describe this pain unprompted" not "people seem interested."
   - **Failure signal:** What evidence would invalidate it? Connect to Leap of Faith kill criteria where applicable.
   - **Timeline:** Maximum elapsed time for this test. Prefer days or weeks, not months.
   - **Owner:** Who runs this test (founder, team member, AI agent).
   - **Downstream framework:** Which M2 framework will consume this evidence (TAM/SAM/SOM, Unit Economics, TRL, Pre-mortem).
2. Where multiple "Test" assumptions can be validated by the same activity (e.g., a single interview round tests three assumptions), group them into a combined test card.
3. Sequence test cards: test the highest-ranked assumptions first. If one assumption's result changes the importance of others, note the dependency.
4. Total test timeline should not exceed 2-4 weeks for the full "Test" batch. If longer, cut scope or combine tests.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Test cards | Structured cards (one per test or test group) | Actionable validation experiments ready to execute |
| Validation backlog | Ordered list of test cards with timelines and owners | Execution plan for M2 validation work |
| Dependency notes | Annotations on test cards | Identifies sequencing constraints between tests |

**Validation:**

- [ ] Every "Test" assumption has at least one test card.
- [ ] Each test card has a concrete success signal and failure signal (not vague language).
- [ ] Test methods are the lightest weight that produce credible evidence. No over-engineering.
- [ ] Total estimated timeline for all tests is 2-4 weeks.
- [ ] At least one test card references Leap of Faith kill criteria as a failure signal.
- [ ] Each test card names the downstream M2 framework that will use the evidence.

---

## Task 5: Document and Wire into Validation Backlog

**Goal:** Finalize the assumption map as a project artifact and connect outputs to downstream frameworks, project memo, and M2 founder diary.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Complete assumption matrix and test cards | Tasks 1-4 | Yes |
| Project memo | `projects/[project]/founder/[project]_memo.md` | Yes |
| M2 founder diary | `projects/[project]/founder/validation/m2_founder_diary.md` | Yes |
| M2 validation_process.md | `validation_process.md` | Yes |

**Action:**

1. Create the assumption mapping document at `projects/[project]/founder/validation/assumption_mapping.md` containing:
   - Normalized assumption inventory (Task 1).
   - Scored table with Importance, Uncertainty, and Action columns (Tasks 2-3).
   - Matrix visualization (Task 3).
   - Test cards and validation backlog (Task 4).
2. Wire test cards into downstream M2 frameworks:
   - **TAM/SAM/SOM:** Flag economic assumptions about market size, segments, and pricing that need market sizing evidence.
   - **Unit Economics:** Flag assumptions about LTV, CAC, retention, and cost drivers.
   - **TRL:** Flag technical assumptions about feasibility, performance, and integration.
   - **Pre-mortem:** Flag all "Test" and "Accept" assumptions as potential failure modes.
3. Update **project memo** Progress > Validation subsection:
   - Note that assumption mapping is complete.
   - List top 3-5 assumptions in the Test quadrant with their test methods.
   - Update Open Questions with any new unknowns surfaced during mapping.
4. Update **M2 founder diary** with:
   - Entry recording the assumption mapping session, date, and key decisions.
   - Note any assumptions that were surprisingly high-importance or high-uncertainty.
   - Note any assumptions dropped or merged during normalization.
5. Share the validation backlog with anyone who will execute tests.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Assumption mapping document | Markdown in `projects/[project]/founder/validation/` | Canonical assumption risk map and test plan |
| Updated project memo | Updated Progress > Validation, Open Questions | Narrative integration of mapping results |
| Updated M2 founder diary | New entry with mapping decisions | Decision trail for assumption prioritization |
| Downstream framework inputs | Flagged assumptions per framework | Ensures TAM/SAM/SOM, Unit Economics, TRL, Pre-mortem receive relevant test targets |

**Validation:**

- [ ] Assumption mapping document exists with all sections (inventory, scores, matrix, test cards).
- [ ] Each "Test" assumption is linked to at least one downstream M2 framework.
- [ ] Project memo reflects top assumptions and their test status.
- [ ] M2 founder diary has at least one entry from this framework.
- [ ] Validation backlog is sequenced and has estimated timelines.

---

## Pitfalls

**Skipping Leap of Faith and Mapping Raw Assumptions**

NEVER start Assumption Mapping without a completed Leap of Faith analysis. Without Leap of Faith's value/growth hypothesis classification and kill criteria, you lack the context to rate importance accurately.

**Treating All Assumptions as Equally Important**

NEVER give every assumption an importance score of 4 or 5. This defeats the purpose of triage. MUST differentiate ruthlessly. If more than 30% of assumptions are scored Importance 5, you have not thought hard enough about which ones truly kill the business.

**Designing Heavy Tests**

NEVER design multi-month research projects for individual assumptions. MUST use the lightest-weight method that produces credible evidence. A 5-conversation interview round beats a 500-person survey for early-stage assumption testing.

**Ignoring the "Accept" Quadrant**

NEVER treat "Accept" as "proven." MUST note what new evidence would cause you to revisit accepted assumptions. Accepted assumptions can become test targets if circumstances change.

**Mapping Once and Never Updating**

NEVER treat the assumption map as a one-time artifact. MUST update the map as tests produce evidence. Move assumptions between quadrants when evidence shifts their importance or uncertainty.

---

## Integration

**Prerequisites:** MUST complete Leap of Faith (M2 Step 2). MUST have access to all M1 framework outputs.

**Builds on:**

| Framework | Output Used | How Used |
|-----------|-------------|----------|
| Leap of Faith (M2) | Prioritized assumptions, value/growth hypothesis classification, kill criteria, observable signals | Provides the raw assumption inventory and priority context for matrix scoring |
| Lean Canvas (M1) | Tagged per-block assumptions (P1, CS2, UVP1, etc.) | Supplies economic and business model assumptions |
| Problem-Solution Fit (M1) | Critical assumptions about customer behaviour and solution fit | Supplies behavioural assumptions |
| Working Backwards (M1) | Internal FAQ assumptions about feasibility and economics | Supplies technical and economic assumptions |
| 5 Whys (M1) | Root cause hypotheses | Supplies problem-level assumptions about underlying causes |

**Feeds into:**

| Framework | Output Provided | How Used |
|-----------|-----------------|----------|
| TAM/SAM/SOM (M2) | Economic assumptions flagged for market sizing validation | Identifies which market size assumptions need evidence |
| Unit Economics (M2) | Financial assumptions flagged for modeling | Identifies which LTV, CAC, retention assumptions to stress-test |
| Technology Readiness Level (M2) | Technical assumptions flagged for feasibility assessment | Identifies which technical risks need spikes or PoCs |
| Pre-mortem (M2) | All Test and Accept assumptions as potential failure modes | Seeds failure brainstorming with prioritized risk areas |
| M5 Market Validation | Test assumptions requiring customer evidence | Informs SPIN Selling questions and smoke test design |

**Workflow Position:** Within M2 Validation, Assumption Mapping sits immediately after Leap of Faith (Step 2) and before TAM/SAM/SOM (Step 4). It provides the structured backlog that all subsequent M2 frameworks draw from.

---

## Success Criteria

This framework is complete when:

- [ ] A normalized assumption inventory exists with 8-25 deduplicated assumptions, each with ID, statement, category, Leap of Faith class, sources, and current evidence.
- [ ] Every assumption has an Importance (1-5) and Uncertainty (1-5) score with justification.
- [ ] A 2x2 matrix visualization exists with all assumptions placed and action-assigned (Test/Accept/Monitor/Ignore).
- [ ] Every "Test" assumption has a test card with hypothesis, method, success signal, failure signal, timeline, and downstream framework reference.
- [ ] The validation backlog is sequenced and fits within 2-4 weeks of elapsed time.
- [ ] At least one test card connects to Leap of Faith kill criteria.
- [ ] The assumption mapping document is saved in the project validation folder.
- [ ] The project memo and M2 founder diary are updated with mapping results.

---

## References

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS >= 6

Sources consulted when designing this framework:

- [1] David J. Bland & Alex Osterwalder, *Testing Business Ideas* (Wiley, 2020) — Research Date: 2026-01-30 — Source Date: 2020 — TS: 8.7 (AT: 9, TR: 9, TM: 8). Primary source for the Importance x Uncertainty matrix and test card methodology.
- [2] Ash Maurya, *Running Lean: Iterate from Plan A to a Plan That Works*, 3rd ed. (O'Reilly, 2022) — Research Date: 2026-01-30 — Source Date: 2022 — TS: 8.0 (AT: 8, TR: 8, TM: 8). Leap of faith assumptions and lightweight validation methods.
- [3] Eric Ries, *The Lean Startup* (Crown, 2011) — Research Date: 2026-01-30 — Source Date: 2011 — TS: 7.7 (AT: 9, TR: 8, TM: 6). Foundational concept of leap of faith assumptions and build-measure-learn.

Additional conceptual references (books, not scored):

- Strategyzer, *Assumption Mapping* — `https://www.strategyzer.com/library/how-to-test-business-ideas-map-your-assumptions` — Practitioner guide to the Importance x Uncertainty matrix.

---

## For AI Agents

**Execution Context:** When executing this framework with a user:

1. MUST confirm that Leap of Faith analysis exists and is complete. If not, MUST run Leap of Faith first.
2. MUST read this framework and `validation_process.md` before starting. Track progress explicitly: "Currently in Task [N]: [Task Name]".
3. MUST push user to use the defined scoring anchors, not gut feel. Ask "What evidence supports this score?" for every Importance and Uncertainty rating.
4. MUST challenge if user scores more than 30% of assumptions at Importance 5. Force differentiation.
5. MUST ensure test cards specify concrete success and failure signals. Reject vague signals like "people seem interested" or "it looks promising."

**Working With Tasks:**

- MUST treat each task as atomic. NEVER skip validation criteria without recording explicit risks or TODOs.
- When user wants to skip directly to test design, MUST insist on completing scoring and matrix placement first. The matrix prevents wasted effort on low-priority tests.
- When test evidence arrives from downstream frameworks (TAM/SAM/SOM, Unit Economics, TRL), MUST propose updating the matrix by moving assumptions between quadrants.
- If total "Test" assumptions exceed 10, MUST help user ruthlessly prioritize to the top 5-7 that can be tested within 2-4 weeks.

---

