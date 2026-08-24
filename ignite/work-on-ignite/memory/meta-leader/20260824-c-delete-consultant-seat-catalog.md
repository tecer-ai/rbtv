# 20260824-c-delete-consultant-seat-catalog — delete consultant seat catalog definition

kind: change
component: meta-leader
date: 2026-08-24
commit: 5962ff7f
deployed: no
pin: NONE
components: meta-master,meta-planning

## Motivation

[T2-R17, D-7-ruling] deleted the `consultant` role. Commit `bbbddaac` (team-kit/engine) removed it
from `STAFF_SEATS`, `bus-answer.js`'s routed-types table, `reconcile.js`'s `STAFF_CHAIRS`, and the
`--route consultant` verb — but explicitly left `meta/leader/` untouched, flagging that the
catalog layer still fully DEFINED and CAST a `consultant` seat. Casting one there today would have
produced a broken ordinary seat: no staff-chair exemption applies to it any more in the runtime,
since `STAFF_SEATS` no longer names it. This entry finishes the deletion at the catalog/definition
layer.

## Design

Pure deletion, matching the shape subsystem 8 used when the `closer` seat class was deleted
(`closer-prompt.md` removed via `git rm`, commit `4930e6a9`): the `consultant` prompt file is
deleted outright rather than archived or stubbed, and every place that described it as a
currently-castable seat is rewritten to describe the sole remaining staff seat, `leader`. No
replacement mechanism was invented — the goal has exactly one staff chair now, mandatory, and the
two-seat "OPTIONAL per workflow" framing that ran through `meta/leader/component.md` and
`meta/planning/references/workflow-anatomy.md` (`## 5 — taskforce.csv`) collapses to a
single-chair description rather than being left describing a phantom second seat.

## How it works

Five files changed:
- `meta/leader/prompts/consultant.md` (95 lines, the seat's whole prompt) — deleted via `git rm`.
- `meta/leader/component.md` — rewritten from a two-seat component description to a one-seat one:
  header `description:`, body prose, the `## Seats` table row, the `## Parts` bullets (including
  the two "Neither X" bullets for `exposure.csv`/`workflows/` that referred to both seats), the
  owner-contact carve-out paragraph, and the closing "owed to the registry" line (now states
  plainly that nothing is owed, since no `consultant` KG term was ever minted).
- `meta/leader/seats.csv` — the `consultant,consultant,serve-staff-mail,...` data row deleted,
  header and the `leader` row preserved byte-for-byte; verified with `python3 -c "import csv;
  print(list(csv.reader(open('meta/leader/seats.csv'))))"` (2 rows, 9 columns each) and with
  `component-lint --component meta/leader` (census now `prompts=1 seats=1`, `seat-integrity`
  clean).
- `meta/master/references/master-scaffold-flow.md` (§6, "Goal-master chair") — a sentence
  contrasting goal-master's auto-mint against the "consultant chair staffs itself once
  `.rbtv/config/modules/meta/leader/bindings/consultant.json` exists" now reads `leader`/
  `leader.json`, since `leader` is minted through the same casting-sheet mechanism the file
  already documents elsewhere.
- `meta/planning/references/workflow-anatomy.md` (§5, "taskforce.csv") — the bullet describing the
  taskforce's STAFF CHAIRS (`leader` mandatory, `consultant` optional, cast via
  `bindings/<chair>.json`) rewritten to describe the single mandatory `leader` chair only.

## Consequences

Deletes the last DEFINITION-layer trace of the `consultant` seat (runtime traces already removed
in `bbbddaac`). Nothing downstream references the deleted prompt file, casting-sheet path
(`bindings/consultant.json`), or catalog row any more inside `meta/`. No regression expected: the
seat was never staffable at runtime after `bbbddaac`, so no live goal could have been relying on
casting it.

## Verification

`component-lint --component meta/leader` run clean on `seat-integrity` (census `prompts=1 tasks=1
seats=1`, no orphan/dangling findings); the two `resources-coverage` FAILs it still reports are
pre-existing bullet-length issues in `leader.md`, untouched by this change. CSV parsed and
row/column-counted with Python's `csv` module. Grep floor `git grep -n -iw 'consultant' -- meta`
run clean except the one correctly-historical sentence left in `component.md`'s provenance
section. Not deployed to any running goal — this is a pre-commit tree edit on
`ignite/core-redesign`, deployed status `no`.

## ATTENTION

- The seat's OWED KG mint is now VOID, not deferred — `component.md` used to say a `consultant`
  term was owed to the registry; it is not, because the role no longer exists. Anyone who finds an
  old note referencing that debt should close it, not pay it.
- `bindings/consultant.json` (a casting sheet path, never a file present in this repo) is dead
  vocabulary now; do not resurrect it as a config knob without first re-litigating [T2-R17,
  D-7-ruling].
- The memory entry for the runtime-layer deletion (`bbbddaac`) that this entry completes was filed
  by a prior sitting into a DIFFERENT clone of this repo
  (`3-resources/tools/rbtv/ignite/work-on-ignite/memory/team-kit/20260824-c-delete-consultant-staff-chair.md`,
  on branch `ignite/core-daemon`, uncommitted there) — it is not present in this worktree
  (`ignite/core-redesign`) or its git history. A future reader on this branch will not find it by
  browsing this worktree's memory folder.
- consultant KG mint is void, not owed
- runtime-deletion memory entry lives in a different clone/branch, not this worktree
