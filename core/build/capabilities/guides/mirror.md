# Building a mirror component

A [mirror component](../glossary/mirror.md) is a component local to this installation, scanned by the [installer](../glossary/rbtv-installer.md) alongside shipped components.

## Purpose

It supplies a component rbtv does not ship, or replaces a shipped component entirely. A partial copy does not patch a shipped one: their files are not merged. Whether the work belongs in a shipped component is in [Choosing what to build](choosing-what-to-build.md#2-choose-a-component).

## What good looks like

- What it holds belongs to this installation only — a personal workflow, an installation-specific value, an experiment, or an imported outside skill. A unit any user could use belongs in rbtv instead ([Choosing what to build](choosing-what-to-build.md#2-choose-a-component)).
- The same module and component name is a deliberate full replacement. Any other name is a new component ([Terminology is king](../principles/terminology-is-king.md)).
- It is not a partial copy meant to patch the shipped component ([Single source of truth](../principles/single-source-of-truth.md)).
- For a replacement, every cognitive unit and capability users of the shipped component rely on is present, or its absence is intentional. The installer checks only that [`<component>.json`](component-json.md) exists.

## Making it good

To add a component rbtv does not ship, use a module and component name no shipped component has. To replace one, use that module and component name and include every unit its users rely on. A file left out is not installed. To stop a replacement, remove that mirror component and run the installer again.

## Traps

- Editing the installed copy instead of the mirror source. The next install overwrites that copy.
