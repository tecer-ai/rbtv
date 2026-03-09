---
name: 'bi-m1-conception'
description: 'Structure idea into comprehensive business concept through 6 frameworks'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-business-innovation/workflow.md
outputFolder: '{bmad_output}/{project-name}/founder/m1-conception'
---

# M1 Conception Milestone Workflow

**Goal:** Structure an idea into a comprehensive business concept with clear problem definition, solution articulation, target customer understanding, and initial business model.

**Your Role:** YC mentor guiding the founder through conception frameworks. Challenge assumptions, demand clarity, push for specificity. This is a partnership — you bring startup expertise, they bring domain knowledge.

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
| Create | Run conception frameworks | steps-c/step-01-init.md | Framework documents |
| Continue | Resume from last framework | steps-c/step-01-init.md (auto-detects) | Updated outputs |

---

## FRAMEWORK ROUTING

| Code | Framework | Workflow | Output File |
|------|-----------|----------|-------------|
| [WB] | Working Backwards | ../bi-m1-working-backwards/workflow.md | working-backwards.md |
| [JT] | Jobs-to-be-Done | ../bi-m1-jobs-to-be-done/workflow.md | jobs-to-be-done.md |
| [CL] | Competitive Landscape | ../bi-m1-competitive-landscape/workflow.md | competitive-landscape.md |
| [PS] | Problem-Solution Fit | ../bi-m1-problem-solution-fit/workflow.md | problem-solution-fit.md |
| [LC] | Lean Canvas | ../bi-m1-lean-canvas/workflow.md | lean-canvas.md |
| [5W] | Five Whys | ../bi-m1-five-whys/workflow.md | five-whys.md |

### Navigation

| Code | Action |
|------|--------|
| [S] | Show framework completion status |
| [B] | Back to milestone selection (bi-business-innovation) |

---

## SUCCESS CRITERIA

Conception milestone is complete when:

1. Working Backwards document exists with Press Release and FAQ
2. Jobs-to-be-Done analysis exists
3. Competitive Landscape analysis exists with geographic benchmarks
4. Problem-Solution Fit Canvas exists
5. Lean Canvas exists with informed Unfair Advantage
6. Five Whys analysis exists
7. Project-memo Progress > Conception section lists all completed frameworks
8. Founder can articulate: Who is the customer? What problem? Why our solution? What must be true?

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/milestone-overview.md | M1 structure, framework dependencies | Step 01 |
