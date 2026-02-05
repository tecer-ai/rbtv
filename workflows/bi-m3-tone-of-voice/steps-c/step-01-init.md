---
name: 'step-01-init'
description: 'Load context, verify prerequisites, explain Tone of Voice framework'
nextStepFile: './step-02-dimensions.md'
outputFile: '{outputFolder}/tone-of-voice.md'
---

# Step 1: Initialize Tone of Voice

**Progress: Step 1 of 6** — Next: Define Tone Dimensions

---

## STEP GOAL

Verify Brand Archetypes and prior M3 framework prerequisites, load context from project-memo and upstream frameworks, explain Tone of Voice methodology.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Demand measurable tone dimensions, not vague aspirations. "Be friendly" is worthless — slider positions with examples are actionable.

### Step-Specific Rules
- Brand Archetypes AND Brand Prism MUST be complete before starting
- Messaging Architecture SHOULD be complete (recommended, not required)
- If prerequisites are missing, HALT and explain what's needed
- If tone-of-voice.md exists with stepsCompleted, offer to continue
- Do NOT define dimensions in this step — that's Step 2

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and stepsCompleted
2. Read `./data/tone-of-voice-framework.md` for framework knowledge
3. Check prerequisites by verifying these exist in stepsCompleted:
   - `bi-m3-brand-archetypes` (REQUIRED — provides character)
   - `bi-m3-brand-prism` (REQUIRED — provides personality facet)
   - `bi-m3-golden-circle` (REQUIRED — provides Why emotional register)
4. Preferred but not required:
   - `bi-m3-messaging-architecture` (provides content to apply tone to)
   - `bi-m3-brand-positioning` (provides register calibration)
5. Check if `{outputFolder}/tone-of-voice.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Verification

Check project-memo stepsCompleted for:

**Required Frameworks:**
- Brand Archetypes (provides character foundation for tone)
- Brand Prism (personality facet becomes audible in dimensions)
- Golden Circle (Why provides emotional conviction)

**Recommended Frameworks:**
- Messaging Architecture (provides content to apply tone to)
- Brand Positioning (register calibration)

If missing required frameworks:
> "⛔ **Prerequisites Incomplete**
>
> Tone of Voice defines HOW your brand sounds. That requires knowing WHO the brand is:
>
> Missing required: [List missing frameworks]
>
> Tone without personality is arbitrary style preference. Complete Brand Archetypes and Brand Prism first.
>
> Return to: [Missing framework]"

HALT — do not proceed.

If Messaging Architecture is missing (recommended, not required):
> "⚠️ **Optional Dependency Missing**
>
> Messaging Architecture provides the content your tone is applied to. Without it, sample copy may need revision later.
>
> You can proceed, but consider completing Messaging Architecture first for stronger examples.
>
> Continue anyway? [Y/N]"

### 2. Context Detection

If prerequisites met:
- Check for existing `tone-of-voice.md` with `stepsCompleted`
- If exists:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Tone of Voice briefly:

> "Tone of Voice defines HOW your brand sounds — not what it says (that's Messaging Architecture), but how it says it.
>
> We'll build:
> 1. **Tone Dimensions** — 3-5 slider scales (formal-casual, serious-playful, etc.) with specific positions
> 2. **Do/Don't Examples** — Concrete pairs showing right and wrong for each dimension
> 3. **Context Adjustments** — How tone shifts by situation while personality stays constant
> 4. **Sample Copy** — Reference copy for common scenarios
>
> Without this guide, every writer sounds different. With it, the brand sounds like one person."

### 4. Load Personality Foundation

From project-memo and upstream frameworks, extract:

**From Brand Archetypes:**
- Primary archetype and its voice tendencies
- Voice character IS/NOT lists (if defined)

**From Brand Prism:**
- Personality facet traits (3-5 traits)
- Relationship facet (brand-customer dynamic)

**From Golden Circle:**
- Why statement (emotional register source)

Present: "Here's your personality foundation for tone definition..."

### 5. Create Output Document

If not continuing, create tone-of-voice.md:

```yaml
---
name: tone-of-voice
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# Tone of Voice: {Project Name}

## Tone Dimensions

*(To be completed in Step 2)*

## Do/Don't Examples

*(To be completed in Step 3)*

## Context Adjustments

*(To be completed in Step 4)*

## Sample Copy

*(To be completed in Step 5)*

## Consistency Checks

*(To be completed in Step 6)*

## Integration Notes

*(To be completed in Step 6)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Define Tone Dimensions

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure tone-of-voice.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-dimensions.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Prerequisites verified, personality foundation extracted, output document created

❌ **FAILURE:** Proceeding without Brand Archetypes or Prism, defining dimensions in this step, skipping personality extraction
