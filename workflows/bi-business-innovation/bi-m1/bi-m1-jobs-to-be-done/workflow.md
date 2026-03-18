---
name: 'bi-m1-jobs-to-be-done'
description: 'Understand customer progress goals through Jobs-to-be-Done methodology'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m1-conception'
outputFile: jobs-to-be-done.md
---

# Jobs-to-be-Done Framework Workflow

**Goal:** Understand the customer's desired progress through JTBD methodology — discover what job they hire products to do.

**Your Role:** YC mentor guiding the founder through job discovery. Customers don't buy products; they hire them to make progress. Push for real episodes, not hypotheticals.

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
| Create | Build JTBD analysis from scratch | steps-c/step-01-init.md | jobs-to-be-done.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, explain JTBD framework, detect continuation |
| 02 | Job Hypotheses | Turn Working Backwards into 3-5 job hypotheses |
| 03 | Interview | Design and run JTBD interviews |
| 04 | Job Stories | Synthesize job stories, forces, and job map |
| 05 | Synthesis | Prioritize jobs, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. 3-5 job hypotheses drafted from Working Backwards
2. JTBD interview guide created (optional: interviews conducted)
3. Primary job story in "When / I want to / so I can" form
4. Forces analysis and job map documented
5. project-memo.md updated with JTBD synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/jtbd-framework.md | Framework methodology and guidance | Step 01 |
