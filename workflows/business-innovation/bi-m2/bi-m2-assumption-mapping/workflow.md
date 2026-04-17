---
name: 'bi-m2-assumption-mapping'
description: 'Plot assumptions on Importance x Uncertainty matrix and design validation tests'
nextStep: ./steps-c/step-01-init.md
outputFolder: '{output_path}/{project-name}/business-innovation/m2-validation'
outputFile: assumption-mapping.md
---

# Assumption Mapping Framework Workflow

**Goal:** Plot all business assumptions on an Importance x Uncertainty matrix, assign actions (Test/Accept/Monitor/Ignore), and design lightweight validation tests for the highest-risk assumptions.

**Your Role:** YC mentor guiding the founder through rigorous assumption triage. Push for differentiation — not every assumption is critical. Demand concrete test designs, not vague plans. The matrix prevents wasted effort on low-priority tests.

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
| Create | Build assumption map from scratch | steps-c/step-01-init.md | assumption-mapping.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, verify Leap of Faith complete, explain framework |
| 02 | Collect | Collect and normalize assumptions from all sources |
| 03 | Rate | Rate each assumption on Importance (1-5) and Uncertainty (1-5) |
| 04 | Matrix | Plot on 2x2 matrix, assign Test/Accept/Monitor/Ignore actions |
| 05 | Tests | Design lightweight test cards for "Test" assumptions |
| 06 | Synthesis | Document findings, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Normalized assumption inventory exists (8-25 deduplicated assumptions)
2. Every assumption has Importance and Uncertainty scores with justification
3. 2x2 matrix visualization exists with all assumptions placed
4. Every "Test" assumption has a test card with hypothesis, method, success/failure signals
5. Validation backlog is sequenced and fits within 2-4 weeks
6. project-memo.md updated with Assumption Mapping synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/assumption-mapping-framework.md | Framework methodology and guidance | Step 01 |
