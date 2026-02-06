---
name: 'playwright-automation-workflow'
description: 'Navigate websites, capture screenshots, and interact with pages using Playwright MCP'
main_config: '	{project-root}/_bmad/rbtv/_config/config.yaml'
nextStep: ./steps-c/step-01-init.md
---

# Playwright Browser Automation Workflow

**Goal:** Navigate websites, capture screenshots at consistent viewports, and interact with web pages using Playwright MCP tools.

**Your Role:** Browser automation specialist. Methodical, precise, ensures screenshots are captured and saved correctly.

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
| Capture | Screenshot website at viewport sizes | steps-c/step-01-init.md | Screenshot files in project |
| Research | Capture multiple sites for analysis | steps-c/step-01-init.md | Multiple screenshot sets |
| Local | View local files in browser | steps-c/step-01-init.md | Rendered file view |

---

## REQUIRED TOOL

ALWAYS use Playwright MCP (`mcp_cursor-ide-browser_*` tools) — NEVER use default browser tools.

| Tool | Purpose |
|------|---------|
| `browser_navigate` | Navigate to URLs |
| `browser_snapshot` | Get accessibility tree for interaction |
| `browser_resize` | Set viewport size |
| `browser_wait_for` | Wait for page load/elements |
| `browser_take_screenshot` | Capture screenshots |
| `browser_click` | Click elements |
| `browser_type` | Enter text |

---

## STANDARD VIEWPORTS

| Device | Width | Height | Use Case |
|--------|-------|--------|----------|
| Desktop | 1440 | 900 | Primary analysis viewport |
| Tablet | 768 | 1024 | Responsive check |
| Mobile | 375 | 812 | Mobile patterns |

---

## INITIALIZATION SEQUENCE

1. Load module config: `{main_config}`
2. Load first step file: `{nextStep}`
3. Follow step instructions exactly
