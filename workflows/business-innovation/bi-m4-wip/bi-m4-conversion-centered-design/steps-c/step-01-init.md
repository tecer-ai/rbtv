---
name: 'step-01-init'
description: 'Load context, explain Conversion-Centered Design framework, verify prerequisites'
nextStepFile: './step-02-funnel-mapping.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/conversion-optimization.md'
---

# Step 1: Initialize Conversion-Centered Design

**Progress: Step 1 of 5** — Next: Funnel Mapping

---

## STEP GOAL

Load context from prior M4 work (user-flow-ia, design outputs), explain the Conversion-Centered Design framework, and prepare for conversion funnel analysis.

---

## Prior Context

**Builds on:** User Flow & IA, Design Context
**Inherits (do not restate):** Conversion paths, information architecture — reference `{outputFolder}/user-flow-ia.md`; content hierarchy, CTA priorities — reference design context outputs
**This framework adds:** Funnel optimization, friction analysis, conversion hypotheses, prioritization matrix

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Challenge decorative design choices. Every element must justify its existence by driving conversion. Be ruthless about distractions.

### Step-Specific Rules
- If conversion-optimization.md exists with stepsCompleted, offer to continue from last step
- Do NOT generate optimization recommendations in this step — that's for later steps
- Prerequisites: User Flow & IA [U] MUST be completed before this framework

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context
2. Read `{outputFolder}/user-flow-ia.md` for user flow and content hierarchy
3. Read `./data/conversion-framework.md` for framework knowledge
4. Check if `{outputFolder}/conversion-optimization.md` exists (continuation mode)
5. If design outputs exist (`design_brief.md`, `design.json`), note visual direction
6. If available, read M3 messaging outputs for conversion content grounding:
   - `{outputFolder}/messaging-architecture.md` — message hierarchy (brand promise, key messages, proof points, CTAs) so CTA analysis uses actual project messaging
   - `{outputFolder}/jobs-to-be-done.md` — customer forces (push/pull/anxieties) so friction analysis references actual customer barriers

---

## MANDATORY SEQUENCE

### 1. Prerequisite Check

Verify User Flow & IA is complete:
- Check project-memo.md for `bi-m4-user-flow-ia` in stepsCompleted
- If NOT complete:
  > "⛔ PREREQUISITE NOT MET: User Flow & IA [U] must be completed before Conversion Optimization.
  > 
  > User Flow & IA provides the conversion funnel structure we'll optimize. Without it, we're optimizing blindly.
  > 
  > **Return to M4 menu and complete [U] first.**"
  
  HALT — Do not proceed.

### 2. Context Detection

Check for existing outputs:
- If `conversion-optimization.md` exists with `stepsCompleted`:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Conversion-Centered Design briefly:

> "Conversion-Centered Design (CCD) focuses every design decision on driving ONE action. We'll analyze your prototype through 7 principles:
>
> 1. **Attention Ratio** — Links competing with your CTA
> 2. **Visual Hierarchy** — Is CTA the most prominent element?
> 3. **Directional Cues** — Do visuals guide toward conversion?
> 4. **Friction Reduction** — What barriers slow users down?
> 5. **Urgency/Scarcity** — Legitimate motivation to act now?
> 6. **Encapsulation** — Is the CTA zone clearly defined?
> 7. **Congruence** — Does the page match user expectations?
>
> The goal: **identify friction points and generate testable optimization hypotheses.**"

### 4. Context Summary

From user-flow-ia.md, summarize:
- Artifact type (landing page, website, infographic, etc.)
- Primary conversion goal
- Key funnel stages identified
- Content hierarchy structure

**Strategic Content Context** (if available):
- Message hierarchy from Messaging Architecture (brand promise → key messages → proof points → CTAs)
- Customer anxieties and barriers from JTBD forces analysis (friction points to address in conversion design)

Present: "Here's what I understand about your conversion flow..."

### 5. Create Output Document

If not continuing, create conversion-optimization.md:

```yaml
---
name: conversion-optimization
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
artifactType: '{artifact-type}'
conversionGoal: '{conversion-goal}'
---

# Conversion Optimization: {Project Name}

## Funnel Analysis

*(To be completed in Step 2)*

## Friction Points

*(To be completed in Step 2)*

## Optimization Hypotheses

*(To be completed in Step 3)*

## Prioritization Matrix

*(To be completed in Step 4)*

## Testing Roadmap

*(To be completed in Step 4)*

## Synthesis

*(To be completed in Step 5)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Funnel Mapping

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure conversion-optimization.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-funnel-mapping.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** User understands CCD framework, prerequisites verified, context loaded, output document created

❌ **FAILURE:** Proceeding without User Flow & IA complete, generating optimizations in this step, not creating output document
