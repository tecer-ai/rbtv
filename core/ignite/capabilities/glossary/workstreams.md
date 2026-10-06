# Workstreams

`.rbtv/memory/workstreams.md` maps active projects, areas and agent-board subjects to their locations. Each project or area has one line linking its folder and its board, or stating `board: none`. An agent subject names the agent and links its board. Keep progress and detail on the [Board](board.md), not copied into this map. Read it on demand through [Memory index](memory-index.md).

The dreamer updates the map when the underlying project is archived or subject closes, recording removals in its publication. Follow [Memory](memory.md#record-and-maintain-information) for writer boundaries. Do not delete active lines to reduce its size.

## Record format

```markdown
---
description: when planning or looking across active work
---
# Workstreams

## Projects
- [<name>](<folder link>) · [board](<board link>)

## Areas
- [<name>](<folder link>) · board: none

## Agent subjects
- <subject> — <agent> · [board](<board link>)
```

Resolve relative links from `.rbtv/memory/`. Each line ends in a board link or `board: none`, as the [dreamer checker](../tools/ignite/dreamer.js) requires. More than 60 nonempty lines produces a digest warning for owner review; length does not refuse the map, though malformed records can still be refused.

After a closure or archive is consolidated, check that the map removes the right pointer, preserves other active work and contains no copied state. If it exceeds the warning threshold, review its contents with the owner rather than truncating it.
