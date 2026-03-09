---
name: 'step-01-init'
description: 'Load context, verify prerequisites, explain Golden Circle framework'
nextStepFile: './step-02-why-discovery.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/golden-circle.md'
---

# Step 1: Initialize Golden Circle

**Progress: Step 1 of 5** — Next: Why Discovery

---

## STEP GOAL

Verify Brand Prism prerequisite, load context from project-memo and prior frameworks, explain Sinek's Golden Circle methodology.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. The Golden Circle defines WHY the company exists. Challenge marketing-speak. The Why must be authentic to the founder, not aspirational fiction.

### Step-Specific Rules
- Brand Prism MUST be complete before starting Golden Circle
- If prerequisites missing, HALT and explain what's needed
- If golden-circle.md exists with stepsCompleted, offer to continue
- Do NOT define Why/How/What in this step — that's Steps 2-4

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context and stepsCompleted
2. Read `./data/golden-circle-framework.md` for framework knowledge
3. Check prerequisites by verifying these exist in stepsCompleted:
   - `bi-m3-brand-prism` (REQUIRED — Culture facet informs Why)
   - `bi-m3-brand-archetypes` (archetype motivation validates Why)
   - `bi-m1-jobs-to-be-done` (emotional jobs ground Why)
4. Read `{outputFolder}/brand-prism.md` for Culture facet
5. Check if `{outputFolder}/golden-circle.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Verification

Check project-memo stepsCompleted for:

**Required:**
- Brand Prism (Culture facet is the strongest Why signal)

**Required M1/M3 Frameworks:**
- Brand Archetypes (archetype motivation)
- Jobs-to-be-Done (emotional jobs)

If missing Brand Prism:
> "⛔ **Prerequisite Incomplete**
>
> Golden Circle requires Brand Prism to be complete.
> The Why derives from your Culture facet — the beliefs and values your brand embodies.
>
> Complete Brand Prism first, then return here.
>
> Return to: bi-m3-brand-prism"

HALT — do not proceed.

### 2. Context Detection

If prerequisites met:
- Check for existing `golden-circle.md` with `stepsCompleted`
- If exists:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Golden Circle briefly:

> "Simon Sinek's Golden Circle has three layers:
>
> **Why** — Your purpose, cause, or belief beyond profit
> **How** — Your differentiated approach that delivers on Why
> **What** — Your tangible product or service
>
> Most companies communicate outside-in: 'Here's what we make.'
> Great companies start inside-out: 'Here's what we believe.'
>
> The Why must:
> - Survive a complete product pivot
> - Be authentic to you, not aspirational fiction
> - Connect to what customers emotionally need
>
> This framework synthesizes your Culture facet, archetype motivation, and JTBD emotional jobs into a purpose statement."

### 4. Purpose Signals Summary

From project-memo and prior frameworks, extract and present:

**From Brand Prism Culture:**
- Core belief statements
- Values and worldview

**From Brand Archetypes:**
- Primary archetype name
- Core motivation

**From JTBD:**
- Key emotional jobs (what customers want to feel)
- Implied beliefs (what must we believe for these feelings to matter?)

**From Working Backwards:**
- "Why it matters" narrative
- Leader quote

**From Project Memo:**
- Tenets (founder operating beliefs)

Present: "Here are the signals that will inform your Why..."

### 5. Create Output Document

If not continuing, create golden-circle.md:

```yaml
---
name: golden-circle
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
---

# Golden Circle: {Project Name}

## Purpose Signals Summary

*(Compiled from Brand Prism Culture, Archetypes, JTBD, Working Backwards)*

## Why

### Why Statement
*(To be completed in Step 2)*

### Why Narrative
*(To be completed in Step 2)*

## How

### How Principles
*(To be completed in Step 3)*

## What

### What Statement
*(To be completed in Step 4)*

### Why-How-What Chain
*(To be completed in Step 4)*

## Validation

*(To be completed in Step 5)*

## Integration Notes

*(To be completed in Step 5)*

## Synthesis

*(To be completed in Step 5)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Why Discovery

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure golden-circle.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-why-discovery.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Prerequisites verified, purpose signals compiled from multiple sources, output document created

❌ **FAILURE:** Proceeding without Brand Prism, defining Why in this step, skipping signals summary
