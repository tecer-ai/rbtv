---
name: 'step-02-external-facets'
description: 'Define sender facets: Physique, Personality, Culture'
nextStepFile: './step-03-internal-facets.md'
outputFile: '{outputFolder}/brand-prism.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 2: External Facets

**Progress: Step 2 of 5** — Next: Internal Facets

---

## STEP GOAL

Define the three sender-side facets: Physique (tangible characteristics), Personality (character traits), and Culture (values and beliefs).

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Personality MUST derive from Brand Archetypes — do not let founders invent new personality traits that contradict their archetype. Culture must be specific beliefs, not generic values.

### Step-Specific Rules
- Physique includes full product experience, not just visual identity
- Personality starts from archetype voice character and expands
- Culture must pass the "competitor copy test" — would they change behavior?
- All three facets must align with each other

---

## CONTEXT TO LOAD

1. Read current `{outputFolder}/brand-prism.md` for progress
2. Read `{outputFolder}/brand-archetypes.md` for personality and visual direction
3. Read Prism Inputs Summary from Step 1

---

## MANDATORY SEQUENCE

### 1. Define Physique

Guide founder through tangible characteristics:

> "Physique is what customers notice on first encounter. For digital products, this includes interface aesthetic, interaction patterns, visual signatures, and product artifacts."

**Elicit:**

1. **Interface Aesthetic** — Ask:
   > "Is your product experience clean or dense? Minimal or rich? Fast or deliberate? Guided or exploratory?"

2. **Visual Signatures** — From Brand Archetypes visual direction, confirm:
   > "Your archetype suggests [visual mood, colors to embrace/avoid]. Does this still feel right?"

3. **Product Artifacts** — Ask:
   > "What tangible things do customers interact with? (dashboards, reports, notifications, emails, etc.)"

4. **First Impression Sentence** — Draft together:
   > "When someone encounters your product for the first time, they should immediately notice _____, _____, and _____."

**Output:** 4-6 tangible attributes + first-impression sentence

### 2. Define Personality

Start from archetype and expand:

> "Personality describes how the brand would act if it were a person. We start with your archetype's voice character."

**From Brand Archetypes, present:**
- Voice character IS: [adjectives]
- Voice character IS NOT: [adjectives]

**Expand to behavior:**

For each IS adjective, ask:
> "Because we are [trait], we _____." (What specific behavior does this drive?)

Example: "Because we are patient, we never rush users through onboarding and always explain why before what."

**Add behavioral traits:**

> "Beyond voice, what other character traits define how your brand acts?"

Elicit 2-3 additional behavioral traits with examples.

**Confirm anti-traits:**

> "What is your brand personality explicitly NOT?"

Review and expand the IS NOT list to 3-5 anti-traits.

**Output:**
- 5-7 personality traits with behavioral examples
- 3-5 anti-traits

### 3. Define Culture

Guide through belief-based culture:

> "Culture is not 'integrity, innovation, customer-centricity' — every company claims those. Culture is the specific worldview that makes YOUR approach inevitable."

**Elicit beliefs:**

1. From archetype motivation:
   > "Your [archetype] believes [core motivation]. How does this show up in your brand?"

2. From Lean Canvas UVP:
   > "Your UVP is [statement]. What belief about the world makes this valuable?"

3. From founder conviction:
   > "What did you believe about this problem space BEFORE you started building? What conviction drives you beyond profit?"

**Format each belief:**
> "We believe [specific claim]. That is why we [concrete action]."

**Test specificity:**
> "Could a direct competitor use this exact statement without changing anything they do? If yes, we need to sharpen it."

**Output:** 3-5 specific belief statements with concrete manifestations

### 4. Test Sender Coherence

Before proceeding, verify alignment:

> "Let's check that Physique, Personality, and Culture tell the same story."

Present all three together and ask:
- Does a [Personality] brand naturally create a [Physique] experience?
- Does a brand that believes [Culture] naturally act like [Personality]?

If contradictions found:
- Identify the outlier facet
- Revise with founder input
- Document the revision reasoning

### 5. Update brand-prism.md

Update the Sender Facets section with:
- Physique: attributes + first-impression sentence
- Personality: traits with behavioral examples + anti-traits
- Culture: belief statements with manifestations

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-external-facets']
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Internal Facets (Reflection, Self-Image)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure all three sender facets are documented
2. Verify `step-02-external-facets` is in `stepsCompleted`
3. Load `./step-03-internal-facets.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Physique defines full product experience, Personality derives from archetype with behavioral examples, Culture passes competitor copy test, all three facets are coherent

❌ **FAILURE:** Physique is just visual identity, Personality contradicts archetype, Culture uses generic values, facets contradict each other
