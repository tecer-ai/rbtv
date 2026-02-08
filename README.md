# RBTV

**Direction before execution.**

AI reasoning is powerful — but execution without direction drifts toward training data patterns, not your specific problem. Training data gives AI the ability to reason; structured direction tells it *what* to execute, *when*, and *how*. That direction comes from putting AI in the right context — through processes, personas, and knowledge files. RBTV provides this for business innovation. BMAD provides it for coding.

RBTV is a BMAD module that bridges the gap between raw ideas and structured execution. It provides:

- **22+ innovation frameworks** that take you from napkin sketch to validated product
- **Structured workflows** for documentation, planning, and quality gates
- **Opinionated agents** that ask hard questions so you make better decisions

The system doesn't make decisions for you. It imposes structure on chaos, challenges your assumptions, and ensures nothing falls through the cracks.

See [get_started.md](./get_started.md) for complete installation instructions.

**Claude Code users:** RBTV is a module that runs inside BMAD, not a standalone repo. A read-only mirror of the parent system is at [_admin/docs/BMAD-mirror/](./_admin/docs/BMAD-mirror/). [CLAUDE.md](./CLAUDE.md) explains how to resolve file paths against this mirror so Claude Code can review and improve RBTV files autonomously. **Note:** CLAUDE.md is intended for Claude to work on the RBTV repo itself (standalone development), not on BMAD instances, and should not be copied to BMAD instances.

---

## Table of Contents

1. [Purpose](#purpose)
2. [Tool Delivery Model](#tool-delivery-model)
3. [Entry Points](#entry-points)
4. [Business Innovation (Founder Mode)](#business-innovation-founder-mode)
5. [Restrictions](#restrictions)
6. [Architecture](#architecture)

---

## Purpose

RBTV provides structured workflows for:

- **Business Innovation** — 22+ frameworks across 6 milestones, from idea to product-market fit
- **Problem Structuring** — Convert vague needs into MECE-structured solutions
- **Documentation** — Compound learnings, context handoffs, product docs
- **Planning** — Create and execute plans with quality gates
- **Git Workflow** — Conventional commits with context-aware messages
- **Design Tooling** — Token extraction, validation, Mermaid rendering
- **Prompting Assistance** — Craft effective prompts using AI model knowledge
- **Web Research** — Rigorous research with source evaluation and citations

---

## Tool Delivery Model

Every RBTV tool is a **command** — a thin loader file that humans invoke via `/command`. A subset of commands are additionally exposed as **skills** and **cursor sub-agents**, making them available to AI agents. The underlying workflow or task is the same; only the invocation mechanism differs.

### Hierarchy

```
Commands (15) ← all tools, available to humans via /command
├── Skills (12) ← subset available for AI auto-detection (in-context)
├── Cursor Sub-agents (12) ← subset available for AI delegation (fresh context)
└── Human-only (3) ← help, mentor, domcobb — no AI entry point
```

### Delivery Mechanisms

| Mechanism | Trigger | Context | Audience |
|-----------|---------|---------|----------|
| **Command** | User types `/command` | Current window | Humans |
| **Skill** | Agent auto-detects relevance | Current window | AI agents |
| **Cursor Sub-agent** | Agent delegates via Task tool | Fresh context (zero prior context) | AI agents |

### Why Three Mechanisms?

1. **Commands** give users direct control — type `/bmad-rbtv-git` to commit
2. **Skills** enable proactive AI assistance — agent sees HTML and auto-applies validation
3. **Cursor sub-agents** provide isolation — research runs in fresh context to avoid pollution

### AI-Available Tools Registry

**Location:** `_bmad/rbtv/_config/tools-manifest.csv` (id, skill_path, cursor_subagent_path, description)

The manifest lists only the 12 tools available to AI agents (skills + cursor sub-agents). Human-only commands (help, mentor, domcobb) are not registered because AI agents do not invoke them.

**Skill:** Read skill_path in current context — no separate invoke API.

**Cursor sub-agent:** Use Task tool with `subagent_type='<id>'` — runs in fresh context. Cursor sub-agents cannot invoke other cursor sub-agents; use skills only when already in a cursor sub-agent.

> **Terminology note:** Files in `.cursor/agents/` are **cursor sub-agents** — thin loaders that make the Cursor sub-agent feature load the desired RBTV workflow or agent. They are NOT RBTV agent personas (which live in `agents/`).

---

## Highlighted Capabilities

Key capabilities from RBTV and BMAD that work together:

### Research Tools

- **[RBTV Web Research](./tasks/web-research.xml)** — Rigorous web research with source evaluation (AT/TR/TM scoring), citation standards, and data integrity rules. Generic, single-shot task.
- **[BMAD Research Workflow](./_admin/docs/BMAD-mirror/_bmad/bmm/workflows/1-analysis/research/)** — Interactive, multi-step research workflow with agent guidance (Mary persona) and domain-specific research types.

### Quality Review Tools

- **[RBTV Quality Review](./tasks/quality-evaluator.xml)** — Binary APPROVED/REJECTED verdict for RBTV component compliance. Validates milestone transitions, step frontmatter, manifest-first compliance, and 5-criteria quality evaluation.
- **[BMAD Editorial Prose Review](./_admin/docs/BMAD-mirror/_bmad/core/tasks/editorial-review-prose.xml)** — Copy editing with 3-column table output (issue/suggestion/location). Advisory, not pass/fail.
- **[BMAD Structural Review](./_admin/docs/BMAD-mirror/_bmad/core/tasks/editorial-review-structure.xml)** — Document reorganization and simplification recommendations.
- **[BMAD Adversarial Review](./_admin/docs/BMAD-mirror/_bmad/core/tasks/review-adversarial-general.xml)** — Cynical, devil's-advocate content criticism for challenging assumptions.

---

## Entry Points

All 15 RBTV tools are commands. 12 of them are also available as skills and cursor sub-agents for AI use.

### Commands (15)

User-invoked commands available via `/bmad-rbtv-{name}`:

| Command | Purpose | AI-available |
|---------|---------|-------------|
| `/bmad-rbtv-help` | List all RBTV commands with deep-dive option | No (human-only) |
| `/bmad-rbtv-mentor` | Business innovation lifecycle (Founder mode) | No (human-only) |
| `/bmad-rbtv-domcobb` | Problem structuring and prompting assistance | No (human-only) |
| `/bmad-rbtv-doc` | Documentation workflows (compound, handoff, product) | Yes |
| `/bmad-rbtv-plan` | Create or execute plans with quality gates | Yes |
| `/bmad-rbtv-git` | Git commit with Conventional Commits format | Yes |
| `/bmad-rbtv-create-component` | Create BMAD components | Yes |
| `/bmad-rbtv-context-search` | Search files for relevant knowledge | Yes |
| `/bmad-rbtv-quality-review` | Evaluate work against quality criteria | Yes |
| `/bmad-rbtv-web-research` | Rigorous web research with citations | Yes |
| `/bmad-rbtv-design-validation` | Validate HTML designs (4-layer framework) | Yes |
| `/bmad-rbtv-visual-design-extraction` | Extract design tokens from screenshots | Yes |
| `/bmad-rbtv-tone-extraction` | Extract voice signature from text | Yes |
| `/bmad-rbtv-mermaid-conversion` | Convert Mermaid diagrams to PNG | Yes |
| `/bmad-rbtv-playwright-browser-automation` | Browser automation with Playwright | Yes |

**Skills (12):** In-context loading layers for AI auto-detection. Available for all commands except the 3 human-only entry points.
**Cursor sub-agents (12):** Fresh-context delegation layers for AI task isolation. Same 12 tools as skills. Registered in `tools-manifest.csv`.

---

## Business Innovation (Founder Mode)

**Command:** `/bmad-rbtv-mentor`

A YC mentor who guides you through **22+ innovation frameworks** across 6 milestones, from idea to product-market fit.

### Milestones Overview

| Milestone | Focus | Status |
|-----------|-------|--------|
| **M1** Conception | Define problem, customer, solution hypothesis | Complete |
| **M2** Validation | Test assumptions, size market, model economics | Complete |
| **M3** Brand | Define identity, positioning, voice | Complete |
| **M4** Prototypation | Build and test early versions | Complete |
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

### M4: Prototypation Frameworks (4 available)

| Framework | Purpose | Output |
|-----------|---------|--------|
| **User Flow & IA** | Entry points, screens, content hierarchy | User flow map, IA structure |
| **Design Direction** | Visual design via BMAD bridge | Design spec, design brief |
| **Conversion-Centered Design** | Apply CCD principles to prototype | Conversion-focused design |
| **Heuristic Evaluation** | Usability evaluation | Critical/Major issues resolved |

*Build Prototype and Testing Prep frameworks are planned.*

### How It Works

1. Run `/bmad-rbtv-mentor` and select `[BI] Business Innovation`
2. The mentor guides you through frameworks sequentially
3. Each framework saves artifacts to your output folder
4. Progress tracked in project memo — resume anytime
5. Complete milestones unlock next phase

---

## Restrictions

### Project-specific output paths require Mentor and project-memo

**Project name** (`{project-name}`) is only set when the user runs **Mentor → New Project → Step 01: Project Setup** and provides a project name. That value is stored in **project-memo.md** frontmatter as `projectName`. Mentor and BI workflows read it from there (or from context) to build paths like `_bmad-output/{project-name}/founder/...`.

**If the user does not use Mentor (or any BI flow that loads project-memo) and does not reference project-memo:**

- **Business Innovation workflows** have no project name to plug into paths; project-specific output locations are undefined.
- **BMAD** (bmm) config uses `{project-name}` in `planning_artifacts` and `implementation_artifacts`; nothing resolves it unless RBTV passes a full path via update-bmad-config when delegating.
- **Other RBTV workflows** (plan, doc, git, etc.) use the base `output_folder` from config (`_bmad-output`), so they write to the root output folder — no project subfolder.

To get project-scoped paths (e.g. `_bmad-output/MyProject/founder/`), use Mentor to create a project and maintain project-memo in context.

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
├── readme.md                # This document
├── get_started.md           # Installation and onboarding guide
├── CLAUDE.md                # Claude Code path resolution and autonomous work guide
├── _config/                 # IDE configuration and tools
│   ├── .cursor/             # Cursor IDE config (agents, commands, skills, rules)
│   ├── .vscode/             # VS Code settings
│   ├── config.yaml          # Module configuration
│   ├── install-rbtv.py      # IDE config sync script
│   └── tools-manifest.csv   # Tool catalog (skills & subagents)
├── agents/                  # Agent personas
│   ├── ana.md               # Documentation Orchestrator
│   ├── god.md               # BMAD Component Builder
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
│   ├── commands/            # Command files — human entry points (bmad-rbtv-*.md)
│   ├── agents/              # Cursor sub-agent files — AI delegation entry points (bmad-rbtv-*.md)
│   ├── skills/              # Skill folders — AI auto-detection entry points (bmad-rbtv-*/SKILL.md)
│   └── rules/               # RBTV-specific rules (bmad-rbtv-*.mdc)
├── .claude/                 # Claude IDE configuration
│   └── commands/            # Command files (mirrors .cursor)
└── .rbtv-docs/              # Internal documentation
```

---