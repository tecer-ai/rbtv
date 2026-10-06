# Agent topic

An agent topic is on-demand detail at `<agent>/memory/<slug>.md`: a board subject, repeated procedure or reference needed by that agent. One file holds one topic; its lowercase slug is the id. Owner facts belong in general [Memory](memory.md), and behavioral lessons in [Learned rules](learned-rules.md).

Read a topic through the [Board](board.md) detail link or the agent’s memory index. It is not injected or listed in general memory’s index. For a subject, the dreamer moves detail here, leaves the board link and retains the subject’s thread links. A closed subject keeps its topic with a closing record; archived records stay in `memory/archive/`.

Follow [Memory](memory.md#record-and-maintain-information) for writers and submission. Keep subjects on the board rather than pasting their full topic into every turn.

## Record format

```markdown
---
description: when <work needing this topic>
type: <subject | procedure | reference>
aliases: [<search words>]
---
# <Topic>

Threads: <none or [label](URL) links separated by ·; subject only>

- <fact, step or state>. (<YYYY-MM-DD> · <source>)
```

A subject has exactly one `Threads:` line mirroring the board; omit it for other types. Procedure records may use numbered steps. Add `Closed <YYYY-MM-DD> — <outcome>` as a dated record when the subject closes. Keep provenance as [Memory](memory.md#record-checks) requires. The [dreamer checker](../tools/ignite/dreamer.js) validates type, metadata, thread form and dated records; the limit is 3,000 characters.

Check the published topic and its board link together: detail must remain reachable, threads must agree, and closure must preserve the topic.
