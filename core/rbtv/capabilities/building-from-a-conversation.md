# Building from a conversation

Use this method when the user asks to turn a completed conversation into reusable instructions. Build the method the user settled, including corrections, so a later agent can perform it on another task without the transcript.

The request's word “skill” or “command” does not determine the result's kind. Nor does a successful task mean every step taken during it was approved. [Tips development](tips-development.md) covers capture during a conversation; it does not perform this extraction.

## Establish what was settled

Read the conversation rather than reconstructing it from memory. If a tips record exists, retain its distinctions and read the conversation for corrections it missed; do not run the capture process retrospectively just to create another intermediate record.

Separate three things:

- **Settled instructions:** what the user stated, confirmed or corrected the agent into doing. Keep a statement as an instruction only if it changes how a later agent performs this method. A correction replaces the rejected step.
- **Task-specific facts:** paths, accounts, hosts, names and results particular to that run. Turn needed values into inputs supplied by the later task; leave the others out.
- **Open points:** inferences, possibilities and statements the user neither settled nor objected to. Silence does not settle them. Keep them out of the instructions until resolved.

A remembered personal fact or a correction unrelated to this method does not become part of it. Do not write learned rules, `memory/learned.md` or an invented destination for them. One conversation is insufficient evidence for an inferred learned rule; that requires at least two conversations. Tell the user what was excluded.

## Select and draft the result

Search for an existing file that owns the method before creating another. Use [rbtv CLI](glossary/rbtv-cli.md) to list or show installed material when needed. Edit the existing home rather than maintaining a second method.

Use [Choosing what to build](choosing-what-to-build.md) for the kind and [Choosing where to build](choosing-where-to-build.md) for its location. Commands run during the conversation are evidence, not automatically a reusable script. A task's path does not decide whether the result belongs in the repository or mirror.

Draft only the settled actions, in the order a later task needs. Use the accepted result as the completion check, not the story of the successful run. Name required inputs and what happens when they are missing, following [Cognitive unit](glossary/cognitive-unit.md).

Separate independent jobs before drafting. Use [Writing a capability](writing-a-capability.md) for each method and [Nested exposure](nested-exposure.md) if several belong under one exposure method. Do not paste the transcript into one file and call its chronology the procedure.

## Resolve gaps and confirm the extraction

Ask only open questions whose answers would change the result. Present named options and a recommendation, one round at a time. Do not reopen the whole method through an interview when the conversation already settled it. Stop questioning when relevant points are settled or the user says to omit them. If the user is unavailable and a necessary point remains open, report it and leave the source files unwritten.

Before saving the extracted source, show the user the proposed instructions, task facts excluded or made inputs, and unresolved statements left out. Each instruction should be an action the later agent can take. Confirmation of the original work is not confirmation of a new extraction. Use the user's confirmation or corrections, then write through the entry for the selected kind. Honor explicit authorization already given for that extraction; do not ask for the same approval again.

## Verify against the source conversation

On edit, compare changes with settled statements or the tips record. On conversion, check for task-specific values, superseded steps and scripts added by the outside extraction method. On review, compare the output with the conversation; the output alone cannot reveal an inference presented as a decision.

Give a fresh agent a different task under the method, including a missing input. Check that it follows the corrected method, uses the new task's values and handles the missing input as instructed. Installer acceptance proves neither fidelity to the conversation nor successful reuse.
