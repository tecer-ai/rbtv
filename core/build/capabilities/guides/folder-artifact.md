# Building a folder artifact

A [folder artifact](../glossary/folder-artifact.md) is a standard file a folder can hold, named after that folder, with one fixed purpose.

## Purpose

It gives one fact a file that agents and programs can find without hunting the folder. Without it, that fact has no standard home. Which kind to add is in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- It holds one fact. A second fact is not stored in it.
- It is not exposed as a [skill](../glossary/skill.md), a [rule](../glossary/rule.md), a [command](../glossary/command.md), or an [agent](../glossary/agent.md).
- Where a file points to it, the pointer names the moment to open it, not only the file ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Before it is opened, an agent sees a name and one line that names the moment or the decide sentence, and no more ([Progressive disclosure](../principles/progressive-disclosure.md)).
- This file is the only home for its fact. No second copy is maintained by hand ([Single source of truth](../principles/single-source-of-truth.md)).
- A proposed new kind states in one line what fails with the existing kinds. If nothing fails, it is not created ([Keep it simple](../principles/kiss.md)).
- A new kind belongs to the component that defines that kind of folder, such as a wiki module defining the folder artifacts of a wiki.
- A folder rename updates the artifact's name in the same change ([Terminology is king](../principles/terminology-is-king.md)).

## Making it good

Give the file one purpose. Write each pointer as the moment to open it. The line seen before opening names that moment, or the sentence that decides, and nothing more. When the folder is renamed, rename the artifact in the same change.
