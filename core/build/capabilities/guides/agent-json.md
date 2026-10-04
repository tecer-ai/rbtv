# Building `agent.json`

[`agent.json`](../glossary/agent-json.md) is an rbtv agent's record: its description, its harness, model, and effort, the units and packs it chose, and what rbtv generated for it.

## Purpose

It is the one file that says what an agent is set up with. The author writes what the agent is; rbtv writes the record of what it generated, so that a second machine can pull the agent's folder and run `rbtv agent update` to get the same files. Without it, the agent's harness, model, and units would live in several files that drift apart. Its shape is in [`agent-json.schema.json`](../templates/agent-json.schema.json).

## What good looks like

- The file holds nothing tied to one machine: no absolute path, no timestamp, no account. It is shared through git, so another machine reads the same file ([Single source of truth](../principles/single-source-of-truth.md)).
- Each field has one writer, shown below. No other file of the agent repeats the harness, model, or effort ([Single source of truth](../principles/single-source-of-truth.md)).
- Whoever chose the harness, model, and effort chose each value; none came from a default that nobody chose.
- Its name matches its folder name and the name in `agent.md`. A disagreement is refused before any change.

## Who writes which field

| Field | Written by | When |
|-------|------------|------|
| name | author | At creation. Must equal the folder name and the name in `agent.md`. |
| description | author | At creation, and by hand afterwards. |
| harness, model, effort | author | At creation. Afterwards only `rbtv agent configure`, which checks them against `cast list`. |
| voice | `rbtv agent configure` | Optional. Not checked. |
| units | author | At creation: full ids, or a short name when it is unique in the catalog. Afterwards `rbtv agent add` and `rbtv agent remove`. |
| packs | author | At creation. Afterwards `rbtv agent add --pack` and `rbtv agent remove --pack`. |
| the record of what was generated | rbtv only | At every `rbtv agent add`, `update`, and `configure`. The field list is in the schema. |

A hand-written file needs only the author's fields. The first `rbtv agent add` adds the record.

A hand edit to `units` or `packs` takes effect when `rbtv agent update AGENT scaffolding` runs, the same as a change that arrived by `git pull`. `rbtv agent add` and `rbtv agent remove` make the same change and check it first, so prefer them.

## Making it good

Write the author's fields first, with the description as one line that tells a caller when to choose this agent. Check the harness, model, and effort with `cast list`. Then run `rbtv agent add AGENT`, and read the record it adds.

## Traps

- An absolute path or a timestamp in the file. A second machine reads it wrongly, and git shows a change on every run.
- Changing harness, model, or effort by hand. The generated files keep the old harness until `rbtv agent configure` regenerates them.
- Editing a record field by hand. The next `rbtv agent update` rewrites it.
- A name that differs between the folder, `agent.md`, and `agent.json`. The command refuses every change until they agree.
