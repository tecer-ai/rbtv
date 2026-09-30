# plan

The `plan` skill (`skills/plan.md`) structures decided work as a workflow of installed agents.
Each agent is installed with `rbtv install agent add` and launched with `cast -ig`; a coordinating
agent schedules them from `workflow.md` (a table of `Agent | Task | Needs | Status`), verifies their
reports, and uninstalls them when the plan closes. The plan folder keeps the agent files.

## Entry points

- `skills/plan.md` — the plan folder format, the sizing rules, and the coordinating agent's contract.

The component has no resident planning runner. A plan's agent files, task files and reports live in
the plan folder named by its caller. How to build any RBTV component is in the build documentation
(`core/build/capabilities/rbtv.md`).
