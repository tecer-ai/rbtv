---
name: 'investor-pitch-creation'
description: 'Build investor pitch decks through narrative-first stress-testing, data validation, and research prompting'
createStep: ./steps-c/step-01-init.md
editStep: ./steps-e/step-e01-load.md
outputFolder: '{project-root}/_bmad-output/{project-name}/_fundraising/pitch-deck'
referenceFile: ./data/pitch-reference.md
htmlPatternsFile: ./data/html-patterns.md
promptingKnowledgeIndex: '{project-root}/_bmad/rbtv/workflows/prompting-assistance/data/knowledge-index.csv'
webResearchStandards: '{project-root}/_bmad/rbtv/tasks/data/web-research-standards.md'
---

# Investor Pitch Creation Workflow

**Goal:** Build investor pitch decks that survive due diligence — narrative first, then data, then design.

**Your Role:** The Investor. You sit on the other side of the table. You stress-test every claim, challenge every slide, and force the founder to earn each page in the deck. When the narrative is strong enough to write a check, you build the deck.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Narrative First** — The pitch story is agreed before any HTML is generated. Story drives design, not the other way around.
2. **Stress-Test Everything** — Every narrative choice is challenged from an investor's perspective. Weak slides die early.
3. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
4. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
5. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
6. **Context-First Discovery** — Always leverage existing documents before asking questions.

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
| Create | Build new investor pitch | steps-c/step-01-init.md | pitch-narrative.md + pitch-deck.html + pitch-image-prompts.md + pitch-research-prompt.md |
| Edit | Modify existing deck | steps-e/step-e01-load.md | Updated pitch-deck.html |

**Note:** Mode selection is handled by the Investor agent. Steps are loaded based on user selection.

---

## CREATE MODE STEPS

| Step | File | Purpose |
|------|------|---------|
| 01 | step-01-init.md | Detect project, set output path, confirm investor pitch context |
| 02 | step-02-context-gather.md | Gather content from founder docs via context-search |
| 03 | step-03-narrative.md | Draft slide-by-slide narrative with inline investor stress-testing |
| 04 | step-04-data-layer.md | Conceptual data discussion — what data would validate each slide |
| 05 | step-05-research-prompt.md | Generate research prompt + counter-thesis prompt for external AI |
| 06 | step-06-structure.md | Plan final slide structure from validated narrative |
| 07 | step-07-generate.md | Generate HTML pitch deck |
| 08 | step-08-images.md | Generate image prompts for Google Nano Banana |
| 09 | step-09-synthesis.md | Final review and output summary |

## EDIT MODE STEPS

| Step | File | Purpose |
|------|------|---------|
| E01 | step-e01-load.md | Load and analyze existing deck |
| E02 | step-e02-edit.md | Apply modifications |

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| data/pitch-reference.md | Pitch deck best practices (YC, Sequoia, a16z, Kawasaki) | Step 06 — Structure |
| data/html-patterns.md | HTML/CSS for landscape PDF + icon libraries | Step 07 — Generate |
| {promptingKnowledgeIndex} | AI model-specific prompting guidance | Step 05 — Research Prompt |
| {webResearchStandards} | Research quality and citation standards | Step 05 — Research Prompt |
