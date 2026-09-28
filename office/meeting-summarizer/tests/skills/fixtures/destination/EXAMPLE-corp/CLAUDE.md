# EXAMPLE-Corp — collection scope (fixture)

Fixture stand-in for a destination repo's own collection `CLAUDE.md`. It carries the clause-9
propagation gate, which lives HERE and in neither summarizer skill.

## Entity memory

`memory-EXAMPLE-corp.md` in this folder is the entity's standing record.

## Propagation gate

After a meeting summary is written into this collection, propose every durable fact the summary
established for propagation into `memory-EXAMPLE-corp.md`, as a table:

| # | Fact | Target section | propagate? |
|---|------|----------------|------------|

Present the table and take a per-row decision before appending anything to the entity memory.
A fact is durable when it outlives the meeting: a commitment, an owner of a workstream, a renewal
date, a named system, a decision. Discussion and one-off numbers are not durable.
