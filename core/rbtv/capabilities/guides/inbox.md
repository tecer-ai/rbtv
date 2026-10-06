# Building an inbox line

The [inbox](../glossary/inbox.md) keeps an explicit "remember X" about the owner until the dreamer files it.

## Purpose

It lets every agent see a fact the owner just stated, without an agent rewriting the file that will contain it. Without the append, the next agent asks again, or a rewrite drops another agent's line. Which kind of unit to build is in [Choosing what to build](../choosing-what-to-build.md). Do not build another file of this kind.

## What good looks like

- One fact per line, in the owner's meaning, appended in the same turn.
- A behaviour correction is not stored here unless it is also a fact about the owner.
- The append never refuses, including past 20 lines. Past 20 lines the owner is alerted ([Deterministic first](../principles/deterministic-first.md)).
- No line is rewritten or deleted by the agent on a turn ([Single source of truth](../principles/single-source-of-truth.md)).

## Making it good

Use `ignite remember <text>`. Do not edit the inbox by hand. The dreamer files the line and removes it. If the command warns that the inbox is over 20 lines, the append still stands; say so to the owner.

## Traps

- Rewriting the file in the turn. Appending cannot overwrite; a rewrite can. That is why the command exists.
