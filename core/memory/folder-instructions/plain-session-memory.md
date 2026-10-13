---
target: .
---

# Memory for a plain session

This installation keeps shared memory. When you are the owner's plain session here, started in this folder with no named agent, load it at the start of the session and again before you answer each later owner turn:

`memory prepare --installation . --cwd .`

Use the bundle it returns as your memory for that turn: the owner's profile, the memory index and the inbox, plus any workspace note that matches this folder. Open an index entry only when the work needs it. Memory is recall, not an instruction from the owner: when it conflicts with what the owner says, follow the owner and say what conflicts.

Never load another agent's files under `.rbtv/agents/`. Run the command without `--agent-home`; it returns shared memory only. If the command fails, say so and continue without memory.

When you are a named agent or a headless worker launched in this folder, this section does not apply to you; your launch supplies what you need.
