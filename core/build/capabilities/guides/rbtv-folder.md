# Building `.rbtv/`

[`.rbtv/`](../glossary/rbtv-folder.md) is the folder the [installer](../glossary/rbtv-installer.md) creates in the target folder and maintains.

## Purpose

It holds this installation's mirror, configuration, installed agents, and runtime data. Without it, that installation has no home for them. It is not hand-written.

## What good looks like

- The only hand-written pieces are [`mirror/`](mirror.md) and each installed agent's agent file and [`settings.json`](settings-json.md). [`config/`](config.md) and the generated files of installed agents match the last install. [`runtime/`](runtime.md) holds only data written while components run; an installed agent's live data stays in its agent folder.
- A human and an agent repair it by running the installer. No step needs a control only a human can use ([Agent parity](../principles/agent-parity.md)).

## Making it good

Run the installer. Add local components only as mirror components. Repair a broken folder by running the installer again.

## Traps

- Editing `config/` or a generated file in an agent folder and expecting the next install to keep those edits. Edit the agent's `agent.md` and run the installer again.
