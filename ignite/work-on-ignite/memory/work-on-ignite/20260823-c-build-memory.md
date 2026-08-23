# 20260823-c-build-memory — ignite build memory

kind: creation
component: work-on-ignite
date: 2026-08-23

## What it is
The ignite build memory: per-component issue and creation logs under `ignite/work-on-ignite/memory/`, plus this folder's reference (`work-on-ignite.md`), 3-line pointers, and body templates. Replaces the planned per-component `HISTORY.md` mechanism.

## Why
Ten days of patch-by-patch fixes kept resurfacing defects. The loop turned around only when agents read git history, then `fix-inventory.csv`, then seeded each batch into the next. Memory makes that structural: every ignite-editing session reads closed craft before it edits and files after.

## How to use & where wired
Read `ignite/work-on-ignite/work-on-ignite.md`. Before editing a component: its `_summary.md` + live indexes, then `rbtv embed-search query` over `memory/` (ladder semantic → keyword → grep). After a fix or creation: `file-issue memory file`. Wired here (`CLAUDE.md` / `AGENTS.md` point at the reference); `skill/` (not yet written) says when. Distillation is `goal-memory-management`.

## commit
pending

## deployed
no

## pin
NONE

## ATTENTION
- Open items stay in the goal's issues.md / loose-ends.md; memory holds only closed issues and filed creations.
- Indexes are append-only and newest-last; never rewrite a live index or entry by hand — the filing command writes them.
- Cite consulted entry ids (filenames) in the proposal and the commit message.
