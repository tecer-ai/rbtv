# RBTV

**The strategic layer AI tools don't provide.**

AI executors like Cursor and Claude are powerful — but execution without direction produces technically correct outputs that miss the bigger picture. Before you build, you need to know *what* you're building and *why*. That's the work AI can't do for you — but it can guide you through it.

RBTV is a BMAD module that bridges the gap between raw ideas and structured execution. It provides:

- **17 innovation frameworks** that take you from napkin sketch to validated product
- **Structured workflows** for documentation, planning, and quality gates
- **Opinionated agents** that ask hard questions so you make better decisions

The system doesn't make decisions for you. It imposes structure on chaos, challenges your assumptions, and ensures nothing falls through the cracks.

See [GET_STARTED.md](./GET_STARTED.md) for complete installation instructions.

---

## Table of Contents

1. [Purpose](#purpose)
2. [Tool Delivery Model](#tool-delivery-model)
3. [Entry Points](#entry-points)
4. [Business Innovation (Founder Mode)](#business-innovation-founder-mode)
5. [Architecture](#architecture)

---

## Purpose

RBTV provides structured workflows for:

- **Business Innovation** — 17 frameworks across 6 milestones, from idea to product-market fit
- **Problem Structuring** — Convert vague needs into MECE-structured solutions
- **Documentation** — Compound learnings, context handoffs, product docs
- **Planning** — Create and execute plans with quality gates
- **Git Workflow** — Conventional commits with context-aware messages
- **Design Tooling** — Token extraction, validation, Mermaid rendering
- **Prompting Assistance** — Craft effective prompts using AI model knowledge
- **Web Research** — Rigorous research with source evaluation and citations

---

## Tool Delivery Model

Commands, skills, and subagents are **the same underlying tools** — workflows and tasks that perform specific functions. The difference is purely in **how they are invoked** and **whether they preserve context**.

### Delivery Mechanisms

| Mechanism | Trigger | Context | Use Case |
|-----------|---------|---------|----------|
| **Command** | User types `/command` | Maintains current window | User explicitly requests a tool |
| **Skill** | Agent auto-detects relevance | Maintains current window | Agent recognizes task matches skill |
| **Subagent** | Agent delegates via Task tool | Fresh context window | Complex task needing isolation |

### Why Three Mechanisms?

1. **Commands** give users direct control — type `/bmad-rbtv-git` to commit
2. **Skills** enable proactive assistance — agent sees HTML and auto-applies validation
3. **Subagents** provide isolation — research runs in fresh context to avoid pollution

### Implications

- A single tool (e.g., `web-research`) can have command, skill, AND subagent entry points
- All three point to the same underlying workflow or task
- The manifest (`rbtv-manifest.csv`) registers all entry points
- Adding a new tool = create workflow/task + register entry points

---

## Entry Points

All RBTV tools are available through three delivery mechanisms: **Commands** (user-invoked), **Skills** (agent auto-detected), and **Subagents** (agent-delegated with fresh context). All three mechanisms are thin loading layers that point to the same underlying workflows and tasks.

### Commands (15)

User-invoked commands available via `/bmad-rbtv-{name}`:

| Command | Purpose |
|---------|---------|
| `/bmad-rbtv-help` | List all RBTV commands with deep-dive option |
| `/bmad-rbtv-mentor` | Business innovation lifecycle (Founder mode) |
| `/bmad-rbtv-doc` | Documentation workflows (compound, handoff, product) |
| `/bmad-rbtv-domcobb` | Problem structuring and prompting assistance |
| `/bmad-rbtv-plan` | Create or execute plans with quality gates |
| `/bmad-rbtv-git` | Git commit with Conventional Commits format |
| `/bmad-rbtv-create-component` | Create BMAD components |
| `/bmad-rbtv-context-search` | Search files for relevant knowledge |
| `/bmad-rbtv-quality-review` | Evaluate work against quality criteria |
| `/bmad-rbtv-web-research` | Rigorous web research with citations |
| `/bmad-rbtv-design-validation` | Validate HTML designs (4-layer framework) |
| `/bmad-rbtv-visual-design-extraction` | Extract design tokens from screenshots |
| `/bmad-rbtv-tone-extraction` | Extract voice signature from text |
| `/bmad-rbtv-mermaid-conversion` | Convert Mermaid diagrams to PNG |
| `/bmad-rbtv-playwright-browser-automation` | Browser automation with Playwright |


**Skills:** Mirror all 15 commands as thin loading layers. Agents auto-detect when to apply them based on task context.
**Subagents:** Mirror all 15 commands as thin loading layers. Agents delegate to them when tasks need isolation in fresh context windows.

---

## Business Innovation (Founder Mode)

**Command:** `/bmad-rbtv-mentor`

A YC mentor who guides you through **17 innovation frameworks** across 6 milestones, from idea to product-market fit.

### Milestones Overview

| Milestone | Focus | Status |
|-----------|-------|--------|
| **M1** Conception | Define problem, customer, solution hypothesis | Complete |
| **M2** Validation | Test assumptions, size market, model economics | Complete |
| **M3** Brand | Define identity, positioning, voice | Complete |
| **M4** Prototypation | Build and test early versions | In Development |
| **M5** Market Validation | Prove demand with real sales | In Development |
| **M6** MVP | Build minimum viable product | In Development |

### M1: Conception Frameworks (6)

| Framework | Purpose | Output |
|-----------|---------|--------|
| **Lean Canvas** | One-page business model | 9-block canvas |
| **Five Whys** | Root cause analysis | Problem tree |
| **Jobs to Be Done** | Customer motivation discovery | Job stories |
| **Competitive Landscape** | Market positioning analysis | Competitor matrix |
| **Problem-Solution Fit** | Validate solution direction | Fit assessment |
| **Working Backwards** | Amazon-style press release | PR/FAQ document |

### M2: Validation Frameworks (6)

| Framework | Purpose | Output |
|-----------|---------|--------|
| **Assumption Mapping** | Identify and prioritize assumptions | Risk matrix |
| **Leap of Faith** | Critical assumption testing | Test plan |
| **Pre-mortem** | Failure scenario planning | Mitigation strategies |
| **TAM-SAM-SOM** | Market sizing | Market size estimates |
| **Technology Readiness Level** | Technical maturity assessment | TRL score + gaps |
| **Unit Economics** | Revenue model validation | CAC, LTV, payback |

### M3: Brand Frameworks (5)

| Framework | Purpose | Output |
|-----------|---------|--------|
| **Brand Archetypes** | Personality definition | Archetype profile |
| **Brand Prism** | Identity structure | 6-facet prism |
| **Brand Positioning** | Market differentiation | Positioning statement |
| **Golden Circle** | Why/How/What articulation | Purpose statement |
| **Tone of Voice** | Communication style | Voice guidelines |

### How It Works

1. Run `/bmad-rbtv-mentor` and select `[BI] Business Innovation`
2. The mentor guides you through frameworks sequentially
3. Each framework saves artifacts to your output folder
4. Progress tracked in project memo — resume anytime
5. Complete milestones unlock next phase

---
## Architecture

RBTV follows BMAD micro-file architecture principles:

| Principle | Description |
|-----------|-------------|
| Micro-file design | Each step is self-contained, under 200 lines |
| Just-in-time loading | Only current step in memory |
| Sequential enforcement | Steps execute in numbered order, no skipping |
| State tracking | Progress saved in output document frontmatter |

### Folder Structure

```
rbtv/
├── GET_STARTED.md           # Installation and onboarding guide
├── install-rbtv.py          # IDE config sync script
├── rbtv-manifest.csv        # Component registry
├── agents/                  # Agent personas
│   ├── ana.md               # Documentation Orchestrator
│   ├── component-creator.md # BMAD Component Builder
│   ├── domcobb.md           # Problem Architect & Prompting Expert
│   └── mentor.md            # YC Mentor for Business Innovation
├── tasks/                   # Standalone procedures
│   ├── context-search.xml
│   ├── quality-evaluator.xml
│   ├── tone-extraction.xml
│   ├── web-research.xml
│   └── data/                # Task knowledge files
├── workflows/
│   ├── bi-business-innovation/  # Founder mode orchestrator
│   ├── bi-m1/                   # M1: Conception milestone
│   ├── bi-m1-lean-canvas/
│   ├── bi-m1-five-whys/
│   ├── bi-m1-jobs-to-be-done/
│   ├── bi-m1-competitive-landscape/
│   ├── bi-m1-problem-solution-fit/
│   ├── bi-m1-working-backwards/
│   ├── bi-m2/                   # M2: Validation milestone
│   ├── bi-m2-assumption-mapping/
│   ├── bi-m2-leap-of-faith/
│   ├── bi-m2-pre-mortem/
│   ├── bi-m2-tam-sam-som/
│   ├── bi-m2-technology-readiness-level/
│   ├── bi-m2-unit-economics/
│   ├── bi-m3/                   # M3: Brand milestone
│   ├── bi-m3-brand-archetypes/
│   ├── bi-m3-brand-prism/
│   ├── bi-m3-brand-positioning/
│   ├── bi-m3-golden-circle/
│   ├── bi-m3-tone-of-voice/
│   ├── doc-compound-learning/
│   ├── doc-context-handoff/
│   ├── plan-lifecycle/
│   ├── git-commit/
│   ├── browser-web-automation/
│   ├── design-qa-validation/
│   ├── design-token-extraction/
│   ├── diagram-mermaid-render/
│   ├── problem-structuring/
│   ├── prompting-assistance/
│   └── build-rbtv-component/
├── .cursor/                 # Cursor IDE configuration
│   ├── commands/rbtv/       # Command files
│   ├── agents/rbtv/         # Subagent files
│   └── skills/rbtv/         # Skill files
├── .claude/                 # Claude IDE configuration
│   └── commands/rbtv/       # Command files (mirrors .cursor)
└── .rbtv-docs/              # Internal documentation
```

---