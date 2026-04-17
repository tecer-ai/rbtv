---
name: 'bi-m3-messaging-architecture'
description: 'Build hierarchical messaging structure from brand promise to CTAs'
nextStep: ./steps-c/step-01-init.md
outputFolder: '{output_path}/{project-name}/business-innovation/m3-brand'
outputFile: messaging-architecture.md
---

# Messaging Architecture Framework Workflow

**Goal:** Build a hierarchical messaging structure (brand promise → key messages → proof points → CTAs) that ensures consistent, audience-specific communication across all touchpoints.

**Your Role:** YC mentor guiding the founder through messaging hierarchy construction. Reject messages without proof. Demand traceability to validated data. Messaging without evidence is marketing fiction.

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
| 03 | Key Messages | Build audience-specific messages with traceability |
| 04 | Proof Points | Attach evidence to each message |
| 05 | CTAs & Journey | Map calls-to-action to customer journey stages |
| 06 | Synthesis | Validate, compile document, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Brand promise exists as single sentence (max 15 words) with documented rationale
2. 3-5 key messages exist per audience with traceability annotations
3. Proof Point Library exists with 2-3 proof points per message, each with source
4. CTA Matrix maps CTAs to journey stages with channel/message/proof links
5. Audience Message Cards exist as one-page summaries per audience
6. Every message traces upward to promise and downward to proof points
7. Messages with insufficient proof flagged for M5 validation
8. project-memo.md updated with Messaging Architecture synthesis

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/messaging-architecture-framework.md | Framework methodology and hierarchy structure | Step 01 |
