# Compound

The result: every issue of the session about the scaffolding the agent worked with is one entry in a compound backlog, with its class, what happened, its cause, the change that would prevent it and the scope that change belongs to. An entry is a proposal: this method implements nothing, and nothing in the backlog is a task until the owner rules it.

A compound entry is about the scaffolding: the skills, tools, rules, agents, hooks, instruction files and harness the agent had. An issue about the matter the agent worked on is a [loose end](loose-ends.md), filed in the project's backlog. One question sorts a find: is it about what I worked *on*, or about what I worked *with*?

Inputs: the session's record (how to find it is in step 1); the path of every sub-agent report this session received; the tier (default, or full when the user asks for it or accepts the proposal in step 3); the destination, by scope (step 6). An agent with no close, such as an agent that answers a conversation thread, runs this when the user asks; its session is that thread.

## What counts

| Class | What it is | What the entry becomes |
|---|---|---|
| Instruction | The agent behaved differently from an instruction it had: a per-turn instruction skipped, a skill whose "always load when" matched and was not opened, a user instruction or decision not followed, work nobody asked for | A change to the scaffolding that carries the instruction, so that it holds; deleting an instruction nobody follows is such a change |
| Scaffolding | A skill, tool, rule, agent or sub-agent failed, refused, misbehaved, had to be worked around or was missing, so the agent deduced, researched or built it itself | A fix or improvement to that tool or scaffolding |
| Safety | The agent ran, or tried to run, something dangerous: a history rewrite on a shared branch, a mutating git command in a folder it had not resolved, a dump of the environment, a retry against a permission gate, whether or not it was blocked | A safety measure where the agent reads the rule it broke, or a mechanism that removes the pressure to break it |

An instruction deviation counts whether or not it had an effect: an instruction skipped with no consequence is evidence that the instruction does not trigger, or that it is noise. A Scaffolding candidate of the "had to deduce or research" kind counts only when it caused a wrong action, cost a significant detour, or recurs on every similar task; a lookup the agent made once and got right is not an entry.

Not an entry: a slip with no lesson for the scaffolding (a wrong count in a message, a step sent before it was rehearsed); a correction about the work itself (tone, format, a fact), which goes to memory with `memory remember` where the installation has it, or to the agent's board watch-outs. Route these in step 4; do not drop them.

## Tiers

| Tier | Finds | Runs |
|---|---|---|
| default | corrected deviations (the user said something), signalled failures (a tool refused, errored, was retried), dangerous commands, and what sub-agent reports declared | at every compound |
| full | the silent deviations too: an instruction skipped that nobody corrected, a decision contradicted that nobody noticed, a "done" claimed that the disk does not show | when the user asks for it, or accepts the proposal: propose it when the session was long, ran sub-agents, or touched shared surfaces |

## 1. Sweep the record

Launch the sweep under the `coordinate` skill: its rules on the plan, `cast route` and the one-page return apply. Create the run folder `.rbtv/runtime/final-act/compound/<run-id>/` from the installation root, or `runtime/final-act/compound/<run-id>/` in an agent folder; `run-id` is `<YYYY-MM-DD-HHMM>-compound`.

1. **Locate the record.** When your harness gave you the record's path (an agent answering a thread has its history path in its prompt), use it. Otherwise put one line holding a fresh marker, for example `sweep-marker 7f3a…`, in the message that shows the user the sweep plan (coordinate's rule 1); a harness records a message after the turn that wrote it, so in the next turn run `session-sweep locate --marker <marker>`: it searches the session records the harnesses on this machine keep and prints `record PATH` and `harness NAME`. When it finds none, the message is not recorded yet: run it again on your next turn. When it finds several, pass the one whose `cwd` is your working folder. Never sweep a record that is not this session's.
2. **Extract the moments.** `session-sweep extract RECORD --out <run>/sweep --report PATH` for each sub-agent report. It writes `moments.json` and `chunks/chunk-NNN.md`, each chunk holding at most thirty moments: every message the user typed with the agent's message before it; every tool result and command that carries a signal (a refusal, an error, an uncertain result, a command repeated with the same input, a mutating git command, a dump of the environment, a force flag); every passage of the agent's own text that says it worked around, skipped or could not find something; every sub-agent report. It prints `moments N`, `chunks N` and `signals N`.
3. **Label.** One sub-agent per chunk, routed `cast route --access bounded --type text --class mechanical --optimize price`, with the task in [Sweep task](compound/sweep-task.md); each writes `<run>/sweep/labels/chunk-NNN.txt`. Do not tell a labeler which answer you expect.
4. **Check.** `session-sweep check <run>/sweep` confirms one well-formed label file per chunk and prints the count per label. A missing or malformed file names its chunk; re-run that labeler.

You read the label files, not the chunks: each label line carries the moment's id and the quoted words you need to judge it, and `moments.json` holds the full moment when a line is not enough.

## 2. Recall what no signal shows

With the labels in hand, list from your own reading of the session, per class:

- every instruction you had and did not follow: the per-turn instructions of the installation's instruction files and rules, every skill whose "always load when" matched a step you took, every user instruction and decision of this session;
- every skill, tool, rule or agent that failed, that you worked around, or that was missing so that you deduced, researched or built it yourself;
- every dangerous action, blocked or not.

A labeler reads one chunk; you read the whole session. This step exists for what a chunk cannot show.

## 3. Full tier

When the tier is full, run the three checks of [Full checks](compound/full-checks.md) before step 4: they compare the whole record against the instruction set in force, against the decisions and requests of the session, and against the disk. Their findings join the candidates.

## 4. Rule each candidate

Each labelled moment, each recalled item and each full-check finding is a candidate. For each, decide: its class, or out with the reason. Then:

- A label of the user's words: A (against a decision from an earlier session or a project file), B (forgot an instruction of this session), C (repeated a corrected mistake) and E (did the unasked) are Instruction. D (broke something that worked) is Scaffolding when a check could have caught it, otherwise a loose end. F (another complaint about the output) is a content correction: route it to memory or the board, as What counts says.
- A tool signal is Scaffolding (refusal, error, uncertain result, workaround, missing tool) or Safety (a dangerous command, a retry against a gate).
- A sub-agent report that declares a skipped or deviated step is Instruction.

Collapse repeats: one instruction skipped in fourteen turns is one candidate with its count, not fourteen. For each candidate, name the file that governed the behaviour, or "no file" (itself a finding), its cost (wrong action, detour, none) and whether it recurs (every time, sometimes, once).

## 5. Triage

Take the candidates through [Triage](triage.md) in full: its value bar classifies each as keep, drop, fold, move or owner-decision, and the owner rules before anything is written. Triage also settles the tracker of each: an entry about the matter is moved to the loose-ends list; an entry about the scaffolding stays here. When no user can answer, skip the owner round and write every candidate you kept, marked unruled in its Ruling column; the owner rules them later in the backlog.

## 6. Write the entries

Write each kept entry to the compound backlog of its scope:

| Scope of the entry | Backlog |
|---|---|
| `agent:<name>`: the agent's own prompt, tools, skills or settings | `output/final-act/compound/compound.md` in that agent's folder |
| `installation`: the installation's mirror, config, instruction files or selections | `.rbtv/output/final-act/compound/compound.md` from the installation root |
| `rbtv`: a shipped component | the installation's file above, scope `rbtv`; a *move* ruling at triage carries it to the rbtv repository |

An installation's instruction file may name another backlog for compound; when it does, write there. Create a missing file with this header and table, and append one row per entry; put a context note a row needs, longer than a cell, in the same folder and link it from the row.

```markdown
# Compound backlog

Each row is an issue about the scaffolding an agent worked with, written as a proposal. The owner rules each row; nothing here is a task until ruled.

| # | Class | Seen | Filed by | What happened | Cause | Proposed change | Scope | Cost · recurs | Ruling |
|---|---|---|---|---|---|---|---|---|---|
```

`Seen` is the date from the system clock and the session or thread. `Filed by` is the agent or the plain session. `Cause` names why it happened and the file that governed the behaviour, or "no file". `Proposed change` says what to add, remove or rewrite where. `Ruling` is empty for a row the owner ruled in the round, `unruled` when no user could answer, and the triage verdict afterwards.

Close with one line: the entries written per backlog, the candidates routed to memory or the board, and the candidates dropped with their reasons.
