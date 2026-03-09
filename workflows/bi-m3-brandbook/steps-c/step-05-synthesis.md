---
name: 'step-05-synthesis'
description: 'Validate consistency, compile final brandbook, mark M3 complete, update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/brandbook.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 5: Synthesis

**Progress: Step 5 of 5** — Final Step (Last M3 Framework)

---

## STEP GOAL

Validate brandbook consistency with all M3 frameworks, compile the final document, UPDATE project-memo.md, and mark M3 Brand as COMPLETE.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. This is the final M3 step — celebrate the achievement. The founder now has a complete brand system: identity, visual language, messaging, and voice, all in one document. The brandbook is the canonical reference for every brand decision going forward.

### Step-Specific Rules
- project-memo.md MUST be updated with Brandbook synthesis
- project-memo.md MUST mark M3 Brand as COMPLETE
- All consistency checks are REQUIRED
- Integration notes for M4, M5, M6 are REQUIRED

---

## CONTEXT TO LOAD

1. Read complete `{outputFolder}/brandbook.md` from Steps 1-4
2. Read `{outputFolder}/project-memo.md` for update
3. Read `{outputFolder}/brand-prism.md` for consistency check
4. Read `{outputFolder}/brand-archetypes.md` for consistency check
5. Read `{outputFolder}/tone-of-voice.md` for consistency check

---

## MANDATORY SEQUENCE

### 1. Visual-Verbal Consistency Check

Verify that visual choices align with verbal identity:

```markdown
### Visual-Verbal Consistency Check

| Visual Element | Brand Personality Alignment | Result |
|---------------|---------------------------|--------|
| Color Palette | Does it reflect [{archetype}] personality? | ✅/❌ |
| Typography | Does it match the tone (e.g., formal type for formal tone)? | ✅/❌ |
| Logo | Does it embody the Brand Prism Physique facet? | ✅/❌ |
| Imagery Style | Does it reinforce the brand relationship type? | ✅/❌ |
| Icon Style | Is it consistent with logo and typography direction? | ✅/❌ |

**Result:** ✅ PASS / ❌ FAIL
```

If FAIL: Document inconsistency and resolve by adjusting the conflicting element.

### 2. Cross-Framework Traceability Check

Verify every brandbook element traces to a framework output:

```markdown
### Cross-Framework Traceability Check

| Brandbook Section | Source Framework(s) | Traceable? |
|-------------------|---------------------|------------|
| Mission Statement | Golden Circle — Why | ✅/❌ |
| Vision Statement | Golden Circle — What | ✅/❌ |
| Brand Persona | Archetypes + Prism | ✅/❌ |
| Target Audience | JTBD + Lean Canvas | ✅/❌ |
| Brand Values | Prism Culture + GC How | ✅/❌ |
| Brand Story | Working Backwards + GC | ✅/❌ |
| Color Palette | Prism Physique + Archetype | ✅/❌ |
| Typography | Personality + Tone | ✅/❌ |
| Logo | Prism Physique + Archetype | ✅/❌ |
| Brand Voice | Tone of Voice | ✅/❌ |
| Tagline | Messaging Architecture | ✅/❌ |
| Value Proposition | Positioning + Lean Canvas | ✅/❌ |
| Key Messaging | Messaging Architecture | ✅/❌ |

**Result:** ✅ All elements traceable / ❌ Gaps found
```

If gaps found: Document and resolve.

### 3. Prepare Downstream Integration Notes

```markdown
## Downstream Integration

### M4 Prototypation

**Design Brief:**
- Use brandbook as the canonical visual reference
- All prototype UI must follow color palette, typography, and imagery guidelines
- Logo placement follows brandbook clear space rules
- All copy follows tone guidelines and context adjustments

**Prototype Copy:**
- Headlines: Use key messages from Messaging & Tone section
- CTAs: Use exact CTA text from Messaging Architecture
- Microcopy: Follow tone guidelines for context-specific adjustments
- Tagline: Display as defined in brandbook

### M5 Market Validation

**Testing Materials:**
- All test copy must follow brand voice and tone guidelines
- A/B test variants must stay within brandbook parameters
- SPIN scripts use investor key messages from messaging section
- Landing page tests use approved visual identity

### M6 MVP

**Production Standards:**
- Brandbook is the canonical reference for all production assets
- Marketing site, app UI, and communications follow visual guidelines
- New team members and partners receive brandbook for onboarding
- Any new visual or verbal assets must align with brandbook standards
```

### 4. Document Key Decisions

Ask:

> "Reflecting on the brandbook process:
> - Are you satisfied with the visual identity? Does it feel like YOUR brand?
> - Which visual element was hardest to get right?
> - Is there anything in the brandbook you want to revisit in M4?
> - How confident are you in using this brandbook to guide all future brand decisions?"

Record responses:

```markdown
## Key Decisions and Learnings

**Visual Identity Confidence:** {High/Medium/Low — founder's assessment}

**Hardest Element:** {Which visual element required most iteration}

**M4 Revisit List:** {Any elements to refine during prototypation}

**Founder Notes:** {Any additional reflections}
```

### 5. Compile Final Document

Ensure brandbook.md contains all sections in correct order:

1. Brand Identity (Mission, Vision, Persona, Audience, Values, Story)
2. Visual Guidelines (Logo, Color Palette, Typography, Imagery, Iconography)
3. Messaging & Tone (Voice, Tone Guidelines, Tagline, Value Proposition, Key Messaging)
4. Quick Reference Sheet
5. Consistency Check Results
6. Downstream Integration
7. Key Decisions and Learnings

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-identity', 'step-03-visual', 'step-04-messaging', 'step-05-synthesis']
status: completed
```

### 6. UPDATE project-memo.md

**CRITICAL: This step MUST update project-memo.md AND mark M3 complete**

Read project-memo.md and update:

**In frontmatter:**
- Add `bi-m3-brandbook` to `stepsCompleted` array
- Set `currentMilestone: m4-prototypation` (M3 is complete, advance to M4)

**In Progress > M3 Brand section:**

```markdown
### Brandbook

**Status:** Completed

**Key Deliverables:**
- Brandbook document: brandbook.md
- Logo assets: brandbook-assets/logo-primary.png, logo-secondary.png, logo-mono.png
- Imagery references: brandbook-assets/imagery-example-*.png
- Quick reference sheet included in brandbook

**Tagline:** "{Tagline}"

**Visual Identity Summary:**
- Colors: {Primary color names and hex codes}
- Typography: {Primary} (headings) + {Secondary} (body)
- Logo: {Brief description of logo concept}

**AI Image Tool Used:** {preferredImageTool}

**Output:** [Link to brandbook.md]

---

## M3 Brand: COMPLETE ✅

All M3 Brand frameworks completed:
- [x] Brand Archetypes — Completed
- [x] Brand Prism — Completed
- [x] Golden Circle — Completed
- [x] Brand Positioning — Completed
- [x] Messaging Architecture — Completed
- [x] Tone of Voice — Completed
- [x] Brandbook — Completed

**M3 Summary:**
{2-3 sentences summarizing overall brand identity achieved, including visual identity}

**Ready for:** M4 Prototypation, M5 Market Validation
```

### 7. Completion Summary

Present to founder:

> "🎉 **Brandbook complete — and M3 Brand is FINISHED!**
>
> **What we achieved in the Brandbook:**
> - Compiled brand identity from all 6 frameworks
> - Defined visual identity: logo, color palette, typography, imagery, iconography
> - Generated and iterated on logo and imagery with {preferredImageTool}
> - Compiled messaging guidelines with approved tagline
> - Built a one-page quick reference sheet
> - Validated consistency across all brand elements
>
> **Your Tagline:** '{Tagline}'
>
> **What M3 Brand achieved overall:**
> - **Identity:** [{Archetype}] character with [{personality traits}]
> - **Positioning:** [{Positioning statement — abbreviated}]
> - **Messaging:** [{Brand promise}] with hierarchical message architecture
> - **Voice:** [{Voice summary}]
> - **Visual:** [{Logo concept}], [{primary colors}], [{typefaces}]
>
> **Your brandbook is the single source of truth for every brand decision.**
>
> **What feeds forward to M4/M5/M6:**
> - M4: Design brief and prototype copy follow the brandbook
> - M5: All test materials use brand-consistent visuals and messaging
> - M6: Production assets inherit from the brandbook
>
> **M3 Brand is now complete. Ready for M4 Prototypation or M5 Market Validation.**"

### 8. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine synthesis or project-memo entry
- **[B] Back to M3** — return to M3 Brand milestone workflow
- **[M] Next Milestone** — proceed to M4 or M5
- **[E] Exit** — end session

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

When **[B] Back to M3** is selected:
1. Verify brandbook.md has status: completed
2. Verify project-memo.md has Brandbook entry
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

✅ **SUCCESS:** All consistency checks passed, integration notes complete, brandbook.md complete with all sections, project-memo.md updated with Brandbook entry AND M3 marked complete, tagline approved, visual assets saved and referenced

❌ **FAILURE:** Consistency checks failed without resolution, project-memo.md not updated, M3 not marked complete, missing visual assets, integration notes missing
