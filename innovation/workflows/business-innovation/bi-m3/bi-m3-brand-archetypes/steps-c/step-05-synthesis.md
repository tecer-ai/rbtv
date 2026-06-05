---
name: 'step-05-synthesis'
description: 'Validate, compile final document, and update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/brand-archetypes.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Validate archetype selection against competitors and coherence, compile final Brand Archetypes document, and UPDATE project-memo.md with synthesis.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate clarity achieved. Note what was learned. Be honest about how this archetype will guide all downstream brand work.

### Step-Specific Rules
- project-memo.md MUST be updated with Brand Archetypes synthesis
- Differentiation stress test is REQUIRED
- Coherence stress test is REQUIRED
- Integration notes for downstream frameworks are REQUIRED

---

## CONTEXT TO LOAD

1. Read complete `{outputFolder}/brand-archetypes.md` from Steps 1-4
2. Read `{outputFolder}/project-memo.md` for update
3. Review competitor archetype map for differentiation test

---

## MANDATORY SEQUENCE

### 1. Differentiation Stress Test

For each of top 3 competitors:

> "Let's test differentiation. Compare your archetype expression to [Competitor]."

Ask:
> "If a customer encountered your brand and [Competitor]'s side by side, would they feel a DISTINCT character difference within 30 seconds?"

If NO:
- Identify which expression dimension needs sharpening
- Return to Step 4 to revise that dimension
- Do not proceed until differentiation is clear

If YES for all competitors:
- Document the differentiation confirmation
- Proceed to coherence test

### 2. Coherence Stress Test

Present all 4 expression dimensions together:

> "Let's verify coherence. Reading Voice, Visuals, Relationship, and Themes together..."

Ask:
> "Do these feel like they belong to the SAME character? Or do they pull in different directions?"

If incoherent:
- Identify the outlier dimension
- Return to Step 4 to revise
- Do not proceed until coherent

If coherent:
- Document coherence confirmation
- Proceed to integration notes

### 3. Prepare Integration Notes

Document how Brand Archetypes feeds into downstream frameworks:

```markdown
## Integration Notes

**Brand Prism (Next):**
- Personality facet derives from: [Archetype + voice adjectives]
- Relationship facet uses: [Relationship type]
- Culture facet references: [Archetype core values]

**Golden Circle:**
- Why should resonate with: [Archetype core motivation]

**Tone of Voice:**
- Voice dimensions seeded by: [Voice Character IS/NOT lists]
- Sample sentences provide: [Starting examples]

**Messaging Architecture:**
- Content themes seed: [Messaging pillars]

**M4 Design Brief:**
- Visual direction provides: [Visual mood, embrace/avoid]
```

### 4. Deduplication Verification

As the first framework in M3, this framework defines foundational concepts. Later frameworks will reference these definitions. No deduplication check is required — this framework is the concept originator for this milestone.

### 5. Compile Final Document

Ensure brand-archetypes.md contains all sections:

1. Emotional Territory Brief
2. Archetype Evaluation Matrix (complete with all 12)
3. Competitor Archetype Map
4. Primary Archetype Selection with Justification
5. Secondary Archetype (or "None")
6. Rejected Archetypes with Reasons
7. Archetype Statement
8. Archetype Expression Guide (all 4 dimensions)
9. Differentiation Confirmation
10. Coherence Confirmation
11. Integration Notes

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-exploration', 'step-03-selection', 'step-04-application', 'step-05-synthesis']
status: completed
```

### 6. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m3-brand-archetypes` to `stepsCompleted` array

**In Progress > M3 Brand section:**

```markdown
### Brand Archetypes

**Status:** Completed

**Primary Archetype:** [Name]

**Key Findings:**
- Emotional Territory: [1-sentence summary of customer emotional landscape]
- Selection Rationale: [1-sentence justification]
- Expression: [1-sentence summary of voice/visual direction]

**Archetype Statement:** "[One-sentence archetype statement]"

**Differentiation:** Confirmed distinct from [top competitors]

**Output:** [Link to brand-archetypes.md]
```

### 7. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 8. Completion Summary

Present to founder:

> "Brand Archetypes framework complete!
>
> **What we achieved:**
> - Extracted emotional territory from [N] M1/M2 artefacts
> - Evaluated all 12 archetypes with evidence-based scoring
> - Selected [Archetype] with [N]-point justification
> - Defined voice, visuals, relationship, and content themes
> - Confirmed differentiation against [N] competitors
>
> **Archetype Statement:**
> '[Statement]'
>
> **What feeds forward:**
> - Brand Prism: personality and relationship facets
> - Golden Circle: core motivation alignment
> - Tone of Voice: voice character and samples
> - Messaging Architecture: content themes
> - M4 Design Brief: visual direction
>
> **Next recommended framework:** Brand Prism
>
> **Return path:** To continue other M3 frameworks, return to bi-m3 milestone workflow."

### 9. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M3.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M3 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 10. Present Menu Options

**Select an Option:**
- **[B] Back to M3** — return to M3 Brand milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M3** is selected:
1. Verify brand-archetypes.md has status: completed
2. Verify project-memo.md has Brand Archetypes entry
3. Load `../../workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Differentiation confirmed, coherence confirmed, brand-archetypes.md complete with all sections, project-memo.md updated with framework entry, integration notes prepared

❌ **FAILURE:** project-memo.md not updated, differentiation test skipped, coherence test skipped, integration notes missing, framework not marked complete
