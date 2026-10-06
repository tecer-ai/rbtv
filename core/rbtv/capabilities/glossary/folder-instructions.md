# Folder instructions

Folder instructions are the file a harness reads into an agent's context for one folder, whenever the agent works in that folder, searches it, or reads a file in it. Outside rbtv the same names, `CLAUDE.md` and `AGENTS.md`, are project instruction files, and authors put procedures in them. Folder instructions are an exposure method and an entry point, whatever the body contains. The page "Exposure method"⁹ and the page "Entry point"¹⁰ name the same four things: a skill, a command, a rule and folder instructions. Each other file is a row of the page "Routing table"¹. The files of the folder and its folder artifacts, as the page "Folder artifact"² says, are rows of that one table, not of two.

The agent did not choose to read this file. The body stops the agent from acting on text only one kind of work needs. A row brings in the file that the work needs. An author wants folder instructions when work on the files in one folder would go wrong without a line that is false in another folder. The same is true when the work needs a route to a file only some of it needs. Write folder instructions so an agent that is only searching does not follow a procedure. An agent that is editing reads the file the row names.

## How it fails

The rbtv CLI can write the file, and the file can still send the agent to the wrong next read. The rbtv CLI does not read the body or the rows.

- The body contains a procedure, a list of names, or a fact that only one kind of work needs. The harness reads that body when the agent is searching and when it is editing. The search follows the procedure, or the edit never reaches the file, because the list named no situation.
- Text that every reading needs is pasted here when another file owns it, or that file has no first row. An agent that is searching reads the paste, or never reads the file.
- The route is two tables, a labeled line, a bare name, an `@` import, or a file that only lists other files. The agent opens the wrong file, or opens none, or the imported file arrives with this file instead of when the row matches.
- The folder has two authored files, an instruction sits in an HTML comment, or a subfolder's file contradicts a parent. One harness reads the line. Another never does.
- A component's section names a file the target folder may not have, or the author edits that section in the target. The next run writes the same body into every installation that has the component, and it overwrites the edit.
- A body line would still be true in another folder. The agent has the line only while it is here, and lacks it in the next folder.

## What it is composed of

You write one file in the folder, under the name this installation maintains. The harnesses read `CLAUDE.md` and `AGENTS.md`. The rbtv CLI writes the other name from yours, and the next run overwrites that copy. You do not write the copy.

Write the body and the table as the page "Entry point" says. The file is an entry point even when that body has no text of its own and the table is absent. One table, when the folder has a file, a subfolder, or a folder artifact that a reading may open, names all of them. A marked section that the rbtv CLI writes is not yours: text outside the markers stays, and the next run overwrites the text between them.

A component that ships instructions for a folder also writes one file in its `folder-instructions/` folder. Set the target folder in the frontmatter. The page "Schema"³ is the authority for that frontmatter, in [folder-instructions.schema.json](../templates/folder-instructions.schema.json). The rbtv CLI removes the frontmatter and writes the body into a marked section of the target folder's file. The agent never sees the frontmatter.

## How to build it

1. **The case the folder went wrong, then what this file does.** Find a case in which an agent was in this folder and the work went wrong. The agent edited a file that does not belong here. The agent searched here for something that lives elsewhere. The agent did the work without the file that the work needed. The cause, for folder instructions, is that the harness read no file into the context, or read a file that contains another kind of work. Name one case in which the agent edits, and one case in which it searches or only reads. Then write what this file does on the next case of that kind, after the harness has read it, so the wrong work does not happen. An author who starts from a list of the folder's files writes a file the rbtv CLI copies and that stops nothing.

   Weak: "After the harness reads it, the agent works in the folder."

   Strong: "After the harness reads it, an agent that is about to add a file stops when the name is a client."

   The weak line names no wrong work, so the lines that follow have nothing to stop.

2. **Put in the body only what this folder adds.** Write the split between every reading and one case as the page "Entry point" says. The harness reads this file when the agent edits, when it searches, and when it only reads. The agent did not choose that read. A line that only one of those needs is a row, because the other two still read a body line, and they do not read a named file until a row matches. Word each body line as the page "Scaffolding language"⁴ says.

   Weak: "When you are about to add a file, a client name does not belong in this folder."

   Strong: "A client name does not belong in this folder."

   The weak line is true of one kind of work, so a search still reads an instruction about adding a file. The row for the decisions file belongs in the table, not in that line.

3. **Read each body line as if the agent were in another folder.** When the line would still be true there, it is not a line of this file. Decide that line with the page "Choosing what to build"⁵. A line that is true only in a subfolder belongs in the file of the subfolder. It may stay here only as a row, and the situation of the row is work in the subfolder. When a body line's answer is a count, a date, or whether a file exists, name the tool that prints the answer, as the page "Cognitive unit"⁶ says. Name that tool only on a line every reading needs. This file is read on a search as well as on an edit.

4. **Write one table, and say what each part contains for this file.** Write the table as the page "Entry point" says, and take the columns from the page "Routing table". One table, not two: the files of the folder, its subfolders, and its folder artifacts are rows of that table. A workspace that already has a file that only lists those names is not a defect this page names.

   For a row of this file, the first cell is a link that opens from this file. A generated copy sits in the same folder, so that link opens from the copy too. An agent is not an exposure method. When a row names an agent, the first cell is the agent's name, as the page "Routing table" says.

   - `CONTAINS` is what is in the named file or folder, in words that separate it from another file in this folder with the same purpose.
   - `PURPOSE` is what that content is for in this folder's work. Not a step of that file.
   - `ALWAYS LOAD WHEN` is a case of being in this folder that the agent can match now, before it has read the named file. Narrow it to editing, searching, or reading. When the row is the one that comes first, the case is that the harness has read this file.
   - A similar case, for this file, is other work in this folder that could open another file of this folder. Write it as the page "Routing table" says.

   An `@` import is not the first cell. Claude Code expands an `@` import when it reads this file into context, so the imported file arrives with this file. Codex and OpenCode do not expand it. Do not add a row for a file the folder does not have, in order to impose a structure. The page "Folder artifact" says that a workspace keeps its own structure. When the first cell is a capability, read the page "Capability"⁷ so the agent reads the page and does not open it as a skill.

   Weak: `ALWAYS LOAD WHEN: the user says decisions`

   Strong: `ALWAYS LOAD WHEN: the agent is choosing an approach for a file in this folder`

   The weak line is not a case of editing, searching, or reading in this folder. The agent cannot match it from the work it is doing here.

5. **Write one file, and write a subfolder's file so a missing subfolder file still leaves the parent right.** Write the one name this installation maintains. When no name is recorded, stop and ask which of `CLAUDE.md` and `AGENTS.md` to write. Do not write both. The rbtv CLI writes the other name from yours and overwrites that copy on the next run. Change the file you author, as the page "Routing table" says for a row and the file it names. The agent sees the other name only after that run.

   Do not put an instruction in an HTML comment. Claude Code strips a block comment before the text reaches the agent. Codex and OpenCode leave the comment in the text.

   A subfolder's file only adds to the files of its parent folders. Do not contradict a parent line. Codex builds its chain once, from the project root down to the folder where the session started, and does not add a file below that folder. A session started above the subfolder never sees the child. Claude Code adds a subfolder's file when it reads a file there, after the parent, and may follow either line when the two contradict. A fact that every session in this tree needs goes in the highest folder whose file those sessions get. Keep that file to the lines every reading needs. Codex stops adding files once their combined size reaches its limit, so a long file in a high folder can keep a lower file out. OpenCode reads `AGENTS.md`, and reads `CLAUDE.md` only when that folder has no `AGENTS.md`. It does not expand a file reference by itself.

   Weak: "The rules for this folder are in CLAUDE.md. Read that file first."

   Strong: "A client name does not belong in this folder."

   The weak line is the whole content of the second file: a harness that reads only that file gets a pointer and none of the lines. The strong line is a line of the one file that you write, which the rbtv CLI copies under the other name.

6. **When a component ships the section, write lines that are true in every installation.** Write the source in the component's `folder-instructions/` folder. Set the target folder in the frontmatter, relative to the installation root. `.` is the root. The rbtv CLI removes the frontmatter and writes the body into a marked section of the target file. The next run overwrites the text between those markers. Edit the source, not the section in the target. Text outside the markers is the author's, and the rbtv CLI leaves it.

   The same body is written into every installation that has the component. Name no file the target may not have. Add no line that contradicts the text outside the section: the agent reads both. Write each link so it opens from the target file, not from the component's source folder, because the body is placed in the target. In an agent's folder the rbtv CLI also writes a marked section that points at the agent's prompt. Write outside it.

   Weak: "Open the roster before any edit in this folder."

   Strong: "Edit the file the installation maintains, not a generated copy."

   The weak line names a file the target may not have, and the rbtv CLI still writes the section into every installation.

When you edit, change the file you author, or the component source, in the same change as a file a row names. The page "Routing table" says to change the row with the file it names. The agent sees a generated copy only after the rbtv CLI has written it again. A change between the markers in the target is lost on that run.

When you convert an outside `CLAUDE.md` or `AGENTS.md`, keep a line that is true on every reading of this folder and that no other file owns. Each other block becomes a row, or a folder artifact the row names. An `@` import becomes a row, not an import. A second harness file is not a second source: keep one, and let the rbtv CLI write the other. When a block is another kind of thing in rbtv, decide it with the page "Choosing what to build".

When you review, read this file as an agent meets it while searching. Read the row before the named file, as the page "Routing table" says. Take an edit that should read a named file. Take an edit that should not. Take a search. Look at whether the search followed a body line it did not need.

Checks:

- A reviewer sees one authored file. The file is an entry point even when the body has no text of its own and the table is absent. Each body line is false in another folder, and true when the agent edits, when it searches, and when it only reads. One table names the files, the subfolders, and the folder artifacts. The first cell of a file, a folder or a capability is a link that opens from this file. When a row names an agent, the first cell is the agent's name. No instruction is in an HTML comment. No route is an `@` import. A subfolder's file adds to its parents and does not contradict them. A component section names no file the target may not have.
- The rbtv CLI accepts a component source when the frontmatter matches its schema, and it writes the other harness name from the file you author. The page "rbtv CLI"⁸ says how to run it. Acceptance shows that the source was recognized and the copy was written. It does not show that an agent in the folder reads the right file, because the rbtv CLI does not read the body or the rows.
- Give the file to an agent on a search, on an edit that should read a named file, and on an edit that should not. Look at whether the search followed a body line it did not need, and whether the edit read the file the row names and not the others.

## Template

The file you author in the folder. Add the column `DO NOT LOAD WHEN` as the page "Routing table" says.

```markdown
# <folder name>

<Text every reading needs, and that no other file owns. Omit when no such text exists.>

| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| [<title>](<path that opens from this file>) | <what is in it> | <what that content is for here> | <the harness has read this file> |
| [<title>](<path that opens from this file>) | <what is in it, apart from another file here with the same purpose> | <what that content is for in this folder> | <editing, searching, or reading here, matched before the named file is read> |
```

The file a component ships, in `folder-instructions/`. The rows use paths that open from the target file.

```markdown
---
target: <target folder, relative to the installation root; . for the root>
---

<the same body, with links that open from the target file>
```

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Routing table | [Routing table](routing-table.md) | when | writing a row | take the table, the first cell, and a similar case |
| 2 | Folder artifact | [Folder artifact](folder-artifact.md) | when | a row names a folder artifact, or you are about to add a row for a file the folder does not have | build that file, and take that a workspace keeps its own structure |
| 3 | Schema | [Schema](schema.md) | when | writing a component source | take the frontmatter the source carries |
| 4 | Scaffolding language | [Scaffolding language](scaffolding-language.md) | must | | word every body line so the agent acts on the meaning you gave it |
| 5 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | a body line would still be true in another folder, or a block of a converted file is another kind of thing in rbtv | decide where that line goes |
| 6 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | when | a body line's answer is a count, a date, or whether a file exists | take how to name the tool that prints the answer |
| 7 | Capability | [Capability](capability.md) | when | the first cell is a capability | take what that read is, so the agent reads the page and does not treat it as a skill |
| 8 | rbtv CLI | [rbtv CLI](rbtv-cli.md) | when | having the rbtv CLI accept a component source, or write the other harness name | find the command to run |
| 9 | Exposure method | [Exposure method](exposure-method.md) | when | the definition of this file | take that folder instructions are one of the four, and an agent is not |
| 10 | Entry point | [Entry point](entry-point.md) | when | the definition of this file, or writing the body or the table | take how that body and table are written, and that the same four things are entry points |
