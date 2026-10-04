# Building `install.json`

[`install.json`](../glossary/install-json.md) is the record of one installation root: which harnesses receive its files, which units and packs it has, and what rbtv generated in it. Its fields and who changes them are defined in the [glossary entry](../glossary/install-json.md).

## Purpose

rbtv reads it to update or remove what it generated. Without it, an update cannot tell its own files from the author's. The installation root is the only place this file sits; an agent's record is [`agent.json`](agent-json.md), beside its `agent.md`. The file is created by `rbtv configure`, not written by hand.

## What good looks like

- What the installation root has is read from this record; no second list is kept by hand ([Single source of truth](../principles/single-source-of-truth.md)).
- Every change to it comes from an rbtv command: `rbtv configure`, `rbtv add`, or `rbtv remove` ([Agent parity](../principles/agent-parity.md)).
- The record stays on the machine that wrote it. Each machine keeps its own root.

## Making it good

Run `rbtv configure` to create the record, then `rbtv add` or `rbtv remove` to change its units. Run `rbtv update all` to bring the folder back in line with the record.

## Traps

- Editing a record field by hand. Change it with the rbtv command that owns it.
- Expecting `rbtv update all` to keep a unit the record no longer lists. It removes that unit's generated files.
