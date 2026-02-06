# CLAUDE.md

## Repository Identity

This repo is the **RBTV module**. It is designed to run installed inside a parent system called **BMAD**, at the path `{project-root}/_bmad/rbtv/`.

RBTV files use `{project-root}` as a placeholder referencing the BMAD installation root.

## Parent System Mirror

`_docs/system-documentation/BMAD/` contains a read-only copy of the parent system (BMAD).

RBTV's slot in the mirror (`_docs/system-documentation/BMAD/_bmad/rbtv/`) is intentionally empty — this repo IS that module.

## Path Resolution

When RBTV files reference `{project-root}` paths, resolve them as follows:

| Reference | Resolves to |
|---|---|
| `{project-root}/_bmad/rbtv/...` | `./...` (this repo's root) |
| `{project-root}/...` (everything else) | `./_docs/system-documentation/BMAD/...` |

## Installation

RBTV ships IDE configuration in `_config/`. The installer (`_config/install-rbtv.py`) copies these files to the BMAD project root. Source files live in this repo; installed copies are generated outputs.

**What the installer does:**

1. Deletes old RBTV files (`bmad-rbtv*`) from `{project-root}/.cursor/` and `{project-root}/.claude/`
2. Copies `_config/.cursor/` contents (commands, agents, skills, rules) → `{project-root}/.cursor/`
3. Merges `_config/.cursor/mcp.json` → `{project-root}/.cursor/mcp.json` and `{project-root}/.claude/.mcp.json`
4. Replicates all `{project-root}/.cursor/commands/` → `{project-root}/.claude/commands/`
5. Updates `{project-root}/_bmad/core/config.yaml` and `{project-root}/_bmad/bmm/config.yaml`
6. Adds RBTV entry to `{project-root}/_bmad/_config/bmad-help.csv`
7. Merges `_config/.vscode/settings.json` → `{project-root}/.vscode/settings.json`
8. Appends patterns to `{project-root}/.cursorignore`

**Installed BMAD structure (RBTV touchpoints only):**

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
├── .vscode/settings.json                    # ← merged from _config/.vscode/settings.json
├── .cursorignore                            # ← patterns appended
├── _bmad/
│   ├── _config/bmad-help.csv                # ← RBTV entry added
│   ├── core/config.yaml                     # ← output_folder updated
│   ├── bmm/config.yaml                      # ← output paths updated
│   └── rbtv/                                # ← THIS REPO
│       └── _config/install-rbtv.py          #    the installer script
└── _bmad-output/                            # runtime output folder
```

## Boundaries

- NEVER modify anything under `_docs/system-documentation/BMAD/` — it is read-only reference material.
- Only modify or create files within the RBTV repo itself (everything outside `_docs/system-documentation/BMAD/`).
- `{project-root}` placeholders in RBTV files are runtime-resolved by the BMAD installer. Always preserve them as-is when editing.
