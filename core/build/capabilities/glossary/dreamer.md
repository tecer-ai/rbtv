# Dreamer

The one shared program that writes long-term [memory](memory.md). It runs nightly and goes through the agents one at a time. It reads conversation transcripts past a cursor that moves only forward, and only after a durable write. It does not learn from boards, from text that was injected or recalled, or from text it wrote itself.

The model proposes add, supersede, or archive. Deterministic code checks each proposal and applies it: an over-cap change is refused, never truncated; a file changed since it was read is not overwritten; no record disappears without a reason. It archives, never deletes. It never edits `agent.md` and never edits rbtv source. A conflict with an agent's instructions goes to a digest for the owner. It stays silent when nothing changed. A failure alerts the owner. The owner is alerted when it has not completed a run in 48 hours.

An owner correction becomes a [learned rule](learned-rules.md) at the next run, without needing to be repeated. Until then the board's watch-out covers it. A lesson it infers on its own needs evidence from two separate conversations. It files inbox lines into their place and removes only the lines it filed, and only if the inbox is unchanged since it was read. It commits general memory, each agent's `memory/` folder, and each agent's board once per run, so a bad change can be undone in git.

The agent on a turn does not run the dreamer and does not write the files the dreamer owns.
