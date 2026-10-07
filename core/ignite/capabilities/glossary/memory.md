# Memory

Memory is information Ignite retains across agent turns. General memory at `.rbtv/memory/` holds facts and pointers shared by the installation’s agents. Agent memory at `<agent>/memory/` holds that agent’s learned behavior and on-demand detail. Keep content in its existing home and link it rather than copying it into memory.

## What a turn receives

Ignite supplies both homes; the agent does not discover a location or request a per-agent grant. Each Ignite turn, including a scheduled wake, receives the [profile](profile.md), that agent’s [learned rules](learned-rules.md) and [board](board.md), the general [memory index](memory-index.md), and the [inbox](inbox.md). [Workspace memory](workspace-memory.md) is supplied only when the working directory matches its declared paths. This is Ignite’s launch contract, not a promise for every harness launch.

Use the index and source links to read [knowledge](knowledge.md), [entities](entity.md), [agent topics](agent-topic.md), [workstreams](workstreams.md), [daily timelines](timeline-daily.md), [weekly timelines](timeline-weekly.md) and nested indexes when needed. Conversations remain in Ignite’s database; do not create a second memory folder of copied conversations.

## Record and maintain information

Use [Inbox](inbox.md) for an explicit request to remember an owner fact. Use the agent’s [Board](board.md) watch-outs for a correction of its behavior, in the same turn. A correction that also states an owner fact belongs in both, with each record serving its own purpose.

The [Dreamer](dreamer.md) writes long-term memory. An agent in conversation must not rewrite the profile, learned rules, topics, knowledge, entities, workspace notes, workstreams or timelines. Follow [Memory index](memory-index.md) for the root index’s separate maintenance convention.

Only a fact with an explicit end date expires; disuse is not expiry. Required record formats and limits belong to each record’s entry. A cap refusal preserves the existing file rather than truncating it.

## Record checks

The [memory checker](../tools/ignite/memory.js) and [dreamer checker](../tools/ignite/dreamer.js) validate their supported records directly. Record entries preserve those formats. Descriptions for selecting skills, rules, commands and agents do not replace record metadata; authored routing tables do not replace the tables software checks. Profile, learned rules and memory indexes begin with a heading and contain no frontmatter or HTML comments; workspace notes use their declared frontmatter.

Keep dated provenance on fact records. New claims cite the supplied owner conversation; filing an inbox line preserves its original provenance, including a bare agent name when no thread link exists. Verified moves preserve existing evidence rather than inventing a new source. The dreamer’s publication checks determine which evidence permits a write.

Character limits count Unicode code points, including frontmatter and line endings; a carriage return and line feed count as two characters. Timeline line limits include headings, metadata and interior blank lines after normalizing line endings and removing trailing whitespace. Each record’s entry states its limit. Over-cap publication leaves the file unchanged and reports the conflict; it does not compress, truncate or split the file to fit.

## Check supplied memory

For a missing or invalid injected file, follow [Turn memory and recovery](../tools/ignite/documentation/runbook.md#turn-memory-and-recovery). Ignite tries a checked committed copy, preserves rejected working bytes, and continues the turn with a visible missing-memory note when recovery is unavailable. Report the missing information; do not invent it or claim that recovery rewrote the working file.

Verify a supported turn’s supplied files and a missing-file case in an isolated installation. Check conditional workspace loading separately. File presence alone does not show that a turn received it.
