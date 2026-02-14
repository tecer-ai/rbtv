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
2. [Highlighted Capabilities](#highlighted-capabilities)
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

## Highlighted Capabilities

### Mentor — Business Innovation Lifecycle

`/bmad-rbtv-mentor`

A YC-style mentor that guides founders through **6 milestones** — from raw idea to MVP. Covers **22+ innovation frameworks** across conception, validation, branding, prototypation, market validation, and MVP. Progress is tracked in a project memo, so you can resume anytime. See [Business Innovation](#business-innovation-founder-mode) below for the full framework breakdown.

### DomCobb — Problem Structuring & Prompting

`/bmad-rbtv-domcobb`

Four modes: **Problem Structuring** (MECE, Pyramid Principle, Problem Trees), **Problem Solving** (routes to BMAD's CIS methodologies), **Prompting Assistance** (craft prompts using **57 knowledge files** covering AI models, prompting techniques, and platforms), and **Add Knowledge** (expand the knowledge base with new model guides or techniques).

### Plan — Structured Planning

`/bmad-rbtv-plan`

Creates self-executing plans using Cursor's native `.plan.md` format with added structure: phased task breakdowns, micro-step task files, companion artifacts (`shape.md`, `learnings.md`), quality gates, and dependency validation. Plans are zero-context executable — any agent can pick one up and run it.

### Doc — Documentation Workflows

`/bmad-rbtv-doc`

Three modes: **Compound** (backlog PRDs from system learnings), **Handoff** (context transfer summaries for agent continuity — plan shaping, execution, or project-level), and **Product** (routes to BMAD for briefs, PRDs, and UX design).

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

RBTV has **15 commands** invoked via `/bmad-rbtv-{name}`. Of these, **12** are also available as **skills** (AI auto-detection in current context) and **cursor sub-agents** (AI delegation in fresh context). The 3 human-only commands — **mentor**, **domcobb**, and **help** — are invoked directly by the user.

Beyond the tools highlighted above, the remaining commands cover: git commits, component creation, context search, design validation, design token extraction, tone extraction, Mermaid diagram conversion, and browser automation.

Run `/bmad-rbtv-help` to explore all 15 commands with detailed usage guidance.

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

## Mobile (Messaging Delivery)

`_mobile/` is the RBTV adapter layer that makes business innovation workflows accessible through Slack (and planned WhatsApp) instead of the Cursor IDE. Same agents, same frameworks, same workflows — delivered through messaging.

Read `_mobile/README.md` for scope and boundaries. Read `_mobile/HOW-IT-WORKS.md` for architecture and design decisions.

---

## Architecture

RBTV follows BMAD micro-file architecture principles:

| Principle | Description |
|-----------|-------------|
| Micro-file design | Each step is self-contained, under 200 lines |
| Just-in-time loading | Only current step in memory |
| Sequential enforcement | Steps execute in numbered order, no skipping |
| State tracking | Progress saved in output document frontmatter |