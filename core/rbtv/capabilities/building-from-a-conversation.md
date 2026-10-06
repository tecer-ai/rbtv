# Building from a conversation

Building from a conversation is the work of writing, from a conversation that just happened, the files that a later agent will follow. The user asks to build from what was done, or to take what was done and turn it into a skill. Outside rbtv, that request is taken as an order to write a skill, and a step that the user did not object to is taken as approved. Here the word that the user uses for the kind is how this page is reached. It is not the choice of kind. A sentence that the user did not settle is not an instruction.

Read this page after the conversation, when creating, and only when the user asks for that work. The page "Tips development"¹ is read before a conversation and during one, and it does not write the files. The two stay separate. Write the files so that a later agent, who was not in the conversation, does the work that the user required after correcting this agent. That agent does not follow a fact that belonged only to this task.

## How it fails

The program can accept a skill, a rule or a command, and a capability page is not checked at all. Either way the extraction can fail. The program does not read the conversation, and it does not compare the files with what the user settled.

- The files follow the path that this agent took, including a step that the user corrected. The next agent repeats the fault.
- A path, an account, a host or a name that appears in the conversation is copied into the files, because it was in the source. It was this task's input. Another task follows it.
- The word that the user used is taken as the kind, so a skill is written when the work is something else.
- The commands of this conversation are written as a script. A later agent runs this task's commands.
- A new file is written when one file already has the method. The next edit has two copies.
- The conversation's several jobs, its story and its corrections are pasted into one file. The next agent reads every job in order to do one of them.
- The whole method is asked again. A settled point is restated, and the restatement changes it.
- Nothing is asked. An open point is written as settled.
- The files are saved because the user confirmed the work. The user has not confirmed the extraction, and a correction that you misread is now the instruction.
- A fact that the user asked to remember, or a lesson inferred from this one conversation, is written into the files. Every later agent follows one installation's fact.

## How to do it

1. **Read the conversation before you write a line, and sort what can become an instruction.** Do not write from what you remember of the work. You did the work, so you will write the path that you took, and you will omit a correction that you already followed. Read the conversation.

   A settled sentence is one that the user stated, confirmed, or corrected you into. A correction is settled: the user rejected the path that you took. The instruction is what the user required after the correction, not that path.

   A fact of this task is a file, a path, an account, a host or a result that this conversation alone had. It is an input that a later task supplies, or it is left out. It is not an instruction.

   An open sentence is one that you inferred, one that the user mentioned and did not settle, or one that the user did not object to. Silence is not a settlement. Mark it open. Do not write it as an instruction.

   A settled sentence becomes an instruction only when a later agent, on a later task of this method, would act differently because of it. A fact that the user asked to remember fails that test. A correction of your behaviour that is not this method fails it too. Neither is an instruction.

   Weak: "Write the steps we followed to produce the report in /home/the-owner/project/out."

   Strong: "Write the step that the user required after correcting the first draft. The folder of this report is an input that the later task names. The guess about the heading, which the user did not confirm, stays open."

   The weak line writes the path that you took and this task's folder, so the next agent repeats the fault and follows that folder.

2. **When a tips record of this conversation exists, read it before you sort a sentence a second time.** The page "Tips development"¹ made the distinctions. Keep each one. Do not write, as an instruction, a sentence that the record left unsettled. After that, read the conversation only to find a correction that the record does not mention. Do not run that page's method on a finished conversation in order to produce a record that you then build from. That page does not write the files, and sorting the sentences a second time drops a distinction that the record already made. When no such record exists, sort the conversation as step 1 says.

3. **Edit the file that already has the method.** Find whether a file already has this method. The page "rbtv command"² says how to list and show what is installed. When one file has the method, edit that file. Read the page "Single source of truth"³ before you write a second copy. You just did the work, so you will not search unless this step says to. A second file leaves the next edit with two copies, and the program accepts both.

4. **The word that the user used does not decide the kind.** The user may say "skill", "command" or "rule". That word is a hint. Decide the kind with the page "Choosing what to build"⁴. Decide the module, the component and the mirror with the page "Choosing where to build"⁵. A path that the conversation names is a fact of this task. It is not a reason to choose the mirror, and it is not a reason to choose the repository. Use the commands that ran in the conversation as evidence when you follow the page "Choosing what to build"⁴. Do not write them as a script because an outside method turns a conversation into a script. A hint that the page rejects is not written.

   Weak: "The user said skill, so write a skill."

   Strong: "The user said skill. Decide the kind with the page "Choosing what to build"⁴, and write the kind that the page gives."

   The weak line treats the request as the decision, so the file is a skill when the work is not.

5. **Write the extraction from the settled sentences only, as what a later agent does.** The later agent was not in the conversation. It does not have this transcript. From the settled sentences of step 1, write the action that the user required, in the order that a later task needs. A correction replaces the step that it rejected. What showed that the step was done becomes the check: the result that the user accepted, not the story of this run. Name a fact of this task as an input that the later task supplies. When that input is absent, the later agent stops and names it, as the page "Cognitive unit"⁶ says. Do not write the story of this run. Do not write an open sentence.

   When the settled sentences are several jobs, and the result of one does not require the next, they are not one file. Do not paste them into one file and then split. The paste is what the program accepts. The page "Writing a capability"⁷ says how one job is written. The page "Nested exposure"⁸ says when several capabilities share one exposure method.

   Weak: "It worked when we ran it on Tuesday's report, so do the same."

   Strong: "The step is done when the file that the task names has one heading and no empty section. Tuesday's report is this task's file, not the check."

   The weak line gives the later agent a story, so it cannot tell a finished result from an unfinished one, and it looks for Tuesday's report.

6. **Ask only what step 1 left open, and only when the answer changes the files.** One round at a time. Each question has named options and one recommendation. A short method needs few questions. Do not ask a point that the conversation settled. A restatement changes the point. Do not skip an open point whose answer changes what the files say. Stop when every such point is settled, or when the user says to leave it out. When the user cannot be reached, do not save. Name the open points, and leave the files unwritten.

   Do not open the skill "Interview"⁹ for the whole method. It asks many questions about an idea that the user has already formed, and its description matches this request. The conversation has already answered the method. Ask only the open points.

   Weak: "Walk me through every step again so I can write the skill."

   Strong: "The conversation settled the steps. It did not settle whether a missing file stops the work or continues. Stop, or continue: I recommend stop, because the correction was about a missing file."

   The weak line asks the method again, so a settled step is restated and the restatement changes it.

7. **Show the extraction, and save only after the user confirms it.** Show three lists: the instructions, taken from the settled sentences; the facts of this task that you will not write; and the open sentences that you left out. Name each instruction as the action that the later agent takes, so the user can reject one line. The user confirmed the work. That confirmation is not a confirmation of these lists. Save only after the user confirms the lists, or corrects them. Then open the page that the page "Choosing what to build"⁴ names for that kind, and write the file as that page says. When the kind is a capability, that page is the page "Writing a capability"⁷. Do not restate how that page writes the file.

   Weak: "The work is done, so I saved the skill."

   Strong: "Here is what I will write, what I will leave out as this task's facts, and what I left open. I have not saved it."

   The weak line treats confirmation of the work as confirmation of the file, so a correction that you misread is saved.

8. **Leave a remembered fact and a one-conversation inference out of every file.** Do not write them into the files of step 7. Do not write `memory/learned.md`, and do not invent another file or a command for them. This agent does not write learned rules. An inferred lesson needs evidence from two conversations before it is a learned rule, and one conversation is not that evidence. A fact that the user asked to remember is not this method. Tell the user you left both out of the files.

- When you edit a file that was built this way: read the conversation again, or the tips record, and change the file against a settled sentence. A change from memory puts the corrected path back.
- When you convert an outside file that was generated from a conversation: sort its sentences as step 1 sorts a conversation. Such a file often has a path of that task, a step that the user later corrected, and a script that the outside method added. The page "Choosing what to build"⁴ decides a part of that file that is not this method.
- When you review: read the files against the conversation, not against the files alone. A review that only reads the files misses an inference that was written as an instruction, because nothing in the files marks that sentence as inferred. Report it as the page "Cognitive unit"⁶ says.

Checks:

- A reviewer sees the three lists that were shown to the user. The saved files contain only the instructions from the settled sentences. No path, account or host of this task is an instruction. No open sentence is an instruction. No fact that the user asked to remember is in the files.
- The kind is the one that the page "Choosing what to build"⁴ gave. An existing file that had the method was edited. Several jobs whose results do not require one another are not one file.
- The program accepts a skill, a rule or a command. Acceptance shows that it recognized the file. It does not show that the file matches the conversation. A capability page is not checked. The page "rbtv command"² says what that run shows for the kind that was written.
- Give the files to an agent that was not in the conversation, with one later task that the files name, and with that task missing one input that the conversation had. Watch whether the agent does the corrected work, whether it follows a fact of the first task, and whether it stops on the missing input.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Tips development | [Tips development](tips-development.md) | when | a tips record of this conversation exists, or you are about to sort the conversation again | take the distinctions that record already made, and do not write the files from that page |
| 2 | rbtv command | [rbtv command](glossary/rbtv-command.md) | when | finding whether a file already has the method, or a run accepts what you wrote | take how to list and show what is installed, and what acceptance shows |
| 3 | Single source of truth | [Single source of truth](principles/single-source-of-truth.md) | when | a second file would repeat a method an existing file already has | take that a fact has one home |
| 4 | Choosing what to build | [Choosing what to build](choosing-what-to-build.md) | when | the user's word names a kind, the conversation ran commands, or a converted part is not this method | decide the kind, and do not treat the word or the commands as the decision |
| 5 | Choosing where to build | [Choosing where to build](choosing-where-to-build.md) | when | placing the files | decide the module, the component and the mirror, without using a path of this task as the reason |
| 6 | Cognitive unit | [Cognitive unit](glossary/cognitive-unit.md) | when | an input may be absent, or a review reports a finding | take the next action when an input is absent, and how a finding is reported |
| 7 | Writing a capability | [Writing a capability](writing-a-capability.md) | when | one job is written as a capability | write that file, and do not restate its steps here |
| 8 | Nested exposure | [Nested exposure](nested-exposure.md) | when | the settled sentences are several jobs that share a purpose or the same documents | take when those jobs share one exposure method |
| 9 | Interview | [Interview](../../../meta/functions/skills/interview.md) | when | you are about to open that skill because its description matches the request | take that it is for an idea that no conversation has settled yet, and ask only the open points |
