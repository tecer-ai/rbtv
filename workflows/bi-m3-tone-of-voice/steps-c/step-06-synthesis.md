---
name: 'step-06-synthesis'
description: 'Validate consistency, wire to M4/M5/M6, update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/tone-of-voice.md'
---

# Step 6: Synthesis

**Progress: Step 6 of 6** — Final Step (Last M3 Framework)

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
You are a YC mentor. Celebrate the milestone. This is the FINAL M3 framework — all brand definition work is complete. The brand now has identity (who), positioning (where), messaging (what), and voice (how).

### Step-Specific Rules
- project-memo.md MUST be updated with Tone of Voice synthesis
- project-memo.md MUST mark M3 Brand as COMPLETE
- All 3 consistency checks are REQUIRED
- Integration notes for M4, M5, M6 are REQUIRED

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

Document how Tone of Voice feeds into downstream milestones:

```markdown
## Integration Notes

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

### 6. Compile Final Document

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

### 7. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md AND mark M3 complete**

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

---

## M3 Brand: COMPLETE ✅

All M3 Brand frameworks completed:
- [ ] Brand Archetypes — [Status]
- [ ] Brand Prism — [Status]
- [ ] Golden Circle — [Status]
- [ ] Brand Positioning — [Status]
- [ ] Messaging Architecture — [Status]
- [ ] Tone of Voice — Completed

**M3 Summary:**
[2-3 sentences summarizing overall brand identity achieved]

**Ready for:** M4 Prototypation, M5 Market Validation
```

### 8. Completion Summary

Present to founder:

> "🎉 **Tone of Voice framework complete — and M3 Brand is FINISHED!**
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
> **What M3 Brand achieved overall:**
> - **Identity:** [Archetype] character with [Prism personality traits]
> - **Positioning:** [Brief positioning statement reference]
> - **Messaging:** [Messaging architecture summary]
> - **Voice:** [Tone summary]
>
> **What feeds forward to M4/M5/M6:**
> - M4: All prototype copy follows this guide
> - M5: All test messaging uses consistent tone
> - M6: This is the production copy standard
>
> **Important:** When new channels emerge (chatbot, push notifications, video), add them to the guide using the context adjustment framework.
>
> **M3 Brand is now complete. Ready for M4 Prototypation or M5 Market Validation.**"

### 9. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M3** — return to M3 Brand milestone workflow
- **[M] Next Milestone** — proceed to M4 or M5
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M3** is selected:
1. Verify tone-of-voice.md has status: completed
2. Verify project-memo.md has Tone of Voice entry
3. Verify project-memo.md marks M3 as complete
4. Load `../bi-m3/workflow.md` and present milestone complete summary

When **[M] Next Milestone** is selected:
1. Verify M3 complete in project-memo
2. Ask user: "M4 Prototypation or M5 Market Validation?"
3. Load appropriate milestone workflow

When **[E] Exit** is selected:
1. Verify all updates saved
2. End workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All consistency checks passed, integration notes complete, tone-of-voice.md complete, project-memo.md updated with framework AND M3 marked complete, downstream wiring explicit

❌ **FAILURE:** Consistency checks failed without resolution, project-memo.md not updated, M3 not marked complete, integration notes missing
