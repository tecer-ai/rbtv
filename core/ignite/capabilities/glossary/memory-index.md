# Memory index

The general memory index at `.rbtv/memory/_artifacts/index.md` routes an Ignite turn to on-demand memory. It is always supplied, with one row per general-memory folder and one for [Workstreams](workstreams.md), so daily files do not expand the always-loaded list.

Do not list Profile or Inbox: they are already supplied. Agent topics belong in that agent’s board and memory index, not the general index. Follow [Memory](memory.md) for the distinction between general and agent memory.

## Maintain the root and generated lists

Write the root index when general memory is created. Update it in the same change that adds or removes a general-memory folder; do not ask the dreamer to regenerate it or add one row per file.

Each folder containing memory files has a generated `_artifacts/index.md`, read on demand. A parent lists its subfolders, not their files. Each generated list has one row per file, built from its description; edit that source description rather than the generated table. No file appears in both the root and a folder list. Generated lists have no row cap or frontmatter.

## Record format

```markdown
# Memory index

| Open | When |
|---|---|
| [<folder or workstreams>](<relative path>) | <task condition for opening it> |
```

Use this software-read format for root and generated memory indexes. The [memory checker](../tools/ignite/memory.js) requires `Open | When`, a link in the first cell and a nonempty second cell. The newer authored routing-table format does not replace these columns. Write When as a recognizable reading condition rather than a content summary. Resolve each link from the index’s actual `_artifacts/` folder.

After a folder change, check the root link and generated contents together, then inspect a supported turn’s supplied root index. Keep Profile/Inbox and agent-topic exclusions intact. Record acceptance checks form, not the accuracy of reading conditions.
