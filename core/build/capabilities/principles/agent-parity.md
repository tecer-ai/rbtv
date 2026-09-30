# Agent parity

**Statement.** Every action a human can take on state that software manages, an agent can take too, reaching the same operations through an interface made for agents, even over the speed of shipping a control only humans can use.

**Rationale.** An action only a human can take makes agents wait on a human, and an agent action with no repeatable form cannot be checked or run again. An agent driving the human interface, such as clicking through screens in a browser, is slow and hard to check. When both reach the same operations through their own interfaces, either can do the work and the results match. An agent driving a human interface fills its [context window](../glossary/context-window.md) with screens the task does not need (context load), and an action with no repeatable form must be pieced together again each time (context gap), which invites hallucination.

**Implications**

- When you build software that humans and agents both use, give each action one operation and let each reach it through its own interface: a screen or guided flow for the human, a repeatable form for the agent, such as a command that runs without asking questions. Both interfaces call the same operation, as [Single source of truth](single-source-of-truth.md) requires; a second implementation is not parity. The [installer](../glossary/rbtv-installer.md) has this shape: its guided flow and its non-interactive commands perform the same install operation.
- Let an agent take every action a human can take on the state rbtv manages, meaning components, agents, settings, runtime data, memory, and folder artifacts: by editing the same file, or through a [tool](../glossary/tool.md) when the action is more than a file edit, such as installing. A human control for the same action calls that tool.
- Treat a control only humans can use, such as a graphical-only action, as a stated exception that agents reach through computer use. Never make it the normal route.
