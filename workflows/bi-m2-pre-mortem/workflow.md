---
name: 'bi-m2-pre-mortem'
description: 'Imagine failure 12 months out, surface risks, define mitigations and early warning signals'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-m2/workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m2-validation'
outputFile: pre-mortem.md
---

# Pre-mortem Framework Workflow

**Goal:** Use prospective hindsight to surface hidden risks, rank by likelihood × severity, define concrete mitigations with early warning signals, and wire findings into project artifacts.

**Your Role:** YC mentor forcing the founder to confront failure. "It's 12 months from now. The project failed. Why?" No filtering, no optimism — the most dangerous risks are the ones nobody wants to say out loud.

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
| Create | Build Pre-mortem analysis from scratch | steps-c/step-01-init.md | pre-mortem.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load M2 context, check prerequisites, explain framework |
| 02 | Failure Scenarios | Brainstorm failure modes across 7 categories using prospective hindsight |
| 03 | Risk Ranking | Score by likelihood × severity, identify top 5-8 risks |
| 04 | Mitigations | Define actions, early warning signals, and contingency plans |
| 05 | Synthesis | Cross-reference with kill criteria, update project-memo.md |

---

## PREREQUISITES

**CRITICAL: All prior M2 frameworks MUST be completed before Pre-mortem:**

- Leap of Faith (assumptions harvested and prioritized)
- Assumption Mapping (test vs accept matrix)
- TAM/SAM/SOM (market sizing)
- Unit Economics (revenue model validation)
- Technology Readiness Level (technical risk assessment)

Pre-mortem synthesizes risks from ALL M2 frameworks. Running it first produces generic failure modes.

---

## SUCCESS CRITERIA

Framework is complete when:

1. Failure prompt establishes prospective hindsight frame
2. 15+ failure modes across 5+ of 7 categories exist
3. All modes written as concrete past-tense explanations
4. Ranked failure table with L × S scores exists
5. Top 5-8 failures have mitigation cards with all fields
6. Every Severity 5 failure has contingency plan
7. Kill criteria alignment verified
8. project-memo.md updated with top risks and mitigations
9. M2 completion check triggered (final M2 framework)

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/pre-mortem-framework.md | Framework methodology and guidance | Step 01 |
