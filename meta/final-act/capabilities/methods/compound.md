# Compound

The result: each improvement opportunity of the session that the user chose to document is one entry in a backlog file, naming what happened, why, and the change that would prevent it. The entry is a proposal; nothing is implemented by this method.

Inputs: the session; the destination file. Default the destination to the loose-ends or tasks file of the project the session worked on, and confirm it with the user before writing; when no user can answer, write nothing and put the candidate table in your final message.

## 1. Collect the candidates

Read the session from its start and list every:

- correction the user gave: what you did, what they wanted instead, and what you had read or assumed that led you there;
- failure you hit: a tool that refused or misbehaved, an assumption that proved wrong, an attempt repeated before it worked, a result you had to retract;
- pattern of your own you noticed: the same kind of mistake twice, a class of case missed each time, a gap in the instructions you worked around.

Keep every candidate, including the ones that fixed themselves; the user picks, not you. The view that produced a mistake is the wrong view to judge it alone.

## 2. Name the cause per candidate

For each, classify the cause and name the file that governed the behaviour, or that was missing:

| Cause | Means |
|---|---|
| misunderstanding | the instructions were read wrongly |
| execution | understood, done wrongly |
| constraint violation | a rule or instruction was broken |
| knowledge gap | the context needed was not available |

The file is a rule, a skill, a page, a memory, a prompt or a task; when none governed the behaviour, say "no file", which is itself a finding.

## 3. The user drives

Show the table: candidate, cause, file, and your proposed lesson per row, labelled as a proposal. Ask the user which rows are documented and what the lesson of each is. Write only the rows the user picked, with the lesson in the user's terms where they gave one. Never write an entry from your own view alone.

## 4. Write the entries

Append to the destination one entry per chosen row:

```markdown
- YYYY-MM-DD — <symptom: what happened, in one sentence>. Cause: <one of the four>, in `<file>`. Change: <what to add, remove or rewrite there, so it does not recur>. Scope: <this installation | rbtv>.
```

Date the entry from the system clock, not from memory. Do not implement the change: a page, rule or prompt is edited only when the user asks for that edit; the entry carries the proposal.

Close with one line: the entries written, and their file.
