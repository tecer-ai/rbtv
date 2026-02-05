---
name: 'step-06-synthesis'
description: 'Compile final document, wire to downstream frameworks, update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/brand-positioning.md'
---

# Step 6: Synthesis

**Progress: Step 6 of 6** — Final Step

---

## STEP GOAL

Compile the validated positioning statement and perceptual map, document integration notes for downstream frameworks, and UPDATE project-memo.md with synthesis.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate clarity achieved. The positioning is now the source code for all messaging — make sure downstream wiring is explicit.

### Step-Specific Rules
- project-memo.md MUST be updated with Brand Positioning synthesis
- Integration notes for downstream frameworks are REQUIRED
- Positioning statement is internal — note that it's not a tagline

---

## CONTEXT TO LOAD

1. Read complete `{outputFolder}/brand-positioning.md` from Steps 1-5
2. Read `{outputFolder}/project-memo.md` for update

---

## MANDATORY SEQUENCE

### 1. Finalize Positioning Statement

Present the validated statement:

```markdown
## Final Positioning Statement

"For [target segment] who [need/job], [brand] is the [category] that [key benefit], unlike [primary alternative] which [key limitation]."

### Element Summary

| Element | Value | Strategic Rationale |
|---------|-------|---------------------|
| Target | [Value] | [Why this target] |
| Need | [Value] | [Why this framing] |
| Category | [Value] | [Why this category] |
| Benefit | [Value] | [Connects to Why] |
| Alternative | [Value] | [Why strongest competitor] |
| Limitation | [Value] | [Why real and hard to fix] |
```

Confirm with user: "This is your validated positioning. Confirm before finalizing."

### 2. Prepare Integration Notes

Document how Brand Positioning feeds into downstream frameworks:

```markdown
## Integration Notes

### Messaging Architecture (Next M3 framework)
- **Brand Promise Layer:** Derives from benefit = "[benefit]"
- **Competitive Differentiation:** Uses alternative and limitation
- **Audience Framing:** Uses target segment and need
- **Key Message:** Translate positioning into customer language (not verbatim)

### Tone of Voice
- **Register:** [Category] and [benefit] imply [formal/casual, authoritative/friendly]
- **Perceptual Map Position:** If positioned as [X-dimension], tone should [reflect that]
- Positioning is internal; Tone makes it sound human

### M4 Design Brief
- **Visual Positioning:** Brand should LOOK like it occupies [map position]
- **Category Visual Cues:** Visual identity should fit [category] expectations
- **Map Translation:** [Dimension] maps to [visual dimension, e.g., minimal vs. feature-rich]

### M5 Market Validation
- **Messaging Hypothesis:** Positioning statement becomes testable hypothesis
- **Evaluation Criteria:** Perceptual map dimensions become test criteria
- **Competitive Testing:** Map axes used for preference testing

### Important Reminder
The positioning statement is **internal strategy**, NOT customer-facing copy.
- NEVER publish verbatim on website, ads, or pitch deck
- Messaging Architecture translates positioning into audience-appropriate language
- The statement judges whether messaging is on-strategy
```

### 3. Compile Final Document

Ensure brand-positioning.md contains all sections:

1. Positioning Inputs Brief (all 6 sections)
2. Draft Variations with annotations
3. Final Positioning Statement with element annotations
4. Perceptual Map (axes, competitors, brand position, white space)
5. Validation Test Results (all 4 tests with evidence)
6. Integration Notes

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-inputs', 'step-03-draft', 'step-04-map', 'step-05-test', 'step-06-synthesis']
status: completed
```

### 4. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m3-brand-positioning` to `stepsCompleted` array

**In Progress > M3 Brand section:**

```markdown
### Brand Positioning

**Status:** Completed

**Positioning Statement:**
"For [target] who [need], [brand] is the [category] that [benefit], unlike [alternative] which [limitation]."

**Key Findings:**
- Target: [1-sentence target description]
- Category: [Category choice and why]
- Competitive Frame: Positioned against [alternative], differentiated by [key differentiator]

**Perceptual Map:**
- Dimensions: [X-axis] vs [Y-axis]
- Position: [Brief description of brand's position]
- White Space: [Key insight from white space analysis]

**Validation:** Passed Uniqueness, Credibility, Relevance, Consistency tests

**Output:** [Link to brand-positioning.md]
```

### 5. Completion Summary

Present to founder:

> "Brand Positioning framework complete!
>
> **What we achieved:**
> - Consolidated positioning inputs from [N] upstream frameworks
> - Drafted and evaluated [N] positioning variations
> - Built perceptual map with [N] competitors
> - Passed all 4 validation tests
>
> **Your Positioning Statement:**
> '[Statement]'
>
> **What feeds forward:**
> - Messaging Architecture: Promise layer, differentiation, audience framing
> - Tone of Voice: Register and personality calibration
> - M4 Design Brief: Visual positioning direction
> - M5 Market Validation: Messaging hypothesis to test
>
> **Important:** This statement is internal strategy. It should never appear verbatim in customer-facing material. Messaging Architecture will translate it.
>
> **Next recommended framework:** Tone of Voice (or Messaging Architecture if doing that first)
>
> **Return path:** To continue other M3 frameworks, return to bi-m3 milestone workflow."

### 6. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M3** — return to M3 Brand milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M3** is selected:
1. Verify brand-positioning.md has status: completed
2. Verify project-memo.md has Brand Positioning entry
3. Load `../bi-m3/workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Final statement documented, all sections complete, integration notes prepared, project-memo.md updated, downstream wiring explicit

❌ **FAILURE:** project-memo.md not updated, integration notes missing, framework not marked complete, positioning published as tagline
