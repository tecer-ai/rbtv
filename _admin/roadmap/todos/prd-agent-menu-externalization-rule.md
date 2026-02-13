---
title: 'Agent Menu Item Externalization Rule'
description: 'Add rule to component pattern standards: agent menu items with non-trivial logic must delegate to external files via exec= or workflow= handlers'
docType: 'prd'
priority: 'Low'
source: 'learnings/mentor-help-mode/L1'
date: '2026-02-13'
---

# Agent Menu Item Externalization Rule

**Type:** Component Pattern Rule Addition
**Priority:** Low
**Status:** Backlog

---

## Problem

PRDs and AI agents default to inline `<action>` blocks for new menu items. This works for trivial operations (exit, simple routing) but creates two problems for non-trivial logic:

1. **Size pressure:** Agent files have a 100-line limit. Each inline action with logic consumes 15-25 lines, leaving less room for future menu items.
2. **Pattern inconsistency:** Existing agents use `exec=` and `workflow=` for complex operations. Inline actions for similar complexity breaks the structural pattern.

Discovered during mentor-help-mode planning: the PRD recommended an inline action for [H] Help. The user corrected this — the correct pattern is `exec=` to an external task file, consistent with existing mentor.md patterns.

---

## Proposed Change

Add rule to `.cursor/rules/admin-rbtv-component-patterns.mdc` under the **Agent Files** section:

| Rule | Requirement |
|------|-------------|
| Menu item delegation | Menu items with logic beyond simple state changes or trivial routing MUST use `exec=` (task file) or `workflow=` (workflow file). Inline `<action>` blocks are reserved for: exit, simple variable set, single-file load-and-follow. |

---

## Acceptance Criteria

- [ ] Rule added to `admin-rbtv-component-patterns.mdc` Agent Files table
- [ ] Rule also added to `_config/.cursor/rules/bmad-rbtv-component-patterns.mdc` (canonical source) if separate
- [ ] Existing agent files (mentor.md, god.md, domcobb.md) comply or violations are documented

---

## Rationale

Codifies a pattern that already exists in practice. Prevents future PRDs from recommending inline actions where external files are the established convention. Low effort — one rule addition to an existing standards file.
