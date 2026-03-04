---
name: 'pitch-deck'
description: 'Build professional HTML pitch decks optimized for PDF export'
createStep: ./steps-c/step-01-init.md
editStep: ./steps-e/step-e01-load.md
outputFolder: '{project-root}/_bmad-output/{project-name}/_fundraising/pitch-deck'
referenceFile: ./data/pitch-reference.md
htmlPatternsFile: ./data/html-patterns.md
---

# Pitch Deck Workflow

**Goal:** Build professional HTML pitch decks optimized for landscape PDF export (Ctrl+P), with AI-generated image prompts and professional icon libraries.

**Your Role:** Pitch Deck Architect crafting presentations that earn their right to exist. Every slide passes the glance test. Design is compression, not decoration.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **Context-First Discovery** — Always leverage existing documents before asking questions.

### Step Processing Rules

1. Read the complete step file before any action.
2. Follow the MANDATORY SEQUENCE exactly as written.
3. Present menu options and HALT. Wait for user selection.
4. On Continue: load the next step file.
5. On Exit: save any work completed so far, exit workflow.

### Critical Rules

- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read the entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER pre-load or mentally plan future steps

---

## MODES

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Build new pitch deck | steps-c/step-01-init.md | pitch-deck.html + pitch-image-prompts.md |
| Edit | Modify existing deck | steps-e/step-e01-load.md | Updated pitch-deck.html |

**Note:** Mode selection is handled by the Pitch Deck Architect agent. Steps are loaded based on user selection.

---

## CREATE MODE STEPS

| Step | File | Purpose |
|------|------|---------|
| 01 | step-01-init.md | Detect pitch type, project, set output path |
| 02 | step-02-context-gather.md | Gather content from founder docs via context-distill |
| 03 | step-03-structure.md | Plan slide structure and content mapping |
| 04 | step-04-generate.md | Generate HTML pitch deck |
| 05 | step-05-images.md | Generate image prompts for Google Nano Banana |
| 06 | step-06-synthesis.md | Final review and output summary |

## EDIT MODE STEPS

| Step | File | Purpose |
|------|------|---------|
| E01 | step-e01-load.md | Load and analyze existing deck |
| E02 | step-e02-edit.md | Apply modifications |

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/pitch-reference.md | Pitch deck best practices (YC, Sequoia, a16z, Kawasaki) | Step 03 — Structure |
| data/html-patterns.md | HTML/CSS for landscape PDF + icon libraries | Step 04 — Generate |
