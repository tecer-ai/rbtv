# Code component rules

This folder is the `code` component of rbtv's `meta` module. It holds the `cli-creator` skill (`skills/`), its CLI user experience capability (`capabilities/cli-ux/`), and the `cli-preview` tool (`capabilities/tools/cli-preview/`). These rules apply to every file in it.

## 1. Written as current

Every file in this component, except `CLAUDE.md` and `AGENTS.md`, describes rbtv 0.2.1 as the current, existing design. It never mentions 0.1 or 0.2, what changed, what was renamed or removed, or why. A decision that compares 0.2.1 with an earlier version belongs in [`core/build/decisions.md`](../../core/build/decisions.md), and only when it is specific to rbtv 0.2.1.

## 2. Raise every inconsistency

When you find an inconsistency in any file of this component while working here, tell the owner, even if it is outside your task. Inconsistencies include contradictions between files, broken links, a term used with two meanings, or text that breaks rule 1. Do not resolve it silently. Report it, and fix it only when the owner agrees.

## 3. Where this folder is going

The `cli-creator` skill is the anticipated migration of rbtv's command-line work into a skill, an early test of how the `core/build` documentation works in use; other cognitive units may follow. Its standard comes from the `rbtv` command-line experience. Every new or edited rbtv command-line tool follows `cli-creator`, and no edit to this component lowers its standards.
