# 20260831-i-pass-open-gate-counted-a-chair — pass-open gate counted a chair's open row as a running pass

kind: issue
component: operator
date: 2026-08-31
commit: 6da3e3b0c03957dd41a2523672b7de7220feeb7c
deployed: no
pin: operator/goals-tree/tool/goal_cli.py#selftest (pass-open arms)
register-id: redesign-continue-1#81

## Observed

`goal_cli.py`'s `_retry_write_gate` (backing `rbtv-goal retry-threshold … --set`) and the
`add-seat` GATE (b) quiescence check both refused whenever ANY row in a goal's
`executions.csv` carried an empty `outcome` — never asking whose row it was. The stools
goal-master (a Slack door, launched per owner turn) opens exactly such a row per turn, so
"the owner is talking" read as "a planning pass is running": the same goal refused a
`--set` on 2026-08-22 and passed the identical call on 2026-08-23 with no code change —
intermittent purely on whether a Slack exchange happened to be mid-turn. Triaged
2026-08-23 from `redesign-plan/loose-ends.md:303`; raised by the goal-master itself.

## Mechanism

`_retry_write_gate` built `open_rows` from `read_executions(goal_dir)` filtered only on
`not (r.get("outcome") or "").strip()` — no seat-identity test at all. `add-seat`'s GATE
(b) additionally intersected against `seat_states()`'s `still_open` set (the seat's LAST
row), but that refinement answers "is this seat's run still going", never "is this seat a
planning-workflow seat". `goal_cli.py` carried no staff/summoned-seat vocabulary of its
own (0 grep hits) to make that second distinction.

## Attempts

First attempt held — checked: `redesign-plan/loose-ends.md:303` (the original triage,
which named the fix but was never built), and `coord/identity.py`'s own history
(`CONVERSATIONAL_CHAIRS`, commit `1dd5d907` and siblings) for the D24 exclusion this fix
reuses. No prior code change in `goal_cli.py` touched this gate's seat-identity blindness.

## Fix

Added `_coord_is_conversational_chair()` (lazy `sys.path` import of `coord/identity.py`,
mirroring the pattern `operator/bindings/tool/bindings.py#_coord_validate_seat` already
uses for the same reason: reuse the ONE predicate rather than re-implement it) and
`planning_pass_open_rows(rows)`, a single filter that excludes any row whose seat is in
`CONVERSATIONAL_CHAIRS` (`SUMMONED_SEATS` + `STAFF_SEATS` — goal-master, leader). Both
`_retry_write_gate` and `add-seat` GATE (b) now call this one helper instead of each
re-deriving "open" from `executions.csv` on its own. Rejected: hardcoding
`("goal-master", "leader")` locally — that mints a second seat-vocabulary list `coord`
already owns and would drift from `SUMMONED_SEATS`/`STAFF_SEATS` the way the seed
explicitly warned against (D24 forbids widening either source; a third copy is the same
hazard from a different angle).

## Consequences

No deletions; the fix is additive (one shared helper, two call-site swaps). Nothing else
read the old unfiltered `open_rows` shape. `consultant` was NOT added to the exclusion —
that role is deleted (T2-R17) and staying out of `CONVERSATIONAL_CHAIRS` is coord's own
invariant, not something this change should override.

## Verification

`goal_cli.py selftest` — 4 new arms: `--set`/`add-seat` succeed while goal-master alone
has an open row, succeed while leader alone has an open row, and a genuine
planning-workflow seat's open row still refuses `pass-open`/`goal-not-quiescent` even
alongside an open goal-master row. Red-first: reverting only the two gate call-sites (kept
the helper and the new selftest arms) in a scratch copy of the tree made exactly those 4
arms fail and no others; restoring made all pass. Not yet deployed — lands with this
commit, `READY-TO-DEPLOY` in the closing report.

## ATTENTION

- The exclusion lives in exactly ONE place (`planning_pass_open_rows`) — a future gate
  that wants "is a planning pass running" must call it, never re-filter `executions.csv`
  by hand, or the goal-master-blocks-writes defect returns under a new gate.
- `CONVERSATIONAL_CHAIRS` is imported, never copied. If `coord/identity.py` ever moves or
  renames it, `_coord_is_conversational_chair()`'s import failure raises a `Refusal`
  rather than silently reusing a stale local list — that refusal is the signal to fix the
  import path, not to hardcode the names here.
- `consultant` is deleted and must not be reintroduced into any chair exclusion.
