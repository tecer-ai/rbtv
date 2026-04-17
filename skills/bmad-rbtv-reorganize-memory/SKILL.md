---
name: bmad-rbtv-reorganize-memory
description: 'Reorganize and maintain the .claude/memory/ knowledge base. Use when user says "reorganize memory" or memory files need cleanup.'
---

# Reorganize Memory Skill

**Purpose:** Execute the 7-step memory maintenance protocol to keep `.claude/memory/` clean, current, and well-organized.

**When to use:**
- User says "reorganize memory"
- Memory files have grown large or contain duplicates
- Index (`memory.md`) is out of sync with actual files

---

## Execution Protocol

Execute these 7 steps in exact order. Report progress after each step.

### Step 1: Read All Memory Files

Read every file under `.claude/memory/` — `memory.md`, `general.md`, all files in `domain/`, and all files in `tools/`. If `.claude/memory/` does not exist or is empty, report that and stop.

### Step 2: Remove Duplicates and Outdated Entries

Scan all entries across all files. Remove:
- Exact duplicate entries (same content in same or different files)
- Entries that are clearly outdated (superseded by later entries, reference removed tools/patterns, or contradict current state)

### Step 3: Merge Related Entries

Combine entries that cover the same topic but were captured at different times. Preserve the most recent date. Keep the merged entry in the most specific applicable file.

### Step 4: Split Overgrown Files

If any single file covers too many unrelated topics (3+ distinct topics in one file), split it into separate files under the appropriate subdirectory (`domain/` or `tools/`).

### Step 5: Re-sort by Date

Within each file, sort entries chronologically (oldest first, newest last).

### Step 6: Update Index

Rewrite `memory.md` to accurately reflect:
- Every file that exists under `.claude/memory/`
- A one-line description of each file's current content
- Remove references to files that no longer exist
- Add references to any new files created during reorganization

### Step 7: Show Summary

Present to the user:

| Metric | Count |
|--------|-------|
| Files read | |
| Duplicates removed | |
| Entries merged | |
| Files split | |
| Entries re-sorted | |
| Index entries updated | |

List any significant changes (files created, files removed, entries deleted) with brief justification.
