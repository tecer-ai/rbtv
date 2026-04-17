---
name: 'step-03-draft'
description: 'Draft positioning statement using template with annotations'
nextStepFile: './step-04-map.md'
outputFile: '{outputFolder}/brand-positioning.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 3: Draft Positioning Statement

**Progress: Step 3 of 6** — Next: Create Perceptual Map

---

## STEP GOAL

Write a single-sentence positioning statement using the template structure, with each element deliberately chosen and annotated.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Reject vague language. Push for specificity in every element. Challenge hedging words ("helps", "aims to", "strives to").

### Step-Specific Rules
- Draft 2-3 variations before selecting final
- Every element must be annotated with strategic reasoning
- No hedging language in final draft
- Benefit must be outcome, not feature

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/brand-positioning.md` with Positioning Inputs Brief
2. Keep Golden Circle Why and How readily accessible

---

## MANDATORY SEQUENCE

### 1. Present Template

Explain the positioning statement template:

> "For **[target segment]** who **[need/job]**, **[brand]** is the **[category]** that **[key benefit]**, unlike **[primary alternative]** which **[key limitation]**."

Walk through each element:
- **Target segment** — Specific enough to picture a real person/org
- **Need/job** — Functional or emotional job in customer language
- **Category** — Category customers already recognize and budget for
- **Key benefit** — Single most important outcome (Golden Circle Why made tangible)
- **Primary alternative** — What target most likely uses today
- **Key limitation** — Real, acknowledged shortcoming of that alternative

### 2. Draft Variation 1

Using the Positioning Inputs Brief, fill each element:

| Element | Choice | Source |
|---------|--------|--------|
| Target segment | [From Inputs Brief Target] | Lean Canvas, WB |
| Need/job | [From Inputs Brief Need] | JTBD, Lean Canvas |
| Category | [From Inputs Brief Category] | Golden Circle What |
| Key benefit | [From Inputs Brief Benefit] | Golden Circle Why |
| Primary alternative | [From Inputs Brief Alternatives #1] | Competitive landscape |
| Key limitation | [That alternative's real weakness] | Competitive analysis |

Write draft: "For [target] who [need], [brand] is the [category] that [benefit], unlike [alternative] which [limitation]."

Present and ask for feedback.

### 3. Draft Variation 2

Vary one or more of:
- **Target specificity** — Narrower or broader segment
- **Category frame** — Adjacent category, category with modifier
- **Competitive alternative** — Different alternative (maybe "do nothing")

Document why you varied each element.

### 4. Draft Variation 3 (Optional)

If first two drafts reveal additional strategic questions, create third variation exploring a different positioning direction.

### 5. Compare and Annotate

For each variation, annotate:

```markdown
### Variation N Analysis

**Target choice:** [Why this target over broader/narrower?]
**Category choice:** [Why this category and not adjacent one?]
**Alternative choice:** [Why this alternative and not another?]
**Benefit choice:** [How does this connect to Why?]
**Limitation choice:** [Is this real and hard for them to fix?]
```

### 6. Selection Criteria

Evaluate each variation against:

| Criterion | V1 Score | V2 Score | V3 Score |
|-----------|----------|----------|----------|
| **Uniqueness** — No competitor could use this exact statement | 0-3 | 0-3 | 0-3 |
| **Defensibility** — Can deliver on claim with current/near-term capabilities | 0-3 | 0-3 | 0-3 |
| **Relevance** — Target cares deeply about stated benefit | 0-3 | 0-3 | 0-3 |
| **Credibility** — Claim is believable given what target knows | 0-3 | 0-3 | 0-3 |
| **Total** | | | |

Present scores and recommend strongest variation.

### 7. Finalize Draft

With user confirmation, write final draft:
- Single sentence following template exactly
- Remove ALL hedging language (helps, aims to, strives to, tries to)
- Use direct, assertive language

```markdown
## Draft Positioning Statement

**Statement:**
"For [final target] who [final need], [brand] is the [final category] that [final benefit], unlike [final alternative] which [final limitation]."

**Element Annotations:**

**Target:** [Choice] — Rationale: [Why this target]
**Need:** [Choice] — Rationale: [Why this job framing]
**Category:** [Choice] — Rationale: [Why this category]
**Benefit:** [Choice] — Rationale: [How connects to Why]
**Alternative:** [Choice] — Rationale: [Why strongest alternative]
**Limitation:** [Choice] — Rationale: [Why this limitation is real and hard to fix]
```

### 8. Update Output Document

Add Draft Positioning Statement section to brand-positioning.md.

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-inputs', 'step-03-draft']
```

### 9. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Create Perceptual Map

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify draft statement follows template completely
2. Verify all elements annotated
3. Verify no hedging language
4. Load `./step-04-map.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 2-3 variations drafted, each annotated, strongest selected with scores, final draft uses direct language, all elements traceable to inputs

❌ **FAILURE:** Single draft without variation, missing annotations, hedging language in final, benefit is feature not outcome
