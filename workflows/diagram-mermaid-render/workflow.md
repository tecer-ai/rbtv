---
name: 'mermaid-conversion-workflow'
description: 'Convert Mermaid diagrams to PNG images using mmdc CLI and validate clarity'
main_config: '	{project-root}/_bmad/rbtv/config.yaml'
nextStep: ./steps-c/step-01-init.md
---

# Mermaid Diagram Conversion Workflow

**Goal:** Convert Mermaid diagrams in Markdown files to PNG images, validate visual clarity, optimize complex layouts, and update Markdown with image references.

**Your Role:** Diagram conversion specialist collaborating with the user as a peer. You bring Mermaid syntax expertise and layout optimization skills; they bring documentation context and quality requirements.

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
| Create | Convert Mermaid diagrams to PNG | steps-c/step-01-init.md | PNG images + updated Markdown |

---

## PREREQUISITES

### Required Tool: Mermaid CLI

The workflow requires `mmdc` (Mermaid CLI) to be installed:

```bash
mmdc --version
```

If missing, user must install: `npm install -g @mermaid-js/mermaid-cli`

### Required MCP: Browser Automation

For diagrams with 5+ nodes, browser MCP tools validate visual clarity:
- `browser_navigate` — Open rendered PNG files
- `browser_take_screenshot` — Capture for inspection

---

## INITIALIZATION SEQUENCE

1. Load module config: `{main_config}`
2. Load first step file: `{nextStep}`
3. Follow step instructions exactly
