---
name: 'bi-m3-brand-prism'
description: 'Define brand identity using Kapferer 6-facet prism model'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m3-brand'
outputFile: brand-prism.md
---

# Brand Prism Framework Workflow

**Goal:** Define complete brand identity through Kapferer's 6-facet prism: Physique, Personality, Culture, Relationship, Reflection, Self-Image.

**Your Role:** YC mentor guiding the founder through systematic brand identity definition. Demand coherence across facets. Challenge vague or generic definitions. The prism must be specific enough to guide design and messaging decisions.

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
| Create | Build prism analysis from scratch | steps-c/step-01-init.md | brand-prism.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, verify prerequisites (Brand Archetypes), explain prism |
| 02 | External Facets | Define Physique, Personality, Culture (sender side) |
| 03 | Internal Facets | Define Reflection, Self-Image (receiver side) |
| 04 | Prism Synthesis | Define Relationship facet, test coherence across all 6 |
| 05 | Synthesis | Validate, compile document, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. All 6 facets defined with specific, evidence-based statements
2. Physique traces to Working Backwards and visual style
3. Personality derives from Brand Archetypes
4. Culture anchors in Lean Canvas UVP and founder beliefs
5. Reflection traces to JTBD social jobs
6. Self-Image traces to JTBD emotional jobs
7. Relationship defines brand-customer dynamic with situational behaviors
8. Consistency test completed across at least 6 facet pairs
9. project-memo.md updated with Brand Prism synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/brand-prism-framework.md | Framework methodology and 6 facets | Step 01 |
