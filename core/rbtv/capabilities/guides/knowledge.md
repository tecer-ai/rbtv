# Building a knowledge file

A [knowledge](../glossary/knowledge.md) file holds durable knowledge about the owner that should not shape every turn.

## Purpose

It keeps topical facts, preferences, decisions, the self-model, and behaviour-changing health lines where an agent can open them when they matter. Without it, those facts are either injected every turn or lost. Which kind of unit to build is in [Choosing what to build](../choosing-what-to-build.md). Do not add a sixth kind.

## What good looks like

- A fact that should shape nearly every turn is in the profile, not here ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Health lines change how an agent acts and point at the owner's notes. They do not copy the notes ([Single source of truth](../principles/single-source-of-truth.md)).
- A life decision is here. A folder's own decision register is not.
- One fact per bullet, dated. A correction replaces its bullet.
- The dreamer wrote it. An over-cap write is refused, never truncated.

## Making it good

Use `ignite remember` and name the kind of fact. Do not edit the knowledge file by hand. The dreamer files the inbox line. `facts`, `preferences`, and `decisions` are one file each. A write that would pass a file's cap is refused and reported; do not split a file by hand.

## Traps

- Copying a health note into the file. The line is the constraint. The note stays where it is.
