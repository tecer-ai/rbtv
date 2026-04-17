---
name: 'pitch'
description: 'Build pitch decks through narrative-first stress-testing, data validation, and research prompting'
pitch_type: '{pitch_type}'
createStep: ./steps-c/step-01-init.md
editStep: ./steps-e/step-e01-load.md
outputFolder_investor: '{bmad_output}/{project-name}/_fundraising/{round}/YYYY-MM-DD-{fund}/'
outputFolder_client: '{bmad_output}/{project-name}/_clients/{client}/presentations/YYYY-MM-DD-{objective}/'
referenceFile: ../_shared/pitch-data/pitch-reference.md
htmlPatternsFile: ../_shared/pitch-data/html-patterns.md
promptingKnowledgeIndex: '{project-root}/_bmad/rbtv/agents/domcobb/agents/domcobb/workflows/prompting-assistance/data/knowledge-index.csv'
webResearchStandards: '{project-root}/_bmad/rbtv/tasks/data/web-research-standards.md'
---

# Pitch Creation Workflow

**If pitch_type = investor:**
**Goal:** Build investor pitch decks that survive due diligence — narrative first, then data, then design.

**Your Role:** The Investor. You sit on the other side of the table. You stress-test every claim, challenge every slide, and force the founder to earn each page in the deck. When the narrative is strong enough to write a check, you build the deck.

**If pitch_type = client:**
**Goal:** Build client/sales pitch decks that survive procurement committees — narrative first, then proof, then design.

**Your Role:** The Buyer. You sit on the client's side of the table. You stress-test every claim from the perspective of someone who has to defend this purchase to their CFO. When the narrative is strong enough to sign a contract, you build the deck.

---

## PITCH TYPE PARAMETER

This workflow supports two pitch types via the `{pitch_type}` variable:

| pitch_type | Audience | Output Folder Pattern | Stress-Test Perspective |
|------------|----------|---------------|------------------------|
| `investor` | VCs, angels, accelerators | `_fundraising/{round}/YYYY-MM-DD-{fund}/` | The Investor — would I write a check? |
| `client` | Customers, partners, procurement | `_clients/{client}/presentations/YYYY-MM-DD-{objective}/` | The Buyer — would I sign a contract? |

The `{pitch_type}` is set during workflow invocation by the agent command. Each step file contains conditional blocks that adapt content, framing, and deliverables based on this parameter.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Narrative First** — The pitch story is agreed before any HTML is generated. Story drives design, not the other way around.
2. **Stress-Test Everything** — Every narrative choice is challenged from the audience's perspective. Weak slides die early.
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

- NEVER load multiple step files simultaneously
- ALWAYS read the entire step file before execution
- NEVER skip steps or optimize the sequence
- ALWAYS halt at menus and wait for user input
- NEVER pre-load or mentally plan future steps

---

## MODES

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Build new pitch | steps-c/step-01-init.md | pitch-narrative.md + pitch-deck.html + pitch-image-prompts.md + pitch-research-prompt.md |
| Edit | Modify existing deck | steps-e/step-e01-load.md | Updated pitch-deck.html |

**Note:** Mode selection is handled by the invoking agent. Steps are loaded based on user selection.

---

## CREATE MODE STEPS

| Step | File | Purpose |
|------|------|---------|
| 01 | step-01-init.md | Detect project, set output path, confirm pitch context |
| 02 | step-02-context-gather.md | Gather content from founder docs via context-distill |
| 03 | step-03-narrative.md | Draft slide-by-slide narrative with inline stress-testing |
| 04 | step-04-data-layer.md | Conceptual data/proof discussion — what evidence would validate each slide |
| 05 | step-05-research-prompt.md | Generate research prompt + adversarial prompt for external AI |
| 06 | step-06-structure.md | Plan final slide structure from validated narrative |
| 07 | step-07-generate.md | Generate HTML pitch deck |
| 08 | step-08-images.md | Visual identity integration & image prompt generation |
| 09 | step-09-synthesis.md | Final review and output summary |
| 10 | step-10-pdf-validation.md | PDF export via Decktape and visual QA loop |

## EDIT MODE STEPS

| Step | File | Purpose |
|------|------|---------|
| E01 | step-e01-load.md | Load and analyze existing deck |
| E02 | step-e02-edit.md | Apply modifications |

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| ../_shared/pitch-data/pitch-reference.md | Pitch deck best practices | Step 06 — Structure |
| ../_shared/pitch-data/html-patterns.md | Layout foundations, colors, typography, print CSS, design constraints | Step 07 — Generate |
| ../_shared/pitch-data/html-components.md | Component patterns (cards, tables, callouts, flow connectors) | Step 07 — Generate |
| {promptingKnowledgeIndex} | AI model-specific prompting guidance | Step 05 — Research Prompt |
| {webResearchStandards} | Research quality and citation standards | Step 05 — Research Prompt |
