---
description: Structure a reusable component workflow manifest and its seat catalog
tags: [planning]
---

# Workflow anatomy — reusable component definitions

A reusable workflow lives in its owning component at `workflows/<name>/` with a `workflow.md`
that explains its purpose and a `<name>.csv` manifest that orders its seats. It is component
scaffolding. A console seat plan follows `plan.md` instead and has no manifest or seat catalog.

## Catalog and manifest

A component seat has one `seats.csv` row pairing a prompt with a task. The workflow manifest
references those seat ids; it does not duplicate prompt or task content. Give each seat one
bounded job and a done contract its reader can verify. Keep reusable prompts and tasks in the
component's flat `prompts/` and `tasks/` pools.

The manifest's `after` field names a real data dependency: the predecessor's output is an input
to this row. Independent rows remain roots. Check that the graph has no cycle and that every
input named by a seat is supplied by its entry request or a predecessor. A conditional branch
needs a written decision rule and an explicit result for each arm. Do not encode priority or a
shared-file lock as an `after` edge; document a custody rule for that resource.

## Registration check

Read `workflow-authoring-checklist.md` for each row. Then run `component-lint` on the owning
component, inspect its census, and verify that every manifest id resolves to a catalog row and
that every catalog row resolves to existing prompt and task files. A definition is finished when
its entry point, dependencies, and failure routes are understandable without a running instance.
