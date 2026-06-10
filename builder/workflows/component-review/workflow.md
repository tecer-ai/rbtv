---
name: component-review
description: Token-efficiency diagnosis of an existing component — measured baseline, sub-agent investigation, waste-pattern synthesis
nextStep: ./step-01-intake.md
outputFolder: ASK-CLAUDE-MD
---

# Component Review

**Goal:** Produce an evidence-based token-efficiency diagnosis of a target component — measured costs, tested hypotheses, and prioritized format fixes that preserve every protection.

**Your Role:** Efficiency diagnostician collaborating with the component's owner. You bring the waste-pattern taxonomy and measurement discipline; the owner brings felt pain and quality judgment.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles
1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After each step, update `stepsCompleted` in the output document's frontmatter.
5. **Append-Only Building** — Build the diagnosis by appending content to the output file.

### Critical Rules
- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update frontmatter of the output file when writing a step's final output
- 🎯 ALWAYS follow the exact instructions in the step file
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER create mental todo lists from future steps

---

## DIAGNOSTIC PRINCIPLES

The five Diagnostic Method Requirements in `./data/efficiency-patterns.md` bind every step of this workflow. Read that file's "Diagnostic Method Requirements" section at Step 1 and hold them for the run: measured figures only, quality floor, hypotheses tested, counter-evidence hunted, read-only investigators.

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Review | Diagnose an existing component's token efficiency | step-01-intake.md | efficiency-diagnosis-{component}-{date}.md |

---

## Initialization

1. Determine output destination from `outputFolder`. It contains `ASK-CLAUDE-MD`: read the workspace `CLAUDE.md` content-routing rules per the `rbtv-output-resolution` rule, propose the resolved path with reasoning, and wait for confirmation.
2. Load `./step-01-intake.md` and follow its instructions exactly.
