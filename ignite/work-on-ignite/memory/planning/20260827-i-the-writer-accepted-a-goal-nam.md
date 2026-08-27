# 20260827-i-the-writer-accepted-a-goal-nam — The writer accepted a goal name the scaffold refuses

kind: issue
component: planning
date: 2026-08-27
commit: 4d06233b
deployed: no
pin: ignite/planning/probes/probe-approve-package.js
components: meta-planning

## Observed

While proving `cf79c881`'s birth path end to end on a scratch vault under /tmp (2026-08-27), an
execution goal named `Scratch_Exec` was accepted by `ignite/planning/approve_package.py` — the
writer exited 0 and the package landed — and then refused by `rbtv-goal scaffold` inside the birth,
with `class: atomic-core-refusal`, `code: scaffold-refused`. In production that sequence is a
refusal in the owner's Slack thread AFTER `approve`, with the approval spent and every planning seat
departed: the same shape as the `contract_file` and roster failures that `cf79c881` had just moved
to the writer. HEAD and deployed were both 96732ef0 at the time; the writer is read live by whatever
runs it, the scaffold by the daemon's deploy worktree.

## Mechanism

Two rules for one field, and the writer re-spoke only the wider one. `SAFE_NAME_RE`
(`^[A-Za-z0-9][A-Za-z0-9._-]*$`) is `bus-ferry.js#isSafeName` in Python, and the writer's own header
names that function and `start-execution.js#COMMIT_RE` as the readers it validates against. But
`execution_goal` has a THIRD reader: `path_b.run_scaffold` hands it to `goal_cli.py#cmd_scaffold`,
whose `GOAL_NAME_RE` is `^[a-z0-9]+(?:-[a-z0-9]+)*$` — lowercase kebab-case, strictly narrower. Any
name carrying a capital, an underscore or a dot sits in the gap between them: valid to write, fatal
to birth.

## Attempts

First attempt held — checked: `git log -S SAFE_NAME_RE` over `approve_package.py` back to its
landing `b2449ebe` (2026-08-25) and its memory entry
`planning/20260825-c-the-approve-package-writer`. That entry states the design rule this defect
violates — "every required field exists because `start-execution.js#readApprovePackage` or
`path_b.py#run_path_b` consumes it, and the two validations are the reader's own rules re-spoken" —
and names two readers where the field has three. `goal_cli.py`'s rule predates the writer
(`GOAL_NAME_RE` is at `goal_cli.py:60` and unchanged through 96732ef0), so nothing narrowed under
the writer's feet; the third reader was simply never counted.

## Fix

`GOAL_NAME_RE` is re-spoken beside `SAFE_NAME_RE` and `is_safe_name` requires both. Re-spoken rather
than imported: `goal_cli.py` is a 5,000-line CLI monolith whose import would drag the whole goals
tree into a writer that runs inside a caged planning seat, and the writer already carries copies of
the ferry's and the daemon's rules for exactly this reason — the copies are the contract, and each
carries a comment naming the reader it belongs to. The refusal detail names both readers, so a seat
reading it knows which door it failed. The four pipeline texts that quoted the old pattern at the
drafter and the reviewer (`tasks/draft-plan.md`, `prompts/drafter.md`, `tasks/review-plan.md`,
`prompts/reviewer.md`) now quote the narrow one — a plan is checked against the rule that will
actually be enforced, two stages before the birth.

## Consequences

Strictly narrowing: a package the writer used to accept it now refuses, and nothing that used to
refuse now passes. No live package is affected — `scratch-tool-inventory-8`'s declares
`scratch-tool-inventory-8-exec`, which satisfies both rules. `probe-approve-package.js`'s R2 arm
already covered a name with path separators; R2b covers the gap between the two rules and is red on
the old code.

## Verification

`probe-approve-package.js` 22/22 → 23/23 EXIT 0, R2b red before the fix (the writer exited 0 on
`Born_Exec`) and green after. On the offline scratch vault: `Scratch_Exec` now refuses
`bad-execution-goal` at the writer with NO package written, where before it wrote one and died at
the scaffold; the same fixture's `scratch-exec` birth is unchanged and still lands its four
taskforce rows. `component_lint --component meta/planning` 5 findings, unchanged. NOT DEPLOYED.

## ATTENTION

- THIS FIELD HAS THREE READERS, NOT TWO. `bus-ferry.js#isSafeName`, `start-execution.js`, and
  `goal_cli.py#cmd_scaffold` — and the scaffold's is the narrowest. A future editor loosening
  `SAFE_NAME_RE` to match the ferry alone reopens a refusal that can only fire after the owner has
  approved.
- THE RULES ARE COPIES ON PURPOSE, AND EACH NAMES ITS READER. Importing `goal_cli.py` to "stop
  duplicating" pulls a 5,000-line CLI into a caged seat's writer. If a reader's rule changes, the
  copy is updated in the SAME change — the comment above each copy is what makes that findable.
- execution_goal has THREE readers; goal_cli.py#GOAL_NAME_RE is the narrowest and only it rejects Capitals/underscores/dots
