# Board

A board is short-term memory of what matters in one folder, organized by subject, at `_artifacts/board.md`. Established agent, project and area boards use the same four sections. Ignite supplies an agent’s board on every turn, including a scheduled wake; this does not require every workspace folder to have a board.

## Maintain a subject or correction

Keep all four headings in order: What matters now, Watch-outs, Timers, Recently closed. A subject has a unique noun-phrase title, one to three state lines with one fact per line, then Threads, Detail and Flags. Add the relevant thread links yourself, or use `none`; Ignite never invents a thread link. The board points to threads, not the reverse. A wake names the check that fired; keep its details on the board.

Record an owner correction of this agent’s behavior in Watch-outs in the same turn. Follow [Memory](memory.md#record-and-maintain-information) when the correction is also an owner fact. Albert folds supported watch-outs into [Learned rules](learned-rules.md). A correction is never dropped for size. A refused watch-out still applies during the conversation; report the refusal rather than ignoring the correction.

The file `_artifacts/board.md` is the one complete canonical board. Capture does not refuse a seventh watch-out, subject or closed line. Identical watch-out lines are still refused. There is no six-item board quota.

For an Ignite agent board, use the checked board operations. `ignite board write -h` owns the write. Copy the current board to a candidate, edit subjects or watch-outs, then submit `ignite board write --file <candidate>`. When the caller has a revision from the checked read, send `--revision`. A stale revision is refused and the file is not written. Keep existing Flags, Timers and Recently closed unchanged; a new subject starts with Flags `none`. Use `ignite board close <subject> <outcome> [thread]` to close a subject. Nothing is pruned or truncated because a count was reached.

## Software-maintained content

Ignite generates Timers from its schedule database and updates Flags from owner replies to linked threads. Flags are `answered <date>` or `idle since <date>` after the documented seven-day interval; follow the runbook for timestamps and threads without replies. A schedule without a subject shows `none`. Create timers on the owner’s request and close one when its wake establishes that its goal is met; do not hand-edit the table.

Nothing is closed or deleted because time passed. Detail that does not stay on the board moves to an [Agent topic](agent-topic.md), leaving the board’s detail link and retaining its thread references. Publication checks for concurrent edits. Follow [Agent](../../../rbtv/capabilities/glossary/agent.md) for sharing the board and memory through git.

The startup view is derived. It is not a second board and it is not saved. It starts `Board view`, holds at most 6,000 Unicode code points, keeps whole entries, and names each omission with a route to the complete section. An omitted watch-out is mandatory to read before acting: `memory board read --file <canonical> --section Watch-outs`. Read the canonical file before editing. Never write the excerpt back. `memory board view -h` prints the derived text. `memory board read -h` prints the revision of the canonical file.

## Shape and checks

Use this shape for the editable subject; preserve the other sections from the current board:

```markdown
### <unique subject title>
<one to three state lines>
- Threads: <[label](URL) links separated by ·, or none>
- Detail: <Markdown path/link, or none>
- Flags: <existing flags; none for a new subject>
```

A watch-out is one bullet with the correction and provenance `(YYYY-MM-DD · agent[/[label](URL)])`. The checker in [board.js](../../../memory/capabilities/tools/memory/lib/board.js) owns the accepted form: four headings, unique watch-out lines, and the subject shape above. It does not refuse a seventh watch-out, subject or closed line. Refused writes leave the board unchanged. A write that sends a stale revision leaves the file unchanged.

In an isolated agent folder, submit a valid update and a candidate with a seventh watch-out, then close a subject through the command. Check that the seventh line is kept, runtime fields are preserved or refreshed from their sources, a stale revision changes no bytes, and closure records the outcome without erasing history. Confirm the derived view stays within 6,000 Unicode code points and names an omitted watch-out with the read command.
