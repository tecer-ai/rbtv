---
name: 'bi-m3-brand-archetypes'
description: 'Define brand character using Carl Jung 12 universal archetypes'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-m3/workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m3-brand'
outputFile: brand-archetypes.md
---

# Brand Archetypes Framework Workflow

**Goal:** Select a primary brand archetype (and optional secondary) grounded in customer emotional/social jobs, with concrete expression guidance for voice, visuals, relationship, and content.

**Your Role:** YC mentor guiding the founder through archetype selection. Reject aspirational choices not grounded in customer evidence. Demand specificity in expression. Archetypes without expression guidance are worthless labels.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After each step, update `stepsCompleted` in output document frontmatter.

### Critical Rules

- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read the entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update frontmatter after completing each step
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER pre-load or mentally plan future steps

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Build archetype analysis from scratch | steps-c/step-01-init.md | brand-archetypes.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, verify prerequisites, explain framework |
| 02 | Exploration | Extract emotional territory, evaluate all 12 archetypes |
| 03 | Selection | Select primary/secondary archetype with justification |
| 04 | Application | Define archetype expression (voice, visuals, relationship, themes) |
| 05 | Synthesis | Validate, compile document, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Emotional Territory Brief exists traceable to M1/M2 artefacts
2. All 12 archetypes evaluated with scores across emotional fit, purpose fit, differentiation
3. Primary archetype selected with written justification
4. If secondary archetype selected, blend ratio defined and coherent
5. Archetype Expression Guide exists (voice, visuals, relationship, themes)
6. At least 3 competitors mapped to approximate archetypes
7. Differentiation confirmed against competitors
8. project-memo.md updated with Brand Archetypes synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/brand-archetypes-framework.md | Framework methodology and 12 archetypes | Step 01 |
