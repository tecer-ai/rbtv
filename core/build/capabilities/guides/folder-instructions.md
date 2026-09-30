# Building folder instructions

[Folder instructions](../glossary/folder-instructions.md) are meant to reach an agent when it reads or changes files in that folder, and to route it to the right file at that moment.

## Purpose

They carry instructions that apply only while working on files in that folder, and route the agent to the right file then. Without them, that folder's work has no route, or instructions that do not belong there ride on every task. Which kind of unit to build is in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- A task that reads or changes a file here needs this file. A task that does not touch this folder does not.
- Every line is about this folder's own files: it would be false or pointless if the same agent worked in another target folder. A line that would still hold there is a [rule](rule.md). A line true only in one subfolder belongs in that subfolder's file, unless it is a trigger plus a pointer to it.
- Read after each parent file, no line contradicts a parent, and no line is true only if a parent is dropped or ignored. The file stays right if it arrives late, early, or stacked with parent files ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Each pointer names the moment and the target, not a path alone ([Progressive disclosure](../principles/progressive-disclosure.md)).
- A one-line warning for a mistake the agent would make before opening the target may stay; the rest is in the target.
- In the highest folder of a tree, only instructions about that folder's own files, plus pointers. If the folder has an [index file](index-file.md), this file points to it and does not copy its list ([Single source of truth](../principles/single-source-of-truth.md)).
- A step with an exact answer names a [tool](tool.md). The sentence is not the check ([Deterministic first](../principles/deterministic-first.md)).
- The file does not hold a procedure, or text a [skill](skill.md), [command](command.md), or [capability](capability.md) already owns. It points.
- Deleting any line would make the agent wrong on a task this file covers ([Keep it simple](../principles/kiss.md)).
- A file a component ships holds for every target folder it can be installed in: no line assumes what the target folder contains, and every line stays about that folder's files, not the component's own source.
- A shipped line never contradicts or overrides the user's own text beside it in the target; it adds, beside that text, only what holds everywhere.

## Making it good

Write each pointer as the moment plus the target ("before adding a tool, read …"), and check every line by reading it after its parents' files.

## Traps

- The same fact written here and in a parent, a rule, or the file a pointer names, other than a one-line warning.
- A file tree, or a document copied in.
- A generated starter left unedited.
- A hand edit inside a marked section, the installer's or a shipped component's, is lost on the next install. A basis edit with no installer run leaves a generated copy old.
