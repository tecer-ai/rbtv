# Prompt

A prompt is the standing text that a model follows on every launch of an agent. In rbtv it is the body of `agent.md`. The frontmatter is not part of the prompt. Outside rbtv a prompt is often a system message, or the body of one file that also carries the description. Here the description is in the record, the task arrives with the launch, and the role, the persona, the navigation, the procedure and the constraints are sections of this one text.

A prompt keeps one standing function, one method and one set of limits while each launch brings a different task. An author wants a prompt when that work still comes out differently on each launch, because no standing text is there for the later launch. Write a prompt so that an agent, launched with a task that the purpose does not name, does the work the failure names and does not invent a task the launch did not carry.

## How it fails

The rbtv CLI can accept the file, and the prompt can still fail, because the rbtv CLI does not read the body.

- The body names one task's files, goal or done check. The next launch is decided by that task, or the agent asks for it. A skill is read inside a task that already has those. A prompt is the text that the model has before the task arrives.
- The role names no standing function, or the persona is a voice that changes no open choice. Each launch invents who the agent is, or it performs the voice and still stops, explores and weighs risk as it would have with no persona.
- Role, procedure and constraints give different orders for the same behavior. The agent spends the launch reconciling them. A skill is one text. A prompt is four sections that can disagree, and the rbtv CLI does not compare them.
- Navigation uses the working folder, or names one task's files. An rbtv launch sets the working folder to the agent folder. On Claude Code, a harness that launches the agent as its sub-agent starts in the caller's folder. The same relative path is a different place in those two launches, so the agent looks in the wrong folder.
- The procedure tells the agent to ask and wait, or it pastes a capability, or it is a second method. A launch that is not a conversation ends before the answer arrives. A pasted capability drifts from the page on the next edit. A second method is improvised on the launch that needed the first.
- The body assumes the caller's prompt, a skill that the record lists, or a memory file. A called agent does not receive the caller's prompt. A placement as a sub-agent of a harness does not install the record's list. A launch that is not an Ignite wake does not inject memory. The agent invents the missing fact, and the rbtv CLI still accepts the file.

## What it is composed of

The author writes the body of `agent.md`, in the folder that the page "Agent"¹ names. The frontmatter of that file carries the name and nothing else. It is not part of the prompt. The schema of that frontmatter is the file "Agent frontmatter"². On an rbtv launch and on an Ignite turn, the CLI that launches the agent removes the frontmatter before the model sees the text. A harness sub-agent file does not contain the body. It tells the model to read the source file.

The body has these headings, in this order, spelled as written: `## Role`, `## Navigation`, `## Procedure`, `## Constraints`. Navigation is absent when the agent works only in its own folder. Constraints are absent when no standing limit remains. The persona has no heading. It sits in Role, and only when an open choice remains. An empty heading is absent: no heading and no placeholder.

Role is always there. It states who the agent is and the standing function that is true of every task. The persona, when it is there, is the standpoint that shapes the choices the procedure and the task leave open.

Navigation, when it is there, names the folders the tasks work in, as paths from the installation root. The rbtv CLI does not read this section.

Procedure is there when the agent does work. It is the method that is true of every task. A step may send the agent to a capability. The page "Capability"³ says how to write that page. A prompt is not an entry point. The page "Entry point"⁴ says what an entry point is. Do not put a routing table in the body.

Constraints, when they are there, are standing limits honored by judgment. They are not a sequence of steps.

The task arrives with the launch. Its scope and its done contract are sections of the task, not of the prompt.

## How to build it

1. **The job that still comes out wrong, who launches, the tasks, then the purpose.** Name the job that still comes out wrong when a fresh launch is given only a task. Write who launches the agent. A person can open it and talk. Another agent can launch it with a task and receive one result. A harness can launch it as a sub-agent with a task. A Slack message or a timer can wake it for one turn. Write two tasks those launches will bring, one of which you are not looking at. The cause is the part of the job the task does not carry and the caller does not pass on: the standing function, the method, a limit, or the next action when an input is absent. A launch does not include the caller's prompt. Then write the purpose from that cause: what the agent does on the second task so that the failure does not happen. When the owner has named what the agent does on a later launch, use those words in the purpose. Do not invent a purpose the owner did not give. An author who starts from the four headings writes a prompt that has every heading and stops no failure.

   Weak: "This prompt helps the agent do better reviews."

   Strong: "After reading it, the agent names the file and the line where the wrong value is born, before the first edit, on a change it has not seen."

   The weak line names no job, so the sections that follow have nothing to stop.

2. **Write the body first, and put the purpose in the first lines of Role.** Write the body before the description, as the page "Cognitive unit"⁵ says. For a prompt, the description is a field of the record, and the purpose goes in the first lines of Role, because the model starts there. The model is given the body. On an rbtv launch and on an Ignite turn, the frontmatter is removed first, so an instruction written only there does not reach the model. Apply the tests of the page "Scaffolding language"⁶ to each sentence of the body.

3. **Name each input the task must carry, and the next action when it is absent.** Name each input the procedure uses, as the page "Cognitive unit" says. For a prompt, the input arrives in the task. A person who opens the agent can answer a question. A launch by another agent, a harness, a Slack message or a timer ends before the answer arrives. When any launch is one of those, the next action is to stop and name what the next launch has to carry. A folder, a path or an account that is true of one installation is an input the task or the installation supplies. It is not a sentence of the prompt.

4. **Name the tool in the procedure when the answer is exact.** When a step has an exact answer, name the tool as the page "Cognitive unit" says, and write that name in the procedure. Do not put the check in Constraints. A constraint is honored by judgment, and the rbtv CLI does not run it. When several ways succeed, follow the page "Cognitive unit" for the result, the criterion and the one way. Write that step in the procedure too. A constraint does not choose among ways.

5. **Keep one method, and send the agent out instead of pasting.** Keep one purpose, as the page "Cognitive unit" says. A second method does not belong in this procedure. Decide where it goes with the page "Choosing what to build"⁷. When a step needs a page that already has the instructions, send the agent there and name the moment, as the page "Cognitive unit" says. Do not paste the caller's prompt. A launch does not include it. When the step needs a skill, a rule or a command that the record lists, state the next action for when it is absent. The page "Agent" says a placement as a sub-agent of a harness does not install that list. When a step names a capability, write the path from the root of the rbtv repository, or from `.rbtv/`, as a rule does, and not from `agent.md`. The rbtv CLI derives from it the path that opens where the prompt is read. One placement reads a copy of the prompt, and the other reads the source, as that page says. A path from the file is a different place in the two placements. Do not paste a memory file. Require one only when every launch of this agent is a wake that injects it, and you named that launcher in the first step. A prompt is not an entry point. Do not put a routing table in the body.

6. **Write the sections under one set of rules.** Use the headings in the order above, spelled as written. The rbtv CLI does not read the headings, so a renamed heading, a missing section, or a section that does another section's job is accepted. A sentence that names one task's files, goal or done check is not in any section. The task carries it. A sentence that restates another section makes the two disagree, and the agent spends the launch on the disagreement. No section names a channel, an account, a host, a credential, or a path that is true of one machine. Leave out a sentence the failure does not need, as the page "Cognitive unit" says.

### Role

**What it is for.** Role states who the agent is and the standing function that is true of every task. It prevents each launch from inventing who the agent is. The persona, inside Role, is the standpoint that shapes the choices the procedure and the task leave open: when to stop, how broadly to look, how to weigh a risk, how to break a tie. It prevents those choices from coming out differently on each launch.

**When the prompt has it.** Role is always there. The persona is there only when a different standpoint would change one of those open choices. When no judgment is left open, write no persona.

**How to write it.** State the standing function in one sentence: who the agent is, and the remit that is true of every task. When the result is wrong, a reader can point to the function that failed. When the reader cannot point to one function, the sentence has two functions. Every sentence is true of every task. No step, no tool name and no done check appears. The persona, when it is there, is one or two sentences in this section, not a heading. It names the standpoint. It does not restate the task's done contract, and it does not set the order of steps. A voice added so two agents differ, while their choices match, is not a persona. When the owner has named who the agent is, use those words.

Weak: "You are the reviewer of a change, with a sharp, witty voice."

Strong: "You are the reviewer of a change. Treat the change as broken until the cited file and the cited line show otherwise."

The weak line adds a voice. The open choices stay unset, so each launch stops and weighs risk as the model would have with no persona.

**Checks.** One standing function, and a reader who has a wrong result can point to it. No sentence names one task. No step. The persona is present only when removing it would change an open choice, it is not a heading, and it does not restate a done check.

### Navigation

**What it is for.** Navigation names the folders the tasks work in, so the agent starts at the work and not at the working folder. It prevents a path that is a different place in the two placements.

**When the prompt has it.** It is there when the work is not only in the agent folder. When the agent works only in its own folder, the heading is absent.

**How to write it.** Write one line that says the paths start at the installation root, not at the working folder. Then one path per line, from that root. An rbtv launch sets the working folder to the agent folder. A harness that launches the agent as its sub-agent starts in the caller's folder, on Claude Code. A path from the working folder is a different place in those two launches. Do not name one task's files. The rbtv CLI does not read this section, so a path of one machine is accepted and still fails on the next machine.

Weak: "The notes for every task of this agent are in ./plans/launch."

Strong: "The notes for every task of this agent are in plans/launch, from the installation root."

The weak line follows the working folder, so an rbtv launch looks inside the agent folder.

**Checks.** Each path starts at the installation root, and the section says so. No path names one task's file, a channel, an account or a host. The heading is absent when the agent works only in its own folder.

### Procedure

**What it is for.** Procedure is the method that is true of every task. It prevents each launch from improvising a method, so the results differ from launch to launch.

**When the prompt has it.** It is there when the agent does work.

**How to write it.** Order the steps that must happen in order. At each branch, state what changes the path and the next action. Write the tool, and the one way, from step 4 in this section. Do not name one task's files, goal or done check. One method. When a step needs a capability, write the path as step 5 says, and name the moment. When a step needs a skill that the record lists, state the next action for when that skill is absent. A check the conclusion depends on runs to completion inside the turn. Do not tell the agent to wait for a later message when any launch of this agent is not a conversation. When the procedure has the agent report a finding, follow the page "Cognitive unit". The finding is about the work of this launch. When another task uses a step's result, name the file or the record that task can read without this agent.

Weak: "Ask which file to review, then wait for the answer."

Strong: "When the launch brings no file, end the turn and say which file the next launch must include."

The weak line asks in a turn that ends before the answer arrives.

**Checks.** One method. Each branch has a next action. No task file and no pasted capability. No wait for a later message when a launch of this agent is not a conversation. A skill the record lists has a next action for when it is absent. An exact answer names the tool.

### Constraints

**What it is for.** Constraints are standing limits on conduct, honored by judgment, on every task. They prevent conduct that has no standing limit. They are not limits that code enforces.

**When the prompt has it.** They are there when a limit must be true of every task, honoring it takes judgment, and no tool can enforce it. When no such limit remains, the heading is absent. A limit that is true of one task is not a constraint. A limit a tool can check is a procedure step that names the tool.

**How to write it.** For each limit, name the behavior, why the limit exists, and what to do instead. A ban with no alternative leaves the agent with no next action. Do not set an order. Order belongs in the procedure. Do not restate a procedure step. Two limits on the same behavior are one limit. The section contains limits only. It contains no steps and no task files.

Weak: "Do not invent a path that the task does not name."

Strong: "Do not invent a path that the task does not name. Stop and name the path the next launch has to carry."

The weak line gives no alternative, so the agent has nothing to do instead.

**Checks.** Each limit names the behavior, the reason and the alternative. No step, no order and no one-task limit. No limit a tool can check. The heading is absent when no limit remains.

When you edit, change the body in the file that the model is given. The page "Agent" says which file that is for each placement. Change the body against the same failure. Leave out a sentence the failure does not need, as the page "Cognitive unit" says.

When you convert an outside agent file, keep the failure it was written against, and write the sections from that failure. The description in the outside file is not a section. It becomes the record, as the page "Agent" says. Drop a heading the failure does not need. An outside file often puts a voice in place of a standpoint, puts one task's files in the method, and tells the agent to ask and wait. A tool list, a model and a permission mode are not sections of the prompt. A part that is not a section of the prompt is decided with the page "Choosing what to build".

When you review, read the body as the model meets it, without the frontmatter and without the caller's prompt. Take one task that the procedure names and one it does not name, and leave one input out. Name each failure as the page "Cognitive unit" says. Acceptance of the file is not a review of the body.

Checks:

- Role states one standing function that is true of a task that the purpose does not name. The persona sits in Role, and only when removing it would change an open choice. Navigation, when present, uses paths from the installation root and says so. Procedure is one method, with a next action at each branch and when an input or a listed skill is absent, and it does not wait for a later message when a launch is not a conversation. Constraints, when present, name the behavior, the reason and the alternative. The headings are the fixed names in the fixed order. No section names one task's files, goal or done check.
- The rbtv CLI accepts the file, as the page "rbtv CLI"⁸ says. Acceptance shows the file was recognized. It does not show that the body was read.
- Launch an agent with this prompt, with a task that the procedure does not name, and with one input left out. Look at the standing function it follows, the path it opens, whether it waits, and whether the missing input ends the turn with that input named.

## Template

```markdown
---
name: <the name, the same as the folder and the record>
---

## Role

<who the agent is, and the standing function for every task>
<the standpoint, when a different one would change an open choice; otherwise omit these sentences>

## Navigation

<one line: paths start at the installation root, not at the working folder>
<one path from the installation root per line; omit this heading when the agent works only in its own folder>

## Procedure

<the method for every task, or the sentence that names a capability at the step, with the next action when an input is absent>

## Constraints

<one limit: the behavior, why, and what to do instead; omit this heading when no limit remains>
```

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Agent | [Agent](agent.md) | must | | take the folder, the record, and which file each placement gives the model |
| 2 | Agent frontmatter | [Agent frontmatter](../templates/agent.schema.json) | when | writing the frontmatter | take the name field, and write no other field |
| 3 | Capability | [Capability](capability.md) | when | a step sends the agent to a capability | write that page, and send the agent there at the step |
| 4 | Entry point | [Entry point](entry-point.md) | when | you are about to put a routing table in the body | take that a prompt is not an entry point |
| 5 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | when | writing the instructions the agent acts on | take the shared steps, and write only what a prompt adds |
| 6 | Scaffolding language | [Scaffolding language](scaffolding-language.md) | must | | word every sentence so the agent acts on the meaning you gave it, and apply its tests |
| 7 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | a second method does not belong here, or a part of a converted file is not a section of the prompt | decide where that part goes |
| 8 | rbtv CLI | [rbtv CLI](rbtv-cli.md) | when | having the rbtv CLI accept the file | find the command to run, and take what acceptance shows |
