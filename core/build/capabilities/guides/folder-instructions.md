# Building folder instructions

[Folder instructions](../glossary/folder-instructions.md) are meant to reach an agent when it reads or changes files in that folder, and to route it to the right file at that moment.

## Purpose

They carry instructions that apply only while working on files in that folder, and route the agent to the right file then. Without them, that folder's work has no route, or instructions that do not belong there ride on every task. Which kind of unit to build is in [Choosing what to build](choosing-what-to-build.md).

## What good looks like

- A task that reads or changes a file here needs this file. A task that does not touch this folder does not.
- Every line is about this folder's own files: it would be false or pointless if the same agent worked in another target folder. A line that would still hold there is a [rule](rule.md). A line true only in one subfolder belongs in that subfolder's file, unless it is a trigger plus a pointer to it.
- Each pointer names the moment and the target, not a path alone ([Progressive disclosure](../principles/progressive-disclosure.md)).
- A one-line warning for a mistake the agent would make before opening the target may stay; the rest is in the target.
- The `| Open | When |` table lists this folder's `_artifacts/` items, each row a moment: BEFORE, WHEN, ALWAYS, or ONLY. "See X" is not a row. `_artifacts/index.md` lists the folder's other content. No item appears in both ([Single source of truth](../principles/single-source-of-truth.md)).
- Besides the table: one line on what the folder is, the folder's own rules, and one-line tripwires. Facts, state, history, tasks, and full procedures are not copied in ([Progressive disclosure](../principles/progressive-disclosure.md)).
- Read after each parent file, a subfolder's file only adds to them. An override names the parent rule it replaces and its reason. The file stays right if it arrives late, early, or stacked with parent files ([Progressive disclosure](../principles/progressive-disclosure.md)).
- About 150 lines. Longer content is an artifact the table points to.
- A step with an exact answer names a [tool](tool.md). The sentence is not the check ([Deterministic first](../principles/deterministic-first.md)).
- The file does not hold a procedure, or text a [skill](skill.md), [command](command.md), or [capability](capability.md) already owns. It points.
- Deleting any line would make the agent wrong on a task this file covers ([Keep it simple](../principles/kiss.md)).
- A file a component ships holds for every target folder it can be installed in: no line assumes what the target folder contains, and every line stays about that folder's files, not the component's own source.
- A shipped line never contradicts or overrides the user's own text beside it in the target; it adds, beside that text, only what holds everywhere.

## Making it good

Write the table first: one row per `_artifacts/` item, the moment in When. Then one identity line, the folder's rules, and tripwires that start with BEFORE. Point at procedures. Do not copy them. A child file adds. An override names the parent rule and the reason. A write-time rule lives here; a hook only reinforces it, and only fires when the harness was started in this folder. A folder that contains `build/` states that every file there goes in a named subfolder, one per run or topic.

## Traps

- The same fact written here and in a parent, a rule, or the file a pointer names, other than a one-line warning.
- A file tree, or a document copied in.
- A generated starter left unedited.
- A hand edit inside a marked section, rbtv's or a shipped component's, is lost on the next `rbtv update all`. A basis edit with no `rbtv update all` run leaves a generated copy old.
