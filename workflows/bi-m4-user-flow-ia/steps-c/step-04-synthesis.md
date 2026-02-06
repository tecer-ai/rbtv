---
name: 'step-04-synthesis'
description: 'Validate, compile document, update project-memo.md'
nextStepFile: null
outputFile: '{outputFolder}/user-flow-ia.md'
---

# Step 4: Synthesis

**Progress: Step 4 of 4** — Final Step

---

## STEP GOAL

Validate user flow and IA against conversion principles, compile final document, update project-memo.md with User Flow & IA synthesis.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. The User Flow & IA document is the foundation for prototype design. If this is weak, the prototype will fail. Validate rigorously.

### Step-Specific Rules
- All validation checks MUST pass before completion
- project-memo.md MUST be updated with synthesis
- Next step guidance MUST be clear (Design Direction via BMAD)

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/user-flow-ia.md` for complete user flow and IA
2. Read `{outputFolder}/project-memo.md` for update

---

## MANDATORY SEQUENCE

### 1. Final Validation Checklist

Run complete validation:

> "**User Flow & IA Final Validation:**
>
> **User Flow Validation:**
> - [ ] Single conversion goal clearly defined
> - [ ] Entry points documented with user mindset
> - [ ] All screens mapped with purpose
> - [ ] Decision points identified with desired paths
> - [ ] Exit points documented with drop-off risks
> - [ ] 3-click rule satisfied (conversion ≤3 clicks)
> - [ ] CTA above fold on mobile (375px)
> - [ ] No escape routes (landing page) / clear nav (website)
>
> **Information Architecture Validation:**
> - [ ] Content inventoried from M1/M3 frameworks
> - [ ] AIDA funnel structure complete (Attention, Interest, Credibility, Action)
> - [ ] Content hierarchy defined per section (Primary, Secondary, Tertiary)
> - [ ] CTA placement strategy documented
> - [ ] Content density appropriate for artifact type
> - [ ] All content supports conversion (no decorative elements)
>
> **Issues Found:** [list any failures]"

If any validation fails:
> "⚠️ **Validation Failed**
>
> The following issues must be resolved:
> - [Issue 1]: [Fix needed]
> - [Issue 2]: [Fix needed]
>
> Return to [Step 2/3] to address."

HALT until issues resolved.

### 2. Design Direction Readiness

Confirm document is ready for BMAD create-ux-design workflow:

> "**Design Direction Readiness:**
>
> The user-flow-ia.md document will inform the BMAD create-ux-design workflow:
>
> | IA Output | BMAD Input |
> |-----------|------------|
> | Artifact type | Design scope (landing page, website, etc.) |
> | Content hierarchy | Visual hierarchy requirements |
> | CTA placement | Layout priorities |
> | Content inventory | Content to style |
> | AIDA sections | Section structure |
>
> When you start Design Direction [D], reference this document as context for design discovery (visual-design-extraction, playwright-browser-automation; optionally design-validation)."

### 3. Compile Synthesis

Generate synthesis section:

```markdown
## Synthesis

### Overview
**Artifact Type:** [type]
**Conversion Goal:** [goal]
**Target User:** [from Working Backwards]

### Key Flow Decisions
1. [Decision 1 and rationale]
2. [Decision 2 and rationale]
3. [Decision 3 and rationale]

### Content Strategy Summary
- **Hero Focus:** [headline strategy]
- **Benefits Emphasis:** [what benefits prioritized]
- **Credibility Approach:** [social proof strategy]
- **CTA Strategy:** [placement and messaging]

### Design Direction Guidance
When executing BMAD create-ux-design:
- Visual hierarchy must support [primary content]
- Layout must ensure CTA visibility at [breakpoints]
- Content density: [low/medium/high] for [artifact type]
- Brand alignment: [M3 outputs to reference]

### Risk Factors
- **Drop-off Risk 1:** [risk] → **Mitigation:** [mitigation]
- **Drop-off Risk 2:** [risk] → **Mitigation:** [mitigation]

### Validation Status
- ✅ User flow complete and validated
- ✅ Information architecture complete and validated
- ✅ Ready for Design Direction (BMAD create-ux-design)
```

### 4. Update Output Document

Finalize user-flow-ia.md:

1. Add Synthesis section (from step 3)
2. Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-user-flow', 'step-03-information-architecture', 'step-04-synthesis']
status: complete
```

### 5. Update Project Memo

Update `{outputFolder}/project-memo.md`:

**Add to stepsCompleted array:**
```yaml
stepsCompleted:
  - ... (existing)
  - bi-m4-user-flow-ia
```

**Add to Progress > Prototypation section:**

```markdown
### User Flow & Information Architecture
**Status:** Complete
**Document:** m4-prototypation/user-flow-ia.md

**Summary:**
- Artifact type: [type]
- Conversion goal: [goal]
- User flow: [entry] → [screens] → [conversion]
- AIDA structure: Hero (attention) → Benefits (interest) → Social Proof (credibility) → Final CTA (action)

**Key Insights:**
- [Insight 1 from flow mapping]
- [Insight 2 from IA work]

**Next:** Design Direction via BMAD create-ux-design workflow
```

### 6. Present Completion Summary

> "**User Flow & IA Complete** ✅
>
> **What was created:**
> - `user-flow-ia.md` with complete user flow and information architecture
> - Project-memo updated with M4 User Flow & IA synthesis
>
> **Next Step:**
> Return to M4 milestone menu and select **[D] Design Direction** to create visual design via BMAD's create-ux-design workflow.
>
> The user-flow-ia.md document provides:
> - Artifact type and conversion goal
> - Content hierarchy for visual design
> - CTA placement requirements
> - Section structure for layout
>
> Reference this document when starting Design Direction."

### 7. Present Menu Options

**Select an Option:**
- **[B] Back** — return to M4 Prototypation milestone menu
- **[R] Review** — review completed document

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

Framework is COMPLETE. User should return to M4 milestone workflow and select next framework (typically Design Direction [D]).

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** All validations passed, synthesis complete, project-memo updated, clear next step guidance provided

❌ **FAILURE:** Validation failures not resolved, synthesis missing, project-memo not updated, next step unclear
