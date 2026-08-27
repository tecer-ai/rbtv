# 20260827-c-the-drafter-authors-the-contra — The drafter authors the contract and the plan's own seats

kind: change
component: meta-planning
date: 2026-08-27
commit: 35a4e98d
deployed: no
pin: ignite/planning/probes/probe-d13-verify-notify.py
components: meta-leader,planning,coord

## Motivation

The BIRTH reads files, and the pipeline produced none of them. `ee4a0334` (2026-08-27,
`20260827-c-the-plan-declares-its-birth-th`) gave the draft an EXECUTION DECLARATION carrying
exactly the fields `approve_package.py` takes — including `contract-file` — but made the file
itself optional ("where the plan names one"), which made the field expressible without making
anyone responsible for the file. On the very next run (`scratch-tool-inventory-8`, 2026-08-27) the
reviewer resolved the gap by writing the contract's TEXT inside `review-package.md` and assigning
the FILE to "the approving act", which has no authoring step; the owner's `approve` then refused
`--contract planning/execution-contract.md: No such file or directory` with the approval already
spent. The same run exposed the larger half: a one-off plan's execution seats existed only as prose
in the draft, and the birth has no catalog to mint prose from — the daemon's only lane for a seat
nobody cataloged is `materialize-seats.py --goal-local`, which reads `planning/current/`
(manifest.csv plus `seats/<seat>/` prompt+task pairs), a layout no planning seat was asked to write.
Filed as `G-leader-0827-2226` and, for the empty-roster half, `G-plan-designer-0827-2230`.
Separately, leader escalation #18 (`stale-hash-in-approval-digest.md`, same goal, same day)
recorded the verifier composing the owner's approval ask against a commit short by
`review-package.md`.

## Design

THE DRAFTER WRITES BOTH, and it is the drafter because its write surface already is `planning/` —
the one goal subtree the cage opens read-write to every seat (D3,
`d-s31-planning-workspace-shared-rw`) — and because the contract and the seat set are the SAME
decision as the plan they come from. Rejected: a sixth pipeline seat, which would put one plan in
two authors' hands and add an edge to a five-seat chain; rejected: the reviewer, whose product is a
findings list about the draft, not part of it; rejected: leaving the contract to the leader, which
would make a chair author a plan artifact it is otherwise forbidden to write. The
`workflow-authoring-checklist`'s "Only ONE `goal-writes`" rule reads as if it forbids this, so it
gains the sentence that resolves it rather than an exception: `goal-writes` names the seat's
PRODUCT — the thing its check-out is verified against — and a product with parts under `planning/`
is still one product. What the rule forbids is a role with two UNRELATED products.

`contract-file` stops being optional. It is `planning/execution-contract.md`, always, because the
birth reads it out of the bound tree and the writer refuses a path that is not a file under
`--plan-artifacts` — an optional field on a required file is how the first gap was expressible.

FOR THE STALE BINDING, the fix is the shape that already exists rather than a new mechanism: the
verifier REFUSES to compose and checks out `--incomplete`, and the leader's §4 already routes "a
seat that reports it cannot find `planning/bound-commit`" to disposition 1, FIX AND RELAUNCH. That
clause is extended to "or reports it STALE". The freshness test is MTIME — `planning/bound-commit`
must be newer than `planning/review-package.md` — chosen over the alternative of having the leader
write the bound tree's file list beside the sha, because mtime needs nothing new from the leader,
adds no format to keep in step with the commit, and does not create a second home for a fact the
git tree already holds; it also catches a review package REWRITTEN after the bind, which a file
list would not. It is compared strictly (older than = stale), so a same-second bind reads as fresh
rather than storming. What is DELETED is the verifier's own re-bind routing: raising the shortfall
as a digest red flag and routing the re-bind at the leader is what shipped an approval ask whose
commit was already wrong.

## How it works

`tasks/draft-plan.md` widens its Write clause to the three artifacts and adds done criteria for
each: the contract is BODY ONLY (no frontmatter — `scaffold` writes the goal's own above it and a
second `---` block lands inside the body, measured), it is the owner's request restated as the born
goal's contract plus a pointer to the plan artifacts at the bound commit, and it is not a copy of
the draft. For a plan that declares no `workflow`, `planning/current/` carries `manifest.csv`
(header `Seat/workflow,after,i/o,Modality`), one `seats/<seat>/` folder per row holding a prompt
(frontmatter `id:` + `<role>` + a `<permissions>` block) and a task (frontmatter `id:` +
`<task-goal>`), and `bindings.json` casting every manifest seat with a harness and a model. The
criteria name the exact refusals the birth will raise — a `<permissions>` block is a HARD GATE, an
`on-fail-relaunch` cell names a SEAT rather than a boolean, an id may not shadow a cataloged one, an
`after` member must exist, an uncast seat is refused — because each is otherwise discovered after
the owner has approved. `prompts/drafter.md` carries the same as procedure step 4b plus the write
surface and the io-spec outputs. `tasks/review-plan.md` and `prompts/reviewer.md` make every one of
those malformations `blocking`, and make a plan that assigns the contract file to "the approving
act", to the leader, or to any later seat blocking too — fixed by the drafter writing it, never by
naming another performer. `workflows/plan-console/workflow.md` states the two artifacts and both
mint routes at the top; `plan-console.csv` and `seats.csv` carry them in the drafter's row.

`prompts/verifier.md` gains step 4b, scoped to the lane whose task Reads `planning/review-package.md`
so the notify-only D13 seat that shares this prompt is untouched, and `tasks/verify-plan.md` gains
the matching done criterion and outcome row. `meta/leader/prompts/leader.md` §4 gains the STALE arm
with the reason the wake is normal: the `after` edge and the leader's wake fire off the same
check-out, so an unlucky order is expected, not an incident.

## Consequences

Nothing was deleted from the catalog. The verify seat's own `--force` habit is closed at the same
time: `verify-plan.md` and `verifier.md` now state that an `--approve-commit` send carries no length
cap (`ignite/coord/messages.py`, same day) and that `--force` is not how a digest is sent. One
behaviour is genuinely new: the plan-console run gains a relaunch on the path where the reviewer
checks out and the leader has not yet re-bound — the verifier refuses, checks out `--incomplete`,
the staff mail wakes the leader, it re-binds and relaunches. That relaunch is the intended
self-healing shape, and it was already disclosed as such when the binding act landed
(`20260827-c-the-plan-declares-its-birth-th`); this makes it fire on STALENESS as well as absence.
A plan that declares a `workflow` + `sheet` writes no seat set and no sheet — the catalog carries
those seats — so the new criteria are conditional, not universal.

## Verification

`component_lint --component meta/planning` reports 5 findings and `--component meta/leader` reports
2, identical before and after (all pre-existing: four `resources-coverage` and one
`exposes-body-match` on prompts this change does not touch; two over-length `<resources>` bullets on
leader.md). `probe-d13-verify-notify.py` 16/16 PASS after the edit, which is what proves the two new
verifier steps are correctly scoped to the approval lane — that probe reads the shared `verifier`
prompt against the D13 notify-only task. The authored-seat layout was proven end to end offline: a
scratch vault under /tmp whose planning goal carried exactly the files these texts ask for, COMMITTED,
births a daemon-lane goal with the plan's two seats plus `leader` and `goal-master` on its
`taskforce.csv` and the contract as its `goal.md` body. Both defects the texts describe were
reproduced first in the same fixture. NOT DEPLOYED — and these texts need no deploy: the catalog root
for `meta` is `rbtv.json`'s `rbtv_path` (`unbuilt-seats.js:61`), the working repo, so a FRESH goal
renders them at materialize. An already-materialized goal does not.

## ATTENTION

- THESE TEXTS ARE LIVE THE MOMENT THEY ARE ON DISK. The catalog root resolves through `rbtv.json`'s
  `rbtv_path`, not the deploy worktree, so there is no "not deployed yet" margin for a bad edit
  here — only "no goal has materialized since".
- `prompts/verifier.md` IS SHARED BY TWO TASKS. `verify-plan` (approval) and `verify-patch` (D13
  notify-only) pair with the same prompt, so any step added to it must be scoped by what the paired
  task's own clauses name — an unscoped step sends the replan seat looking for a review package
  that does not exist on that lane.
- THE CONTRACT FILE CARRIES NO FRONTMATTER. `goal_cli.py scaffold` reads `--contract` as the goal.md
  BODY and writes its own frontmatter above it; a contract with its own `---` block produces a goal
  whose body opens with a second one.
- DO NOT RE-ROUTE A STALE BINDING FROM THE DIGEST. Raising it as a red flag and asking the leader to
  re-bind is what produced an approval ask citing a commit that was already superseded, in front of
  an owner one word away from starting execution. The refusal has to be BEFORE the compose.
- `on-fail-relaunch` IN A GOAL-AUTHORED PROMPT NAMES A SEAT. YAML turns a `yes` into a boolean and
  the birth refuses `on-fail-relaunch-unknown-seat` naming "True" — measured while building the
  offline fixture for this change.
- verifier.md is shared by verify-plan and D13 verify-patch — scope every added step by the paired task's own clauses
