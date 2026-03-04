# Founder Module

This directory contains the complete founder module system for taking ideas from concept to MVP through 6 structured milestones.

## What Is This Folder?

The founder module is a structured journey guiding users through **6 milestones** to transform raw ideas into launch-ready MVPs. Each milestone uses proven business frameworks and creates comprehensive documentation.

## Quick Start

**For users:**
- Read [get_started.md](get_started.md) for quick-start guide
- Invoke `/bmad-rbtv-mentor` (Business Innovation command) or `@mentor` (agent) to begin working through milestones

**For AI agents:**
- Read [founder_process.md](founder_process.md) for complete milestone documentation, including the **Agent Handoff Protocol**
- Read [get_started.md](get_started.md) for user workflow overview

## How Multi-Agent Execution Works

The founder module is built for **multi-agent execution with zero shared memory**. All context between agents passes through files:

| File | Role |
|------|------|
| `[project]_memo.md` | **Evolving narrative** — what is this project about |
| `m[x]_founder_diary.md` | **Operational state & strategic context** — where are we, what was done, what is next, and why the project is in this state |

See the **Agent Handoff Protocol** in [founder_process.md](founder_process.md) for the step-by-step protocol agents follow when starting and ending sessions.

## Folder Structure

| Folder | Purpose |
|--------|---------|
| `m1_conception/` | Milestone 1 frameworks (Working Backwards, JTBD, Competitive Landscape, Problem-Solution Fit, Lean Canvas, 5 Whys) |
| `m2_validation/` | Milestone 2 frameworks (Leap of Faith, Assumption Mapping, TAM/SAM/SOM, Unit Economics, TRL, Pre-mortem) |
| `m3_brand/` | Milestone 3 frameworks (Brand Archetypes, Brand Prism, Golden Circle, Positioning Statement, Messaging Architecture, Tone of Voice) |
| `m4_prototypation/` | Milestone 4 process and frameworks (User Flow Mapping, Information Architecture, Design Brief, Atomic Design, Conversion-Centered Design, WCAG, Heuristic Evaluation, Landing Page, Infographic, Design Tokens) |
| `m5_market_validation/` | Milestone 5 process and frameworks (Mom Test, SPIN Selling, Smoke Test, Van Westendorp, Bullseye, Sean Ellis) |
| `m6_mvp/` | Milestone 6 process and templates (User Story Map, MoSCoW, Architecture, Feature Docs, QA, Launch) |

**Note:** M1, M4, M5, M6 are live. M2 and M3 are in development.

## Key Files

| File | Purpose | Audience |
|------|---------|----------|
| [founder_process.md](founder_process.md) | Master navigation: milestones, glossary, folder structure, framework candidates | AI agents, advanced users |
| [get_started.md](get_started.md) | Quick-start guide for the founder module | New users |
| [mentor.md](agents/paul.md) | Mentor agent system prompt | AI agents |
| [lavoisier.md](agents/lavoisier.md) | Design direction agent system prompt | AI agents |

## How Users Work Through the Module

1. User invokes `/bmad-rbtv-mentor` or `@mentor` with their project idea — or `@mentor @m[x]_founder_diary.md` to resume a project
2. Mentor reads the founder diary first (session entry point); if none exists, creates new project and starts M1
3. Mentor guides through milestones using structured Acts: Process Contextualization, Framework Execution, Synthesis, Session Close
4. Mentor asks 2–3 questions per batch, writes documentation incrementally, and logs diary-worthy events (decisions, pivots, blockers, learnings)
5. User must log out with mentor before leaving so Session Status and project documents are updated
6. Each milestone creates a folder in `[project]/docs/founder/` with applied frameworks; the founder diary tracks status, file map, framework progress, and decisions

## Where User Projects Live

In the brownfield installation, each project is an independent git repository. Founder outputs live inside the project's `docs/founder/` directory:

```
[project]/docs/founder/
├── [project]_memo.md               # Amazon-style narrative memo
├── conception/
│   ├── m1_founder_diary.md         # Session tracking + decisions
│   ├── working_backwards.md        # Applied framework
│   └── ...
└── ... (one folder per milestone)
```

See [project-structure.mdc](../../.cursor/rules/documentation/project-structure.mdc) for complete project structure standards.

---