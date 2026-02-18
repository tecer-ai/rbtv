---
---

# Pre-mortem

**Purpose:** Imagine the project has failed 12 months from now. Brainstorm every plausible reason for that failure. Rank by likelihood and severity, define mitigation actions and early warning signals, and cross-reference with Leap of Faith kill criteria.

**Context:** Use in M2 Validation, Step 7. Run AFTER all other M2 frameworks (Leap of Faith, Assumption Mapping, TAM/SAM/SOM, Unit Economics, TRL) so you can synthesize risks across the full validation picture.

---

## Framework Overview

Pre-mortem uses Gary Klein's prospective hindsight method. Instead of asking "what could go wrong?" (which triggers optimism bias and social pressure to stay positive), you state as fact: "The project failed. It is 12 months from now. Why?" This reframe gives team members psychological permission to voice doubts they would otherwise suppress. Research shows prospective hindsight increases the ability to identify reasons for future outcomes by 30%.

The method works across seven failure categories: market, product, team, financial, technical, competitive, and operational. For each category, you generate failure modes, then rank them by likelihood (how probable is this failure?) and severity (if it happens, how much damage?). The top-ranked failures get concrete mitigation actions and early warning signals that you can monitor during execution.

Pre-mortem is the final synthesis step in M2 Validation. It consumes risks and uncertainties surfaced by every prior framework: Leap of Faith kill criteria, Assumption Mapping's "Test" quadrant, TAM/SAM/SOM's market risk estimates, Unit Economics' sensitivity points, and TRL's technical unknowns. The output feeds directly into the project memo's Open Questions and risks section, M5 Market Validation's risk-informed test design, and M6 MVP's risk-aware architecture decisions.

---

## Task Structure

High-level view of framework execution:

| Task | Goal | Key Inputs | Key Outputs |
|------|------|------------|-------------|
| 1. Set the Stage | Define the failure scenario, scope, and time horizon; create psychological safety for honest risk surfacing | Project memo, all M2 framework outputs | Failure prompt, participant briefing, category checklist |
| 2. Brainstorm Failure Modes | Generate plausible failure reasons across all seven categories without filtering | Failure prompt, M2 risks and uncertainties, founder/team knowledge | Raw failure mode inventory (unfiltered, uncensored) |
| 3. Rank by Likelihood and Severity | Score each failure mode and identify the top threats | Raw failure mode inventory | Ranked failure table with L x S scores |
| 4. Define Mitigations and Early Warning Signals | Create concrete actions and monitoring triggers for top-ranked failures | Ranked failure table, Leap of Faith kill criteria | Mitigation plan with actions, owners, timelines, and warning signals |
| 5. Cross-reference and Wire into Project Artifacts | Connect pre-mortem outputs to Leap of Faith kill criteria, project memo, and downstream milestones | Mitigation plan, Leap of Faith analysis, project memo, M2 founder diary | Updated project memo (risks, open questions), pre-mortem document, diary entries |

---

## Task 1: Set the Stage

**Goal:** Define the failure scenario precisely, establish the scope and time horizon, and create the psychological conditions for honest risk surfacing.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Project memo (current state) | `projects/[project]/founder/[project]_memo.md` | Yes |
| All M2 framework outputs (Leap of Faith, Assumption Mapping, TAM/SAM/SOM, Unit Economics, TRL) | `projects/[project]/founder/validation/` | Yes |
| Team composition and roles (if applicable) | M2 founder diary or project memo | No |

**Action:**

1. Write the **failure prompt** — one paragraph that states the failure as fact:
   - "It is [date 12 months from now]. [Project name] has failed. The product never reached product-market fit. The team has disbanded. Funding ran out or was not secured. We are now conducting a post-mortem to understand why."
   - Adjust time horizon if appropriate (6 months for a very early concept, 18 months for a more complex venture). Default to 12 months.
2. Define the **scope of failure**: total project failure (shutdown), not partial setback. The goal is to surface existential risks, not minor inconveniences.
3. Prepare the **category checklist** for brainstorming. Use these seven categories:
   - **Market:** Customers do not exist, do not care, or cannot be reached.
   - **Product:** Solution does not solve the problem, is unusable, or is not differentiated.
   - **Team:** Missing skills, founder conflict, burnout, key person leaves.
   - **Financial:** Revenue too low, costs too high, funding not secured, cash runs out.
   - **Technical:** Cannot build it, performance inadequate, integration fails, security breach.
   - **Competitive:** Incumbent responds, new entrant captures market, open-source alternative emerges.
   - **Operational:** Regulatory block, legal issue, partner dependency fails, scaling bottleneck.
4. If working with a team, brief participants: "We are assuming failure already happened. Your job is to explain why. No idea is too pessimistic. We want the uncomfortable truths."
5. If working solo or with an AI agent, commit to the same mindset. Write down: "I will not filter or rationalize. Every plausible failure reason gets listed."

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Failure prompt | One paragraph | Sets the psychological frame for prospective hindsight |
| Category checklist | Seven categories with one-line descriptions | Ensures brainstorming covers all risk domains |
| Participant briefing | Short instructions (team) or personal commitment (solo) | Creates psychological safety for honest risk surfacing |

**Validation:**

- [ ] The failure prompt states failure as fact, not possibility. Uses past tense or present tense from the future vantage point.
- [ ] The time horizon is explicitly stated and appropriate for the project stage.
- [ ] All seven failure categories are listed with clear definitions.
- [ ] If working with a team, all participants have read the briefing before brainstorming starts.

---

## Task 2: Brainstorm Failure Modes

**Goal:** Generate the fullest possible list of plausible failure reasons across all seven categories without filtering, editing, or debating.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Failure prompt and category checklist | Task 1 | Yes |
| Leap of Faith analysis (kill criteria, high-risk assumptions) | M2 Step 2 | Yes |
| Assumption Mapping ("Test" and "Accept" assumptions) | M2 Step 3 | Yes |
| TAM/SAM/SOM analysis (market risks, data gaps) | M2 Step 4 | Yes |
| Unit Economics model (sensitivity points, break-even risks) | M2 Step 5 | Yes |
| TRL assessment (low-TRL components, technical unknowns) | M2 Step 6 | Yes |

**Action:**

1. Go through each of the seven categories one by one. For each category, spend 5-10 minutes generating failure modes.
2. For each failure mode, write a **one-sentence reason** explaining how and why this killed the project. Use past tense from the future vantage point:
   - "We failed because early adopters loved the concept but refused to pay more than $5/month, making unit economics unviable."
   - "We failed because the NLP model never achieved 90% accuracy, and customers abandoned after two bad experiences."
3. Draw explicitly from M2 framework outputs:
   - **From Leap of Faith:** Convert each kill criterion into a failure mode. "Kill criterion X was triggered because..."
   - **From Assumption Mapping:** Convert each "Test" assumption into a failure mode. "We assumed X, but it turned out..."
   - **From TAM/SAM/SOM:** Convert market sizing gaps into failure modes. "The market was actually 10x smaller because..."
   - **From Unit Economics:** Convert sensitivity points into failure modes. "CAC was 3x higher than modeled because..."
   - **From TRL:** Convert technical risks into failure modes. "Component X never reached TRL 6 because..."
4. After exhausting M2 inputs, brainstorm additional failure modes from founder intuition, industry knowledge, and general startup failure patterns.
5. Do NOT filter, merge, or debate during brainstorming. Capture everything. Quantity over quality at this stage.
6. Minimum target: 15 failure modes across at least 5 of the 7 categories. If you have fewer than 15, push harder on underrepresented categories.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Raw failure mode inventory | Numbered list with category tag and one-sentence reason per mode | Complete, unfiltered catalog of plausible failure reasons |

**Validation:**

- [ ] At least 15 failure modes are listed.
- [ ] At least 5 of the 7 categories have at least one failure mode.
- [ ] Every Leap of Faith kill criterion appears as a failure mode (or is explicitly marked as covered by another mode).
- [ ] Failure modes are written as concrete past-tense explanations, not vague risks ("we failed because X" not "X might happen").
- [ ] No filtering or merging occurred during brainstorming.

---

## Task 3: Rank by Likelihood and Severity

**Goal:** Score each failure mode on Likelihood (1-5) and Severity (1-5), compute a combined score, and identify the top failures that demand mitigation.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Raw failure mode inventory | Task 2 | Yes |
| M2 framework evidence (existing data, scores, confidence levels) | All M2 outputs | Yes |

**Action:**

1. Define the **Likelihood** scale:
   - **5 — Near certain:** Multiple signals already point to this. Would be surprising if it did NOT happen.
   - **4 — Probable:** More likely than not given current evidence.
   - **3 — Possible:** Could go either way. Evidence is mixed or absent.
   - **2 — Unlikely:** Would require several things to go wrong simultaneously.
   - **1 — Remote:** Theoretically possible but requires extreme bad luck or negligence.
2. Define the **Severity** scale:
   - **5 — Fatal:** Project dies. No recovery path.
   - **4 — Crippling:** Major pivot required. Months of work lost.
   - **3 — Serious:** Significant setback. Recovery possible but expensive.
   - **2 — Moderate:** Noticeable impact. Can be managed with effort.
   - **1 — Minor:** Inconvenience. Normal course correction.
3. Score each failure mode on both scales.
4. Compute **Risk Score = Likelihood x Severity** (range 1-25).
5. Sort failure modes by Risk Score descending.
6. Draw a **cutoff line**: the top failures whose cumulative risk accounts for the majority of total risk. Typically the top 5-8 failures. These are your "must mitigate" list.
7. Merge truly duplicative failure modes now (not during brainstorming). If two modes describe the same underlying cause, combine them and take the higher scores.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Ranked failure table | Table with columns: Rank, Category, Failure Mode, Likelihood (1-5), Severity (1-5), Risk Score (L x S) | Prioritized list of threats to the project |
| Top failures shortlist | Top 5-8 failures above cutoff | Focus list for mitigation in Task 4 |

**Validation:**

- [ ] Every failure mode has Likelihood and Severity scores with brief justification.
- [ ] Risk Scores are computed correctly (L x S).
- [ ] Table is sorted by Risk Score descending.
- [ ] Top failures shortlist contains 5-8 items. If fewer than 5, you may be under-counting risks. If more than 8, raise the cutoff.
- [ ] At least one failure mode has Risk Score 15 or higher. If none do, challenge whether you are being honest about likelihood and severity.

---

## Task 4: Define Mitigations and Early Warning Signals

**Goal:** For each top-ranked failure, define a concrete mitigation action and an early warning signal that you can monitor during execution.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Top failures shortlist | Task 3 | Yes |
| Leap of Faith kill criteria and observable signals | M2 Leap of Faith | Yes |
| Assumption Mapping test cards | M2 Assumption Mapping | Yes |

**Action:**

1. For each top failure, create a **mitigation card** containing:
   - **Failure mode:** One-sentence description from Task 2.
   - **Root cause:** What underlying assumption, gap, or weakness would cause this?
   - **Mitigation action:** One or two concrete steps you can take NOW or SOON to reduce likelihood or severity. Be specific: "Interview 10 enterprise buyers about procurement process" not "learn more about the market."
   - **Early warning signal:** An observable, measurable indicator that this failure is becoming more likely. Define the threshold: "If fewer than 2 of 10 interviewees mention this pain unprompted, escalate."
   - **Trigger response:** What you do when the early warning signal fires. Options: investigate further, pivot approach, activate contingency plan, invoke kill criterion.
   - **Owner:** Who monitors this signal and executes the mitigation.
   - **Timeline:** When the mitigation action should be completed and when to first check the warning signal.
2. Cross-reference each mitigation with **Leap of Faith kill criteria**:
   - If a failure mode maps to a kill criterion, the early warning signal MUST align with the kill criterion's observable signal.
   - If a failure mode reveals a risk NOT covered by existing kill criteria, propose a new kill criterion.
3. Cross-reference with **Assumption Mapping test cards**:
   - If a test card already addresses the root cause of a failure mode, link them. Do not duplicate effort.
   - If no test card exists for a critical failure mode, create one or flag it as a gap.
4. For failures with Severity 5 (fatal), also define a **contingency plan**: what you do if the failure actually occurs despite mitigation. Options: pivot direction, exit the market, restructure team, seek emergency funding.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Mitigation cards | Structured cards (one per top failure) | Concrete risk reduction actions with monitoring triggers |
| Kill criteria alignment | Cross-reference table mapping failures to kill criteria | Ensures pre-mortem and Leap of Faith are consistent |
| New kill criteria (if any) | Additions to Leap of Faith | Captures risks not previously identified |
| Contingency plans (for Severity 5 failures) | Brief plans | Last-resort responses if mitigation fails |

**Validation:**

- [ ] Every top-ranked failure has a mitigation card with all required fields.
- [ ] Mitigation actions are specific and time-bound, not vague intentions.
- [ ] Early warning signals are observable and measurable with a defined threshold.
- [ ] Every Severity 5 failure has a contingency plan.
- [ ] Failures that map to Leap of Faith kill criteria have aligned early warning signals.
- [ ] No mitigation duplicates an existing Assumption Mapping test card without linking to it.

---

## Task 5: Cross-reference and Wire into Project Artifacts

**Goal:** Finalize the pre-mortem document and connect it to the project memo, Leap of Faith kill criteria, and downstream milestones.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Ranked failure table and mitigation cards | Tasks 3-4 | Yes |
| Project memo | `projects/[project]/founder/[project]_memo.md` | Yes |
| M2 founder diary | `projects/[project]/founder/validation/m2_founder_diary.md` | Yes |
| Leap of Faith analysis | M2 Step 2 | Yes |

**Action:**

1. Create the pre-mortem document at `projects/[project]/founder/validation/pre_mortem.md` containing:
   - Failure prompt (Task 1).
   - Full ranked failure table (Task 3).
   - Mitigation cards for top failures (Task 4).
   - Kill criteria alignment table (Task 4).
2. Update **Leap of Faith analysis** with any new kill criteria identified in Task 4.
3. Update **project memo**:
   - Progress > Validation subsection: note pre-mortem completion and top 3 risks.
   - Open Questions: add unresolved risks from the pre-mortem that require further investigation.
   - Next Steps: include mitigation actions that must occur in M3, M4, M5, or M6.
4. Update **M2 founder diary** with:
   - Entry recording the pre-mortem session, date, and participants.
   - Top 3 surprising or uncomfortable failure modes.
   - Any new kill criteria added.
   - Explicit statement of overall risk posture: "Given the pre-mortem, our biggest existential risk is X. Our plan to address it is Y."
5. Flag specific risks for downstream milestones:
   - **M5 Market Validation:** Which failure modes require customer evidence to de-risk? Feed into SPIN Selling and smoke test design.
   - **M6 MVP:** Which failure modes should inform architecture decisions, feature prioritization, or launch sequencing?

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Pre-mortem document | Markdown in `projects/[project]/founder/validation/` | Canonical risk assessment for the project |
| Updated Leap of Faith | Additions to kill criteria (if any) | Ensures kill criteria cover all identified existential risks |
| Updated project memo | Risks, open questions, next steps | Narrative integration of risk findings |
| Updated M2 founder diary | New entries with risk decisions | Decision trail for risk assessment |
| Downstream risk flags | Notes for M5 and M6 | Ensures future milestones are risk-aware |

**Validation:**

- [ ] Pre-mortem document exists with ranked failure table and mitigation cards.
- [ ] Leap of Faith kill criteria are updated if new existential risks were found.
- [ ] Project memo reflects top risks and mitigation actions.
- [ ] M2 founder diary has at least one entry from this framework.
- [ ] At least one risk is flagged for M5 Market Validation and at least one for M6 MVP.

---

## Pitfalls

**Running Pre-mortem Before Other M2 Frameworks**

NEVER run pre-mortem first. It MUST be the last M2 framework. Without TAM/SAM/SOM, Unit Economics, TRL, and Assumption Mapping, you lack the evidence to brainstorm credible failure modes. You will generate generic startup failure lists instead of project-specific risks.

**Filtering During Brainstorming**

NEVER debate, dismiss, or merge failure modes while brainstorming. Capture everything. Filtering happens in Task 3 (ranking), not Task 2 (brainstorming). Premature filtering suppresses the uncomfortable truths the pre-mortem exists to surface.

**Writing Vague Failure Modes**

NEVER accept "market risk" or "technical challenges" as failure modes. MUST write concrete, past-tense explanations: "We failed because enterprise buyers required SOC 2 compliance and we could not afford the audit for 18 months." Vague failure modes produce vague mitigations.

**Treating Pre-mortem as Pessimism Exercise**

NEVER use pre-mortem to argue against proceeding. The purpose is to surface risks so you can mitigate them, not to kill the project. If the pre-mortem reveals truly fatal risks with no mitigation, that is a valid kill signal — but that is the exception, not the goal.

**Ignoring the Early Warning Signals After Writing Them**

NEVER create early warning signals and then forget to monitor them. MUST assign owners and check-in dates. Wire signals into the M2 founder diary so they become part of ongoing decision-making.

---

## Integration

**Prerequisites:** MUST complete all prior M2 frameworks: Leap of Faith (Step 2), Assumption Mapping (Step 3), TAM/SAM/SOM (Step 4), Unit Economics (Step 5), TRL (Step 6).

**Builds on:**

| Framework | Output Used | How Used |
|-----------|-------------|----------|
| Leap of Faith (M2) | Kill criteria, value/growth hypothesis classification, observable signals | Kill criteria become failure modes; observable signals become early warning signal templates |
| Assumption Mapping (M2) | "Test" and "Accept" assumptions, test cards | Unvalidated assumptions become failure mode sources; test cards prevent mitigation duplication |
| TAM/SAM/SOM (M2) | Market sizing gaps, segment risks, data quality notes | Market-category failure modes grounded in actual sizing evidence |
| Unit Economics (M2) | Sensitivity points, break-even risks, CAC/LTV uncertainty ranges | Financial-category failure modes grounded in modeled scenarios |
| Technology Readiness Level (M2) | Low-TRL components, technical unknowns, de-risking gaps | Technical-category failure modes grounded in assessed readiness levels |

**Feeds into:**

| Framework | Output Provided | How Used |
|-----------|-----------------|----------|
| Project memo | Top risks, open questions, mitigation next steps | Integrates risk findings into the narrative decision document |
| M5 Market Validation | Risk-informed test priorities, customer evidence needs | Ensures market validation targets the highest-risk assumptions about customers and market |
| M6 MVP | Risk-aware architecture decisions, feature prioritization, launch sequencing | Ensures MVP design accounts for identified technical, product, and operational risks |
| Leap of Faith (updated) | New kill criteria from failure modes not previously covered | Strengthens the kill/pivot decision framework with pre-mortem insights |

**Workflow Position:** Within M2 Validation, Pre-mortem is the final framework (Step 7), run after all analytical frameworks are complete. It synthesizes risks from the entire validation milestone before the project memo update in Step 8.

---

## Success Criteria

This framework is complete when:

- [ ] A pre-mortem document exists with the failure prompt, at least 15 failure modes across at least 5 categories, and a ranked failure table.
- [ ] Top 5-8 failures have mitigation cards with concrete actions, early warning signals with thresholds, and assigned owners.
- [ ] Every Severity 5 failure has a contingency plan.
- [ ] Every Leap of Faith kill criterion is represented in the failure mode inventory.
- [ ] Any new kill criteria discovered are added to the Leap of Faith analysis.
- [ ] The project memo is updated with top risks, open questions, and mitigation next steps.
- [ ] The M2 founder diary records the pre-mortem session and the overall risk posture statement.
- [ ] At least one risk is flagged for M5 and at least one for M6.

---

## References

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS >= 6

Sources consulted when designing this framework:

- [1] Gary Klein, "Performing a Project Premortem," *Harvard Business Review*, September 2007 — Research Date: 2026-01-30 — Source Date: 2007-09 — TS: 9.0 (AT: 9, TR: 9, TM: 9). Originating article for the pre-mortem method.
- [2] Daniel Kahneman, *Thinking, Fast and Slow* (Farrar, Straus and Giroux, 2011) — Research Date: 2026-01-30 — Source Date: 2011 — TS: 8.3 (AT: 10, TR: 9, TM: 6). Prospective hindsight research and cognitive bias foundations.
- [3] David J. Bland & Alex Osterwalder, *Testing Business Ideas* (Wiley, 2020) — Research Date: 2026-01-30 — Source Date: 2020 — TS: 7.7 (AT: 9, TR: 8, TM: 6). Risk assessment in the context of business model validation.

Additional conceptual references (books, not scored):

- Deborah Mitchell, Jay Russo, and Nancy Pennington, "Back to the Future: Temporal Perspective in the Explanation of Events," *Journal of Behavioral Decision Making* 2 (1989): 25-38. Original research showing prospective hindsight increases outcome identification by 30%.

---

## For AI Agents

**Execution Context:** When executing this framework with a user:

1. MUST confirm that Leap of Faith, Assumption Mapping, TAM/SAM/SOM, Unit Economics, and TRL are complete. If any are missing, MUST flag it and recommend completing them first. Pre-mortem without upstream inputs produces generic, low-value output.
2. MUST read this framework and `validation_process.md` before starting. Track progress explicitly: "Currently in Task [N]: [Task Name]".
3. MUST maintain the prospective hindsight frame throughout brainstorming. Use past tense: "We failed because..." not "We might fail if..." Correct the user if they slip into conditional language.
4. MUST NOT filter or dismiss failure modes during Task 2. If user says "that would never happen," respond: "In this exercise, it already did. Let us keep it and rank it in the next task."
5. MUST push for concrete, specific failure modes. Reject category-level answers like "market risk." Demand: "What specifically about the market caused failure?"

**Working With Tasks:**

- MUST treat each task as atomic. NEVER skip validation criteria without recording explicit risks or TODOs.
- During Task 2, generate failure modes from ALL M2 framework outputs before asking for additional brainstorming. The AI agent should propose failure modes derived from each upstream framework.
- During Task 4, cross-reference every mitigation with existing Assumption Mapping test cards. Propose linking rather than duplicating.
- After Task 5, summarize the overall risk posture in one paragraph and ask the user: "Given these risks, do you still want to proceed? What is your confidence level?"

**Red Flags:**

- Fewer than 15 failure modes after brainstorming (insufficient depth).
- All failure modes in 1-2 categories (blind spots in other domains).
- No failure mode with Risk Score above 15 (likely under-rating likelihood or severity).
- Mitigation actions are vague ("do more research") instead of specific ("interview 10 customers about X by [date]").
- Early warning signals have no defined threshold.

---

