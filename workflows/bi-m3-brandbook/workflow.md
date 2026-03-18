---
name: 'bi-m3-brandbook'
description: 'Compile all M3 brand frameworks into a comprehensive brandbook with visual identity'
nextStep: ./steps-c/step-01-init.md
parentWorkflow: ../bi-m3/workflow.md
outputFolder: '{bmad_output}/{project-name}/business-innovation/m3-brand'
outputFile: brandbook.md
---

# Brandbook Framework Workflow

**Goal:** Synthesize all 6 M3 brand framework outputs into a single brandbook document — adding visual identity specifications (logo, colors, typography, imagery, iconography) through AI-assisted image generation — to produce the canonical brand reference.

**Your Role:** This workflow uses multiple agents. Paul (mentor) owns steps 01-02 and 04-05. Vivian (designer) owns step 03. Agent handoff instructions are embedded in the step files at each boundary.

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
| Create | Build brandbook from M3 outputs | steps-c/step-01-init.md | brandbook.md |
| Continue | Resume from last step | steps-c/step-01-init.md (auto-detects) | Updated output |

---

## MULTI-AGENT ROUTING

This workflow spans two agents. Handoff instructions are embedded in the step files at each boundary.

| Step Range | Agent | Command | Responsibility |
|------------|-------|---------|----------------|
| 01-02 | Paul (mentor) | `@bmad-rbtv-mentor` | Init, Brand Identity compilation |
| 03 | Vivian (designer) | `@bmad-rbtv-designer` → [BV] | Visual Guidelines (color, typography, logo, imagery, iconography) |
| 04-05 | Paul (mentor) | `@bmad-rbtv-mentor` | Messaging & Tone, Synthesis |

**Handoff flow:** Paul completes step 02 → user invokes Vivian for step 03 → Vivian completes step 03 → user invokes Paul for step 04.

---

## STEP SEQUENCE

| Step | Name | Agent | Purpose |
|------|------|-------|---------|
| 01 | Init | Paul | Load all M3 contexts, verify prerequisites, set up AI image tool preference |
| 02 | Identity | Paul | Compile Brand Identity section from M3 frameworks |
| 03 | Visual | Vivian | Create Visual Guidelines with AI image prompts for logo/imagery |
| 04 | Messaging | Paul | Compile Messaging & Tone section, craft tagline, build quick reference |
| 05 | Synthesis | Paul | Validate, compile final document, mark M3 complete, update project-memo.md |

---

## SUCCESS CRITERIA

Framework is complete when:

1. Brand Identity section compiled from all 6 M3 frameworks
2. Visual Guidelines created with logo, colors, typography, imagery, iconography
3. Logo and imagery generated via AI prompts, approved by founder, saved to output folder
4. Messaging & Tone section compiled with tagline and quick reference
5. All visual elements have explicit do's/don'ts
6. Quick reference sheet exists as one-page summary
7. project-memo.md updated with Brandbook synthesis and M3 marked COMPLETE
8. Founder has a single document that answers: What does our brand look like? How does it sound? What are the rules?

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/brandbook-framework.md | Framework methodology and brandbook structure | Step 01 |

## EXTERNAL KNOWLEDGE

| File | Purpose | When to Load |
|------|---------|--------------|
| {project-root}/_bmad/rbtv/workflows/prompting-assistance/data/knowledge-index.csv | AI model/platform knowledge for image prompts | Step 03 |
