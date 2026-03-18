---
name: 'step-03-internal-facets'
description: 'Define receiver facets: Reflection, Self-Image'
nextStepFile: './step-04-prism-synthesis.md'
outputFile: '{outputFolder}/brand-prism.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 3: Internal Facets

**Progress: Step 3 of 5** — Next: Prism Synthesis

---

## STEP GOAL

Define the two receiver-side facets: Reflection (how customers appear to others) and Self-Image (how customers feel internally).

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Reflection and Self-Image are about the CUSTOMER, not the brand. If statements describe the brand's image, redirect. This is where deep brand loyalty forms.

### Step-Specific Rules
- Reflection traces to JTBD social jobs — how customers want to be PERCEIVED
- Self-Image traces to JTBD emotional jobs — how customers want to FEEL
- These two facets must be DISTINCT — external perception vs internal feeling
- Do not let Reflection and Self-Image overlap or blur together

---

## CONTEXT TO LOAD

1. Read current `{outputFolder}/brand-prism.md` for progress
2. Read `{outputFolder}/jtbd.md` or JTBD summary from project-memo
3. Read Working Backwards customer quote and narrative

---

## MANDATORY SEQUENCE

### 1. Explain the Distinction

Clarify Reflection vs Self-Image before eliciting:

> "These next two facets are about your CUSTOMER, not your brand:
>
> **Reflection** = How others perceive someone who uses your brand
> 'My colleagues think I am...'
>
> **Self-Image** = How the customer feels internally
> 'When I use this, I feel...'
>
> The test: Reflection is what others would say about the customer. Self-Image is what the customer would say to themselves alone."

### 2. Define Reflection

Ground in JTBD social jobs:

> "From your JTBD analysis, here are the social jobs — how customers want to be perceived by others:"

Present social jobs from JTBD analysis.

**Elicit Reflection statements:**

For each social job, translate to Reflection:
> "A person who uses [brand] is seen as _____."

Guide toward 3-5 statements that are:
- About how OTHERS perceive the customer
- Aspirational but believable
- Grounded in actual social jobs

**Validate each statement:**

> "Would a customer's colleague actually say this about them because they use your product?"

If the statement is about the brand's image (not customer's), redirect:
> "That describes your brand, not your customer. How do others perceive the CUSTOMER differently because they use you?"

**Output:** 3-5 Reflection statements traced to social jobs

### 3. Define Self-Image

Ground in JTBD emotional jobs:

> "From your JTBD analysis, here are the emotional jobs — how customers want to feel:"

Present emotional jobs from JTBD analysis.

**Elicit Self-Image statements:**

For each emotional job, translate to Self-Image:
> "When I use [brand], I feel _____."

Guide toward 3-5 statements that are:
- About internal feelings
- Connected to the before/after emotional transformation
- Private, not performative

**Connect to Problem-Solution Fit:**

> "Think about the emotional before state (anxious, overwhelmed, uncertain) and the after state. Self-Image is the after state."

**Validate each statement:**

> "If the customer is using your product alone with no one watching, is this how they would describe their feeling?"

If the statement is about external perception, redirect:
> "That's about how others see them. How do they feel INTERNALLY?"

**Output:** 3-5 Self-Image statements traced to emotional jobs

### 4. Test Reflection/Self-Image Distinction

Present both facets side by side:

> "Let's verify these are distinct:
>
> **Reflection (external):** [statements]
>
> **Self-Image (internal):** [statements]"

**Ask:**
> "Do these feel like different things? Or do they blur together?"

**Example of proper distinction:**
- Reflection: "My colleagues think I am organized and ahead of the curve."
- Self-Image: "I feel confident that I haven't missed anything important."

If overlap detected:
- Identify which statements are misplaced
- Revise to sharpen the external/internal distinction
- Document revision reasoning

### 5. Update brand-prism.md

Update the Receiver Facets section with:
- Reflection: 3-5 statements with traced social jobs
- Self-Image: 3-5 statements with traced emotional jobs

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-external-facets', 'step-03-internal-facets']
```

### 6. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine Reflection or Self-Image
- **[C] Continue** — proceed to Prism Synthesis (Relationship + Coherence)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure both receiver facets are documented
2. Verify Reflection and Self-Image are distinct
3. Verify `step-03-internal-facets` is in `stepsCompleted`
4. Load `./step-04-prism-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Reflection traces to social jobs and describes customer's external image, Self-Image traces to emotional jobs and describes internal feeling, the two facets are clearly distinct

❌ **FAILURE:** Reflection describes the brand instead of customer, Self-Image and Reflection overlap, statements not grounded in JTBD evidence
