# Building a memory index

The [memory index](../glossary/memory-index.md) is the always-loaded router of general memory: one row per folder.

## Purpose

It lets every turn find general memory without listing every file. Without it, the agent opens the wrong folder or the index grows with every daily file. Which kind of unit to build is in [Choosing what to build](<../_under-evaluation/guides/procedure documents/choosing-what-to-build.md>). Do not add a second always-loaded index.

## What good looks like

- One row per folder, plus workstreams. The profile and the inbox are not listed: they are already injected ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Agent topics are not listed.
- A folder added or removed updates this index in the same change. The dreamer does not regenerate it ([Single source of truth](../principles/single-source-of-truth.md)).
- Each When is a trigger, not a description of the folder.
- No file appears both here and in a folder's generated index.

## Making it good

Hand-edit this file only when a general-memory folder is added or removed, in that same change. Do not add a row per file. Do not ask the dreamer to rebuild it. Nested indexes are generated; do not hand-edit those.

## Traps

- Listing profile or inbox "so the agent can find them". They are injected. A row here is a second route.
