# RBTV — Getting Started

Welcome to **RBTV** (Robotville), a BMAD module for business innovation, documentation, planning, and developer workflows.

---

## Prerequisites

### Software

| Software | Purpose | Required |
|----------|---------|----------|
| **Python 3** | Runs the installation script | Yes |
| **Node.js** (with `npx`) | Required by `playwright-mcp` MCP server | Yes (for browser automation tools) |

### BMAD Modules

RBTV requires the following BMAD modules installed:

| Module | Tick in installer | Provides | Purpose | Required |
|--------|-------------------|----------|---------|----------|
| BMAD Core | **BMad Core** | `core/`, `bmm/` | Workflow engine, config, brainstorming; product documentation (Brief, PRD, UX) | Yes |
| cis | **BMad Creative Innovation Suite** | `cis/` | Problem-solving methodologies (used by domcobb) | Yes |

**Install BMAD** with these modules before proceeding. Use either:

- **Guided (recommended):** `npx bmad-method install` — interactive installer, select the modules above when prompted
- **Manual:** Clone [BMAD-METHOD](https://github.com/bmadcode/BMAD-METHOD) and set up `_bmad/` yourself

When you select **BMad Core** during installation, both `core/` and `bmm/` folders are created in `_bmad/`.

**MCP requirement for Business Innovation:** The **Playwright MCP** must be configured to use the Business Innovation module from milestone 3 onward (milestone 3 inclusive).

### MCP Servers

The install script merges the following MCP servers into `.cursor/mcp.json` and `.claude/.mcp.json`:

| Server | Install Method | Used By |
|--------|---------------|---------|
| `playwright-mcp` | `npx -y playwright-mcp` | `/bmad-rbtv-playwright-browser-automation`, `/bmad-rbtv-design-validation` |

---

## Setup Overview

After installation, your directory structure will look like this:

```
BMAD-METHOD/                    (installed from github.com/bmadcode/BMAD-METHOD)
├── _bmad/
│   ├── core/                   (from BMAD Core)
│   ├── bmm/                    (from BMAD Core)
│   ├── cis/                    (BMAD cis module)
│   └── rbtv/                   (this module - cloned from github.com/hlealt/rbtv)
│
├── .cursor/                    (merged content from BMAD + RBTV via install script)
├── .claude/                    (merged content from BMAD + RBTV via install script)
│
└── _bmad-output/
    ├── project-1/              (your GitHub repos)
    ├── project-2/              (your GitHub repos)
    └── project-N/              (your GitHub repos)
```

**Key points:**
- BMAD-METHOD is your main installation directory
- `_bmad/` contains all BMAD modules including RBTV
- `.cursor/` and `.claude/` are created/updated by the install script
- `_bmad-output/` contains your projects and development work
- `.vscode/settings.json` configures workspace visibility (UI only)
- `.cursorignore` blocks AI agent access to specified folders

---

## Installation

### Step 1: Clone RBTV

Navigate to your BMAD `_bmad/` folder and clone RBTV:

```bash
cd path/to/BMAD-METHOD/_bmad
git clone https://github.com/bmadcode/rbtv.git rbtv
```

### Step 2: Run the Installation Script

RBTV includes IDE configuration files (`.cursor/`) that must be merged with BMAD's configuration. Run the installation script:

```bash
cd rbtv
python _config/install-rbtv.py
```

> **macOS users:** use `python3` if `python` is not found.

**What the script does:**
- Deletes old RBTV files under `/.cursor/` (rules, agents, commands, skills with `bmad-rbtv-` prefix)
- Copies `rbtv/_config/.cursor/` contents → project root `/.cursor/`
- Merges `rbtv/_config/.cursor/mcp.json` → project root `/.cursor/mcp.json` (for Cursor IDE)
- Merges `rbtv/_config/.cursor/mcp.json` → project root `/.claude/.mcp.json` (for Claude Code)
- Creates project root `/.claude/commands/` and replicates Cursor commands for Claude compatibility
- Creates `/.vscode/settings.json` from `rbtv/_config/.vscode/settings.json` only if `.vscode/` does not exist (leaves existing untouched)
- Merges RBTV patterns into project root `/.cursorignore` (adds `_bmad-output/archive/`)
- Overwrites existing files if conflicts occur (except `.vscode/settings.json` and `.cursorignore` which merge)

> **Important:** Run this script every time you update RBTV (`git pull` or `git fetch`). The script copies (not moves) files, so source files remain in `rbtv/`.

### Step 3: Open Your IDE

Open Cursor (or Claude) in your BMAD project root folder (the parent of `_bmad/`).

---

## Workspace Organization & Visibility

RBTV automatically configures your workspace to manage project visibility and AI access control.

### File Exclusions (UI Visibility)

**Default Configuration:**
The install script creates/updates `.vscode/settings.json` with these exclusions:
- All `_bmad/*` folders (BMAD system files and RBTV source code)
- `_bmad-output/archive/` folder (for inactive projects)

**What This Does:**
- Hides BMAD internals from Cursor's sidebar (you still have access to `.cursor` and `.claude` tools)
- Removes excluded folders from search results
- Excludes them from Quick Open (Ctrl+P)
- Keeps your workspace focused on your active projects
- **Does NOT block AI agent access** (agents can still read these files)

**Managing Project Visibility:**
You can add your own projects to `files.exclude` in `.vscode/settings.json`:

```json
{
  "files.exclude": {
    "_bmad/*": true,
    "_bmad-output/archive": true,
    "_bmad-output/my-inactive-project": true
  }
}
```

**Recommended Workflow:**
1. When not actively working on a project, add it to `files.exclude`
2. Or move inactive projects to `_bmad-output/archive/` (already excluded by default)
3. This keeps your workspace clean and focused on active work
4. You don't need to see RBTV source code or BMAD internals - just use the tools via `.cursor` and `.claude`

### AI Access Control

**Blocking AI Access:**
To prevent AI agents from accessing folders or files, add them to `.cursorignore`:

```
# Block AI access to archived projects
_bmad-output/archive/

# Block AI access to specific project
_bmad-output/old-project/

# Block AI access to sensitive files
secrets.json
.env
```

**Default Configuration:**
The install script adds `_bmad-output/archive/` to `.cursorignore` by default.

**Key Difference:**
- `.vscode/settings.json` (`files.exclude`) = UI visibility only
- `.cursorignore` = Blocks AI agent access completely

**Best Practice:**
For archived or inactive projects, add them to BOTH:
1. `.vscode/settings.json` → hides from UI
2. `.cursorignore` → prevents AI from reading them

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
| **Commands** | User types `/command` | Maintains current context window | Humans |
| **Skills** | Agent auto-detects relevance | Maintains current context window | AI agents |
| **Cursor Sub-agents** | Agent delegates via Task tool | Fresh context window (zero prior context) | AI agents |

All 15 RBTV tools are commands. 12 of them are additionally exposed as skills and cursor sub-agents for AI use. The remaining 3 (help, mentor, domcobb) are human-only commands with no AI entry point.

**AI tool catalog:** `_bmad/rbtv/_config/tools-manifest.csv` — lists the 12 AI-available tools with skill_path and cursor_subagent_path. Skills: read skill_path in context. Cursor sub-agents: use Task tool with `subagent_type='<id>'`.

> **Deep dive:** See the [RBTV README](./readme.md) for full architectural details and complete entry point listings.

---

## Entry Points

All 15 RBTV tools are commands (human-invoked). 12 are also available as skills (AI auto-detected) and cursor sub-agents (AI-delegated with fresh context). 3 commands (help, mentor, domcobb) are human-only.

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
python _config/install-rbtv.py
```

> **macOS users:** use `python3` if `python` is not found.

The installation script must run after every update to sync IDE configuration files.

---

## Developing RBTV (Admin Mode)

If you are developing or maintaining RBTV itself (working directly from the `rbtv/` repository rather than a BMAD installation), see [`_admin/README.md`](./_admin/README.md) for admin tools that set up standalone IDE configuration.

**Warning:** The installer (`_config/install-rbtv.py --mode admin`) manages all `bmad-rbtv-*` and `admin-rbtv-*` files in `.cursor/`. These files are deleted and recreated on every sync. Do not use those prefixes for personal cursor tools — they will be lost.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Commands not appearing | Run `install-rbtv.py` and restart your IDE |
| "Module not found" errors | Ensure BMAD Core (provides core + bmm) and cis modules are installed |
| Workflows fail to load | Check `_bmad/rbtv/_config/config.yaml` exists and is valid |

---

*Built with the BMAD Method — structure reveals solutions.*
