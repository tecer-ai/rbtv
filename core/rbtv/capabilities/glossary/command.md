# Command

A command is a cognitive unit a human invokes by typing its name. At that point the agent has read none of the command. Outside rbtv, the harness lists the command file and fills a placeholder in that file with the text typed after the name. In rbtv the harness lists a short file the program writes. That file points at the source. The agent reads the source as text, so a placeholder in the source is never filled.

A command is for an action that should start because a human typed its name, and that should carry, in that same typing, what the action needs. An author wants one when that action still starts at a moment the human did not choose, or never starts because the human has no name to type. Write a command so that a human who has only the name and the description invokes it for that one action, with the text the action needs, and the agent then does the action.

## How it fails

The program can accept a command, and the command can still fail, because the program checks the frontmatter and does not read the instructions.

- The name is not the words the human would type for this action, or it is a name a harness already uses for its own command. The human invokes a different action, or the harness runs this file in place of its own command.
- `PURPOSE:` does not name the text the human types after the name. The human invokes with nothing, and the agent then asks for what that typing could have carried.
- The instructions contain a placeholder for that text, such as `$ARGUMENTS`. The agent reads the placeholder as words. The program does not fill it, and a harness fills a placeholder only in the file it lists, which is not this source.
- The instructions ask the human a question, or ask whether to start. The human already chose by typing the name. The question requests a decision the typing was supposed to carry, or it delays the action the name started.
- The action that an agent must also do without a human typing the name lives only in this command. The agent does that action without the text the human would have typed, or it asks for that text again.
- The description names no similar command to leave untyped. The human types this name for the neighbor's action.

## What it is composed of

The author writes one file, `commands/<name>.md`, in the component. `<name>` is the name the human types. The program checks the frontmatter against [command.schema.json](../templates/command.schema.json) and does not read the body.

The description is always present. It is the row a human reads before typing the name. Take the labels, the order and the quoting from the page "Routing table"¹.

The body is always present. It is the instructions the agent reads after the invocation. When the command is an entry point, the body has a markdown table that names capabilities. Take that table from the page "Routing table"¹ and from the page "Entry point"². A command can route, keep text in the body, or both.

The program writes one short file for each harness that receives the command, named with the command's name. That is the file the harness lists. Its text tells the agent to read this source and follow it. The program does not copy the body into that file. On Claude Code and OpenCode the short file also carries the description. On Codex it does not, so the human chooses from the name alone.

## How to build it

1. **The action the human cannot start by typing, then the purpose.** Find the action that should start only when a human types its name, and that today either never starts or starts because an agent chose the moment. That is the failure. Its cause, for a command, is that the human has no name to type that starts the action with what it needs, or the agent starts the action without that typing. The situation is the human at the harness, about to type a name, on one task you can point at and on a second task you are not looking at. Write the purpose from that failure: what the agent does after the human has typed the name, so the failure does not happen.

   Weak: "After the human types the name, the agent does better work."

   Strong: "After the human types the name, the agent writes the memo before the first edit, so the run does not start without a memo."

   The weak line names no action the typing starts. The strong line names that action for one case.

2. **Write the instructions for an invocation that has already happened.** Write the instructions before the description, as the page "Cognitive unit"³ says, and put in the first lines what the agent does after the human has typed the name. The human has already typed the name and the text the action needs, so the instructions start that action. They do not ask the human whether to start, and they do not teach the human how to invoke, because the human does not read the body before typing. A sentence in the body is an instruction to the agent. Word the name the human types, and the row the human reads before typing, by the tests of the page "Scaffolding language"⁴. A word the human takes in another sense is the name the human types.

3. **Name each input in the words the human types, and write no placeholder for it.** The human types each input on the same line as the name, and the agent has not read the body yet. Name each input in those words, in the instructions and later in `PURPOSE:`. Tell the agent to take each input from the text that followed the name. Do not write a placeholder such as `$ARGUMENTS` in the source. The program copies none of the body into the file the harness lists, and it never fills a placeholder. A harness fills a placeholder only in the file it lists. The agent reads this source as text, so the placeholder stays as words. When the text after the name lacks an input, the agent stops and names what the next typing has to include. A question then requests what that typing could have included.

   Weak: "Ask the user where the project folder lives, then continue."

   Strong: "Take the project folder from the text typed after the name. When that text names no folder, stop and say the next typing has to include the folder. Do not ask."

   The weak line is accepted and still requests what the typing could have included.

4. **Name the command with the words the human types for this one action.** The program names the file the harness lists with this name, and the human chooses from that name before reading a line. On Codex the listed file carries no description, so the name is the whole choice there. Pick words the human would type for this action and for no other. Do not pick a name a harness already uses for its own command. The program accepts that name. On Claude Code the listed file then replaces the harness command, except an alias of it. On OpenCode the listed file overrides the built-in of the same name.

   Weak: "Name it review, because that is the word for this review."

   Strong: "Name it trail-review, because review is a name a harness already lists as its own command."

   The weak line is a name the harness already lists, so the file the program writes replaces that command.

5. **Write the description as the row the human reads before typing.** Write one row, and take the labels, the order and the quoting from the page "Routing table"¹. The reader is the human who is about to type a name and has not read the body. For a command, the parts contain:

   - `CONTAINS:` what is in this command that separates it from another command with the same purpose, in words the human can use without the body.
   - `PURPOSE:` what that content is for, and each input in the words the human types after the name.
   - `ALWAYS LOAD WHEN:` the job for which the human types this name, matched from this row and the name, before the body is read.
   - `DO NOT LOAD WHEN:` one similar situation, and the other command the human should type, or that no command is right.

   Weak: `PURPOSE: starts a trail run`

   Strong: `PURPOSE: starts one trail for the idea typed after the name`

   The weak line leaves the idea out of the typing, so the human types the name alone.

6. **Keep a tool name out of the row the human reads before typing.** When a step's answer is a count, a date, a comparison, a format or the existence of a file, name the tool in the instructions, as the page "Cognitive unit"³ says, and leave that name out of the row the human reads before typing. A tool name in that row is a step the human has not loaded, and the human may type it as if it were the command.

7. **When the same action must also run without this typing, put its instructions in a capability.** The command is built for a human who types its name. When an agent must also do this action without that typing, the instructions are a capability: read the page "Capability"⁵ for how to write it. After the name is typed, the command sends the agent there at the step that needs those instructions, and keeps only which inputs arrived and the stop when one did not.

8. **When the command routes, the table is for the agent after the typing.** A command can work as an entry point. The human still chooses it by the name, before the agent reads the table. Write the table as the page "Routing table"¹ says, and write each link as the page "Entry point"² says. A row names a capability. It does not name an exposure method. The page "Exposure method"⁹ says what an exposure method is. An exposure method is not placed inside this command. Do not ask in the table for text this invocation already carried. Do not write the table as a menu the human picks after typing. The name already chose this command. When several capabilities might belong under this command, read the page "Nested exposure"⁶ and take when they belong under this one exposure method.

9. **When the result the human typed the name to get is a finding, name the passage.** Give the passage, what it causes, and the repair, as the page "Cognitive unit"³ says. The passage is in the work this typing started, not in a later task the human did not name.

When you edit the instructions, change the source. The agent reads the source on the next invocation, so a change to the body reaches the agent then. When you edit the description, the human still reads the description in the file the harness lists until the program writes that file again. Have the program accept the command, as the page "rbtv command"⁷ says, before you treat the new row as what the human reads.

When you convert an outside command, take each placeholder for arguments out of the body and name those inputs in the words the human types. Put them in `PURPOSE:`. Write the outside description as the four parts. When a piece of that outside file is a skill, a rule, a capability or another kind in rbtv, send that piece to the page "Choosing what to build"⁸.

When you review, read the name and the description before the body, as the page "Routing table"¹ says. Then name the typing the row causes, for a situation that should invoke and for a situation that should not. Run one invocation that carries what `PURPOSE:` names, and one that leaves an input off. Acceptance by the program is not a review of the command.

Checks:

- A reviewer sees a name a human would type for one action, and not a name a harness already uses for its own command. The description is one row, and `PURPOSE:` names each input in the words the human types after the name. The instructions contain no placeholder for that text. A missing input has a stop that names the next typing. The first lines say what the agent does after the name is typed, and that action is the one that stops the failure. When the command routes, the table names capabilities and names no exposure method.
- Have the program accept the command, as the page "rbtv command"⁷ says. Acceptance shows the frontmatter matches the schema. It does not show whether the human can choose from the name. It does not show whether the typing carries the inputs. It does not show whether the instructions do the action.
- Give the name and the description, without the body, to a person, with one action that should invoke and one that should not. The person invokes on the first and not on the second, and the invocation carries what `PURPOSE:` names. Then give the command to an agent with that invocation, and with one input left off. Look at whether the agent does the action, and whether the missing input stops it with the next typing named.

## Template

```markdown
---
name: <the words the human types for this one action>
description: "CONTAINS: <what is in the command, separable without the body> PURPOSE: <what it is for, and each input in the words the human types after the name> ALWAYS LOAD WHEN: <the situation in which the human types this name> DO NOT LOAD WHEN: <the similar command to type instead, or that no command is right>"
---

<What the agent does after the human has typed the name, so the failure does not happen.>

<Each input, taken from the text typed after the name. The stop when that text lacks an input. No placeholder.>

<When the command routes: a markdown table of capabilities, each a link. No row names an exposure method.>
```

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Routing table | [Routing table](routing-table.md) | must | | write the description as one row, and take the labels, the order and the quoting |
| 2 | Entry point | [Entry point](entry-point.md) | when | the command routes, or the body has text every invocation needs | take which text is in the body, which text is a row, and how each link is written |
| 3 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | must | | write the instructions, name a tool for an exact answer, and give a finding as the passage, what it causes, and the repair |
| 4 | Scaffolding language | [Scaffolding language](scaffolding-language.md) | must | | word the name, the row and the instructions so the reader acts on the meaning you gave them |
| 5 | Capability | [Capability](capability.md) | when | the same action must also run without a human typing the name, or a step sends the agent to a page | write the capability, and have the command send the agent there once the name is typed |
| 6 | Nested exposure | [Nested exposure](../nested-exposure.md) | when | several capabilities might belong under this command | take when they belong under this one exposure method |
| 7 | rbtv command | [rbtv command](rbtv-command.md) | when | having the program accept the file, or a description change must reach the human | find how to have the program write the listed file again, and take what acceptance shows |
| 8 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | a piece of a converted command is a skill, a rule, a capability or another kind in rbtv | decide where that piece goes |
| 9 | Exposure method | [Exposure method](exposure-method.md) | when | a row of the table might name an exposure method | take what an exposure method is, so the row names a capability instead |
