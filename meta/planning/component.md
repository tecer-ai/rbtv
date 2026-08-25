---
description: The planning component — the intelligence-generation mechanism that authors seats, workflows, and taskforces for every goal, optimize, port, and scaffold request
---

# planning

The `plan-console` workflow turns a planning request — an ad-hoc goal, an optimize, a port, or a
scaffold ask — into an owner-approved plan. Five seats, one linear pass, four lean stages (understand
→ design → draft → review+finalize, plus a separate verify seat): rolling planning is dead — no
goal-level/per-milestone split, no per-use-case fork. Whether the plan lands as a one-off taskforce
(ad-hoc) or a durable workflow (optimize/port/scaffold) is the owner's declaration at goal creation,
honoured by the draft stage alone; no seat branches on it.

The `d13-replan` workflow is the gate-failure lane: when a milestone's closing judge returns FAIL, three seats — understand → draft → verify — patch that ONE milestone inside its unwidened permission envelope, checked against its unchanged done contract, without stopping the goal. It reuses the `understander` / `drafter` / `verifier` prompts; all three of its tasks are D13-specific. Its verify seat is NOTIFY-ONLY (owner ruling 2026-08-25): `verify-patch` reports what it finds to the owner and the replan finishes either way — no verdict, no `on-fail-relaunch` route, no approval outcome, nothing withheld.

The `forge` workflow is the small-request lane beside it: one create, edit, or parse request for a PART of a component that already exists — a reference, prompt, task, seat, capability, exposure entry, or sub-agent definition — scoped, built, registered, and judged in one serial three-seat run.

## Entry points

- Router surface: `references/build.md` — the ONE console entry, exposed as the `build` skill; it holds the workflow-vs-guide route rule, the kind router (moved out of forge's console entry), and the guide table. The standalone `planning`, `forge`, and `plan-in-session-run` skills folded into it (owner-ruled 2026-08-21).
- Workflow `plan-console`: `workflows/plan-console/` — `workflow.md` (orientation) + `plan-console.csv` (the five-seat linear DAG: understand → design → draft → review+finalize → verify).
- Workflow `forge`: `workflows/forge/` — `workflow.md` (orientation) + `forge.csv` (three serial seats: intake → builder → judge). Small, frequent create/edit/parse requests for PARTS of components that already exist; it executes what it specifies, and a request needing a new component, workflow, or DAG escalates to `plan-console`.
- Workflow `d13-replan`: `workflows/d13-replan/` — `workflow.md` (orientation) + `d13-replan.csv` (three serial seats: understand → draft → verify, seat-ids `repl-*` because a workflow code must be four ASCII letters). The D13 gate-failure mini-pipeline, minted into an EXISTING execution goal through the same supervised materialize door as plan-approval (path A) — never a second door, never a new goal. The two-failed-replan cap it documents is daemon policy, not seat behaviour, and it is the only cap in the lane — the verify seat holds none.
- Pools: `prompts/<id>.md` and `tasks/<id>.md` (one file per prompt/task, kind-named XML sections; no prompts.csv/tasks.csv — `d-prompt-task-files`).
- `seats.csv` — the prompt+task pairings; prefix `plan` for the plan-console workflow, `forg` for forge, `repl` for `d13-replan`. `researcher`/`diagnoser` are cataloged definitions fanned out as SUB-AGENTS by planning seats (exposure rows in `exposure.csv`); they hold no workflow node.
- Judge/eval pool — the two closing-seat definitions (`prompts/dod-judge.md` + `tasks/judge-milestone.md`, `prompts/unblock-checker.md` + `tasks/check-unblocked.md`, rows in `seats.csv`) the `drafter` shops into every PRODUCED taskforce as its closing seats; they hold no `plan-console.csv` node.
- `references/` — the 16 craft/anatomy guides + the shared ethos (`ethos.md`). Forced reads for authoring seats; stage C wires the read steps.
- `capabilities/` — `capability-cards` (resource shopping CLI) and `component-lint` (the component's lint step).
