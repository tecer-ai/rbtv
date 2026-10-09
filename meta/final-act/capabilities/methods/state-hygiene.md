# State hygiene

A file that a later agent reads to know what to do next shows only what is true now. Such a file is a state: a task list, a file of decisions, a status page, a page an agent follows, or the interface of code. The state names the next action. The history of how the result was reached is kept whole, in a folder of its own, and the state names that folder; the state does not contain it.

The later agent has no memory of the session that wrote the file. It acts on what it reads. A line that is no longer true makes it do something the writer did not mean: repeat a finished task, follow a closed question, edit code no interface reaches, or derive a first action of its own.

Two principles bound this one. [Single source of truth](../../../../core/rbtv/capabilities/principles/single-source-of-truth.md) gives each fact one home; a log can be that home and still fail here, because the home then contains what is no longer to do. The state and the history are kept apart on purpose: the state points to the history folder and does not copy it, since a copy would be a second home, and the history is not deleted to keep the state short, since the history is a stated need. [Keep it stupidly simple](../../../../core/rbtv/capabilities/principles/keep-it-stupidly-simple.md) refuses a part nobody needs; this page says how a superseded design is removed, not whether it was needed.

## How it fails

No program checks these files. A commit of them is accepted, so each failure is found only by the agent it misleads.

- A finished task stays on the list, open or checked. The agent does it again, or cannot tell what is left.
- A decision is written in its home and the question stays in a file the agent reads. The agent follows the question; nothing compares the two files.
- An interface is removed and the code that implemented it stays. A later agent edits it, or a caller still reaches it.
- The state contains the history. The agent derives its first action from the history and derives a different one.
- The history is deleted to keep the state short. How the result was reached is gone.
- The state does not name, in one place and in order, the first action, what is still running and where its result goes, and what waits for whom. The agent works the first action out and gets a different one.
- An old word, field or page is left beside the new one so that readers do not break before the work is finished. The agent follows the old one.
- A page that an agent follows narrates what changed. The agent treats the narration as the design, or spends its reading on it.

## How to apply it

1. **Find the file and the action you did not mean.** Read each file a later agent will act on as that agent meets it, with no memory of the session. The failure is the action it would take that you did not mean; the cause is a line that is no longer true, or a first action that is not written. Write what the file must show so that the action does not happen. A mark added to the old line leaves the line in the file.

2. **Keep the history whole, apart, and named.** The history stays in a folder of its own, in the project, so an agent that has the project can open it; not on one machine only, not excluded from the project. The state names the folder, says what it holds and when to open it. For the folder's path follow [Folder artifact](../../../../core/rbtv/capabilities/glossary/folder-artifact.md); do not write the history into the state while that path is unset.

   Weak: "The state contains the status, the decisions, the findings and the transcripts, so nothing is lost."

   Strong: "The state names the first action. The transcripts stay in the history folder; the state names that folder, what it contains, and when to open it."

3. **Name the first action in one place, in order.** Write, in the state, in this order: what the later agent does first; what is still running and where its result is written; what waits for whom. Write the first action as one order, not as conditions the reader combines. When the first action depends on a condition, write the condition before the order, in the same place; a fact it depends on is one line there, not a list the reader derives from.

   Weak: "Completed: survey, costs. The next agent reads the list and continues in the recommended order."

   Strong: "First, write the pricing file. The files survey and costs are written; do not write them again. Nothing is running. Nothing waits."

4. **Take a finished task off the open list, in the same change.** The list holds only what is still to do. The record of the finished task goes to the history folder the state names, or to the file the workspace already uses for finished work. When neither exists, follow [Folder artifact](../../../../core/rbtv/capabilities/glossary/folder-artifact.md) for the path; do not mark the task done on the list while that path is unset.

   Weak: "Mark the task done and leave it on the list, so the next agent can see it."

   Strong: "Remove the task from the list. Put its record in the history folder the state names, in the same change."

5. **When the decision is in its home, delete the question.** In the same change as the decision is written, delete the open question, its placeholder, every reference that still presents it as open, and any hint recorded under it. Leave none in a file a later agent reads. Attempts that are not the reason of the decision stay in the history folder.

   Weak: "The decision is in its home. The open question stays in the plan, marked resolved, so the reader can see what was tried."

   Strong: "The decision and its reason are in its home. The open question and the plan line that still asks it are deleted in the same change."

6. **Remove the implementation with the interface.** When a verb, parameter, command or page leaves what is invoked or followed, remove the code that implemented it and every caller, in the same change. Search for the name. A function no remaining interface calls does not stay and is not commented out; the program still starts when nothing calls it.

   Weak: "The verb is gone from the help. The function stays, with a comment that it is unused, until the callers are updated."

   Strong: "The verb is gone from the help. The function and every caller are gone in the same change."

7. **One design, in the same change.** Decide the one word, field or page for each thing a later agent acts on, and change every such file to it in the same change. Do not leave the old one in place so that a reader that still uses it does not break; that is two designs, and the later agent follows the old one. A name the design still uses is not this case; when you cannot tell, ask, and do not delete a name the design still uses.

   Weak: "The new page is written. The old page stays until every link is updated, so nothing breaks."

   Strong: "The new page is the only page. Every link names it, and the old page is gone, in the same change."

8. **A page an agent follows describes the design as it is.** Delete a sentence whose only job is to say what a file used to be called, where it was copied from, or which earlier design did the work differently. When a comparison with an earlier design is required, write it in the file of decisions and replace the superseded decision; do not append the new one after the old, and do not put the comparison in the page.

   Weak: "This file replaces the older memo, which was copied from the previous workflow on 21 August."

   Strong: "This file is the only record of where the run is. It names the first action."

## Checks

- In the state, one place names in order the first action, what is still running and where its result is written, and what waits for whom. The state does not contain the history; when a history folder exists, the state names it, what it holds and when to open it, and the folder is in the project.
- The list a later agent treats as open has no finished task. No resolved question is still asked in a file the agent reads. No removed interface has code only it called. No old interface sits beside the new one for safety. No page an agent follows narrates what changed.
- Give the state to a reader who has not seen the work and ask what it would do first, what it thinks is still running, and what it would open the history for. The answers are what the writer meant. Give that reader the history folder alone: the first action is not in it.
