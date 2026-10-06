# Capability

A capability is a file with a method or with knowledge. An exposure method exposes it, and the agent reads it then. The page "Exposure method"²⁰ says which files those are. A step of a prompt may also send the agent to the file. The page "Prompt"⁴ says how that step names it. Outside rbtv, the nearest file sits in one skill's folder, and that skill's package carries it. In rbtv the file lives in the component's `capabilities/` folder. The program does not install it. The agent reads it in the source when a route names it. More than one route can name the same file. It is not a procedure.

A capability has the work that remains after the route has been followed. That work is not copied into every skill, rule, command, or prompt that needs it. An author wants one when the remaining work has no file yet. The author also wants one when the existing file still fails an agent who arrives with only what the route passed. Write a capability so that an agent, with only what the route passed, does the work that remained.

## How it fails

Acceptance of the component leaves the capability free to fail. The program never reads this file.

- The file repeats the route, or it uses a file, a path, or a fact the route did not pass. The agent does the route's work again, or it searches for what was not passed.
- The file is a list of other files. The agent already followed a route to reach it, so the list is a further choice, and the page for the step stays unread.
- The file opens as a skill would, with a name and a case in which to load it, or it writes the method of the agent's whole work. No harness lists the file. The agent treats the first lines as a load it already made, and the work that remained is never done.
- The file names one caller's task, or a path, an account, a host, or a credential of one installation. A second route, or another installation, follows those names.
- The file has a second job, and the first job's result does not require it. No description can refuse half the file, because the route has already committed to the whole of it. The route that needed one job pays for both.
- A copy of the text sits in the skill, the rule, the command, or the prompt. The next read of this file does not change that copy.

## What it is composed of

One markdown file is what the author writes, under the component's `capabilities/` folder, at `<module>/<component>/capabilities/<name>.md` or in a subfolder of `capabilities/`. The program does not read that file. It has no frontmatter the program checks, and no headings the program requires. The file stays in the source.

A skill or a command reaches the agent as an instruction to read the source of that skill or command. A link in that source opens from the source. The page "Skill"¹ and the page "Command"² say how those routes name this file. When the route is a rule, write the path of this file from the root of the rbtv repository, or from `.rbtv/`. The program derives from that path the path that opens where the rule is placed. The page "Rule"³ says how that route names this file. The page "Routing table"¹⁵ says that a capability cell in a rule's table starts at that root. A prompt is copied only when it is placed as an rbtv agent: the launch reads the copy. Placed as a sub-agent of a harness, the harness file points at the source. The page "Agent"¹⁸ says which file the model is given. The page "Prompt"⁴ says how a step names this file. A link in this file opens from this file's folder, because the program does not copy this file. The page "Folder instructions"⁵ says how a row there names this file.

When the file is a glossary entry, write its parts as the page "Writing a glossary entry"⁶ says, and still write, as the steps below say, what the agent does with what the route passed. Do the same for a principle, as the page "Principle"⁷ says, for a template, as the page "Template"⁸ says, and for a schema, as the page "Schema"⁹ says. When the work is a program under `capabilities/tools/`, write it as the page "Tool"¹⁰ says. Do not write that program as this file. A file that folder instructions send the agent to, in a work folder, is a folder artifact. The page "Folder artifact"¹¹ says what that file is. Supporting files that sit in a self-contained skill's folder stay there. The page "Self-contained skill"¹² says that shape.

## How to build it

1. **The work that remains after the route, then the purpose.** Find the route that will send the agent here. It may be an exposure method, as the page "Exposure method" says, or a step of a prompt. Read that file as the agent meets it. Write what it has passed by the step that names this file, and what it has not passed. The failure is the work that is still wrong at that step. Its cause, for a capability, is a fact, a step, a limit or a next action that the route did not pass and that the agent still needs. The situation is that step, on one task. Add a second route that will name this file, or the same route on a later task, one you are not using as the example. Then write the purpose from that failure. The purpose is the action the agent takes with what the route passed, so the remaining failure stops. Starting from a list of pages, or from a skill's headings, produces a file the program never reads and that corrects nothing.

   Weak: "This page explains how logs are stored."

   Strong: "State which line of the log the next edit must change. If the route named no log, stop and say so."

   The weak line gives the agent no remaining work to stop.

2. **Write the continuation, and put that purpose in the first lines.** Write what the agent does with what the route passed. Do not write the route's row again, and do not write the method of the agent's whole work. That method is a procedure. The page "Prompt" says what a procedure is, and how that section is written. A step of it may send the agent here. This file does not replace the section. Put the purpose in the first lines. The agent has already decided to read the file, and it uses those lines to read the rest. Do not open with a name and a case in which to load the file. No harness lists this file, and the program does not read a description written in it. Word each sentence as the page "Scaffolding language"¹³ says. Write the instructions the agent acts on as the page "Cognitive unit"¹⁴ says. For a capability, the agent already has what the route passed. It does not have what the route did not pass.

   Weak: "Open this page when the task needs a swarm."

   Strong: "Split the problem the route passed into one question per lane."

   The weak line decides a load the route already made, so the continuation never becomes the work.

3. **Use a fact the route passed, or a fact this file owns.** Name each fact the file uses. A fact the route passed is named as passed. A fact this file owns is stated here, and in no other file. A path, an account, a host, or a credential of one installation is neither. It belongs to the settings or to the task. The route passes it, or the agent reads it from the settings at the moment of the step. Do not type it into the file. When a fact the instructions use was not passed, state the next action as the page "Cognitive unit" says. For a capability, the only source of a fact is the route, not the other files of the task. Stop, and name what the route has to pass. Do not search the workspace, and do not take a fact from a file the route did not name.

   Weak: "Write the output under /home/the-owner/project/out."

   Strong: "Write the output in the folder the route names. When the route named no folder, stop and name the folder the route has to pass."

   The weak line types one installation into the file, so another installation follows that path.

4. **Keep one job in this file, so a second route can name it.** Keep the job the failure names, as the page "Cognitive unit" says. The agent reads this file whole once the route has sent it here, and no description can refuse half of it, so every route pays for a second job. A second job is another file under `capabilities/`. Do not paste this text into the file that routed here, as the page "Cognitive unit" says. When you find a page that already has the instructions, the route names that page.

   Weak: "This page covers the swarm and the panel."

   Strong: "This page covers the swarm. The panel is another file."

   The weak line makes every reader do a job it did not come for.

5. **Name the file that has the instructions. Do not make this file a list.** When a step needs another page, name the file that has the instructions. Put the name at the step. The link opens from this file's folder. The program does not copy this file, so the link is from the source. Do not name a file that only lists other files, and do not name an entry point. The page "Entry point"¹⁹ says a row names the file that has the instructions. The agent has already followed a route to this file, so a list in this file leaves the instructions unread. Write the instructions in this file.

   Weak: "See the guides and follow the one that fits."

   Strong: "Before the first edit of a skill, read the page "Skill" from this file."

   The weak line never names the page, so the step cannot be done.

6. **Put the file where the program does not install it.** Write the file under the component's `capabilities/` folder, under a name that says the job. The program does not install that file, and the agent reads it in the source. Do not put it in `skills/`, `rules/`, or `commands/`. A file there is not this file. Do not name the file after its folder. A file named for the folder, such as `capabilities.md` or `glossary.md`, is the index rbtv does not have.

When you edit, change this file in the source. The program does not copy it, so the next read of the source sees the edit. When the edit changes what a route's row says the file contains, or when the route should name it, change that row as the page "Routing table" says. Do not edit a copy that lives in the routing file.

When you convert an outside reference that sits beside one skill, write it here when a route in an rbtv skill, rule, command, or prompt must send the agent to it. An outside reference often teaches the subject, points at a stack of pages, and types a path from one machine. Drop a paragraph the failure does not need, as the page "Cognitive unit" says. Write the continuation from what the route will pass. When one part of the converted file is some other term of rbtv, send that part to the page "Choosing what to build"¹⁶. When the outside file is the supporting file of a self-contained skill, leave it in that skill's folder.

When you review, read the file as the agent meets it, with only what the route passed. Take the route's step, and a second route that names the same file. Report each failure as the page "Cognitive unit" says. If the review's only finding is that the component was accepted, the file was not reviewed.

Checks:

- The lines at the start name the action the agent takes with what the route passed. That action is what stops the remaining failure. Those lines do not name a case in which to load the file.
- Each fact the file uses is one the route passed, or one this file owns. No path, account, host, or credential of one installation is typed in. A fact the route did not pass stops the agent, and the agent names what the route has to pass. That stop does not search.
- The file does one job. It is not a list of other files. A step that needs another page names the file that has the instructions, and the link opens from this file's folder. No copy of the text sits in the file that routes here.
- The file is under the component's `capabilities/` folder, and its name is not the name of that folder. A path in a rule starts at the root of the rbtv repository, or at `.rbtv/`.
- The program does not read the file. A run that accepts the component shows only that the component was found. It says nothing about whether this file does the work. The page "rbtv command"¹⁷ is where that run is described.
- Give the file to an agent that has the route and does not have this file until the route names it. Give one task the route names, one task a second route would name, and one route that passed no file the file uses. Watch whether the agent does the remaining work, what it does about the absent fact, and whether it opens a file the route did not name.

## Template

```markdown
# <the job, in the words the route used>

<The action the agent takes with what the route passed, so the failure that remained does not happen. Name each fact the route passed that this file uses.>

<The continuation of that job. Each fact is one the route passed, or one this file owns. When a fact was not passed, stop and name what the route has to pass. Name the tool when the answer is exact. State what is observed when the agent decides.>

<At the step that needs another page, a link from this file to the file with the instructions. Not a file that only lists other files.>
```

When the file is a glossary entry, a principle, a template, or a schema, use that page's layout in place of this one. What the agent does with what the route passed is still written as the steps above say.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Skill | [Skill](skill.md) | when | the route is a skill | take how that route names this file |
| 2 | Command | [Command](command.md) | when | the route is a command | take how that route names this file |
| 3 | Rule | [Rule](rule.md) | when | the route is a rule | take how that route names this file; the path starts at the rbtv repository root or at `.rbtv/` |
| 4 | Prompt | [Prompt](prompt.md) | when | about to write the method of the agent's whole work, or the route is a step of a prompt | take what a procedure is, and how that step names this file |
| 5 | Folder instructions | [Folder instructions](folder-instructions.md) | when | the route is a row of folder instructions | take how that row names this file |
| 6 | Writing a glossary entry | [Writing a glossary entry](../writing-a-glossary-entry.md) | when | the file is a glossary entry | take its parts, and still write what the agent does with what the route passed, as this page says |
| 7 | Principle | [Principle](principle.md) | when | the file is a principle | take its parts |
| 8 | Template | [Template](template.md) | when | the file is a template | take what a template is |
| 9 | Schema | [Schema](schema.md) | when | the file is a schema | take what a schema is |
| 10 | Tool | [Tool](tool.md) | when | the work is a program under `capabilities/tools/` | take what a tool is, and do not write that program as this file |
| 11 | Folder artifact | [Folder artifact](folder-artifact.md) | when | the file would live in a work folder | take what a folder artifact is |
| 12 | Self-contained skill | [Self-contained skill](self-contained-skill.md) | when | converting a file that sits in a skill folder that is shared as a whole | leave those files in that folder |
| 13 | Scaffolding language | [Scaffolding language](scaffolding-language.md) | must | | apply the wording tests to each sentence |
| 14 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | when | writing the instructions, an absent fact, a tool, one job, a paragraph the failure does not need, or a finding | take those steps, then add only what the route passed and what remains to do |
| 15 | Routing table | [Routing table](routing-table.md) | when | the route is a rule, or a route's row must change with this file | take the path a rule's cell uses, and how to change the row |
| 16 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | one part of a converted file is some other term of rbtv | decide where that part goes |
| 17 | rbtv command | [rbtv command](rbtv-command.md) | when | a run accepts the component | take what that run shows, and what it does not show for this file |
| 18 | Agent | [Agent](agent.md) | when | the route is a step of a prompt | take which placement reads a copy and which placement reads the source |
| 19 | Entry point | [Entry point](entry-point.md) | when | a step is about to name a file that only lists other files, or an entry point | take that a row names the file that has the instructions |
| 20 | Exposure method | [Exposure method](exposure-method.md) | when | naming what exposes a capability | take which files those are, and that an agent is not one |
