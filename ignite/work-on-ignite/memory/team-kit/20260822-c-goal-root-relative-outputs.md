# 20260822-c-goal-root-relative-outputs — goal-root-relative-outputs

kind: creation
component: team-kit
date: 2026-08-22
commit: ffdf2dc2
deployed: yes
pin: NONE
components: meta-planning
seeded: true

## What it is
D90 (#594 second half): a goal-root-relative output declaration grammar — `./name.ext`.

Lets a seat declare an output like `goal.md` or `milestones.csv` that lives at the goal root rather than inside its own seat folder, so `review-goal-completeness.md` and `structure-milestone-dag.md` stop being leader-flipped.

## Why
D90 (owner, 2026-08-22): option A of #594's second half — extend the output-declaration grammar (both the templates and the cage-admission gate's output resolver) so a goal-root-relative output is declarable. Before this, the two templates `review-goal-completeness.md` and `structure-milestone-dag.md` produced outputs the cage-admission gate could not resolve against a seat-scoped path, so the leader had to flip in and write them by hand instead of the intended seat.

## How to use & where wired
`ignite/team-kit/coord.py` (output-declaration grammar + cage-admission gate's output resolver, +81 lines), `meta/planning/tasks/review-goal-completeness.md`, `meta/planning/tasks/structure-milestone-dag.md` (both templates updated to declare their outputs via the new `./name.ext` grammar). Commit `ffdf2dc2` ("declare goal-root outputs via ./name.ext (D90, #594 second half)").

## commit
ffdf2dc2

## deployed
yes

## pin
NONE

## ATTENTION
- This is a grammar EXTENSION, not a replacement — seat-scoped output declarations still work the old way; only a `./`-prefixed path resolves against the goal root. A template author who forgets the `./` prefix on a goal-root file will get the old seat-scoped (wrong) resolution silently.
- Extension not replacement; a template author who forgets the ./ prefix silently gets old seat-scoped resolution
