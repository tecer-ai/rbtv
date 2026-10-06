# Building an entity

An [entity](../glossary/entity.md) is thin facts about one person, organisation, geographic place, or device.

## Purpose

It gives every agent one pointer for that entity, without copying the note that holds the content. Without it, aliases and the relation to the owner are rediscovered, or the note is pasted into the window. Which kind of unit to build is in [Choosing what to build](../choosing-what-to-build.md). Do not add a second file for the same entity.

## What good looks like

- One file per entity. The filename is the id.
- `places/` is geography only. A shared repository is workspace memory, not a place.
- The vault note is linked, not copied ([Single source of truth](../principles/single-source-of-truth.md)).
- People and organisations link to the transcription glossary. They do not replace it.
- The dreamer wrote it. An over-cap write is refused, never truncated.

## Making it good

Use `ignite remember` and name the person, organisation, place, or device. Do not edit the entity file by hand. The dreamer files the inbox line and writes aliases once.

## Traps

- A second file under a nickname. Aliases live on the one file. The filename stays the id.
