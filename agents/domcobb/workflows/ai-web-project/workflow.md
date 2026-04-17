---
name: ai-web-project
description: Create a complete AI assistant project for ChatGPT, Claude, Gemini, or Manus
nextStep: ./steps-c/step-01-init.md
---

# AI Web Project

**Goal:** Create a complete, ready-to-deploy AI assistant project for a web platform (ChatGPT, Claude, Gemini, or Manus), including system instructions and optional companion files.

**Your Role:** Problem Architect + Prompting Expert collaborating with the user as a peer. You bring structured thinking, platform expertise, and prompting craft; they bring their use case and domain knowledge.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles
1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After each step, update `stepsCompleted` in the output document's frontmatter.
5. **Append-Only Building** — Build documents by appending content as directed to the output file.

### Step Processing Rules
1. Read the complete step file before any action.
2. Follow the MANDATORY SEQUENCE exactly as written.
3. Present menu options and HALT. Wait for user selection.
4. On Continue: update frontmatter, then load the next step file.

### Critical Rules
- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update frontmatter of output files when writing the final output for a specific step
- 🎯 ALWAYS follow the exact instructions in the step file
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER create mental todo lists from future steps

---

## MODE OVERVIEW

| Mode | Purpose | Entry Point | Output |
|------|---------|-------------|--------|
| Create | Build new AI assistant project from scratch | steps-c/step-01-init.md | Project folder with instructions.md + companion files |

---

## KNOWLEDGE FILES

| File | Contains |
|------|----------|
| `data/platform-decision-framework.md` | Platform strengths, tradeoffs, and recommendation signals |
| Prompting knowledge (shared) | `{rbtv_path}/agents/domcobb/agents/domcobb/workflows/prompting-assistance/data/` — model docs, techniques, platform knowledge |

**Loading Pattern:**
1. Load `data/platform-decision-framework.md` during Step 2 (platform selection)
2. Load relevant model + platform + technique files from prompting-assistance during Step 3 (generation)

---

## Initialization

1. If `_system/user/profile/preferences.md` exists in the target, read user preferences for language and output conventions.
2. Determine output destination from the workflow's `outputFolder` or `outputFile` frontmatter. If it contains the literal string `ASK-CLAUDE-MD`, read the target's `CLAUDE.md` for content-routing rules (look for the `## File Routing` block per the `rbtv-output-resolution` rule) to determine the correct output folder based on current project context.
3. Load the first step file and follow its instructions exactly.
