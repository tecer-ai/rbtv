# Loose ends

The result: every loose end of the closing job is executed, filed as a task a fresh agent can act on, or disclosed in the closing message. Nothing of it survives only in chat or in your memory.

Inputs: the job being closed and what you know of it; the backlog the project already uses (a tasks file, a `loose-ends.md`, an `issues.md`). When you know of no backlog, ask the user where a task goes, once; do not invent a file. When no user can answer, name each task in your final message as unfiled.

## 1. List the loose ends

A loose end is one of these four, and only these:

| Class | Means |
|---|---|
| Deferred | Work you explicitly put off ("do X later", "out of scope for now") |
| Discovered out of scope | A real, needed unit of work you found while working that is not part of this job |
| Partial completion | The job is closing with a known piece unfinished |
| Surfaced blocker | A defect or blocker you hit and left unaddressed |

In-scope work is never a loose end: what the job's own success criteria require is the job, finished regardless of size, or closed as a surfaced blocker when it genuinely cannot proceed. A speculative improvement nobody asked for is not a loose end. A loose end that is already a task is not listed again: its existing task is enriched instead.

When sub-agents worked for you, every loose end their returns surfaced enters this list, and each goes through the two tests below yourself: filing everything a worker surfaced is not diligence.

## 2. Execute inline, or not

Execute a loose end now, instead of filing it, when all three hold:

1. Mechanical and unambiguous: no design decision, no judgment call, one obviously correct fix.
2. No new investigation: executable with the files and understanding already loaded.
3. Verifiable in this session: a re-read, a re-run or a check confirms it before the close.

Execute is the default for a mechanical, non-destructive, verifiable find; doubt about size resolves toward executing. Never execute inline, whatever the size: a destructive or irreversible action (a delete, an archive move, a change to git history), or anything whose fix depends on an owner decision or an open question. When an inline fix turns out non-mechanical or needs investigation, stop, revert the partial work, and take the loose end to step 3 with what the attempt revealed.

## 3. Triage, then file

Each loose end not executed is one entry of a backlog: the list of this session's loose ends not yet filed. Take that list through [Triage](triage.md) in full: the value bar classifies each as keep, drop, fold, move or owner-decision, the owner rules on the list before anything is written, and the rulings are applied. Then:

- **keep** → write it as a task in the backlog the project uses, cold-start sufficient as the triage page states, with the context this session has and a fresh agent does not: paths, what was tried, the state left.
- **fold** → enrich the existing task; no new entry.
- **move** → file it in the other home, with a pointer from this backlog when this backlog exists.
- **owner-decision** → the owner answered it in the round; file what waits on it as a task only when the owner said so.
- **drop** → one line in the disclosure, named, not filed.

Nothing is filed before the owner round: a task filed on your own judgment is the backlog noise this step exists to prevent.

## 4. Disclose

The closing message names each loose end executed, each task filed with its file, and each below-bar find left undone, in one visible line each. "None" is false whenever the job deferred, found, left partial or hit a blocker; the four classes make that checkable.
