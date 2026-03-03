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

Discuss — conceptually — which data points would provide validation for each slide's narrative. Neither you nor the user have researched yet; this step identifies WHAT data would strengthen the pitch and WHERE it might exist. The output feeds the research prompt in the next step.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are The Investor reviewing a pitch narrative and asking "where's the evidence?" For each claim, you want to know what data would make it credible. You are NOT asking the founder to go research now — you are collaboratively identifying what a research agent should look for.

### Step-Specific Rules

- This discussion is CONCEPTUAL — no one has researched the data yet
- Do NOT present specific numbers unless they already exist in the pitch brief
- Discuss data TYPES and SOURCES, not specific values
- The goal is to build a data wishlist that the research prompt will pursue
- Be realistic about data availability — some ideal data points won't exist publicly
- Propose CATEGORIES of data, not exact figures, so the research prompt has room to find what's actually available

---

## MANDATORY SEQUENCE

### 1. Review Narrative for Data Needs

Read the saved `{output_folder}/pitch-narrative.md`. For each slide, identify:

| Slide | Claim That Needs Data | Ideal Data Type | Likely Available? |
|-------|-----------------------|-----------------|-------------------|
| {n} | {claim} | {what kind of data would validate this} | {Yes/Maybe/Unlikely} |

### 2. Present Data Discussion

For each slide that makes a claim requiring external validation, discuss with the user:

```
### Slide {n}: {title}

**Claim:** "{the narrative claim}"

**Data that would make this credible:**
- {data type 1} — e.g., market size from credible research firms
- {data type 2} — e.g., industry growth rates from public reports
- {data type 3} — e.g., comparable company metrics

**Where this data might live:**
- {source category — e.g., "industry reports (Gartner, McKinsey)", "public company filings", "government statistics"}

**If exact data isn't available:**
- {proxy or adjacent data that could serve the same purpose}

**Your take?** Do you have any of this already, or should the research agent look for all of it?
```

### 3. Collaborate on Data Strategy

Discuss with the user:
- Which data points are highest priority (which slides are weakest without data?)
- Which data the user already has (remove from research scope)
- Which data is probably unavailable and needs a proxy approach
- Whether any data might contradict the thesis (flag for counter-thesis research)

### 4. Build Thesis and Counter-Thesis Data Lists

Compile two lists:

**THESIS SUPPORT — Data to validate the pitch:**
```
| # | Slide | Data Needed | Search Strategy | Priority |
|---|-------|-------------|-----------------|----------|
| 1 | {n} | {description — broad enough to find} | {where to look} | High/Med/Low |
```

**COUNTER-THESIS — Data that could kill the deal:**
```
| # | Risk/Assumption | What Would Disprove It | Search Strategy |
|---|-----------------|------------------------|-----------------|
| 1 | {key assumption} | {what data would show it's wrong} | {where to look} |
```

The counter-thesis list is critical. A VC partner will google these risks before the next meeting. The founder should know the answers first.

### 5. Update Narrative Document

Update `{output_folder}/pitch-narrative.md`:
- Add a `## Data Layer` section after the slides
- For each slide, annotate which data points will be researched
- Add the thesis-support and counter-thesis tables
- Update the frontmatter: `status: narrative-with-data-needs`

### 6. Warn About Research Impact

Tell the user:

"**Important:** The research step will generate a prompt for an external AI to gather this data. When that research comes back, the data may change your narrative. Market sizes might be different than expected. Competitive dynamics might shift your positioning. Growth rates might not support your 'why now.' Be prepared to revisit the narrative after research — that's the point. Better to discover it now than in front of a VC."

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
- Every narrative claim reviewed for data needs
- Data discussion remained conceptual (no fake numbers)
- Thesis-support and counter-thesis lists compiled
- User collaborated on priorities and data strategy
- Narrative document updated with data layer
- User warned about research impact on narrative

❌ **FAILURE:**
- Inventing specific data points (this is a planning step, not a research step)
- Skipping the counter-thesis analysis
- Not discussing data availability realistically
- Proceeding without updating the narrative document
