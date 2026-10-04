# Building `.rbtv/`

[`.rbtv/`](../glossary/rbtv-folder.md) is the folder the [rbtv command](../glossary/rbtv-command.md) creates in the installation root and maintains.

## Purpose

It holds this installation's mirror, configuration, agents found by name, and runtime data. Without it, that installation has no home for them. It is not hand-written.

## What good looks like

- The only hand-written pieces are [`mirror/`](mirror.md) and each agent's `agent.md`, [`agent.json`](agent-json.md), and [`settings.json`](settings-json.md). [`config/`](config.md) and the generated files of each agent match the last `rbtv` run. [`runtime/`](runtime.md) holds only data written while components run; an agent's live data stays in its agent folder.
- A human and an agent repair it by running rbtv. No step needs a control only a human can use ([Agent parity](../principles/agent-parity.md)).

## Making it good

Run `rbtv update all` once the record exists ([install.json](../glossary/install-json.md)). Add local components only as mirror components. Repair a broken folder by running `rbtv update all` again.

## Traps

- Editing `config/` or a generated file in an agent folder and expecting the next update to keep those edits. Edit the agent's `agent.md` or `agent.json`, and run `rbtv agent update AGENT all`.
