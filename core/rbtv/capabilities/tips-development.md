# Tips development

Record decisions, observations, interpretations and open questions while the task is underway, without replacing the task with a new build. The record lets a later reader distinguish what the owner authorized from what the agent inferred.

Before the conversation, name the subject and a nearby subject excluded from it. Save the record as `build/tips/<subject>.md` in the task's project, not beside this guide in rbtv. When the task already specifies the subject, confirm it briefly rather than opening another interview.

## Capture and return to the task

For each tip, record who said or observed it, its kind and enough of the passage to preserve its meaning. Keep these distinctions:

- A stated need, preference or possibility is not automatically a decision.
- A report from the owner is attributed to the owner. A test the agent observed is separate evidence.
- An expectation inferred from a correction, obstacle or reaction is an **interpretation**. If it changes scope or calls for a new action, ask before acting on it.
- Separate the need, proposed mechanism and authorization. A proposal alone does not authorize implementation, external contact, a wider test or a scope change.

If the line has two plausible readings, keep both and mark the doubt. Confirm the tip in a few bullets and accept corrections; do not interview the owner for every tip. Omit fields that add nothing to the distinction. Then return to the task and continue capture until the owner ends the conversation.

Fix an obstacle only within the current authorized task. Recording a future tool or file layout does not authorize building it or investigating a product that does not exist. Turning a completed conversation into reusable instructions is separate work under [Building from a conversation](building-from-a-conversation.md).

## Keep the evidence and its limits

Record what happened, who observed it, under which conditions and what was not shown. Prefer identifiers and results emitted by the tool over prose copies. Acceptance of a send does not establish delivery, reading, response or completion. Compare what the user experienced with what the component did before claiming the need was met.

When environments differ, carry forward the need and success criterion rather than assuming the local mechanism transfers. Do not turn a product's operating details into the general method.

One occurrence supports a hypothesis, not a universal principle. A candidate is ready for later principle-writing only when there is a second comparable case, declared limits, a recognizable condition, an observable effect and a failure that could refute it. Record the need the mechanism serves. Calling the candidate ready does not create the principle page or authorize it.

A request for a later principle page is recorded without interrupting the current task. If the owner explicitly changes the active task to writing that page, follow that instruction and [Choosing what to build](choosing-what-to-build.md); capture itself grants no such change.

## Corrections and moved subjects

Preserve an earlier formulation with the period when it governed, and mark the corrected formulation and when it takes effect. This record is history; the file that owns current state must separately say only what governs now. Do not rewrite the history to pretend the earlier decision never existed.

When a subject moves elsewhere, retain the learning relevant here and a pointer. Its current decisions, evidence, hypotheses and execution limits move to their own home under [Single source of truth](principles/single-source-of-truth.md). Do not duplicate them or continue that subject's tests from this record merely because it was moved.

## Close and review

When the owner ends the conversation, have a second agent read the transcript for missed tips within this subject. It records additions with the same distinctions and limits. The original agent's rereading is not a substitute for this independent pass. Ending capture does not authorize creating a skill, rule, command or prompt.

When converting an outside decision log, separate decisions from inferences, retain untested conditions and remove product-specific detail presented as general method. On review, a reader without the conversation must be able to identify each tip's kind, authorization and evidence limits. Test an ambiguous line: both readings should remain open and capture should not trigger an unauthorized build. Installer acceptance says nothing about this record.
