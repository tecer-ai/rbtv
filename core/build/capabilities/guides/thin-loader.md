# Building a thin loader

A [thin loader](../glossary/thin-loader.md) is the installer's pointer from a harness to a [skill](../glossary/skill.md) or [command](../glossary/command.md) in its component.

## Purpose

It lets an agent choose a skill, or a human invoke a command, without copying the body into the harness. Without it, the harness has no pointer to that source. It is not hand-written. A [rule](../glossary/rule.md) does not use one.

## What good looks like

- The skill or command body is only in the component. The loader points at that source and does not copy the body ([Single source of truth](../principles/single-source-of-truth.md)).

## Making it good

Write the skill or command in its component. The installer creates the loader.

## Traps

- Editing the loader by hand. The next install rewrites it.
