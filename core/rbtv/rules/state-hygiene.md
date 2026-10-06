---
name: state-hygiene
description: "CONTAINS: the orders that apply when a file a later agent acts on is about to be left behind: a task list, a file of decisions, a state, a page an agent follows, code whose interface changed PURPOSE: a later agent that reads such a file does the first action the writer meant, and treats no finished task, closed question or removed interface as still in force ALWAYS LOAD WHEN: the agent writes or leaves files that a later agent will read to know what to do next DO NOT LOAD WHEN: the agent's work writes no file that a later agent acts on"
---

The point comes when you are about to leave a file that a later agent will read to know what to do next: a task list, a file of decisions, a state, a page that an agent follows, or code whose interface you changed. When that point has not come, this rule asks nothing.

When it comes, before you end the change:

- Take a finished task off the list that a later agent treats as open, in the same change. A checked line on that list is still a line that the agent reads. The record of the finished task goes in the history folder that the state names, or in the file this workspace uses for finished work.
- When a decision is written in its home, delete the open question, its placeholder and every line that still presents it as open, in the same change. Two readings of one question are two interpretations.
- When you remove a verb, a parameter, a command or a page from what is invoked or followed, remove the code that implemented it and every caller, in the same change. A function that is commented out is still read.
- The state says only what is true now, and names in one place, in order: what the later agent does first, what is still running and where its result is written, and what waits for whom. The history of how the result was reached stays whole in a folder of its own, in the project, and the state names that folder. Do not copy the history into the state, and do not delete it to keep the state short.
- Do not leave the old word, field or page beside the new one so that nothing breaks before the work is finished. Change every file that a later agent acts on to the one design, in the same change. A name that the design still uses is not this case; when you cannot tell, ask.
- A page that an agent follows describes the design as it is. Delete a sentence whose only job is to say what the file used to be called or where it was copied from; a comparison with an earlier design goes in the file of decisions, where a superseded decision is replaced, not appended.

Then give the state to a reader with no memory of the work, and ask what it would do first, what it thinks is still running, and what it would open the history for. When an answer is not what you meant, rewrite that place.
