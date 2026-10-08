# Reviewing a plan

Before handover, an agent that did not write the plan reviews its structure: the sizes of its agents, its Needs edges and its shared-write rules. The author follows the task list it already holds and does not see these defects in its own plan.

Two readers use this page. The author sets up the review, implements what it holds and approves the result. The review agent's task file sends it here for "The review" and "Run the checks again". The input is a complete plan folder that passed items 1 to 10 of the self-check in [Planning a workflow](../planning-a-workflow.md).

## Set up the review (author)

1. Create the agent folder `agents/plan-review/`. Its prompt tells the agent to do the task it was given and write its report, and constrains it not to edit a task file or a prompt and to read `workflow.md` only as its task's named input.
2. Choose a model different from the one that wrote the task files, and install the agent as Planning a workflow says.
3. Write `task.md` from the template below. Fill `<plan-folder>` and `<rbtv-root>`, the root of the rbtv source, as absolute paths. Fill the `authored-by:` line with the model id of the session that wrote the task files: no other file in a plan records it.
4. Add the row `plan-review` to the workflow table and launch the agent with `cast --agent`.
5. Read the launch's standard error. `cast` can replace a model that fails to start and names the replacement there. When the replacement is the authoring model, launch the review again on another model.

```markdown
Read <plan-folder>/read-first.md first. Then read <rbtv-root>/meta/plan/capabilities/methods/planning-a-workflow/reviewing-a-plan.md and <rbtv-root>/meta/plan/capabilities/methods/planning-a-workflow/sizing-agents.md, and follow "The review" in the first. Write your report to <plan-folder>/reports/plan-review.md.

Review the structure of the plan in <plan-folder> and write the verdict file <plan-folder>/judgements/plan-review.md.

authored-by: <model id of the session that wrote the task files>

## Scope

Examine: <plan-folder>/workflow.md, <plan-folder>/read-first.md, <plan-folder>/checkpoints/, every prompt.md, agent.json and task.md under <plan-folder>/agents/ except agents/plan-review/, and the two method pages named above.
May change: <plan-folder>/workflow.md, <plan-folder>/judgements/plan-review.md, <plan-folder>/reports/plan-review.md, and the prompt.pre-split.md and task.pre-split.md copies you create.

Do not change a prompt.md, an agent.json, a task.md, a checkpoint file or a judge's file. Before you change workflow.md, read <rbtv-root>/core/rbtv/skills/framework.md and the pages it routes to for a workflow. A review that keeps every agent does not change workflow.md and does not read them.

## Phases

| Phase | Resource it writes | Hands to the next | Artifact |
|---|---|---|---|
| Review | judgements/plan-review.md | the verdicts and held changes, to the author | <plan-folder>/judgements/plan-review.md |

## Done contract

1. The first two lines of the verdict file are `authored-by:` and `reviewed-by:`, with different model ids.
2. The verdict file holds every part "The verdict file" lists in reviewing-a-plan.md.
3. reports/plan-review.md and your final message start with the list of verdicts.

When an input is missing, or the two model ids are equal, stop and report it.
```

## The review (review agent)

Write the first two lines of `judgements/plan-review.md` before anything else: `authored-by:` copied from your task file, and `reviewed-by:` copied from the `model` in `agents/plan-review/agent.json`.

Then check every agent folder under `agents/` that holds a `task.md`, except your own. A `task.pre-split.md` is a kept copy and not a task.

1. **Structure.** A task file without `## Scope` or `## Done contract`, without a `## Phases` block, or with that block anywhere but directly above `## Done contract`, is a FAIL. Check the written block against the task file. Never write the block yourself.
2. **Hand-offs.** An artifact cell whose path is insufficient for a stranger who holds only that file is a SPLIT. A `same-state:` cell that names no input is a SPLIT. Rows that write different resources and hand each other nothing are separate agents that launch together. Phases that read the same artifact each need its producer; they do not form a chain.
3. **Ceiling.** Record two numbers: the `wc -l` total of the agent's named read set, `read-first.md` and the craft-binding reads it inherits, and the ceiling its `## Scope` states. A total that contradicts the ceiling is a SPLIT. A ceiling with no measured total beside it is a SPLIT.
4. **Needs edges.** For each edge, name the artifact path the downstream agent reads from the upstream one and quote the task-file line that reads it. Remove an edge with no such artifact, which makes the downstream agent a root. When the two agents' write sets share a path, keep the edge as a write order or replace it with an exclusion line that names the shared files. Every "X first, then Y" order written inside one task file is a SPLIT.
5. **Shared writes.** Derive the shared-write rules again from the task files, as Sizing agents says. Remove every rule that orders agents you have shown share no written file.
6. **Description.** Compare the `description` in each `agent.json` with "Description format" in `<rbtv-root>/core/rbtv/capabilities/glossary/routing-table.md`. Record a description in another format with the agent's name and hold it for the author.

The verdict for each agent is KEEP, or SPLIT or RE-EDGE with the exact new form. State every SPLIT's reason as an artifact path or a contended resource. Never split on a number of steps, files, operations or targets.

**What you change.** You change `workflow.md` only: the table, the Needs cells, the scheduling rules and the checkpoint table. When any row other than your own is `running` or `done`, the plan is already running. Then do not change `workflow.md`: write the rewritten sections in a `## workflow.md payload` section of the verdict file, and the coordinating agent applies it as one edit between its own status changes.

**What you hold for the author.** Every change to a prompt, a task file, a checkpoint file, a judge's file or a launch setting. Before you record a rename or a split, copy the parent's `prompt.md` to `prompt.pre-split.md` and its `task.md` to `task.pre-split.md` in the same agent folder, unchanged. State the new form completely enough that a comparison of files confirms the author implemented it:

- **Each new agent**: its name, its Needs cell, the resource it writes, the command that performs that write, and its Install command. Each new task file opens with the same `read-first.md` directive as its parent, writes every path as an absolute path, and keeps the parent's craft-binding line when the new agent still writes code or rbtv source files.
- **The clause-reallocation table**: `old-agent #n → new-agent #m | dropped-because-moved | new-contract <path § heading>`, ending with `before: N, after: N + k new contract clauses`. Across the agents whose boundary moved, the done-contract clauses after the split equal the clauses before it. A new clause is allowed only when it names, by path and heading, an artifact a downstream agent already reads. A clause with no destination row was dropped, and the split is void.
- **The wall table**: `parent wall → child: duplicate | rescoped | dropped | added`. Duplicate a wall into every child whose files it still names. Rescope it where it named a target that is now split. Drop it from a child that no longer touches the target. Add to each child one wall that names the other child's files, devices and state files: without it both children may open all of them. Add no other wall, and drop none that still applies.
- **The repoint inventory**: every place that names the old agent, on this closed list:
  1. `workflow.md`: the table, the Needs cells, the scheduling rules, the checkpoint table, the Install section and the judge statement;
  2. every `checkpoints/cp*.md`: its opens-when, holds and failure cells;
  3. every judge's task file: its agent list, its adjacent cases, its count of agents and clauses, and every `grep` in its done contract;
  4. every task file that names the parent, in its walls, its done contract or its description of what it needs. Quote each child's Needs cell beside that description: the two agree;
  5. `read-first.md`;
  6. every prompt that names the parent.

## Implement what the review holds (author)

Do this in one sitting with the review, while you still hold the reasons for the plan's form.

1. Write the files the verdict prescribes and repoint every place in the inventory in the same edit. You may rewrite an agent whose work was the source of a moved phase: its task file states what was cut, its walls gain what was cut, and its done contract drops the moved clauses.
2. For each new agent, get its launch settings from `cast route`, install it and add its command to the Install section.
3. Launch the review agent again with `-p` text that asks it to run the checks again.

## Run the checks again (review agent)

Run only these, and write each result in the verdict file:

1. `grep -rn '<old-agent-name>' <plan-folder>`. Hits are allowed only in `decisions.md`, `status.md` and the pre-split copies. Record `old-name grep: 0 live hits` with the output.
2. `cast --agent <plan-folder>/agents/<plan>-<agent> --dry-run` exits 0 for every agent the change touched.
3. The comparison of the new shared-write rules with the parent's, as Sizing agents says.

## Approve (author)

Approve these four things and nothing else:

1. the table, rules and Install section of `workflow.md`;
2. the list of files the review changed, read as a comparison with their earlier content;
3. `old-name grep: 0 live hits`;
4. the walls and done contract of every new or changed task file.

Then append `author approved <YYYY-MM-DD>` to `judgements/plan-review.md` and set the `plan-review` row to `done`. Never hand over a plan whose verdict file records a change and has no approval line. When you reject a task file's walls or done contract, restore it from its pre-split copy; the review agent does not split that agent a second time.

## The verdict file

`judgements/plan-review.md` holds, in this order: the two model lines; the verdict table, one row per agent with both ceiling numbers; the list of Needs edges with their artifacts; the shared-write table with the cited write lines; the description findings; and every file the review changed. When the review splits or re-edges an agent it also holds the clause-reallocation table, the wall table, the repoint inventory and `old-name grep: 0 live hits`. It ends with the author's approval line.
