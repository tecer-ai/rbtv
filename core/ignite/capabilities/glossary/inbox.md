# Inbox

`.rbtv/memory/inbox.md` holds explicit owner requests to remember facts until the [Dreamer](dreamer.md) files them. Ignite supplies it on each turn so another agent can see a new fact before consolidation.

Append one fact in the owner’s meaning in the same turn:

```text
ignite remember <text>
```

The command adds the date, agent and available conversation provenance. It normalizes embedded newlines and never rewrites existing bytes. An agent does not edit or remove inbox lines. Follow [Remember an owner fact](../tools/ignite/documentation/runbook.md#remember-an-owner-fact) for explicit agent/installation arguments, literal option-like text and result fields.

A correction only about this agent’s behavior belongs in [Board](board.md) watch-outs. If it also states an owner fact, use both as [Memory](memory.md#record-and-maintain-information) specifies.

## Stored record and result

```markdown
- <fact to remember> (<YYYY-MM-DD> · <agent or agent/thread link>)
```

A heading is optional; an absent inbox starts as a headerless list. More than 20 bullet lines triggers an owner warning, not a length refusal. Existing malformed content does not prevent an append. Missing text, unresolved installation or a filesystem error can still fail the command.

Check append success separately from warning delivery. If the append succeeded but its alert could not be queued, report the warning without appending the fact again. Repeating the command creates another record.

The dreamer files supported lines into Profile, Knowledge or Entity and removes only what it filed or verified as already known, with provenance preserved. Follow [Memory’s recovery route](memory.md#check-supplied-memory) for a rejected inbox; recovery must preserve unfiled working bytes.

Verify an append through the command in a temporary installation. Confirm that prior bytes remain, the added fact and provenance are present, and crossing the warning threshold does not lose the append.
