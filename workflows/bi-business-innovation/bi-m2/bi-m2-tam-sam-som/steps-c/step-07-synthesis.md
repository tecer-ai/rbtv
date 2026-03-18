---
name: 'step-07-synthesis'
description: 'Synthesize findings and update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/tam-sam-som.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 7: Synthesis

**Progress: Step 7 of 7** — Final Step

---

## STEP GOAL

Synthesize TAM/SAM/SOM findings into a concise summary, extract inputs for Unit Economics, wire fragile assumptions to Assumption Mapping, and UPDATE project-memo.md.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate the clarity achieved. Be honest about uncertainties. Note what needs validation.

### Step-Specific Rules
- project-memo.md MUST be updated with TAM/SAM/SOM synthesis
- Extract Unit Economics inputs explicitly
- Wire fragile assumptions to Assumption Mapping
- Mark framework as completed in project-memo frontmatter

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/tam-sam-som.md` for complete analysis
2. Read `{outputFolder}/project-memo.md` for update
3. Read `{outputFolder}/assumption-mapping.md` for assumption updates (if exists)

---

## MANDATORY SEQUENCE

### 1. Review Completed Work

Summarize what was accomplished:

> "Let's review what we built:
>
> - **TAM:** $[range] — the total market for [category] if everyone bought
> - **SAM:** $[range] — what we can serve given our constraints
> - **SOM:** $[range] Year 1, $[range] Year 3 — what we can realistically capture
> - **Confidence:** TAM [level], SAM [level], SOM [level]
> - **Top fragile assumption:** [The #1 assumption that could change everything]"

### 2. Extract Unit Economics Inputs

> "These figures feed directly into Unit Economics:
>
> | Input | Value | Source |
> |-------|-------|--------|
> | Year 1 customers | [N] | SOM calculation |
> | Year 2 customers | [N] | SOM calculation |
> | Year 3 customers | [N] | SOM calculation |
> | ARPU | $[range] | Market Definition Brief |
> | Churn rate | [X]% | SOM assumptions |
> | Net revenue retention | [X]% | SOM assumptions |
>
> When you run Unit Economics, use these inputs directly."

### 3. Wire to Downstream Frameworks

**Assumption Mapping:**
> "These fragile assumptions need to go into your Assumption Map:
>
> 1. [Assumption 1] — needs [validation method]
> 2. [Assumption 2] — needs [validation method]
> 3. [Assumption 3] — needs [validation method]
>
> If Assumption Mapping is complete, add these. If not, note them for when you run it."

**Pre-mortem:**
> "These market risk scenarios should feed into Pre-mortem:
>
> - Market too small: [What if TAM is 50% of estimate?]
> - Wrong segment: [What if your SAM narrowing is off?]
> - Slow capture: [What if SOM Year 1 is 50% of estimate?]"

### 4. Draft Framework Synthesis

Create a concise synthesis (300 words max):

**Market Summary:**
- TAM: $[range] (confidence: [level])
- SAM: $[range] (confidence: [level])
- SOM Year 1-3: $[Y1] → $[Y3] (confidence: [level])

**Key Findings:**
- [Insight 1 about market size or structure]
- [Insight 2 about constraints or opportunities]
- [Insight 3 about validation needs]

**Fragile Assumptions:**
- Top 3 that need validation before committing

**Next Steps:**
- Unit Economics to model LTV/CAC using these inputs
- Assumption Mapping to prioritize validation tests
- Pre-mortem to stress-test market scenarios

### 5. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/workflows/bi-business-innovation/data/founder-process.md` for M2.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 6. Update tam-sam-som.md

Add Synthesis section:

```markdown
## Synthesis

### Market Summary

| Layer | Range | Confidence |
|-------|-------|------------|
| TAM | $[low]–$[high] | [H/M/L] |
| SAM | $[low]–$[high] | [H/M/L] |
| SOM Y1 | $[low]–$[high] | [H/M/L] |
| SOM Y2 | $[low]–$[high] | [H/M/L] |
| SOM Y3 | $[low]–$[high] | [H/M/L] |

### Key Findings

1. [Insight 1]
2. [Insight 2]
3. [Insight 3]

### Unit Economics Inputs

| Input | Value | Notes |
|-------|-------|-------|
| Y1 Customers | [N] | From SOM |
| Y2 Customers | [N] | From SOM |
| Y3 Customers | [N] | From SOM |
| ARPU | $[range] | From Market Definition |
| Churn | [X]% | From SOM |
| NRR | [X]% | From SOM |

### Fragile Assumptions for Validation

1. [Assumption 1] — validate via [method]
2. [Assumption 2] — validate via [method]
3. [Assumption 3] — validate via [method]

### Market Risk Scenarios for Pre-mortem

- TAM overestimated: [Impact]
- SAM narrowing wrong: [Impact]
- SOM capture slow: [Impact]
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-boundaries', 'step-03-tam', 'step-04-sam', 'step-05-som', 'step-06-stress-test', 'step-07-synthesis']
status: completed
```

### 7. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m2-tam-sam-som` to `stepsCompleted` array

**In Progress > M2 Validation section:**

```markdown
### TAM/SAM/SOM

**Status:** Completed

**Market Summary:**
- TAM: $[range] ([confidence])
- SAM: $[range] ([confidence])
- SOM Y1: $[range], Y3: $[range] ([confidence])

**Key Finding:** [One-sentence insight]

**Fragile Assumptions:** [Top 2-3]

**Unit Economics Inputs:** Extracted for downstream use

**Output:** [Link to tam-sam-som.md]
```

### 8. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 9. Completion Summary

Present to founder:
> "TAM/SAM/SOM market sizing complete!
>
> **What we achieved:**
> - Sized market with both top-down and bottom-up methods
> - Built SOM from actual go-to-market capacity
> - Identified [N] fragile assumptions needing validation
> - Extracted inputs for Unit Economics
>
> **What's next:**
> - Unit Economics to model LTV/CAC/payback
> - Assumption Mapping to prioritize validation tests
> - Pre-mortem to explore failure scenarios
>
> **Return path:** To continue other M2 frameworks, return to bi-m2 milestone workflow."

### 10. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M2.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M2 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 11. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M2** — return to M2 Validation milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M2** is selected:
1. Verify tam-sam-som.md has status: completed
2. Verify project-memo.md has TAM/SAM/SOM entry
3. Load `../bi-m2/workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** tam-sam-som.md complete with synthesis, project-memo.md updated, Unit Economics inputs extracted, fragile assumptions wired

❌ **FAILURE:** project-memo.md not updated, Unit Economics inputs not extracted, fragile assumptions not connected to downstream
