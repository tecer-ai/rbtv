---
name: memory-review
description: "CONTAINS: the review of the open questions this agent has collected about the owner's memory: asking them in small groups, capturing each answer, correcting memory when an answer changes a record, and clearing the list PURPOSE: the questions memory could not settle on its own are answered by the owner and the list is empty or holds only what he deferred ALWAYS LOAD WHEN: the owner asks to go through the questions, doubts or pending items this agent has about him or his memory, in any words (\"vamos passar as perguntas\", \"tira suas dúvidas\", \"o que você quer saber de mim?\", \"review your open questions\", \"what do you need me to clarify?\"): open it as the first step, before reading the list DO NOT LOAD WHEN: the owner states a fact or correction on his own (`memory remember`, or the consolidation), or asks to import files (the memory-ingest skill); this skill is not needed for those"
---

Go through the open questions with the owner and leave the list clean. The list is `runtime/albert/open-questions.md` in this agent folder: one line per subject, written by import jobs and by the consolidation when a source names a person, organisation, place or period that memory does not know or cannot place. When the file is absent or empty, say so and stop.

## Ask

Read the whole list and the memory records each question names. Order the questions by the number of sources that mention the subject, highest first. Ask at most five per message, each with the context the owner needs to answer without opening a file: the subject, what the sources say about it in a few words, and the question. Where the sources suggest an answer, offer it as an option to confirm ("Bia is your sister Beatriz?"), never as a fact. The owner may answer some, defer some ("later", "skip") and refuse some ("drop it"); each of the three has its own outcome below.

## Capture each answer

- An answer that settles the question is captured the same turn with `memory remember --installation <root> --agent albert "<the fact in one line, with the owner's words where they matter>"`; the next consolidation publishes it. A fact that names a person goes with the identity it settles (alias, relation, which of two people).
- An answer that changes a published record (a wrong identity, a merged person, a date) is a correction: capture it with `memory remember` as `Owner corrects: <record>. Owner said: <his words>`, so the consolidation replaces the record with his evidence as its source. Never edit the memory file by hand.
- An answer that says two files are one subject (two entity files for one person) is captured the same way; the consolidation folds them.
- A deferred question stays on the list unchanged.
- A refused question ("drop it", "not important") is removed from the list and noted in the reply, so the owner sees what left.

## Clear the list

After each group, rewrite `runtime/albert/open-questions.md` keeping only the deferred lines; this file is operational data of this agent, written directly. Close the session with what was answered, what the consolidation will change, what stays deferred, and what was dropped.
