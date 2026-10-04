# Building `agent.json`

[`agent.json`](../glossary/agent-json.md) is an rbtv agent's record: its description, its harness, model, and effort, the units and packs it chose, and what rbtv generated for it. Its fields and who changes them are defined in the [glossary entry](../glossary/agent-json.md).

## Purpose

It is the one file that says what an agent is set up with. The author writes what the agent is; rbtv writes the record of what it generated, so that a second machine can pull the agent's folder and run `rbtv agent update` to get the same files. Without it, the agent's harness, model, and units would live in several files that drift apart.

## What good looks like

- The file holds nothing tied to one machine: no absolute path, no timestamp, no account. It is shared through git, so another machine reads the same file ([Single source of truth](../principles/single-source-of-truth.md)).
- Each field has one writer. No other file of the agent repeats the harness, model, or effort ([Single source of truth](../principles/single-source-of-truth.md)).
- Whoever chose the harness, model, and effort chose each value; none came from a default that nobody chose.
- Its name matches its folder name and the name in `agent.md`. A disagreement is refused before any change.

## Making it good

Write the author's fields first, with the description as one line that tells a caller when to choose this agent. Check the harness, model, and effort with `cast list`. Then run `rbtv agent add AGENT`, and read the record it adds.

## Traps

- An absolute path or a timestamp in the file. A second machine reads it wrongly, and git shows a change on every run.
- Changing harness, model, or effort by hand after creation. `rbtv agent configure` is the command that changes them and regenerates affected files.
- A name that differs between the folder, `agent.md`, and `agent.json`. The command refuses every change until they agree.
