# RBTV

A standalone Claude Code toolkit for business innovation, pitch generation, documentation, and structured thinking.

## What is RBTV?

RBTV is a self-contained set of agents, workflows, skills, and rules designed to be bootstrapped into any Claude Code workspace. After install, RBTV appears as `/rbtv-<command>` slash commands (e.g., `/rbtv-client-pitch`, `/rbtv-doc`, `/rbtv-planning`) and auto-triggered skills in your workspace.

## Requirements

- Claude Code (CLI, desktop, or IDE extension)
- Python 3.11+ (for `install.py`)
- `pyyaml` Python package
- Claude Code plugins (see [Plugins](#plugins) for install instructions)

### Optional dependencies (per module)

**npm:**

| Dependency | Install | Required by |
|---|---|---|
| `playwright-cli` | `npx playwright install` | browser-automation, design-extraction, playwright-cli skill |
| `serve` | `npx -y serve` (auto) | browser-automation (local server for file:// bypass) |
| `md-to-pdf` | `npm install -g md-to-pdf` | doc-export (PDF output) |
| `defuddle` | `npm install -g defuddle` | web-search, web-searching skill |
| `decktape` | `npx decktape` (auto) | pitch (HTML→PDF export) |

**Python:**

| Dependency | Install | Required by |
|---|---|---|
| `python-docx` | `pip install python-docx` | doc-export (DOCX output) |
| `pyyaml` | `pip install pyyaml` | doc-export (DOCX output), install.py |

**System:**

| Dependency | Required by |
|---|---|
| `git` | commit workflow |

**Runtime CDN (no install — loaded at render time):**

| Resource | Required by |
|---|---|
| Google Fonts (Inter), Font Awesome 6, Material Icons | pitch (HTML slides) |
| Twitter/YouTube/noembed oEmbed APIs | web-search (embed previews) |

## Plugins

RBTV uses Claude Code plugins for extended functionality. Install them from inside a Claude Code session using `/plugin` commands.

**Recommended** — enhance specific workflows but RBTV works without them:

| Plugin | What it enhances |
|---|---|
| `bmad-method-lifecycle` | Market/domain/technical research for M2 Validation |
| `bmad-pro-skills` | Advanced elicitation and brainstorming after problem structuring |

```
/plugin marketplace add https://github.com/bmad-code-org/BMAD-METHOD.git
/plugin install bmad-pro-skills@bmad-method
/plugin install bmad-method-lifecycle@bmad-method
```

**Also recommended** — complement RBTV well:

| Plugin | What it provides |
|---|---|
| `frontend-design` | Production-grade UI generation with high design quality |
| `superpowers` | Skill-driven workflows, TDD, brainstorming, plan execution, code review |
| `compound-engineering` | Frontend design, git workflows, debugging, ideation, browser automation |

```
/plugin install frontend-design@claude-plugins-official
/plugin install superpowers@claude-plugins-official
```

```
/plugin marketplace add EveryInc/compound-engineering-plugin
/plugin install compound-engineering@compound-engineering-plugin
```

## Install

1. Clone RBTV as a subfolder of your workspace:

   ```bash
   cd /path/to/your/workspace
   git clone <rbtv-repo-url> rbtv
   ```

   RBTV must live INSIDE the workspace that will use it.

2. Run the installer:

   ```bash
   python rbtv/install.py --target /path/to/your/workspace
   ```

   The installer prompts for:
   - Modules to install (core is always included)

   Output paths are resolved at runtime by the `rbtv-output-resolution` rule, which uses conversation context and workspace CLAUDE.md conventions to propose paths.

3. After install, your workspace has:
   - `.claude/skills/rbtv-*/` — thin loaders for skills
   - `.claude/commands/rbtv-*.md` — slash commands
   - `.claude/rules/rbtv-*.md` — rule content (copied — includes `rbtv-output-resolution` which governs how components resolve output paths at runtime)
   - `rbtv.yaml` — your install config

## Modules

| Module | What it does |
|---|---|
| **core** (always installed) | Generic productivity skills — planning, documentation, domcobb (problem structuring), meeting summarization, web research, component creation |
| **innovation** | Business innovation frameworks (lean canvas, JTBD, TAM/SAM/SOM, brandbook) via Paul, plus product discovery |
| **work-productivity** | Pitch generation (client, investor), design extraction, visual design via Vivian, document export (PDF/DOCX with brand discovery), legal advisory |
| **writing** | Long-form writing via George Orwell, tone extraction |

## Updating RBTV

RBTV content (agents, workflows, tasks) stays in this repo — thin loaders in your workspace reference it by path. To get new content:

```bash
cd /path/to/your/workspace/rbtv
git pull
```

Content changes appear live. You only need to re-run `install.py` when:
- Adding or removing modules
- RBTV's own module manifest or loader templates change

## Source of truth

Installed files in `.claude/skills/rbtv-*`, `.claude/commands/rbtv-*.md`, `.claude/rules/rbtv-*.md`, `.claude/agents/rbtv-*.md` are regenerated on every `install.py` run. **Do not edit them in your workspace** — edit the source in this repo and re-install. See `.claude/rules/rbtv-source-of-truth.md` in your workspace for more.

## Architecture notes

- **Thin loaders:** installed loaders are short files that point back to this repo via a vault-relative path (e.g., `rbtv/`). No content is duplicated into your workspace.
- **Rule exception:** rule files are copied as content (not loaders), because rules load passively into Claude's context and indirection is unreliable.
- **Subagent exception:** subagent files (`.claude/agents/rbtv-*.md`) are copied as content too — they're dispatched in fresh context via the Task tool, so they must be self-contained.
- **Overwrite scope:** re-install tracks the previous install's file list in `rbtv.yaml` (`installed_files:`) and removes only those paths. Your workspace content (notes, projects, other skills, Fernando-authored local components) is never touched.

## Extending RBTV

Use `/rbtv-create-component`. When you create a new component, the agent will ask whether to publish it to the RBTV source (requires re-install to propagate) or write it locally to your workspace only.
