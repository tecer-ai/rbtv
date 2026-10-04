# Building `install.json`

[`install.json`](../glossary/install-json.md) is the record of one installation root: which harnesses receive its files, which units and packs it has, and what rbtv generated in it.

## Purpose

rbtv reads it to update or remove what it generated. Without it, an update cannot tell its own files from the author's. The installation root is the only place this file sits; an agent's record is [`agent.json`](agent-json.md), beside its `agent.md`. The file is created by `rbtv configure`, not written by hand.

## What good looks like

- What the installation root has is read from this record; no second list is kept by hand ([Single source of truth](../principles/single-source-of-truth.md)).
- Every change to it comes from an rbtv command. A hand edit to `units` or `packs` takes effect at the next `rbtv update all` ([Agent parity](../principles/agent-parity.md)).
- The record stays on the machine that wrote it. Each machine keeps its own root.

## Who writes which field

| Field | Written by | When |
|-------|------------|------|
| harnesses | `rbtv configure` | At creation, and when the owner changes which harnesses receive files. |
| units, packs | `rbtv add`, `rbtv remove` | Whenever the units or packs change. A hand edit is applied by `rbtv update all`. |
| the record of what was generated | rbtv only | At every change. The field list is in the schema. |

The root has no name, description, harness, model, or effort. Those belong to an agent, not to the place where its agents are kept.

## Making it good

Run `rbtv configure` to create the record, then `rbtv add` or `rbtv remove` to change its units. Run `rbtv update all` to bring the folder back in line with the record.

## Traps

- Editing a record field by hand. The next `rbtv update all` rewrites it.
- Expecting `rbtv update all` to keep a unit the record no longer lists. It removes that unit's generated files.
