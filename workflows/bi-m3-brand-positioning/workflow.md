---
name: 'bi-m3-brand-positioning'
description: 'Craft positioning statement and perceptual map defining unique market position'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-m3/workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m3-brand'
outputFile: brand-positioning.md
---

# Brand Positioning Framework Workflow

**Goal:** Create a positioning statement and perceptual map that define the brand's unique place in the customer's mind relative to alternatives, grounded in Golden Circle, Brand Prism, and competitive landscape.

**Your Role:** YC mentor guiding the founder through positioning. Reject vague category frames and weak competitive alternatives. Demand specificity in every element. Positioning without a perceptual map is unvalidated assumption.

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
| Create | Build positioning analysis from scratch | steps-c/step-01-init.md | brand-positioning.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, verify prerequisites, explain framework |
| 02 | Inputs | Consolidate positioning inputs from upstream frameworks |
| 03 | Draft | Draft positioning statement with template and annotations |
| 04 | Map | Create perceptual map with competitor positions |
| 05 | Test | Run 4 validation tests (Uniqueness, Credibility, Relevance, Consistency) |
| 06 | Synthesis | Compile document, wire to downstream frameworks, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Positioning Inputs Brief exists with Target, Need, Benefit, Category, Alternatives, Differentiators
2. Positioning statement follows template: "For [target] who [need], [brand] is the [category] that [benefit], unlike [alternative] which [limitation]"
3. Every element annotated with strategic rationale
4. Perceptual map exists with 5+ competitors, brand position, and white space analysis
5. All 4 tests passed: Uniqueness, Credibility, Relevance, Consistency
6. Wiring notes prepared for Messaging Architecture, Tone of Voice, M4 Design Brief
7. project-memo.md updated with Brand Positioning synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/brand-positioning-framework.md | Framework methodology and template | Step 01 |
