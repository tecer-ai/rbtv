# Building a mirror component

A [mirror component](../glossary/mirror.md) is a component local to this installation, scanned by the [rbtv](../glossary/rbtv-cli.md) alongside shipped components. The mirror also contains [self-contained skills](../glossary/self-contained-skill.md) in `_skills/`; use the [self-contained skill guide](self-contained-skill.md) when importing or writing one to share.

## Purpose

It supplies a component rbtv does not ship, or replaces a shipped component entirely. A partial copy does not patch a shipped one: their files are not merged. Whether the work belongs in a shipped component is in [Choosing what to build](../choosing-what-to-build.md).

## What good looks like

- A mirror component contains what belongs to this installation only: a personal workflow, an installation-specific value, or an experiment. A generally useful rbtv-format unit belongs in the rbtv repository; a shareable standard skill belongs in the mirror as a [self-contained skill](../glossary/self-contained-skill.md) ([Choosing what to build](../choosing-what-to-build.md)).
- The same module and component name is a deliberate full replacement. Any other name is a new component ([Terminology is king](../principles/terminology-is-king.md)).
- It is not a partial copy meant to patch the shipped component ([Single source of truth](../principles/single-source-of-truth.md)).
- For a replacement, every cognitive unit and capability users of the shipped component rely on is present, or its absence is intentional. rbtv checks only that [`<component>.json`](../glossary/component-json.md) exists.

## Making it good

To add a component rbtv does not ship, use a module and component name no shipped component has. To replace one, use that module and component name and include every unit its users rely on. A file left out is not installed. To stop a replacement, remove that mirror component, then run `rbtv update all`. Where the mirror is kept is in [mirror](../glossary/mirror.md).

## Traps

- Editing the installed copy instead of the mirror source. The next `rbtv update all` overwrites that copy.
