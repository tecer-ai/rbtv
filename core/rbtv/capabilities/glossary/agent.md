# Agent

An agent is a model, a harness and scaffolding, launched with a task. Scaffolding is everything the agent is exposed to, the prompt included. The harness is not part of the scaffolding. In rbtv the prompt stays the same while the task changes, and the author writes it in one folder with a record. Outside rbtv an agent is often one file that a harness launches, with the description and the prompt in that file, and a sub-agent is a second file. Here the program places one folder either as an rbtv agent or as a sub-agent of a harness.

An agent gives that prompt a fresh context, so the caller's context does not fill with the work, and a later launch can bring a different task to the same prompt. An author wants an agent when the work cannot stay in the caller's context and the same prompt must take a different task on each launch. Decide the kind with the page "Choosing what to build"¹ before you open this page. Write an agent so that a launcher who has only the description launches it for the situation the description names, with the task that the description says to give, and does not launch it for the similar case.

## How it fails

The program can accept the folder, and the agent can still fail. The program does not read the prompt, and it does not check that the description decides a launch.

- The work can stay in the caller's context. The launch pays for a fresh context and returns a summary the caller could have produced, and the description has no situation that is not also the caller's own job.
- The description restates the prompt, or it names no input the task has to carry. The launcher has not read the prompt. It launches with nothing, or it does not launch. A launch that is not a conversation ends before a question in the prompt is answered.
- The description's situation is a message that arrives after the agent is already connected, or a task an already-running agent should act on. The agent is chosen for one wake and is missing from the list that a person or another agent reads, or it is launched for a job that was never a launch.
- The prompt requires a skill, a rule or a command that only the record lists, and the folder is placed as a sub-agent of a harness. That placement does not install the list. The agent follows the prompt and the skill is absent. The program accepts the placement and reports that the list was not applied.
- The description and the prompt name different jobs. The launcher chooses the agent for the description's job, and the prompt does the other one.

## What it is composed of

The author writes one folder. It contains two files the author writes:

- `agent.md` is the prompt. It is the text that the model follows on every launch, while the task changes. The page "Prompt"² says how to write it. The name in its frontmatter is the same as the folder name and the name in the record.
- `agent.json` is the record. The author writes the name and the description, and may list the skills, the rules, the commands and the packs that an rbtv-agent placement installs. The schema of the record is the file "Agent record"³. A folder a component ships names no harness, no model and no effort in the record. Those three exist only in an installation. The program writes them into the record when it places the folder as an rbtv agent, if the record does not already name them.

A component ships the folder at `agents/<name>/` inside the component. The program reads that folder, and it can place the folder either way. A folder managed in place can live at any path. A name with no path is found under `.rbtv/agents/<name>/`.

Placed as an rbtv agent, the folder is copied to `.rbtv/agents/<name>/`, and the launch reads the copy. The program installs the record's skills, rules, commands and packs into that folder. The working folder is the agent folder. The program also writes a pointer to `agent.md` in that folder's folder instructions, so the model can find the prompt again after a long conversation. The author does not write that pointer.

Placed as a sub-agent of a harness, the harness file points at the source `agent.md`. It copies the description and does not copy the prompt. It does not install the record's skills, rules, commands or packs. The sub-agent sees what its target already has. The parent agent matches the task to the copied description before it reads the prompt. The prompt is copied only when the folder is placed as an rbtv agent.

The prompt and the record contain nothing tied to one machine: no channel, no account, no host, no credential and no absolute path. The same folder works on every machine where the installation root is the same repository.

## How to build it

1. **The work that cannot stay in the caller's context.** Name the work that cannot stay in the caller's context. The cause is what the caller would have to keep: a search, a set of files, or a method that must stay the same while the task changes. The situation is one launch a person or another agent would make, and a second launch with a different task. Write one sentence on why this agent exists. When the owner has named why the work cannot stay in the caller's context, use those words. Do not invent a reason the owner did not give. Then write the prompt, as the page "Prompt" says. An agent whose sentence is also true of the caller's own job has a fresh context the work does not need, and the program still accepts the folder.

   Weak: "A separate agent keeps the review organized."

   Strong: "The search of the change fills the caller's context."

   The weak line names no work the caller cannot keep, so the folder is a second context for the caller's own job.

2. **Write one name in the folder, the frontmatter and the record.** Write the same name in the folder, in the frontmatter of `agent.md`, and in the record. A launcher finds an rbtv agent by that name, and a harness file is named with it. Choose a name a launcher can tell from the neighboring agents' names. When the owner has named the agent, use that name in those three places. When the name changes, change the three places in the same edit. The page "Agent record" says what the program checks.

3. **Write the description from the finished prompt, as one row of a routing table.** The description is the description field of the record. It is the row a launcher reads before the prompt. The page "Routing table"⁴ has the form. Write the row after the prompt, as the page "Cognitive unit"⁷ says. The launcher has not read the prompt, so write the row from the finished prompt.

   `CONTAINS:` is the standing function and the method, in words that separate this agent from another a launcher could choose for a similar job.

   `PURPOSE:` is what that function is for, and each input the task has to carry, in the words the launcher supplies. It is not the harness, the model or the effort. The launcher has not read the prompt. A launch that is not a conversation ends before a question in the prompt is answered, so an input left out of `PURPOSE:` is an input the launch does not carry.

   `ALWAYS LOAD WHEN:` is a situation in which to launch this agent, matchable from the row alone. It is not a message that arrives after the agent is already connected to a channel, and it is not a task an already-running agent should act on. Once a channel is connected, the description does not filter the messages in that channel.

   `DO NOT LOAD WHEN:` names one similar launch, and the other agent to launch, or that no launch is right. It does not name a message that arrives after the agent is connected. The page "Routing table" says when the part is on the line.

   The list a person or another agent reads shortens the description to the line, unless the whole description is asked for. A part that sits past what the line can show is missed. Keep the row to what the four labels need. Apply the tests of the page "Scaffolding language"⁵ to the row.

   Weak: `PURPOSE: reviews a change`

   Strong: `PURPOSE: reviews the change the launcher names, in the files the launcher names`

   The weak line leaves the change and the files in the prompt. The launcher starts the agent with nothing.

   Weak: `DO NOT LOAD WHEN: the agent is already running`

   Strong: `DO NOT LOAD WHEN: the job is to change the files, which is a launch of the implementer agent`

   The weak line names a moment after the launch, so it excludes no similar launch.

4. **List in the record only what an rbtv-agent placement should install.** List a skill, a rule, a command or a pack in the record when that placement should install it into the agent folder. A placement as a sub-agent of a harness does not install the list, and the program still accepts that placement. A folder a component ships can be placed either way, so the prompt cannot require a skill that only the list installs. Do not write a harness, a model or an effort in a record that a component ships. Those three exist only in an installation. The program writes them into the record when it places the folder as an rbtv agent, if the record does not already name them. The page "rbtv command"⁶ says what the program checks. Do not copy them into the prompt. When the folder is managed in place and is not one a component ships, the record may already name them. Leave them in the record.

When you edit the description, change it in the record that the launcher reads, as the page "Routing table" says for a row that changes with what it names. An rbtv agent's list reads the record in the folder that the launch uses. A harness file contains a copy of the description from the moment the folder was placed as a sub-agent. An edit to the source record reaches that copy when the folder is placed that way again. When you edit the prompt, change the `agent.md` that the model is given. For a folder managed in place, that file is the `agent.md` in the folder. A harness sub-agent file points at the source `agent.md`, so the model reads the source. Placed as an rbtv agent, the launch reads the copy. An edit to the source reaches that launch when the folder is placed again. When the name changes, change the folder, the frontmatter and the record in the same edit.

When you convert an outside agent file, write its description as the record's description, in the form above. Its body becomes the prompt; follow the page "Prompt". A model, a tool list and a permission mode in the outside file are not written into the prompt. A model is a launch value of an installation, not a field of a record that a component ships. A part that is not the prompt and not the description is decided with the page "Choosing what to build".

When you review, read the description with the prompt closed, as the page "Routing table" says. For one request that should launch this agent and one that should not, write the launch the description causes. The first request's task has to contain every input `PURPOSE:` names.

Checks:

- `PURPOSE:` names each input the task has to carry, in the words the launcher supplies. `ALWAYS LOAD WHEN:` is a situation in which to launch this agent, not a message after it is connected. The description names the same job as the prompt.
- The program accepts the folder, as the page "rbtv command" says. Acceptance shows the folder was recognized. It does not show that the description decides a launch, or that the prompt does the work.
- Hand a person the description and a neighboring agent's description, and not the prompt. Ask which agent to launch for a job this agent does, and for a job the neighbor does. The person names this agent only for the first, and the task they would give contains every input `PURPOSE:` names.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | before this page is opened, or a part of a converted file is another kind of thing in rbtv | decide the kind, or where that part goes |
| 2 | Prompt | [Prompt](prompt.md) | must | | write the prompt, and take which file a launch reads |
| 3 | Agent record | [Agent record](../templates/agent-json.schema.json) | when | writing the record | take the fields the program checks |
| 4 | Routing table | [Routing table](routing-table.md) | when | writing the description | take the form of the row, and write only what each part contains for an agent |
| 5 | Scaffolding language | [Scaffolding language](scaffolding-language.md) | must | | word every sentence so the agent acts on the meaning you gave it, and apply its tests |
| 6 | rbtv command | [rbtv command](rbtv-command.md) | when | having the program accept the folder | find the command to run, and take what acceptance shows |
| 7 | Cognitive unit | [Cognitive unit](cognitive-unit.md) | when | writing the description after the prompt | write that text after the instructions, and take only what an agent adds |
