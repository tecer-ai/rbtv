# Coordinating-agent contract

Write these rules into the contract section of `workflow.md`, in your own words, for the agent that will execute the plan. That agent schedules the work and does not perform it. It holds the plan folder and never reads this page, so the section must be complete without it. The inputs are the finished workflow table, the scheduling rules, the checkpoints and judge agents, and the user's loose-ends answer.

## Before the first launch and at the end

- Before the first launch, the coordinating agent runs every command in the Install section. A second run changes nothing.
- When every row is `done`, or the caller stops the run, it runs `rbtv agent remove <plan-folder>/agents/<plan>-<agent> --all --yes` for every agent. This removes the agent's generated harness files and empties the file list in its `agent.json`. The agent folder, its prompt and its task stay.

## What it reads

The coordinating agent reads the main documents itself and receives supporting material through reports. Name in the contract, by path, the pages that govern the work and the documents being changed or evaluated. It reads them, and `workflow.md`, before the first launch and before judging a result. An agent's summary does not replace that reading.

It does not read a prompt, a task file or `read-first.md` to schedule: they are written for the agents. It reads `reports/<agent>.md` to set `done` or `failed`, and a checkpoint file only when that checkpoint opens. The report's file name is the agent's short job name, without the `<plan>-` prefix of its row: state that in the contract. When a decision depends on a claim, it reads the one document that settles the claim, whichever file that is.

## Scheduling

1. An agent is ready when its row is `open`, every agent in its Needs cell is `done`, no exclusion line holds it and no checkpoint holds it.
2. At every scheduling moment the coordinating agent launches all ready agents together. Each launch is `cast --agent <plan-folder>/agents/<plan>-<agent>`, with the folder as an absolute path. `cast` sends the folder's `task.md` and returns when the agent finishes.
3. Each launch is a background command that the harness tracks, so that its completion notice reaches the coordinating agent. A launch detached with `nohup`, `setsid` or `&` loses that notice, and `cast` refuses it. The completion notice is the signal to schedule again.
4. At launch `cast` prints one `cast: handle {…}` line on standard error with the process id and session id. The coordinating agent addresses the launch by that handle, never by a `pgrep` pattern: the pattern matches the shell that runs the search.
5. It sets the row to `running` at launch.
6. For each batch it starts `cast monitor --watch` once, also as a tracked background command, and writes no polling loop of its own. The monitor prints nothing while every launch is healthy. Its exit is the signal:

   | Exit | Meaning | Action |
   |---|---|---|
   | 3, with `STALL` or `NO-SIGNAL` lines | A launch appears frozen or never started | Verify before killing. Confirm that no live process remains under the handle's process id and that no file the agent named is still being written. Only then kill by the handle's process id and launch the agent again as a resume. Start the monitor again for the rest of the batch. |
   | 4, with `ENDED` lines | A launch the monitor saw alive has ended | Never kill. Read the launch's output and exit code. |
   | 0 | The monitor was started with no launch to watch | This does not mean every agent finished successfully. |

7. A resume launch passes `-p` with text that points to the agent's `task.md` by absolute path and names the files the earlier run left changed. When the task file's `Resume point:` line is enough, the plain launch is the resume.

## Judging a result

1. The coordinating agent judges a row from the content of `reports/<agent>.md`, one done-contract clause at a time. A clause whose command output is absent is unmet. A clause the report does not state is read in the task file's `## Done contract`. When the agent ended without writing its report, the coordinating agent saves the launch's standard output to that path and judges that file.
2. It sets `done` only when every clause is met, and writes no evidence in the Status cell.
3. When a clause is unmet, it either launches the agent again with what the report got wrong, or sets `failed` and writes the reason in one line of the report. It never sets `done` because the agent's final message said the work was finished.
4. A failed agent blocks every agent that needs it. The coordinating agent does not launch those agents, and does not reorder, merge or edit Needs to pass a failed row. A change of scope returns to the caller.
5. When a row becomes `done`, it launches every agent that became ready.

When the plan has judge agents, write this in place of rule 1's clause-by-clause check: on an agent's completion the coordinating agent checks only that the report exists, addresses each clause and names its commands, then sets the row. The judges perform the verification. A judge FAIL sets the judged agent's row to `open`, and the coordinating agent launches it again as a resume with the judge's findings word for word. After two consecutive FAILs on one agent it stops launching that agent, and it handles the open point as Questions and blockers says. Agents already launched that need it are not stopped, and nothing new launches on a failed row.

## Owner checkpoints

When every row in a checkpoint's "opens when" cell is `done`, the coordinating agent reads that checkpoint's file and follows the part above its line. It never launches a held agent while the checkpoint is pending or failed, and never answers a judgment item itself. On PASS it records the answer and launches what became ready.

## Questions and blockers

- When an agent raises a question, reports a deviation or claims it is blocked, the coordinating agent first launches one read-only agent to check that one claim against the code and the files: `cast <harness> <model> <effort> --rogue <prompt-file> -p <the claim to check>`, with the three launch settings from `cast route`. It decides on that evidence.
- When a documented rule or the specification answers the point, it resolves the point and records the reasoning in the plan's `doubts.md`. It does not ask the owner.
- It asks the owner only when the open point is a judgment, as Checkpoints and judges defines one. The question carries the claim, what the check found and the options. A repeated mechanical failure is not a judgment: the row becomes `failed`.
- The owner is absent unless they say otherwise. The coordinating agent queues the question and continues all work that does not wait for the answer. It never stops the plan to wait for the owner, and never answers for the owner to continue.

## Loose ends

Agents state loose ends in their reports and never write a captured task. Only the coordinating agent captures one, in the destination the contract's `Loose ends:` line records. When that line says `chat-only`, it states the captures in its own report and writes no file.

It captures only:

1. a defect that can be observed now;
2. a teardown or cleanup that is owed;
3. something that would mislead a later agent.

For anything else it writes one line, `noted, not captured: <what>`, in its own record.
