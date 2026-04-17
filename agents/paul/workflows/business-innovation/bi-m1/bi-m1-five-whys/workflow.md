---
name: 'bi-m1-five-whys'
description: 'Trace problems to structural root causes using 5 Whys methodology'
nextStep: ./steps-c/step-01-init.md
outputFolder: '{output_path}/{project-name}/business-innovation/m1-conception'
outputFile: five-whys.md
---

# Five Whys Framework Workflow

**Goal:** Trace visible problems to structural root causes through disciplined iterative "why" questioning, and identify which levers your solution will address.

**Your Role:** YC mentor guiding the founder through root cause analysis. Enforce one scenario per chain. Reject individual blame — push for systems, incentives, constraints. Demand evidence for facts vs hypotheses.

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
| Create | Build 5 Whys analysis from scratch | steps-c/step-01-init.md | five-whys.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, explain framework, detect continuation |
| 02 | Problem Framing | Select and frame concrete problem scenario |
| 03 | Why Chain | Run 5 Whys chains, separate facts from hypotheses |
| 04 | Root Cause | Synthesize root causes, select structural levers |
| 05 | Synthesis | Wire to Lean Canvas and validation backlog, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Anchor Problem Statement and Scenario Brief exist and trace to prior M1 artefacts
2. At least one 5 Whys chain reaches a structural root cause
3. All chain links are labelled Fact or Hypothesis with evidence noted
4. Root Cause Map identifies targeted vs non-targeted causes
5. Lean Canvas Problem block updated with structural causes
6. project-memo.md updated with Five Whys synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/five-whys-framework.md | Framework methodology and guidance | Step 01 |
