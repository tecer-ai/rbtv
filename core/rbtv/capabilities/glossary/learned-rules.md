# Learned rules

The capped file of how one agent must behave, learned from the owner's corrections and from that agent's repeated experience, at `<agent>/memory/learned.md`. It is not facts about the owner, and it is not `agent.md`. Ignite injects it into every turn of that agent.

The [dreamer](dreamer.md) alone writes it. The agent on a turn never writes it. An owner correction becomes a rule at the dreamer's next run, marked `[correction]`, without needing to be repeated; the board's watch-out covers the gap. A lesson the dreamer infers needs evidence from two separate conversations and is marked `[inferred]`. A conflict with an existing rule or with `agent.md` goes to the owner's digest. The dreamer never edits `agent.md`.

Each rule is one bullet: the marker, the rule, a `Why:` clause, and dated provenance. An inferred rule cites two distinct conversations. A changed rule replaces its bullet. At most 30 rules. An over-cap write is refused, never truncated. No rule expires from disuse. The file is tracked in git, one commit per dreamer run.
