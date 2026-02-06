---
name: 'visual-extraction-workflow'
description: 'Extract design tokens from website screenshots'
main_config: '	{project-root}/_bmad/rbtv/config.yaml'
nextStep: ./steps-c/step-01-init.md
templateFiles:
  design-brief: ./templates/design-brief.md
  design-tokens: ./templates/design-tokens.json
---

# Visual Design Extraction Workflow

**Goal:** Extract design tokens (colors, typography, spacing, layout, visual identity) from website screenshots and produce structured documentation.

**Your Role:** Design system analyst collaborating with the user as a peer. You bring visual analysis expertise; they bring domain knowledge and design intent.

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
| Create | Extract tokens from new website | steps-c/step-01-init.md | Design brief or tokens file |

---

## DESIGN TOKEN CATEGORIES

This workflow extracts five categories of design tokens:

| Category | Elements Captured |
|----------|-------------------|
| **Colors** | Primary, secondary, neutral, accent, background (hex values) |
| **Typography** | Font families, sizes, weights, line heights, letter spacing |
| **Spacing** | Base unit, scale (xs-2xl), section gaps, component padding |
| **Layout** | Grid systems, column counts, max-widths, breakpoints |
| **Visual Identity** | Brand tone, aesthetic style, border radius, shadows, density |

---

## INITIALIZATION SEQUENCE

1. Load module config: `{main_config}`
2. Load first step file: `{nextStep}`
3. Follow step instructions exactly
