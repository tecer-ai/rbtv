# 20260910-c-plan-review-on-a-running-plan — plan-review on a running plan: seats.md payload, no edit

kind: change
component: meta-planning
date: 2026-09-10
commit: d26ba30c
deployed: yes
pin: NONE

## Motivation
The plan-review seat introduced by 20260910-c-plan-format-artifact-boundary (commit 6a43193a) rewrites `seats.md` directly. Its first live use, minutes after landing, was on a plan ALREADY RUNNING: the orchestrator rewrites `seats.md` every few minutes for status flips, so a reviewer edit would race those flips and one side would lose. The orchestrator ran the review with a deliberate deviation and reported it.

## Design
On a running plan the reviewer never edits `seats.md`; it emits the rewritten table, DAG and rules as a `## seats.md payload` block of its verdict file, and the orchestrator applies that payload as one edit between its own flips.

The rule is added in two places, commit d26ba30c: the section prose (§ The review before handover, the MAY-REWRITE paragraph) and the template body, where the condition is stated checkably — any row other than `read-first` reading `wip` or `done` means the plan is running. Rejected: a lock file on `seats.md` (new machinery for one race the payload form removes outright) and leaving the deviation undocumented (the next live review would re-discover the race).

## How it works
Pre-handover review, unchanged: the reviewer edits `seats.md`. Mid-run review: the reviewer reads the `status` column; on any `wip`/`done` beyond `read-first` it writes the payload block instead, and the orchestrator applies it in one edit and continues flipping. Frontmatter-only folder creation is unaffected in both modes.

## Consequences
Extends the 20260910 entry's review section; deletes nothing. A mid-run review now costs the orchestrator one apply step. No other surface changed.

## Verification
Reference text; no runnable surface. The rule reproduces the deviation the orchestrator session reported after running the first live review on 2026-09-10 (its ruling 44 in that plan's decisions.md). Live at commit d26ba30c.

## ATTENTION
- The running-plan test is the `status` column, not the orchestrator's presence: a plan with one `wip` row has a concurrent `seats.md` writer even when no session appears active, so the reviewer must never fall back to editing on "it looks idle".
- The running-plan test is the status column (any wip/done beyond read-first), never whether the orchestrator looks active
