# 20260902-i-fail-status-discharge-halted-c — fail-status discharge: HALTED clears after later PASS

kind: issue
component: coord
date: 2026-09-02
commit: 128987cc1f1ad35da2fbe97688e3f150dfacf94d
deployed: yes
pin: ignite/coord/coord_selftest.py
components: meta-planning

## Observed
`coordinate fail-status <milestone>` reported a milestone's `escalated` flag as a raw, append-only
fact (an escalation row ever existed for it) and the two planning prompts that gate on it
(`unblock-checker.md`, `check-unblocked.md` under `meta/planning/`) both queued nothing once
`escalated` OR `at_bar` was true — permanently, because `escalated` never went false again even
after a later trial verdict PASSed the same milestone. A milestone that was escalated, then fixed and
re-judged PASS, stayed HALTED forever: no future pass could ever queue against it again. Task 24.

## Mechanism
`cmd_fail_status` computed `escalated` as `escalation_row(base, milestone) is not None` — true the
moment any escalation row for the milestone ever existed on the append-only message log, with no
mechanism to un-set it. A later PASS trial verdict zeroed the TRAILING-FAIL count (so `at_bar` could
go false again), but nothing ever cleared the escalation row itself or read whether a newer verdict
had superseded it. The two consuming prompts gated queueing on `at_bar OR escalated`, so once
`escalated` first went true, that OR-clause stayed true across every future call regardless of what
happened afterward — the append-only escalation history was being read as the live gate, when the
live gate needed to be "is there a newer PASS since the escalation."

## Attempts
First attempt at this problem — checked: `git log -- ignite/coord/messages.py` around
`escalation_row`/`cmd_fail_status` and the two planning prompts; no earlier attempt to distinguish
raw escalation history from a live halt state was found.

## Fix
Added `escalation_discharged(base, milestone_id)` (`messages.py`): true when an escalation row exists
AND a later `verdict` message for the same milestone (by the log's own monotonic `num`, allocated
under `coord_lock`, never a timestamp) reads PASS. `cmd_fail_status` now computes a derived `halted`
field — `at_bar OR (escalated AND NOT discharged)` — alongside the raw, unchanged `escalated` history,
and both the text and `--json` output print/gate off `halted`, never the raw flag. The two source
prompts (`unblock-checker.md`, `check-unblocked.md`) were repointed to read `halted` as the SOLE gate
(never re-deriving it from `at_bar`/`escalated` themselves — that would be a second authority
disagreeing with the one that enforces the halt), with `escalated` documented as raw history that a
discharged milestone still carries as true. This closes the gap at the producer (`fail-status`) and
both known consumers in the same commit, rather than patching each prompt's own OR-logic separately.

## Consequences
No caller loses information: `escalated` is unchanged (still permanent, at-most-once history) and a
new `discharged` field states explicitly why `halted` differs from it. A discharged milestone can now
queue its next planning pass again — the defect this fix closes. The two prompts' done-criteria and
outcome-map sections were also updated to state the gate is `halted` alone, with the discharge case
(escalated-but-now-cleared) explicitly folded into the "queue a gap-fill" branch rather than left
ambiguous. Filing this seat's own honest self-accounting: it also found and fixed one of the suite's
25 pre-existing failures being caused by its own bad check-ordering (a `check()` call whose
continuation-line indentation had drifted), dropping the run's failure count 25->24 — a coincidental,
disclosed fix bundled into the same commit.

## Verification
A new `coord_selftest.py` arm proves the escalate-then-PASS discharge case directly: escalate a
milestone, then land a `verdict ... --pass` for the same milestone, and assert `fail-status` now
reports `escalated: true` (row on disk unchanged) but `discharged: true` and `halted: false`.
Deployed — `ignite/coord/`, `meta/planning/`, branch `ignite/core-daemon`, live on deploy tree
`e8524c31`.

## ATTENTION
1. `halted` is the ONE gate every future consumer of `fail-status` must read — `escalated` alone is
   permanent history and will silently disagree with the true halt state on any milestone that was
   ever escalated and later discharged. A future caller reading `escalated` directly reintroduces
   this exact defect.
2. `escalation_discharged` orders by the log's own monotonic `num`, never a timestamp — two rows can
   share a `now()` second but never a `num`. A future reimplementation that sorts by timestamp instead
   risks misordering an escalation and its discharging PASS.
3. The prompt repoint touched SOURCE files only (`meta/planning/prompts/unblock-checker.md`,
   `meta/planning/tasks/check-unblocked.md`) — a materialized/rendered seat descriptor under
   `.rbtv/goals/…/seat.md` only reflects this change after a descriptor refresh runs.
