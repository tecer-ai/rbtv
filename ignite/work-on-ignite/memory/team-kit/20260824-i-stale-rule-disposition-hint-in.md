# 20260824-i-stale-rule-disposition-hint-in — stale rule-disposition hint in ready.py HELD row

kind: issue
component: team-kit
date: 2026-08-24
commit: 26c14aac
deployed: no
pin: NONE

## Observed
`ignite/team-kit/ready.py` (post-2026-08-24 move-only split of `coord.py`, commit 867a240f),
`cmd_ready_seats`'s HELD-row detail line (~line 1578) still instructed the leader to run
`rule-disposition {rec['seat']} <destination> --anchor <a> --go` to release a hold. This is one of
the two sites `team-kit/20260824-c-delete-rule-disposition-ruled.md` (commit 7b978663) explicitly
disclosed as a left-alone loose end in its ATTENTION #2 (the other being `attest-exit`'s closing
hint, out of scope there per the task's hold-anchor-store boundary) — deployed tree and HEAD agreed
on the stale text; nothing had touched it since the parent deletion.

## Mechanism
`cmd_rule_disposition` and its CLI verb were deleted whole under ruling [T2-R12, T1-R9] (grant-store
authority model retired), but this f-string in `cmd_ready_seats`'s hold-detail branch was not
rewritten in that pass — it still named the deleted verb with a full runnable invocation, which a
leader reading the HELD row would have tried to run and found nonexistent.

## Attempts
First attempt held — checked `team-kit/20260824-c-delete-rule-disposition-ruled.md` and
`engine/20260824-c-fix-stale-rule-disposition-ref.md`: the former named this exact line as
untouched by design (out of its scope boundary), the latter fixed cross-component sites
(`reconcile.js` and friends) but was scoped away from `ignite/team-kit/` entirely. No prior attempt
touched this line.

## Fix
Reworded the clause to the established sibling pattern already used at `ready.py:~1124`
(`cmd_launch`'s renew-blocked detail) and `cli_main.py:~905` (`--reopen`'s refusal-door text): state
the row "is still rulable" but that `` `rule-disposition` `` was deleted [T2-R12, T1-R9] and no
replacement ruling instrument is wired here yet, instead of handing out dead CLI syntax. The
`{_hold}` conditional and surrounding f-string mechanics are unchanged — only the trailing clause's
wording changed.

## Consequences
No behavior change (this is a printed report line, not a control path). Closes the loose end
`team-kit/20260824-c-delete-rule-disposition-ruled.md` ATTENTION #2 flagged for `cmd_ready_seats`.
The sibling loose end at `attest-exit`'s closing hint (`attest.py:720`) is UNCHANGED — still stale,
still out of scope for this fix, and still a loose end for a future pass.

## Verification
`python3 -m py_compile ignite/team-kit/ready.py` clean. `python3 -B ignite/team-kit/coord.py
selftest` from `ignite/team-kit` — `selftest: PASS (0 failure(s))`. Deployed: no (worktree only,
`5-workbench/rbtv-redesign`, branch `ignite/core-redesign`).

## ATTENTION
1. `attest-exit`'s closing hint (`ignite/team-kit/attest.py:720`, in the exit-attest report block)
   still hands out the full runnable `` `... rule-disposition <seat> done --go` `` line — it is the
   sibling loose end named in the parent deletion entry's ATTENTION #2 and was deliberately left
   alone here (out of this fix's scope, a different file), not missed.
2. No replacement ruling instrument exists anywhere in the tree — this is a real operational gap
   per [T1-R9], not a documentation nit; do not treat this fix as closing that gap, only as
   correcting one more stale pointer to the deleted one.
- attest.py:720's closing hint still names the deleted verb; deliberately unfixed here
- no replacement ruling instrument exists yet — a real operational gap, not a doc nit
