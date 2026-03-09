---
name: 'step-01-init'
description: 'Load context, verify prerequisites, explain Messaging Architecture framework'
nextStepFile: './step-02-brand-promise.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/messaging-architecture.md'
---

# Step 1: Initialize Messaging Architecture

**Progress: Step 1 of 6** — Next: Brand Promise

---

## STEP GOAL

Verify M1/M2/M3 prerequisites, load context from project-memo and prior frameworks, explain Messaging Architecture methodology.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Challenge messaging without proof. Demand traceability to validated data. Messaging without evidence is marketing fiction, not strategy.

### Step-Specific Rules
- M1, M2, AND M3 positioning/prism/golden-circle must be complete before starting
- If prerequisites are missing, HALT and explain what's needed
- If messaging-architecture.md exists with stepsCompleted, offer to continue
- Do NOT build messages in this step — that's Steps 2-5

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and stepsCompleted
2. Read `./data/messaging-architecture-framework.md` for framework knowledge
3. Check M1/M2/M3 prerequisites by verifying these exist in stepsCompleted:
   - `bi-m1-working-backwards`
   - `bi-m1-jobs-to-be-done`
   - `bi-m1-lean-canvas`
   - At least 3 M2 frameworks
   - `bi-m3-brand-positioning`
   - `bi-m3-golden-circle`
   - `bi-m3-brand-prism`
4. Check if `{outputFolder}/messaging-architecture.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Verification

Check project-memo stepsCompleted for:

**Required M1 Frameworks:**
- Working Backwards (PR headline, customer quote, narrative)
- Jobs-to-be-Done (customer language, job stories, forces)
- Lean Canvas (UVP, Customer Segments, Channels)

**Required M2 Frameworks:**
- At least 3 M2 validation frameworks completed (for proof points)

**Required M3 Frameworks:**
- Brand Positioning (positioning statement for rational foundation)
- Golden Circle (Why statement for emotional register)
- Brand Prism (all facets for message consistency)

If missing:
> "⛔ **Prerequisites Incomplete**
>
> Messaging Architecture requires:
> - [Missing framework list]
>
> Complete these before starting Messaging Architecture. You cannot build a messaging hierarchy without positioning, emotional foundation, and customer evidence.
>
> Return to: [M1/M2/M3 milestone]"

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

> "Messaging Architecture is a hierarchical communication structure that ensures every piece of copy you produce traces to a single brand promise and is backed by concrete evidence. We'll build four levels:
>
> 1. **Brand Promise** — Single sentence distilling your positioning + Golden Circle Why
> 2. **Key Messages** — 3-5 messages per audience (early adopters, mainstream, partners, investors)
> 3. **Proof Points** — 2-3 evidence items per message (data, customer quotes, feature-benefits)
> 4. **CTAs** — Calls-to-action mapped to customer journey stages and channels
>
> Every message must trace to validated data from M1/M2. Messages without proof are flagged for M5 validation. The output becomes the canonical source for all brand copy in M4, M5, and M6."

### 4. Project Context Summary

From project-memo and M1/M2/M3 frameworks, summarize:
- Project name
- Brand Positioning Statement (from M3)
- Golden Circle Why (from M3)
- Primary customer and emotional jobs (from M1 JTBD)
- Key validated assumptions (from M2)
- Available proof sources (M2 validation data, JTBD customer quotes)

Present: "Here's the foundation we'll build your messaging hierarchy on..."

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

## Key Messages by Audience

### Early Adopters

*(To be completed in Step 3)*

### Mainstream Customers

*(To be completed in Step 3)*

### Partners

*(To be completed in Step 3)*

### Investors

*(To be completed in Step 3)*

## Proof Point Library

*(To be completed in Step 4)*

## CTA Matrix

*(To be completed in Step 5)*

## Audience Message Cards

*(To be completed in Step 6)*

## Synthesis

*(To be completed in Step 6)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Brand Promise definition

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure messaging-architecture.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-brand-promise.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Prerequisites verified, positioning/Golden Circle/Prism context summarized, available proof sources identified, output document created

❌ **FAILURE:** Proceeding without M1/M2/M3 prerequisites, building messages in this step, skipping proof source identification
