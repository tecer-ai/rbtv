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
**Status:** Partially Done — Phase 1–2 complete, Phase 3 pending

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

## Phase 3 — Command + Skill Name Collision (pending)

### Root Cause

Claude Code registers both `commands/*.md` and `skills/*/SKILL.md` in the same slash-command picker. When a name exists in both locations, it appears twice. This is independent of the directory-scanning issue fixed in Phases 1–2.

### Affected Names

All 7 duplicates originate in `_config/claude/` (RBTV source config) and are faithfully copied to the installed `.claude/` by the installer:

| Name | `commands/` | `skills/` |
|------|-------------|-----------|
| `bmad-rbtv-create-component` | exists | exists |
| `bmad-rbtv-designer` | exists | exists |
| `bmad-rbtv-doc` | exists | exists |
| `bmad-rbtv-plan` | exists | exists |
| `bmad-rbtv-quality-review` | exists | exists |
| `bmad-rbtv-tone-extraction` | exists | exists |
| `bmad-rbtv-visual-design-extraction` | exists | exists |

### Behavioral Difference: Commands vs. Skills

Commands and skills are NOT functionally identical — removing one changes behavior:

| Aspect | Command (`commands/*.md`) | Skill (`skills/*/SKILL.md`) |
|--------|--------------------------|----------------------------|
| User invocation | `/name` in picker — user explicitly triggers | `/name` in picker — user explicitly triggers |
| AI auto-trigger | Never — commands are user-invoked only | Yes — AI can invoke autonomously based on `description` and "when to use" metadata matching conversation context |
| Metadata | Bare activation wrapper (name + description) | Rich trigger descriptions, "when to use" conditions, purpose statement |
| Format | Single `.md` file | `SKILL.md` inside a named directory |

### Cross-Platform Concern: Cursor

The installer replicates skills to `.cursor/skills/` as a direct 1:1 copy (`workspace_replicate_skills_to_cursor()`). However, Cursor adopted `.cursor/commands/` early as its primary slash-command mechanism. Whether Cursor fully supports `.cursor/skills/` with the same discovery and auto-trigger behavior as Claude Code is unverified. If Cursor does not recognize skills, deleting the command files would make these 7 capabilities invisible in Cursor's picker.

### Fix Decision (not yet resolved)

Three options:

| Option | Action | Trade-off |
|--------|--------|-----------|
| **A: Delete commands** | Remove 7 command files from `_config/claude/commands/` | Eliminates duplicates. Gains AI auto-trigger. Risk: Cursor may lose visibility if it does not support skills. |
| **B: Delete skills** | Remove 7 skill directories from `_config/claude/skills/` | Eliminates duplicates. Preserves explicit-only invocation. Loses AI auto-trigger and rich metadata. |
| **C: Deduplicate per platform** | Keep commands for Cursor, skills for Claude Code. Installer conditionally deploys based on target. | No duplication, no feature loss. Requires installer changes. Most complex. |

### Recommended Test

Before bulk-fixing, test with a single duplicate:

1. Pick one name (e.g. `bmad-rbtv-doc`)
2. Delete `_config/claude/commands/bmad-rbtv-doc.md` from source
3. Re-run installer for both modes (`--mode admin` and default)
4. Test in **Claude Code (terminal):** type `/bmad-rbtv-doc` — verify it appears once and activates correctly
5. Test in **Cursor IDE:** type `/bmad-rbtv-doc` — verify it appears in the picker and activates correctly
6. If both work: proceed with Option A for all 7 duplicates
7. If Cursor fails to discover the skill: restore the command and pursue Option C

---

## Verification

After changes, restart Claude Code and Cursor. Every command must appear exactly once in the command picker.
