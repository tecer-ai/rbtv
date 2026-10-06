# Skill

A skill, in rbtv, is a cognitive unit the agent opens when its description matches the task, and whose instructions the agent reads only after that open. Outside rbtv a skill is a folder, and the harness reads the instructions from a file in that folder, together with any file beside it. In rbtv the author writes one file, `skills/<name>.md`. The page "Component"¹ says which folder has it. The program writes a pointer: the file that the harness lists as the skill. The pointer has the name and the description, and it tells the agent to read the source file. The program does not copy the instructions into the pointer, and the folder that has the pointer has no other file.

A skill is for instructions the agent needs on some tasks and must not carry on the others. The agent decides the open from the description. The person does not choose the skill by typing its name. An author wants one when that work comes out wrong because those instructions were not in the task, and having them in front of the agent on every task would put them on a task that is not this work. Open this page only after the page "Choosing what to build"² has settled that the cognitive unit is a skill. Write a skill so that an agent with only the description opens it on the task that needs it, and leaves it closed on the similar task. After the open, the agent does the work that the failure names.

## How it fails

The program can accept a skill, and the skill can still fail, because the program does not read the body and does not read the situation in the description.

- The description restates the name, or the situation that should open the skill is only in the body. The agent matches the description before it has the body, so it never opens the skill, or it opens the skill only when the task uses the name. The agent does that work as it would with no skill.
- The description lists words a person might say, and not a situation that the agent can match when those words are absent and the name is absent. A task that is this job, said without those words, does not open the skill.
- The description names no similar situation that must not open the skill. The agent opens it for a neighbor whose description could match the same request.
- The body waits for a word that the person would type after the name. The agent opened the skill from the description, so that word did not arrive. The agent asks for it, or it guesses.
- A path in the body is written for the folder that has the pointer. That folder has only the pointer. The agent does not find the file.
- The body names several capabilities, and the description's situation names one of them. The agent does not open the skill for the others, so those capabilities are never read.
- A check that must pass even when the agent does not open the skill sits only in the body. The open is a choice, so a missed open skips the check.

## What it is composed of

The author writes that one file. The program checks its frontmatter against the schema [skill](../templates/skill.schema.json). The page "Schema"³ says what the check uses. The description is the line the agent matches before the open. The page "Routing table"⁴ has that line. The body is the instructions that the agent follows after the open. A skill can work as an entry point, including one that both routes and has instructions of its own. The page "Entry point"⁵ says what an entry point is. When the skill routes, the body has the table that the page "Routing table" has for a body. Each row names a capability. The page "Exposure method"¹⁰ says what an exposure method is, so a row does not name one.

## How to build it

Follow the steps of the page "Cognitive unit"⁶ for the instructions. The steps below are the ones that a skill does differently, and the ones that only a skill has.

1. **The failure, its cause and the situation, then the purpose.** Name three things before any line of the skill. The failure is the work that comes out wrong when the agent does not have these instructions, on a task that needs them. The cause, for a skill, is something the agent lacks until it opens the skill: the instructions are not in the task until the agent chooses them from the description. The situation has three tasks. One is a task where the cause shows. The second is a task of this work that is not the task in front of you. The third is a similar task that must not open the skill. Then write the purpose from the failure: what the agent does after it opens the skill, so that the failure does not happen. The page "Cognitive unit"⁶ says how the first lines of the body carry that purpose. An author who starts from the name and the description writes a file that the program accepts, and the agent does not open it for the work.

   Weak: "After the agent opens it, the agent does better visual work."

   Strong: "After the agent opens it, the agent names the banned pattern."

   The weak line names a quality, so the description written from it has no situation to match.

2. **Write the body before the description.** Write the instructions that the agent follows after the open, before the description, because the agent matches the description in the pointer before it reads the source. The page "Cognitive unit" says how to write those instructions.

3. **Name each input, and do not wait for a word after the name.** Name each input, and the next action when it is absent, as the page "Cognitive unit" says. The person does not type the inputs after the name, because the agent opened the skill from the description, and the program does not pass a word from the name into the body.

   Weak: "Use the file that the person passed after the skill name."

   Strong: "Use the file that the task names. When the task names no file, stop and say which file the task must name."

   The weak line waits for an input the open did not bring, so the agent asks or guesses.

4. **Name a capability from the source file.** A file the skill sends the agent to is a capability. The page "Capability"⁷ says how to write it. Name it at the step that needs it. The path opens from the folder of the source file, because the pointer names that file and the folder that has the pointer has no other file.

   Weak: "Before the first edit, read checks.md."

   Strong: "Before the first edit, read checks.md in the folder of this file."

   The weak line names the file as if it sat next to the pointer. The agent looks there and finds no file.

5. **A check that must pass without an open does not go in the body.** A check that must pass each time the agent opens the skill is a step in the body. After the open, the agent follows the body, and the skill has no second place a check runs. Do not put a check in the body when the task that needs it may not open the skill. A missed open skips the check.

6. **Write the description, and say what each part contains for a skill.** Write the description after the body, as the page "Routing table" says. Fill the four parts as follows, and stop. A step belongs in the body. The agent has not read the source yet, so a step in the description is acted on with none of the instructions.

   `CONTAINS:` names what the instructions have that another skill with the same purpose does not. When the skill routes, name the kind of choice the body makes among the capabilities it names, not each capability's job. The agent reads each capability's row only after the open.

   `PURPOSE:` names the result of the open: the work that the failure names. It does not name a word that the person types. The person does not type the name for the agent to open the skill.

   `ALWAYS LOAD WHEN:` names a situation in the task that the agent can match now, without the name and without the body. The criterion: a reader who has not seen the body can point to a task that matches, and that task does not use the name. Write the situation as a fact about the task. An order in this part is not the body. The agent can skip an order in the description, because the description is a row it matches, not instructions it has opened.

   `DO NOT LOAD WHEN:` names one similar situation, and names the other skill to open, or names that no open is right. The similar situation is another skill the agent could open from the same list, not a capability that the body names. A capability that the body names is reached after the open.

   Write each part as a fact about the skill or about the task. Do not write it as the author's speech. The program copies the description into the pointer, and the agent matches that copy before it reads the source.

   Weak: `ALWAYS LOAD WHEN: the person says ban list, visual ban, or slop`

   Strong: `ALWAYS LOAD WHEN: the task is about to set the look of a page`

   The weak line opens on the word. A task that is this job, said without those words, does not open the skill.

   Weak: `ALWAYS LOAD WHEN: you should open this before you change code that failed`

   Strong: `ALWAYS LOAD WHEN: the task is about to change code that failed`

   The weak line is an order. The agent can skip it, because it is not the body.

7. **Name the file for the work, not for a word of the task.** Name the file for the work that the purpose names. The program writes that name into the pointer, beside the description, and the agent sees the name before it opens the skill. The criterion: the name is not a word that the task will contain for a reason other than this work. A name that is such a word makes the agent open the skill when the situation does not match.

    Weak: `name: files`

    Strong: `name: page-look`

    The weak line is a word of ordinary tasks, so the agent opens the skill on that word.

8. **When the skill routes, the open is decided before the table is read.** Write the description so the open covers every row, as the page "Entry point" says. The agent reads the table only after the open, and the description is the only text it has for that choice. When the table names more than one capability, the page "Nested exposure"⁸ says when those capabilities belong under one exposure method.

- When you edit the body, change the source file. The next open reads the new body, because the pointer names the source and the program does not copy the body. When you edit the description or the name, the agent still matches the copy in the pointer until the program writes the pointer again. Change the source, then have the program write the pointer again, in the same change. The page "rbtv command"⁹ says how. A description in the source that the pointer does not yet have sends the agent to the old open.
- When you convert an outside skill, keep the failure it was written against, and write the body from that failure, as the page "Cognitive unit" says. The outside skill is a folder. The instructions go in the body of the one file. A file beside those instructions is not copied into the folder that has the pointer. Send a file beside the outside skill, when it is not these instructions, to the page "Choosing what to build". A field that the outside file uses to block the agent's open, to name one harness's tool, or to take a word typed after the name, is not a part of the skill. Drop it. The inputs come from the task. Rewrite the outside description as the page "Routing table" says, and fill the parts as the description step says.
- When you review, read the description before the body, as the page "Routing table" says. Name the open it causes for one task that should open the skill and one that should not. Neither task uses the name. Then follow the body on a task that types nothing after the name, and follow each path.

Checks:

- A reviewer who has only the description can name one task that should open the skill and one that should not, and neither task uses the name. `CONTAINS:` and `PURPOSE:` are not the same sentence. No step is in the description. The name is not a word of an ordinary task.
- The body does not ask for a word typed after the name. Each path in the body says it opens from the folder of the source file.
- The checks of the page "Cognitive unit" pass for the instructions. The checks of the page "Routing table" pass for the description. The checks of the page "Entry point" pass when the skill routes.
- A run of the program accepts the file. The page "rbtv command" says how to run it. Acceptance shows that the frontmatter matches the schema. It does not show that the agent opens the skill on the task that the description names, or stays closed on the similar task, because the program does not read the body or the situation.
- Give an agent the description and not the body. Give one task that should open the skill and one that should not. Neither task uses the name. The agent opens the skill for the first task and leaves it closed for the second. Then give the agent the skill, on a task that types nothing after the name, and with one input absent. Watch the work that the purpose names, the action on the absent input, and the folder of any path the agent opens.

## Template

```markdown
---
name: <the file's name: the work, not a word of an ordinary task>
description: "<CONTAINS: what the instructions have that another skill with the same purpose does not; when the skill routes, the kind of choice the body makes, not each capability's job PURPOSE: the result of the open, the work that the failure names ALWAYS LOAD WHEN: a situation in the task, matchable without the name and without the body DO NOT LOAD WHEN: the similar situation, and the other skill to open, or that no open is right>"
---

<the purpose in the first lines of the body: what the agent does after the open, so the failure does not happen>

<the instructions. An input is in the task, not a word typed after the name. A path opens from the folder of this file. A file that this skill sends the agent to is a capability, named at the step that needs it. A check that must pass on each open is a step here.>

<when the skill routes: the table the page "Routing table" has for a body. Leave this out when the skill does not route.>
```

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Component | [Component](component.md) | when | placing the file | take which folder has `skills/<name>.md` |
| 2 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | the choice of a skill is not yet settled, or a file beside an outside skill is not these instructions | settle that choice, or send that file onward |
| 3 | Schema | [Schema](schema.md) | when | the program checks the frontmatter | find the schema file the program loads |
| 4 | Routing table | [Routing table](routing-table.md) | when | writing or reviewing the description, or the body has a table | take the line and the table, and apply the checks of a description |
| 5 | Entry point | [Entry point](entry-point.md) | when | the skill routes, or it both routes and has instructions of its own | take what an entry point is, and what each part contains when the file sends the agent on |
| 6 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | when | writing, editing, converting or reviewing the instructions | write the instructions, and take the checks that every cognitive unit shares |
| 7 | Capability | [Capability](capability.md) | when | the body sends the agent to a file | write that file, and name it at the step that needs it |
| 8 | Nested exposure | [Nested exposure](../nested-exposure.md) | when | the table names more than one capability | take when those capabilities belong under one exposure method |
| 9 | rbtv command | [rbtv command](rbtv-command.md) | when | having the program accept the file, or writing the pointer again after a description or a name changes | run that acceptance, and read what a matching frontmatter does not prove |
| 10 | Exposure method | [Exposure method](exposure-method.md) | when | a row might name an exposure method | take what an exposure method is, so the row names a capability |
