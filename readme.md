# RBTV

A standalone Claude Code toolkit for business innovation, pitch generation, documentation, and structured thinking.

## What is RBTV?

RBTV is a self-contained set of agents, workflows, skills, and rules designed to be bootstrapped into any Claude Code workspace. After install, RBTV appears as `/rbtv-<command>` slash commands (e.g., `/rbtv-client-pitch`, `/rbtv-doc`, `/rbtv-planning`) and auto-triggered skills in your workspace.

## Requirements

- Claude Code (CLI, desktop, or IDE extension)
- Python 3.11+ (for `install.py`)
- `pyyaml` Python package
- BMAD plugins for full functionality:
  - `bmad-method-lifecycle` (Ana references this for PRD, Brief, UX)
  - `bmad-pro-skills` (DomCobb references this for Problem Solving)

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

   Output paths are NOT configured at install time. They are resolved at runtime from `## File Routing` blocks in your workspace's CLAUDE.md files (governed by the `rbtv-output-resolution` rule). See step 4 below to populate these blocks after install.

3. After install, your workspace has:
   - `.claude/skills/rbtv-*/` — thin loaders for skills (including `rbtv-output-routing` for the post-install setup in step 4)
   - `.claude/commands/rbtv-*.md` — slash commands (including `/rbtv-output-routing`)
   - `.claude/rules/rbtv-*.md` — rule content (copied — includes `rbtv-output-resolution` which governs how components resolve output paths at runtime)
   - `.claude/agents/rbtv-*.md` — dispatchable subagents (designer, web-research)
   - `rbtv.yaml` — your install config

4. Configure output routing (one-time post-install):

   Open Claude Code in the workspace and run:

   ```
   /rbtv-output-routing
   ```

   The workflow scans your CLAUDE.md files and interactively writes `## File Routing` blocks so RBTV components know where to place outputs. Routing is human-readable in CLAUDE.md and can be edited by hand or re-run via the same command whenever structure changes.

## Modules

| Module | What it does |
|---|---|
| **core** (always installed) | Generic productivity skills — planning, documentation, domcobb (problem structuring), meeting summarization, web research, component creation |
| **innovation** | Business innovation frameworks (lean canvas, JTBD, TAM/SAM/SOM, brandbook) via Paul, plus product discovery |
| **work-productivity** | Pitch generation (client, investor), design extraction, visual design via Vivian |
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

To change output routing, edit the `## File Routing` blocks in your workspace CLAUDE.md files directly, or re-run `/rbtv-output-routing`. No install re-run needed.

## Source of truth

Installed files in `.claude/skills/rbtv-*`, `.claude/commands/rbtv-*.md`, `.claude/rules/rbtv-*.md`, `.claude/agents/rbtv-*.md` are regenerated on every `install.py` run. **Do not edit them in your workspace** — edit the source in this repo and re-install. See `.claude/rules/rbtv-source-of-truth.md` in your workspace for more.

## Architecture notes

- **Thin loaders:** installed loaders are short files that point back to this repo via a vault-relative path (e.g., `rbtv/`). No content is duplicated into your workspace.
- **Rule exception:** rule files are copied as content (not loaders), because rules load passively into Claude's context and indirection is unreliable.
- **Subagent exception:** subagent files (`.claude/agents/rbtv-*.md`) are copied as content too — they're dispatched in fresh context via the Task tool, so they must be self-contained.
- **Overwrite scope:** re-install tracks the previous install's file list in `rbtv.yaml` (`installed_files:`) and removes only those paths. Your workspace content (notes, projects, other skills, Fernando-authored local components) is never touched.

## Extending RBTV

Use `/rbtv-create-component` with Fernando. When you create a new component, Fernando asks whether to publish it to the RBTV source (requires re-install to propagate) or write it locally to your workspace only.

## License and contact

TBD.
