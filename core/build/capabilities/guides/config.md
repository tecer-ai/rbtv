# Building `config/`

[`config/`](../glossary/config.md) is the one store for the user-specific configuration rbtv and its components need, and for the record of what the installer installed.

## Purpose

Installation state and component configuration are read from here. Without it, that state has no store. It is not hand-written.

## What good looks like

- What is installed is read from this folder. No second list is kept by hand ([Single source of truth](../principles/single-source-of-truth.md)).
- A change to installation state is made by running the installer, not by editing the record ([Agent parity](../principles/agent-parity.md)).
- No file here holds a secret: each names the environment variable that holds one.

## Making it good

Change the source of what is installed, then run the installer again.

## Traps

- Editing the record by hand. The next install overwrites it.
