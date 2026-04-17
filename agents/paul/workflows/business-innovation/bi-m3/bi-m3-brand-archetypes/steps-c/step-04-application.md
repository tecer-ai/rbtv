---
name: 'step-04-application'
description: 'Define archetype expression across voice, visuals, relationship, and content'
nextStepFile: './step-05-synthesis.md'
outputFile: '{outputFolder}/brand-archetypes.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: Archetype Application

**Progress: Step 4 of 5** — Next: Synthesis

---

## STEP GOAL

Translate selected archetype into concrete, actionable guidance for voice character, visual style direction, customer relationship type, and content themes.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Demand specificity. "Friendly" is not a voice adjective — what KIND of friendly? Every guidance item must be specific enough that two people following it would produce similar outputs.

### Step-Specific Rules
- Every expression dimension must connect back to customer emotional/social jobs
- Voice adjectives must distinguish this brand from competitors
- Sample sentences must sound like a real brand, not textbook definitions
- Visual direction is DIRECTIONAL for M4, not a finished identity

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/brand-archetypes.md` for selected archetype
2. Review Emotional Territory Brief for customer grounding
3. Load M1 frameworks for customer language:
   - Working Backwards (tone, customer quotes)
   - JTBD (emotional jobs, social jobs)
   - Lean Canvas (Customer Segments, Channels)

---

## MANDATORY SEQUENCE

### 1. Define Voice Character

Prompt user to define how the brand SOUNDS:

> "Let's define [Archetype]'s voice. Based on customer emotional jobs and your UVP, how should this brand sound?"

**Voice IS (3-5 adjectives):**
- Must be specific (not just "friendly" — specify "warm-friendly" vs "professional-friendly")
- Must connect to customer emotional needs
- Must distinguish from competitors

**Voice is NOT (3-5 adjectives):**
- What tones would feel wrong or inauthentic?
- What would contradict customer needs?

**Sample Sentences:**
Draft 2-3 sentences addressing customer's primary emotional job:

Example for Sage archetype:
> "We don't just give you data — we help you understand what it means."

Ask user to validate: "Does this sound like YOUR brand, or a textbook definition?"

### 2. Define Visual Style Direction

Prompt user to define how the brand LOOKS:

> "Visual style translates archetype into visual cues. This feeds into M4 Design Brief — we're setting direction, not finalizing identity."

**Visual Mood:**
- What feeling should visuals evoke? (e.g., "open spaces, natural light, clarity")
- What references capture the right feel?

**Elements to EMBRACE:**
- Color family (warm/cool, bold/muted)
- Imagery style (photography vs illustration, abstract vs concrete)
- Typography direction (serif vs sans, heavy vs light)

**Elements to AVOID:**
- What would feel wrong for this archetype?
- What visual cliches should be rejected?

### 3. Define Customer Relationship Type

Prompt user to define how the brand RELATES:

> "Every archetype implies a relationship dynamic. What relationship does [Archetype] create with your customer?"

**Relationship Dynamic:** Name it.
- Sage = Teacher-Student
- Hero = Coach-Athlete
- Caregiver = Protector-Protected
- Explorer = Fellow Adventurer
- Ruler = Expert-Client

**What the brand PROMISES in this relationship:**
- What can customers count on?

**What the brand EXPECTS from customers:**
- What level of engagement?
- What customer behavior supports the relationship?

**How it manifests in key moments:**
- Onboarding: How does the relationship start?
- Support: How does the brand respond to problems?
- Crisis: How does the brand handle mistakes?

### 4. Define Content Themes

Prompt user to define what the brand TALKS ABOUT:

> "Content themes are recurring topics your brand gravitates toward. They must connect to customer emotional/social jobs."

**Themes to EMBRACE (4-6):**
For each theme:
- Name the theme
- Connect to specific emotional or social job

Example for Sage:
- "Demystifying complexity" → connects to customer job "feel informed and capable"

**Themes to AVOID (2-3):**
- What topics would feel off-brand?
- What would undermine the archetype?

### 5. Secondary Archetype Modifications (If Applicable)

If secondary archetype was selected:

> "How does [Secondary] modify [Primary]'s expression?"

- Which voice adjectives shift or are added?
- Which content themes are added?
- How does relationship dynamic gain nuance?

Document the blend clearly.

### 6. Update Output Document

Update brand-archetypes.md:

```markdown
## Archetype Expression Guide

### Voice Character

**Voice IS:**
- [Adjective 1]: [How it connects to customer need]
- [Adjective 2]: [How it connects]
- [Adjective 3]: [How it connects]
- [Adjective 4]: [How it connects]
- [Adjective 5]: [How it connects]

**Voice is NOT:**
- [Adjective 1]
- [Adjective 2]
- [Adjective 3]

**Sample Sentences:**
> "[Sentence 1]"
> "[Sentence 2]"
> "[Sentence 3]"

### Visual Style Direction

**Visual Mood:** [Description]

**Embrace:**
- Colors: [Direction]
- Imagery: [Direction]
- Typography: [Direction]

**Avoid:**
- [What to avoid]

### Customer Relationship Type

**Dynamic:** [Name]

**Brand Promises:** [What customers can count on]

**Brand Expects:** [Customer engagement level]

**Key Moments:**
- Onboarding: [How relationship starts]
- Support: [How brand responds]
- Crisis: [How brand handles mistakes]

### Content Themes

**Embrace:**
1. [Theme] → [Emotional job connection]
2. [Theme] → [Emotional job connection]
3. [Theme] → [Emotional job connection]
4. [Theme] → [Emotional job connection]

**Avoid:**
1. [Theme] — [Why]
2. [Theme] — [Why]
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-exploration', 'step-03-selection', 'step-04-application']
```

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Synthesis

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all 4 expression dimensions complete
2. Verify voice adjectives are specific and distinguishing
3. Verify sample sentences sound authentic
4. Load `./step-05-synthesis.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All 4 expression dimensions defined with customer job connections, voice adjectives specific enough to distinguish, sample sentences sound authentic

❌ **FAILURE:** Generic voice adjectives, no customer job connections, textbook-style sample sentences, missing expression dimensions
