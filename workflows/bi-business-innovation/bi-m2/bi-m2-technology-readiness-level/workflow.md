---
name: 'bi-m2-technology-readiness-level'
description: 'Assess technical readiness using NASA TRL 1-9 scale and design de-risking spikes'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m2-validation'
outputFile: technology-readiness-level.md
---

# Technology Readiness Level Framework Workflow

**Goal:** Assess the technical readiness of each major component using NASA's TRL 1-9 scale. Identify what must be proven before prototypation. Design technical spikes for components below TRL 4.

**Your Role:** YC mentor enforcing brutal technical honesty. "We could build that" is TRL 1-2, not TRL 5. Evidence must exist, not be imagined. The weakest component determines the risk profile.

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
| Create | Build TRL assessment from scratch | steps-c/step-01-init.md | technology-readiness-level.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, verify M1 complete, explain TRL framework |
| 02 | Current TRL Assessment | Decompose into components, rate each on TRL 1-9 |
| 03 | Target TRL | Identify risks, unknowns, and target TRL for M4 |
| 04 | Gap Analysis | Design spike cards for low-TRL components |
| 05 | Synthesis | Estimate de-risking effort, overall posture, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Component inventory exists with 4-10 technical building blocks
2. Every component has TRL score (1-9) with evidence statement
3. Technical risk inventory exists with categorized unknowns
4. Spike cards exist for every component below TRL 4
5. Overall posture stated (Green/Yellow/Red) with rationale
6. De-risking effort and timeline estimated
7. Technical risks flagged for Pre-mortem
8. project-memo.md updated with TRL synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/trl-framework.md | TRL scale definitions and methodology | Step 01 |
