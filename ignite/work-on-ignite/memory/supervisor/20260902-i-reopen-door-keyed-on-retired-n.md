# 20260902-i-reopen-door-keyed-on-retired-n — --reopen door keyed on retired, not crashed/exited

kind: issue
component: supervisor
date: 2026-09-02
commit: d2093ebfcdb61b35ab44fb5abb316e72f37afd21
deployed: yes
pin: ignite/supervisor/launch.py (fixture-verified, no dedicated selftest arm)
components: coord

## Observed
`launch.py`'s `--reopen` refusal table (`_ro_door`, inside `cmd_launch`) keys the crash-shaped
from-state on the literal string `exited`. Running `--reopen` against a seat that had actually
crashed (ending `failed` with reason class `crash` or `provider-error`) printed the generic fallback
message `` `{disp}` is not a finished ending and this door does not admit it `` instead of pointing the
caller at `--rerun <leader-anchor>`, the door that actually handles a crashed seat.

## Mechanism
The ending store has refused to WRITE the ending value `exited` at its own write boundary since the
redesign retired that word [T1-R3, T4-R7] — every crash is now persisted as `failed` with a
`reason_class` of `crash` or `provider-error`. `_ro_door`'s dict literal was never updated after that
retirement, so its `"exited": …` key could never match a real row, and Python's `dict.get(..., default)`
silently fell through to the generic message for every crashed seat, with no error raised anywhere to
surface the dead key.

## Attempts
First attempt held — checked: the redesign's own retirement commits [T1-R3, T4-R7] (which changed what
the store writes) did not also sweep this file's refusal table; no earlier fix to `_ro_door` exists in
this plan's history.

## Fix
Read the reason class the same way `--rerun`'s own admission check already does
(`RERUN_ADMITTED_REASON_CLASSES`), and route on `_ro_disp == "failed" and _ro_class in
RERUN_ADMITTED_REASON_CLASSES` BEFORE falling into the dict lookup, rather than adding a second,
independently-maintained `exited`→`failed`/crash rename inside the dict (one classification source,
not two hand-kept tables that could drift apart again). A `failed` ending outside that reason class
(e.g. `outputs-missing`, the accept/reject gate's verdict, not a crash) keeps its own distinct message
inside the dict. Also swept three further dead-`exited` prose spots in the same file's D54/D66 header
comment and the undeclared-ending/deferred-seat detail strings that still asserted `exited` as a live
from-state.

## Consequences
No change to `--rerun`'s own admission logic — this fix reads it, does not duplicate or alter it. No
other caller of `_ro_door` changed. Two further dead-prose `exited` mentions were found OUTSIDE this
file's granted scope and left for their owning seat: `ignite/coord/checkout.py:1517,1564` and
`records.py`'s already-self-labeled-retired `RECORD_DISPOSITION_WRITER` comment block.

## Verification
Verified with a synthetic ending-store fixture (`ENDING_STORE_DB` pointed at a scratch `heart.db`):
pre-fix, `--reopen` on a `failed`/`crash` seat printed the generic fall-through; post-fix it prints the
`--rerun` pointer, and a `failed`/`outputs-missing` seat still gets its own, non-rerun message.
`coord.py selftest` run to confirm only the 24 pre-existing, already-catalogued failures remained, none
touching this door. No dedicated automated selftest arm was added for `_ro_door` itself — verification
was fixture-only. Deployed live on deploy tree `e8524c31` (`ignite/core-daemon`).

## ATTENTION
1. `_ro_door`'s crash-shaped branch must keep reading `RERUN_ADMITTED_REASON_CLASSES` rather than a
   second hand-written set of reason-class strings — a future edit that hardcodes its own list here
   can silently drift from what `--rerun` actually admits, reopening a version of this same bug.
2. `exited` is a RETIRED ending value the store refuses to write — any code elsewhere in
   `ignite/coord/` or `ignite/supervisor/` that still branches on the literal string `"exited"` is
   dead by construction; two such spots (`checkout.py:1517,1564`, `records.py`) were found but left
   unfixed as out of this change's scope.
