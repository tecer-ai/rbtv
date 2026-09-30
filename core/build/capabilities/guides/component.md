# Building a component

A [component](../glossary/component.md) is the named folder inside a [module](../glossary/module.md) that groups the [cognitive units](../glossary/cognitive-unit.md) and [capabilities](../glossary/capability.md) for one purpose.

## Purpose

It gives one purpose a home the installer can read. Without that home, those units are not grouped as a component. Whether the purpose needs its own component is in [Choosing what to build](choosing-what-to-build.md#2-choose-a-component).

## What good looks like

- Its purpose fits in one line, and no existing component's stated purpose already covers the new cognitive units and capabilities ([Keep it simple](../principles/kiss.md)).
- Every cognitive unit and capability serves that one purpose. One that does not belongs in a separate component.
- A human and an agent create it by editing the same files and running the [installer](../glossary/rbtv-installer.md). No step needs a control only a human can use ([Agent parity](../principles/agent-parity.md)).
- A rename updates every current file that uses the name, including skills, agent files, and tool paths, not only [`<component>.json`](component-json.md). Decision records stay as written ([Terminology is king](../principles/terminology-is-king.md)).

## Making it good

State the purpose in one line before adding units. If an existing component's purpose already covers them, add them there. A unit that serves a second purpose is a second component. On a rename, update every current file that uses the name in the same change.
