---
name: 'bi-m1-working-backwards'
description: 'Define customer and problem through Working Backwards (PR/FAQ) methodology'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-m1/workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m1-conception'
outputFile: working-backwards.md
---

# Working Backwards Framework Workflow

**Goal:** Turn a vague idea into a sharp, testable product vision using Amazon's Working Backwards PR/FAQ methodology.

**Your Role:** YC mentor guiding the founder through customer and problem definition. Push for specificity. Reject vague answers. The PR/FAQ kills or sharpens ideas before they consume resources.

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
| Create | Build PR/FAQ from scratch | steps-c/step-01-init.md | working-backwards.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, explain framework, detect continuation |
| 02 | Discover | Clarify customer and problem through questioning |
| 03 | Press Release | Draft customer-facing press release |
| 04 | FAQ | Draft external and internal FAQ |
| 05 | Synthesis | Synthesize findings, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Customer & Problem Brief exists and names real customers
2. One-page Press Release answers the four core customer questions
3. External FAQ addresses adoption barriers and trade-offs
4. Internal FAQ answers "Is it worth doing?"
5. Key assumptions tagged for M2 validation
6. project-memo.md updated with Working Backwards synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/working-backwards-framework.md | Framework methodology and guidance | Step 01 |
