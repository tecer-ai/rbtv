# Workflow

A set of [tasks](task.md) arranged as a DAG (directed acyclic graph): each task names the tasks whose results it needs, and no chain of needs loops back on itself. [Sub-agents](agent.md#sub-agent) launched through `cast` run it. Each agent in a workflow is an [rbtv agent](agent.md#rbtv-agent) in the plan folder, launched with `cast --agent NAME`. Every task whose needs are met runs at the same time, except tasks that would change the same file or record, which run one after another ([Micro agency](../principles/keep-it-stupidly-simple.md)).

A workflow is written in a `workflow.md` file: one row per agent, with its task, the agents whose results it needs, and its status. The agent that coordinates the workflow reads it, launches every agent that is ready, and updates each status; no CLI reads it.
