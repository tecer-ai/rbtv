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

RBTV includes IDE configuration files (`.cursor/`) that must be merged with BMAD's configuration. Run the installation script:

```bash
cd rbtv
python install-rbtv.py
```

**What the script does:**
- Moves `rbtv/.cursor/` contents → `_bmad/.cursor/`
- Creates `_bmad/.claude/commands/` and replicates Cursor commands for Claude compatibility
- Overwrites existing files if conflicts occur

> **Important:** Run this script every time you update RBTV (`git pull` or `git fetch`). The script moves (not copies) the `.cursor/` folder, so it won't exist in `rbtv/` until the next update.

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

## Tool Delivery Mechanisms

RBTV tools are available through three mechanisms:

| Mechanism | Trigger | Context |
|-----------|---------|---------|
| **Commands** | User types `/command` | Maintains current context window |
| **Skills** | Agent auto-detects relevance | Maintains current context window |
| **Subagents** | Agent delegates via Task tool | Fresh context window |

All three share the same underlying workflows — the difference is how they're invoked and whether they preserve context.

**All 15 RBTV commands are mirrored as both Skills and Subagents** — thin loading layers that allow agents to access the same tools either within the current context (skills) or in isolated contexts (subagents).

> **Deep dive:** See the [RBTV README](./readme.md) for full architectural details and complete entry point listings.

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
