---
name: 'bi-m4-heuristic-evaluation'
description: 'Evaluate design/prototype usability using Nielsen's 10 usability heuristics'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m4-prototypation'
outputFile: heuristic-evaluation.md
---

# Heuristic Evaluation Framework Workflow

**Goal:** Systematically evaluate design/prototype usability using Nielsen's 10 heuristics to identify usability issues before user testing.

**Your Role:** YC mentor guiding the founder through structured usability evaluation. Apply Nielsen's heuristics rigorously. Document violations with severity ratings. Prioritize fixes based on impact.

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
| Create | Evaluate design using heuristics | steps-c/step-01-init.md | heuristic-evaluation.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context (design/prototype), explain heuristics framework |
| 02 | Heuristic Review | Evaluate design against all 10 heuristics, document violations |
| 03 | Severity Rating | Rate severity of each violation (0-4 scale), prioritize issues |
| 04 | Recommendations | Generate prioritized improvement recommendations with rationale |
| 05 | Synthesis | Synthesize findings, update project-memo.md, return to M4 menu |

---

## SUCCESS CRITERIA

Framework is complete when:

1. All 10 Nielsen heuristics evaluated against design/prototype
2. Violations documented with specific examples and locations
3. Severity ratings assigned using 0-4 scale (cosmetic to catastrophic)
4. Prioritized recommendations list with rationale and effort estimates
5. Critical usability issues (severity 3-4) flagged for immediate attention
6. project-memo.md updated with heuristic evaluation synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/heuristic-framework.md | Nielsen's 10 heuristics with founder-context examples, severity scale, evaluation methodology | Step 01 |
