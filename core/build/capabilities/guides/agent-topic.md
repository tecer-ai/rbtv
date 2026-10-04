# Building an agent topic

An [agent topic](../glossary/agent-topic.md) is on-demand detail of one agent's memory.

## Purpose

It holds the detail a board subject, a repeated procedure, or a private reference needs, so the board stays short. Without it, that detail stays on the board or is lost when the subject is shortened. Which kind of unit to build is in [Choosing what to build](choosing-what-to-build.md). Do not put owner facts here.

## What good looks like

- One topic, one file. Owner facts are general memory. Rules are learned rules ([Single source of truth](../principles/single-source-of-truth.md)).
- A subject file mirrors the board's thread links, or says none.
- The board keeps a link. The topic does not replace the board entry.
- The file is not injected, and it is not listed in general memory's index ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Closed subjects are kept, with a closing bullet. Nothing is deleted.
- The dreamer wrote it. An over-cap write is refused, never truncated.

## Making it good

Do not create or edit the file by hand. Keep the board entry lean through `ignite-agent board write`. The dreamer moves detail here and leaves the detail link. To undo a bad move, revert the dreamer's commit.

## Traps

- Pasting the topic into the board to "make sure it is seen". The board is injected every turn. The topic is opened when the subject needs it.
