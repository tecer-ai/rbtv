# 20260824-c-retire-the-17-rolling-planning — retire the 17 rolling-planning seat definitions

kind: change
component: meta-planning
date: 2026-08-24
commit: 6318207d
deployed: no
pin: NONE

## Motivation

The five-seat one-pass pipeline (`67f93286`) and the D13 replan mini-pipeline (`32ad68a8`) replaced
the rolling-planning shape [D9, D10] but deliberately left its seat definitions in the catalog: the
planning workflow.md said in so many words that "their retirement from the catalog is a later
change, not this one". That left `meta/planning/seats.csv` carrying seventeen rows no workflow
manifest names, with their prompt and task files still on disk — a teachable, castable definition of
a workflow that no longer exists. `component-lint` scored the state at 52 findings, forty of which
were exactly those orphans.

## Design

Pure deletion, matching the shape used when the `consultant` seat class was retired at the catalog
layer (`5962ff7f`): the rows and the orphaned prompt/task files are removed with `git rm`, never
archived or stubbed, and every place that described them as currently-castable is rewritten to
describe the live five-seat pipeline instead. The retirement set was DERIVED, never remembered — a
seat was retired only when it appeared in no workflow csv, no live doc procedure and no
execution-plan shopping surface. `forge/`, the judge pool (`dod-judge`, `unblock-checker`),
`researcher` and `diagnoser` are kept unconditionally: execution plans shop them regardless of how
few references a grep returns.

## How it works

Seventeen `seats.csv` rows deleted (`plan-interviewer`, `plan-completeness-reviewer`,
`plan-splitter`, `plan-dag-structurer`, `plan-task-definer`, `plan-resource-definer`,
`plan-assembler`, the six `plan-check-<dimension>` swarm seats, `plan-check-mechanization`,
`plan-check-assembler`, `plan-binder`, `plan-planner`), with the twelve prompts and seventeen tasks
that no surviving seat pairs. `checker.md` went with the swarm; `check-unblocked.md` did not,
because the judge-pool `plan-unblock-checker` still pairs it.

Docs-in-sync rode the same commit. `workflows/planning/workflow.md`'s closing paragraph now records
the splice as GONE rather than as cataloged-but-unused. `workflows/planning/console-entry.md`'s step
2e taught arming `coordination/edge-fastpath.json` so the edge-runner could discharge a
`planning-mode` guard and a `use-case` alternate; the manifest carries neither any more, so the step
now states there is nothing to arm and names the leftover arm file as dead configuration.
`component.md`, `references/ethos.md` (its carrying-prompt roster, eleven → nine),
`component-anatomy.md`, `exposure.md`, `exposure-choice.md`, `file-prompt.md`, `file-task.md`,
`seat-id-naming.md` and `workflow-authoring-checklist.md` lost their retired-seat examples and
citations.

`prompts/intake.md` (forge) carried the user-stories gate as a verbatim copy sourced from
`prompts/interviewer.md#user-stories-gate`. Deleting the interviewer left the copy's home gone. The
gate text is unchanged byte for byte; the carried-block wrapper and its markers are dropped, because
a canonical block with exactly one carrier is ceremony — forge's intake is now the gate's one home,
and its own prose says so.

`component-lint`'s `dimension-roster` vacuity tripwire inferred "a check swarm exists" from a
check-* task STEM. With the swarm gone, the surviving judge-pool `check-unblocked.md` tripped it and
the check reported "0 carry a dimension clause — nothing was checked" on a component with no
dimensions at all. It now keys on the sign its own converse branch already used: a check-* task held
by a MANIFEST ROW.

## Consequences

`meta/planning` holds twenty seats, twelve prompts and nineteen tasks where it held thirty-seven,
twenty-four and thirty-six. `component-lint --component meta/planning` drops from 52 findings to 5,
and all five are pre-existing `coordinate`-grant/`<resources>`-bullet findings on KEEP prompts
(`builder`, `dod-judge`, `intake`, `unblock-checker`) that were present in the pre-change baseline —
zero new findings. Nothing under `meta/` references any retired id.

`ignite/` still names several retired seat-ids, in daemon code this change does not own: narrative
comments and test fixtures in `engine/reconcile.selftest.js`, `team-kit/materialize-seats.py`,
`team-kit/ready.py`, `capabilities/bindings/`, `server/spawn/`, `bridges/chat/`. One of them is a
live probe assertion, not a comment — `capabilities/bindings/probes/probe-bindings.py` asserts on
`plan-binder` in the REAL `meta/planning/workflows/planning/planning.csv` — but that manifest lost
its `plan-binder` row at `67f93286`, so the probe was already stale before this change.

## Verification

`component-lint --component meta/planning` before (52 findings) and after (5, all in the before-set)
— the census fell from `prompts=24 tasks=36 seats=37 dimensions=7 carried-blocks=22` to `prompts=12
tasks=19 seats=20 dimensions=0 carried-blocks=9`. `test_component_lint.py` passes 112 tests, one of
them new: `test_green_lone_pool_check_task_no_swarm`, which reproduces the planning
`check-unblocked` shape (a check-* task on a pool-sanctioned seat with no manifest row) and was
confirmed RED against the old tripwire before being made green by the fix.

End-to-end, on a throwaway goals root under `/tmp` and never the live goals tree: `rbtv-goal
scaffold` + `rbtv-goal materialize <toy> --catalog-root meta/planning --dry-run --json` returns exit
0, `"dry_run": true`, and exactly the five pipeline seats; `rbtv-goal dag` prints the linear
understand → design → draft → review+finalize → verify chain and `check-acyclic` reports the
after-graph clean. Not deployed: a pre-commit tree edit on `ignite/core-redesign`.

## ATTENTION

- The retirement set was derived from a reference sweep, never from the seat names. Any future
  catalog deletion here repeats the sweep: `forge/`, the judge pool, `researcher` and `diagnoser`
  survive a zero-reference grep because execution plans shop them, and a grep-driven deletion would
  take them out.
- `capabilities/bindings/probes/probe-bindings.py` asserts on the seat-id `plan-binder` against the
  live `planning.csv`, which has not carried that row since `67f93286`. The probe is stale, and a
  future reader will misread it as proof the row should still exist.
- `prompts/unblock-checker.md` and `tasks/check-unblocked.md` still read a `planning-mode` stamp off
  `milestones.csv`, while `prompts/designer.md` now explicitly refuses to write one. That contract
  gap is real and untouched here — the judge pool is out of this change's scope.
- The user-stories gate has no canonical-block source any more. Amend it in `prompts/intake.md`;
  `git show 6318207d^:meta/planning/prompts/interviewer.md` is where its former home reads.
- derive a catalog deletion from a reference sweep; forge/judge-pool/researcher/diagnoser survive a zero-reference grep
- probe-bindings.py asserts on plan-binder against a planning.csv that lost the row at 67f93286
- unblock-checker still reads a planning-mode stamp the new designer refuses to write
