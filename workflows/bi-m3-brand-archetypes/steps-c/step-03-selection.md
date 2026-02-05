---
name: 'step-03-selection'
description: 'Select primary and optional secondary archetype with justification'
nextStepFile: './step-04-application.md'
outputFile: '{outputFolder}/brand-archetypes.md'
---

# Step 3: Archetype Selection

**Progress: Step 3 of 5** — Next: Archetype Application

---

## STEP GOAL

Make decisive, justified archetype selection: one primary archetype, and optionally one secondary archetype that adds nuance without creating incoherence.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for decisive selection. Reject "we're a bit of everything" thinking. A brand without clear character has no character at all.

### Step-Specific Rules
- Primary archetype MUST score in top 2, or override requires explicit written justification
- Secondary archetype MUST NOT contradict primary (check incoherent combinations)
- Rejected archetypes MUST be documented with reasons
- Do NOT define expression in this step — that's Step 4

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/brand-archetypes.md` for evaluation matrix and top candidates
2. Review Emotional Territory Brief for customer evidence
3. Review competitor archetype map for differentiation context

---

## MANDATORY SEQUENCE

### 1. Review Top Candidates

Present the top 3-4 archetypes from Step 2 evaluation:

> "Based on your evidence-backed scoring, your top archetype candidates are:
>
> 1. [Archetype]: [Total score] — [Brief rationale]
> 2. [Archetype]: [Total score] — [Brief rationale]
> 3. [Archetype]: [Total score] — [Brief rationale]
> 4. [Archetype]: [Total score] — [Brief rationale]"

### 2. Apply Selection Criteria

For each top candidate, ask:

1. **Authenticity Test:**
   > "Can we authentically sustain this character across EVERY touchpoint — website, support emails, error messages, pricing page, investor pitch? Or would we constantly slip out of character?"

2. **Team Fit Test:**
   > "Does this archetype feel TRUE to the founding team's values? Or would maintaining it require constant pretending?"

3. **Recognition Test:**
   > "Would your target customer immediately recognize this as 'a brand that gets me'?"

Walk through each candidate with these questions.

### 3. Select Primary Archetype

Prompt user for selection:

> "Based on evidence and the tests above, which archetype should be your PRIMARY brand character?"

Once selected, draft justification paragraph that references:
- Specific emotional and social jobs it serves (cite JTBD)
- Purpose and UVP alignment (cite Lean Canvas)
- Competitive differentiation (cite competitor map)

Present: "Here's the justification for [Archetype]..."

Confirm with user. Revise if needed.

### 4. Consider Secondary Archetype (Optional)

> "A secondary archetype can add nuance. It's NOT required. Consider adding one only if:
>
> 1. The primary leaves a significant emotional job unaddressed
> 2. The secondary adds texture without contradicting the primary
> 3. The combination creates something distinctive
>
> Do you want to add a secondary archetype?"

If yes:
- Verify it's not an incoherent pairing (Outlaw + Ruler, Innocent + Outlaw, etc.)
- Define blend ratio (primary 70-80%, secondary 20-30%)
- Write brief explanation of what secondary adds

If no:
- Proceed to rejected archetypes documentation

### 5. Document Rejected Archetypes

For at least 3 archetypes NOT selected, document why:

```markdown
## Rejected Archetypes

**[Archetype 1]:** Rejected because [specific reason tied to scores or evidence]

**[Archetype 2]:** Rejected because [specific reason]

**[Archetype 3]:** Rejected because [specific reason]
```

This prevents future revisiting without new evidence.

### 6. Craft Archetype Statement

Create one-sentence summary:

> "[Brand] is primarily the [Archetype] because [reason], with elements of the [Secondary] that [what it adds]."

Or if no secondary:

> "[Brand] is the [Archetype] because [reason]."

Present. Confirm with user:
> "Can you read this aloud and say 'yes, that is us' without hesitation?"

If hesitation, revisit selection.

### 7. Update Output Document

Update brand-archetypes.md:

```markdown
## Primary Archetype Selection

**Archetype:** [Name]

**Justification:**
[Paragraph citing emotional jobs, purpose fit, differentiation]

**Archetype Statement:**
[One-sentence summary]

## Secondary Archetype (Optional)

**Archetype:** [Name or "None"]
**Blend Ratio:** [70/30 or N/A]
**What It Adds:** [Brief explanation or N/A]

## Rejected Archetypes

[List with reasons]
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-exploration', 'step-03-selection']
```

### 8. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — reconsider selection or refine justification
- **[C] Continue** — proceed to Archetype Application

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify primary archetype selected with justification
2. Verify archetype statement exists
3. Verify at least 3 rejected archetypes documented
4. Load `./step-04-application.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Primary archetype selected with evidence-backed justification, archetype statement clear and authentic, rejected archetypes documented

❌ **FAILURE:** Selection without justification, picking archetype outside top 2 without override rationale, incoherent primary/secondary pairing, no rejected archetype documentation
