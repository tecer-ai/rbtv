---
stepNumber: 4
stepName: 'data-layer'
nextStepFile: ./step-05-research-prompt.md
outputFile: pitch-narrative.md
---

# Step 04: Conceptual Data Layer

**Progress: Step 4 of 9** — Next: Research Prompt

---

## STEP GOAL

Discuss — conceptually — which data and proof points would make each slide credible to a buyer. Neither you nor the user have researched yet; this step identifies WHAT evidence would win the deal and WHERE it might exist. The output feeds the research prompt in the next step.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are The Buyer reviewing a pitch narrative and asking "where's the proof?" For each claim, you want to know what evidence would make it credible to a procurement committee. You are NOT asking the founder to go research now — you are collaboratively identifying what a research agent should look for.

### Step-Specific Rules

- This discussion is CONCEPTUAL — no one has researched the data yet
- Do NOT present specific numbers unless they already exist in the pitch brief
- Discuss data TYPES and SOURCES, not specific values
- Client pitches need different proof than investor pitches: ROI calculations, case studies, industry benchmarks, implementation success rates, customer satisfaction metrics
- Be realistic about data availability
- Propose CATEGORIES of data so the research prompt has room to find what's actually available

---

## MANDATORY SEQUENCE

### 1. Review Narrative for Proof Needs

Read the saved `{output_folder}/pitch-narrative.md`. For each slide, identify:

| Slide | Claim That Needs Proof | Ideal Proof Type | Likely Available? |
|-------|-----------------------|------------------|-------------------|
| {n} | {claim} | {what evidence would validate this for a buyer} | {Yes/Maybe/Unlikely} |

### 2. Present Proof Discussion

For each slide that makes a claim requiring external validation, discuss with the user:

```
### Slide {n}: {title}

**Claim:** "{the narrative claim}"

**Proof a buyer would accept:**
- {proof type 1} — e.g., case study from similar company/industry
- {proof type 2} — e.g., industry benchmark showing cost of status quo
- {proof type 3} — e.g., ROI calculation framework with real inputs

**Where this proof might exist:**
- {source category — e.g., "customer success stories", "industry reports", "analyst reviews", "G2/Capterra reviews"}

**If direct proof isn't available:**
- {proxy or adjacent proof that could serve — e.g., "industry-wide cost data that implies ROI"}

**Your take?** Do you have any of this already, or should the research agent look for all of it?
```

### 3. Collaborate on Proof Strategy

Discuss with the user:
- Which proof points are highest priority (which slides are weakest without them?)
- Which proof the user already has (case studies, testimonials, pilot data)
- Which proof is probably unavailable and needs a proxy approach
- What buyer objections would arise from LACK of proof on specific slides

### 4. Build Proof and Objection Lists

Compile two lists:

**PROOF SUPPORT — Evidence to validate the pitch:**
```
| # | Slide | Proof Needed | Search Strategy | Priority |
|---|-------|-------------|-----------------|----------|
| 1 | {n} | {description — broad enough to find} | {where to look} | High/Med/Low |
```

**BUYER OBJECTIONS — What a skeptical buyer would push back on:**
```
| # | Objection | What Would Address It | Search Strategy |
|---|-----------|----------------------|-----------------|
| 1 | {objection the buyer would raise} | {what data/proof would defuse it} | {where to look} |
```

The objection list is critical. A procurement team will raise these in the evaluation. The vendor should have answers ready.

Common buyer objections to research:
- "What's the real total cost of ownership?" (hidden costs, integration costs, training)
- "Who else in our industry uses this?" (references, case studies)
- "What happens if this doesn't work?" (risk mitigation, SLAs, exit clauses)
- "How does this compare to [specific competitor]?" (feature/price comparison)
- "What's the implementation risk?" (timeline, resources, disruption)

### 5. Update Narrative Document

Update `{output_folder}/pitch-narrative.md`:
- Add a `## Data Layer` section after the slides
- For each slide, annotate which proof points will be researched
- Add the proof-support and buyer-objections tables
- Update the frontmatter: `status: narrative-with-data-needs`

### 6. Warn About Research Impact

Tell the user:

"**Important:** The research step will generate a prompt for an external AI to gather this proof. When that research comes back, some claims may need adjustment. Industry benchmarks might not support your ROI numbers. Competitor comparisons might reveal gaps. Better to discover this now than have a buyer point it out in a meeting."

### 7. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to research prompt generation
- **[X] Exit** — exit workflow (narrative with data needs is saved)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Load `{nextStepFile}` and carry the data layer forward

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Every narrative claim reviewed for proof needs
- Proof discussion remained conceptual (no fake data)
- Proof-support and buyer-objection lists compiled
- User collaborated on priorities
- Narrative document updated with data layer
- User warned about research impact

❌ **FAILURE:**
- Inventing specific data points
- Skipping the buyer objection analysis
- Not discussing proof availability realistically
- Focusing on investor-style data (TAM/SAM) instead of buyer-style proof (ROI, case studies)
