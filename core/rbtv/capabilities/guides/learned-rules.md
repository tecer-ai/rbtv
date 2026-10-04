# Building learned rules

[Learned rules](../glossary/learned-rules.md) are how one agent must behave, learned from corrections and from repeated experience.

## Purpose

They stop the same correction being needed twice, without letting a wrong lesson rewrite `agent.md`. Without them, a correction lives only on the board until someone edits the prompt. Which kind of unit to build is in [Choosing what to build](<../_under-evaluation/guides/procedure documents/choosing-what-to-build.md>). Do not add a second rules file for the same lessons.

## What good looks like

- The dreamer wrote every line. The agent on a turn did not ([Single source of truth](../principles/single-source-of-truth.md)).
- A correction is `[correction]` and does not wait for a second occurrence. An inference is `[inferred]` and cites two separate conversations.
- One declarative rule per bullet, with `Why:` and dated provenance. A changed rule replaces its bullet.
- At most 30 rules. Over cap is refused, never truncated ([Deterministic first](../principles/deterministic-first.md)).
- No rule restates `agent.md`. A conflict is in the digest, not applied.

## Making it good

Never edit the file by hand. Record the owner's correction as a board watch-out in the same turn. The dreamer folds it on the next run and removes the watch-out in that run. Until then, follow the watch-out. To undo a bad rule, revert the dreamer's commit.

## Traps

- Writing the rule during the conversation. Shipped memory systems studied for this design found notes taken then unreliable, and the talking agent is not the writer.
- Marking a one-off inference as a correction. The owner's word is the correction. One conversation is not evidence for an inference.
