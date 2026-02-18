---
---

# Technology Readiness Level (TRL)

**Purpose:** Assess the technical readiness of each major component using NASA's 9-level TRL scale. Identify what must be proven technically before prototypation. Estimate de-risking effort and design technical spikes for components below TRL 4.

**Context:** Use in M2 Validation, Step 6. Can run in parallel with TAM/SAM/SOM (Step 4) and Unit Economics (Step 5). MUST have access to Working Backwards Internal FAQ, Problem-Solution Fit solution concept, and Lean Canvas Solution block.

---

## Framework Overview

Technology Readiness Level is NASA's 9-level scale for assessing how close a technology is to operational deployment. TRL 1 means basic principles observed. TRL 9 means proven in real-world operations. Most startup founders either overestimate their technical readiness ("we can build that in a weekend") or underestimate it ("we need years of R&D"). The TRL framework forces honest, evidence-based assessment of each component separately, preventing the common failure mode where one immature component blocks the entire product.

For digital startups, TRL assessment covers software components, algorithms, data pipelines, integrations, infrastructure, and any novel technical approaches. A standard CRUD web app might sit at TRL 7-8 for most components. A machine learning model trained on proprietary data might sit at TRL 2-3. A blockchain-based verification system might sit at TRL 4-5. The point is not to penalize low TRL, but to identify which components need de-risking work before you commit to prototypation in M4.

Components below TRL 4 require technical spikes or proof-of-concepts before M4 Prototypation can proceed safely. Components at TRL 4-6 can be prototyped but carry residual risk. Components at TRL 7+ can be built with standard engineering practices. This assessment feeds directly into Pre-mortem (technical risks), M4 planning (build sequencing and technical architecture), and M6 MVP (architecture decisions and feature scope).

---

## Task Structure

High-level view of framework execution:

| Task | Goal | Key Inputs | Key Outputs |
|------|------|------------|-------------|
| 1. Identify Major Technical Components | Decompose the solution into assessable technical building blocks | Problem-Solution Fit solution concept, Lean Canvas Solution block, Working Backwards Internal FAQ | Component inventory with descriptions and dependencies |
| 2. Assess Current TRL for Each Component | Rate each component on the 1-9 TRL scale with supporting evidence | Component inventory, technical knowledge, existing prototypes or research | TRL assessment table with scores and evidence |
| 3. Identify Technical Risks and Unknowns | Surface specific technical unknowns, dependencies, and failure points per component | TRL assessment table, Working Backwards Internal FAQ technical questions | Technical risk inventory with categorized unknowns |
| 4. Design Technical Spikes for Low-TRL Components | Create spike plans for components below TRL 4 that must be proven before prototypation | Components with TRL < 4, technical risk inventory | Spike cards with objectives, methods, success criteria, and timelines |
| 5. Estimate De-risking Effort and Wire into Planning | Size the total technical de-risking work and connect to M4, M6, and project artifacts | Spike cards, TRL assessment, project memo, M2 founder diary | De-risking roadmap, updated project memo, updated diary, M4/M6 inputs |

---

## Task 1: Identify Major Technical Components

**Goal:** Decompose the proposed solution into distinct technical building blocks that can each be assessed independently on the TRL scale.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Problem-Solution Fit solution concept (Our Solution block) | M1 Problem-Solution Fit Canvas | Yes |
| Lean Canvas Solution block (top 3-5 features/capabilities) | M1 Lean Canvas | Yes |
| Working Backwards Internal FAQ (technical feasibility questions) | M1 Working Backwards | Yes |
| Any existing technical notes, sketches, or prototypes | Founder/team | No |

**Action:**

1. From the Problem-Solution Fit solution concept, extract the **core mechanism of value creation** — the fundamental technical capability that makes the solution work.
2. From the Lean Canvas Solution block, list each capability and ask: "What technical system or component delivers this?"
3. From the Working Backwards Internal FAQ, extract any technical questions, dependencies, or feasibility concerns raised.
4. Decompose into **major technical components**. A component is a building block that:
   - Can be assessed independently for readiness.
   - Has a clear function in delivering the solution.
   - Could be built, bought, or integrated separately from other components.
5. For each component, document:
   - **Component ID:** Short label (e.g., TC-01, TC-02).
   - **Name:** Descriptive name (e.g., "NLP intent classifier," "payment processing integration," "real-time data pipeline").
   - **Description:** One paragraph explaining what it does and why it is needed.
   - **Type:** Novel (built from scratch, new approach), Adapted (existing technology applied to new context), or Standard (well-understood, widely available).
   - **Dependencies:** Other components or external systems this depends on.
6. Aim for 4-10 components. Fewer than 4 means you have not decomposed enough. More than 10 means you are going too granular — combine related sub-components.
7. For each component, note whether existing code, prototypes, or third-party solutions already exist.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Component inventory | Table with ID, name, description, type, dependencies, existing assets | Complete list of technical building blocks to assess |

**Validation:**

- [ ] Every capability in the Lean Canvas Solution block maps to at least one component.
- [ ] Each component has a clear type classification (Novel, Adapted, or Standard).
- [ ] Dependencies between components are documented.
- [ ] Component count is between 4 and 10.
- [ ] A technical reader can understand what each component does without reading upstream documents.

---

## Task 2: Assess Current TRL for Each Component

**Goal:** Rate each component on the NASA TRL 1-9 scale with explicit evidence supporting the assessment.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Component inventory | Task 1 | Yes |
| Technical knowledge and experience | Founder/team | Yes |
| Existing prototypes, code, research, or third-party documentation | Various | No |

**Action:**

1. Use the following **TRL scale** (adapted for digital startups):
   - **TRL 1 — Basic principles observed:** You understand the scientific or engineering principle but have not applied it. Example: "We know transformer models can classify text."
   - **TRL 2 — Technology concept formulated:** You have a concept for how to apply the principle to your problem. Example: "We believe a fine-tuned BERT model could classify customer support tickets."
   - **TRL 3 — Proof of concept:** You have demonstrated the core concept works in a controlled setting. Example: "We ran a Jupyter notebook showing 85% accuracy on a sample dataset."
   - **TRL 4 — Validated in lab:** The component works in a development environment with representative data. Example: "We built a working classifier in a dev environment using production-like data."
   - **TRL 5 — Validated in relevant environment:** The component works in a staging environment that approximates production conditions. Example: "The classifier runs on our staging server with real API calls and handles 100 requests/minute."
   - **TRL 6 — Demonstrated in relevant environment:** The component has been tested with real users or real data in a near-production setting. Example: "10 beta users have used the classifier on their own data with acceptable accuracy."
   - **TRL 7 — Prototype in operational environment:** A working prototype operates in the real environment. Example: "The classifier is running in production for 50 users with monitoring and error handling."
   - **TRL 8 — System complete and qualified:** The component is fully integrated, tested, and meeting performance requirements. Example: "The classifier is in production, handles 1000 requests/minute, and meets our 95% accuracy SLA."
   - **TRL 9 — Proven in operations:** The component has a track record of reliable real-world operation. Example: "The classifier has run in production for 6 months with 99.9% uptime and consistent accuracy."
2. For each component, assess the current TRL by:
   - Identifying the **highest TRL level for which you have concrete evidence.**
   - Writing a one-sentence **evidence statement** justifying the score.
   - Noting what evidence would be needed to advance to the next TRL level.
3. Be brutally honest. A proof-of-concept notebook is TRL 3, not TRL 5. An idea you discussed is TRL 1-2, not TRL 3. Default to the lower score when uncertain.
4. For Standard-type components (widely available technology), typical starting TRL is 6-8 unless your specific use case introduces novel requirements.
5. For Novel-type components, typical starting TRL is 1-3 unless you have already built prototypes.
6. Flag any component at TRL 1-3 as **high technical risk**. Flag components at TRL 4-5 as **moderate technical risk**.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| TRL assessment table | Table with Component ID, Name, TRL Score (1-9), Evidence, Next TRL Requirements, Risk Level | Honest snapshot of technical readiness per component |

**Validation:**

- [ ] Every component has a TRL score with a one-sentence evidence statement.
- [ ] No component is scored above the highest level for which concrete evidence exists.
- [ ] Novel-type components are not scored above TRL 3 without demonstrated proof of concept.
- [ ] Standard-type components are scored at TRL 6+ unless specific use-case constraints lower readiness.
- [ ] Each component notes what is required to reach the next TRL level.
- [ ] Components at TRL 1-3 are flagged as high technical risk.

---

## Task 3: Identify Technical Risks and Unknowns

**Goal:** For each component, surface specific technical unknowns, dependencies, and failure points that could block progress.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| TRL assessment table | Task 2 | Yes |
| Working Backwards Internal FAQ (technical questions) | M1 Working Backwards | Yes |
| Technical domain knowledge | Founder/team | Yes |

**Action:**

1. For each component, ask these questions:
   - **Performance:** Can this component meet the required performance targets (speed, accuracy, throughput, latency)?
   - **Scalability:** Can this component scale to the expected user/data volume within cost constraints?
   - **Integration:** Does this component depend on external APIs, services, or systems that could change, fail, or restrict access?
   - **Data:** Does this component require data that you do not yet have, or data whose quality is unproven?
   - **Security/Privacy:** Does this component handle sensitive data or require compliance certifications?
   - **Skills:** Does building or operating this component require expertise that the team does not currently have?
   - **Cost:** Does this component have variable costs (API calls, compute, storage) that could become prohibitive at scale?
2. For each risk identified, document:
   - **Risk ID:** Short label (e.g., TR-01).
   - **Component:** Which component this risk belongs to.
   - **Risk description:** One sentence describing what could go wrong.
   - **Category:** Performance, Scalability, Integration, Data, Security, Skills, or Cost.
   - **Current mitigation:** What you already know or have done to address this.
   - **Residual uncertainty:** High, Medium, or Low — how much unknown remains.
3. Cross-reference with the Working Backwards Internal FAQ. Every technical question raised in the FAQ should map to a risk or be explicitly addressed.
4. Identify **dependency chains**: where the failure of one component would block or degrade other components. Mark these as critical path risks.
5. Count total risks per component. Components with 3+ high-residual-uncertainty risks are candidates for technical spikes in Task 4.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Technical risk inventory | Table with Risk ID, Component, Description, Category, Current Mitigation, Residual Uncertainty | Comprehensive map of technical unknowns |
| Critical path risks | Subset of risks involving dependency chains | Identifies where a single failure cascades |
| Working Backwards FAQ coverage | Cross-reference list | Confirms all technical feasibility questions are addressed |

**Validation:**

- [ ] Every component with TRL below 6 has at least one identified risk.
- [ ] Every technical question from the Working Backwards Internal FAQ is mapped to a risk or marked as addressed.
- [ ] Dependency chains are documented. At least one critical path risk is identified (unless the system has no inter-component dependencies).
- [ ] Risk categories cover at least 3 of the 7 categories (Performance, Scalability, Integration, Data, Security, Skills, Cost).
- [ ] Components with 3+ high-uncertainty risks are flagged for spike work.

---

## Task 4: Design Technical Spikes for Low-TRL Components

**Goal:** Create spike plans for components below TRL 4 that define what must be proven, how, and by when.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| Components with TRL < 4 | Task 2 | Yes |
| Technical risk inventory (high-uncertainty risks) | Task 3 | Yes |
| Team skills and available resources | Founder/team | Yes |

**Action:**

1. For each component below TRL 4, create a **spike card** containing:
   - **Component ID and name.**
   - **Current TRL and target TRL:** Where you are and where you need to be before M4 Prototypation. Minimum target: TRL 4 (validated in lab). Preferred target: TRL 5 (validated in relevant environment).
   - **Key question:** The single most important technical question this spike must answer. Frame as: "Can we [specific capability] with [specific constraints]?"
   - **Method:** How you will run the spike. Options include:
     - Build a minimal proof-of-concept (code, model, pipeline).
     - Run a benchmark against representative data or load.
     - Evaluate and test a third-party service or library.
     - Consult a domain expert for feasibility assessment.
     - Analyze comparable implementations in adjacent products.
   - **Success criteria:** Specific, measurable outcomes that would advance the TRL. Examples: "Model achieves 85% accuracy on 500-sample test set," "API handles 200 requests/second with <500ms p95 latency," "Third-party service meets all 5 integration requirements."
   - **Failure criteria:** What result would indicate this component cannot be built as conceived. Connect to Leap of Faith kill criteria where applicable.
   - **Estimated effort:** Person-days or person-weeks. Be realistic.
   - **Dependencies:** Other spikes, data, access, or resources needed before this spike can run.
   - **Owner:** Who executes the spike.
2. Also create spike cards for components at TRL 4-5 if they have 3+ high-uncertainty risks from Task 3.
3. Sequence spike cards by:
   - **Critical path first:** Spikes that block other components.
   - **Highest risk first:** Spikes for the most uncertain components.
   - **Quickest wins first:** When two spikes have equal priority, run the faster one first to reduce uncertainty sooner.
4. If no components are below TRL 4, document this explicitly. You still have residual technical risks to track, but no spikes are required before M4.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| Spike cards | Structured cards (one per component needing a spike) | Actionable technical de-risking experiments |
| Spike sequence | Ordered list with dependencies | Execution plan for technical de-risking |

**Validation:**

- [ ] Every component below TRL 4 has a spike card.
- [ ] Each spike card has measurable success and failure criteria (not vague: "see if it works").
- [ ] Spike methods are the lightest-weight approach that produces credible evidence.
- [ ] Total estimated effort for all spikes is realistic given team size and timeline.
- [ ] Spike sequence respects dependency chains.
- [ ] At least one spike card connects failure criteria to a Leap of Faith kill criterion.

---

## Task 5: Estimate De-risking Effort and Wire into Planning

**Goal:** Size the total technical de-risking work, connect findings to downstream milestones, and update project artifacts.

**Inputs:**

| Input | Source | Required |
|-------|--------|----------|
| TRL assessment table | Task 2 | Yes |
| Technical risk inventory | Task 3 | Yes |
| Spike cards and sequence | Task 4 | Yes |
| Project memo | `projects/[project]/founder/[project]_memo.md` | Yes |
| M2 founder diary | `projects/[project]/founder/validation/m2_founder_diary.md` | Yes |

**Action:**

1. Compute the **total de-risking effort**: sum of all spike card estimated effort.
2. Compute the **de-risking timeline**: apply the spike sequence, accounting for dependencies and parallelism.
3. Assess overall technical readiness posture:
   - **Green:** All components TRL 4+, no spikes required, moderate residual risks. Ready for M4 Prototypation.
   - **Yellow:** 1-2 components below TRL 4, spikes required but estimated at under 2 weeks total. Proceed to M4 after spikes.
   - **Red:** 3+ components below TRL 4, or any component below TRL 2 with no clear path forward. Technical feasibility is in serious question. May need to pivot the technical approach or invoke a kill criterion.
4. Create the TRL assessment document at `projects/[project]/founder/validation/technology_readiness_level.md` containing:
   - Component inventory (Task 1).
   - TRL assessment table (Task 2).
   - Technical risk inventory (Task 3).
   - Spike cards and sequence (Task 4).
   - De-risking effort estimate and overall posture (this task).
5. Wire outputs into downstream milestones:
   - **Pre-mortem (M2 Step 7):** Provide technical risks and low-TRL components as failure mode inputs.
   - **M4 Prototypation:** Provide the TRL table and spike results as inputs to architecture decisions and build planning. Components at TRL 4-5 need extra attention during prototypation. Components at TRL 7+ can use standard practices.
   - **M6 MVP:** Provide residual technical risks as inputs to feature scope and launch sequencing. Low-TRL components may need to be descoped from MVP or replaced with simpler alternatives.
6. Update **project memo**:
   - Progress > Validation subsection: note TRL assessment completion and overall posture.
   - Open Questions: add technical unknowns that spikes will address.
   - Solution section: revise if TRL assessment reveals that certain solution elements are technically infeasible.
7. Update **M2 founder diary** with:
   - Entry recording TRL assessment, date, and overall posture (Green/Yellow/Red).
   - List of components below TRL 4 and planned spikes.
   - Any surprises: components that were more or less ready than expected.
   - Any changes to the solution concept driven by technical feasibility.

**Output:**

| Output | Format | Purpose |
|--------|--------|---------|
| TRL assessment document | Markdown in `projects/[project]/founder/validation/` | Canonical technical readiness assessment |
| De-risking effort estimate | Summary with total effort, timeline, and overall posture | Planning input for M4 Prototypation |
| Updated project memo | Progress > Validation, Open Questions, Solution section | Narrative integration of technical readiness findings |
| Updated M2 founder diary | New entries with TRL decisions | Decision trail for technical feasibility assessment |
| Downstream milestone inputs | Flagged risks and TRL table for Pre-mortem, M4, M6 | Ensures downstream work is technically informed |

**Validation:**

- [ ] TRL assessment document exists with all sections (inventory, scores, risks, spikes, effort estimate).
- [ ] Overall technical posture is stated (Green/Yellow/Red) with justification.
- [ ] De-risking effort and timeline are estimated and realistic.
- [ ] Technical risks are flagged for Pre-mortem (M2 Step 7).
- [ ] Project memo and M2 founder diary are updated.
- [ ] At least one output is flagged for M4 Prototypation and at least one for M6 MVP.

---

## Pitfalls

**Overestimating TRL Because "We Could Build That"**

NEVER score TRL based on capability or intent. MUST score based on what has actually been demonstrated with evidence. "We could build that" is TRL 1-2. "We built a proof of concept" is TRL 3. "We ran it in a staging environment" is TRL 5. The evidence must exist, not be imagined.

**Treating All Components as a Single System**

NEVER assess TRL for "the product" as a whole. MUST decompose into components and assess each independently. A product where 4 of 5 components are at TRL 8 and 1 is at TRL 2 is NOT at TRL 7. The weakest component determines the risk profile.

**Ignoring Third-Party Dependencies**

NEVER assume third-party APIs, libraries, or services are at TRL 9 for your use case. MUST assess whether the third-party capability meets YOUR specific requirements (rate limits, data formats, compliance, pricing). A well-known API at TRL 9 in general might be TRL 4 for your particular integration.

**Designing Spikes That Are Actually MVPs**

NEVER let a technical spike expand into a prototype or MVP. A spike answers ONE specific question with the minimum effort necessary. If a spike takes more than 1-2 weeks, it is too broad. MUST split into smaller questions.

**Skipping TRL for "Simple" Products**

NEVER skip TRL assessment because the product seems technically simple. Even a standard web application has components worth assessing: authentication, data migration, third-party integrations, deployment pipeline. The assessment may confirm that everything is TRL 7+, and that is a valuable finding.

---

## Integration

**Prerequisites:** MUST have access to M1 framework outputs (Working Backwards Internal FAQ, Problem-Solution Fit solution concept, Lean Canvas Solution block). Can run in parallel with TAM/SAM/SOM and Unit Economics.

**Builds on:**

| Framework | Output Used | How Used |
|-----------|-------------|----------|
| Working Backwards Internal FAQ (M1) | Technical feasibility questions, architecture assumptions | Provides the initial technical questions to assess and ensures all FAQ concerns are addressed |
| Problem-Solution Fit (M1) | Solution concept (Our Solution block) | Defines what the solution must do, which drives component identification |
| Lean Canvas (M1) | Solution block (top 3-5 capabilities) | Lists the capabilities that must be decomposed into technical components |
| Assumption Mapping (M2) | Technical assumptions flagged for assessment | Identifies which technical assumptions have highest importance and uncertainty |

**Feeds into:**

| Framework | Output Provided | How Used |
|-----------|-----------------|----------|
| Pre-mortem (M2) | Technical risks, low-TRL components, critical path dependencies | Grounds technical failure modes in assessed readiness levels rather than speculation |
| M4 Prototypation | TRL table, spike results, component readiness posture | Informs architecture decisions, build sequencing, and resource allocation |
| M6 MVP | Residual technical risks, TRL-informed feature scope | Determines which features can be built with standard effort and which carry technical risk |

**Workflow Position:** Within M2 Validation, TRL assessment runs at Step 6, in parallel with TAM/SAM/SOM (Step 4) and Unit Economics (Step 5). It feeds into Pre-mortem (Step 7) and provides direct inputs to M4 and M6 milestones.

---

## Success Criteria

This framework is complete when:

- [ ] A component inventory exists with 4-10 technical building blocks, each with type classification and dependency mapping.
- [ ] Every component has a TRL score (1-9) with a one-sentence evidence statement and next-level requirements.
- [ ] A technical risk inventory exists with risks categorized by type and residual uncertainty rated.
- [ ] Every component below TRL 4 has a spike card with measurable success/failure criteria and estimated effort.
- [ ] Overall technical posture is stated (Green/Yellow/Red) with supporting rationale.
- [ ] Total de-risking effort and timeline are estimated and realistic for the team.
- [ ] Technical risks are flagged for Pre-mortem.
- [ ] TRL assessment document is saved in the project validation folder.
- [ ] Project memo and M2 founder diary are updated with technical readiness findings.

---

## References

> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS >= 6

Sources consulted when designing this framework:

- [1] NASA, "Technology Readiness Level Definitions" — `https://www.nasa.gov/directorates/somd/space-communications-navigation-program/technology-readiness-levels/` — Research Date: 2026-01-30 — Source Date: n/a — TS: 9.3 (AT: 10, TR: 10, TM: 8). Authoritative source for the TRL 1-9 scale.
- [2] European Commission, "Technology Readiness Levels (TRL), Horizon 2020 Work Programme" — Research Date: 2026-01-30 — Source Date: 2014 — TS: 8.3 (AT: 9, TR: 9, TM: 7). Adapted TRL definitions for broader technology assessment.
- [3] Steve Blank, "The Four Steps to the Epiphany" (K&S Ranch, 2005) — Research Date: 2026-01-30 — Source Date: 2005 — TS: 7.3 (AT: 8, TR: 8, TM: 6). Customer development methodology that contextualizes technical readiness within startup validation.

Additional conceptual references (books, not scored):

- John C. Mankins, "Technology Readiness Levels: A White Paper," NASA Office of Space Access and Technology, 1995. Original NASA white paper defining the TRL scale.
- Mariana Mazzucato, *Mission Economy* (Allen Lane, 2021). Context on how TRL frameworks apply beyond aerospace to innovation policy and digital ventures.

---

## For AI Agents

**Execution Context:** When executing this framework with a user:

1. MUST confirm that Working Backwards Internal FAQ, Problem-Solution Fit solution concept, and Lean Canvas Solution block exist. If missing, MUST flag and recommend completing them first.
2. MUST read this framework and `validation_process.md` before starting. Track progress explicitly: "Currently in Task [N]: [Task Name]".
3. MUST enforce honest TRL scoring. When user claims a component is TRL 5+, ask: "What concrete evidence supports this? Has it actually been demonstrated in that environment?" Default to the lower score when evidence is ambiguous.
4. MUST prevent TRL inflation for novel components. If a component is typed as Novel but scored above TRL 3, demand proof-of-concept evidence.
5. MUST keep spikes focused on single questions. If a spike plan exceeds 2 weeks estimated effort, propose splitting into smaller experiments.

**Working With Tasks:**

- MUST treat each task as atomic. NEVER skip validation criteria without recording explicit risks or TODOs.
- During Task 1, propose component decomposition based on upstream documents and ask user to validate, add, or remove components.
- During Task 2, walk through the TRL scale level by level for each component. Stop at the highest level with demonstrated evidence.
- During Task 4, generate spike card drafts for the user to review. Ensure each spike has concrete success and failure criteria.
- After Task 5, state the overall posture clearly: "Your technical readiness is [Green/Yellow/Red] because [reasons]. This means [implications for M4]."

**Red Flags:**

- All components scored TRL 7+ for a product with Novel-type components (likely over-optimistic).
- No spike cards when multiple components are below TRL 4 (insufficient de-risking).
- Spike estimated effort exceeds 4 weeks total (scope creep or premature MVP building).
- No risks identified for a product with external API dependencies (blind spot).
- User resists honest TRL scoring ("we can definitely build that") — push back with evidence requirements.

---

