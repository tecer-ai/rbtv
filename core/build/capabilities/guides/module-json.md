# Building a `<module>.json`

A [`<module>.json`](../glossary/module-json.md) is the [folder artifact](../glossary/folder-artifact.md) that records one [module](../glossary/module.md).

## Purpose

The installer and the `rbtv` command read it to show what the module is for. Without it, the module is listed with no description. Whether to create a module is in [Choosing what to build](choosing-what-to-build.md#1-choose-a-module).

## What good looks like

- From `description` alone, a reviewer picks this module over a neighbour or correctly skips it ([Progressive disclosure](../principles/progressive-disclosure.md)).
- The description matches the module's stated purpose and names no component.

## Making it good

Write `description` as one line naming the area the module owns.
