# Building `install.json`

[`install.json`](../glossary/install-json.md) is the installer's record of what it installed in one target folder.

## Purpose

The installer reads it to update or remove what it installed. Without it, an update cannot tell its own files from the author's. It is not hand-written.

## What good looks like

- What is installed in the target folder, including an agent folder, is read from this record; no second list is kept by hand ([Single source of truth](../principles/single-source-of-truth.md)).
- Every change to it comes from running the installer ([Agent parity](../principles/agent-parity.md)).
