# Single source of truth

**Statement.** Each fact, instruction, setting, and operation has one authoritative home that everything else points to, even over the convenience of a local copy.

**Rationale.** Separately kept copies drift apart as soon as one changes, and an agent reading either cannot tell which is current. With one home, every change is a single edit and every reader gets the same answer. A stale copy is context poisoning, and two copies that disagree are cognitive load; either can lead the model to hallucinate ([context window](../glossary/context-window.md)).

**Implications**

- Before writing a fact, instruction, or setting, look for its existing home. If one exists, link to it; do not restate it.
- Keep every text consistent with the home of each fact that it uses. When a text has to state a fact that another file owns in order to be understood, state it as its home states it and link the home. When the two disagree, the home is right: correct the text in the same change.
- When a second cognitive unit or tool needs content that another one holds, move that content to one shared home and point both to it: a [capability](../glossary/capability.md): a document for instructions, a [tool](../glossary/tool.md) for an executable operation.
- Give each operation one implementation. Every way to perform it, whether for a human or an agent, calls that implementation.
- Keep each kind of state, such as installation settings in [`config/`](../glossary/config.md), in one store with one format. Every view or summary of that state reads the store; none is maintained by hand as a second copy.
- When a boundary requires a copy, such as the files the [rbtv command](../glossary/rbtv-command.md) writes for a harness or under `.rbtv/agents/`, change the source and regenerate the copy; never edit the copy.
