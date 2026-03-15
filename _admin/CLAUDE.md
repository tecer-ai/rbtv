# CLAUDE.md

> When updating mirrored sections, ALWAYS update both files together.

> **EXECUTION:** Agents must read `CLAUDE.md` only. NEVER read mirrored copies.

> **EDITING:** When editing any mirrored content in `CLAUDE.md`, update `_admin/.claude/rules/admin-rbtv-bmad-mirror.md` and `workflows/build-rbtv-component/data/admin-restrictions.md` to match.

## Repository Identity

This repo is the **RBTV module**. It is designed to run installed inside a parent system called **BMAD**, at the path `{project-root}/_bmad/rbtv/`.

RBTV files use `{project-root}` as a placeholder referencing the BMAD installation root. Always preserve these placeholders as-is when editing.

## Parent System Mirror

`_admin/docs/BMAD-mirror/` is a **read-only, complete snapshot** of a BMAD project root — the parent system RBTV installs into. When this repo is opened standalone in Cursor or Claude Code, the workspace root is `rbtv/` — agents cannot see any parent folders and have zero visibility into BMAD's structure. The mirror brings a copy of the parent system into RBTV's tree so agents can resolve cross-module references, inspect BMAD components (workflows, configs, manifests), and check existing capabilities before creating new ones.

The mirror reproduces the BMAD project root layout: `claude/`, `cursor/`, `_bmad/` (with all modules: core, bmm, bmb, cis, tea), `docs/`, and `projects/`. The `claude/` and `cursor/` directories correspond to `.claude/` and `.cursor/` in the real workspace — the dot prefix is removed to prevent IDEs from scanning them as live command sources (which causes duplicate entries in the command picker). RBTV's slot (`_admin/docs/BMAD-mirror/_bmad/rbtv/`) is intentionally empty — this repo IS that module.

**The mirror must always match the BMAD version RBTV targets** (currently v6.0.4, per `_config/config.yaml`).

## Upgrade Reference Versions

When upgrading RBTV to a new BMAD version, the target BMAD installation is placed at `_admin/docs/BMAD-v{version}/`. Compare this against `_admin/docs/BMAD-mirror/` (current baseline) to identify structural changes affecting RBTV. After the upgrade, replace the mirror contents with the new version's files (preserving `MIRROR-VERSION.md` and the empty `_bmad/rbtv/` slot), then delete the `BMAD-v{version}/` directory.

## Path Resolution

RBTV uses path variables from `_config/config.yaml` (`paths:` section). Use these in all cross-module references:

| Variable | Installed BMAD value | Admin (standalone) value |
|---|---|---|
| `{bmad_core}` | `{project-root}/_bmad/core` | `_admin/docs/BMAD-mirror/_bmad/core` |
| `{bmad_bmm}` | `{project-root}/_bmad/bmm` | `_admin/docs/BMAD-mirror/_bmad/bmm` |
| `{bmad_rbtv}` | `{project-root}/_bmad/rbtv` | `.` (rbtv root) |
| `{bmad_output}` | `{project-root}/{output-folder}` (read from BMAD `core/config.yaml`) | `_admin-output` |

**Admin mode overrides** are declared in `_admin/.claude/rules/admin-rbtv-bmad-mirror.md`.

For `{project-root}` direct references in admin mode:

| Reference | Resolves to |
|---|---|
| `{project-root}/_bmad/rbtv/...` | `./...` (this repo's root) |
| `{project-root}/.cursor/...` | `./.cursor/...` (admin-installed IDE config) |

## Installation

RBTV ships IDE configuration in `_config/`. The unified installer (`_config/install-rbtv.py`) handles three modes:

- **`workspace`** (default) — full IDE setup at BMAD project root: copies commands/agents/skills/rules from `_config/claude/` to `.claude/`, derives `.cursor/` equivalents (with format conversion), merges MCP config, normalizes output paths, adds RBTV to help catalog
- **`admin`** — standalone dev setup at rbtv root: copies from `_config/claude/` and `_admin/claude/` to `.claude/`, derives `.cursor/`, with path substitution and admin-specific rules
- **`sync`** — BMAD config patching only (for nanobot): normalizes output paths and help catalog, no IDE artifacts

```
python _config/install-rbtv.py              # workspace mode (default)
python _config/install-rbtv.py --mode admin
python _config/install-rbtv.py --mode sync
python _config/install-rbtv.py --skip-version-check
```

Idempotent for all modes — re-run after every `git pull`. See `_config/install-rbtv.py` for full details.

## Boundaries

- NEVER modify anything under `_admin/docs/BMAD-mirror/` — it is read-only reference material.
- Only modify or create files within the RBTV repo itself (everything outside `_admin/docs/BMAD-mirror/`).

> **EXECUTION:** Agents must read this section in `CLAUDE.md` only. NEVER read `workflows/build-rbtv-component/data/admin-restrictions.md` to execute these restrictions.

> **EDITING:** When editing this section in `CLAUDE.md`, update `workflows/build-rbtv-component/data/admin-restrictions.md` to match.

## [MIRRORED → admin-restrictions] Admin Restrictions

### Hard Restrictions

#### 1. BMAD Component Map Check

Before any component creation or structural modification, read `_admin/docs/BMAD-mirror/_bmad/_config/bmad-help.csv`. This manifest lists every BMAD capability with module, name, and description. Evaluate whether the request can be delegated totally or partially to an existing BMAD component.

#### 2. Never Touch BMAD

BMAD is maintained by a separate group unaware of RBTV. NEVER modify BMAD components directly. In a BMAD instance, touch BMAD files only when absolutely unavoidable — and when done, automate the change (via installer or script) so it survives BMAD updates without manual intervention.

#### 3. Leverage BMAD

Use all BMAD components (not just entry points) to make RBTV and business innovation modules more powerful. RBTV integrates TO BMAD; integrating BMAD to RBTV is out of scope.

#### 4. Prefer Native BMAD

ALWAYS use an existing BMAD component instead of creating a new RBTV one, if it fulfills the requirements of what is being requested.

#### 5. Minimal Internalization

Internalize from BMAD to RBTV only what is strictly necessary for correct functioning. Prefer referencing over copying.

#### 6. Discrepancy Documentation

If structural differences between BMAD and RBTV are discovered during work, document them in `_admin/docs/bmad-discrepancies/`, in the for of a PRD to fix the discrepancy, adapting rbtv to BMAD standards and highlighting what is unique to BMAD and what is unique to RBTV. Do not document the discrepancies if they are documented in existing PRDs in this folder (place a YAML header in the PRDs with a description that will allow you and other AI Agents to identify that later on)

> **EXCLUSIVE:** Sections below are exclusive to this document.

### Task Location

Plans live in `_admin/roadmap/todos/_claude-code-workspace/`. NEVER execute work that is not listed in a plan file there.

### Supported Format

Only `.plan.md` files are supported. Do not execute other formats unless the user explicitly instructs otherwise.

### Reading `.plan.md` Files

A `.plan.md` file has a YAML frontmatter followed by a markdown body:

- **Frontmatter fields:**
  - `name` — Plan identifier (used for branch naming)
  - `overview` — One-line summary of the plan's goal
  - `todos` — Array of tasks, each with `id`, `content`, and `status` (`pending` | `completed` | `cancelled`)
  - `isProject` (optional) — Whether the plan represents a full project

- **Body:** Context, decisions, constraints, companion file references. Read the full body before starting execution — it contains critical context.

- **Status tracking:** Mark tasks as `completed` when done. No `in_progress` state needed.

### Branching

Each plan (each `.plan.md` file) MUST be executed in its own branch, named after the plan's `name` field. Exception: user explicitly instructs otherwise, or the plan file specifies a different branching strategy.

### Sequential Execution

Always work on the HEAD of the plan's branch. Plan files may reference previous commits for context — NEVER modify those commits. All work is forward-only.

### Micro Commits

Plan commit groups before executing code changes:

| Rule | Description |
|------|-------------|
| **Plan first** | Before writing code, decide which additions/modifications form a coherent commit |
| **Commit immediately** | Commit right after completing each planned group of changes |
| **Push after each commit** | Push to remote after every commit — never batch pushes |
| **Minimum per phase** | At least one commit per phase of the plan |
| **Multi-commit tasks** | More than one commit per phase or task is allowed and encouraged for complex work |
| **Conventional Commits** | All commits MUST follow the Conventional Commits specification (`type(scope): description`) |

### Commit Message Format

```
type(scope): P{phase}-{task-id} description
```

For tasks requiring multiple commits, append sequential letters:

```
type(scope): P{phase}-{task-id}a description of first part
type(scope): P{phase}-{task-id}b description of second part
type(scope): P{phase}-{task-id}c description of third part
```
