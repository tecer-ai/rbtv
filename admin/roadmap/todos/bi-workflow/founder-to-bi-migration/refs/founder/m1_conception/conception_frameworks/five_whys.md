---
---

# Five Whys (Root Cause Analysis)

**Purpose:** Task-based guide for using 5 Whys technique to uncover root causes of customer problems in M1 Conception Step 6.

**Context:**  
Read [conception_process.md](system/founder/m1_conception/conception_process.md) before starting. Apply 5 Whys to a single, concrete problem statement and scenario.

---

## Framework Overview

Trace visible problems to structural root causes by iteratively asking "Why?" and recording each answer as a causal chain link.

**Core principles:**

- Anchor on one concrete scenario
- Surface structural causes (incentives, processes, constraints), never blame individuals
- Separate facts from hypotheses
- Mark validation requirements for M2 and M5

---

## Task Structure

High-level view of framework execution:

| Task | Goal | Key Inputs | Key Outputs |
|------|------|------------|-------------|
| 1. Select And Frame The Problem Scenario | Choose a single, precise problem statement and scenario grounded in prior M1 artefacts | PR/FAQ, JTBD, Problem-Solution Fit, Lean Canvas, project memo | Anchor Problem Statement, Scenario Brief |
| 2. Design The 5 Whys Session | Define participants, rules, and structure so the analysis is disciplined, not a free-form debate | Anchor Problem Statement, Scenario Brief, data snippets | 5 Whys Session Plan and Chain Template |
| 3. Run 5 Whys Chains And Capture Evidence | Execute 5 Whys on the chosen scenario, capturing causal chains and evidence | Session Plan, data, team insights | One or more documented 5 Whys chains with fact/hypothesis tags |
| 4. Synthesize Root Causes And Select Levers | Turn chains into a small, prioritized set of root causes and levers your concept will address | 5 Whys chains, core M1 artefacts | Root Cause Map and Targeted Root Cause Hypotheses |
| 5. Wire Root Causes Into M1 And M2 Artefacts | Embed root causes into project memo, Lean Canvas, founder log, and validation backlog | Root Cause Map, existing M1 documents | five_whys.md, updated memo/log, inputs to M2/M5 validation work |

---

## Task 1: Select And Frame The Problem Scenario

**Goal:** Produce a single, unambiguous Anchor Problem Statement and Scenario Brief.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Working Backwards PR/FAQ (Press Release + External/Internal FAQs) | M1 Working Backwards framework | Yes |
| JTBD analysis (jobs, struggling moments, current alternatives) | M1 Step 3 artefact | Yes |
| Problem-Solution Fit Canvas | [problem_solution_fit.md](system/founder/m1_conception/conception_frameworks/problem_solution_fit.md) | Yes |
| Lean Canvas (draft) | M1 Step 5 artefact | Yes (even if incomplete) |
| Project memo (Problem and Solution drafts) | M1 Step 1 and Step 7 (in progress) | No but recommended |
| M1 Conception process doc | [conception_process.md](system/founder/m1_conception/conception_process.md) | Yes |

**Action:**

1. From the PR/FAQ, extract:
   - The primary **customer and problem** as written in the Press Release.
   - The **objections and edge cases** in the External FAQ.
   - The key **assumptions and risks** in the Internal FAQ.
2. From JTBD and Problem-Solution Fit:
   - Identify **1–3 recurring "struggling moments"** where the problem is most acute.
   - List the **current alternatives and behaviours** in those moments.
3. From the Lean Canvas:
   - Review the **Problem** and **Customer Segments** blocks.
   - Note any **metrics or symptoms** (for example, low activation, churn, manual workload).
4. Choose **one primary scenario** to analyse with 5 Whys:
   - One customer segment (for example, "product managers at B2B SaaS companies with 50–200 employees").
   - One recurring situation (for example, "end of month reporting when assembling data from 5 tools").
5. Draft an **Anchor Problem Statement** (one or two sentences) that:
   - Describes the problem **as experienced in that scenario**, not as a generic market category.
   - Does not mention your product; it must make sense even if your solution did not exist.
6. Write a short **Scenario Brief** (5–8 sentences) capturing:
   - Who is involved, when it happens, what tools/processes are in play.
   - What "bad outcome" they are trying to avoid or mitigate.
   - Any relevant constraints (budget, time, approvals, skills).

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Anchor Problem Statement | 1–2 sentences at top of five_whys.md | Ensures all whys refer to the same, precise problem |
| Scenario Brief | Short narrative block | Locks 5 Whys to a real situation, not an abstract idea |

**Validation:**

- [ ] You can name **at least three real organisations or people** who fit the scenario.
- [ ] A neutral reader can restate the problem and scenario without seeing any other document.
- [ ] The Anchor Problem Statement is directly traceable to the Problem blocks in PR/FAQ, JTBD, Problem-Solution Fit, and Lean Canvas.
- [ ] You are analysing **one scenario only**; other scenarios are explicitly parked for later.

---

## Task 2: Design The 5 Whys Session

**Goal:** Design a focused 5 Whys session (or solo analysis) that will produce disciplined causal chains.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Anchor Problem Statement | Task 1 | Yes |
| Scenario Brief | Task 1 | Yes |
| Key qualitative and quantitative signals (if available) | Product analytics, customer interviews, market observations | No but strongly recommended |
| Team roster and roles | Founder/team | No but recommended |

**Action:**

1. Decide **who participates**:
   - Minimum: founder plus one person who can challenge assumptions.
   - Ideal for a digital startup: cross-functional mix (product, design, engineering, go-to-market) if available.
2. Define **session rules** and write them at the top of the working document:
   - Focus on **this specific scenario only**; if a different scenario appears, park it.
   - **Blame processes, structures, incentives, and assumptions, never individuals.**
   - Each answer to "why?" must be a **direct cause** of the previous answer, not a different problem.
   - Mark each answer as **Fact** (supported by data or direct observation) or **Hypothesis** (to be validated).
   - Stop when you reach a **structural cause** that is actionable.
3. Design your **5 Whys Chain Template**. At minimum, define columns:
   - Level (1 to 5+).
   - Why question.
   - Answer.
   - Fact/Hypothesis flag.
   - Evidence or data source.
   - Notes / follow-up ideas.
4. Decide if you need **multiple chains**:
   - If there are clearly different symptomatic expressions (for example, "customers churn after month 1" vs "sales cycles stall before contract"), plan **one chain per symptom** rooted in the same Anchor Problem Statement.
5. Schedule a **time-boxed session** (for example, 45–60 minutes per main chain) and share the Anchor Problem Statement, Scenario Brief, and rules in advance.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| 5 Whys Session Plan | Short section in five_whys.md or separate note | Aligns participants on scope, rules, and expectations |
| 5 Whys Chain Template | Table structure in five_whys.md | Ensures consistent capture of questions, answers, and evidence |

**Validation:**

- [ ] Session rules are written down and visible to all participants.
- [ ] The Chain Template has a place to distinguish **facts vs hypotheses** and to link to evidence.
- [ ] There is a clear decision on whether you will run one chain or multiple chains.
- [ ] Everyone invited to the session has seen the Anchor Problem Statement and Scenario Brief.

---

## Task 3: Run 5 Whys Chains And Capture Evidence

**Goal:** Execute one or more 5 Whys chains, capturing a clear causal narrative and separating facts from assumptions.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| 5 Whys Session Plan | Task 2 | Yes |
| 5 Whys Chain Template | Task 2 | Yes |
| Anchor Problem Statement and Scenario Brief | Task 1 | Yes |
| Available data and examples | Product analytics, user interviews, founder experience | No but strongly recommended |

**Action:**

1. For each planned chain, write the **Problem (Level 0)** at the top using the Anchor Problem Statement.
2. Ask the first question: **"Why is this problem happening in this scenario?"**
   - Capture the answer in the template, including who said it.
   - Immediately label it as **Fact** or **Hypothesis** and note any data source.
3. For each subsequent level:
   - Formulate the next question as **"Why is [previous answer] true in this scenario?"**
   - Reject answers that jump to a different topic; keep the chain **single-threaded**.
   - If participants strongly disagree, fork into a **second chain** rather than averaging.
4. Continue until one of these conditions is met:
   - You reach a **structural cause** (for example, incentive structure, pricing model, organisational process, missing capability) that clearly explains the upstream symptoms.
   - Additional whys only repeat the same idea with different words.
   - You hit a point where all further answers are labelled **Hypothesis** with no way to test them soon; mark this as a **knowledge frontier**.
5. For each chain, summarise the **terminal node(s)** as a draft **Root Cause Candidate**, expressed in plain language (for example, "Our onboarding assumes data is clean and centralised, but in this segment it is fragmented across four tools and nobody owns consolidation.").
6. Review all chains at the end of the session:
   - Highlight which links are **well-supported by data** vs purely speculative.
   - Note any **patterns** where different chains converge on similar underlying issues.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Completed 5 Whys chains | Tables in five_whys.md | Provide a transparent causal narrative for each symptom |
| Root Cause Candidates list | Bulleted list summarising chain endpoints | Raw material for synthesis and prioritisation |

**Validation:**

- [ ] Each chain is a **linear sequence of causes**; there are no skipped levels or topic jumps.
- [ ] Every answer is marked as **Fact** or **Hypothesis**, with evidence noted where available.
- [ ] At least one chain reaches a **structural cause** that is more fundamental than "users do not care" or "team is slow".
- [ ] You can explain how each chain maps back to the Problem blocks in PR/FAQ, Problem-Solution Fit, and Lean Canvas.

---

## Task 4: Synthesize Root Causes And Select Levers

**Goal:** Convert raw 5 Whys chains into a concise Root Cause Map and decide which causes your initial concept will deliberately address.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Completed 5 Whys chains and Root Cause Candidates | Task 3 | Yes |
| Problem-Solution Fit Canvas | [problem_solution_fit.md](system/founder/m1_conception/conception_frameworks/problem_solution_fit.md) | Yes |
| Lean Canvas | M1 Step 5 artefact | Yes |
| Working Backwards PR/FAQ | M1 Working Backwards framework | Yes |
| JTBD analysis | M1 Step 3 artefact | Yes |

**Action:**

1. List all **Root Cause Candidates** from the chain endpoints.
2. Cluster them into **categories** such as:
   - Customer behaviour and context (for example, habits, incentives, skills, workflows).
   - Product and UX (for example, discovery, onboarding, feedback loops).
   - Business model and pricing (for example, misaligned incentives, long approvals).
   - Go-to-market and channels (for example, wrong decision-maker targeted, weak trust signals).
   - Organisation and operations (for example, internal bottlenecks that slow iteration).
   - External constraints (for example, regulation, vendor lock-in).
3. For each cluster, define a **Root Cause Statement** in one or two sentences:
   - Describe what is structurally true about the world that creates the observed symptoms.
   - Avoid blaming individuals; focus on systems, incentives, and constraints.
4. Map each Root Cause Statement back to existing artefacts:
   - Where does it already appear (explicitly or implicitly) in PR/FAQ, JTBD, Problem-Solution Fit, or Lean Canvas?
   - Where does it **contradict or refine** earlier assumptions?
5. Decide which root causes your **initial product concept will target**:
   - Mark 3–5 **Targeted Root Cause Hypotheses**: "If we change X, we expect Y problem to reduce in this scenario."
   - Mark important **Non-Targeted Root Causes** you will **live with** for now (for example, "We are not solving data governance in v1.").
6. Create a simple **Root Cause Map** table with columns:
   - Root Cause ID and statement.
   - Category.
   - Targeted vs non-targeted.
   - Related Lean Canvas blocks (Problem, UVP, Solution, Key Metrics, Channels, Unfair Advantage).
   - Notes on evidence vs hypothesis.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Root Cause Map | Table in five_whys.md | Connects chains to a coherent set of structural causes and categories |
| Targeted Root Cause Hypotheses list | Short labelled list | Clarifies what the initial product is actually trying to change |

**Validation:**

- [ ] At least one Root Cause Statement is **non-obvious** compared to the initial problem description.
- [ ] Each Targeted Root Cause Hypothesis can be linked to **specific behaviours or metrics** you expect to change.
- [ ] You have explicitly documented at least one **Non-Targeted Root Cause** you are choosing not to tackle in early versions.
- [ ] Updates implied by the Root Cause Map are reflected in Problem-Solution Fit and Lean Canvas drafts (even as TODOs).

---

## Task 5: Wire Root Causes Into M1 And M2 Artefacts

**Goal:** Feed 5 Whys outputs directly into the project memo, founder log, and validation/market work.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Root Cause Map and Targeted Root Cause Hypotheses | Task 4 | Yes |
| Completed 5 Whys chains | Task 3 | Yes |
| Project memo | M1 Step 1 and Step 7 | Yes |
| Lean Canvas | M1 Step 5 artefact | Yes |
| Problem-Solution Fit Canvas | [problem_solution_fit.md](system/founder/m1_conception/conception_frameworks/problem_solution_fit.md) | Yes |
| M1 founder diary | `[project]/docs/founder/conception/m1_founder_diary.md` | Yes |
| M2 Validation process and frameworks (for planning) | [validation_process.md](system/founder/m2_validation/validation_process.md) and related frameworks | No but recommended |

**Action:**

1. Create or update the **five_whys.md** in your project:
   - Save under `[project]/docs/founder/conception/five_whys.md`.
   - Include sections for Anchor Problem Statement, Scenario Brief, 5 Whys chains, Root Cause Map, and Targeted Root Cause Hypotheses.
2. Update the **project memo**:
   - Problem section: incorporate key Root Cause Statements that explain why the problem exists and persists.
   - Solution section: make explicit which root causes the proposed solution is designed to address.
   - Tenets section: add any guiding principles that emerge (for example, "We fix structural causes, not just surface friction X.").
3. Update the **Lean Canvas**:
   - Refine the **Problem** block to reflect the structural causes, not just symptoms.
   - Adjust **Key Metrics** to track whether targeted root causes are actually moving (for example, setup completion rates, time-to-value).
   - Revisit **UVP** and **Unfair Advantage** if understanding root causes changes what is truly differentiated.
4. Update the **Problem-Solution Fit Canvas**:
   - Reflect newly understood constraints or behaviours uncovered by 5 Whys.
   - Adjust **Critical Assumptions** to include root-cause-level hypotheses (for example, "Teams will centralise data if we provide X.").
5. Update the **M1 founder log**:
   - Add entries summarising the main Root Cause Statements and which ones you chose to target.
   - Record any **pivots** in problem framing or solution concept that resulted from the analysis.
6. Seed **M2 and M5 validation work**:
   - Translate Targeted Root Cause Hypotheses into **Leap of Faith** or Assumption Mapping entries.
   - Note which future experiments (for example, JTBD interviews, smoke tests, pricing experiments) will directly test whether you are shifting the root causes you chose.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Project five_whys.md | Markdown document in project founder/conception folder | Canonical record of root cause analysis for M1 |
| Updated project memo, Lean Canvas, Problem-Solution Fit, and founder log | artefacts | Ensures root cause insights propagate through the conception narrative and models |
| Initial validation backlog entries | Items in M2/M5 frameworks | Connects 5 Whys directly to future experiments and metrics |

**Validation:**

- [ ] A complete 5 Whys analysis document exists at `[project]/docs/founder/conception/five_whys.md`.
- [ ] The project memo's Problem and Solution sections explicitly reference key root causes.
- [ ] Lean Canvas and Problem-Solution Fit both reflect the same underlying root causes and targeted levers.
- [ ] The M1 founder log contains at least one entry summarising what you learned from 5 Whys and what you decided to do about it.
- [ ] There are explicit links from Targeted Root Cause Hypotheses to planned M2/M5 validation activities.

---

## Pitfalls

**Stopping At Three Whys Because The Meeting Is Over**

Busy teams often rush through the exercise, stopping after two or three whys once they hit a cause that feels "actionable" (for example, "onboarding is confusing"). This leaves deeper structural causes (like misaligned incentives, data fragmentation, or channel selection) unexplored, so you end up optimising surface UX while the real blocker remains. Instead: time-box properly, and push at least one chain per scenario to a structural cause you are slightly uncomfortable to write down.

**Blaming People Instead Of Systems**

Force every answer to be about **structures, policies, incentives, workflows, skills, or information**, not about personal character.

**Mixing Multiple Problems In One Chain**

Keep each chain anchored to the Anchor Problem Statement and single scenario; when a genuinely different problem appears, fork a new chain rather than merging them.

**Ignoring Evidence And Treating All Whys As Equal**

Label each answer as Fact or Hypothesis, attach data where possible, and deliberately prioritise chains supported by real user behaviour or metrics.

**Using 5 Whys As A One-Off Ritual**

Treat the five_whys.md as a living hypothesis document; update or version it when major assumptions are validated or falsified, and log the changes in the founder log.

**Applying 5 Whys To Fuzzy, Unbounded Topics**

Always narrow to a specific scenario, metric, and segment (for example, "Why do trial users from segment X not complete onboarding within seven days?") before starting the chain.

---

## Integration

**Prerequisites:**  
Read [conception_process.md](system/founder/m1_conception/conception_process.md).

**Builds on:**

| Framework | Output Used | How Used |
|-----------|-------------|----------|
| Working Backwards (PR/FAQ) | Customer and problem narratives, External/Internal FAQs | Provides starting problem statements, objections, and internal assumptions to test |
| Jobs-To-Be-Done | Jobs, struggling moments, current alternatives | Supplies concrete scenarios and behaviours for Anchor Problem Statement and Scenario Brief |
| Problem-Solution Fit Canvas | Problem, behaviours, constraints, critical assumptions | Anchors 5 Whys on a well-defined problem and exposes assumptions at the problem-solution boundary |
| Lean Canvas | Problem, Customer Segments, Key Metrics | Identifies key symptoms and metrics that 5 Whys must explain |
| Project memo and M1 founder log | Narrative and decision history | Provide context for how the problem has been framed so far and where pivots have occurred |

**Feeds into:**

| Framework | Output Provided | How Used |
|-----------|-----------------|----------|
| Project memo | Refined problem narrative, explicit root causes, updated tenets | Ensures the conception narrative reflects structural causes, not just symptoms |
| Lean Canvas | Refined Problem and Key Metrics, UVP/Unfair Advantage nuances | Aligns model blocks with the real levers you plan to move |
| Problem-Solution Fit Canvas | Updated constraints and critical assumptions | Deepens understanding of why the solution fits (or does not fit) the problem |
| M1 founder log | Documented root causes and decisions about what to target | Creates an auditable trail of how and why you chose these levers |
| M2 Validation frameworks | Targeted Root Cause Hypotheses and evidence gaps | Seed experiments and models that test whether you are really moving the root causes |
| M5 Market Validation frameworks | Hypotheses about which root causes drive adoption and retention | Inform design of tests that check if addressing these causes changes customer behaviour |

**Workflow Position:**

5 Whys sits after Working Backwards, JTBD, and Problem-Solution Fit and alongside or just after the first Lean Canvas draft.

---

## Success Criteria

- [ ] A project-level `five_whys.md` exists under `[project]/docs/founder/conception/` with at least one fully documented 5 Whys chain for a specific scenario.
- [ ] The Anchor Problem Statement and Scenario Brief can be traced back to PR/FAQ, JTBD, Problem-Solution Fit, and Lean Canvas without contradictions.
- [ ] A Root Cause Map and a list of Targeted vs Non-Targeted Root Cause Hypotheses are documented.
- [ ] The project memo, Lean Canvas, Problem-Solution Fit Canvas, and M1 founder log have been updated to reflect the root causes and resulting decisions.
- [ ] At least one M2/M5 validation activity explicitly references a Targeted Root Cause Hypothesis from this analysis.

---

## References

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6

[1] Five Whys — https://en.wikipedia.org/wiki/Five_whys — 2025-12-21 — 2023-01-01 — TS:8.7 (AT:9.0 TR:9.0 TM:8.0)  
[2] 5 Whys for Incident Postmortems — https://www.atlassian.com/incident-management/postmortem/5-whys — 2025-12-21 — 2022-06-01 — TS:8.0 (AT:8.0 TR:8.0 TM:8.0)  
[3] The Power Of The 5 Whys: A Guide To Effective Problem Solving And Continuous Improvement — https://www.gestaldt.com/insights/the-power-of-the-5-whys-a-guide-to-effective-problem-solving-and-continuous-improvement — 2025-12-21 — 2021-09-01 — TS:7.3 (AT:7.0 TR:7.0 TM:8.0)

---

## For AI Agents

**Execution Context:**

1. Read [conception_process.md](system/founder/m1_conception/conception_process.md) before starting.
2. Track progress: "Currently in Task [N]: [Task Name]".
3. Enforce session rules: one scenario per chain, never blame individuals, label Fact vs Hypothesis with data references.
4. Connect chain endpoints to PR/FAQ, JTBD, Problem-Solution Fit, Lean Canvas, project memo.

**Working With Tasks:**

- Complete each task atomically; note explicit TODOs when validation criteria are unmet.
- When chains stall in speculation, recommend M2/M5 data gathering activities.
- Log root cause insights and decisions in M1 founder diary; version five_whys.md when assumptions are validated.

---

