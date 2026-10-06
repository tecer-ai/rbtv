# Building `config/`

[`config/`](../glossary/config.md) is the one store for the user-specific configuration rbtv and its components need, and for the installation root's record of what rbtv installed.

## Purpose

Installation state and component configuration are read from here. Without it, that state has no store. It is not hand-written.

## What good looks like

- What is installed is read from this folder. No second list is kept by hand ([Single source of truth](../principles/single-source-of-truth.md)).
- A change to installation state is made by the rbtv CLI. The root's units and packs change only through `rbtv add` and `rbtv remove` ([Agent parity](../principles/agent-parity.md)).
- No file here holds a secret: each names the environment variable that holds one.

## Making it good

Change the source of what is installed, then run `rbtv update all`.

## Traps

- Editing a generated field of the record by hand. The next `rbtv update all` rewrites it.
