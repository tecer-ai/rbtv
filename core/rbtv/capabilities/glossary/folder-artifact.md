# Folder artifact

A folder artifact is a file, or a folder, with one purpose. Folder instructions name it so an agent reads it only for the work the purpose serves. Outside rbtv a file in a project is whatever the author stored there. In rbtv the file starts with a section a later agent does not edit, and rbtv does not replace a structure a workspace already has. rbtv proposes a structure of folder artifacts for a workspace that has none of its own. It does not enforce that structure, and this page names no set of files to create.

The artifact keeps a fact, a history, or a rule for adding files out of the folder instructions, so an agent that is doing other work in the folder does not read it. An author wants one when a folder has content only some of the work needs, and the next agent has to keep the purpose. Write a folder artifact so that an agent doing the work the row names reads it, an agent doing other work in the same folder does not, and a later edit adds to it without changing what it is.

## How it fails

No CLI reads a folder artifact. A file with two purposes, or with no first section, is still a file.

- The content is needed on every reading of the folder instructions, and it was put in an artifact. An agent that is searching never reads it, because the row is not that reading. Or the first section is also pasted into the folder instructions. Read the page "Folder instructions"¹ for when that text is a row and when it is in the body.
- The artifact has two purposes, or it has no first section. A later agent adds a log to a file that is not a log, or rewrites the rules, and the next agent follows the rewritten file. Nothing refuses the edit.
- The artifact is a folder, and that folder has no folder instructions. The harness reads nothing for it, and the agent treats its files as ordinary files.
- The artifact is written, and the folder instructions are not changed in the same change. The harness does not read the artifact on its own. The agent never opens it.
- The artifact is given a place this workspace does not use, or a name taken from another installation. The agent looks in a folder that is not there, or a file the workspace already uses is treated as a defect.
- The first section exists only in one folder's copy. The next folder of the same kind gets a different section, and the two stop agreeing.

## What it is composed of

You write a file, or a folder. The path is the path the row in the folder's folder instructions opens. This page does not name a directory every artifact sits in. A file that a CLI reads by a fixed path is a record, not a folder artifact: the CLI finds it without a row.

A file always has a first section. The section says what the artifact is, what it is not, how a later agent adds to it, and that the agent does not edit the section. After that section, the agent adds the records the purpose names. Those records are the form in the artifact's glossary entry.

A folder artifact that is a folder has its own folder instructions. The first section is the start of that file, because every reading of that folder needs those rules. The page "Folder instructions" says what else that file contains. The component's glossary names what the folder contains.

The component that organises this work states the artifact in its glossary, as an entry of its own. The page "Component"² says what a component is. The page "Writing a glossary entry"³ says how that entry is written. Write that entry in the component's glossary, not in rbtv's glossary. A folder artifact is not an exposure method, and it is not an agent. The page "Exposure method"⁸ says what an exposure method is. The rbtv CLI does not install a folder artifact.

## How to build it

1. **The work that does not need this, then what the artifact keeps.** Find a case in which an agent was in the folder and read text it did not need. Or find a case in which it needed a fact and did not find it. The fact was in the folder instructions. The harness reads that file on every reading. Or the fact was in no file a row names. The cause, for a folder artifact, is content that only some work in the folder needs. It sits in the folder instructions, or it sits in no file a row names. Name the work that needs the content, and other work in the same folder that does not. Then write what this artifact keeps, so an agent doing the first work reads it and an agent doing the other work does not. An author who starts from a file name writes a dump, and the row has no situation.

   Weak: "Keeps the approaches already chosen for this folder."

   Strong: "Keeps the approaches already chosen for this folder, so an agent that is choosing an approach reads it, and an agent that is searching for a file name does not."

   The weak line names no work, so the row cannot say when to read the file.

2. **Keep one purpose, and write the first section the later agent does not edit.** Keep one purpose in the file. Read the page "Cognitive unit"⁴ when a second purpose would be another text. An agent that opens this file for one purpose also reads the other, because the row names the file. The first section is not edited later, so that second purpose cannot be split off after the file exists.

   Write the first section before any record. It says what the artifact is, what it is not, how a later agent adds to it, and that the agent does not change the section. Word the first section as the page "Scaffolding language"⁵ says. The rbtv CLI does not fence the section. A later agent that rewrites it changes the purpose, and the next agent follows the new text.

   Weak: "Add a decision after this section, with the date and the file it governs. Do not edit this section."

   Strong: "This file records an approach that has been chosen. It is not a log of attempts. Add a decision after this section, with the date and the file it governs. Do not edit this section."

   The weak line does not say what the file is not, so the next agent appends a transcript.

3. **Choose a file or a folder by whether the records are read on the same work.** Choose a file when the later agent adds every record after one first section, and no record is read on different work from the others. Choose a folder when two records are read on different work, so each needs its own row. One file would make the agent that opened it for one record read the other. A folder has its own folder instructions, as the page "Folder instructions" says, and the first section is the start of that file. A folder with no folder instructions gives the agent no first section: the harness reads nothing that says what the files are.

   Weak: "This is a folder because there are several notes."

   Strong: "The chosen approach and the rejected approach are read on different work, so each is a file in a folder, and each has a row."

   The weak line counts the notes and does not ask which work reads them.

4. **State it in the glossary of the component that organises the work.** That component states the artifact as its own glossary entry, in the same change as the first file. The first section in the file is that entry's section, not a new wording. A section written only in one folder drifts from the next folder of the same kind. Write the entry in that component's glossary, not in rbtv's glossary.

5. **Write the records the purpose names, from that glossary entry.** After the first section, write each record in the form the entry gives. Do not invent a second form in the file. A record the entry does not name is a second purpose, and the agent that opened the file for the first purpose reads it too.

6. **Use the place this workspace already uses. Do not invent one.** When the task names a path, use it. When the workspace already has a place and a name for this purpose, use them. The row's link opens that path. rbtv does not replace a structure a workspace already has. When the workspace has no place for this purpose, do not invent a wrapper folder, and do not take a name from another installation. State the artifact in the component's glossary, and stop and ask the owner for the path.

7. **Add the row in the same change as the file.** Add the row as the page "Routing table"⁶ says, in the same change. The row is in the folder instructions of the folder that contains the artifact, not in the artifact. The harness reads those folder instructions and does not read the artifact until the agent follows the row. The situation is the work you named in the first step, not every reading of the folder instructions. An artifact with no row is never opened. Do not make the artifact a file that only lists other files. The folder instructions table already names those files.

When you edit the rules, change the first section in the glossary entry and in every file of that artifact, in the same change. Change the row with the file it names, as the page "Routing table" says. A later agent follows the section it reads. A change to one copy leaves the others old. The records after the section are the work of that case, not a second source of the rules.

When you convert an outside file, a file that mixes several purposes becomes several artifacts, or one artifact and a row for the rest. The standing rules at the start become the first section. A list of sibling files becomes a row in the folder instructions, not a section of the artifact. When a part is another kind of thing in rbtv, decide it with the page "Choosing what to build"⁷.

When you review, read the first section and not the records. Name the work that should read the file and the work that should not. Then check that the folder instructions have the row, and that the section matches the glossary entry. A review that reads the records first misses a section the next agent can rewrite.

Checks:

- A reviewer sees one purpose, and a first section that says what the artifact is, what it is not, how to add, and that the section is not edited. The records after it match the glossary entry. The folder instructions of the folder that contains it have a row. The situation of the row is the work the purpose names, not every reading of those instructions. A folder artifact that is a folder has folder instructions, and the section is the start of that file. The component's glossary has the entry. The path is a path the task or the workspace already uses, or the path is unset.
- No CLI accepts or refuses a folder artifact. A file that is present shows that it was written. It does not show that an agent in the folder reads it, or that a later agent leaves the first section.
- Give an agent work that should read the artifact, and work that should not, with the folder instructions and without the path said again. Look at whether the first work reads it and leaves the first section, and whether the second work does not read it.

## Template

The layout of a folder artifact that is a file. A folder artifact that is a folder has no separate layout: the first section is the start of its folder instructions, and the page "Folder instructions" has that file's layout. The records follow the glossary entry of this artifact, not a second form.

```markdown
# <what the artifact is>

<What it is. What it is not. How a later agent adds to it. The agent does not edit this section.>

<A record in the form the glossary entry of this artifact gives. A later agent adds these after the section. It does not change the section.>
```

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Folder instructions | [Folder instructions](folder-instructions.md) | when | writing the row, the artifact is a folder, or text every reading needs has another owner | take what each part of the row contains, when that text is a row or in the body, and how that folder's file is built |
| 2 | Component | [Component](component.md) | when | deciding which component's glossary states the artifact | find the component, and its glossary |
| 3 | Writing a glossary entry | [Writing a glossary entry](../writing-a-glossary-entry.md) | when | stating the artifact in the component's glossary | write that entry, including the form of a record |
| 4 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | when | a second purpose would be another text | take when that purpose is another text |
| 5 | Scaffolding language | [Scaffolding language](scaffolding-language.md) | must | | word the first section so the later agent acts on the meaning you gave it |
| 6 | Routing table | [Routing table](routing-table.md) | when | adding the row, or changing the row with the file | take the same change of the row and the file it names |
| 7 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | a part of a converted file is another kind of thing in rbtv | decide where that part goes |
| 8 | Exposure method | [Exposure method](exposure-method.md) | when | deciding whether to expose the artifact as a skill, a rule, a command or folder instructions | take that those are exposure methods, and a folder artifact is not one |
