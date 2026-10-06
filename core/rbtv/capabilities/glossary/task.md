# Task

A task is the one piece of work a launch gives an agent. Outside rbtv the same word often names the standing instructions, or a short line a parent types when it delegates. Here the prompt stays for every launch, and the task is the text of one launch. That text has two sections, scope and the done contract, and those sections are not written in the prompt.

A task gives the launch the boundary and the done conditions that the prompt does not carry, so the launch does this work and does not invent a second one. An author wants one when a person, another agent, a timer or a Slack message is about to start a launch that will not have the supplier in it. Write a task so that the launch produces the result that the first lines name and stops on the done contract. That launch has the prompt and this text, and nothing else from the supplier; an Ignite agent also has its memory, its board and the recent messages of its channel, which are not the task.

## How it fails

A launch accepts the text it is given as the task, and the task can still fail, because no program reads the sections.

- The text restates the prompt's method, or it leaves this launch's files for the agent to find. The launch follows two methods, or it opens a file that the supplier did not name. A prompt fails when it names one task's files. A task fails when it carries the standing method, or when it does not carry this launch's files.
- Scope says the work is related, or it names what may change and not what to examine. The agent changes a file that the supplier did not mean, or it searches the workspace. A role states a standing remit. Scope is the closed boundary of this launch.
- The done contract says the work looks done, says only to retry, or copies a check that is true of every run of the prompt. The agent stops on a result a second reader would fail, or it asks in a launch that has already ended. Nothing in the launch judges the contract.
- The done contract names the next launch's work. The agent starts that work, and this result is never passed or failed.
- An agent that launches another writes "the file we were reading", or it pastes its own prompt. The launched agent spends the launch on the wrong file, or on reconciling two prompts. The page "Prompt"¹ says what a launch does not include.
- A timer names only the check, or a Slack message is a hint, and the boundary sits in memory or on another subject of the board. The board is the short-term memory that the turn already shows. The agent does that other subject, or it asks and the turn ends.
- The done contract lists two results a reader can pass separately. The agent finishes one and reports the task done.
- A task saved for a later launch is a note of the writing session, or it names a path that only that session had. The later launch follows the note as if the supplier were still there.

## What it is composed of

You write the text of one task. The rbtv program does not install that text, and it is not a file in a component. A person types it in a conversation. An agent passes it when it launches another. A Slack message or a timer supplies it when that message or that timer wakes an Ignite agent for one turn. The launch receives this text beside the prompt.

The text has first lines and two sections, in this order: `## Scope`, then `## Done contract`. Both sections are always there. The first lines state the result of this launch, in ordinary language. They are not a section.

Scope is the boundary of this launch: what to examine, and what may change. The done contract states the conditions a second reader uses to pass or fail the result, and the next action when the result misses them.

A task saved to be done later is this same text in a file that the later launch reads. That file is the task. It is not a list of tasks.

## How to build it

1. **The launch that cannot ask, then the result.** Name who supplies the task. A person supplies it in a conversation. An agent supplies it when it launches another. A Slack message or a timer supplies it when that message or that timer wakes an Ignite agent. Name the launch that will not have the supplier in it. The failure is the work this launch does wrong when the text leaves out this launch's boundary or its done conditions, or when the text puts the supplier's method there instead. The cause is what the supplier can see and the launch cannot: an open file, the supplier's prompt, the turns before this message, or a board subject that is not this work. Then write the first lines from that failure: the result this launch produces, so the failure does not happen. Starting from the two headings produces a text that has both headings and bounds nothing.

   Weak: "Write a review of the failing tests into out/count.txt."

   Strong: "Write the count of failing tests into out/count.txt."

   The weak line names an activity, so the sections that follow have no result to bound.

2. **Carry each input the prompt and the description say this launch has to have.** Read the prompt of the agent that will receive the task. The page "Prompt"¹ names the inputs the procedure uses. Those inputs arrive in the task. Read the description. The page "Agent"² names the inputs that description requires the launch to be given. Write each of them here, as a path or a value that this launch can open. Use the words that the launcher will pass. Do not point at a file that the supplier has open. Do not paste the supplier's prompt. A path that exists on one machine is named in this task, as a path that this launch can open. The prompt does not already know it. When a launch that will receive this task cannot answer a question, do not leave a gap for one. The page "Prompt"¹ names the launches that end before a reply.

   Weak: "The log is the file we were reading from the installation root."

   Strong: "The log is logs/nightly.txt from the installation root."

   The weak line points at the supplier's context. The launch opens a different file, or it asks, and the supplier is not there.

3. **Keep each sentence in one place.** Spell the headings `## Scope` and `## Done contract`, in that order. The agent looks for those words. A renamed heading is still given, and the agent may not find the boundary. The page "Prompt"¹ says which sentences stay in the prompt and out of every task. A sentence that restates the other section makes the agent spend the launch on the disagreement. The first lines state the result. They do not state the boundary, and they do not state a done check. Run the tests of the page "Scaffolding language"³ on each sentence before you stop.

### Scope

**What it is for.** Scope is the boundary of this launch: what to examine, and what may change. It stops the agent from treating related work as in, and from changing a file that the result did not name.

**When the task has it.** Every task has it. A launch that reads no file and changes no file still says so.

**How to write it.** Name what to examine. Name what may change. Keep the two lists separate, and close both: only those names are in, and only the may-change names may change. A name is a file, a folder or a record that this launch can open. "Related", "the rest" and "as needed" are not names. Do not copy the standing remit. Do not state a done check. When the two lists serve two results a reader can pass apart, write two tasks. The page "Keep it stupidly simple"⁴ says a task has one purpose.

Weak: "Examine logs/nightly.txt and the related files. Change out/count.txt only."

Strong: "Examine logs/nightly.txt and tests/nightly.py. Change out/count.txt only."

The weak line leaves the examine list open, so the agent treats a neighboring file as in.

**Checks.** A reviewer who was not in the writing classifies any candidate action as in or out. The two lists are separate and closed. No sentence is true of every task of this agent. No done check.

### Done contract

**What it is for.** The done contract is the standard a second reader uses to pass or fail this result, and the next action when the result misses it. It stops the agent from ending when the work looks done, and from asking in a launch that has ended.

**When the task has it.** Every task has it.

**How to write it.** State each condition as something a reader can observe on the result, without the supplier and without the launch. An exact condition, a number, a date, or whether a file exists, names the tool and the result that passes, as the page "Deterministic first"⁵ says. A condition that needs judgment says what on the result to look at. Do not copy a condition that is true of every run of the prompt, the skill or the command that does the work. On a miss, name the next action this launch can finish: stop and name the miss, or continue with a named change. "Retry" names no change. Do not name the next launch's work. Do not tell this launch to ask and wait when the supplier will not be in it.

Weak: "Done when out/count.txt is one integer and no other file has changed. Retry if not."

Strong: "Done when out/count.txt is one integer and no other file has changed. When logs/nightly.txt is absent, stop and name that missing log."

The weak line gives no next action, so the agent asks in a launch that has ended, or it stops on a result a second reader would fail.

**Checks.** A second reader, with only the result, reaches the same pass or fail. Each exact condition names the tool and the result that passes. Each miss names a next action this launch can finish. No condition is true of every run of the prompt. One result. No next launch's work.

4. **Put the sections where this supplier's launch will read them.** A person in a conversation writes the sections in the message. The turns before that message are not the task. A later launch of another agent does not have those turns, and an Ignite agent has only the recent ones. An agent that launches another writes the sections in the text it passes. It names each file by a path that the launched agent can open. A Slack message that starts the work is the task. Memory and the board arrive with that turn, and they are not the files that this task examines. Name the files in the message. A timer's wake names the check and tells the agent to read the board for the details. Write the first lines, the scope and the done contract in the board entry for that check. The wake name is the name of the check, not the task.

   Weak: "Write the check's name in the board entry for the check the wake names."

   Strong: "Write the scope and the done contract in the board entry for the check the wake names."

   The weak line records the name and not the boundary. The agent reads the board, finds no boundary, and treats another subject as this work.

5. **When you save the task for a later launch, save this text.** The later launch reads the file when it starts. It was not in the writing. A path, an account or a result of the writing session is an input that the later task names, or it is left out. Do not write "as we discussed". An edit after that start does not reach that launch. Change the file before the launch reads it, or write the correction as the next launch's text.

When you edit a task a launch has not yet read, change that text against the same failure. Remove a sentence the result does not need. The agent reads it on this launch and has less attention for the boundary.

When you convert an outside ticket, a user story or a tagged block, keep the failure it was written against. The result becomes the first lines. The boundary becomes Scope. The acceptance criteria become the done contract. A tag that carried the standing method is not a section. The page "Choosing what to build"⁶ decides where that method goes. Drop a heading the result does not need. An outside task often says the work is related, says the work looks done, and pastes a standing check into the done conditions.

When you review, read the task with the supplier's files closed, beside the prompt, as the launch meets it. Classify one action as in or out from Scope alone. Pass or fail a result from the done contract alone. Leave out one input the prompt says the task carries, and see whether the task names the next action.

Checks:

- The first lines state one result this launch produces. Scope has two closed lists, and a reviewer who was not in the writing classifies an action as in or out. The done contract states observations on the result, and a next action on a miss that this launch can finish. No sentence is true of every task of this agent. No sentence points at the supplier's open files or at turns that the launch does not have. A timer's sections are in the board entry the wake names, not in the wake name alone.
- No program reads the sections. A launch that starts shows the text was given. It does not show that a second reader would pass the result, or that an action is in or out.
- Give the prompt and the task to a fresh agent, and withhold the supplier's other files. Look at the files it opens, whether it asks, and whether the result meets the done contract.

## Template

```markdown
<the result this launch produces>

## Scope

Examine: <the closed list of files, folders or records this launch may read>
May change: <the closed list this launch may change; write "no file" when it may change nothing>

## Done contract

<each condition a second reader can observe on the result; an exact condition names the tool and the result that passes>
<on a miss: stop and name the miss, or continue with a named change>
```

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Prompt | [Prompt](prompt.md) | when | writing a task for an agent that has a prompt | take the inputs the procedure expects from the task, and which launches end before a reply |
| 2 | Agent | [Agent](agent.md) | when | the description names what the launch has to be given | take the inputs that description requires |
| 3 | Scaffolding language | [Scaffolding language](scaffolding-language.md) | must | | run its tests on each sentence of the task |
| 4 | Keep it stupidly simple | [Keep it stupidly simple](../principles/keep-it-stupidly-simple.md) | when | the two lists, or the done contract, serve two results | take that a task has one purpose, and write two tasks |
| 5 | Deterministic first | [Deterministic first](../principles/deterministic-first.md) | when | a condition is a number, a date, or whether a file exists | leave that check to the tool, and name the result that passes |
| 6 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | a converted sentence is true of every task of the agent | decide where that sentence goes |
