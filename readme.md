# RBTV

**Direction before execution.**

AI reasoning is powerful — but execution without direction drifts toward training data patterns, not your specific problem. Training data gives AI the ability to reason; structured direction tells it *what* to execute, *when*, and *how*. That direction comes from putting AI in the right context — through processes, personas, and knowledge files. RBTV provides this for business innovation. BMAD provides it for coding.

RBTV is a BMAD module that bridges the gap between raw ideas and structured execution. It provides:

- **22+ innovation frameworks** that take you from napkin sketch to validated product
- **Structured workflows** for documentation, planning, and quality gates
- **Opinionated agents** that ask hard questions so you make better decisions

The system doesn't make decisions for you. It imposes structure on chaos, challenges your assumptions, and ensures nothing falls through the cracks.

See [get_started.md](./get_started.md) for complete installation instructions.

**Claude Code users:** RBTV is a module that runs inside BMAD, not a standalone repo. A read-only mirror of the parent system is at [_docs/system-documentation/BMAD/](./_docs/system-documentation/BMAD/). [CLAUDE.md](./CLAUDE.md) explains how to resolve file paths against this mirror so Claude Code can review and improve RBTV files autonomously.

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

- Most tools (e.g., `web-research`) have command, skill, AND subagent entry points
- All entry points for a tool point to the same underlying workflow or task
- Some commands are human-only entry points with no skill or subagent (e.g., `help`, `mentor`, `domcobb`)
- The manifest (`tools-manifest.csv`) registers all skills and subagents
- Adding a new tool = create workflow/task + register entry points

### Manifest and Invocation

**Location:** `_bmad/rbtv/_config/tools-manifest.csv` (id, skill_path, subagent_path, description)

**Skill:** Read skill_path in current context — no separate invoke API.

**Subagent:** Use Task tool with `subagent_type='<id>'` — runs in fresh context. Subagents cannot invoke other subagents; use skills only when already in subagent.

---

## Entry Points

RBTV tools are available through up to three delivery mechanisms: **Commands** (user-invoked), **Skills** (agent auto-detected), and **Subagents** (agent-delegated with fresh context). Most tools have all three entry points; some commands are human-only.

### Commands (15)

User-invoked commands available via `/bmad-rbtv-{name}`:

| Command | Purpose | Skill/Subagent |
|---------|---------|----------------|
| `/bmad-rbtv-help` | List all RBTV commands with deep-dive option | Human-only |
| `/bmad-rbtv-mentor` | Business innovation lifecycle (Founder mode) | Human-only |
| `/bmad-rbtv-domcobb` | Problem structuring and prompting assistance | Human-only |
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

**Skills (12):** Thin loading layers for agent auto-detection. Available for all commands except the 3 human-only entry points (help, mentor, domcobb).
**Subagents (12):** Thin loading layers for agent delegation with fresh context. Same 12 tools as skills.

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
│   ├── commands/            # Command files (bmad-rbtv-*.md)
│   ├── agents/              # Subagent files (bmad-rbtv-*.md)
│   ├── skills/              # Skill folders (bmad-rbtv-*/SKILL.md)
│   └── rules/               # RBTV-specific rules (bmad-rbtv-*.mdc)
├── .claude/                 # Claude IDE configuration
│   └── commands/            # Command files (mirrors .cursor)
└── .rbtv-docs/              # Internal documentation
```

---