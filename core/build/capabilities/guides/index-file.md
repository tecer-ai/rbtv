# Building an index file

An [index file](../glossary/index-file.md) lists a folder's items and the moment to open each.

## Purpose

It lets an agent open the one item a task needs, when the folder's items are needed at different moments. Without it, the agent opens the wrong file or all of them. Whether to add one is in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- From each line alone, a reviewer can say whether a given task should open that item ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Each item has one line: its name, a link, and the moment to open it. Not a summary of its contents.
- The file holds the list only. Each item's content stays in the item ([Single source of truth](../principles/single-source-of-truth.md)).
- After an add, rename, or removal, every item in the folder is listed once, under its current name.
- If the folder has [folder instructions](folder-instructions.md), they point at this file and do not copy the list ([Single source of truth](../principles/single-source-of-truth.md)).

## Making it good

Write the moment as a when, not a description of the item ("before adding a tool, read …"). Update the list in the same change that adds, renames, or removes an item.
