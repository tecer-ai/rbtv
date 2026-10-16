---
name: memory-ingest
description: "CONTAINS: the method for importing memory from existing files the owner points to (documents, transcripts, notes, exported chats): one reader per source, a check of risky readings, reconciliation and a `memory migrate` manifest PURPOSE: memory records that each cite their source file and lines, published with rollback and without touching the recurring consolidation ALWAYS LOAD WHEN: the owner asks to import, ingest or learn from material that already exists (\"ingest these files\", \"import my transcripts into memory\", \"look at my folder and understand me\", \"importa pra memória\", \"read my notes and remember them\"): open it as the first step, before reading the sources DO NOT LOAD WHEN: a scheduled consolidation of new conversation evidence (the albert tool's prepare and apply), or saving one fact the owner just stated (`memory remember`); this skill is not needed for either"
---

Import memory from files the owner selected. Every record cites its source file, hash and lines, and is published through `memory migrate`; `memory migrate -h` teaches the manifest fields. An import job never uses `albert prepare`, `albert apply` or the consolidation cursors.

## Inputs

- **Sources.** The files or folders the owner named. When he named none, ask which ones; do not search the workspace for material on your own. A chat history that is not a file, such as WhatsApp, is first written to a text file with one message per line, each line carrying its date and speaker; that file is the source.
- **Focus.** Optional: what the owner wants understood (people, work history, health). A focus guides which records are worth keeping; it never makes a statement true.
- **Names.** Read `.rbtv/config/communication/glossary.md` before reading the sources and give it to every reader. A relationship label in the glossary dates from when it was written; the dated sources decide relationship history.

Keep the job's files in `runtime/albert/ingest/<job>/` in this agent folder, `<job>` being the date and a short name: the reader briefs and results, the review, the manifest and the job report. Deferred and omitted candidates stay there with their reasons; they never enter memory.

## 1. Read the sources

Read the original, never only its summary. When a source exists as a transcript and a generated summary, read the transcript; a summary is not evidence and does not corroborate its original.

When the job has one source, read it yourself. With more, launch one reader per source with the [swarm](../../../meta/coordinate/capabilities/methods/swarm.md) method; the reading needs judgment, so route it as a middle lane (`--class bounded`). Each reader reads its whole source with the glossary and writes one result file with one entry per candidate:

| Field | Content |
|---|---|
| `text` | The proposed record, one line, in English, stating who said it, when and in what sense, and ending `(YYYY-MM-DD · <installation-relative source path>)` with the date of the statement |
| `span` | `[first, last]` lines of the source that support it |
| `kind` | `fact`, `reflection`, `hypothesis`, `plan`, `third-party statement` or `joke-or-example` |
| `support` | What the passage establishes |
| `use` | Why the owner would want this recalled, and when |
| `destination` | The memory file it belongs in (Destinations below) |
| `disposition` | `retain`, `defer` or `omit`, with the reason |

A reader makes three separate judgments for each passage and never folds them into one score:

- **Meaning and attribution.** Who said it and in what sense: a report, a reflection, a hypothesis, a plan, a joke or an example. Read enough of the surrounding text to decide; a passage the next one qualifies is read with its qualification. When the sense stays uncertain, the candidate is deferred.
- **Support.** A statement establishes that the person said it, not that it is true. A third party's claim stays attributed to that person. A plan does not establish that it happened. A hypothesis discussed in therapy stays a hypothesis, attributed to whoever raised it.
- **Use.** Keep what helps the owner later or serves the focus. How often something is said, or how emotional it is, does not make it important: a repeated joke is omitted; a single consequential event is kept.

## 2. Check the risky readings

Launch one [checker](../../../meta/coordinate/capabilities/methods/checker.md) over every retained candidate whose kind is `reflection`, `hypothesis` or `third-party statement`, or whose sense the reader marked uncertain. The checker reads each candidate's span in the source and returns keep, reword (with the new text) or defer, with the reason. Apply its result.

## 3. Reconcile with memory

Read the memory index and the files the candidates name before writing the manifest.

- A record already in memory becomes a `merged-duplicate` row naming that line.
- `memory migrate` only appends. When a source contradicts a current record, keep both dated records, write nothing that claims which is current, and list the contradiction in the job report.
- One person under two names, or two people under one name, is settled from the glossary and existing entity files; when they cannot settle it, the candidate is deferred and the question goes in the job report.
- A person, organisation, place or period that the sources mention repeatedly and memory does not know, or knows too thinly to place the candidates, is a question for the owner, not a guess. Append it to `runtime/albert/open-questions.md` in this agent folder as one line: the subject, what the sources say about it in a few words, how many sources mention it, the job, and the question (`- Dum: appears in 14 therapy sources as the owner's brother; no entity file. Who is he and what should memory hold? (job 2026-10-16-therapy)`). One line per subject across jobs: a subject already listed gets its count and job updated, not a second line. The owner answers them in a review conversation with this agent, which the `memory-review` skill conducts; they never enter memory through a manifest.

## Destinations

| Content | Destination |
|---|---|
| A person, organisation, place or device | Its file in `.rbtv/memory/entities/` |
| The owner's facts, preferences and decisions | The matching file in `.rbtv/memory/knowledge/` |
| Reflections, self-description, therapy and other intimate content | A file in `.rbtv/memory/knowledge/self/` whose `description` says to open it only for personal reflection or therapy work, with its row added to `.rbtv/memory/knowledge/_artifacts/index.md` in the same manifest |

Never write `.rbtv/memory/profile.md`; the consolidation decides what every agent loads on every turn.

## 4. Publish

1. Write `manifest.json` in the job folder from the retained candidates, as `memory migrate -h` states: one row per source, `origin` `{"workspace": "<installation folder name>"}`, scope `workspace`, and in `cutover.destinations` each destination's current SHA-256, or `null` for a new file, computed when you write the manifest.
2. Run `memory migrate dry-run --installation <root> --manifest <job>/manifest.json`. Correct every failure it lists and run it again until it passes. A destination it refuses is corrected or its records are deferred with the refusal in the report; a second file for the same person, organisation or subject is never the answer, since one subject has one file.
3. Run `memory migrate apply` with the same arguments. It keeps a copy of each source in `.rbtv/runtime/migration/originals/` and commits the memory files.
4. Check retrieval. Launch one worker that receives only the output of `memory prepare --installation <root> --agent-home <another agent's folder>` and three questions the sources should answer; it answers from memory, opening what the index routes it to. Pass when every answer is right and cites its record. Then confirm that the bundle `memory prepare` printed contains nothing from `knowledge/self/`.
5. Write `report.md` in the job folder: records published per destination, the deferred and omitted counts, the contradictions, the open questions this job added, and the retrieval result. Reply to the owner with that content when the job runs in his conversation; when it runs headless (a `cast` launch with no owner thread), the report file is the reply. When he asks to undo the job, run `memory migrate rollback` with the same manifest.
