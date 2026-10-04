# Building a pack

A [pack](../glossary/pack.md) is a named list of units that a component declares, so that one switch adds all of them to an agent or to the installation.

## Purpose

Several agents often need the same group of units. A pack holds that group once, so an agent turns it on with one name instead of listing each unit. Without it, every agent author copies the list, and the copies drift apart. The pack's own file is the only place the group is written. Where declared packs sit is in [rbtv](../rbtv.md).

## What good looks like

- Declared when two or more agents need the same group of units together. A group that one agent needs goes in that agent's own units ([Keep it simple](../principles/kiss.md)).
- Every unit in it is one that each agent turned on the pack needs. A unit only some of them use goes in a second pack, or in the agent's own units ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Its description says what the group is for, in one line.
- Each unit is named by its full id, `<module>/<component>#<unit>`, so the pack reads the same wherever it is shown.
- Its name is unique across the catalog, and it is always named with `--pack`. A bare name is always a unit ([Single source of truth](../principles/single-source-of-truth.md)).

## Making it good

Write the pack's description and its full unit ids. Check the result with `rbtv show --pack NAME`. Then preview its effect on an agent with `rbtv agent add AGENT --pack NAME --dry-run` before turning it on. The Ignite pack is the example: `ignite connect` turns it on for an Ignite agent, and the agent's units are then the pack's units plus its own.

Turning a pack off removes its units, except those the agent lists itself or those of another pack that is on. Expect that when you turn one off.

## Traps

- A pack declared for one agent. Its units belong in that agent's own units.
- A short unit name inside a pack. A short name is accepted on an agent's input only; the pack names every unit in full.
- A unit added to a pack "in case" an agent needs it. Every agent that turns the pack on carries that unit's text into its context window.
