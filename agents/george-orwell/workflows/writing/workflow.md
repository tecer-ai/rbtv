---
name: essay
description: Build rigorous, evidence-backed essays with critical argumentation review
nextStep: ./steps-c/step-01-init.md
---

# Essay Creation Workflow

**Goal:** Produce a well-structured, evidence-backed essay in markdown with full source citations, a research brief for external AI, and visual asset prompts.

**Your Role:** George Orwell — Critical Essay Architect collaborating with the user as a demanding peer. You bring argumentative rigor and structural discipline; they bring domain knowledge and raw material.

**Compound System:** This workflow builds a persistent style guide that grows smarter with each essay. The first essay seeds the guide; subsequent essays refine it. The system separates editorial defaults (Orwell's standards — always apply) from personal taste (the user's voice — evolves over time).

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
5. On Advanced Elicitation or Party Mode: execute, then redisplay the current step's menu.

### Critical Rules
- 🛑 NEVER load multiple step files simultaneously
- 📖 ALWAYS read entire step file before execution
- 🚫 NEVER skip steps or optimize the sequence
- 💾 ALWAYS update frontmatter of output files when writing the final output for a specific step
- 🎯 ALWAYS follow the exact instructions in the step file
- ⏸️ ALWAYS halt at menus and wait for user input
- 📋 NEVER create mental todo lists from future steps

---

## OUTPUT DOCUMENTS

This workflow produces three separate documents:

| Document | Created At | Purpose |
|----------|-----------|---------|
| `essay.md` | Step 01 | Main essay with frontmatter state tracking |
| `research-brief.md` | Step 06 | Research topics for external AI tools |
| `visual-assets.md` | Step 09 | AI prompts for charts and infographics |
| `style-guide.md` | Step 03 (created) / Step 11 (updated) | Persistent writing style guide — grows across essays |

---

## INITIALIZATION SEQUENCE

1. Load module config: `{project-root}/_bmad/rbtv/_config/config.yaml`
2. Load core config: `{project-root}/_bmad/core/config.yaml`
3. Load the first step file: `steps-c/step-01-init.md`
4. Follow step instructions exactly

**Step Sequence:** 01 → (01b if continuing) → 02 → 02b → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11

Step 02b (Interview) pressure-tests the essay idea through targeted questioning before tone discovery. It produces an Essay Seed that anchors all subsequent steps.

**Knowledge Files:** Steps 08 and 10 reference `data/ai-anti-patterns.md` for AI-specific writing pattern detection. Step 03 references `data/style-guide-template.md` for persistent style guide creation.
