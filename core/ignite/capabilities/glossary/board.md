# Board

A board is short-term memory of what matters in one folder, organized by subject, at `_artifacts/board.md`. Established agent, project and area boards use the same four sections. Ignite supplies an agent’s board on every turn, including a scheduled wake; this does not require every workspace folder to have a board.

## Maintain a subject or correction

Keep all four headings in order: What matters now, Watch-outs, Timers, Recently closed. A subject has a unique noun-phrase title, one to three state lines with one fact per line, then Threads, Detail and Flags. Add the relevant thread links yourself, or use `none`; Ignite never invents a thread link. The board points to threads, not the reverse. A wake names the check that fired; keep its details on the board.

Record an owner correction of this agent’s behavior in Watch-outs in the same turn. Follow [Memory](memory.md#record-and-maintain-information) when the correction is also an owner fact. The [Dreamer](dreamer.md) folds supported watch-outs into [Learned rules](learned-rules.md), removing each folded line in the same publication. A refused watch-out still applies during the conversation; report the refusal rather than ignoring the correction.

For an Ignite agent board, use the [checked board operations](../tools/ignite/documentation/runbook.md#write-or-close-a-board-subject). Copy the current board to a candidate, edit subjects or watch-outs, then submit `ignite board write --file <candidate>`. Keep existing Flags, Timers and Recently closed unchanged; a new subject starts with Flags `none`. Use `ignite board close <subject> <outcome> [thread]` to close a subject. Archive old closed entries before closing another when all six slots are occupied; no automatic pruning or truncation occurs.

## Software-maintained content

Ignite generates Timers from its schedule database and updates Flags from owner replies to linked threads. Flags are `answered <date>` or `idle since <date>` after the documented seven-day interval; follow the runbook for timestamps and threads without replies. A schedule without a subject shows `none`. Create timers on the owner’s request and close one when its wake establishes that its goal is met; do not hand-edit the table.

Nothing is closed or deleted because time passed. The dreamer moves detailed subject material into an [Agent topic](agent-topic.md), leaving the board’s detail link and retaining its thread references. Publication checks for concurrent edits. Follow [Agent](../../../rbtv/capabilities/glossary/agent.md) for sharing the board and memory through git.

## Shape and checks

Use this shape for the editable subject; preserve the other sections from the current board:

```markdown
### <unique subject title>
<one to three state lines>
- Threads: <[label](URL) links separated by ·, or none>
- Detail: <Markdown path/link, or none>
- Flags: <existing flags; none for a new subject>
```

A watch-out is one bullet with the correction and provenance `(YYYY-MM-DD · agent[/[label](URL)])`. The checker in [board.js](../tools/ignite/board.js) owns the accepted form: at most 90 nonempty lines outside the Timers table, eight subjects, six watch-outs and six closed entries. Refused writes leave the board unchanged.

In an isolated agent folder, submit a valid update and an over-cap candidate, then close a subject through the command. Check that runtime fields are preserved or refreshed from their sources, the refusal changes no bytes, and closure records the outcome without erasing history.
