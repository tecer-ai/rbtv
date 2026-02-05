---
name: 'bi-m4-user-flow-ia'
description: 'Map user flows and define information architecture for conversion-optimized prototypes'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-m4/workflow.md
outputFolder: '{project-root}/_bmad-output/{project-name}/founder/m4-prototypation'
outputFile: user-flow-ia.md
---

# User Flow & Information Architecture Framework Workflow

**Goal:** Map the user's journey from first contact to conversion, and structure content hierarchy to maximize comprehension and action.

**Your Role:** YC mentor guiding conversion-focused design. Challenge flows that bury the CTA, demand clarity at every decision point. If a user can't understand what to do next in 3 seconds, the flow is broken.

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
| Create | Build user flow and IA from scratch | steps-c/step-01-init.md | user-flow-ia.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, verify prerequisites, determine artifact type |
| 02 | User Flow Mapping | Map primary user journey from entry to conversion |
| 03 | Information Architecture | Structure content hierarchy for conversion funnel |
| 04 | Synthesis | Validate, compile document, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Artifact type determined (landing page, website, infographic, etc.)
2. Primary user flow documented with entry points, screens, decisions, conversion goal
3. Exit points and drop-off risks identified
4. Content inventory created from M1/M3 outputs
5. Information architecture follows AIDA funnel: Attention → Interest → Credibility → Action
6. Content hierarchy defined per section (primary, secondary, supporting)
7. CTA placement strategy documented
8. project-memo.md updated with User Flow & IA synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/user-flow-ia-framework.md | Framework methodology and patterns | Step 01 |
