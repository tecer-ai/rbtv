---
name: design-extraction
description: 'Extract design tokens from a live website via multi-page navigation, DOM/CSS extraction, and visual analysis'
nextStep: ./steps-c/step-01-init.md
templateFiles:
  design-brief: ./templates/design-brief.md
  design-tokens: ./templates/design-tokens.json
---

# Visual Design Extraction Workflow

**Goal:** Navigate a live website, capture multiple pages, extract design tokens from the DOM/CSS and visual analysis, and produce structured documentation.

**Your Role:** Design system analyst collaborating with the user as a peer. You bring visual analysis expertise and programmatic extraction capability; they bring domain knowledge and design intent.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles

1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After each step, update `stepsCompleted` in the output document's frontmatter.

### Step Processing Rules

1. Read the complete step file before any action.
2. Follow the MANDATORY SEQUENCE exactly as written.
3. Present menu options and HALT. Wait for user selection.
4. On Continue: update frontmatter, then load the next step file.

### Critical Rules

- NEVER load multiple step files simultaneously
- ALWAYS read the entire step file before execution
- NEVER skip steps or optimize the sequence
- ALWAYS update frontmatter after completing each step
- ALWAYS halt at menus and wait for user input
- NEVER pre-load or mentally plan future steps

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Extract tokens from new website | steps-c/step-01-init.md | Design brief and/or tokens JSON |

---

## STEP OVERVIEW

| Step | Name | Purpose |
|------|------|---------|
| 01 | Init | URL confirmation, output format, create output document |
| 02 | Site Discovery | Navigate site, map pages/sections/interactive states, user confirms capture list |
| 03 | Capture & DOM Extraction | Per-page: full-page screenshot + comprehensive DOM/CSS extraction |
| 04 | Token Synthesis | Merge DOM data with visual analysis, consolidate tokens across all pages |
| 05 | Document | Generate design brief and/or tokens JSON, save to output folder |

---

## DESIGN TOKEN CATEGORIES

| Category | Elements Captured |
|----------|-------------------|
| **Colors** | Primary, secondary, neutral, accent, background (hex values from DOM + visual) |
| **Typography** | @font-face declarations, font families, sizes, weights, line heights, letter spacing |
| **Spacing** | Base unit, scale, section gaps, component padding, margins, gaps |
| **Layout** | Grid systems, column counts, max-widths, breakpoints, media queries |
| **Visual Identity** | Brand tone, aesthetic style, border radius, shadows, density |
| **Transitions** | Durations, easings, animation keyframes |
| **CSS Variables** | :root custom properties and inline variable declarations |

---

## OUTPUT QUALITY CONSTRAINTS

1. The tokens JSON output must NEVER contain `null` for any field extractable from the site's DOM/CSS.
2. `null` is only acceptable when the site genuinely does not define that token.
3. Every token must document its source: `"dom"` (from stylesheets/computed styles) or `"screenshot-sampled"` (from visual analysis).
4. DOM-extracted values always take precedence over screenshot-sampled values.

---

## INITIALIZATION SEQUENCE

1. Load module config: `{main_config}`
2. Load first step file: `{nextStep}`
3. Follow step instructions exactly
