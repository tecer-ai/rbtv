# Index file

The [folder artifact](folder-artifact.md) `_artifacts/index.md` that lists a folder's content and states when to open each item. It holds the list, never the items' content. Rows are an `| Open | When |` table. The When column is a trigger, never a description of the item.

The folder instructions table lists that folder's `_artifacts/` items. This index lists the rest: subfolders and documents. No item appears in both. It does not list the folder instructions file, `_artifacts/` itself, or this index.

A generated index uses the same table, one row per file, built from each file's description, and is read on demand. It lists every file of its folder and has no row cap. A parent index lists its subfolders, not their files. General memory's always-loaded router is the [memory index](memory-index.md), not this generated form.

Module, component, and tool folders have none: their JSON record, [`<module>.json`](module-json.md), [`<component>.json`](component-json.md), or [`<tool>.json`](tool-json.md), describes them. rbtv's `capabilities/` indexes stay in place. A wiki keeps its own index names, so links by file name keep working.
