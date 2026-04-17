---
name: 'step-06-synthesis'
description: 'Validate consistency, wire to M4/M5/M6, update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/tone-of-voice.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 6: Synthesis

**Progress: Step 6 of 6** — Final Step

---

## STEP GOAL

Validate consistency with upstream brand frameworks, prepare integration notes for M4/M5/M6, and UPDATE project-memo.md marking M3 Brand as COMPLETE.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Celebrate the framework completion. Tone of Voice defines how the brand sounds — the final piece before compiling the Brandbook. The brand now has identity (who), positioning (where), messaging (what), and voice (how). Next: the Brandbook will add visual identity and compile everything into one reference.

### Step-Specific Rules
- project-memo.md MUST be updated with Tone of Voice synthesis
- All 3 consistency checks are REQUIRED
- Integration notes for Brandbook, M4, M5, M6 are REQUIRED
- Do NOT mark M3 as complete — the Brandbook framework handles that

---

## CONTEXT TO LOAD

1. Read complete `{outputFolder}/tone-of-voice.md` from Steps 1-5
2. Read `{outputFolder}/project-memo.md` for update
3. Read `{outputFolder}/brand-prism.md` for consistency check
4. Read `{outputFolder}/brand-archetypes.md` for consistency check
5. Read `{outputFolder}/brand-positioning.md` for consistency check (if exists)

---

## MANDATORY SEQUENCE

### 1. Brand Prism Consistency Check

Compare tone to Brand Prism facets:

```markdown
### Brand Prism Consistency Check

**Personality Facet:** [List traits from Brand Prism]

| Prism Trait | Audible in Dimensions? | Evidence |
|-------------|----------------------|----------|
| [Trait 1] | [Yes/No] | [Which dimension reflects this] |
| [Trait 2] | [Yes/No] | [Which dimension reflects this] |
| [Trait 3] | [Yes/No] | [Which dimension reflects this] |

**Relationship Facet:** [Relationship type from Brand Prism]

| Context | Preserves Relationship? | Evidence |
|---------|------------------------|----------|
| Marketing | [Yes/No] | [How] |
| Onboarding | [Yes/No] | [How] |
| Error/Support | [Yes/No] | [How — critical!] |
| Documentation | [Yes/No] | [How] |
| Social | [Yes/No] | [How] |

**Culture Facet:** [Values from Brand Prism]

Any sample copy contradict culture values? [Yes/No — specify if yes]

**Result:** ✅ PASS / ❌ FAIL
```

If FAIL: Document inconsistency and resolve by adjusting tone guide.

### 2. Brand Archetypes Consistency Check

Compare tone to archetype voice:

```markdown
### Brand Archetypes Consistency Check

**Primary Archetype:** [Name]
**Archetype Voice Tendencies:** [From archetype analysis]

| Tendency | Reflected in Tone? | Evidence |
|----------|-------------------|----------|
| [Tendency 1] | [Yes/No] | [Which dimension/sample shows this] |
| [Tendency 2] | [Yes/No] | [Which dimension/sample shows this] |

**Archetype Character IS/NOT:**

| IS | Reflected? | NOT | Avoided? |
|----|------------|-----|----------|
| [Word] | [Yes/No] | [Word] | [Yes/No] |
| [Word] | [Yes/No] | [Word] | [Yes/No] |

**Coherence Test:** Does the tone sound like [Archetype] speaking? [Yes/No — explain]

**Result:** ✅ PASS / ❌ FAIL
```

If FAIL: Adjust tone to align with archetype.

### 3. Brand Positioning Consistency Check (If Exists)

If Brand Positioning was completed:

```markdown
### Brand Positioning Consistency Check

**Positioning Category:** [From positioning statement]
**Positioning Benefit:** [From positioning statement]

**Register Alignment:**
- Does the category [X] imply a tone register? [e.g., premium implies more formal]
- Does our tone match that register? [Yes/No]

**Perceptual Map Alignment:**
- Our map position on [Dimension]: [Position]
- Does our tone reflect that position? [Yes/No — how]

**Result:** ✅ PASS / ❌ FAIL
```

If Brand Positioning not complete: Skip with note.

### 4. Document Consistency Results

```markdown
## Consistency Checks

| Check | Result | Notes |
|-------|--------|-------|
| Brand Prism | ✅/❌ | [Brief summary] |
| Brand Archetypes | ✅/❌ | [Brief summary] |
| Brand Positioning | ✅/❌/Skipped | [Brief summary] |

**Overall:** [All checks passed / Adjustments made]
```

### 5. Prepare Integration Notes

Document how Tone of Voice feeds into downstream frameworks and milestones:

```markdown
## Integration Notes

### Brandbook (M3 Next)
The tone dimensions, voice summary, do/don't examples, and context adjustments from this framework will be compiled into the brandbook's Messaging & Tone section. The brandbook is the final M3 framework and produces the canonical brand reference document.

**Handoff:**
- Voice dimensions and summary → Brandbook Brand Voice section
- Do/don't examples → Brandbook Tone Guidelines
- Context adjustments → Brandbook Tone Guidelines

### M4 Prototypation

**Landing Page Copy:**
- Use Sample 1 (Homepage) as starting template
- Apply Marketing context adjustments
- Ensure all copy follows tone dimensions

**Onboarding Flow:**
- Use Sample 2 (Welcome) as template
- Apply Onboarding context adjustments
- Dial up encouragement per adjustment matrix

**UI Microcopy:**
- Use error/support context for error states
- Use documentation context for tooltips and help text
- Non-negotiable dimensions apply everywhere

**M4 Design Brief:**
- Tone dimensions inform verbal identity direction
- Visual and verbal must align
- [Specific alignment notes]

### M5 Market Validation

**Test Messaging:**
- ALL A/B test copy must follow this tone guide
- Inconsistent tone pollutes test results
- Use samples as templates for test variants

**SPIN Scripts:**
- Apply appropriate context adjustments
- Maintain non-negotiable core dimensions
- Use do/don't examples as calibration

**Smoke Test Copy:**
- Follow Marketing context adjustments
- Brand promise must be visible

### M6 MVP

**Production Copy Standard:**
- This guide is the canonical reference
- All marketing, product, support, docs follow it
- New writers should read do/don't examples first

**New Contexts:**
- When new channels emerge (chatbot, push notifications, video)
- Define reader emotional state
- Apply adjustment framework from Step 4
- Add to this guide
```

### 6. Deduplication Verification

Before writing the synthesis output, verify:
1. Read the content ownership mapping in `{bmad_rbtv}/workflows/bi-business-innovation/data/founder-process.md` for M3.
2. For each concept this framework does NOT own: confirm the synthesis output references the owning framework's definition rather than restating it.
3. New insights and deltas are permitted — full restatements are not.
4. If duplication is found, rewrite the affected section to use the `## Prior Context` reference format.

### 7. Compile Final Document

Ensure tone-of-voice.md contains all sections:

1. Tone Dimensions (with slider positions and rationales)
2. Voice Summary (2-3 sentence narrative)
3. Do/Don't Examples (3 pairs per dimension)
4. Context Adjustments (5 contexts with matrix)
5. Non-Negotiable Core (1-2 dimensions)
6. Sample Copy (5 scenarios with annotations)
7. Consistency Check Results
8. Integration Notes

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-dimensions', 'step-03-examples', 'step-04-adjustments', 'step-05-samples', 'step-06-synthesis']
status: completed
```

### 8. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md with Tone of Voice synthesis. Do NOT mark M3 as complete — the Brandbook framework handles that.**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m3-tone-of-voice` to `stepsCompleted` array

**In Progress > M3 Brand section:**

```markdown
### Tone of Voice

**Status:** Completed

**Tone Dimensions:**
| Dimension | Position |
|-----------|----------|
| [Dim 1] | [N]/5 |
| [Dim 2] | [N]/5 |
| [Dim 3] | [N]/5 |

**Voice Summary:** [2-3 sentence summary]

**Non-Negotiable Core:** [1-2 dimensions that never shift]

**Key Findings:**
- [1-sentence on dimension choices]
- [1-sentence on context adjustments]
- [1-sentence on error/support approach]

**Output:** [Link to tone-of-voice.md]
```

### 9. Assumption Inventory Update

Review all assumptions identified during this framework. For each assumption:
1. Check if it already exists in the project-memo Canonical Assumption Inventory.
2. If new: add it with appropriate tier (Existential / High / Lower / Founder Conviction), this framework as source.
3. If existing: update status or evidence if this framework produced new validation data.

### 10. Completion Summary

Present to founder:

> "🎉 **Tone of Voice framework complete!**
>
> **What we achieved in Tone of Voice:**
> - Defined [N] tone dimensions with specific positions
> - Created [N] do/don't examples per dimension
> - Built context adjustments for 5 communication contexts
> - Wrote sample copy for 5 common scenarios
> - Validated consistency with Brand Prism, Archetypes, and Positioning
>
> **Your Voice Summary:**
> '[Voice summary narrative]'
>
> **What feeds forward:**
> - Brandbook: Voice and tone guidelines will be compiled into the brandbook
> - M4: All prototype copy follows this guide
> - M5: All test messaging uses consistent tone
> - M6: This is the production copy standard
>
> **Important:** When new channels emerge (chatbot, push notifications, video), add them to the guide using the context adjustment framework.
>
> **Next recommended framework:** Brandbook — compile all M3 frameworks into a comprehensive brand reference with visual identity."

### 11. Cross-Framework Consistency Gate

**Condition:** Display this section only when ≥3 frameworks are marked completed in the project-memo `stepsCompleted` array for M3.

> **Recommended:** You have completed 3+ frameworks in this milestone. Consider running a cross-framework consistency review in a fresh context to detect drift between framework outputs.
>
> **How:** Open a new conversation and paste the following prompt:
>
> "Review the following framework outputs for [project-name] milestone M3 and identify contradictions, unstated assumption changes, or concept drift between frameworks: [list completed framework output files]"
>
> This is non-blocking — you may continue without running the review.

### 12. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M3** — return to M3 Brand milestone workflow
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M3** is selected:
1. Verify tone-of-voice.md has status: completed
2. Verify project-memo.md has Tone of Voice entry
3. Load `../../workflow.md` and present framework menu

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All consistency checks passed, integration notes complete, tone-of-voice.md complete, project-memo.md updated with framework entry, downstream wiring explicit

❌ **FAILURE:** Consistency checks failed without resolution, project-memo.md not updated, integration notes missing
