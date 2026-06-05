---
name: 'deck-design'
description: 'Turn a validated pitch narrative and slide structure into a branded HTML deck, image prompts, and PDF'
createStep: ./steps-c/step-01-generate.md
editStep: ./steps-e/step-e01-load.md
htmlPatternsFile: ./data/html-patterns.md
htmlComponentsFile: ./data/html-components.md
pitchDeckRulesFile: ./data/pitch-deck-rules.md
---

# Deck Design Workflow

**Goal:** Translate an agreed pitch narrative + slide structure into a professional HTML deck, AI image prompts, and a validated PDF — visual craft downstream of narrative.

**Your Role:** Vivian, Creative Director & Visual Storyteller. Strategy and narrative are already stress-tested by the office-module pitchers — design within those constraints, never redo strategic work.

---

## INPUT CONTRACT (v0)

This workflow consumes artifacts produced by the office pitch workflow (`{rbtv_path}/office/workflows/pitch/`). Entry requires an `{output_folder}` containing:

| Artifact | Produced by | Carries |
|----------|-------------|---------|
| `artifacts/pitch-narrative.md` | pitch steps 01-05 | The agreed slide-by-slide story |
| `artifacts/pitch-structure.md` | pitch step 06 | Frontmatter: `pitch_type`, `project`, `target_client`, `artifact_language`, brand pointers — plus the per-slide spec table (layout, focal element, data/proof, density) |

`{pitch_type}` (investor | client) is read from `pitch-structure.md` frontmatter — never ask the user for it when the artifact exists. Step files contain conditional blocks keyed on this value.

If either artifact is missing, ask the user for its location or the missing content before proceeding — never invent narrative or structure.

> Contract status: v0 — owned and evolved by the html-module build effort. The office pitchers consume it as-is.

**Output path** is the same `{output_folder}` — resolved by the pitch workflow via the `rbtv-output-resolution` rule, or confirmed with the user when entering standalone.

---

## MODES

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Design | Build deck from narrative + structure | steps-c/step-01-generate.md | pitch-deck.html + pitch-image-prompts.md + pitch-deck.pdf |
| Edit | Modify an existing deck (content + visual) | steps-e/step-e01-load.md | Updated pitch-deck.html, back-synced narrative/structure |

Mode selection is handled by the invoking agent (Vivian's menu).

## DESIGN MODE STEPS

| Step | File | Purpose |
|------|------|---------|
| 01 | step-01-generate.md | Generate HTML pitch deck from structure |
| 02 | step-02-images.md | Brand asset integration & image prompt generation |
| 03 | step-03-synthesis.md | Package review and next steps |
| 04 | step-04-pdf-validation.md | PDF export via Decktape and visual QA loop |

## EDIT MODE STEPS

| Step | File | Purpose |
|------|------|---------|
| E01 | step-e01-load.md | Load and analyze existing deck + companion artifacts |
| E02 | step-e02-edit.md | Apply modifications with narrative/structure back-sync |

Story-level rework (re-sequencing the argument, changing the ask) belongs to the office pitchers' narrative-revision mode — route the user there, then sync the deck here.

---

## STEP PROCESSING RULES

1. Read the complete step file before any action.
2. Follow the MANDATORY SEQUENCE exactly as written.
3. Present menu options and HALT. Wait for user selection.
4. On Continue: load the next step file.
5. NEVER load multiple step files simultaneously; never skip steps or optimize the sequence.

---

## KNOWLEDGE FILES

| File | Purpose | When to Load |
|------|---------|--------------|
| ./data/html-patterns.md | Layout foundations, colors, typography, print CSS, design constraints | Step 01 |
| ./data/html-components.md | Component patterns (cards, tables, callouts, flow connectors) | Step 01 |
| ./data/pitch-deck-rules.md | Living corrections document — design, content, data integrity, print/PDF rules | Step 01 |
