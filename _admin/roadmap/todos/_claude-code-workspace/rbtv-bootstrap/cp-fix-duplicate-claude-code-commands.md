---
title: 'Change Point: Fix Duplicate Claude Code Commands'
docType: 'change-point'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted:
  - renamed _config/.claude/ to _config/claude/ (2026-03-13)
  - renamed _admin/.claude/ to _admin/claude/ (2026-03-13)
  - updated install-rbtv.py config_claude and admin_claude paths (2026-03-13)
  - renamed _admin/docs/BMAD-mirror/.claude/ to claude/ (2026-03-15)
  - renamed _admin/docs/BMAD-mirror/.cursor/ to cursor/ (2026-03-15)
  - removed duplicate todo at _claude-code-workspace/ level (2026-03-15)
outputPath: '{project-root}/_bmad/rbtv/_admin/roadmap/todos'
date: '2026-03-13'
yoloMode: false
---

# Fix Duplicate IDE Command Discovery

**Type:** Change Point
**Priority:** High
**Tracker:**
**Status:** Done (2026-03-15)

---

## Problem

Claude Code and Cursor discover slash commands by scanning all `.claude/commands/` and `.cursor/commands/` directories under the workspace root. Multiple directories in the RBTV repo used the dot-prefixed names (`.claude/`, `.cursor/`) for storing source templates and reference snapshots. After the installer deployed files to the root `.claude/` and `.cursor/`, both the source and deployed copies were live — causing commands to appear multiple times in the command picker.

---

## Root Cause

Three locations used the dot-prefixed directory names that IDEs auto-discover:

| Location | Contents | Duplication effect |
|---|---|---|
| `_config/.claude/` | 31 RBTV source templates (commands, rules, agents, skills) | Every RBTV command appeared twice |
| `_admin/.claude/` | 3 admin rules | Rules loaded twice |
| `_admin/docs/BMAD-mirror/.claude/` + `.cursor/` | 150 core BMAD reference commands | Every core BMAD command appeared twice |

---

## Fix Applied

Renamed all non-deployed `.claude/` and `.cursor/` directories to drop the dot prefix. IDEs only scan directories literally named `.claude/` or `.cursor/`, so the renamed directories are invisible to the scanner.

### Phase 1 (2026-03-13)

| From | To | Files | Installer change |
|---|---|---|---|
| `_config/.claude/` | `_config/claude/` | 31 | `config_claude` path in `get_paths()` |
| `_admin/.claude/` | `_admin/claude/` | 3 | `admin_claude` path in `get_paths()` |

### Phase 2 (2026-03-15)

| From | To | Files | Installer change |
|---|---|---|---|
| `_admin/docs/BMAD-mirror/.claude/` | `_admin/docs/BMAD-mirror/claude/` | 75 | None (reference only, not used by installer) |
| `_admin/docs/BMAD-mirror/.cursor/` | `_admin/docs/BMAD-mirror/cursor/` | 75 | None (reference only, not used by installer) |

All renames done with `git mv` to preserve file history.

### Convention

Directories in the RBTV repo that mirror IDE config structure but are NOT the deployed runtime copy MUST use the name WITHOUT the dot prefix (`claude/`, `cursor/`). Only the actual deployed directories at the workspace root use the dot prefix (`.claude/`, `.cursor/`).

---

## Affected Files

- `_config/claude/` — renamed from `_config/.claude/`
- `_admin/claude/` — renamed from `_admin/.claude/`
- `_admin/docs/BMAD-mirror/claude/` — renamed from `_admin/docs/BMAD-mirror/.claude/`
- `_admin/docs/BMAD-mirror/cursor/` — renamed from `_admin/docs/BMAD-mirror/.cursor/`
- `_config/install-rbtv.py` — updated `config_claude` and `admin_claude` paths

---

## Verification

After changes, restart Claude Code and Cursor. Every command must appear exactly once in the command picker.
