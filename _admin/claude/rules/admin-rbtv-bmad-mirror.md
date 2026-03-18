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
| `{project-root}/.cursor/...` | `./.cursor/...` (admin-installed workspace config) |
| `{project-root}/...` (everything else) | `./_admin/docs/BMAD-mirror/...` |

## Installation

RBTV ships platform configuration in `_config/claude/` (canonical source, no dot prefix). The installer (`_config/bootstrap.py`) copies these files to the workspace root and derives `.cursor/` equivalents. Source files live in this repo; installed copies are generated outputs.

**Installed BMAD structure (RBTV touchpoints only):**

```
{project-root}/                              # BMAD project root
├── .claude/
│   ├── commands/bmad-rbtv-*.md              # ← from _config/claude/commands/
│   ├── rules/bmad-rbtv-*.md                 # ← from _config/claude/rules/
│   ├── agents/bmad-rbtv-*.md                # ← from _config/claude/agents/
│   ├── skills/bmad-rbtv-*/SKILL.md          # ← from _config/claude/skills/
│   └── .mcp.json                            # ← merged from _config/claude/.mcp.json
├── .cursor/
│   ├── commands/bmad-rbtv-*.md              # ← derived from .claude/commands/
│   ├── agents/bmad-rbtv-*.md                # ← derived from .claude/agents/
│   ├── skills/bmad-rbtv-*/SKILL.md          # ← derived from .claude/skills/
│   ├── rules/bmad-rbtv-*.mdc               # ← derived from .claude/rules/ (.md→.mdc)
│   └── mcp.json                             # ← derived from _config/claude/.mcp.json
├── .vscode/settings.json                    # ← created from _config/.vscode/settings.json (only if new)
├── .cursorignore                            # ← patterns appended
├── _bmad/
│   ├── _config/bmad-help.csv                # ← RBTV entry added
│   ├── core/config.yaml                     # ← output_folder updated
│   ├── bmm/config.yaml                      # ← output paths updated
│   └── rbtv/                                # ← THIS REPO
│       └── _config/bootstrap.py              #    the installer script
└── projects/                            # runtime output folder
```

## Admin / Standalone Development

`_admin/` contains tooling for developing RBTV as a standalone repo (outside a parent BMAD project). Run `_config/bootstrap.py --mode admin` to set up `.claude/` and `.cursor/` at the rbtv root so commands, agents, skills, and rules work without a parent BMAD installation.

## Boundaries

- NEVER modify anything under `_admin/docs/BMAD-mirror/` — it is read-only reference material.
- Only modify or create files within the RBTV repo itself (everything outside `_admin/docs/BMAD-mirror/`).
- `{project-root}` placeholders in RBTV files are runtime-resolved. Always preserve them as-is when editing.
