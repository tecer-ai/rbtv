# Progressive disclosure

Progressive disclosure is the placement of content so that it reaches an agent when the work needs it, even when putting all of it in front of the agent at the start would be easier. The moment is when the agent needs the content.

Outside rbtv, a skill's further files sit in that skill's folder, and the agent reads one when the body names it. Here a further file is a capability¹, and the agent enters through an exposure method². A case that looks close and must not open the thing is `DO NOT LOAD WHEN:`, as the page "Routing table"³ has it. A long work is one file for each phase. A phase starts at a point that a later agent can observe. The later stretch is not needed while the earlier stretch is being done.

Content that reaches the agent before the moment is context load⁴: it competes with the step that the agent is on, and the agent drifts from that step. Content that is absent at the moment is a context gap: the agent guesses the step. An author applies this when the content is needed and the open question is when it arrives. When the question is whether the content is needed at all, read the page "Keep it stupidly simple"⁵. When the question is which file already owns the fact, read the page "Single source of truth"⁶. Apply progressive disclosure so that the content is in front of the agent at the moment, and is not in front of the agent before the moment.

## How it fails

The program can accept the file that the agent enters, and the placement can still fail. It does not read when a sentence arrives. A page in `capabilities/` is not installed.

- The method of a later step sits in the file that the agent already has, because that file was open and the later step will need the method. Every reading contains a step that has not come, and the agent drifts from the step that it is on.
- A pointer names the file and not the moment. The reader opens every named file, or opens none, and two readers open different files.
- A long work is one file, and the phases are headings. A second agent cannot start at the current phase. It has to derive which heading is current, and it reads the phases that it is not in.
- A folder of rbtv has a file whose only job is to list that folder, such as `capabilities.md`, `glossary.md` or `principles.md`, so that items needed at different moments have a home. The reader reads the list and still does not know which file the case needs.
- Each capability has its own exposure method. The agent chooses among them before the work, including on a task that needs none of them, and the choice takes the attention that the task needs. The page "Nested exposure"⁷ has the cases in which nested exposure still fails.
- The description names when to open the thing, and the case that must not open it is a sentence after that, or is absent. The reader opens the thing for a neighbor's job.
- Content whose moment can come on any task, and that the agent would not choose a file for, is kept out of the text that every task has, because the content does not apply on every task. When the point comes, the text is absent. Or the method of that point is pasted into the text that every task has, so every task contains it, and the agent acts where the point has not come.

## How to apply it

1. **The wrong moment, then what this placement does.** Find a task where the content was in front of the agent before the work needed it, or was absent when the work needed it. The cause is a placement made from the file that was open, or from whether the content is needed at all, rather than from the moment. The situation is one task where the content should be in front of the agent, and a second task, or a second reading of the same file, where the content should not. Write the moment as a point that the agent can observe, and write what is absent before that point. The placement then does this: the content reaches the agent at that point, and a task that has not reached the point does not have the content. An author who starts from the file that is open writes a file that the program accepts. The content still arrives at the wrong time. When you cannot name the moment, do not place the content. Decide the file with the page "Choosing what to build"⁸ only after the moment is named.

   Weak: "Put the check in this file, so the agent has it."

   Strong: "The check reaches the agent when the changes are listed. A task that has no list of changes does not have the check."

   The weak line places the check in the file that was open. The agent that is still listing changes reads the check.

2. **In the text that this reading already includes, put only what every such reading needs.** A reading, here, is one agent reading the file, before it opens a file that the text names. A fact, a method or a list that only one case needs goes in the file that case opens. The file that the agent has names that file and when to read it. Text every reading needs, and that another file owns, is not pasted into this reading. Read the page "Entry point"⁹ for the split between that text and a row, and for which file a row names. Read the page "Routing table"³ for the row. On a description, the case that must not open the thing is `DO NOT LOAD WHEN:`, as that page has it. Do not write that case as a sentence after the rest, and do not leave it out of a description. When the harness reads a file on every visit to a folder, that visit is a reading the agent did not choose. Read the page "Folder instructions"¹⁰ for what is its own.

   Weak: "When the changes are listed, run each test and write the failure beside the change."

   Strong: "When the changes are listed, read the check file."

   The weak line puts the next stretch's method in the text that every reading includes. A task that is still listing changes contains the tests.

3. **Split a long work into one file per phase.** Split when a later stretch is not needed while the earlier stretch is being done, and a later agent can name the start of that stretch without reading the earlier file's method. The file the agent has at the start names each phase file and that point, as the page "Entry point"⁹ says. A second agent resumes at the file of the current phase. It does not read the other phases to find which one is current. A heading in the file that the agent already has is not a phase: the same agent reads it in the same sitting, and a second agent cannot be handed that heading without the rest of the file. Do not wait for a line count. A short file can still carry a later phase.

   Weak: "Phase 1 lists the changes. Phase 2 runs the tests. Phase 3 writes the note."

   Strong: "When the changes are listed, read the check file. When the check is written, read the note file."

   The weak line keeps every phase in one file. A second agent derives the current phase from the headings, and it reads the phases that it is not in.

4. **For three common cases, use the page that owns the method.** A list of the files of a folder: rbtv has no index file, and the page "Entry point"⁹ says how the file that the agent entered names each file with its moment. A workspace that has files of its own is not missing an index: the page "Folder artifact"¹¹ says what those files are. One exposure method for each capability: the page "Nested exposure"⁷ says when several capabilities belong under one. Content whose moment can come on any task, and for which the agent would not choose a file: it goes in a rule, and the page "Rule"¹² says how a rule states its point. Do not keep such content out of a rule because it does not apply on every task: the agent acts at the point, and without the text in front of it the point passes unseen.

- When you edit: a sentence added to the file that the agent already has is in every reading of that file. In the same change, name a reading of that file that does not need the sentence. When you can name one, the sentence does not stay there. The program does not ask.
- When you convert: an outside skill whose later files sit in its folder becomes capabilities, each named with the moment, not one file that contains every phase and not one exposure method per file. The page "Capability"¹ says which supporting files stay in the folder of a self-contained skill. A checklist of every phase in one body is how the outside skill was written, and it is not kept. When a part is another kind of thing in rbtv, decide it with the page "Choosing what to build"⁸.
- When you review: take one sentence that every reading of the file contains, and name a reading that does not need it. Then take one later phase and name the file that a second agent would open to resume there. A review that only checks that the file is complete misses a sentence that arrives too early.

Checks:

- A reviewer sees, in the text that a reading already includes, only what every such reading needs. Each later file is named with the point when it is read. A long work has one file per phase, and the point that starts a phase can be matched without reading the other phases. A folder of rbtv has no `capabilities.md`, no `glossary.md` and no `principles.md`. Content whose point can come on any task, and that the agent would not choose a file for, is already in front of the agent, and the method of that point is not in that text.
- The program accepts the file that the agent enters, as the page "rbtv command"¹³ says. Acceptance shows that the file was a skill, a command, a rule or folder instructions. It does not show the moment. A body that contains every phase is accepted the same as a body that names a phase file. A capability page is not installed.
- Give an agent the file that it has at the start of a long work, and a task that is one later phase. It opens that phase's file and does not use another phase's method. Then give a second agent only that phase's file and the same task. It starts at that phase.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Capability | [Capability](../glossary/capability.md) | when | a later file is not the file that the agent entered | take that the file is a capability, and that the program does not install it |
| 2 | Exposure method | [Exposure method](../glossary/exposure-method.md) | when | the agent enters through a file, or you are about to add another | take the four, and that an agent is not one of them |
| 3 | Routing table | [Routing table](../glossary/routing-table.md) | when | writing the case that must not open the thing, or a row | write `DO NOT LOAD WHEN:` and the row |
| 4 | Context window | [Context window](../glossary/context-window.md) | when | naming whether content arrived too early or too late | take context load and context gap |
| 5 | Keep it stupidly simple | [Keep it stupidly simple](keep-it-stupidly-simple.md) | when | the question is whether the content is needed at all | decide that before this placement |
| 6 | Single source of truth | [Single source of truth](single-source-of-truth.md) | when | the question is which file already owns the fact | keep one home, and do not paste a second |
| 7 | Nested exposure | [Nested exposure](../nested-exposure.md) | when | several capabilities share a purpose or the same documents, or each has its own exposure method | take whether they belong under one method, and the cases in which nested exposure still fails |
| 8 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | the moment is named and the file is not yet chosen, or a converted part is another kind of thing in rbtv | decide the file |
| 9 | Entry point | [Entry point](../glossary/entry-point.md) | when | writing the text that every reading includes, a row, or the name of a phase file | write the split and the row, and take which file a row names |
| 10 | Folder instructions | [Folder instructions](../glossary/folder-instructions.md) | when | the harness reads the file on every visit to a folder | take what is its own, and that the visit is not a choice |
| 11 | Folder artifact | [Folder artifact](../glossary/folder-artifact.md) | when | the folder is a workspace that already has its own files | do not treat that structure as a missing index |
| 12 | Rule | [Rule](../glossary/rule.md) | when | the text must already be in front of the agent, and the agent acts at a point | take how the body states the point, and that the body is on every task where the rule is installed |
| 13 | rbtv command | [rbtv command](../glossary/rbtv-command.md) | when | having the program accept the file | find the command to run, and take what acceptance shows |
