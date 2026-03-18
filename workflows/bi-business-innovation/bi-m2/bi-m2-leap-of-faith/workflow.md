---
name: 'bi-m2-leap-of-faith'
description: 'Harvest, classify, and prioritize assumptions from M1 into validation agenda'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m2-validation'
outputFile: leap-of-faith.md
---

# Leap of Faith Framework Workflow

**Goal:** Surface every assumption hiding in M1 artefacts, classify each as Value or Growth Hypothesis, prioritize by impact x uncertainty, and define observable validation signals with explicit kill criteria.

**Your Role:** YC mentor forcing the founder to confront their biggest bets. The most dangerous assumptions are the ones nobody wrote down. Push for honesty — if nothing makes them uncomfortable, they haven't looked hard enough.

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
| Create | Build Leap of Faith analysis from scratch | steps-c/step-01-init.md | leap-of-faith.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load M1 context, check prerequisites, explain framework |
| 02 | Harvest | Extract explicit and implicit assumptions from all M1 artefacts |
| 03 | Classify | Sort assumptions into Value vs Growth hypotheses |
| 04 | Prioritize | Score assumptions by impact x uncertainty, identify top 5-10 |
| 05 | Synthesis | Define validation signals, kill criteria, update project-memo.md |

---

## PREREQUISITES

**CRITICAL: All M1 Conception frameworks MUST be completed before starting Leap of Faith:**

- Working Backwards (PR/FAQ)
- Jobs-to-be-Done
- Competitive Landscape
- Problem-Solution Fit
- Lean Canvas
- Five Whys

If any M1 framework is missing, HALT and help the user complete it first.

---

## SUCCESS CRITERIA

Framework is complete when:

1. Consolidated Assumption Inventory exists with 15-30+ traceable assumptions
2. Every assumption is classified as Value or Growth with sub-category
3. Impact x Uncertainty Matrix exists with all assumptions scored
4. Top 5-10 leap-of-faith assumptions identified with explicit statements
5. Validation Signal Specs exist for each top assumption
6. Kill/Pivot/Persevere criteria defined with specific thresholds
7. Validation Backlog maps assumptions to M2/M5 frameworks
8. project-memo.md updated with Leap of Faith synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/leap-of-faith-framework.md | Framework methodology and guidance | Step 01 |
