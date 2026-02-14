---
---

# Jobs-To-Be-Done Analysis

**Purpose:** Task-based guide for using JTBD to translate customer behavior and motivations into explicit jobs that a digital product is "hired" to do in M1 Conception Step 3.

**Context:**  
Read `conception_process.md` before starting. Execute in M1 Conception Step 3: Understand Customer's Progress Goal.

---

## Framework Overview

Customers do not simply "buy products"; they **hire** them to make progress in specific situations, relative to imperfect alternatives.

**Core concept:** When a person in a given context wants to achieve an outcome, they consider options (including spreadsheets, email, doing nothing) and "hire" the one that best balances functional, emotional, and social jobs.

---

## Task Structure

| Task | Goal | Key Inputs | Key Outputs |
|------|------|------------|-------------|
| 1. Frame Job Context From PR/FAQ | Turn the PR/FAQ into 3–5 explicit JTBD hypotheses | Working Backwards document, target customer hypotheses | Draft job statements (When / I want to / so I can) |
| 2. Design JTBD Research Plan And Interview Guide | Define who to interview and how, using timeline-based JTBD interviews | Job hypotheses, access to potential users | Recruitment criteria, screener, interview guide |
| 3. Run Jobs Interviews And Capture Timelines | Collect concrete stories that show how and why people "hire" solutions | Interview guide, recruited participants | Structured notes or transcripts with timelines and forces |
| 4. Synthesize Job Stories, Forces, And Job Map | Convert interview data into job stories, forces, and a job map | Interview notes, job hypotheses | Primary job stories, forces analysis, job map |
| 5. Prioritize Jobs And Produce JTBD Analysis Document | Select primary job(s) for M1 and document them to feed downstream frameworks | Synthesized jobs, forces, job map, PR/FAQ | JTBD analysis document and logged decisions/assumptions |

---

## Task 1: Frame Job Context From PR/FAQ

**Goal:** Turn the Working Backwards narrative into concrete, testable JTBD hypotheses.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Working Backwards PR/FAQ (Press Release + External/Internal FAQ) | `working_backwards.md` applied framework | Yes |
| Initial target customer hypotheses | M1 conception work (Step 1–2) | Yes |
| Early user anecdotes or founder experience stories | Founder memory, notes, emails, support threads | No |

**Action:**

1. Re-read the Press Release and External FAQ with a JTBD lens. Highlight any phrase where the customer is trying to achieve or avoid something (for example, "ship faster", "avoid errors", "prove impact", "feel in control").
2. For each highlighted phrase, answer explicitly:
   - In what **situation** does this matter? (time, trigger, context)
   - What **progress** is the customer trying to make from "current state" to "desired state"?
   - What happens if they **fail** to make this progress?
3. Draft 3–7 raw job statements using the canonical structure:
   - "When **[situation/trigger]**, I want to **[progress I am trying to make]**, so I can **[ultimate outcome]**."
4. Tag each draft job with its dominant type:
   - Functional (what they are doing),
   - Emotional (how they want to feel),
   - Social (how they want to be perceived).
5. Remove or merge jobs that are:
   - Just features in disguise (for example, "When I use the dashboard, I want to filter quickly"),
   - Too broad to be actionable in this product (for example, "grow my business" without a clear scope),
   - Duplicates that only differ in wording.
6. Select 3–5 sharp job hypotheses you want to stress-test via interviews.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Draft JTBD hypotheses | List of 3–5 job statements in "When / I want to / so I can" form | Provides a starting point for interviews and synthesis |

**Validation:**

- [ ] Each job can be explained **without** mentioning your product or any feature names.
- [ ] Each job includes a concrete **situation trigger** (for example, "end-of-month reporting") rather than just a demographic label.
- [ ] You can think of at least **three real people or organisations** who plausibly experience each job.
- [ ] Different jobs are meaningfully distinct in situation or progress, not just in wording.

---

## Task 2: Design JTBD Research Plan And Interview Guide

**Goal:** Set up rigorous, timeline-based interviews that surface real jobs and switching forces.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Draft JTBD hypotheses | Task 1 | Yes |
| Access to potential participants (recent adopters, switchers, non-users) | Founder network, early users, domain communities | Yes |
| Basic scheduling and recording tools | Calendar, video conference tool, recording (if allowed) | Yes |

**Action:**

1. Define target interview groups explicitly:
   - **Recent adopters** (started using your or a competing solution in the last 3–6 months),
   - **Switchers** (moved from one solution to another),
   - **Strugglers** (still using workarounds such as spreadsheets, email, manual processes).
2. Write recruitment criteria for each group (role, company size, industry, geography, tech stack, language) based on the primary customer from Working Backwards.
3. Draft a 3–5 question screener to confirm:
   - They have recently experienced the **situation** described in at least one job hypothesis,
   - They have tried **something** (any solution) to make progress,
   - They are willing to talk through a specific recent episode.
4. Design a **timeline-based interview guide** inspired by Christensen/Moesta switch interviews:
   - Opening: "Tell me about the last time you **[job situation]**. When was that?"
   - Trigger: "What changed that made this a problem worth addressing?"
   - Passive looking: "What did you try at first, casually, if anything?"
   - Active looking: "When did you decide you needed to find a better way? What did you look at?"
   - Deciding: "What made you choose solution X instead of Y or doing nothing?"
   - Consuming: "Walk me through how you used it the first few times."
5. Add probes to uncover functional, emotional, and social dimensions:
   - "How did you feel at that moment?",
   - "Who else cared whether this worked or failed?",
   - "What would have happened if you had done nothing?"
6. Remove leading and speculative questions. Replace prompts such as "Would feature X be useful?" with "How do you handle this today?" or "What did you actually do?"
7. Plan logistics: number of interviews (aim for at least 5–10), duration (45–60 minutes), recording approach, and note-taking template.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| JTBD research plan | Short document outlining targets, counts, and logistics | Keeps recruitment and execution aligned with goals |
| Interview screener | 3–5 question form or email template | Ensures participants match the jobs and situations you care about |
| Interview guide | Question flow and probes focused on real episodes | Standardises how interviews explore jobs and switching forces |

**Validation:**

- [ ] Every question in the guide can be answered with a **story about a real past event**, not a hypothetical.
- [ ] The guide can be used even if you **never** show your product or mention features.
- [ ] You cover at least **two distinct participant types** (for example, adopters and strugglers).
- [ ] You have a realistic plan to complete the planned number of interviews within the M1 timeline.

---

## Task 3: Run Jobs Interviews And Capture Timelines

**Goal:** Collect rich, chronological narratives that explain how and why people "hire" solutions to do the job.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Interview guide | Task 2 | Yes |
| Recruited participants | JTBD research plan and screener | Yes |
| Note-taking template | Custom template with sections for timeline and forces | Yes |

**Action:**

1. At the start of each interview, set expectations:
   - Clarify that you are not selling anything,
   - Explain that you want to reconstruct **one specific recent episode** in detail.
2. Anchor on a single concrete story:
   - "Think about the last time you **[job situation]**. When was that? Walk me through that day from the beginning."
3. Guide the conversation along the **timeline**:
   - **Trigger**: "What first happened that made you think you needed to deal with this?"
   - **Passive looking**: "What did you try casually at first, before making it a project?"
   - **Active looking**: "When did you decide 'I need to fix this now'? What did you search for? Who did you ask?"
   - **Deciding**: "What did you compare? What tipped the decision toward the option you chose?"
   - **Consuming**: "Show or describe what you did the first few times you used that option."
4. Capture the **forces** affecting the decision:
   - Push of the present (pains and frustrations with the current way),
   - Pull of the new solution (what was attractive about alternatives),
   - Anxieties (fears about adopting something new),
   - Habits (inertia and comfort with the status quo).
5. Take verbatim quotes for key moments (trigger, decision, unmet expectations, workarounds) and attribute them with context (role, company type, situation).
6. Avoid jumping to pitching or solutioning; when tempted, redirect to behavior:
   - "Before we get into ideas, walk me through what you actually did next."
7. Immediately after each interview, clean up notes while memory is fresh:
   - Clarify ambiguous parts of the timeline,
   - Tag recurring patterns (for example, same trigger, same workaround, same anxiety).

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Structured interview notes or transcripts | Document per participant, structured by timeline and forces | Raw material for synthesis of jobs, forces, and opportunities |

**Validation:**

- [ ] For each interview, you can reconstruct a **coherent story** from trigger through usage and aftermath.
- [ ] You can list at least **three alternative options** participants considered (including doing nothing).
- [ ] You have at least **5–10 structured interviews** across relevant participant types.
- [ ] You already see emerging **patterns in situations, progress sought, and forces**, even before formal clustering.

---

## Task 4: Synthesize Job Stories, Forces, And Job Map

**Goal:** Convert messy interview data into clear, reusable JTBD artifacts that describe situations, progress, forces, and stages of the job.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Structured interview notes or transcripts | Task 3 | Yes |
| Draft JTBD hypotheses | Task 1 | Yes |

**Action:**

1. Cluster interview episodes by similarity in:
   - Situation trigger (for example, "board meeting preparation", "month-end close", "feature launch"),
   - Type of customer (role, company size, environment),
   - Progress sought (what "better" looked like for them).
2. For each cluster, write a refined **job story**:
   - "When **[specific situation]**, I want to **[progress]**, so I can **[ultimate outcome]**."
3. Distinguish between:
   - **Main job**: the core progress they hire a solution for,
   - **Related jobs**: upstream and downstream tasks that may be out of scope initially,
   - **Emotional and social jobs**: how they want to feel and be perceived (for example, "feel in control", "look competent to my team").
4. For each main job, summarise the **forces**:
   - Push of the present (reasons to leave the status quo),
   - Pull of the new solution (reasons to adopt an alternative),
   - Anxieties (risks and doubts about new options),
   - Habits (reasons to stay with the current way).
5. Build a simple **job map** for the main job, listing the stages of progress. For digital products this often looks like:
   - Define (recognise and frame the problem),
   - Locate (find options and information),
   - Prepare (set up data, integrations, processes),
   - Execute (do the core work),
   - Confirm (check results, share with stakeholders),
   - Evolve (adjust process, refine setup).
   For each stage, note pain points and workarounds observed in interviews.
6. Compare these refined job stories and maps to the original hypotheses from Task 1 and explicitly document where reality diverged.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Primary job stories | List of 1–3 main job statements plus related/emotional/social jobs | Captures how customers describe progress in their own context |
| Forces analysis | Short document or table per job listing push, pull, anxieties, habits | Explains adoption, non-adoption, and switching behavior |
| Job map | Stage-by-stage description of how customers try to get the job done today | Identifies pain points and opportunity areas across the workflow |

**Validation:**

- [ ] You can point to **real interview quotes** that support each main job story.
- [ ] The job map is written in **customer language** and does not mirror your product UI structure.
- [ ] The forces analysis explains both **why some people switch** and **why others stay** with the status quo or another solution.
- [ ] When you read the Working Backwards PR/FAQ again, you can see exactly which claims are supported or challenged by the JTBD synthesis.

---

## Task 5: Prioritize Jobs And Produce JTBD Analysis Document

**Goal:** Decide which job(s) to focus on in M1 and document them to feed Problem-Solution Fit, Lean Canvas, and the project memo.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Primary job stories, forces analysis, job map | Task 4 | Yes |
| Working Backwards PR/FAQ | Applied framework in M1 | Yes |
| Team and resource constraints | Founder and core team | Yes |

**Action:**

1. For each primary job, assess qualitatively (or quantitatively if you have data):
   - **Importance** to the customer (how critical success or failure is),
   - **Current satisfaction** with existing alternatives,
   - **Strategic fit** with your mission, capabilities, and go-to-market.
2. Create a simple matrix or table that ranks jobs along importance and satisfaction (for example, high/medium/low or a 1–5 scale). Jobs that are **high importance and low satisfaction** are most attractive.
3. Select:
   - **One primary job** for M1 focus, and
   - Optionally 1–2 **secondary jobs** that you will explicitly not optimise yet but may serve later.
4. Draft the **JTBD analysis document** (for example, `[project]/docs/founder/conception/jtbd.md`) with at least these sections:
   - Context (product, customer segment, link to PR/FAQ),
   - Primary job story and related/emotional/social jobs,
   - Alternatives and forces (push, pull, anxieties, habits),
   - Job map and main pain points,
   - Importance vs satisfaction assessment,
   - Implications for Problem-Solution Fit, Lean Canvas, and early metrics.
5. Translate key implications explicitly:
   - Which **Problem-Solution Fit Canvas** blocks this job clarifies (problem statement, solution framing, assumptions),
   - Which **Lean Canvas** blocks this informs (Problem, Customer Segments, UVP, Solution, Channels, Key Metrics).
6. Record key choices and assumptions in `m1_founder_diary.md`, including:
   - Why you chose this primary job over others,
   - What would make you revisit or change this focus later.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| JTBD analysis document | Applied framework in `[project]/docs/founder/conception/jtbd.md` | Canonical reference for jobs, forces, and implications in M1 |
| Job prioritisation summary | Short matrix or table plus narrative | Makes the choice of primary job explicit and reviewable |
| Founder diary entry | Row(s) in `m1_founder_diary.md` | Captures decisions and assumptions for future milestones |

**Validation:**

- [ ] You can answer in one sentence: "Our product is hired when **[job story]**."
- [ ] You can explain why this job is more attractive **now** than other jobs you could pursue.
- [ ] Problem-Solution Fit Canvas and Lean Canvas both reference and are consistent with the JTBD analysis.
- [ ] The founder log clearly records the chosen job, alternatives considered, and the reasons behind the decision.

---

## Pitfalls

**Confusing Personas Or Features With Jobs**

Phrase jobs around **moments and progress**, independent of your product or UI.

**Only Capturing Functional Jobs**

Always probe for emotional and social stakes and document them explicitly.

**Relying On Hypotheticals Instead Of Real Episodes**

Anchor interviews on **specific past episodes** and reconstruct what they actually did, felt, and chose.

**Over-Fitting To Early Adopters**

Explicitly label insights as early adopter–driven, and test whether the same job and forces appear in more mainstream segments.

**Treating JTBD As A One-Time Exercise**

Treat JTBD as a **living artefact**; revisit the analysis when you see major shifts in adoption patterns, segments, or key metrics.

---

## Integration

**Prerequisites:**  
Read `conception_process.md`.

**Builds On:**

| Framework | Output Used | How Used |
|-----------|-------------|----------|
| Working Backwards (PR/FAQ) | Press Release, External FAQ, Internal FAQ | Provides customer narrative, problem framing, claims, and assumptions that become JTBD hypotheses |
| Early customer conversations (if any) | Notes, informal insights | Offer raw material and examples for candidate jobs and situations |
| Founder log (M1) | Prior decisions and context | Helps interpret why previous choices were made and how they relate to jobs |

**Feeds Into:**

| Framework | Output Provided | How Used |
|-----------|-----------------|----------|
| Problem-Solution Fit Canvas | Primary job, alternatives, forces, job map | Grounds problem statement and solution framing in real customer progress and competition |
| Lean Canvas | Customer Segments, Problem, UVP, Solution, Channels, Key Metrics | Uses jobs and forces to populate core blocks and avoid feature-driven modelling |
| 5 Whys | Clear problem description and job context | Provides starting point for probing root causes behind the core job's pain points |
| Project memo | Introduction, Problem, Solution, Tenets, Progress (Conception) | Ensures narrative in the memo reflects the chosen primary job and its implications |
| Validation and experimentation in later milestones | Assumptions about jobs, forces, and adoption behavior | Feeds M2 and M5 experiments that validate whether you truly help customers make progress |

**Workflow Position:**

JTBD sits in M1 directly after Working Backwards.

---

## Success Criteria

- [ ] You have at least **5–10 structured JTBD interviews** across relevant participant types.
- [ ] You can state **one primary job** and 1–3 related/emotional/social jobs in "When / I want to / so I can" form.
- [ ] You have a **forces analysis** and **job map** that explain both adoption and non-adoption.
- [ ] A JTBD analysis applied framework exists in `[project]/docs/founder/conception/jtbd.md` and is referenced by Problem-Solution Fit and Lean Canvas.
- [ ] The project memo's Introduction, Problem, Solution, and Tenets sections are consistent with the JTBD analysis.
- [ ] The M1 founder log contains at least one entry documenting the chosen primary job, alternatives considered, and main assumptions.

---

## References

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1–10 | Threshold: TS ≥ 6

Sources consulted when designing this framework:

- [1] Jobs To Be Done — `https://en.wikipedia.org/wiki/Jobs_to_Be_Done` — Research Date: 2025-12-21 — Source Date: n/a — TS: 8 (AT: 7, TR: 8, TM: 9)
- [2] Getting Started With JTBD Interviews — `https://jobstobedone.org/news/getting-started-with-jtbd-interviews/` — Research Date: 2025-12-21 — Source Date: n/a — TS: 8 (AT: 8, TR: 7, TM: 9)
- [3] JTBD Framework: What It Is And How To Use It — `https://productschool.com/blog/product-fundamentals/jtbd-framework` — Research Date: 2025-12-21 — Source Date: n/a — TS: 7 (AT: 7, TR: 7, TM: 7; TR penalised −1 for marketing language)
- [4] Jobs To Be Done (JTBD) For Digital Product Discovery — `https://scaleupmethodology.com/scaling/scaling-startups/digital-products/digital-product-discovery/jobs-to-be-done-jtbd/` — Research Date: 2025-12-21 — Source Date: n/a — TS: 7 (AT: 6, TR: 7, TM: 8; TR penalised −1 for marketing language)
- [5] Jobs To Be Done Framework — `https://www.clay.com/glossary/jobs-to-be-done-framework` — Research Date: 2025-12-21 — Source Date: n/a — TS: 7 (AT: 6, TR: 7, TM: 8; TR penalised −1 for marketing language)

Additional conceptual references (books, not scored):

- Clayton M. Christensen et al., *Competing Against Luck* (2016).  
- Anthony Ulwick, *Jobs to Be Done: Theory to Practice* (2016).  
- Bob Moesta, *Demand-Side Sales 101* (2020).

---

## For AI Agents

**Execution Context:**

1. Read `conception_process.md` and the user's Working Backwards PR/FAQ before starting.
2. Track progress: "Currently in Task [N]: [Task Name]".
3. Confirm each task's validation checklist before proceeding.
4. Keep JTBD, Problem-Solution Fit Canvas, Lean Canvas, and the project memo aligned.
5. Record key JTBD insights and decisions in M1 founder log as they emerge.

**Working With Tasks:**

- Complete each task atomically.
- If validation criterion cannot be met, surface risk and propose mitigations.
- Treat JTBD artefacts as living documents; suggest revisiting when later milestones reveal new patterns.

---

