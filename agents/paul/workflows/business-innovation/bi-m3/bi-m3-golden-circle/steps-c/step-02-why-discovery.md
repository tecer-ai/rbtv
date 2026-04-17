---
name: 'step-02-why-discovery'
description: 'Extract purpose signals, articulate core belief'
nextStepFile: './step-03-how-articulation.md'
outputFile: '{outputFolder}/golden-circle.md'
---

# Step 2: Why Discovery

**Progress: Step 2 of 5** — Next: How Articulation

---

## STEP GOAL

Synthesize purpose signals from prior frameworks and articulate the brand's core belief (Why) in a single sentence.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. The Why is the founder's genuine belief — you can extract, propose, and challenge, but you cannot invent it. If the Why sounds like marketing copy, push back.

### Step-Specific Rules
- Why must NOT mention product, category, or features
- Why must survive a complete product pivot
- Why must trace to at least one JTBD emotional job
- Why must be specific enough that a competitor wouldn't use same words
- Surface candidate Why statements to founder for gut-check

---

## CONTEXT TO LOAD

1. Read current `{outputFolder}/golden-circle.md` for Purpose Signals Summary
2. Read `{outputFolder}/brand-prism.md` Culture facet in detail
3. Read `{outputFolder}/jtbd.md` emotional jobs section
4. Review project-memo Tenets

---

## MANDATORY SEQUENCE

### 1. Consolidate Purpose Signals

Organize the signals from Step 1 into three categories:

**Founder Beliefs** — What does the founder personally care about beyond revenue?
- Extract from project-memo Tenets
- Extract from Working Backwards leader quote
- Extract from Brand Prism Culture statements

**Customer Emotional Needs** — What do customers need to feel or become?
- Extract from JTBD emotional jobs
- Ask: "What must we believe about the world for this emotional outcome to matter?"

**Cultural Values** — What does the brand stand for in the market?
- Extract from Brand Prism Culture facet
- Extract from archetype core motivation

Present the organized signals:
> "Here are the purpose signals organized by source..."

### 2. Identify Convergence

Look for the recurring theme across all three categories:

> "Looking at founder beliefs, customer emotional needs, and cultural values — what's the ONE theme that appears across all of them?"

Guide founder to identify the convergence point. This is the strongest Why candidate.

### 3. Draft Candidate Why Statements

Generate 3-5 candidate Why statements:

**Format:** "We believe that [statement of belief about the world]."

**Requirements:**
- No product mention
- No category mention
- No feature mention
- Statement about the world, not about the company

Present candidates and guide founder through evaluation:

> "Here are candidate Why statements. Let's test each one..."

### 4. Apply Three Filters

For each candidate, test:

**A. Endurance Filter**
> "Would this Why still be true if you pivoted to a completely different product in the same domain?"

If no → eliminate candidate

**B. Authenticity Filter**
> "Would you say this at a dinner table without feeling like you're performing?"

If hesitation → revise or eliminate

**C. Customer Resonance Filter**
> "Does this belief connect to an emotional job your customers actually experience?"

If no connection → revise or eliminate

### 5. Test Specificity

For surviving candidates:

> "Could a direct competitor use this exact statement without changing a word?"

If yes → too generic, needs sharpening

Ask:
> "What's the specific perspective, context, or value that makes this belief YOURS?"

Revise until the Why is specific to this brand.

### 6. Select Final Why

Guide founder to select one Why statement.

**Write the Why as:**
- Single sentence
- Plain language (not corporate-speak)
- Read it aloud to verify it sounds natural

**Write supporting narrative:**
- 3-5 sentences explaining the belief
- Reference the Brand Prism Culture facet
- Connect to at least one JTBD emotional job

### 7. Update golden-circle.md

Update the Why section with:
- Why Statement (single sentence)
- Why Narrative (supporting paragraph)
- Traceability notes (which signals informed it)

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-why-discovery']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to How Articulation

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure Why Statement exists (single sentence, no product mention)
2. Ensure Why Narrative exists with traceability
3. Verify `step-02-why-discovery` is in `stepsCompleted`
4. Load `./step-03-how-articulation.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Why statement is single sentence with no product/feature mention, passes endurance/authenticity/resonance filters, is specific enough competitors wouldn't copy it, traces to emotional job and culture facet

❌ **FAILURE:** Why mentions product or features, is generic enough any competitor could use it, founder hesitates to own it, no connection to customer emotional job
