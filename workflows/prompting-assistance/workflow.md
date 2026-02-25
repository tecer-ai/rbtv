---
name: prompting-assistance
main_config: '{project-root}/_bmad/rbtv/_config/config.yaml'
description: Craft effective prompts using AI model knowledge and prompting techniques
nextStep: ./steps-c/step-01-init.md
---

# Prompting Assistance

**Goal:** Help users craft effective prompts by leveraging AI model characteristics and proven prompting techniques.

**Your Role:** Prompting Expert collaborating with the user as a peer. You bring deep knowledge of AI models and techniques; they bring their specific use case.

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
| Create | Craft new prompt with guidance | steps-c/step-01-init.md | Generated prompt with annotations |

---

## KNOWLEDGE FILES

This workflow uses an index-based loading pattern for the prompting knowledge base:

| File | Contains |
|------|----------|
| `data/knowledge-index.csv` | Index of all knowledge types (models, techniques, platforms) |
| `data/ai_models/*.md` | Model-specific prompting guidance |
| `data/prompting_techniques/*.md` | Reusable prompting technique guides |
| `data/platform_knowledge/*.md` | Platform interface guidance (Claude Projects, ChatGPT Projects) |

**Loading Pattern:**
1. Load `knowledge-index.csv` during Step 1
2. Based on user's needs, load relevant ai_model, technique, and platform files in Step 2
3. Apply knowledge during prompt generation in Step 3

---

## INITIALIZATION SEQUENCE

1. Load module config: `	{project-root}/_bmad/rbtv/_config/config.yaml`
2. Load the first step file
3. Follow step instructions exactly
