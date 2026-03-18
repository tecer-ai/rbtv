---
name: 'bi-m1-lean-canvas'
description: 'Map business model hypothesis through Lean Canvas 9-block methodology'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m1-conception'
outputFile: lean-canvas.md
---

# Lean Canvas Framework Workflow

**Goal:** Encode business model hypotheses across nine blocks, creating a testable model anchored to prior frameworks.

**Your Role:** YC mentor guiding the founder through hypothesis articulation. Challenge vague assumptions. Push for specificity. Every block is a hypothesis, not a fact.

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
| Create | Build Lean Canvas from scratch | steps-c/step-01-init.md | lean-canvas.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, explain 9 blocks, check prerequisites |
| 02 | Customer-Problem | Problem (top 3), Customer Segments, Early Adopters |
| 03 | Value-Solution | Unique Value Proposition, Solution (top 3 features) |
| 04 | Channels-Revenue | Channels, Revenue Streams, Cost Structure |
| 05 | Metrics-Advantage | Key Metrics, Unfair Advantage |
| 06 | Synthesis | Tag assumptions, update project-memo.md |

---

## PREREQUISITES

**MUST complete before starting:**
- Working Backwards (PR/FAQ) — customer and problem narrative
- Jobs-To-Be-Done — job stories and forces
- Problem-Solution Fit — solution-problem connections

---

## SUCCESS CRITERIA

Framework is complete when:

1. All 9 blocks populated with specific, testable hypotheses
2. Each block traces to prior framework outputs (WB, JTBD, PSF)
3. Assumptions tagged for M2 validation
4. Competitive landscape informs Unfair Advantage
5. project-memo.md updated with Lean Canvas synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/lean-canvas-framework.md | 9-block methodology and guidance | Step 01 |
