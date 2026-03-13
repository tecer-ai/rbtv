---
title: 'Change Point: Fix Duplicate Claude Code Commands'
docType: 'change-point'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted:
  - renamed _config/.claude/ to _config/claude/ (2026-03-13)
  - updated install-rbtv.py config_claude path
outputPath: '{project-root}/_bmad/rbtv/_admin/roadmap/todos'
date: '2026-03-13'
yoloMode: false
---

# Fix Duplicate Claude Code Commands

**Type:** Change Point
**Priority:** High
**Tracker:**
**Status:** Done (committed 2026-03-13)

---

## Problem

Claude Code discovers slash commands by scanning all `.claude/commands/` directories under the project root. The RBTV repo stored its canonical command sources at `_config/.claude/commands/`, which is a `.claude/commands/` path inside the workspace. After the installer copied these files to the root `.claude/commands/`, both locations were live — causing every RBTV command to appear twice in the Claude Code command picker.

---

## Root Cause

The canonical source directory `_config/.claude/` used the same name (`.claude/`) that Claude Code uses for command discovery. Claude Code found both:
- `{workspace}/.claude/commands/` — deployed by installer (correct)
- `{workspace}/_bmad/rbtv/_config/.claude/commands/` — source files (duplicate)

---

## Fix Applied

Renamed `_config/.claude/` → `_config/claude/` in the RBTV git repo. Claude Code only discovers directories literally named `.claude/`, so the renamed directory is invisible to the command scanner.

Updated `install-rbtv.py` `get_paths()`:
```python
# Before
"config_claude": script_dir / ".claude",
# After
"config_claude": script_dir / "claude",
```

All 31 source files renamed with full git history preserved (`git mv`).

---

## Affected Files

- `_config/claude/` — renamed from `_config/.claude/` (31 files, history preserved)
- `_config/install-rbtv.py` — updated `config_claude` path

---

## Verification

After running installer, `/doc` and other RBTV commands should appear exactly once in Claude Code command picker. Restart Claude Code after install to confirm.
