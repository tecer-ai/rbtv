---
name: communication
description: "CONTAINS: concise writing, readable names and explanations, and decision questions PURPOSE: chat and documents understood on first reading ALWAYS LOAD WHEN: an agent writes to people or writes documents and instructions that people may read DO NOT LOAD WHEN: an agent produces only machine-readable records under a fixed format"
---

# Communication

When writing chat, documents or instructions for agents, use the fewest words that preserve the requirements, decisions, necessary reasoning and uncertainty. Treat documents as human-readable even when their immediate reader is an agent. Preserve exact syntax and values in code, commands, quoted evidence and machine-readable records.

## Write for understanding

- Lead with the result, decision or action the reader needs. Add the evidence and explanation needed to assess it.
- Remove repetition, filler and commentary about the writing itself. Do not shorten a document by making its reader reconstruct a missing requirement or reason.
- Use familiar words and established terminology. Explain an unfamiliar term on first use; repeat the explanation only when the reader needs it. An analogy may support a clear explanation when it helps, but must not replace the actual behavior.
- Refer to work by its readable title or purpose. Include an exact identifier or technical name when needed to locate or operate something, alongside its readable description. Do not require the reader to remember numbered tasks, steps or project codes.
- Spell out an unfamiliar acronym on first use and explain its meaning when the expanded words do not make it clear. Use the readable term thereafter unless the abbreviation helps the reader.
- Describe technical decisions through their effects: what the system does and what the user will see, gain or lose. Keep implementation details that help the reader make the decision or verify the result.
- Use connected prose for an explanation, lists for parallel items or steps, and tables for comparisons. Follow the document's required format without adding headings or summaries that merely repeat its content.

## Chat and speech

Give the conclusion and the information needed for the next decision in chat. Link to supporting files instead of pasting long contents or logs. The message must still make sense without opening those files.

For speech, state the outcome and necessary reasoning in sentences the listener can follow. Put paths, identifiers, tables and text the user must copy in accompanying written material.

On Slack, keep one topic per message and reply in the thread where the request arrived. Start a message needing the owner's answer with `❓`; start optional reasoning, grounding notes and progress remarks with `💭`. Keep an ask separate from an optional note and omit decorative emoji, including a thread marker.

## Questions

Ask only for information or decisions the task does not already settle. Ask no more than five questions at once. For a decision, give named options with their consequences and recommend one with a reason. Ask a direct factual question when options would invent the missing fact. An explicitly requested interview or other question method follows its own protocol.
