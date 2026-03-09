---
name: 'step-01-init'
description: 'Load context, verify prerequisites, determine artifact type'
nextStepFile: './step-02-user-flow.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/user-flow-ia.md'
---

# Step 1: Initialize User Flow & IA

**Progress: Step 1 of 4** — Next: User Flow Mapping

---

## STEP GOAL

Verify M1/M3 prerequisites, load context from project-memo and prior frameworks, determine artifact type (landing page, website, infographic).

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Push for conversion-focused decisions. Artifact type determines everything that follows — challenge fuzzy thinking.

### Step-Specific Rules
- M1 AND M3 should be complete before starting (at minimum: Working Backwards, JTBD, Lean Canvas, Brand Archetypes)
- If prerequisites are sparse, WARN but allow proceeding with founder knowledge
- If user-flow-ia.md exists with stepsCompleted, offer to continue
- Do NOT map user flows in this step — that's Step 2

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and stepsCompleted
2. Read `./data/user-flow-ia-framework.md` for framework knowledge
3. Check prerequisites by verifying these exist in stepsCompleted:
   - `bi-m1-working-backwards`
   - `bi-m1-jobs-to-be-done`
   - `bi-m1-lean-canvas`
   - At least one M3 framework (brand direction)
4. Load M2 validation context (if available):
   - `{outputFolder}/technology-readiness-level.md` — check for components below TRL 4
   - `{outputFolder}/leap-of-faith.md` — extract top "Test" quadrant assumptions the prototype should validate
   - `{outputFolder}/unit-economics.md` — extract pricing model and revenue assumptions
5. Check if `{outputFolder}/user-flow-ia.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Check

Check project-memo stepsCompleted for:

**Recommended M1 Frameworks:**
- Working Backwards (target customer, value proposition)
- Jobs-to-be-Done (functional/emotional jobs)
- Lean Canvas (UVP, channels)

**Recommended M2 Frameworks:**
- Technology Readiness Level (technical feasibility constraints)
- Leap of Faith (assumptions the prototype should help validate)
- Unit Economics (pricing/revenue model informing CTA and pricing display)

**Recommended M3 Frameworks:**
- At least one brand framework (tone, messaging)

If missing:
> "⚠️ **Prerequisites Incomplete**
>
> User Flow & IA works best with:
> - [Missing framework list]
>
> You can proceed using founder knowledge, but outputs will be less grounded. Continue anyway?"

If M2 `bi-m2-technology-readiness-level` is missing from stepsCompleted:
> "⚠️ **M2 Validation Gap:** Technology Readiness Level not completed. Components with low technical readiness may be prototyped prematurely. Proceed with caution."

Allow proceeding if user confirms.

### 2. Context Detection

If prerequisites met (or user confirmed):
- Check for existing `user-flow-ia.md` with `stepsCompleted`
- If exists:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to artifact type selection

### 3. Artifact Type Selection

Present artifact types with guidance:

> "What are you building? This determines the entire flow structure.
>
> **[LP] Landing Page** — Single conversion goal, no navigation
> Best for: Lead capture, product launch, email signup
> Structure: Hero → Benefits → Social Proof → CTA
>
> **[WS] Website** — Multiple pages, exploration allowed
> Best for: Product with multiple features, company presence
> Structure: Home → Category → Detail → Conversion
>
> **[IG] Infographic** — Visual data communication, vertical scroll
> Best for: Statistics, research findings, complex explanations
> Structure: Hero → Visual sections → Footer
>
> **[OP] One-Pager** — Document summary, print-friendly
> Best for: Sales collateral, executive summary
> Structure: Header → Key sections → Contact"

HALT — wait for user selection.

### 4. Conversion Goal Definition

Once artifact type selected:

> "What's the single most important action you want users to take?
>
> Examples:
> - Submit email for newsletter
> - Download whitepaper/guide
> - Request demo
> - Sign up for free trial
> - Make a purchase
> - Submit inquiry form
>
> Be specific: 'Get more leads' is too vague. 'Collect email for product launch waitlist' is specific."

HALT — wait for user input.

### 5. Project Context Summary

From project-memo and M1/M2/M3 frameworks, summarize:
- Project name
- Target customer (from Working Backwards or founder knowledge)
- Key value proposition (from Lean Canvas or founder knowledge)
- Primary emotional benefit (from JTBD or founder knowledge)
- Brand tone (from M3 or founder knowledge)

**M2 Validation Context** (if available):
- TRL posture: Any components below TRL 4? (warn: these may not be feasible to prototype)
- Top 3 assumptions the prototype should help validate (from Leap of Faith "Test" quadrant)
- Pricing/revenue model constraints (from Unit Economics)

Present: "Here's the context that will inform your user flow..."

### 6. Create Output Document

If not continuing, create user-flow-ia.md:

```yaml
---
name: user-flow-ia
project: '{project-name}'
artifactType: '{selected-type}'
conversionGoal: '{conversion-goal}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# User Flow & Information Architecture: {Project Name}

## Artifact Type

**Type:** {Landing Page / Website / Infographic / One-Pager}

**Conversion Goal:** {Specific conversion action}

## User Flow Map

*(To be completed in Step 2)*

## Information Architecture

*(To be completed in Step 3)*

## Synthesis

*(To be completed in Step 4)*
```

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to User Flow Mapping

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure user-flow-ia.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-user-flow.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Artifact type selected, conversion goal defined, context summarized, output document created

❌ **FAILURE:** Proceeding without artifact type selection, vague conversion goal, mapping flows in this step
