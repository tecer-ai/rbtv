# Building with the dreamer

The [dreamer](../glossary/dreamer.md) is the program that writes long-term memory. It is not a file an agent authors.

## Purpose

It turns transcripts into durable memory after the conversation, so a lesson does not depend on a note taken mid-turn. Without it, learned rules and general memory do not update, and a stopped run is silent. Which kind of unit to build is in [Choosing what to build](../choosing-what-to-build.md). Do not build a second writer.

## What good looks like

- One shared run, agents in sequence. Not a writer per agent ([Keep it simple](../principles/keep-it-stupidly-simple.md)).
- The cursor moves only after a durable commit. A failed run does not advance it.
- An over-cap proposal is refused, never truncated ([Deterministic first](../principles/deterministic-first.md)).
- Injected text, recalled text, and the dreamer's own text are not evidence.
- `agent.md` and rbtv source are untouched. A conflict is in the owner's digest, not applied.
- Nothing is deleted. A removed record is archived, with a reason.
- Silence when nothing changed. An alert when a run fails, or when 48 hours pass without a completed run.

## Making it good

Do not invoke it from a turn, and do not edit the files it owns. Change long-term memory by what the transcripts and the inbox show: `ignite remember` for a fact about the owner, a board watch-out for a correction of behaviour. Undo a bad run in git: each run is one commit of general memory plus each agent's memory folder and board.

## Traps

- Treating a single inference as a rule. The owner's correction is enough. An inference needs two separate conversations.
- Editing `agent.md` to "fix" a lesson. A wrong lesson must not rewrite the agent's instructions.
