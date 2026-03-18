---
name: 'bi-m2-validation'
description: 'Validate technical and financial feasibility through research'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-business-innovation/workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m2-validation'
---

# M2 Validation Milestone Workflow

**Goal:** Validate that the business concept is technically feasible, financially viable, and worth pursuing — or identify specific pivots, de-risking actions, or kill signals before investing further.

**Your Role:** YC mentor guiding the founder through validation frameworks. Challenge assumptions, demand evidence, push for honest assessment. Every unvalidated assumption is a risk you're choosing to ignore.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After each framework, update `stepsCompleted` in project-memo frontmatter.

### Critical Rules

- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read the entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update project-memo after completing each framework
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER pre-load or mentally plan future steps

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Run validation frameworks | steps-c/step-01-init.md | Framework documents |
| Continue | Resume from last framework | steps-c/step-01-init.md (auto-detects) | Updated outputs |

---

## FRAMEWORK ROUTING

| Code | Framework | Workflow | Output File |
|------|-----------|----------|-------------|
| [LF] | Leap of Faith | ../bi-m2-leap-of-faith/workflow.md | leap-of-faith.md |
| [AM] | Assumption Mapping | ../bi-m2-assumption-mapping/workflow.md | assumption-mapping.md |
| [TS] | TAM/SAM/SOM | ../bi-m2-tam-sam-som/workflow.md | tam-sam-som.md |
| [UE] | Unit Economics | ../bi-m2-unit-economics/workflow.md | unit-economics.md |
| [TR] | Technology Readiness Level | ../bi-m2-technology-readiness-level/workflow.md | technology-readiness.md |
| [PM] | Pre-mortem | ../bi-m2-pre-mortem/workflow.md | pre-mortem.md |

### Navigation

| Code | Action |
|------|--------|
| [S] | Show framework completion status |
| [B] | Back to milestone selection (bi-business-innovation) |

---

## SUCCESS CRITERIA

Validation milestone is complete when:

1. Leap of Faith analysis exists with prioritized assumptions, value/growth classification, and kill criteria
2. Assumption map exists showing test-or-accept decisions for all M1 assumptions
3. TAM/SAM/SOM analysis exists with sourced estimates using both top-down and bottom-up methods
4. Unit economics model exists with LTV, CAC, payback period, and break-even estimates
5. TRL assessment exists with component-level ratings and de-risking plan
6. Pre-mortem analysis exists with ranked failure modes and mitigation actions
7. Project-memo Progress > Validation section lists all completed frameworks
8. There is an explicit persevere/pivot/kill recommendation with supporting evidence

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/milestone-overview.md | M2 structure, framework dependencies | Step 01 |
