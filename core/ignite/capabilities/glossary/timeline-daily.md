# Daily timeline

A daily timeline records a day’s owner–agent work at `.rbtv/memory/timeline/daily/<YYYY-MM-DD>.md`. It covers episodes across agents, in the owner’s language that day, and is read on demand. The dreamer writes it; a day without activity needs no file, so absence alone does not establish broken memory.

Link the owner’s periodic note without copying it. Episodes point to their source threads. Durable facts also need their proper home in [Profile](profile.md), [Knowledge](knowledge.md) or [Entity](entity.md); the timeline does not replace that filing. Follow [Memory](memory.md#record-and-maintain-information) to submit or correct information rather than editing the timeline during a turn.

## Record format

```markdown
---
description: when asked what happened on <YYYY-MM-DD>
---
# <YYYY-MM-DD>

Periodic note: [<daily note>](<relative path>)
Week: [<YYYY-Www>](../weekly/<YYYY-Www>.md)

- <episode> — <agent>/[<thread>](<URL>)
```

The filename is a valid date. Resolve the periodic-note link from the daily file’s folder. Each episode occupies one line and cites a thread backed by the run’s owner evidence. The [dreamer checker](../tools/ignite/dreamer.js) validates the form and a 40-line limit; [Memory](memory.md#record-checks) defines the count and refusal behavior.

Check the day, thread links and separate durable-fact destinations after publication. A missing day is not repaired by inventing episodes.
