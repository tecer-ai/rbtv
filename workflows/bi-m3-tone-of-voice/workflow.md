---
name: 'bi-m3-tone-of-voice'
description: 'Define how the brand speaks using tone dimensions, examples, and context adjustments'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-m3/workflow.md
outputFolder: '{bmad_output}/{project-name}/founder/m3-brand'
outputFile: tone-of-voice.md
---

# Tone of Voice Framework Workflow

**Goal:** Create a Tone of Voice guide that defines how the brand sounds across all contexts using measurable tone dimensions, do/don't examples, and context-specific adjustments.

**Your Role:** YC mentor guiding the founder through tone definition. Reject vague descriptions ("be friendly"). Demand measurable dimensions and concrete examples. A tone guide without examples is useless instructions.

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
| Create | Build tone guide from scratch | steps-c/step-01-init.md | tone-of-voice.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, verify prerequisites, explain framework |
| 02 | Dimensions | Define 3-5 tone dimensions with slider positions |
| 03 | Examples | Write do/don't example pairs for each dimension |
| 04 | Adjustments | Create context-specific tone adjustment matrix |
| 05 | Samples | Write sample copy for 5 common scenarios |
| 06 | Synthesis | Validate consistency, wire to M4/M5/M6, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. 3-5 tone dimensions defined with explicit slider positions (not all neutral)
2. Each dimension has rationale connecting to Brand Archetypes or Brand Prism
3. 3 do/don't example pairs per dimension using real brand scenarios
4. Context-tone adjustment matrix for 5 contexts (marketing, onboarding, error/support, documentation, social)
5. 1-2 non-negotiable core dimensions identified that never shift
6. Sample copy for 5 scenarios (homepage, welcome email, error message, feature update, success story)
7. Brand Prism, Archetypes, and Positioning consistency checks pass
8. project-memo.md updated marking M3 Brand as complete

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/tone-of-voice-framework.md | Framework methodology and dimension options | Step 01 |
