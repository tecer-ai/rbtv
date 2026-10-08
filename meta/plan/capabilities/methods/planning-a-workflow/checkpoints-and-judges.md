# Checkpoints and judges

Decide which checks the owner rules on and which checks a judge agent performs. The inputs are the candidate agents and every check the plan needs before work continues. Do this before writing the task files, so that each pass condition is copied into a judge's task file and each checkpoint states the facts those conditions name.

An owner checkpoint holds named agents until the owner rules on a judgment. A judge agent verifies other agents' finished work and gives a PASS or FAIL verdict for each. The owner never repeats a check a program or an agent can perform.

## Apply the pass-condition test

For each candidate check, write the exact observation that makes it pass, before the check runs: a command and the output it must print, a file and the content it must hold, or a count and its value.

| Result | Classification |
|---|---|
| You wrote the pass condition | Mechanical. It goes to a judge agent, and the condition becomes that judge's criterion, word for word, in its task file. |
| You cannot write it without an evaluative word such as good, acceptable, enough, reasonable, appropriate, clear or worth it, or the right answer would differ for another owner who sees the same evidence | Judgment. It is a checkpoint item. |
| Part is observable and part is evaluative | Split it. "The backup exists and its checksums match" goes to the judge. "Are you willing to delete the original on that evidence" is the checkpoint item. |
| A documented rule or the specification already answers it | Neither. The coordinating agent resolves it and records the reasoning in the plan's `doubts.md`. |

A checkpoint item is one of four kinds, and the checkpoint file names the kind:

- a preference only the owner holds;
- a risk the owner must accept, which every irreversible or destructive step is;
- a quality call only the owner can make;
- an act only a person can perform, which is named as that and not written as a judgment.

## Write a checkpoint only for what remains

Write a checkpoint only where a judgment item remains after the test. Do not write one per agent, and do not add one to make the plan look careful. When no item remains, write no checkpoint: state in one line of `workflow.md` that the plan has none, and the plan proceeds on the judges' verdicts.

A hard checkpoint is the one exception. The owner may ask, in the inputs or during planning, for a checkpoint at a named point for a stated reason. Write it even when it holds no judgment item, put the owner's reason in its text and record it in the plan's `decisions.md`. Do not invent a hard checkpoint, do not ask the owner whether they want checkpoints, and do not propose a set of checkpoints to the owner.

Place the hold where the ruling changes what may launch. A risk-acceptance item sits before its irreversible or destructive step. A finished layer or a large change with no remaining judgment item is checked by a judge, not held for the owner.

**The row.** The checkpoint table sits directly under the workflow table in `workflow.md`:

```markdown
| Checkpoint | Opens when all of these are `done` | Holds these agents and the agents that need them, until the owner answers PASS | File |
|---|---|---|---|
```

A checkpoint is not a Needs edge. The coordinating agent does not launch a held agent while its checkpoint is pending or failed.

**The file.** Each checkpoint is one file, `checkpoints/cp<n>-<name>.md`. The coordinating agent reads it only when the checkpoint opens, so write it for that moment. It has two parts separated by a `---` line.

Above the line, for the coordinating agent:

- when to open this file, which agents it holds and which facts to verify;
- verify every fact the lower part states before presenting it. When a fact does not hold, do not present the checkpoint: handle the named agent as the contract's failure rule says;
- present only the judgment items, each with its verified fact, and never a step for the owner to perform. Present a hard checkpoint with no judgment item as the owner's stated reason and the request to release;
- hold only the held agents while all other work continues, and record the checkpoint as pending, then PASS or FAIL, in `status.md`;
- on FAIL, handle the named agent as the contract's failure rule says and present the checkpoint again after the correction;
- never answer a judgment item yourself.

Below the line, for the owner, who reads it with no context:

- what was just finished and why this checkpoint exists, in plain words;
- the judges' results, stated as facts;
- numbered judgment items, each naming its kind and asking for the ruling, with no command to run and no evidence to read again;
- the reply format: `CP<n> PASS` or `CP<n> FAIL: <which item and the ruling>`.

A hard checkpoint's lower part is the owner's stated reason and that reply format.

## Design the judge agents

Design a judge agent for every check the test classified as mechanical. Then add judges where any of these holds: several agents change files in one subsystem, the change affects credentials, destructive acts or running services, or the plan has deploy or restart windows that run one at a time. When the test classified nothing as mechanical and none of those holds, state in one line of `workflow.md`, beside the checkpoint statement, that the plan has no judge agent. A plan with no such group and no such window uses the final judge alone.

| Judge | Use |
|---|---|
| Cluster judge | One per group of agents that change one subsystem. Its Needs cell names them, so it launches when they are all finished and finds regressions across their shared files. Do not use one judge per agent by default. In a plan with several layers, do not use only a final judge: a defect in the first layer would be found after everything built on it. |
| Deploy-window judge | Where the plan has deploy or restart windows that run one at a time. The coordinating agent launches it at the end of each window with that window's agent list, and it runs each delivered correction's verification commands against the running system. This is a scheduling rule, not a Needs edge. |
| Final judge | Gives verdicts for the agents no cluster judge covers, runs a sample of the commands of agents the cluster judges passed, and gives the whole plan ACCEPT or HOLD before any closing agent runs. |

A judge is an ordinary agent with a row, an agent folder and a report. Its prompt's constraints say that it reads the code and changes nothing. Its task file states that it:

- runs every done-contract command itself. A claim it cannot reproduce is a FAIL, whatever the report says;
- tests at least one adjacent case per agent beyond the stated commands, such as a control that separates a pass from a failure, or a failure path;
- runs again the reproduction behind any claim that a defect no longer occurs;
- compares the agent's change with the craft bindings. A violation the change created is a FAIL; an earlier one the agent did not report is a note;
- runs a destructive test only in a scratch copy;
- gives the correction for every FAIL;
- writes its verdicts to `judgements/<judge-name>.md` and starts `reports/<judge-name>.md` with the verdict list.

## Check before handover

- Every checkpoint item remained after the pass-condition test, and no documented rule or the specification answers it.
- Every checkpoint without a judgment item is a hard checkpoint with the owner's reason in its text and a record in `decisions.md`.
- Every mechanical check has a judge agent whose task file holds its pass condition word for word.
- Every checkpoint row names rows of the workflow table, and every checkpoint file exists with both parts.
- `workflow.md` states in one line each that the plan has no checkpoint or no judge agent, where that is the case.
