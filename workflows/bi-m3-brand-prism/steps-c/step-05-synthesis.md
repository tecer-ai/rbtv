---
name: 'step-05-synthesis'
description: 'Validate, compile final document, and update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/brand-prism.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Prepare integration notes for downstream frameworks, compile final Brand Prism document, and UPDATE project-memo.md with synthesis.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate the complete identity system. Be explicit about what each downstream framework receives. The prism is now the central identity reference.

### Step-Specific Rules
- project-memo.md MUST be updated with Brand Prism synthesis
- Integration notes for ALL downstream frameworks are REQUIRED
- Final document must contain all 6 facets with evidence and examples
- Prism narrative must be under 30 seconds to read aloud

---

## CONTEXT TO LOAD

1. Read complete `{outputFolder}/brand-prism.md` from Steps 1-4
2. Read `{outputFolder}/project-memo.md` for update

---

## MANDATORY SEQUENCE

### 1. Prepare Integration Notes

Document exactly what each downstream framework receives:

```markdown
## Integration Notes

**Golden Circle (Next):**
- Why derives from: Culture facet beliefs
- How informed by: Personality facet values orientation

**Brand Positioning:**
- Differentiation informed by: Physique + Personality
- "Unlike [competitor]" clause uses: Tangible characteristics and character traits

**Tone of Voice:**
- Tone dimensions seeded by: Personality traits with behavioral examples
- Do/don't guidelines from: IS/IS NOT adjectives

**Messaging Architecture:**
- Brand-level messages from: Physique and Culture facets
- Benefit messages from: Reflection and Self-Image facets
- Overall messaging stance from: Relationship facet

**M4 Design Brief:**
- Visual identity direction from: Physique facet attributes
- First-impression sentence constrains: Design exploration
- Mood and embrace/avoid lists provide: Visual guardrails
```

### 2. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/workflows/bi-business-innovation/data/founder-process.md` for M3.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 3. Compile Final Document

Ensure brand-prism.md contains all sections:

1. **Prism Inputs Summary** — evidence from upstream frameworks
2. **Physique** — tangible attributes + first-impression sentence
3. **Personality** — 5-7 traits with behavioral examples + 3-5 anti-traits
4. **Culture** — 3-5 belief statements with manifestations
5. **Reflection** — 3-5 statements traced to social jobs
6. **Self-Image** — 3-5 statements traced to emotional jobs
7. **Relationship** — type, promises, expectations, situational behaviors, statement
8. **Consistency Assessment** — 6 pairs tested, any revisions documented
9. **Prism Narrative** — single coherent story
10. **Integration Notes** — downstream framework wiring

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-external-facets', 'step-03-internal-facets', 'step-04-prism-synthesis', 'step-05-synthesis']
status: completed
```

### 4. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m3-brand-prism` to `stepsCompleted` array

**In Progress > M3 Brand section:**

```markdown
### Brand Prism

**Status:** Completed

**The 6 Facets:**
- **Physique:** [1-sentence summary of tangible characteristics]
- **Personality:** [Primary archetype] — [key traits]
- **Culture:** [Core belief statement]
- **Relationship:** [Relationship type] — [key promise]
- **Reflection:** Customers seen as [key perception]
- **Self-Image:** Customers feel [key feeling]

**Prism Narrative:**
"[Complete prism narrative in one sentence]"

**Consistency:** Tested [N] facet pairs, no contradictions

**Output:** [Link to brand-prism.md]
```

### 5. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 6. Completion Summary

Present to founder:

> "Brand Prism framework complete!
>
> **What we achieved:**
> - Defined all 6 facets grounded in M1/M2/M3 evidence
> - Physique describes full product experience
> - Personality derives from your [archetype] selection
> - Culture captures your specific worldview
> - Reflection maps how customers appear to others
> - Self-Image maps how customers feel internally
> - Relationship defines the brand-customer dynamic
> - Tested [N] facet pairs for consistency
>
> **Prism Narrative:**
> '[Narrative]'
>
> **What feeds forward:**
> - Golden Circle: Culture → Why
> - Brand Positioning: Physique + Personality → differentiation
> - Tone of Voice: Personality → tone dimensions
> - Messaging Architecture: All facets → messaging layers
> - M4 Design Brief: Physique → visual identity
>
> **Next recommended framework:** Golden Circle
>
> **Return path:** To continue other M3 frameworks, return to bi-m3 milestone workflow."

### 7. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M3.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M3 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 8. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M3** — return to M3 Brand milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M3** is selected:
1. Verify brand-prism.md has status: completed
2. Verify project-memo.md has Brand Prism entry
3. Load `../bi-m3/workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All 6 facets documented with evidence, consistency test complete with no unresolved contradictions, integration notes prepared for all downstream frameworks, project-memo.md updated with framework entry, prism narrative reads in under 30 seconds

❌ **FAILURE:** project-memo.md not updated, integration notes missing, facets lack evidence tracing, consistency test not documented
