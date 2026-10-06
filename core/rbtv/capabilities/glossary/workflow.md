# Workflow

A workflow arranges [tasks](task.md) by the results they need and the files they change. It lets independent work run together while dependent work waits for its inputs. A coordinating agent follows `workflow.md`; no command-line program schedules it from that file.

Use one row per agent. For a workflow of installed rbtv agents, follow [Planning a workflow](../../../../meta/plan/capabilities/methods/planning-a-workflow.md) for the complete plan folder, installation, review and handover. The table below is the common scheduling form, not a substitute for that method.

## Arrange the work

Start from settled work and its task inputs. Give each task one result that can be judged independently. Name the file or record it produces and the downstream task that reads it; the next agent must be able to use that result without its producer present. Use [Task](task.md) for the task's inputs, scope and done contract.

For each row, put in Needs every agent whose result it reads. Add an order between tasks that change the same file or record, naming the shared target in the scheduling rules. No chain of needs may lead back to itself. A preference about which task is more important is not a dependency.

```markdown
# <Workflow result>

| Agent | Task | Needs | Status |
|---|---|---|---|
| <agent name> | <task-file path> | <agent names, comma-separated; — for none> | open |

## Scheduling rules

<Shared-write order and the exact files or records it protects, when applicable.>
```

Task paths resolve from the workflow folder. Needs names rows in the same table. Status is `open`, `running`, `done` or `failed`; keep result evidence in the task's report rather than the cell.

## Coordinate and verify

Use [Delegating work](../../../../meta/sub-agents/capabilities/methods/delegating-work.md) for worker selection, launch and verification. Launch every open task whose needs are done and whose declared scheduling conditions allow it. Set running at launch; verify its result against its done contract before setting done. A failed result is failed and blocks its dependents. Reconsider ready rows whenever a result returns.

Before handover, check that task files exist, Needs names real rows, dependencies have no cycles and shared writes cannot overlap. Give a fresh reader the workflow and task inputs, then ask which tasks launch first, which become ready after a named result and which remain blocked after a failure. Correct any difference from the intended schedule. A successful agent launch alone does not verify these decisions.
