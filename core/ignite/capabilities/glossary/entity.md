# Entity

An entity file holds facts and pointers about one person, organization, geographic place or device at `.rbtv/memory/entities/<people|orgs|places|devices>/<slug>.md`. The lowercase filename is its id. Put aliases and nicknames in that file, not in separate files for the same entity. A shared repository is [Workspace memory](workspace-memory.md), not a geographic place.

Read entities on demand through their folder’s [Memory index](memory-index.md) or search. Link the note containing the substance rather than copying it. People and organizations also link the installation’s transcription-glossary entry; that glossary remains the name-transcription authority. Submit owner facts through [Inbox](inbox.md), naming the entity; [Memory](memory.md#record-and-maintain-information) owns writer boundaries.

## Record format

```markdown
---
description: when <work needing this entity>
type: <person | org | place | device>
aliases: [<other names or spellings>]
---
# <Name>

- <relationship or fact>. (<YYYY-MM-DD> · <source>)
- Vault: [<note>](<relative path>)
- Glossary: [<name>](<relative path; people and organizations only>)
```

The type matches the containing kind folder. Resolve links from this file’s own folder. Follow [Memory](memory.md#record-checks) for provenance and counting; the limit is 3,000 characters. The [dreamer checker](../tools/ignite/dreamer.js) checks metadata and records; identity and whether a linked note already holds the detail still require review.

After publication, check that the aliases resolve to one entity, the source-note and glossary links work, and no detail was lost through truncation.
