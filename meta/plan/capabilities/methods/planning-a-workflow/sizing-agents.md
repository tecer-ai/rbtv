# Sizing agents

Decide how many agents the plan has, where one agent ends and the next begins, and which agents may run together. The inputs are the candidate agents and the files each one reads and changes. Do this before writing a task file, and derive the shared-write rules again from the finished task files before handover.

## Measure the context ceiling

Each agent finishes within about 40% of one context window. Measure this for each candidate agent before writing its task file; do not assume it.

1. List the read set: the specification, `read-first.md`, every file the agent must open, and the craft-binding reads it inherits.
2. Count the lines with `wc -l`.
3. Add the writing and the verification output. Reading alone often costs 60,000 to 90,000 tokens for an agent that changes code.
4. When the estimate is above 40% of one window, the work is two agents.

The task file's `## Scope` states the ceiling and the measured line total beside it. It tells the agent to stop at a point where its state is saved and report that state when it reaches the ceiling. An agent whose ceiling was written without a measurement usually exceeds it.

## Write the Phases block

Every task file has a `## Phases` block directly above its `## Done contract`, with one row per phase:

```markdown
| Phase | Resource it writes | Hands to the next | Artifact |
|---|---|---|---|
| <phase> | <file, record or device> | <what the next phase needs> | <artifact path>, or same-state: <the input that cannot be written down> |
```

Write the block before the rest of the task file. For each hand-off, ask one question: could a stranger who holds only a file with exactly what the next phase needs do that phase correctly?

| Answer | Result |
|---|---|
| A file can hold all of it | The agent ends there. The next phase is its own agent with a Needs edge, and it holds only that artifact. The artifact's path becomes a numbered clause in the producing agent's done contract. |
| Some needed input cannot be written into a file, such as a decision that determines the next edit or the consistency one agent keeps across related edits | The phases stay in one agent. The `same-state:` cell names that input in one line. |
| Two rows hand each other nothing and write different resources | They are separate agents that launch together. A loop over targets inside one task file is this case. |

Split where an artifact can carry the work, never by a count. The number of files, operations, targets or steps is not a reason: related edits in one agent often cost less context and give a better result. Every split states its reason as the artifact path or the contended resource that requires it. A split whose reason is a number is void: restore the agent.

## Apply the special cases

**An ordering ruling.** "Do X on the source first, then apply it to every target" is a Needs edge. It is not one task file that does the source and then each target. Group the targets after that edge by resource:

- Two targets are one agent when they share a file either one writes, when one verification run proves both, or when they contend for one device, host or slot.
- Two targets are separate agents when none of those holds and each has its own command that performs its write.
- Targets inside one repository or one artifact are one phase of one agent, which works from the source agent's artifact.
- When one tool invocation writes the source and one target together, cut by the tool: one agent per resource, each with the part of the source its tool writes.

Check independence: the scheduling rules hold one line that names both agents' write sets and shows that no path is in both. When a path is in both, write a shared-write rule instead. Every agent that writes a resource names in its task file the command that performs the write. A split that leaves a new agent with no named command, or with a script the parent agent did not have, is void.

**Long mechanical input and output**, such as hashing a whole device, a bulk conversion or a bulk copy. Make it its own agent only when all of these hold:

- A stranger could run it from start to finish from an artifact alone.
- Its failures are handled by reporting and stopping.
- The task file names in one line what the cut frees: work that runs beside it, or a reasoning agent that ends its turn and does not hold its context through the wait.
- The new agent's harness, model or effort differs from the parent's. The same launch settings waiting on the same command gain nothing.

Input and output that is the inner loop of a judgment made per item stays with the judgment. A final verification on a device the agent already holds stays in that agent.

**A boundary between strictly serial phases** where the plan can name nothing that would run beside the cut. Keep one agent and write the literal line `Resume point: <artifact path>` at that phase in the task file. Make the phases separate agents when the measured estimate is not under the ceiling, or when the phases need a different harness, model or effort. A boundary with neither a separate agent nor a `Resume point:` line fails the review.

**Verification of the whole suite** runs once per chain, in the last agent of the chain. Earlier agents run only the tests their own files affect.

## Derive the shared-write rules

After the task files exist, derive the shared-write rules from them. A rule written earlier is provisional: a rule that names a subsystem orders agents that share no file.

- A rule is about one file or record, with a concrete path. A path with a wildcard or a `<placeholder>` names a subsystem: expand it, or state both agents' expanded sets in the rule and show that no path is in both.
- Only writes count. For each agent in a rule, cite the task-file line whose verb is edit, write, repoint, delete or back up. A path the task file only reads, counts, reports, locates or forbids is not a shared write. A rule that cites no task-file line is void.
- Each rule is a Needs order or an exclusion line, as Planning a workflow says for `workflow.md`. Agents that append to one file still need a rule, and they commit by naming the path.
- One agent named as the only writer, with the others forbidden to touch the file, is a wall in those task files and not a rule.
- After a split, compare the new rules with the parent agent's. A new rule that orders two agents sharing no written file is a defect of the split: correct the task files and remove the rule.

## Make every possible agent a root

The longest chain of Needs sets the plan's duration, so ten roots and one edge finish sooner than ten agents in a line. Every agent that can be a root is one. A Needs edge is a read-dependency or a write order from a shared-write rule. Contention with no required order is an exclusion line, never a Needs edge and never an unwritten sequence.

## Check each block

- Every task file has a Phases block, and every row names the resource it writes.
- No artifact cell names a path that is insufficient for a stranger.
- Every `same-state:` cell names the input that cannot be written down.
- Every split's reason is an artifact path or a contended resource.
