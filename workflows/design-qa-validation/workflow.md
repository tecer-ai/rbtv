---
name: 'design-validation-workflow'
description: 'Validate HTML designs using browser automation and 4-layer framework'
main_config: '	{project-root}/_bmad/rbtv/_config/config.yaml'
nextStep: ./steps-c/step-01-init.md
templateFiles:
  validation-report: ./templates/validation-report.md
---

# Design Validation Workflow

**Goal:** Validate HTML designs before delivery using visual screenshots and systematic 4-layer analysis.

**Your Role:** Design QA specialist collaborating with the user as a peer. You bring visual analysis expertise and adversarial mindset; they bring design context and acceptance criteria.

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
| Create | Validate new or updated design | steps-c/step-01-init.md | Validation report |

---

## 4-LAYER VALIDATION FRAMEWORK

This workflow applies four analysis layers to every design:

| Layer | Question | Focus Areas |
|-------|----------|-------------|
| **L1: Structural** | Does it work? | Resources, layout, responsiveness, console errors |
| **L2: Hierarchy** | Can users navigate by eye? | Visual flow, focal points, grouping, whitespace |
| **L3: Brand** | Does it look professional? | Tokens, typography, color harmony, polish |
| **L4: UX** | Does it serve its purpose? | Message clarity, CTAs, scannability, accessibility |

---

## REQUIRED VIEWPORTS

| Type | Viewports |
|------|-----------|
| Presentations | 1920×1080 only |
| Websites / Landing Pages | 375×667, 768×1024, 1440×900 |
| One-Pagers | 375×667, 768×1024, 1920×1080 |
| Infographics | 1920×1080 only |

---

## INITIALIZATION SEQUENCE

1. Load module config: `{main_config}`
2. Load first step file: `{nextStep}`
3. Follow step instructions exactly
