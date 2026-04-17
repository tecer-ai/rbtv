---
name: 'bi-m3-golden-circle'
description: 'Define brand purpose using Sinek Why/How/What model'
nextStep: ./steps-c/step-01-init.md
outputFolder: '{output_path}/{project-name}/business-innovation/m3-brand'
outputFile: golden-circle.md
---

# Golden Circle Framework Workflow

**Goal:** Define brand purpose through Simon Sinek's Golden Circle: Why (belief), How (approach), What (offering) — starting from the inside out.

**Your Role:** YC mentor guiding the founder to articulate authentic purpose. The Why must survive product pivots. Challenge marketing-speak. Demand founder ownership of the belief.

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
| Create | Build Golden Circle from scratch | steps-c/step-01-init.md | golden-circle.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, verify prerequisites (Brand Prism), explain framework |
| 02 | Why Discovery | Extract purpose signals, articulate core belief |
| 03 | How Articulation | Define differentiated approach and values |
| 04 | What Definition | State tangible offering connected to Why and How |
| 05 | Synthesis | Validate authenticity, compile document, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Why statement exists — one sentence, no product mention, survives pivot test
2. Why traces to JTBD emotional job AND Brand Prism culture facet
3. How principles (2-3) are observable, differentiating, and connected to Why
4. What statement names product category in plain customer language
5. Why-How-What chain reads as coherent narrative
6. Endurance, Authenticity, and Motivation tests passed
7. Golden Circle is consistent with Brand Prism and Archetypes
8. project-memo.md updated with Golden Circle synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/golden-circle-framework.md | Framework methodology and Why/How/What | Step 01 |
