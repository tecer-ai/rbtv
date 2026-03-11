---
description: "RBTV admin mode — standalone path resolution, config overrides, module identity"
---
# RBTV Admin Mode

> **EXECUTION:** Cursor agents must read this file only. NEVER read `CLAUDE.md` for path resolution.

> **EDITING:** When editing any content below "Admin Config Overrides", update `CLAUDE.md` to match.

## Admin Config Overrides

These values take precedence over `_config/config.yaml`:

| Key | Value |
|-----|-------|
| user_name | "{admin_user_name}" |
| communication_language | "{admin_communication_language}" |
| document_output_language | "{admin_document_output_language}" |
| output_folder | "_admin-output" |
| paths.bmad_core | "_admin/docs/BMAD-mirror/_bmad/core" |
| paths.bmad_bmm | "_admin/docs/BMAD-mirror/_bmad/bmm" |
| paths.bmad_rbtv | "." |
| paths.bmad_output | "_admin-output" |

## Repository Identity

This repo is the **RBTV module**. It is designed to run installed inside a parent system called **BMAD**, at the path `{project-root}/_bmad/rbtv/`.

RBTV files use `{project-root}` as a placeholder referencing the BMAD installation root.

## Parent System Mirror

`_admin/docs/BMAD-mirror/` contains a read-only copy of the parent system (BMAD).

RBTV's slot in the mirror (`_admin/docs/BMAD-mirror/_bmad/rbtv/`) is intentionally empty — this repo IS that module.

## Path Resolution

When RBTV files reference `{project-root}` paths, resolve them as follows:

| Reference | Resolves to |
|---|---|
| `{project-root}/_bmad/rbtv/...` | `./...` (this repo's root) |
| `{project-root}/.cursor/...` | `./.cursor/...` (admin-installed IDE config) |
| `{project-root}/...` (everything else) | `./_admin/docs/BMAD-mirror/...` |

## Installation

RBTV ships IDE configuration in `_config/.claude/` (canonical source). The installer (`_config/install-rbtv.py`) copies these files to the BMAD project root and derives `.cursor/` equivalents. Source files live in this repo; installed copies are generated outputs.

**What the installer does:**

1. Deletes old RBTV files (`bmad-rbtv*`) from `{project-root}/.cursor/` and `{project-root}/.claude/`
2. Copies `_config/.claude/` contents (commands, agents, skills, rules) → `{project-root}/.claude/`
3. Merges `_config/.cursor/mcp.json` → `{project-root}/.cursor/mcp.json` and `{project-root}/.claude/.mcp.json`
4. Derives `{project-root}/.cursor/commands/` from `{project-root}/.claude/commands/` (direct copy)
5. Derives `{project-root}/.cursor/rules/` from `{project-root}/.claude/rules/` (`.md` → `.mdc`, frontmatter converted)
6. Derives `{project-root}/.cursor/agents/` from `{project-root}/.claude/agents/` (frontmatter converted)
7. Derives `{project-root}/.cursor/skills/` from `{project-root}/.claude/skills/` (direct copy)
8. Updates `{bmad_core}/config.yaml` and `{bmad_bmm}/config.yaml`
9. Adds RBTV entry to `{project-root}/_bmad/_config/bmad-help.csv`
10. Creates `{project-root}/.vscode/settings.json` if `.vscode/` does not exist (leaves existing untouched)
11. Appends patterns to `{project-root}/.cursorignore`

**Installed BMAD structure (RBTV touchpoints only):**

```
{project-root}/                              # BMAD project root
├── .claude/
│   ├── commands/bmad-rbtv-*.md              # ← from _config/.claude/commands/
│   ├── rules/bmad-rbtv-*.md                 # ← from _config/.claude/rules/
│   ├── agents/bmad-rbtv-*.md                # ← from _config/.claude/agents/
│   ├── skills/bmad-rbtv-*/SKILL.md          # ← from _config/.claude/skills/
│   └── .mcp.json                            # ← merged from _config/.cursor/mcp.json
├── .cursor/
│   ├── commands/bmad-rbtv-*.md              # ← derived from .claude/commands/
│   ├── agents/bmad-rbtv-*.md                # ← derived from .claude/agents/
│   ├── skills/bmad-rbtv-*/SKILL.md          # ← derived from .claude/skills/
│   ├── rules/bmad-rbtv-*.mdc               # ← derived from .claude/rules/ (.md→.mdc)
│   └── mcp.json                             # ← merged from _config/.cursor/mcp.json
├── .vscode/settings.json                    # ← created from _config/.vscode/settings.json (only if new)
├── .cursorignore                            # ← patterns appended
├── _bmad/
│   ├── _config/bmad-help.csv                # ← RBTV entry added
│   ├── core/config.yaml                     # ← output_folder updated
│   ├── bmm/config.yaml                      # ← output paths updated
│   └── rbtv/                                # ← THIS REPO
│       └── _config/install-rbtv.py          #    the installer script
└── _bmad-output/                            # runtime output folder
```

## Admin / Standalone Development

`_admin/` contains tooling for developing RBTV as a standalone repo (outside a parent BMAD project). Run `_config/install-rbtv.py --mode admin` to set up `.claude/` and `.cursor/` at the rbtv root so IDE commands, agents, skills, and rules work without a parent BMAD installation.

**What admin mode does:**

1. Deletes old managed files (`bmad-rbtv*`, `admin-rbtv*`) from `.cursor/` and `.claude/` at rbtv root
2. Copies `_config/.claude/` contents → rbtv root `.claude/`, applying path substitution (`{project-root}/_bmad/rbtv/` → ``) and appending a reinforcement reminder to commands/agents/skills
3. Copies `_admin/.claude/` contents (admin-specific rules) → rbtv root `.claude/` as-is
4. Derives `.cursor/commands/` from `.claude/commands/` (direct copy)
5. Derives `.cursor/rules/` from `.claude/rules/` (`.md` → `.mdc`, frontmatter converted)
6. Derives `.cursor/agents/` from `.claude/agents/` (frontmatter converted)
7. Derives `.cursor/skills/` from `.claude/skills/` (direct copy)
8. Merges `_config/.cursor/mcp.json` → rbtv root `.claude/.mcp.json`
9. Prompts for admin config values (user name, languages) and injects them into the admin rule
10. Ensures `.gitignore` at rbtv root contains required entries (`.cursor/`, `.claude/`, `_admin-output/`) — additive, preserves existing content

Idempotent for all modes — re-run after every `git pull`.

## Boundaries

- NEVER modify anything under `_admin/docs/BMAD-mirror/` — it is read-only reference material.
- Only modify or create files within the RBTV repo itself (everything outside `_admin/docs/BMAD-mirror/`).
- `{project-root}` placeholders in RBTV files are runtime-resolved. Always preserve them as-is when editing.
