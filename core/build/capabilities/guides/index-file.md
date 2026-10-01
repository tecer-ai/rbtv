# Building an index file

An [index file](../glossary/index-file.md) lists a folder's content and the moment to open each item.

## Purpose

It lets an agent open the one item a task needs, when the folder's items are needed at different moments. Without it, the agent opens the wrong file or all of them. Whether to add one is in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- Rows are an `| Open | When |` table. From the When cell alone, a reviewer can say whether a given task should open that item ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Each item has one row: a link and the moment. Not a summary of its contents. "See X" is not a row.
- The file holds the list only. Each item's content stays in the item ([Single source of truth](../principles/single-source-of-truth.md)).
- `_artifacts/` items are not listed here. Folder instructions list those. No item appears in both ([Single source of truth](../principles/single-source-of-truth.md)).
- After an add, rename, or removal, every covered item is listed once, under its current name, in the same change.
- A generated index lists every file of its folder, one row built from that file's description, and is not hand-edited. It has no row cap.
- A wiki keeps its own index names.

## Making it good

Write When as a trigger: BEFORE, WHEN, ALWAYS, or ONLY. Update the list in the same change that adds, renames, or removes an item. Do not copy the folder-instructions table into this file, and do not copy this list into the folder instructions. For a generated index, change the file's description; do not edit the generated table by hand.
