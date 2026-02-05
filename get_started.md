# RBTV — Getting Started

Welcome to **RBTV** (Robotville), a BMAD module for business innovation, documentation, planning, and developer workflows.

---

## Prerequisites

RBTV requires the following BMAD modules installed:

| Module | Purpose | Required |
|--------|---------|----------|
| **core** | Workflow engine, config, brainstorming | Yes |
| **cis** | Problem-solving methodologies (used by domcobb) | Yes |
| **bmm** | Product documentation workflows (Brief, PRD, UX) | Yes |

Install BMAD with these modules before proceeding: [BMAD GitHub Repository](https://github.com/bmadcode/BMAD-METHOD)

---

## Installation

### Step 1: Clone RBTV

Navigate to your BMAD `_bmad/` folder and clone RBTV:

```bash
cd path/to/your/project/BMAD-METHOD/_bmad
git clone https://github.com/bmadcode/rbtv.git rbtv
```

### Step 2: Run the Installation Script

RBTV includes IDE configuration files (`.cursor/` and `.claude/`) that must be merged with BMAD's configuration. Run the installation script:

```bash
cd rbtv
python install-rbtv.py
```

**What the script does:**
- Moves `rbtv/.cursor/` contents → `_bmad/.cursor/`
- Moves `rbtv/.claude/` contents → `_bmad/.claude/`
- Overwrites existing files if conflicts occur

> **Important:** Run this script every time you update RBTV (`git pull` or `git fetch`). The script moves (not copies) the folders, so they won't exist in `rbtv/` until the next update.

### Step 3: Open Your IDE

Open Cursor (or Claude) in your BMAD project root folder (the parent of `_bmad/`).

---

## Quick Start

Run the help command to see available RBTV commands:

```
/bmad-rbtv-help
```

This shows all RBTV commands with the option to deep-dive into any command to understand its workflows and modes.

---

## Core Components

### Founder Mode — The Star of RBTV

**Command:** `/bmad-rbtv-mentor`

A YC mentor who guides you through **17 innovation frameworks**, from idea to product-market fit.

The Founder workflow spans 6 milestones:

| Milestone | Focus | Frameworks |
|-----------|-------|------------|
| **M1** Conception | Define problem, customer, solution | Lean Canvas, Five Whys, JTBD, Competitive Landscape, Problem-Solution Fit, Working Backwards |
| **M2** Validation | Test assumptions, size market | Assumption Mapping, Leap of Faith, Pre-mortem, TAM-SAM-SOM, TRL, Unit Economics |
| **M3** Brand | Define identity and positioning | Brand Archetypes, Brand Prism, Brand Positioning, Golden Circle, Tone of Voice |
| **M4** Prototypation | Build and test early versions | *(In development)* |
| **M5** Market Validation | Prove demand with real sales | *(In development)* |
| **M6** MVP | Build minimum viable product | *(In development)* |

**How to work with Founder:**
1. Start with `/bmad-rbtv-bi` and select `[BI] Business Innovation`
2. The mentor guides you through frameworks sequentially
3. Each framework produces artifacts saved to your output folder
4. Resume anytime — progress is tracked in your project memo

---

### Supporting Commands

| Command | Purpose | Note |
|---------|---------|------|
| `/bmad-rbtv-domcobb` | Problem structuring (MECE, Pyramid) and prompting assistance | Routes to CIS for problem-solving |
| `/bmad-rbtv-doc` | Documentation: compound learnings, context handoffs, product docs | |
| `/bmad-rbtv-plan` | Create and execute structured plans with quality gates | **Do not start in Plan mode** — use Agent mode |
| `/bmad-rbtv-git` | Conventional commits with context-aware messages | |

**Other tools:** design validation, token extraction, Mermaid diagrams, browser automation, web research, tone extraction.

---

## Tool Delivery Mechanisms

RBTV tools are available through three mechanisms:

| Mechanism | Trigger | Context |
|-----------|---------|---------|
| **Commands** | User types `/command` | Maintains current context window |
| **Skills** | Agent auto-detects relevance | Maintains current context window |
| **Subagents** | Agent delegates via Task tool | Fresh context window |

All three share the same underlying workflows — the difference is how they're invoked and whether they preserve context.

> **Deep dive:** See the [RBTV README](./readme.md) for full architectural details.

---

## BMAD Integration

RBTV is one module in the BMAD ecosystem. Access the full BMAD help system:

```
/bmad-help
```

This shows all installed modules and their workflows, helps you navigate between phases, and recommends next steps based on your progress.

---

## Updating RBTV

When you update RBTV:

```bash
cd _bmad/rbtv
git pull
python install-rbtv.py
```

The installation script must run after every update to sync IDE configuration files.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Commands not appearing | Run `install-rbtv.py` and restart your IDE |
| "Module not found" errors | Ensure core and cis modules are installed |
| Workflows fail to load | Check `_bmad/core/config.yaml` exists and is valid |

---

*Built with the BMAD Method — structure reveals solutions.*
