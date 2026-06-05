---
name: 'step-02-exploration'
description: 'Extract emotional territory and evaluate all 12 archetypes'
nextStepFile: './step-03-selection.md'
outputFile: '{outputFolder}/brand-archetypes.md'
---

# Step 2: Archetype Exploration

**Progress: Step 2 of 5** — Next: Archetype Selection

---

## STEP GOAL

Extract emotional territory from M1/M2 artefacts and systematically evaluate all 12 archetypes against emotional fit, purpose fit, and differentiation.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Demand evidence for every score. Push back on intuitive assessments. "That feels like a 3" is not acceptable — cite specific customer jobs or competitive gaps.

### Step-Specific Rules
- MUST evaluate ALL 12 archetypes — no skipping or dismissing without evidence
- Every score must be traceable to customer evidence or competitive analysis
- Competitor mapping is REQUIRED, not optional

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/brand-archetypes.md` for current state
2. Load M1 framework outputs for customer evidence:
   - `{outputFolder}/working-backwards.md` (customer language, quotes)
   - `{outputFolder}/jobs-to-be-done.md` (emotional jobs, social jobs, forces)
   - `{outputFolder}/lean-canvas.md` (UVP, Segments, Unfair Advantage)
   - `{outputFolder}/problem-solution-fit.md` (emotions before/after)
3. Load M2 validation outputs for confirmed findings

---

## MANDATORY SEQUENCE

### 1. Extract Emotional Territory

From M1/M2 artefacts, extract and cluster:

**Emotional Jobs** (how customers want to feel):
- List verbatim from JTBD analysis
- Extract emotional language from Working Backwards customer quotes
- Pull "emotions after" from Problem-Solution Fit

**Social Jobs** (how customers want to be perceived):
- List verbatim from JTBD analysis
- Extract aspirational self-image from Working Backwards PR

**Validated Motivations** (from M2):
- What assumptions about customer motivation were validated?
- What was refuted? (these constrain archetype choices)

Present to user:
> "Here's your customer's emotional territory based on M1/M2 evidence..."

Ask: "Is this accurate? Any corrections or additions?"

### 2. Draft Emotional Territory Brief

Create a half-page synthesis (max 200 words):

```markdown
## Emotional Territory Brief

**Core Motivations:** [What drives customers to act]

**Emotional Pain Points:** [How they feel when problem is active]

**Social Stakes:** [How they want others to perceive them]

**Key Evidence Sources:**
- JTBD: [Specific jobs cited]
- Working Backwards: [Specific quotes cited]
- M2 Validation: [Specific findings cited]
```

Present draft. Confirm with user before proceeding.

### 3. Competitor Archetype Mapping

Identify top 3-5 competitors and map each to approximate archetype:

> "Before we evaluate archetypes, let's map your competitors. What 3-5 brands compete for your customer's attention?"

For each competitor:
- Identify their apparent archetype (voice, visuals, relationship)
- Note: Most haven't done formal archetype work — infer from brand expression

Create competitor map:
| Competitor | Apparent Archetype | Evidence (voice/visual/messaging) |
|------------|-------------------|-----------------------------------|

### 4. Evaluate All 12 Archetypes

Create Archetype Evaluation Matrix:

| Archetype | Core Motivation | Emotional Fit (0-3) | Purpose Fit (0-3) | Differentiation (0-3) | Total | Rationale |
|-----------|-----------------|---------------------|-------------------|----------------------|-------|-----------|
| Innocent | Safety, optimism | | | | | |
| Explorer | Freedom, discovery | | | | | |
| Sage | Understanding, wisdom | | | | | |
| Hero | Mastery, achievement | | | | | |
| Outlaw | Liberation, revolution | | | | | |
| Magician | Transformation, power | | | | | |
| Regular Guy | Belonging, authenticity | | | | | |
| Lover | Intimacy, passion | | | | | |
| Jester | Enjoyment, play | | | | | |
| Caregiver | Service, protection | | | | | |
| Creator | Innovation, expression | | | | | |
| Ruler | Control, stability | | | | | |

**Scoring Guidance:**

**Emotional Fit:**
- 3: Archetype directly embodies primary emotional/social job
- 2: Strongly related but not primary match
- 1: Tangentially relevant
- 0: Contradicts customer needs

**Purpose Fit:**
- 3: Naturally delivers your UVP
- 2: Strong alignment
- 1: Partial fit
- 0: Forced or contradictory

**Differentiation:**
- 3: No competitor occupies this archetype
- 2: One competitor partially occupies
- 1: Crowded space
- 0: Dominant competitor owns it

For each archetype, ask user to provide evidence-backed scores.

### 5. Identify Top Candidates

After completing matrix:
- Highlight top 3-4 scoring archetypes
- Write 2-3 sentence rationale for each explaining why it scored well

Present: "Based on evidence, your top archetype candidates are..."

### 6. Update Output Document

Update brand-archetypes.md:
- Add Emotional Territory Brief
- Add Competitor Archetype Map
- Add complete Evaluation Matrix with rationales for top scorers

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-exploration']
```

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Archetype Selection

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify all 12 archetypes have scores
2. Verify at least 3 competitors mapped
3. Verify top candidates identified with rationales
4. Load `./step-03-selection.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Emotional territory extracted with evidence, all 12 archetypes scored, competitors mapped, top candidates identified

❌ **FAILURE:** Skipping archetypes, accepting intuitive scores without evidence, no competitor analysis, proceeding with incomplete matrix
