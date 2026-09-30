<!-- How a workflow is written:
     - One row per agent. Agent: the installed agent's name. Task: the path of its task file, from this folder.
     - Needs: the agents in this table whose results the task reads, comma-separated; — when none.
       No chain of needs loops back. Two agents that change the same file or record never run together: one needs the other.
     - Status: open, running, done, or failed. The coordinating agent launches every open agent whose needs are all done,
       sets it to running when it starts, and to done or failed when it ends. -->

# <workflow>

| Agent | Task | Needs | Status |
|---|---|---|---|
| `<agent>` | `<task file>` | `<agent>, <agent>` or — | open |
