---
name: 'step-01-init'
description: 'Load context, verify prerequisites, explain Assumption Mapping framework'
nextStepFile: './step-02-collect.md'
continueStepFile: './step-01b-continue.md'
outputFile: '{outputFolder}/assumption-mapping.md'
---

# Step 1: Initialize Assumption Mapping

**Progress: Step 1 of 6** — Next: Collect & Normalize Assumptions

---

## STEP GOAL

Load context from project-memo and Leap of Faith, verify prerequisites are complete, explain the Assumption Mapping framework, and prepare for assumption collection.

---

## Prior Context

**Builds on:** Leap of Faith
**Inherits (do not restate):** Assumption inventory, classification — reference `{outputFolder}/leap-of-faith.md`
**This framework adds:** Assumption scoring (impact × uncertainty), prioritized test cards, validation experiment design

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Challenge assumptions, demand differentiation, push for concrete test designs. Continue this persona throughout.

### Step-Specific Rules
- If assumption-mapping.md exists with stepsCompleted, offer to continue from last step
- Do NOT score assumptions in this step — that's for later steps
- MUST verify Leap of Faith is complete before proceeding

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/project-memo.md` for project context
2. Read `{outputFolder}/leap-of-faith.md` for assumption inventory
3. Read `./data/assumption-mapping-framework.md` for framework knowledge
4. Read `{outputFolder}/bmad-analysis/` contents (if exists) for research-backed assumptions to include in mapping
5. Check if `{outputFolder}/assumption-mapping.md` exists (continuation mode)

---

## MANDATORY SEQUENCE

### 1. Prerequisite Check

Verify Leap of Faith is complete:
- Check project-memo.md `stepsCompleted` for `bi-m2-leap-of-faith`
- Check if `leap-of-faith.md` exists with status: completed

**If Leap of Faith NOT complete:**
> "⚠️ Prerequisite Missing: Assumption Mapping requires a completed Leap of Faith analysis.
>
> Leap of Faith provides the prioritized assumption inventory with value/growth hypothesis classification and kill criteria that we need before scoring.
>
> **Action needed:** Return to M2 workflow and complete Leap of Faith first."

HALT and present option to return to M2 workflow.

### 2. Context Detection

Check for existing outputs:
- If `assumption-mapping.md` exists with `stepsCompleted`:
  - Display last completed step
  - Offer: "Continue from step N?" or "Start fresh?"
- If no existing output:
  - Proceed to framework introduction

### 3. Framework Introduction

Explain Assumption Mapping briefly:

> "Assumption Mapping takes your Leap of Faith assumptions and plots them on a 2x2 matrix of Importance x Uncertainty. This visual triage tells us exactly what to do with each assumption:
>
> - **Test** (high importance + high uncertainty): Design and run validation experiments
> - **Accept** (high importance + low uncertainty): Treat as working assumption
> - **Monitor** (low importance + high uncertainty): Track passively
> - **Ignore** (low importance + low uncertainty): No action needed
>
> The goal is to **prevent wasted effort** — testing things that don't matter or accepting things that could kill the business."

### 4. Leap of Faith Summary

From leap-of-faith.md, summarize:
- Total number of assumptions identified
- Number of Value Hypothesis assumptions
- Number of Growth Hypothesis assumptions
- Kill criteria (assumptions that would kill the business if wrong)

Present: "Here's what Leap of Faith identified..."

### 5. Create Output Document

If not continuing, create assumption-mapping.md:

```yaml
---
name: assumption-mapping
project: '{project-name}'
stepsCompleted: ['step-01-init']
status: in-progress
prerequisite: leap-of-faith
---

# Assumption Mapping: {Project Name}

## Normalized Assumption Inventory

*(To be completed in Step 2)*

## Scored Assumptions

*(To be completed in Step 3)*

## Assumption Matrix

*(To be completed in Step 4)*

## Test Cards

*(To be completed in Step 5)*

## Synthesis

*(To be completed in Step 6)*
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Collect & Normalize Assumptions

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure assumption-mapping.md exists with frontmatter
2. Verify `step-01-init` is in `stepsCompleted`
3. Load `./step-02-collect.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Leap of Faith verified complete, framework explained, output document created

❌ **FAILURE:** Proceeding without Leap of Faith, scoring assumptions in this step, not creating output document
