# 20260831-i-after-edge-launched-against-a — after-edge launched against a stale bound-commit

kind: issue
component: supervisor
date: 2026-08-31
commit: 81e516275c6b29f74dfe3cb33dbc9563944d99ce
deployed: no
pin: ignite/planning/probes/probe-bound-commit.py
components: planning,meta-leader,meta-planning

## Observed
A planning successor became READY the instant its predecessor checked out, while `planning/bound-commit` was older than the just-landed artifact. Measured on `meet-transcript-summarizer-planning` (verify sitting 1, bound-commit 969s older than `review-package.md`) and `ignite-engine-planning` (reviewer launched at 20:08 against `8aca9b15` while the leader rebound at 20:09). Recurrence: every `planning/` write invalidated the bind and the after-edge spawned in the same window. Reproduced 2026-08-31 on a `test-bound-commit` fixture: `supervise ready-seats --json` reported verifier READY / `after: reviewer=done` with bound-commit 120s older than review-package.md.

## Mechanism
`ready.py#ready_seat_rows` treated predecessor `done` as sufficient for successor READY. The bind was a later leader hand act (`leader.md` §4). Seeding consumed `verdict === READY` and launched. Occupant prose (verifier step 4b) could refuse after launch; it could not stop the spawn. A refuse-stale-only patch without an automatic bind would stall the pipeline on the leader.

## Attempts
First attempt held — checked: `meta-planning/20260827-c-the-drafter-authors-the-contra` (mtime freshness as occupant refuse, leader disposition 1), `meta-planning/20260827-c-the-plan-declares-its-birth-th` (caged seats never run git), `meta-leader/20260828-i-no-leader-register-for-an-orde` (armed incomplete relaunched before rebind), `supervisor/20260831-i-successor-launched-on-sitting` (after-edge vs gate-artifact, a different term). Live goals were hand-rebound; the after-edge arithmetic was not changed.

## Fix
A successor with met `after` members is BLOCKED `bind=stale` when `planning/bound-commit` exists and is older than another file under `planning/` (roots and unbound packages unchanged). `planning_bind.py` is the one bind act: seeding calls it before ready-seats so the same pass can offer READY on a fresh hash without a leader sitting. Frozen once `approve-package.json` records `bound_commit` (`p-no-rebind-after-the-ask-is-delivered`) — the standing stale-binding rule must not move a delivered ask's hash. Rejected: occupant-only refuse (fails criterion 2), caged seats repairing the bind (`.git` masked), committing twice to make the in-tree pointer equal the named hash (memory ATTENTION on the birth-th entry).

## Consequences
Verifier/leader prose no longer treat leader hand-rebind as the pipeline's only advance. `probe-failed-upstream-gate` still passes: that fixture has `planning/` evidence and no bound-commit, so the new term does not apply. Daemon-side until deploy.

## Verification
`ignite/planning/probes/probe-bound-commit.py` PASS 2026-08-31 (red: freshness skipped → READY; green: BLOCKED bind=stale; after bind() READY; freeze holds). `probe-failed-upstream-gate.py` PASS. Not deployed.

## ATTENTION
- `git commit -- planning/` snapshots the working tree. A tracked `bound-commit` sitting on disk is pulled into the named tree even after `git rm --cached`. The bind unlinks the pointer for the commit, then writes it.
- Do not rebind after `approve-package.json` records `bound_commit`. That freeze is mechanical; a leader sitting that "cleans" the pointer moves the hash a live ask names.
- ready-seats writes nothing. Auto-bind lives in seeding, not in the verdict computer.
- git commit -- planning/ snapshots the working tree; unlink bound-commit for the commit
- do not rebind after approve-package.json records bound_commit
- ready-seats writes nothing; auto-bind lives in seeding
