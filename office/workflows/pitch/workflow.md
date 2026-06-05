---
name: 'pitch'
description: 'Build pitch narratives through stress-testing, data validation, and research prompting — HTML design delegated to the html module'
pitch_type: '{pitch_type}'
createStep: ./steps-c/step-01-init.md
editStep: ./steps-e/step-e01-narrative.md
referenceFile: ./data/pitch-reference.md
webResearchStandards: '{rbtv_path}/core/workflows/web-search/data/web-research-standards.md'
---

# Pitch Creation Workflow

**If pitch_type = investor:**
**Goal:** Build investor pitch narratives that survive due diligence — narrative first, then data, then structure. Design execution is delegated.

**Your Role:** The Investor. You sit on the other side of the table. You stress-test every claim, challenge every slide, and force the founder to earn each page in the deck. When the narrative is strong enough to write a check, you lock the structure and hand off to design.

**If pitch_type = client:**
**Goal:** Build client/sales pitch narratives that survive procurement committees — narrative first, then proof, then structure. Design execution is delegated.

**Your Role:** The Buyer. You sit on the client's side of the table. You stress-test every claim from the perspective of someone who has to defend this purchase to their CFO. When the narrative is strong enough to sign a contract, you lock the structure and hand off to design.

---

## PITCH TYPE PARAMETER

This workflow supports two pitch types via the `{pitch_type}` variable:

| pitch_type | Audience | Stress-Test Perspective |
|------------|----------|------------------------|
| `investor` | VCs, angels, accelerators | The Investor — would I write a check? |
| `client` | Customers, partners, procurement | The Buyer — would I sign a contract? |

The `{pitch_type}` is set during workflow invocation (by the dispatch file or the invoking persona). Each step file contains conditional blocks that adapt content, framing, and deliverables based on this parameter.

**Output path** is resolved via the `rbtv-output-resolution` rule (File Routing in workspace CLAUDE.md). The workflow never hardcodes folder conventions — the workspace owns its own directory structure.

---

## SCOPE — NARRATIVE ONLY

This workflow owns the pitch NARRATIVE: story, data layer, research prompts, and slide structure. It NEVER generates or edits HTML. HTML deck design, image prompts, and PDF export execute in the html module's deck-design workflow (`{rbtv_path}/html/workflows/deck-design/workflow.md`), invoked via the `rbtv-designing` skill (Vivian).

### Handoff Contract (v0)

Step 06 finalizes two artifacts in `{output_folder}/artifacts/` that the deck-design workflow consumes:

| Artifact | Carries |
|----------|---------|
| `pitch-narrative.md` | The agreed slide-by-slide story with data annotations |
| `pitch-structure.md` | Frontmatter (pitch_type, project, target, language, brand pointers) + per-slide spec table (layout, focal element, data/proof, density) |

Contract status: v0 — owned and evolved by the html-module build effort; this workflow produces it as specified there.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Narrative First** — The pitch story is agreed before any HTML is generated. Story drives design, not the other way around.
2. **Stress-Test Everything** — Every narrative choice is challenged from the audience's perspective. Weak slides die early.
3. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
4. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
5. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
6. **Context-First Discovery** — Once the output path is resolved, derive the entity directory and brand location from File Routing. Read existing documents before asking questions.

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
| Create | Build new pitch narrative | steps-c/step-01-init.md | pitch-narrative.md + pitch-structure.md + pitch-research-prompt.md → handoff to deck-design |
| Revise | Story-level rework of an existing narrative | steps-e/step-e01-narrative.md | Updated pitch-narrative.md + pitch-structure.md → re-handoff |

**Note:** Mode selection is handled by the invoking agent. HTML deck editing is NOT a mode here — it lives in the deck-design workflow's edit mode (Vivian's menu).

---

## CREATE MODE STEPS

| Step | File | Purpose |
|------|------|---------|
| 01 | step-01-init.md | Detect project, set output path, confirm pitch context |
| 02 | step-02-context-gather.md | Gather context from entity directory and brand folder |
| 03 | step-03-narrative.md | Draft slide-by-slide narrative with inline stress-testing |
| 04 | step-04-data-layer.md | Conceptual data/proof discussion — what evidence would validate each slide |
| 05 | step-05-research-prompt.md | Generate research prompt + adversarial prompt for external AI |
| 06 | step-06-structure.md | Plan final slide structure, write pitch-structure.md, hand off to design |

## REVISE MODE STEPS

| Step | File | Purpose |
|------|------|---------|
| E01 | step-e01-narrative.md | Story-level narrative revision with audience stress-testing + re-handoff |

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| ./data/pitch-reference.md | Pitch deck best practices | Step 06 — Structure |
| {webResearchStandards} | Research quality and citation standards | Step 05 — Research Prompt |
