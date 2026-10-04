# Building a task file

A [task file](../glossary/task-file.md) is the task list a project or area keeps beside its board.

## Purpose

The task tool depends on it. Without it, that tool cannot find the folder's tasks. The board does not replace it. Which kind of unit to build is in [Choosing what to build](<../_under-evaluation/guides/procedure documents/choosing-what-to-build.md>).

## What good looks like

- The name ends in `-tasks.md`, under `_artifacts/`. A plain name fails the task tool ([Deterministic first](../principles/deterministic-first.md)).
- Tasks stay here. The board holds what matters, not the task list ([Single source of truth](../principles/single-source-of-truth.md)).
- The folder instructions point at it with a moment, and the content index does not list it again.

## Making it good

Keep the file where the task tool finds it. Do not rename it to a plain name. Do not merge its tasks into the board. The task tool owns the line shape; do not invent a second one.

## Traps

- Moving it to the folder top so it is "easier to see". The tool matches the ending inside `_artifacts/`. A move hides it from the tool.
