---
name: 'bi-m3-messaging-architecture'
description: 'Build hierarchical messaging structure from brand promise through key messages, proof points, and CTAs'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-m3/workflow.md
outputFolder: '{project-root}/_bmad-output/{project-name}/founder/m3-brand'
outputFile: messaging-architecture.md
---

# Messaging Architecture Framework Workflow

**Goal:** Create a hierarchical messaging structure that ensures consistent, audience-specific communication across all touchpoints — from a single brand promise through key messages, proof points, and calls to action.

**Your Role:** YC mentor guiding the founder through message architecture. Demand traceability — every message traces upward to the promise, every proof point traces to validated evidence. Messaging without proof is marketing fantasy.

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
| Create | Build messaging architecture from scratch | steps-c/step-01-init.md | messaging-architecture.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## STEP SEQUENCE

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | Load context, verify prerequisites, explain framework |
| 02 | Brand Promise | Distill positioning into single customer-facing promise |
| 03 | Key Messages | Create 3-5 audience-specific messages with traceability |
| 04 | Proof Points | Build evidence library with 2-3 proof points per message |
| 05 | CTA Matrix | Map calls to action to journey stages and channels |
| 06 | Synthesis | Compile architecture, create audience cards, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Brand promise exists as single sentence (max 15 words) with rationale
2. 3-5 key messages per audience with traceability annotations
3. Proof Point Library with 2-3 evidence items per message
4. CTA Matrix mapping actions to journey stages with channel and message links
5. Audience Message Cards as one-page quick-reference summaries
6. All messages trace upward to promise and downward to proof
7. Messages with insufficient proof flagged for M5 validation
8. project-memo.md updated — this is final M3 framework, trigger M3 completion check

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/messaging-architecture-framework.md | Hierarchy levels, audience definitions, proof point types | Step 01 |
