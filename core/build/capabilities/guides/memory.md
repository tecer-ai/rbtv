# Building memory

[Memory](../glossary/memory.md) is general memory, shared by every agent, and agent memory, kept in one agent's folder.

## Purpose

It gives recall the runtime can supply, so an agent does not hunt for a fact it must not miss. Without it, a fact the owner stated has no home that every later turn can see. Which kind of unit to build is in [Choosing what to build](choosing-what-to-build.md). Memory is not one of those units.

## What good looks like

- A fact about the owner is general memory. A lesson about how one agent must behave is that agent's learned rules. The two are not mixed ([Single source of truth](../principles/single-source-of-truth.md)).
- Always-loaded files stay small. Detail is a file opened on demand ([Progressive disclosure](../principles/progressive-disclosure.md)).
- The content's own home is linked, not copied ([Single source of truth](../principles/single-source-of-truth.md)).
- The dreamer wrote every long-term file. The agent on a turn did not.
- A missing or invalid injected file does not block the turn, and the owner is told.

## Making it good

Record a fact about the owner with `ignite-agent remember`. Record a correction of this agent's behaviour on the board in the same turn. Do not edit learned rules, the profile, knowledge, entities, workspace notes, workstreams, timeline files, or topic files by hand. The dreamer files and folds them on its next run.

## Traps

- A note taken during the conversation, written straight into long-term memory. Shipped memory systems studied for this design found those notes unreliable. The transcripts are the evidence. The dreamer writes the lesson.
