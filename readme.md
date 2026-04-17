# RBTV

**Direction before execution.**

AI reasoning is powerful — but execution without direction drifts toward training data patterns, not your specific problem. Training data gives AI the ability to reason; structured direction tells it *what* to execute, *when*, and *how*. That direction comes from putting AI in the right context — through processes, personas, and knowledge files. RBTV provides this for business innovation. BMAD provides it for coding.

RBTV is a BMAD module that bridges the gap between raw ideas and structured execution. It provides:

- **22+ innovation frameworks** that take you from napkin sketch to validated product
- **Structured workflows** for documentation, planning, and quality gates
- **Opinionated agents** that ask hard questions so you make better decisions

The system doesn't make decisions for you. It imposes structure on chaos, challenges your assumptions, and ensures nothing falls through the cracks.

---

## Table of Contents

1. [Installation](#installation)
2. [Main Commands](#main-commands)
3. [Auxiliary Commands](#auxiliary-commands)
4. [Business Innovation Milestones](#business-innovation-milestones)
5. [IDE Notes](#ide-notes)

---

## Installation

RBTV runs inside [BMAD](https://github.com/bmadcode/BMAD-METHOD). Install BMAD first, then add RBTV.

### 1. Install BMAD

Follow the [BMAD installation guide](https://github.com/bmadcode/BMAD-METHOD#installation) to set up a BMAD project. You need:

- A project with BMAD installed at `{project-root}/_bmad/`
- Python 3 (standard library only — no extra packages)

### 2. Add RBTV

Clone or copy the RBTV module into your BMAD project:

```
{project-root}/_bmad/rbtv/
```

### 3. Run the installer

```bash
python _bmad/rbtv/_config/bootstrap.py
```

The installer copies commands, agents, skills, and rules to your project's `.cursor/` and `.claude/` directories, merges MCP config, and registers RBTV in the BMAD help catalog.

Re-run after every `git pull` to pick up new commands and configuration changes. The script is idempotent.

---

## Main Commands

These are the primary entry points you'll use directly. All commands are invoked via `/{name}` in Cursor.

### Mentor — Business Innovation Lifecycle

`/mentor`

A YC-style mentor that guides founders through **6 milestones** — from raw idea to MVP. Covers **22+ innovation frameworks** across conception, validation, branding, prototypation, market validation, and MVP. Progress is tracked in a project memo, so you can resume anytime. See [Business Innovation Milestones](#business-innovation-milestones) below for the full framework breakdown.

**How it works:**

1. Run `/mentor` and select `[BI] Business Innovation`
2. The mentor guides you through frameworks sequentially
3. Each framework saves artifacts to your output folder
4. Progress tracked in project memo — resume anytime
5. Complete milestones unlock next phase

### DomCobb — Problem Structuring & Prompting

`/domcobb`

Four modes: **Problem Structuring** (MECE, Pyramid Principle, Problem Trees), **Problem Solving** (routes to BMAD's CIS methodologies), **Prompting Assistance** (craft prompts using **57 knowledge files** covering AI models, prompting techniques, and platforms), and **Add Knowledge** (expand the knowledge base with new model guides or techniques).

### Plan — Structured Planning

`/planning`

Creates self-executing plans using Cursor's native `.plan.md` format with added structure: phased task breakdowns, micro-step task files, companion artifacts (`shape.md`, `learnings.md`), quality gates, and dependency validation. Plans are zero-context executable — any agent can pick one up and run it.

### Pitch Creation — Investor & Client Decks

`/investor-pitch` · `/client-pitch`

Builds pitch decks through narrative-first stress-testing. The agent sits on the *other side of the table* — as the investor or the buyer — and challenges every claim before building the deck. The workflow covers narrative development, data validation, research prompting, slide structure, HTML generation, and image prompt creation across 9 steps.

---

## Auxiliary Commands

### Doc — Documentation Workflows

`/doc`

Three modes: **Compound** (backlog PRDs from system learnings), **Handoff** (context transfer summaries for agent continuity — plan shaping, execution, or project-level), and **Product** (routes to BMAD for briefs, PRDs, and UX design).

### Help — Command Explorer

`/help`

Lists all RBTV commands with descriptions and lets you deep-dive into any command to understand its workflows, agents, and outputs.

### Other Tools

| Command | What it does |
|---------|-------------|
| `/quality-review` | Binary APPROVED/REJECTED verdict for deliverable quality |
| `/designer` | Visual design for pitch decks and brand identity |
| `/create-component` | Create new BMAD components (agents, workflows, tasks) |
| `/design-extraction` | Extract design tokens from website screenshots |
| `/tone-extraction` | Extract voice signatures from text samples |

Most commands are also available as **skills** (AI auto-detects when relevant) and **Cursor sub-agents** (AI delegates in fresh context).

---

## Business Innovation Milestones

**Command:** `/mentor`

A YC mentor who guides you through **22+ innovation frameworks** across 6 milestones, from idea to product-market fit.

### Milestones Overview

| Milestone | Focus | Status |
|-----------|-------|--------|
| **M1** Conception | Define problem, customer, solution hypothesis | Available |
| **M2** Validation | Test assumptions, size market, model economics | Available |
| **M3** Brand | Define identity, positioning, voice | Available |
| **M4** Prototypation | Build and test early versions | WIP |
| **M5** Market Validation | Prove demand with real sales | WIP |
| **M6** MVP | Build minimum viable product | WIP |

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

### M5: Market Validation — WIP

Frameworks for validating market demand, pricing, and sales channels. In development.

### M6: MVP — WIP

Frameworks for building and shipping a minimum viable product. In development.

---

## IDE Notes

**Cursor** is the primary IDE. All commands, agents, skills, and rules are installed to `.cursor/` by the installer.

**Claude Code** is also supported. The installer replicates commands and rules to `.claude/` with format conversion. See [CLAUDE.md](./CLAUDE.md) for path resolution details. Note: `CLAUDE.md` is intended for working on the RBTV repo itself (standalone development), not for BMAD instances.

Run `/help` to explore all commands with detailed usage guidance.
