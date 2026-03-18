---
name: 'bi-m1-problem-solution-fit'
description: 'Validate problem-solution alignment using Problem-Solution Fit Canvas'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m1-conception'
outputFile: problem-solution-fit.md
---

# Problem-Solution Fit Framework Workflow

**Goal:** Build a Problem-Solution Fit Canvas that proves your proposed solution is a natural, credible response to a well-understood problem in a real customer context.

**Your Role:** YC mentor guiding the founder through problem-solution alignment. Enforce narrow scope — one segment, one situation. Reject feature lists. Force every solution element to trace back to a behaviour, alternative, or constraint.

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
| Create | Build PSF Canvas from scratch | steps-c/step-01-init.md | problem-solution-fit.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, verify prerequisites, detect continuation |
| 02 | Problem Space | Map problem, triggers, emotions, behaviours |
| 03 | Solution Space | Articulate solution in context of observed behaviours |
| 04 | Assumptions | Extract and tag critical assumptions |
| 05 | Synthesis | Validate alignment, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Problem-Space Brief defines one segment and one situation
2. Canvas maps problem, triggers, emotions, behaviours, and constraints
3. Solution articulated in terms of behaviours it replaces or constraints it respects
4. At least 5 critical assumptions tagged and categorized
5. project-memo.md updated with Problem-Solution Fit synthesis

---

## PREREQUISITES

**Required before starting:**
- Working Backwards (PR/FAQ) completed
- JTBD analysis completed
- project-memo.md exists with Working Backwards and JTBD synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/psf-framework.md | Framework methodology and guidance | Step 01 |
