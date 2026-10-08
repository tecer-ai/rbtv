# State hygiene

State hygiene is the rule that each file that a later agent acts on shows what is true now. The state is the file that the later agent reads to know what to do next, and the state names that next action. Outside rbtv, the state often keeps every finished task, every closed question and the history of how the work was done. Here the history is kept whole, in a folder of its own, and the state names that folder. The state does not contain the history.

A later agent has no memory of the session that wrote the files. It acts on what it reads. Apply this principle when you leave a task list, a file of decisions, a state, a page that an agent follows, or code whose interface you changed. Apply it so that a reader with no memory of the writing does the first action you meant, and does not treat a finished task, a closed question or a removed interface as still in force.

The page [Single source of truth](../../../../core/rbtv/capabilities/principles/single-source-of-truth.md) gives each fact one home. A log can be that one home and still fail this principle, because the home then contains what is no longer to do. This principle keeps the state and the history apart on purpose. The state points to the history folder. It does not copy the history. A copy would give the history two homes, which that page refuses. Deleting the history so the state stays short also fails this principle.

The page [Keep it stupidly simple](../../../../core/rbtv/capabilities/principles/keep-it-stupidly-simple.md) refuses a part nobody has stated a need for. The history is a stated need, so this principle does not delete it to shorten the state. This principle also refuses an old word, an old field or an old page left beside the new one so that nothing breaks before the work is finished. That pair is two designs in the files that an agent acts on. What remains is one design, written in the same change. That page refuses the part that nobody needs. This page says how the old design is removed.

## How it fails

No program reads a task list, a file of decisions, a state or a page for this failure. A commit of those files is accepted.

- A finished task stays on the list that the later agent treats as open, marked done or still open. The agent does the task again, or it cannot tell what is left.
- A decision is written in its home, and the open question stays in a file that the agent still reads. The agent follows the question. Nothing compares the two files.
- An interface is removed from what is invoked, and the code that implemented it stays. A later agent edits that code, or a caller still reaches it. The program that remains still starts.
- The state contains the history of how the work was done. The later agent derives its first action from that history and derives a different one.
- The history is deleted so the state stays short. How the result was reached is gone.
- The state says what is true and does not name, in one place and in order, the first action, what is still running and where that result is written, and what waits for whom. The reader can work the first action out, and works out a different one.
- An old word, an old field or an old page is left beside the new one so that existing readers do not break before the work is finished. The later agent follows the old one.
- A page that an agent follows narrates what changed. The agent treats the narration as the design, or spends the reading on the narration.

## How to apply it

1. **Name the file that the later agent acts on, and the action you did not mean.** Find a file that a later agent will read to know what to do, or to follow a design. Read it as that agent meets it, with no memory of the session that wrote it. The failure is the action that the agent takes and that you did not mean. The agent repeats a finished task, follows a closed question, edits code that no interface reaches, or derives a first action that you did not mean. The cause is a line that is no longer true, or a first action that is not written. The situation is that reading. Then write what the file must show so that the action does not happen. Adding a mark to the old line leaves the line in the file that the agent reads.

2. **Keep the history whole, apart from the state, and point to it.** The state says only what is true now. The history of how the result was reached stays whole in a folder of its own. The two never share a file. The folder is in the project, so a later agent that has the project can open it. Do not keep the folder only on one machine, and do not exclude it from the project. When the folder exists, the state names it, says what it contains, and says when to open it. Do not copy the history into the state. Do not delete the history so the state stays short. For the path of the folder, follow the page [Folder artifact](../../../../core/rbtv/capabilities/glossary/folder-artifact.md). Do not write the history into the state while that path is unset. When the folder is a folder artifact, write it as that page says.

   Weak: "The state contains the status, the decisions, the findings and the transcripts, so nothing is lost."

   Strong: "The state names the first action. The transcripts stay in the history folder. The state names that folder, what it contains, and when to open it."

   The weak line puts the history in the file that the later agent reads to know what to do next.

3. **Name the first action in one place, in order.** In the state, in one place, write in this order: what the later agent does first; what is still running, and where that result is written; what waits for whom. Write the first action as one order, so that the reader does not derive it from several conditions. When the first action depends on a condition, write the condition before the order, in that same place. A fact the first action depends on is one line there, such as which files are already written. It is not a list the reader uses to derive the first action.

   Then give the state to a reader who has no memory of the work. Ask what that reader would do first, what it thinks is still running, and what it would open the history for. When any answer is not what you meant, rewrite that place, and ask again. The test is this comparison. It applies to every state, not only to a file written for a handoff.

   Weak: "Completed: survey, costs. The next agent reads the list and continues in the recommended order."

   Strong: "First, write the pricing file. The files survey and costs are written. Do not write them again. Nothing is running. Nothing waits."

   The weak line makes the reader derive the first action.

4. **Take a finished task off the list that the later agent treats as open, in the same change.** When a task recorded in the repository is finished, remove it from that list in the same change. The list contains only what is still to do. Put the record of the finished task in the history folder that the state names, or in the file that this workspace already uses for finished work. Do not leave the task on the list as a checked line. When neither file exists, follow the page [Folder artifact](../../../../core/rbtv/capabilities/glossary/folder-artifact.md) for the path. Do not mark the task done on the list while that path is unset.

   Weak: "Mark the task done and leave it on the list, so the next agent can see it."

   Strong: "Remove the task from the list that the later agent treats as open. Put its record in the history folder that the state names, in the same change."

   The weak line keeps the finished task on the list that the later agent treats as open.

5. **When the decision is in its home, delete the question.** The page [Single source of truth](../../../../core/rbtv/capabilities/principles/single-source-of-truth.md) says where the fact lives. A text that states the fact matches that home. In the same change as the decision is written in its home, delete the open question, the placeholder, and every reference that still presents the question as open. A hint recorded under the question goes with the question. Leave none of them in a file that the later agent reads. Two readings of one question are two interpretations, and nothing compares the files. When the file of decisions is a folder artifact, write it as the page [Folder artifact](../../../../core/rbtv/capabilities/glossary/folder-artifact.md) says.

   Weak: "The decision is in its home. The open question stays in the plan, marked resolved, so the reader can see what was tried."

   Strong: "The decision and its reason stay in its home. The open question, and the line in the plan that still asks it, are deleted in the same change. Attempts that are not the reason of the decision stay in the history folder."

   The weak line leaves the resolved question in a file that the agent reads, where it still reads as open.

6. **Remove the implementation with the interface, in the same change.** When you remove a verb, a parameter, a command or a page from what is invoked or followed, remove the code that implemented it and every caller of that code. Search for the name. A function that no remaining interface calls does not stay, and it is not commented out. Commenting it out leaves it in the file that a later agent reads. The program that remains still starts when nothing calls the function.

   Weak: "The verb is gone from the help. The function stays, with a comment that it is unused, until the callers are updated."

   Strong: "The verb is gone from the help. The function and every caller are gone in the same change."

   The weak line leaves the implementation in a file that a later agent reads.

7. **Do not leave the old beside the new until the work is finished.** Decide the one design first: one word, one field, one page, for each thing that a later agent acts on. Change every such file to that one design in the same change. Do not leave the old word, the old field or the old page in place so that a reader that still uses it does not break before the work is finished. That pair is two designs, and the later agent follows the old one. An old name that the design still uses is not this case. When you cannot tell whether the old name is still the design, ask. Do not delete a name that the design still uses.

   Weak: "The new page is written. The old page stays until every link is updated, so nothing breaks."

   Strong: "The new page is the only page. Every link names it, and the old page is gone, in the same change."

   The weak line leaves two pages that a later agent can follow.

8. **A page that an agent follows describes the design as it is.** Delete a sentence whose only job is to say what a file used to be called, where the file was copied from, or which earlier design did the work differently. The later agent treats that sentence as the design, or spends the reading on that sentence. When a comparison with an earlier design is required, write it in the file of decisions, and replace a superseded decision. Do not append the new decision after the old one. Do not put the comparison in the page.

   Weak: "This file replaces the older memo, which was copied from the previous workflow on 21 August."

   Strong: "This file is the only record of where the run is. It names the first action. It does not say which file it replaced."

   The weak line says where the file was copied from, which the later agent does not need in order to act.

Checks:

- A reviewer sees, in the state, one place that names in order the first action, what is still running and where that result is written, and what waits for whom. The state does not contain the history. When a history folder exists, the state names it, what it contains, and when to open it. The folder is in the project. The list that the later agent treats as open has no finished task. A resolved question is not still asked in a file that the agent reads. A removed interface has no remaining code that only that interface called. No old interface sits beside the new one only so that nothing breaks before the work is finished. A page that an agent follows does not narrate what changed.
- No program reads these files for this failure. A file that is present shows that it was written. It does not show that a later agent does the first action the writer meant, or that the history was kept.
- Give the state to a reader who has not seen the work. Look at what that reader would do first, what it thinks is still running, and what it would open the history for. The answers are what the writer meant. Then give that reader the history folder alone. The first action is not in that folder.
