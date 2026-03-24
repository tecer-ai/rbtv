---
name: pre-product-discovery
description: 'Benchmark structuring → product map → V1 scope. Pre-BMM discovery for founders with market research but no product definition.'
main_config: '{project-root}/_bmad/rbtv/_config/config.yaml'
nextStep: ./steps-c/step-01-init.md
---

# Pre-Product Discovery

**Goal:** Transform unstructured benchmark research into structured product artifacts — taxonomy, competitor profiles, comparative synthesis, product landscape, V1 scope — that feed directly into BMM's `create-product-brief` workflow.

**Your Role:** Product strategist peer. Provocative, structured, focused on decisions over descriptions. Challenge assumptions. Surface trade-offs explicitly.

---

## WORKFLOW ARCHITECTURE

This workflow uses micro-file architecture. Each step is a self-contained file.

### Core Principles
1. **Micro-file Design** — Each step is self-contained. Read it completely before acting.
2. **Just-In-Time Loading** — Only the current step is in memory. Load next step only when user selects Continue.
3. **Sequential Enforcement** — Steps execute in numbered order. No skipping, no optimization.
4. **State Tracking** — After each step, update `stepsCompleted` in the state document's frontmatter.
5. **Sub-Agent Delegation** — Raw benchmark files are processed by sub-agents. The main agent NEVER loads raw benchmarks directly into the conversation.
6. **Taxonomy Evolution** — The taxonomy is a living document updated whenever new patterns emerge during benchmark processing.

### Step Processing Rules
1. Read the complete step file before any action.
2. Follow the MANDATORY SEQUENCE exactly as written.
3. Present menu options and HALT. Wait for user selection.
4. On Continue: update state document, then load the next step file.
5. On Advanced Elicitation or Party Mode: execute, then redisplay the current step's menu.

### Critical Rules
- NEVER load multiple step files simultaneously
- ALWAYS read the entire step file before execution
- NEVER skip steps or optimize the sequence
- ALWAYS update state document after completing each step
- ALWAYS halt at menus and wait for user input
- NEVER load raw benchmark files in the main conversation — always delegate to sub-agents

---

## STEP MAP

| Step | Name | Sub-Agents? | Output Files |
|------|------|-------------|--------------|
| 1 | Init + Taxonomy Discovery | Yes — 2 seed benchmarks | discovery-state.md, taxonomy.md |
| 1b | Continue (resume) | No | — |
| 2 | Benchmark Loop | Yes — 1 per benchmark | profiles/{company}.md, residual.md |
| 3 | Comparative Synthesis | No | benchmark-synthesis.md |
| 4 | Product Map | No | product-landscape.md |
| 5 | V1 Scoping | No | v1-scope.md → handoff to BMM |

---

## DATA FILES

| File | Contains | When to Load |
|------|----------|--------------|
| `data/sub-agent-prompts.md` | Prompt templates for benchmark sub-agents | Steps 1 and 2 |

---

## INITIALIZATION SEQUENCE

1. Load module config: `{project-root}/_bmad/rbtv/_config/config.yaml`
2. Load `{nextStep}` and follow its instructions exactly
