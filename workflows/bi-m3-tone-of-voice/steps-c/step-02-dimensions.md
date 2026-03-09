---
name: 'step-02-dimensions'
description: 'Define 3-5 tone dimensions with slider positions and rationale'
nextStepFile: './step-03-examples.md'
outputFile: '{outputFolder}/tone-of-voice.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 2: Define Tone Dimensions

**Progress: Step 2 of 6** — Next: Do/Don't Examples

---

## STEP GOAL

Choose 3-5 tone dimensions, position the brand on each slider scale (1-5), and ground every choice in Brand Archetypes or Brand Prism personality.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Reject neutral positions on every dimension — that's not a personality, that's blandness. Push for distinctive positions.

### Step-Specific Rules
- 3-5 dimensions required (not more, not fewer)
- No dimension should be scored 3 (neutral) without strong justification
- Every position must cite archetype or personality trait as rationale
- Dimensions as a set must describe a COHERENT person

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/tone-of-voice.md` for current state
2. Read `{outputFolder}/brand-archetypes.md` for:
   - Primary archetype and its voice tendencies
   - Voice Character IS/NOT lists
3. Read `{outputFolder}/brand-prism.md` for:
   - Personality facet (3-5 traits)
4. Read `{outputFolder}/golden-circle.md` for:
   - Why statement (emotional conviction source)

---

## MANDATORY SEQUENCE

### 1. Present Dimension Options

Display available dimensions:

| Dimension | Left Pole (1) | Right Pole (5) |
|-----------|---------------|----------------|
| **Formal ↔ Casual** | Structured, conventional | Relaxed, conversational |
| **Serious ↔ Playful** | Earnest, focused | Light, humorous |
| **Humble ↔ Confident** | Modest, understated | Assertive, bold |
| **Technical ↔ Accessible** | Expert vocabulary | Plain language |
| **Reserved ↔ Enthusiastic** | Calm, measured | Energetic, expressive |
| **Respectful ↔ Irreverent** | Conventional, polite | Challenging, unconventional |
| **Abstract ↔ Concrete** | Conceptual, philosophical | Specific, tangible |

> "You can also define custom dimensions if none fit. Select 3-5 that are most meaningful for your brand."

### 2. Extract Archetype Voice Tendencies

From Brand Archetypes, identify natural tendencies:

| Archetype | Natural Tendencies |
|-----------|-------------------|
| [Primary] | [Voice tendencies from archetype] |
| [Secondary, if exists] | [Voice tendencies] |

> "Your [Archetype] archetype naturally tends toward [tendencies]. Let's see how this maps to dimensions."

### 3. Extract Personality Traits

From Brand Prism Personality facet:

| Trait | Dimension Implication |
|-------|----------------------|
| [Trait 1] | [Which dimension and direction?] |
| [Trait 2] | [Which dimension and direction?] |
| [Trait 3] | [Which dimension and direction?] |

### 4. Select Dimensions

Guide user to select 3-5 dimensions:

> "Based on your archetype ([Name]) and personality traits ([traits]), I recommend these dimensions:
>
> 1. [Dimension] — because [archetype/trait connection]
> 2. [Dimension] — because [archetype/trait connection]
> 3. [Dimension] — because [archetype/trait connection]
>
> Do you want to use these, or modify?"

### 5. Position on Each Dimension

For each selected dimension, determine position:

```markdown
### Dimension: [Name]

**Scale:** [Left Pole] (1) ←→ (5) [Right Pole]

**Your Position:** [1-5]

**Rationale:**
- Archetype evidence: [How [Archetype] informs this position]
- Personality evidence: [How [trait] informs this position]

**What this means in practice:**
- At position [N], we [describe what this sounds like]
- We DON'T [describe what we avoid]
```

**Scoring guidance:**
- 1 = Extreme left pole
- 2 = Lean left
- 3 = Neutral (avoid without strong justification)
- 4 = Lean right
- 5 = Extreme right pole

### 6. Check for Neutrality

If any dimension is scored 3:

> "⚠️ You positioned [Dimension] at neutral (3). A neutral position adds no distinctiveness.
>
> Why neutral here?
> - [A] This dimension doesn't apply to us → Remove it, pick a different one
> - [B] We genuinely shift based on context → Document this in context adjustments
> - [C] We should actually pick a direction → Let's reconsider"

### 7. Coherence Check

Read all dimensions together as a set:

> "Let's check if these dimensions describe a coherent person:
>
> | Dimension | Position | Meaning |
> |-----------|----------|---------|
> | [1] | [N] | [Brief meaning] |
> | [2] | [N] | [Brief meaning] |
> | [3] | [N] | [Brief meaning] |
>
> **Coherence test:** Does this combination feel like ONE consistent character? Or do the dimensions contradict each other?"

If contradictions:
- Identify the conflicting dimensions
- Decide which takes precedence
- Either resolve conflict or document when each applies

### 8. Write Dimension Summary Narrative

Create 2-3 sentence voice summary:

```markdown
## Voice Summary

[Brand Name] sounds like [overall character description in 1-2 sentences]. We are [position 1], [position 2], and [position 3] — never [what we avoid].
```

Example: "Acme sounds like a knowledgeable friend who explains complex things simply and gets genuinely excited about your progress. We are confident but never arrogant, accessible but never dumbed-down, enthusiastic but never breathless."

### 9. Differentiation Check

> "Can you think of 2 competitors who would position DIFFERENTLY on at least 2 of these dimensions?"

| Competitor | Different On | Their Position vs Ours |
|------------|--------------|------------------------|
| [Competitor 1] | [Dimension] | They are [X], we are [Y] |
| [Competitor 2] | [Dimension] | They are [X], we are [Y] |

If cannot identify differences → dimensions may not be distinctive enough.

### 10. Update Output Document

Add Tone Dimensions section:

```markdown
## Tone Dimensions

### Dimension Sliders

| Dimension | Position (1-5) | Rationale |
|-----------|----------------|-----------|
| [Name 1] | [N] | [Archetype/trait connection] |
| [Name 2] | [N] | [Archetype/trait connection] |
| [Name 3] | [N] | [Archetype/trait connection] |
| [Name 4] | [N] | [Archetype/trait connection] |
| [Name 5] | [N] | [Archetype/trait connection] |

### Voice Summary

[2-3 sentence narrative]

### Coherence Notes

[Any tensions and how resolved]

### Differentiation

[2 competitors with different positions]
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-dimensions']
```

### 11. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine positions or add/change dimensions
- **[C] Continue** — proceed to Do/Don't Examples

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify 3-5 dimensions selected with positions
2. Verify no unexplained neutral (3) positions
3. Verify coherence check passed
4. Load `./step-03-examples.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 3-5 dimensions defined with non-neutral positions, each grounded in archetype/personality, coherent set, differentiates from competitors

❌ **FAILURE:** Too many/few dimensions, all neutral positions, no archetype/trait connection, contradictory set
