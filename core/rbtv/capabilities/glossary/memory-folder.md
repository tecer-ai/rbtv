# `memory/`

`.rbtv/memory/` holds an installation’s general memory: the facts and pointers Ignite supplies to the installation’s agents, such as the profile, the memory index, the inbox and the knowledge records. Ignite generates and maintains the folder and its layout. A user, component or tool does not design it: add no folder or file kind of your own here.

Put other material in its own home: a component’s settings in [config/](config.md), data a program writes while running in [runtime/](runtime.md), and one agent’s memory in that [agent’s](agent.md) folder.

For the record kinds, their formats and who may write each, follow [Memory](../../../ignite/capabilities/glossary/memory.md), which routes to each record’s entry. Change a record only through the operation its entry names.

Check a file under `.rbtv/memory/` against the record kinds Memory names. A file that is none of them belongs in one of the homes above.
