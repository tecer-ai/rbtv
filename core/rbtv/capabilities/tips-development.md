# Tips development

Tips development is the work of recording, while a task is still going, what the owner decided, what happened, what was inferred and what is still open. The record starts before the conversation. It accompanies the task and does not replace it. It does not become a skill, a rule, a command or a prompt. An interpretation is a need inferred from a line, a correction, an obstacle or a reaction. It is not a decision.

A later reader was not in the conversation. Name the subject before the first tip, then record each tip while the task is still going. Record each tip so that the later reader can name who said it, what kind it is, what was authorized and what was not shown.

## How it fails

The program does not read the record. A record that mixes a decision with an interpretation remains, and a later reader acts on the mix.

- The subject is not named before the conversation. A tip about another subject is recorded in this file. The later reader applies it to this subject.
- The record is written next to this page, in the rbtv component. Another project's task never sees it, or a tip about one project is read as a fact of rbtv.
- The agent stops the task to investigate a product that does not exist yet, or writes a skill, a rule, a command or a prompt. The task the owner is doing stops.
- An interpretation is written as a decision. The task's scope changes without the owner.
- One reading of an ambiguous line is kept, and the other is dropped. The later reader treats a preference as a decision.
- The need, the proposed mechanism and the authorization are one sentence. A later agent builds, contacts someone outside the task, widens a test, or changes the task's scope.
- The prose copy of a name is the evidence, or a tool's acceptance is treated as the person having received the result. The later reader trusts a result that was not shown.
- One occurrence is written as a principle for every case. The later reader applies it outside the case that was observed.
- A product's operating detail is written as this method. The later reader follows that product's steps as if they were this work.
- A correction replaces the earlier line. The record no longer shows that the earlier decision existed.
- The conversation ends, and the agent that missed a tip is the only reader of the transcript. The missed tip stays missing.

## How to do it

1. **Before the conversation, name what the later reader would mix, then the subject and the file.** The task is about to start. The failure this record corrects is a later reader who cannot tell a decision, what happened, an interpretation and an open question apart. The same failure is a tip about another subject read as a decision about this one. The cause is a line whose subject and kind were not written while the task was still going. Write the subject of this file, and name the other subject that must not be recorded here. When the task already states the subject, write it and confirm it in a few bullets. Do not open a round of questions before the task starts. The file is `build/tips/<subject>.md` in the project of the task. The project is the folder of that work. This page lives in the rbtv component. The record does not. A field that does not clarify the tip is left out. A few lines are enough when the four can still be told apart.

   Weak: "This file records what the task teaches about the principle pages. Write it next to this page."

   Strong: "This file records what the task teaches about the principle pages. Write it at `build/tips/principle-pages.md` in the project of the task."

   The weak line puts one project's tips in the component, so another project never sees them.

2. **Record the tip and return to the task.** Write enough to keep the tip, then return. Keep recording until the owner says the conversation has ended. An obstacle that blocks this task gets a local fix. The fix is for this task. It is not an investigation of a product that does not exist yet, and it is not a skill, a rule, a command or a prompt. When the owner later asks to turn the conversation into one of those four, that work is the page "Building from a conversation"¹.

   Weak: "The owner named a file layout for a later tool and asked that the tip be recorded before any build. Start the tool, and return to the task after it."

   Strong: "The owner named a file layout for a later tool and asked that the tip be recorded before any build. Record the direction. Return to the task. Do not build the tool."

   The weak line replaces the task with a build the owner did not authorize.

3. **Write the kind of the line, and mark an interpretation.** An explicit line can name a need, a preference, a decision, or only a possibility. A preference is not a decision. A report and an observation are what happened. An indirect tip appears when a correction, an obstacle or a reaction shows an expectation the proposal did not state. Mark the expectation you inferred as an interpretation. Write the passage. When you do not have the passage, write its sense, and do not add a requirement. Write who said it, or who observed it. When the interpretation would change the task's scope, or would require a new action, ask the owner. Do not write it as a requirement.

   Weak: "The owner said the file was written and the next agent did not find it. Requirement: the tool must push the file to the next agent."

   Strong: "The owner said the file was written and the next agent did not find it. Interpretation: writing the file and the next agent finding it are not the same. Ask before any new action."

   The weak line promotes the interpretation to a requirement, so the task's scope changes without the owner.

4. **Write the need, the mechanism and the authorization apart.** A tip, even a specific one, is not consent to implement, to contact someone outside the task, to widen a test, or to change the task's scope. A decision exists only when the owner took it, or authorized it, at that scope. A later authorization does not extend to a scope the owner did not name.

   Weak: "Need: the direction has no home. Mechanism proposed: one shared file. Authorized now: record the tip and build the shared file."

   Strong: "Need: the direction has no home. Mechanism proposed: one shared file. Authorized now: record the tip. The shared file is not authorized."

   The weak line treats the proposed mechanism as authorized.

5. **Confirm the tip in a few bullets, and keep both readings when the line is ambiguous.** Show the owner the tip in a few bullets, and take the correction. Do not interview the owner for each tip, because the task is still going. When the line can be read two ways, write both and the doubt. Do not pick one.

   Weak: "The line can mean a preference or a decision. Recorded as the decision."

   Strong: "The line can mean a preference or a decision. Both are in the record. The doubt is open."

   The weak line drops one reading, so a later reader treats a preference as a decision.

6. **Write what was observed, by whom, under which conditions, and what was not shown.** A report the owner gives is attributed to the owner. A test you watched is a different kind of evidence. Prefer the line that a tool wrote over a prose copy of a name. A tool accepting what was sent does not show that the recipient got it, read it, answered, or finished the task. Do not write that the result met the need until what the user perceived has been compared with what the component did. Name the conditions that were not exercised. When another tool or another environment could change the mechanism, carry the need and the criterion of success. Do not carry the local fix by habit.

   Weak: "Observed: one run, confirmed by the name that was copied into the record."

   Strong: "Observed: one run, confirmed by the tool's own line. The name in the prose omitted a part. The tool's line is the evidence."

   The weak line prefers the prose copy, so a later reader trusts a name the tool did not confirm.

7. **A candidate principle states the need the mechanism was meant to meet. One occurrence is not a principle page.** Write a candidate principle when the material is there. Do not write a principle page from this record. The record may call a candidate ready for a later page only when a second comparable case exists, the limits are declared, a reader can recognize the condition, a reader can observe the effect, and a failure can refute it. Calling it ready is not writing the page. One occurrence can justify a hypothesis. It does not justify a rule for every case. Do not copy a product's operating detail into this record as the method. When the owner asks for a principle page while the task is still going, record the request as a decision and return to the task. Do not write the page then. When the owner asks after the conversation has ended, stop this work. Decide the file with the page "Choosing what to build"².

   Weak: "Principle: the next agent always finds the file, on every machine."

   Strong: "Candidate: the next agent has to find the file, not only the tool that wrote it. One case. Limits: this task, this machine. Not a principle page."

   The weak line makes one case a rule for every machine.

8. **When the owner corrects a line, keep the earlier formulation with the time when it governed.** Write the formulation that now governs, and from when it governs. Keep the earlier formulation, with the time when it governed. A correction does not erase that the earlier decision existed. The product's current state is in the file that owns that state. This record is not that file. Do not rewrite an earlier tip so that the file shows only what is true now.

   Weak: "The scope is the named action. The earlier line is replaced."

   Strong: "Until the correction, the scope was record only. From the correction, one named action is authorized. The earlier line stays, with the time when it governed."

   The weak line erases the earlier decision, so a later reader cannot tell what governed then.

9. **When the owner moves a subject out of this file, keep the learning and the pointer.** Keep the learning that a later reader of this subject still needs. Add a pointer to the file that now owns the moved subject's current state. The decisions, the evidence, the hypotheses and the limits of execution go with that file. Do not restate them here. The page "Single source of truth"³ says a fact stays in its home. Do not continue the moved subject's tests from this file. Moving the subject is not authorization to keep operating it here.

   Weak: "The owner moved the subject. This file keeps the learning and continues the subject's tests."

   Strong: "The owner moved the subject. This file keeps the learning and the pointer. The subject's decisions and evidence go with its file. Do not continue its tests from here."

   The weak line treats the move as authorization to keep operating the subject.

10. **When the owner says the conversation has ended, a second agent reads the transcript for a tip that the first agent did not record.** The second agent writes each added tip as steps 3 to 7 say. It adds nothing outside the subject. The end of the conversation is not a request to write a skill, a rule, a command or a prompt. That request is the page "Building from a conversation"¹. The first agent does not do this reading as a substitute. The agent that missed the tip does not see the miss.

   Weak: "The first agent reads the transcript and adds the in-subject tip that it did not record, with its kind and its limit."

   Strong: "A second agent reads the transcript and adds the in-subject tip that the first agent did not record, with its kind and its limit."

   The weak line leaves the miss to the agent that missed it, so the miss stays.

- When you edit: change the tip in this file. When the edit changes a fact that a page owns, change that page, as the page "Single source of truth"³ says. Do not edit a copy of the tip that was pasted into a skill, a rule, a command or a prompt.
- When you convert an outside decision log: split a sentence that joins a decision and an inference. Name the condition that was not shown. Drop a product's operating detail. When the log contains a skill, a rule, a command or a prompt to write, do not write that file from the log. Decide it with the page "Choosing what to build"².
- When you review: read the file as a later reader who was not in the conversation. For each tip, name the kind, the authorization and what was not shown. When you cannot name one of the three, the tip fails. A review that only says the file exists has not reviewed the record.

Checks:

- A reviewer sees the subject, the other subject that must not be recorded here, and the file path, before any tip. Each tip names who said it or who observed it, its kind, the need apart from the mechanism, what was authorized, and what was not shown. An inferred need is marked as an interpretation. An earlier formulation that was corrected is still in the file, with the time when it governed. No skill, rule, command or prompt was written from the conversation. No product's operating detail is stated as this method. The file is in the project of the task, not next to this page.
- The program does not read the file. A run that accepts a component shows nothing about this record. The page "rbtv command"⁴ says what that run shows.
- Give an agent this page, a task that is still going, and one line that can be read as a decision or as a possibility. The agent records both readings, returns to the task, and does not build what the line named. Then the owner ends the conversation. A second agent adds a tip that the first agent did not record, and adds nothing outside the subject.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Building from a conversation | [Building from a conversation](building-from-a-conversation.md) | when | the owner asks to turn the conversation into a skill, a rule, a command or a prompt | do that work there, not from a tip |
| 2 | Choosing what to build | [Choosing what to build](choosing-what-to-build.md) | when | the owner asks for a principle page after the conversation, or an outside log contains a skill, a rule, a command or a prompt to write | decide the file, and do not write it from this record |
| 3 | Single source of truth | [Single source of truth](principles/single-source-of-truth.md) | when | a fact in a tip already has a home, a subject has moved, or an edit changes a fact that a page owns | leave the fact in its home, and change that page |
| 4 | rbtv command | [rbtv command](glossary/rbtv-command.md) | when | a run that accepts a component is taken as a check of the record | take what that run shows, and what it does not show for this file |
