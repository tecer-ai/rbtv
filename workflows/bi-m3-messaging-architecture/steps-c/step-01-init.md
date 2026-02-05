---
name: 'step-01-init'
description: 'Load context, verify prerequisites, explain Messaging Architecture framework'
nextStepFile: './step-02-brand-promise.md'
outputFile: '{outputFolder}/messaging-architecture.md'
---

# Step 1: Initialize Messaging Architecture

**Progress: Step 1 of 6** — Next: Define Brand Promise

---

## STEP GOAL

Verify Brand Positioning and prior framework prerequisites, load context from project-memo and upstream frameworks, explain Messaging Architecture methodology.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Every message must trace to evidence. "Great messaging" means nothing without proof points sourced from validated data.

### Step-Specific Rules
- Brand Positioning MUST be complete before starting
- If prerequisites are missing, HALT and explain what's needed
- If messaging-architecture.md exists with stepsCompleted, offer to continue
- Do NOT define messages in this step — that starts in Step 2

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and stepsCompleted
2. Read `./data/messaging-architecture-framework.md` for framework knowledge
3. Check prerequisites by verifying these exist in stepsCompleted:
   - `bi-m3-brand-positioning` (REQUIRED — provides positioning foundation)
   - `bi-m3-golden-circle` (REQUIRED — provides emotional Why)
   - `bi-m1-working-backwards` (REQUIRED — provides PR headline)
   - `bi-m1-jobs-to-be-done` (REQUIRED — provides customer language)
4. Recommended (not required):
   - `bi-m3-brand-prism` (personality consistency)
   - `bi-m3-brand-archetypes` (narrative patterns)
   - M2 validation frameworks (evidence for proof points)
5. Check if `{outputFolder}/messaging-architecture.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Verification

Check project-memo stepsCompleted for:

**Required Frameworks:**
- Brand Positioning (provides rational foundation — the benefit clause)
- Golden Circle (provides emotional register — the Why)
- Working Backwards (provides customer-facing narrative and PR headline)
- Jobs-to-be-Done (provides customer language for messages)

**Recommended Frameworks:**
- Lean Canvas (provides audience segments, channels, UVP)
- Brand Prism (personality consistency check)
- Brand Archetypes (narrative patterns)
- M2 Validation (evidence for proof points)

If missing required frameworks:
> "⛔ **Prerequisites Incomplete**
>
> Messaging Architecture builds the hierarchy from promise to proof. That requires:
>
> Missing required: [List missing frameworks]
>
> - Positioning gives you the rational benefit
> - Golden Circle gives you the emotional Why
> - Working Backwards gives you the customer narrative
> - JTBD gives you customer language
>
> Complete missing frameworks first.
>
> Return to: [Missing framework]"

HALT — do not proceed.

### 2. Context Detection

If prerequisites met:
- Check for existing `messaging-architecture.md` with `stepsCompleted`
- If exists:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Messaging Architecture briefly:

> "Messaging Architecture is a hierarchical structure ensuring every word traces to strategy:
>
> We'll build:
> 1. **Brand Promise** — Single sentence (max 15 words) combining emotional + rational
> 2. **Key Messages** — 3-5 per audience with traceability annotations
> 3. **Proof Points** — 2-3 evidence items per message (data, quotes, features-as-benefits)
> 4. **CTA Matrix** — Calls to action by journey stage and channel
>
> Most startups write ad hoc copy. Then landing page says one thing, deck says another, onboarding says a third. This architecture prevents that."

### 4. Load Positioning Foundation

From project-memo and upstream frameworks, extract:

**From Brand Positioning:**
- Full positioning statement
- Key benefit clause (the "that [benefit]" part)
- Competitive frame (unlike X which Y)

**From Golden Circle:**
- Why statement (emotional register)

**From Working Backwards:**
- PR headline
- Customer quote

**From JTBD:**
- Primary job statement
- Customer language examples

Present: "Here's your foundation for the messaging hierarchy..."

### 5. Create Output Document

If not continuing, create messaging-architecture.md:

```yaml
---
name: messaging-architecture
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# Messaging Architecture: {Project Name}

## Brand Promise

*(To be completed in Step 2)*

## Key Messages

*(To be completed in Step 3)*

## Proof Point Library

*(To be completed in Step 4)*

## CTA Matrix

*(To be completed in Step 5)*

## Audience Message Cards

*(To be completed in Step 6)*

## Integration Notes

*(To be completed in Step 6)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Define Brand Promise

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure messaging-architecture.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-brand-promise.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Prerequisites verified, positioning foundation extracted, output document created

❌ **FAILURE:** Proceeding without Brand Positioning, defining messages in this step, skipping foundation extraction
