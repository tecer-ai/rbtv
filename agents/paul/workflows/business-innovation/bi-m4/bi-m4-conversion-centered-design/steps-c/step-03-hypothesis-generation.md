---
name: 'step-03-hypothesis-generation'
description: 'Generate optimization hypotheses based on friction analysis'
nextStepFile: './step-04-optimization-plan.md'
outputFile: '{outputFolder}/conversion-optimization.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 3: Hypothesis Generation

**Progress: Step 3 of 5** — Next: Optimization Plan

---

## STEP GOAL

Generate testable optimization hypotheses for each significant friction point, grounded in CCD principles. Each hypothesis must be specific, measurable, and linked to a conversion principle.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for specificity. Vague hypotheses ("make it better") are useless. Every hypothesis must predict a measurable outcome and explain WHY based on conversion principles.

### Step-Specific Rules
- Focus on Severity 5-3 friction points first (Critical, Major, Moderate)
- Every hypothesis must follow the IF/THEN/BECAUSE template
- Link each hypothesis to a specific CCD principle
- Generate 2-3 alternative hypotheses for top friction points

---

## CONTEXT BOUNDARIES

**Available context:**
- conversion-optimization.md with Funnel Analysis and Friction Points
- data/conversion-framework.md for CCD principles
- user-flow-ia.md for structural reference

**Out of scope:**
- Implementation details (how to code the fix)
- Prioritization (Step 4)
- A/B testing methodology specifics

---

## MANDATORY SEQUENCE

### 1. Review Friction Points

Load friction points from Step 2, sorted by severity:

> "From our friction analysis, here are the issues to address:
> 
> **Critical (5):** [list]
> **Major (4):** [list]
> **Moderate (3):** [list]
> 
> We'll generate hypotheses for all Critical and Major issues, and select Moderate issues. Minor and Cosmetic can be addressed opportunistically."

### 2. Hypothesis Generation — Top Friction Points

For each Critical and Major friction point, generate 1-3 hypotheses using the template:

```
**Hypothesis [N]: [Short Name]**

IF we [specific change]
THEN we expect [metric] to [increase/decrease] by [estimated amount]
BECAUSE [rationale based on CCD principle]

**Linked Principle:** [Attention Ratio / Visual Hierarchy / Directional Cues / Friction Reduction / Urgency / Encapsulation / Congruence]

**Addresses Friction:** [Friction point #N from Step 2]
```

**Example:**
```
**Hypothesis 1: Remove Nav Menu**

IF we remove the navigation menu from the landing page
THEN we expect CTA click rate to increase by 15-25%
BECAUSE attention ratio improves from 8:1 to 1:1 (Attention Ratio principle)

**Linked Principle:** Attention Ratio
**Addresses Friction:** #2 - Multiple competing links dilute focus
```

Present each hypothesis and ask for founder input:
> "For friction point [N], here's my hypothesis:
> [Hypothesis]
> 
> Does this make sense? Any concerns?"

### 3. CTA Optimization Hypotheses

Generate specific CTA optimization hypotheses covering:

**Copy:**
> "IF we change CTA from '[current]' to '[proposed]'
> THEN we expect [metric] because [rationale]"

**Placement:**
> "IF we add a CTA [above fold / after testimonials / etc.]
> THEN we expect [metric] because [rationale]"

**Visual:**
> "IF we increase CTA contrast to [specific change]
> THEN we expect [metric] because [rationale]"

### 4. Alternative Hypotheses for Key Issues

For the top 2-3 friction points, generate alternative hypotheses:

> "For friction point [N], I have two alternative approaches:
> 
> **Option A:** [Hypothesis A]
> **Option B:** [Hypothesis B]
> 
> Option A is [safer/bolder], Option B is [cheaper/more impactful]. Which resonates more?"

Document founder's preference and rationale.

### 5. Hypothesis Summary Table

Compile all hypotheses into a summary:

| # | Hypothesis | Friction | Principle | Expected Impact | Effort Est. |
|---|------------|----------|-----------|-----------------|-------------|
| 1 | [Name] | [#N] | [Principle] | [+X% metric] | [Low/Med/High] |

Present table to founder:
> "Here's our hypothesis backlog. In Step 4, we'll prioritize these into a testing roadmap."

### 6. Update Output Document

Add to conversion-optimization.md:

```markdown
## Optimization Hypotheses

### Critical Friction Hypotheses

#### Hypothesis 1: [Name]
**IF** we [change]
**THEN** we expect [metric] to [change] by [amount]
**BECAUSE** [rationale]

- **Linked Principle:** [Principle]
- **Addresses Friction:** #[N]
- **Effort Estimate:** [Low/Med/High]

[Repeat for each hypothesis]

### CTA Optimization Hypotheses

#### Copy
[Hypothesis]

#### Placement
[Hypothesis]

#### Visual
[Hypothesis]

### Hypothesis Summary

| # | Hypothesis | Friction | Principle | Expected Impact | Effort |
|---|------------|----------|-----------|-----------------|--------|
| 1 | ... | ... | ... | ... | ... |
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-funnel-mapping', 'step-03-hypothesis-generation']
```

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Optimization Plan

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify Optimization Hypotheses section is complete
2. Verify at least one hypothesis exists for each Critical/Major friction point
3. Verify frontmatter updated with `step-03-hypothesis-generation`
4. Load `./step-04-optimization-plan.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All Critical/Major friction points have hypotheses, each hypothesis follows IF/THEN/BECAUSE template, linked to CCD principles, founder validated key hypotheses

❌ **FAILURE:** Vague hypotheses without metrics, missing principle linkage, skipping founder input, implementing solutions instead of hypothesizing
