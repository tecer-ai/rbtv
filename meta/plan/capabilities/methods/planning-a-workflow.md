# Planning a workflow

Write settled work as a plan folder that a coordinating agent executes without you present. The required inputs are the settled scope, the decisions and rulings, and the location of the plan folder.

Every fact the plan states comes from those inputs. This method does not interview, decide content or choose the work. When a fact a file needs is missing, or no plan folder location was given, stop and name the missing input to the caller; do not invent it. The one question this method asks the user is the loose-ends destination in step 1.

The saved files are the whole deliverable. Nothing registers a plan and no program schedules it: the coordinating agent follows `workflow.md`. [Workflow](../../../../core/rbtv/capabilities/glossary/workflow.md) defines the table, [Task](../../../../core/rbtv/capabilities/glossary/task.md) the task file, [Agent](../../../../core/rbtv/capabilities/glossary/agent.md) the agent folder and [Prompt](../../../../core/rbtv/capabilities/glossary/prompt.md) the prompt. This page states what a plan adds to them.

## The plan folder

```
<plan-folder>/
├── workflow.md                  the one file the coordinating agent schedules from
├── read-first.md                what every agent reads before its own task
├── agents/<plan>-<agent>/       one agent folder per agent: prompt.md, agent.json, task.md
├── reports/<agent>.md           written by the agent when it finishes
├── checkpoints/cp<n>-<name>.md  one file per owner checkpoint, when the plan has any
├── judgements/<judge>.md        one verdict file per judge agent, and plan-review.md
├── CLAUDE.md
└── AGENTS.md
```

`<plan>` is the plan folder's name, written with lower-case letters, digits and hyphens only, which is what an agent name accepts. `<agent>` is the agent's short job name and the stem of its report file. The agent's name, its folder name, the `name` in its `agent.json` and its cell in the workflow table are all `<plan>-<agent>`. The review agent of step 10 is the exception: its folder and its row are `plan-review`.

A plan carries `workflow.md`, `read-first.md` and one agent folder per agent. `decisions.md`, `doubts.md` and `status.md` are created in the plan folder when the first record is written to them.

`CLAUDE.md` and `AGENTS.md` each hold these two lines and nothing else. They send an agent that opens the folder to the scheduling file and give it the artifact names:

```
If you are coordinating the execution of this plan, read workflow.md first.
Folder artifacts used here when applicable: loose-ends.md (captured loose ends), issues.md (open questions needing a ruling), doubts.md (self-resolved doubts + reasoning, recorded for later review), ideas.md (framed, not ruled), decisions.md (rulings, append-only), status.md (current state).
```

## Order of work

1. Ask the user where captured loose ends go: a file, and which file, or chat only. Record the answer as `Loose ends: <path>` or `Loose ends: chat-only` in the contract section of `workflow.md`.
2. List the candidate agents. Read [Sizing agents](planning-a-workflow/sizing-agents.md) and size each one before writing its task file.
3. Read [Checkpoints and judges](planning-a-workflow/checkpoints-and-judges.md) and design the owner checkpoints and judge agents before writing any task file. A checkpoint added after the task files exist can only cite evidence that happens to exist.
4. Write `read-first.md`.
5. Write each agent folder.
6. Write `workflow.md`.
7. Write `CLAUDE.md` and `AGENTS.md`.
8. Install every agent and verify that it launches.
9. Run the self-check.
10. Read [Reviewing a plan](planning-a-workflow/reviewing-a-plan.md) and have the plan reviewed, unless `workflow.md` has no Needs edge and no exclusion line. In that case state in one line of `workflow.md` that the review was skipped for that reason.

## `read-first.md`

One file that every agent reads before its own task file. It holds only what is true for all of them; a fact true of one agent belongs in that agent's task file.

- **Program context**: what the program is, what settled it, and that those rulings are settled. An agent that reads a ruling as open reopens it.
- **Where things are**: the code trees, the runtime state and the branch. State that a cited `file:line` may have moved and is located again by its content.
- **Hazards**: each condition that would cost an agent its work. Examples are a file saved through a gate and never written in place, a change that takes effect when saved while another waits for a restart, a shared repository where other sessions hold uncommitted work, and the commit form that keeps another session's change out of a commit.
- **The report**: `reports/<agent>.md` states what was done, what was verified with the command output that proves it, and the loose ends. A report that names no command has verified nothing. The coordinating agent sets `done` or `failed` from this file.
- **The craft bindings**: an agent that writes or edits code reads `meta/code/skills/coding.md` in the rbtv source before its first edit. An agent that creates or changes a rule, prompt, skill, task, agent, capability, workflow or another rbtv source file reads `core/rbtv/skills/framework.md` in the rbtv source, and the pages it routes to for that kind, before its first write. An agent that only verifies reads neither. These readings count in each agent's measured context.

## The agent folder

Write `prompt.md` as [Prompt](../../../../core/rbtv/capabilities/glossary/prompt.md) says. It holds the agent's standing function, never this task's result, scope or done contract. Its procedure tells the agent to do the task it was given, to write `reports/<agent>.md`, and not to read `workflow.md`. Its constraints say that the agent does not wait after its turn ends: a `cast` launch is one turn and nothing wakes it with a result, so every check its conclusion depends on finishes inside the turn.

Write `agent.json` as [Agent record](../../../../core/rbtv/capabilities/glossary/agent-json.md) says: `name`, a `description` in the four-field format of [Routing table](../../../../core/rbtv/capabilities/glossary/routing-table.md), `files` as full ids `<module>/<component>#<name>`, and `packs` when any. Turn a pack on with `rbtv agent add <agent-folder> --pack <name>`; a pack is never listed as a file. Before writing an instruction an existing file already holds, look for that file with `rbtv list`, `rbtv search` and `rbtv show`. Name each selected file and its use in the agent's task file or prompt.

Write `task.md` as [Task](../../../../core/rbtv/capabilities/glossary/task.md) says. The agent that receives it has no memory of the planning session and holds its prompt, `read-first.md` and this one file. A plan's task file has these parts, in this order:

1. **The opening directive**: read `read-first.md` first, by absolute path, and write the report to the absolute path of `reports/<agent>.md`.
2. **The result**: the one result this launch produces, before any heading.
3. **`## Scope`**: the closed lists `Examine:` and `May change:`, then:
   - The whole scope, written in this file: the defect, the ruling it implements, the form of the change and the dependencies on other agents that affect this one. Point only to a scope, design or ruling document that already exists. Never split one agent's scope across added files.
   - The walls: each file, device or record this agent must not touch, by name. An agent that crosses a wall has failed.
   - The agent's context ceiling with its measured read set, as Sizing agents says, its commit form, and what it must never do, such as restart a service, write a captured task or contact the user.
4. **`## Phases`**: the table Sizing agents defines, directly above the done contract. Write it before the rest of the file.
5. **`## Done contract`**: numbered clauses, each one falsifiable. A clause a program can check names the exact command and the result that passes: "the tests pass" is not a clause. The section ends with the action on a missing input or a failed clause: stop and report it, never wait for a reply.

Write every path in a task file as an absolute path. The agent's working folder is its agent folder, so a path relative to the installation resolves from the wrong folder. When one agent produces a file another reads, both task files name the same path.

## `workflow.md`

Only the coordinating agent reads it. It holds these sections in this order:

1. The workflow table, with exactly the columns `Agent | Needs | Status`.
2. The checkpoint table, or one line stating that the plan has no checkpoint, and one line when it has no judge agent. Checkpoints and judges defines both.
3. The Install section.
4. The scheduling rules.
5. The coordinating-agent contract.

**The table.** Follow [Workflow](../../../../core/rbtv/capabilities/glossary/workflow.md), and in a plan:

- Needs names every agent whose results this agent reads, and every agent that must finish first because both change the same file or record. `—` marks a root: an agent that needs nothing. A preference, a priority or a sequence nobody's files require is never a Needs edge.
- A Status cell holds one of `open`, `running`, `done` or `failed`, and no other text. A run that cannot finish is `failed`, and its reason is in the report.
- The table has no column for a task, a description, a harness, a model or an effort. The task is `task.md` in the agent folder, and the launch settings are in `agent.json`.
- A step that waits for a person is a checkpoint hold in the checkpoint table, not a row and not a mark in this table.
- `read-first.md` is not a row. A judge agent and `plan-review` are rows. The coordinating agent launches only `open` rows.

**The Install section** lists one command per agent, which the coordinating agent runs before its first launch:

```
rbtv agent add <plan-folder>/agents/<plan>-<agent>
```

**The scheduling rules** list the constraints that are not read-dependencies, so that none of them is written as a Needs edge. The recurring one is a file or record that two or more agents change. Those agents never run together. Either one needs the other, and the rule names the shared file so a reader can tell a write order from a read, or an exclusion line names the file, every agent that changes it and the limit, such as "at most one of A, B, D in flight". An agent that only appends to the file still changes it. Sizing agents says how to derive these rules from the task files.

**The coordinating-agent contract.** Read [Coordinating-agent contract](planning-a-workflow/coordinating-agent-contract.md) and write its rules into this section in your own words. The coordinating agent holds the plan folder and never reads this method.

## Install and verify the launch

For each agent, ask `cast route` for the harness, model and effort its work needs, then install it:

```
rbtv agent add <plan-folder>/agents/<plan>-<agent> --harness <harness> --model <model> --effort <effort>
```

`--effort` takes the number `cast route` returns. The command checks that the installation selected the model, writes the three values into `agent.json` and generates the agent's harness files. Run it once per agent before handover. A second run takes no launch options: it is the command in the Install section. Change a value afterwards with `rbtv agent configure`.

Then run `cast --agent <plan-folder>/agents/<plan>-<agent> --dry-run` for each agent. It prints the composed launch and exits 0 without launching, and exits 2 when the folder holds no `task.md`. It does not show whether the agent was installed: that is the exit status of the `rbtv agent add` command.

## The self-check before handover

1. Every done-contract clause is falsifiable, and every clause a program can check names its command.
2. Every task file needs nothing beyond itself, its prompt, `read-first.md` and documents that already exist.
3. Every `rbtv agent add` command exited 0, and `cast --agent <plan-folder>/agents/<plan>-<agent> --dry-run` exits 0 for every agent.
4. Every Needs cell names a row of the table, no chain of Needs returns to its start, and every edge is a read-dependency or a write order the scheduling rules name.
5. Every file that two or more agents change has a Needs order or an exclusion line.
6. `workflow.md` holds its five sections in order, including the `Loose ends:` line, and no column or status text this page excludes.
7. `CLAUDE.md` and `AGENTS.md` exist with their two lines.
8. The checkpoints and judge agents pass the checks at the end of Checkpoints and judges.
9. `read-first.md` holds the craft bindings.
10. `grep -L '## Phases' <plan-folder>/agents/*/task.md` and `grep -L '## Done contract' <plan-folder>/agents/*/task.md` print nothing, and every Phases block passes the checks in Sizing agents.
11. The review is complete as Reviewing a plan says, or `workflow.md` states that it was skipped because it has no Needs edge and no exclusion line. Run items 1 to 10 before launching the review.
