# planning

The `plan` skill (`skills/plan.md`) structures decided work as a seat plan. A console
orchestrator dispatches its self-contained seats with `cast seat`, verifies their reports, and
records the result in `seats.md`. The `build` skill (`skills/build.md`) routes component
scaffolding work to the matching authoring guide or to a seat plan when the work spans units.

## Entry points

- `skills/plan.md` — the console plan folder, scheduling and verification contract.
- `skills/build.md` — component authoring router; its mandatory reads are `ethos.md`,
  `component-anatomy.md`, and `exposure.md`.
- `references/workflow-anatomy.md` and `skills/workflow-authoring-checklist.md` — format
  for reusable component workflows. Those workflows are catalog entries, separate from a
  console seat plan.
- `capabilities/component-lint/` — deterministic checks for authored components.
- `capabilities/capability-cards/tool/capability_cards.py` — live exposure cards used while
  assigning instruments to plan seats.
- `capabilities/stools-wrapper/` — the approved workspace file transfer command.
- `skills/google-workspace.md` — Google Workspace requests through the external `gtools` CLI; its existing `ws:` tool row remains in this component's exposure manifest.

The component has no resident planning runner or seat catalog. A plan's seat bodies and
reports live in the plan folder named by its caller.
