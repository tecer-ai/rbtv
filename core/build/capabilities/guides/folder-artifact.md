# Building a folder artifact

A [folder artifact](../glossary/folder-artifact.md) is a standard file a folder an agent maintains can hold, with one fixed purpose, under `_artifacts/` and a plain name.

## Purpose

It gives one fact a file that agents and programs can find without hunting the folder. Without it, that fact has no standard home. Which kind to add is in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- It lives in `_artifacts/` under a plain name that says its purpose, such as `board.md` or `decisions.md`. The path already names the folder.
- It holds one fact. A second fact is not stored in it.
- It is not exposed as a [skill](../glossary/skill.md), a [rule](../glossary/rule.md), a [command](../glossary/command.md), or an [agent](../glossary/agent.md).
- It is not a substitute for rbtv's `capabilities/` folder. rbtv's JSON records stay beside their folder.
- Where a file points to it, the pointer names the moment to open it, not only the file ([Progressive disclosure](../principles/progressive-disclosure.md)).
- This file is the only home for its fact. No second copy is maintained by hand ([Single source of truth](../principles/single-source-of-truth.md)).
- A proposed kind states in one line what fails with the existing kinds. If nothing fails, it is not created ([Keep it simple](../principles/kiss.md)).
- A wiki keeps its own index names. The task file keeps the `-tasks.md` ending. Every other artifact uses a plain name.

## Making it good

Give the file one purpose and a plain name. Put it in `_artifacts/`. Write each pointer as the moment to open it. Do not put an artifact loose in the folder, and do not hide the folder. An agent's board is `_artifacts/board.md`.
