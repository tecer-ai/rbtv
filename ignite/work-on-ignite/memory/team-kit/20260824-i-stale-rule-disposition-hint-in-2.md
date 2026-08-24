# 20260824-i-stale-rule-disposition-hint-in-2 — stale rule-disposition hint in attest.py exit-attest

kind: issue
component: team-kit
date: 2026-08-24
commit: 79030314
deployed: no
pin: NONE

## Observed
`ignite/team-kit/attest.py:720`, `cmd_attest_exit`'s closing hint (printed after `--go` attests
one or more seats `exited`), still handed the leader a full runnable
`` `{coord_invocation(args)} rule-disposition <seat> done --go` `` invocation as the way to record
a ruling that the work had in fact concluded. This was the sibling loose end flagged (but
deliberately left unfixed) in `team-kit/20260824-i-stale-rule-disposition-hint-in.md`'s ATTENTION
#1, itself carried forward from `team-kit/20260824-c-delete-rule-disposition-ruled.md`'s ATTENTION
#2 — and, per this task's orchestrator sweep of the whole `ignite/` tree, the LAST remaining
runnable `rule-disposition` hint anywhere in the tree.

## Mechanism
Same root cause as the ready.py sibling: `cmd_rule_disposition` and the CLI verb were deleted
whole under ruling [T2-R12, T1-R9] (commit 7b978663), but this f-string in `attest.py` — a
different file from `coord.py`/`ready.py`, so outside that deletion pass's own file and outside
the cross-component follow-up's (`engine/20260824-c-fix-stale-rule-disposition-ref.md`) remit,
which was scoped to `ignite/engine/` and docs — was never rewritten. It kept building a
`coord_invocation(args) + " rule-disposition <seat> done --go"` string that no longer resolves to
a real verb.

## Attempts
First attempt held — checked `team-kit/20260824-i-stale-rule-disposition-hint-in.md` (the ready.py
fix, commit 26c14aac), whose ATTENTION #1 named this exact line as a known, deliberately-unfixed
sibling; and `engine/20260824-c-fix-stale-rule-disposition-ref.md`, whose remit never reached
`ignite/team-kit/attest.py`. No prior attempt touched this line.

## Fix
Reworded the clause to the same established pattern used at `ready.py:~1578` (this task's
predecessor fix) and `ready.py:~1124`/`cli_main.py:~905`: drop the runnable invocation and state
plainly that `` `rule-disposition` `` was deleted [T2-R12, T1-R9] with no replacement ruling
instrument wired yet. Kept the surrounding f-string mechanics (`{acted}` count guard, the
`coord_invocation(args)` call in the trailing `ready-seats` pointer, which is a SURVIVING verb and
was left alone) and the message's intent (route the leader to investigate, name the terminal
`ready-seats` check) unchanged.

## Consequences
No behavior change (printed hint only, not a control path). Closes the last remaining runnable
`rule-disposition` hint in `ignite/` per the orchestrator's tree-wide sweep — no further loose end
of this specific shape (a live, copy-pasteable dead command) is known to remain.

## Verification
`python3 -m py_compile ignite/team-kit/attest.py` clean. `python3 -B ignite/team-kit/coord.py
selftest` from `ignite/team-kit` — `selftest: PASS (0 failure(s))`. Deployed: no (worktree only,
`5-workbench/rbtv-redesign`, branch `ignite/core-redesign`).

## ATTENTION
1. This closes the pair opened by `team-kit/20260824-i-stale-rule-disposition-hint-in.md` — that
   entry's ATTENTION #1 named this line; there is no longer a known live runnable
   `rule-disposition` invocation anywhere in `ignite/`, per the orchestrator's explicit tree sweep,
   though non-runnable explanatory prose naming the deleted verb remains in several files by
   design (`records.py`, `launch.py`, `ready.py:1124`, `cli_main.py:884,905` — all already state
   the deletion, not a live command).
2. No replacement ruling instrument exists anywhere in the tree — this is a real operational gap
   per [T1-R9], not a documentation nit; this fix only removes one more dead-command pointer to it.
- last remaining runnable rule-disposition invocation in ignite/, per tree-wide sweep
- no replacement ruling instrument exists yet — a real operational gap, not a doc nit
