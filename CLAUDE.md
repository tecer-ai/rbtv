# CLAUDE.md

> When updating mirrored sections, ALWAYS update both files together.

> Claude Code reads this file directly — all content is inline, no external reads needed.

> **EXECUTION:** Agents must read `CLAUDE.md` only. NEVER read mirrored copies.

> **EDITING:** When editing any mirrored content in `CLAUDE.md`, update `_admin/.cursor/rules/admin-rbtv-bmad-mirror.mdc` and `workflows/build-rbtv-component/data/admin-restrictions.md` to match.

## Repository Identity

This repo is the **RBTV module**. It is designed to run installed inside a parent system called **BMAD**, at the path `{project-root}/_bmad/rbtv/`.

RBTV files use `{project-root}` as a placeholder referencing the BMAD installation root.

## Parent System Mirror

`_admin/docs/BMAD-mirror/` contains a read-only copy of the parent system (BMAD).

RBTV's slot in the mirror (`_admin/docs/BMAD-mirror/_bmad/rbtv/`) is intentionally empty — this repo IS that module.

## Path Resolution

RBTV uses path variables from `_config/config.yaml` (`paths:` section) to avoid multi-hop resolution. Use these variables in all cross-module references:

| Variable | Installed BMAD value | Admin (standalone) value |
|---|---|---|
| `{bmad_core}` | `{project-root}/_bmad/core` | `_admin/docs/BMAD-mirror/_bmad/core` |
| `{bmad_bmm}` | `{project-root}/_bmad/bmm` | `_admin/docs/BMAD-mirror/_bmad/bmm` |
| `{bmad_rbtv}` | `{project-root}/_bmad/rbtv` | `.` (rbtv root) |
| `{bmad_output}` | `{project-root}/_bmad-output` | `_admin-output` |

**Admin mode overrides** are declared in `_admin/.cursor/rules/admin-rbtv-bmad-mirror.mdc`.

For `{project-root}` direct references (`.cursor/`, etc.) in admin mode:

| Reference | Resolves to |
|---|---|
| `{project-root}/_bmad/rbtv/...` | `./...` (this repo's root) |
| `{project-root}/.cursor/...` | `./.cursor/...` (admin-installed IDE config) |

## Installation

RBTV ships IDE configuration in `_config/`. The unified installer (`_config/install-rbtv.py`) handles three modes: `ide` (default), `admin`, and `sync`. Source files live in this repo; installed copies are generated outputs.

**Installer modes:**

```
python _config/install-rbtv.py              # IDE mode (default)
python _config/install-rbtv.py --mode ide
python _config/install-rbtv.py --mode admin
python _config/install-rbtv.py --mode sync
python _config/install-rbtv.py --skip-version-check
```

**IDE mode** — full IDE setup at BMAD project root:

1. Checks BMAD version compatibility (warn-only, see `bmad-compat.yaml`)
2. Deletes old RBTV files (`bmad-rbtv*`) from `{project-root}/.cursor/` and `{project-root}/.claude/`
3. Copies `_config/.cursor/` contents (commands, agents, skills, rules) → `{project-root}/.cursor/`
4. Merges `_config/.cursor/mcp.json` → `{project-root}/.cursor/mcp.json` and `{project-root}/.claude/.mcp.json`
5. Replicates all `{project-root}/.cursor/commands/` → `{project-root}/.claude/commands/`
6. Normalizes `{bmad_core}/config.yaml` and `{bmad_bmm}/config.yaml` output paths to `_bmad-output/{project-name}/`
7. Adds RBTV entry to `{project-root}/_bmad/_config/bmad-help.csv`
8. Creates `{project-root}/.vscode/settings.json` if `.vscode/` does not exist (leaves existing untouched)
9. Appends patterns to `{project-root}/.cursorignore`

**Admin mode** — standalone dev setup at rbtv root (for developing RBTV outside BMAD):

1. Deletes old managed files (`bmad-rbtv*`, `admin-rbtv*`) from `.cursor/` at rbtv root
2. Copies `_config/.cursor/` contents → rbtv root `.cursor/`, applying path substitution (`{project-root}/_bmad/rbtv/` → ``) and appending a reinforcement reminder to commands/agents/skills
3. Copies `_admin/.cursor/` contents (admin-specific rules) → rbtv root `.cursor/` as-is
4. Prompts for admin config values (user name, languages) and injects them into the admin rule
5. Ensures `.gitignore` at rbtv root contains required entries (`.cursor/`, `.claude/`, `_admin-output/`) — additive, preserves existing content

**Sync mode** — BMAD config patching only (for nanobot workspace integration):

1. Checks BMAD version compatibility
2. Normalizes BMAD output paths in `_bmad/core/config.yaml` and `_bmad/bmm/config.yaml`
3. Adds RBTV entry to `_bmad/_config/bmad-help.csv`
4. No IDE config created (.cursor/.claude artifacts not touched)

Idempotent for all modes — re-run after every `git pull`.

**Installed BMAD structure (RBTV touchpoints only — IDE mode):**

```
{project-root}/                              # BMAD project root
├── .cursor/
│   ├── commands/bmad-rbtv-*.md              # ← from _config/.cursor/commands/
│   ├── agents/bmad-rbtv-*.md                # ← from _config/.cursor/agents/
│   ├── skills/bmad-rbtv-*/SKILL.md          # ← from _config/.cursor/skills/
│   ├── rules/bmad-rbtv-*.mdc               # ← from _config/.cursor/rules/
│   └── mcp.json                             # ← merged from _config/.cursor/mcp.json
├── .claude/
│   ├── commands/bmad-rbtv-*.md              # ← replicated from .cursor/commands/
│   └── .mcp.json                            # ← merged from _config/.cursor/mcp.json
├── .vscode/settings.json                    # ← created from _config/.vscode/settings.json (only if new)
├── .cursorignore                            # ← patterns appended
├── _bmad/
│   ├── _config/bmad-help.csv                # ← RBTV entry added
│   ├── core/config.yaml                     # ← output_folder normalized to _bmad-output/{project-name}
│   ├── bmm/config.yaml                      # ← output paths normalized to _bmad-output/{project-name}
│   └── rbtv/                                # ← THIS REPO
│       └── _config/install-rbtv.py          #    the unified installer (3 modes)
└── _bmad-output/                            # runtime output folder
```

## Boundaries

- NEVER modify anything under `_admin/docs/BMAD-mirror/` — it is read-only reference material.
- Only modify or create files within the RBTV repo itself (everything outside `_admin/docs/BMAD-mirror/`).
- `{project-root}` placeholders in RBTV files are runtime-resolved by the BMAD installer. Always preserve them as-is when editing.

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
