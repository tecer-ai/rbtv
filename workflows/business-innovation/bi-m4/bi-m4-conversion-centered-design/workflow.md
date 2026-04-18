---
name: 'bi-m4-conversion-centered-design'
description: 'Optimize conversion funnel using Conversion-Centered Design principles'
nextStep: ./steps-c/step-01-init.md
outputFolder: '{project-name}/business-innovation/m4-prototypation'
outputFile: conversion-optimization.md
---

# Conversion-Centered Design Framework Workflow

**Goal:** Optimize the prototype's conversion funnel by applying Conversion-Centered Design principles to maximize user action and minimize friction.

**Your Role:** YC mentor guiding conversion optimization. Challenge decorative choices, demand evidence for every design decision. If an element doesn't drive conversion, it's a distraction. Kill it.

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
| Create | Optimize conversion from scratch | steps-c/step-01-init.md | conversion-optimization.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, explain framework, verify prerequisites |
| 02 | Funnel Mapping | Map conversion funnel stages and identify friction points |
| 03 | Hypothesis Generation | Generate optimization hypotheses based on friction analysis |
| 04 | Optimization Plan | Prioritize experiments and create testing roadmap |
| 05 | Synthesis | Synthesize findings, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Conversion funnel mapped with stages: Attention → Interest → Credibility → Action
2. Friction points identified at each stage with severity ratings
3. Optimization hypotheses generated for top friction points
4. Hypotheses prioritized by impact vs. effort matrix
5. Testing roadmap created with measurable success criteria
6. CTA optimization strategy documented (placement, copy, contrast, urgency)
7. Distraction audit completed (elements removed or justified)
8. project-memo.md updated with Conversion Optimization synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/conversion-framework.md | Conversion-Centered Design principles and patterns | Step 01 |
