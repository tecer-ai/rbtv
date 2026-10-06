# Learned rules

`<agent>/memory/learned.md` holds how one agent must behave, learned from owner corrections or repeated experience. Ignite supplies it on every turn of that agent. It is not the agent’s prompt or a store of owner facts.

Record an owner correction as a [Board](board.md) watch-out in the same turn and follow it immediately. The [Dreamer](dreamer.md) folds it into a rule when the required evidence is available; an explicit correction needs no repeat occurrence. An inferred lesson needs two distinct conversations. Mark the two sources of learning differently.

Do not edit the file during a turn or repeat `agent.md` in it. A conflict with the prompt or another learned rule belongs in the owner’s digest. The dreamer never rewrites the prompt to fit a lesson. [Memory](memory.md#record-and-maintain-information) owns publication and correction boundaries.

## Record format

```markdown
# Learned rules — <agent>

- [correction] <rule>. Why: <reason>. (<YYYY-MM-DD> · <agent>/[<thread>](<URL>))
- [inferred] <rule>. Why: <reason>. (<YYYY-MM-DD> · <agent>/[<first thread>](<URL>) · <agent>/[<second thread>](<URL>))
```

Optional subheadings group rules. Each bullet has its marker, one declarative rule, reason and dated provenance. Replace a changed rule instead of adding a conflicting copy. No learned rule expires from disuse.

The [memory checker](../tools/ignite/memory.js) requires at most 30 rules and two distinct links for an inferred rule. The [dreamer checker](../tools/ignite/dreamer.js) additionally verifies that the cited sources are the required owner conversations; distinct links alone do not establish distinct conversations.

After consolidation, check that a folded correction retains its source and date, appears in the next turn, and leaves no duplicate watch-out. A correction without sufficient evidence remains on the board rather than becoming an invented learned rule.
