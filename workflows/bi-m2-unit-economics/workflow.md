---
name: 'bi-m2-unit-economics'
description: 'Model LTV, CAC, payback, and break-even to assess financial viability'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-m2/workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m2-validation'
outputFile: unit-economics.md
---

# Unit Economics Framework Workflow

**Goal:** Model the financial viability of the business at the per-customer level. Calculate LTV, CAC, LTV:CAC ratio, payback period, and break-even — all with explicit assumption ranges.

**Your Role:** YC mentor demanding financial honesty. Push for ranges not point estimates. Never let optimistic scenarios mask pessimistic reality. Every number is a hypothesis until validated.

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
| Create | Build unit economics model from scratch | steps-c/step-01-init.md | unit-economics.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, verify TAM/SAM/SOM complete, explain framework |
| 02 | CAC Analysis | Define unit, estimate CAC per channel and blended |
| 03 | LTV Calculation | Calculate ARPU, gross margin, churn, and LTV ranges |
| 04 | Payback Period | Compute LTV:CAC ratio, payback, cash implications |
| 05 | Synthesis | Model break-even, sensitivity analysis, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Unit Definition Statement exists with clear revenue model
2. CAC estimates exist per channel and blended (pessimistic/base/optimistic)
3. LTV estimates exist with ARPU, margin, and churn assumptions
4. LTV:CAC ratio computed for pessimistic and base scenarios
5. Payback period stated with cash flow implications
6. Break-even customer count and timeline modelled
7. Sensitivity analysis identifies top 3-5 critical assumptions
8. project-memo.md updated with Unit Economics synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/unit-economics-framework.md | Framework methodology and guidance | Step 01 |
