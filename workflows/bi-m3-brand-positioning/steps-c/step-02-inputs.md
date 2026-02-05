---
name: 'step-02-inputs'
description: 'Consolidate positioning inputs from upstream frameworks'
nextStepFile: './step-03-draft.md'
outputFile: '{outputFolder}/brand-positioning.md'
---

# Step 2: Consolidate Positioning Inputs

**Progress: Step 2 of 6** — Next: Draft Positioning Statement

---

## STEP GOAL

Gather and organize every strategic input needed for positioning from all completed upstream frameworks into a Positioning Inputs Brief.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Demand traceable evidence. Every input must cite its source framework — no fresh brainstorming allowed.

### Step-Specific Rules
- All 6 sections of the Inputs Brief MUST be populated
- At least 3 competitors/alternatives must be named
- Target must be specific segment and situation, not demographic label
- Benefit must connect to Golden Circle Why

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/brand-positioning.md` for current state
2. Load upstream framework outputs:
   - `{outputFolder}/golden-circle.md` (Why, How, What)
   - `{outputFolder}/brand-prism.md` (physique, personality, relationship) — if exists
   - `{outputFolder}/lean-canvas.md` (UVP, Segments, Unfair Advantage)
   - `{outputFolder}/tam-sam-som.md` (competitive landscape)
   - `{outputFolder}/working-backwards.md` (differentiation claims, customer language)
   - `{outputFolder}/brand-archetypes.md` (character traits) — if exists
   - `{outputFolder}/jobs-to-be-done.md` (primary job, emotional context) — if exists

---

## MANDATORY SEQUENCE

### 1. Extract From Golden Circle

From the Golden Circle document, extract:

| Element | Content | Use In Positioning |
|---------|---------|---------------------|
| **Why** | [Copy verbatim] | Emotional foundation of benefit claim |
| **How (Principles)** | [List 3-5 principles] | Differentiation mechanisms |
| **What** | [Copy verbatim] | Category frame |

Present: "Here's what Golden Circle provides for positioning..."

### 2. Extract From Brand Prism (If Available)

If Brand Prism exists, extract:

| Facet | Content | Use In Positioning |
|-------|---------|---------------------|
| **Physique** | [Tangible characteristics] | Shapes category perception |
| **Personality** | [Character traits] | Influences competitive tone |
| **Relationship** | [Brand-customer dynamic] | Defines value delivery type |

If not available: Note as gap and proceed.

### 3. Extract From Lean Canvas

From Lean Canvas, extract:

| Element | Content | Use In Positioning |
|---------|---------|---------------------|
| **UVP** | [Value proposition] | Benefit hypothesis |
| **Customer Segments** | [Including Early Adopters] | Target definition |
| **Unfair Advantage** | [What's defensible] | Position defensibility |
| **Problem** | [Top 3 problems] | Need definition |
| **Alternatives** | [Existing alternatives] | Competitive frame |

### 4. Extract From Competitive Landscape

From TAM/SAM/SOM and competitive analysis, extract:

| Competitor | Their Positioning | Their Weakness |
|------------|-------------------|----------------|
| [Name 1] | [How they position] | [Real limitation] |
| [Name 2] | [How they position] | [Real limitation] |
| [Name 3] | [How they position] | [Real limitation] |
| "Do Nothing" | [Current manual process] | [Limitations] |

Require at least 3 competitors. Include "do nothing" option.

### 5. Extract From Working Backwards

From PR/FAQ document, extract:
- **Headline claims** — Key differentiation language
- **Solution paragraph** — Benefit articulation
- **Customer quote** — Language that resonates
- **Leader quote** — Founder's conviction

### 6. Compile Positioning Inputs Brief

Create structured brief:

```markdown
## Positioning Inputs Brief

### Target
**Who we position for:** [Specific segment + role + situation]
- Source: Lean Canvas Customer Segments, Working Backwards customer definition
- Evidence: [Cite specific text]

### Need
**What job/problem we address:** [Functional or emotional job in customer language]
- Source: JTBD primary job, Lean Canvas Problem
- Evidence: [Cite specific text]

### Benefit
**What we promise:** [Single outcome = purpose made tangible]
- Source: Golden Circle Why + How
- Evidence: [Cite specific text]

### Category
**What kind of thing we are:** [Recognizable category]
- Source: Golden Circle What, market reality
- Evidence: [Cite specific text]

### Alternatives
**Who we position against:**
1. [Primary alternative] — [What they claim]
2. [Secondary alternative] — [What they claim]
3. [Do nothing] — [Current process]
- Source: TAM/SAM/SOM competitive landscape

### Differentiators
**Why we are different:**
1. [How principle 1] — [Evidence]
2. [How principle 2] — [Evidence]
3. [Unfair Advantage] — [Evidence]
- Source: Golden Circle How, Lean Canvas Unfair Advantage, Brand Prism personality
```

Present brief to user. Ask: "Is this accurate? Any corrections?"

### 7. Validate Completeness

Check:
- [ ] Every section populated with specific, traceable content
- [ ] At least 3 competitors/alternatives named with positioning claims
- [ ] Target describes specific segment AND situation
- [ ] Benefit connects to Golden Circle Why

If incomplete, work with user to fill gaps.

### 8. Update Output Document

Update brand-positioning.md with Positioning Inputs Brief.

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-inputs']
```

### 9. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine inputs or add more evidence
- **[C] Continue** — proceed to Draft Positioning Statement

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all 6 sections of Inputs Brief are populated
2. Verify at least 3 alternatives documented
3. Load `./step-03-draft.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All 6 sections populated with traceable evidence, 3+ competitors named, target is specific, benefit connects to Why

❌ **FAILURE:** Missing sections, vague target like "businesses", benefit as feature list, fresh brainstorming instead of framework citations
