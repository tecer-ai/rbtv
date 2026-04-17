---
name: 'step-05-samples'
description: 'Write sample copy for 5 common scenarios'
nextStepFile: './step-06-synthesis.md'
outputFile: '{outputFolder}/tone-of-voice.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 5: Sample Copy

**Progress: Step 5 of 6** — Next: Synthesis

---

## STEP GOAL

Produce reference copy (3-5 sentences each) for five common brand scenarios that demonstrate the full tone system in action.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Demand specificity. Generic copy defeats the purpose. Every sample should be usable as a starting template.

### Step-Specific Rules
- All 5 scenarios MUST have sample copy
- Each sample must be 3-5 sentences
- Each sample must have annotations showing dimensions and context adjustments applied
- All samples must sound like the SAME brand in different situations
- Brand promise must be audible in at least 3 samples

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/tone-of-voice.md` with Dimensions, Examples, and Context Adjustments
2. Read `{outputFolder}/messaging-architecture.md` for brand promise and key messages (if exists)
3. Read `{outputFolder}/brand-positioning.md` for positioning reference (if exists)
4. Have brand product/service specifics available

---

## MANDATORY SEQUENCE

### 1. Review Five Scenarios

Present the sample copy scenarios:

| # | Scenario | Context | Length | Purpose |
|---|----------|---------|--------|---------|
| 1 | **Homepage headline + subhead** | Marketing | 2 sentences | First words visitor reads |
| 2 | **Welcome email** | Onboarding | 3-5 sentences | First post-signup communication |
| 3 | **Error message** | Error/Support | 3-5 sentences | Something failed |
| 4 | **Feature update announcement** | Marketing | 3-5 sentences | New capability shipped |
| 5 | **Customer success story intro** | Marketing | 3-5 sentences | Case study opening |

### 2. Write Sample 1: Homepage Headline + Subhead

```markdown
### Sample 1: Homepage Headline + Subhead

**Context:** Marketing
**Dimensions Applied:** [List baseline + any adjustments]
**Messaging Source:** [Brand promise from Messaging Architecture, if exists]

---

**Headline:** [Single powerful headline — typically 5-10 words]

**Subhead:** [1-2 sentences adding specificity]

---

**Annotation:**
- Dimension [X] at [position]: [How visible in this copy]
- Dimension [Y] at [position]: [How visible in this copy]
- Brand promise connection: [How the promise appears]
```

### 3. Write Sample 2: Welcome Email

```markdown
### Sample 2: Welcome Email

**Context:** Onboarding
**Dimensions Applied:** [List with adjustments per context matrix]
**Reader State:** Just signed up, hopeful but uncertain

---

**Subject:** [Email subject line]

**Body:**
[3-5 sentences welcoming user, acknowledging what they did, explaining what happens next, expressing brand personality]

---

**Annotation:**
- Dimension [X] adjusted to [position]: [Why and how visible]
- Encouragement element: [Where warmth appears]
- Next steps: [Where clarity appears]
- Brand personality: [Where distinctiveness shows]
```

### 4. Write Sample 3: Error Message

```markdown
### Sample 3: Error Message

**Context:** Error/Support
**Dimensions Applied:** [List with adjustments per context matrix]
**Reader State:** Frustrated, anxious, needs clarity

**Scenario:** [Specific error — e.g., payment failed, data import failed, connection timeout]

---

**Error Copy:**
[3-5 sentences: acknowledge what happened, express empathy without being dramatic, state what it means, tell user exactly what to do]

---

**Annotation:**
- Empathy element: [Where/how we acknowledge frustration]
- Clarity element: [Where/how we state what happened]
- Action element: [Where/how we tell user what to do]
- Personality retained: [What brand traits still show through]
- Personality dialed down: [What we avoided in this context]
```

### 5. Write Sample 4: Feature Update Announcement

```markdown
### Sample 4: Feature Update Announcement

**Context:** Marketing
**Dimensions Applied:** [List baseline + any adjustments]
**Scenario:** [Specific new feature or capability]

---

**Announcement:**
[3-5 sentences: name the capability, state the benefit, show enthusiasm appropriately, include CTA]

---

**Annotation:**
- Feature naming: [How we introduced the feature]
- Benefit framing: [How we connected to user value]
- Enthusiasm level: [How dimension position shows]
- CTA: [What we asked user to do]
```

### 6. Write Sample 5: Customer Success Story Intro

```markdown
### Sample 5: Customer Success Story Intro

**Context:** Marketing
**Dimensions Applied:** [List baseline + any adjustments]
**Scenario:** Opening paragraph of case study or testimonial page

---

**Success Story Intro:**
[3-5 sentences: introduce the customer and their context, state their challenge, hint at the outcome]

---

**Annotation:**
- Customer introduction: [How we set up the story]
- Challenge framing: [How we stated the problem]
- Credibility element: [How we built trust]
- Brand voice: [How personality shows in storytelling]
```

### 7. Consistency Check

Read all 5 samples sequentially:

> "Do all 5 samples sound like the SAME brand speaking in different situations? Or does any sample sound like a different company wrote it?"

If inconsistent:
- Identify the outlier sample
- Determine which dimension was inconsistently applied
- Revise until consistent

### 8. Brand Promise Check

Review samples for brand promise visibility:

> "Is the brand promise (or its spirit) audible in at least 3 of 5 samples?"

| Sample | Brand Promise Visible? | How? |
|--------|------------------------|------|
| 1. Homepage | [Yes/No] | [Explain] |
| 2. Welcome | [Yes/No] | [Explain] |
| 3. Error | [Yes/No] | [Explain] |
| 4. Feature | [Yes/No] | [Explain] |
| 5. Success | [Yes/No] | [Explain] |

Target: At least 3 samples with visible promise.

### 9. Usability Check

Ask:

> "Could a new writer use these samples as starting templates for similar scenarios?"

If no:
- Add more detail
- Make samples more complete
- Ensure they're not just fragments

### 10. Compile All Samples

```markdown
## Sample Copy

### Overview

| Scenario | Context | Dimensions | Promise Visible? |
|----------|---------|------------|-----------------|
| Homepage | Marketing | [List] | [Yes/No] |
| Welcome | Onboarding | [List] | [Yes/No] |
| Error | Error/Support | [List] | [Yes/No] |
| Feature | Marketing | [List] | [Yes/No] |
| Success | Marketing | [List] | [Yes/No] |

### Samples

[All 5 samples with annotations]
```

### 11. Update Output Document

Add Sample Copy section to tone-of-voice.md.

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-dimensions', 'step-03-examples', 'step-04-adjustments', 'step-05-samples']
```

### 12. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Synthesis

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all 5 samples written (3-5 sentences each)
2. Verify all samples have annotations
3. Verify consistency check passed
4. Verify brand promise visible in 3+ samples
5. Load `./step-06-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 5 samples written with annotations, all sound like same brand, brand promise in 3+, usable as templates, error message shows empathy and clarity

❌ **FAILURE:** Missing samples, generic copy, inconsistent voice across samples, promise invisible, samples not usable as templates
