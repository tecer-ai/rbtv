# Entry point

An entry point is a skill, a command, a rule or folder instructions. The page "Exposure method"¹⁰ names the same four things. A prompt is not an entry point. An agent is not an entry point. The agent meets a skill when it loads the skill from the description. It meets a command when a human invokes the command. It meets a rule on every task where the rule is installed. The harness reads folder instructions whenever the agent works in the folder. A file of one of the four is an entry point whatever the body contains.

The body sends the reader to other files, carries information of its own, or does both. A body with neither is still an entry point. Outside rbtv, extra files sit in the skill's own folder and are not separate skills. Here a capability is not an entry point. The entry point is the file the agent enters.

The entry point is the file the reader has after that meeting and before any file that it names. It gives what every reading of this file needs, and it names the file that a case needs, so the reader opens that file and not another. An author writes these parts when writing a skill, a command, a rule or folder instructions. Read the page "Folder instructions"¹¹ for what is their own. This page says how the body and the table of any entry point are written. Write an entry point so that a reader who has the file has what every such reading needs. That reader opens the file that the case needs. It does not open a file that the case does not need.

## How it fails

The program can accept the file, and the entry point can still fail. It does not read the body.

- The description names one row's job, or it lists each file the table names. The reader never loads this file for the other rows, or it loads on a word from one file and misses the boundary. Claude Code cuts the skill listing at 1,536 characters, so a list of files can lose the boundary before the reader sees it.
- The body sends the reader to a file that only lists other files, or to another entry point. The match this file made is dropped, and two readers open different files. The program does not read the body. A folder is a load the table may name. A file that only lists other files is not.
- Information that only one case needs sits in the text every reading includes, or the fact that chooses the row sits below the table. Every reading pays for one case, or the reader follows a row that the fact would have ruled out.
- A link to a file, a folder or a capability in a skill or a command is not relative to the source file. A capability in a rule is not a path from the root of the rbtv repository, or from `.rbtv/`. The reader cannot open the file from the place where this entry point is read.
- A row names a skill, a rule, a command or folder instructions. An exposure method sits inside this entry point. The reader loads one method to find another. Read the page "Exposure method"¹⁰ for what those methods are. The rows name capabilities. Read the page "Nested exposure"⁷ when several capabilities share a purpose or the same documents. The program does not read the row.
- A rule's body carries a method that only one task needs. That method is on every task of every agent that has the rule, and the agent follows it on a task it does not cover. The body is present on every task.
- A command's table asks which row, and the description did not name what the human types to distinguish the rows. The agent asks after the invoke for a choice the human could have typed.

## What it is composed of

The author does not write a file named for an entry point. The description, when the kind has one, and the body are parts of the skill, the command, the rule or the folder-instructions file. Read the page "Skill"¹, the page "Rule"², the page "Command"³ or the page "Folder instructions"¹¹ for the file, the folder, and what the load is.

The description is one row, in the form the page "Routing table"⁴ has, and it has no link. A skill, a command and a rule have one. Folder instructions have none: the harness reads the file whenever the agent works in the folder. Each part contains, for a description:

- `CONTAINS:` the information every reading of this file needs, and the jobs the table covers, in words that separate this entry point from another with the same purpose. Not the steps. Not the name of each file.
- `PURPOSE:` what meeting this file is for. When the entry point is a command, this part also names what the human types with the name, including the word that distinguishes the rows, in the words the human types.
- `ALWAYS LOAD WHEN:` the situation for this kind's load that covers every row and the information every reading needs. Not the situation of one row. When the entry point is a rule, the situation is a case in which to install the rule, and that case is the case for the whole body, because the body is on every task once the rule is installed.
- `DO NOT LOAD WHEN:` one similar situation, including a situation that shares a word with one row and is not a job of this entry point. Name the other the reader should load, or name that no load is right.

The body has information of its own, a table, or both. Information of its own is text every reading of this file needs, and that no other file owns. It is absent when no such text exists. The table is absent when this file sends the reader nowhere.

The table is a markdown table, in the form the page "Routing table"⁴ has. The rows name capabilities. A capability is a link. A row may name a folder. The first cell names the file that has the instructions. It does not name a file that only lists other files, and it does not name another entry point. It does not name an exposure method. Read the page "Exposure method"¹⁰. Read the page "Nested exposure"⁷ when several capabilities share a purpose or the same documents and might belong under this one entry point.

When the entry point is a skill or a command, write a link to a file, a folder or a capability relative to the source file. The program tells the agent to read that source file and follow it. When the entry point is a rule and the cell is a capability, write the path from the root of the rbtv repository, or from `.rbtv/`. The author writes that path so the program can derive the path that opens where the rule is placed. Read the page "Rule"² for the copy the agent has. When the entry point is folder instructions, write the link as the page "Folder instructions"¹¹ says.

A row that says to read a file on every reading of this entry point comes before the other rows. Each bracket below is a decision. Do not paste a line that contains a bracket.

```markdown
| File | CONTAINS | PURPOSE | ALWAYS LOAD WHEN |
|---|---|---|---|
| <link to a capability, relative to this source file, or a path from the rbtv repository root or from .rbtv/ when this file is a rule> | <what is in it> | <what that content is for on this load> | <every reading of this file> |
| <the same kind of cell> | <what is in it> | <what that content is for on this load> | <the case> |
```

## How to build it

1. **The missed file, then what this load does.** Find a task where the reader had this file and still missed the file that the case needed. Or the reader opened a file that the case did not need. Or the reader acted without a fact every reading of this file needs. That miss is the failure. The cause is one of three. The body has no place for a fact every reading needs. The body has no place for the file a case needs. The description does not cover a case the table names. The situation is the load. The reader has matched the description, or has the rule on this task, and does not yet have the files that the table would name. Write the purpose from that miss: what the reader has after the load, and which file it opens, so the miss does not happen. An author who starts from the four labels, with the name filled in, writes a description that the program accepts and a load that decides nothing.

2. **Split the text every reading needs from the text one case needs.** The reader reads the body on the load. For a skill or a command, that read happens only after the description matches, and the loader tells the agent to read the source file and follow it, so the whole body is that read. For a rule, read the page "Rule"² for the copy, and the body is on every task. For folder instructions, the harness reads the file whenever the agent works in the folder, so the whole body is that read. Put in the body, before any row, only text every reading needs and that no other file owns. Write that text as the page "Cognitive unit"⁵ says. When another file owns text every reading needs, write a row that says to read it on every reading, and put that row before the other rows. Do not paste the text. When only one case needs it, write a row for that case. When the file sends the reader nowhere, write no table.

   Weak: "The token format is name, value and source."

   Strong: "The token format is in the check page."

   The weak line puts one case's fact in the text every reading includes. A reading that is not a review still pays for it, and the program accepts the file.

3. **Put the fact that chooses the row before the case rows.** The reader uses the first lines to read the rest, and follows a row it can match. A fact that would send the reader to a different row, written below that row, arrives after the reader has followed it. Information of its own comes first. Then the row that says to read a file on every reading. Then the rows for one case.

4. **Write the description so the load covers every row.** Write it as the page "Routing table"⁴ says, and take what the load is from the page "Skill"¹, the page "Rule"² or the page "Command"³. Folder instructions have no description. The harness reads that file whenever the agent works in the folder. Name the jobs the table covers, and the information every reading needs, not each file and not one row's job. The reader decides this load before it has the table. A description that names one row leaves the other rows unloaded. Those files are capabilities, not exposure methods the reader can find without this file. A description that lists the files makes the list that the reader already has as long as the table. Claude Code cuts the skill listing at 1,536 characters, so put the boundary where a cut still leaves it: in `ALWAYS LOAD WHEN:` and `DO NOT LOAD WHEN:`, not after a list of files.

   Weak: `ALWAYS LOAD WHEN: the user asks for a design system`

   Strong: `ALWAYS LOAD WHEN: the job is the project's visual system, a token extraction, or a check of HTML against that system`

   The weak line loads this file for one row. The other rows are never loaded.

5. **Write each row for the load that happens after this file, and write the file cell so it opens.** Write the row as the page "Routing table"⁴ says. The situation is one the reader can match now, with this file and without the target. A page every reading needs has that situation: every reading of this file. A page one case needs names that case, in words that do not require the target. `PURPOSE:` names what the capability is for on this load. It is not an input the reader gives in order to invoke a second exposure method.

   When the entry point is a skill or a command, write the link to the capability relative to the source file. When the entry point is a rule, write the path from the root of the rbtv repository, or from `.rbtv/`. When the entry point is folder instructions, write the link as the page "Folder instructions"¹¹ says. A folder, when a row names one, is a link in the same way.

   Weak: `| [Capabilities](capabilities.md) |`

   Strong: `| [Design tokens](../capabilities/design-tokens.md) |`

   The weak line names a file that only lists other files. The strong line names the file that has the instructions.

6. **Replace a list, and do not name another entry point.** Give each target its own row, as the page "Routing table"⁴ says. When the target is a file that only lists other files, replace the pointer with rows in this file. When several capabilities share a purpose or the same documents, read the page "Nested exposure"⁷ for whether they belong under this one entry point. When the set is too large for one entry point, that page says to write two. A row does not name the other, and it does not name an exposure method. When the target is a capability, read the page "Capability"⁶ so the load stays a read.

7. **When the entry point is a rule, the table is on every task.** Read the page "Rule"² for the copy and for the size of the instructions file. The description does not decide a second load of the body. Keep the body to lines every such task needs. A page only one task needs is a row, not information of its own, and the row stays one line, because the line is on every task. The description's situation is the case for installing the whole body, not the situation of one row.

   Weak: "When the job is a review, check each token against name, value and source."

   Strong: "When the job is a review, read the check page."

   The weak line puts one task's method in the text every task has. The strong line names the page.

8. **When the entry point is a command, the typed words distinguish the rows.** The human invokes before the agent reads the table. Name, in `PURPOSE:` of the description, the word the human types that picks the row, in the words the human types. A question in the table that asks which row asks for what the invoke could have carried. The page "Command"³ says how a command names its inputs. This step adds the word that separates the rows.

   Weak: `PURPOSE: starts the office work`

   Strong: `PURPOSE: starts the office work for the result the person types after the command`

   The weak line leaves the result in the table. The person invokes with nothing that picks a row.

- When you edit: change the description in the same change as a row that adds or removes a job that the description must cover. The description and the table are the same file. A new row whose job the description does not name is never loaded, because a capability is not an exposure method the reader can find without this file.
- When you convert: an outside skill whose folder has extra files becomes information of its own, or rows, not one skill per extra file. A column table in that body becomes the markdown table above. A file that only lists other files becomes rows in this file. When several of those files share a purpose or the same pages, read the page "Nested exposure"⁷. When a part of the outside file is another kind of thing in rbtv, decide that part with the page "Choosing what to build"⁸.
- When you review: read the description and not the body. Name the load it causes for one task of each row, and for one task that shares a word with a row and is not a job of this file. Then read the body. Name a reading that pays for text only one row needs.

Checks:

- A reviewer sees a description that names the jobs the table covers, not one row and not each file. Text every reading needs, and that no other file owns, is in the body before the table. A page every reading needs that another file owns is a row before the other rows. A link to a file, a folder or a capability in a skill or a command is relative to the source file. A capability in a rule is a path from the root of the rbtv repository, or from `.rbtv/`. A rule body has no method that only one task needs.
- The program accepts the file, as the page "rbtv command"⁹ says. Acceptance shows the file was recognized. It does not show that a reader reaches every row, because the program does not read the body.
- Give the description, without the body, to a reader, with one task for each row and one task that shares a word with a row and is not a job of this file. The reader loads on each row's task and not on the other. Then give the body and one task that matches one row. The reader opens that row's file and does not open another row's file.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Skill | [Skill](skill.md) | when | the entry point is a skill | take the file, the folder, and what the load is |
| 2 | Rule | [Rule](rule.md) | when | the entry point is a rule | take the file, the folder, what the load is, the copy, and the size of the instructions file |
| 3 | Command | [Command](command.md) | when | the entry point is a command | take the file, the folder, what the load is, and how a command names its inputs |
| 4 | Routing table | [Routing table](routing-table.md) | must | | write the description and the table in the form, and take what a load is |
| 5 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | when | writing the text every reading needs | write that text, and take what an instruction adds |
| 6 | Capability | [Capability](capability.md) | when | a row names a capability | keep the load a read, and take where that file is written |
| 7 | Nested exposure | [Nested exposure](../nested-exposure.md) | when | several capabilities share a purpose or the same documents, or the set is too large for one entry point | take whether they belong under this one entry point |
| 8 | Choosing what to build | [Choosing what to build](<../_under-evaluation/guides/procedure documents/choosing-what-to-build.md>) | when | a part of a converted file is another kind of thing in rbtv | decide where that part goes |
| 9 | rbtv command | [rbtv command](rbtv-command.md) | when | having the program accept the file | find the command to run, and take what acceptance shows |
| 10 | Exposure method | [Exposure method](exposure-method.md) | when | a row might name a skill, a rule, a command or folder instructions | take that the same four things are the kinds, and a row does not name one |
| 11 | Folder instructions | [Folder instructions](folder-instructions.md) | when | the entry point is folder instructions | take the file, the folder, and the link, and leave what is their own |
