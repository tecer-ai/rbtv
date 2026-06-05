---
name: 'step-02-current-trl-assessment'
description: 'Decompose solution into components and rate each on TRL 1-9'
nextStepFile: './step-03-target-trl.md'
outputFile: '{outputFolder}/technology-readiness-level.md'
---

# Step 2: Current TRL Assessment

**Progress: Step 2 of 5** — Next: Target TRL & Risk Analysis

---

## STEP GOAL

Decompose the proposed solution into 4-10 technical components and rate each on the TRL 1-9 scale with explicit evidence supporting each score.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Default to the lower TRL score when evidence is ambiguous. "We could build that" is TRL 1-2. A Jupyter notebook is TRL 3, not TRL 5.

### Step-Specific Rules
- MUST decompose into 4-10 components (fewer = not granular enough; more = too granular)
- MUST score based on DEMONSTRATED evidence, not capability or intent
- MUST classify each component as Novel, Adapted, or Standard
- Novel components should NOT be scored above TRL 3 without proof-of-concept evidence

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/technology-readiness-level.md` for current progress
2. Review solution definition from Step 1
3. Load TRL scale from framework knowledge

---

## MANDATORY SEQUENCE

### 1. Decompose Into Components

Work with user to identify major technical building blocks:

> "Let's decompose your solution into assessable technical components. A component is:
> - Independently assessable for readiness
> - Has a clear function in delivering the solution
> - Could be built, bought, or integrated separately
>
> Aim for 4-10 components. What are the major technical building blocks?"

For each component, document:

| Field | Description |
|-------|-------------|
| **ID** | Short label (TC-01, TC-02, etc.) |
| **Name** | Descriptive name |
| **Description** | What it does and why needed |
| **Type** | Novel / Adapted / Standard |
| **Dependencies** | Other components or external systems |
| **Existing Assets** | Code, prototypes, or third-party options |

### 2. Create Component Inventory

Build the inventory table:

| ID | Name | Type | Description | Dependencies | Existing Assets |
|----|------|------|-------------|--------------|-----------------|
| TC-01 | [Name] | [Novel/Adapted/Standard] | [One paragraph] | [List] | [List] |
| TC-02 | [Name] | [Novel/Adapted/Standard] | [One paragraph] | [List] | [List] |
| ... | ... | ... | ... | ... | ... |

### 3. Validate Component Coverage

Check coverage:
- [ ] Every capability in Lean Canvas Solution block maps to at least one component
- [ ] Component count is between 4 and 10
- [ ] Dependencies between components are documented
- [ ] Each component has clear type classification

If gaps, add missing components.

### 4. Score Each Component on TRL

For each component, walk through the TRL scale:

**TRL Scale Reference:**

| TRL | Evidence Required | Examples |
|-----|-------------------|----------|
| 1 | Basic principles understood | "We know transformers can classify text" |
| 2 | Concept formulated for this problem | "We believe BERT could classify our tickets" |
| 3 | Proof of concept in controlled setting | "Jupyter notebook shows 85% accuracy on sample" |
| 4 | Works in dev with representative data | "Classifier built in dev with production-like data" |
| 5 | Works in staging approximating production | "Runs on staging with real API calls" |
| 6 | Tested with real users/data | "10 beta users tested on their data" |
| 7 | Prototype in real environment | "Running in production for 50 users" |
| 8 | Fully integrated and meeting requirements | "Production at scale, meeting SLA" |
| 9 | Track record of reliable operation | "6 months production, 99.9% uptime" |

**Scoring Process:**
For each component, ask:
> "What is the highest TRL level for which you have CONCRETE EVIDENCE?"

**Component TRL Template:**

| ID | Name | TRL | Evidence | Next TRL Requirement | Risk Level |
|----|------|-----|----------|---------------------|------------|
| TC-01 | [Name] | [1-9] | [One sentence evidence] | [What's needed to advance] | [High/Med/Low] |

**Type-Based Defaults:**
- **Standard** components: Typical TRL 6-8 unless specific use case adds constraints
- **Adapted** components: Typical TRL 3-5 depending on adaptation complexity
- **Novel** components: Typical TRL 1-3; cannot be higher without demonstrated PoC

### 5. Flag High-Risk Components

Identify risk levels:

| TRL Range | Risk Level | Action |
|-----------|------------|--------|
| TRL 1-3 | 🔴 High | Spike required before M4 |
| TRL 4-5 | 🟡 Moderate | Extra attention in M4 |
| TRL 6-9 | 🟢 Low | Standard engineering |

> "Components at TRL 1-3 are HIGH RISK. These need technical spikes to de-risk before M4 Prototypation."

### 6. Challenge Inflated Scores

If user claims Novel component is TRL 5+:
> "Hold on. You classified [component] as Novel but scored it TRL [X]. 
> 
> Novel means new approach. TRL [X] requires [evidence requirement].
>
> What concrete evidence supports this? Has it actually been demonstrated in that environment?"

If no evidence, score lower.

### 7. Update Output Document

Update technology-readiness-level.md with:
- Component Inventory table
- TRL Scores table with evidence
- Risk level for each component

Update frontmatter: add `step-02-current-trl-assessment` to `stepsCompleted`

### 8. Present Menu Options

**Summary:**
> "Components assessed: [N]
> - High risk (TRL 1-3): [N] components
> - Moderate risk (TRL 4-5): [N] components
> - Low risk (TRL 6-9): [N] components"

**Select an Option:**
- **[C] Continue** — proceed to Target TRL & Risk Analysis
- **[R] Refine** — revisit component scores

ALWAYS halt and wait for user selection.

---

## VALIDATION CHECKLIST

Before proceeding, verify:
- [ ] Component count is 4-10
- [ ] Every component has TRL score with one-sentence evidence
- [ ] No Novel component is scored above TRL 3 without PoC evidence
- [ ] Standard components are scored TRL 6+ unless constraints lower them
- [ ] Dependencies between components are documented

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all validation checklist items pass
2. Ensure technology-readiness-level.md is updated
3. Load `./step-03-target-trl.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 4-10 components identified, each scored with evidence, risk levels flagged

❌ **FAILURE:** Scoring based on capability not evidence, Novel components at TRL 5+
