# 20260819-c-record-ledger-custody — record-ledger-custody

kind: change
component: team-kit
date: 2026-08-19
commit: e56d8704,85f0a30a
deployed: yes
pin: NONE
seeded: true

## What it is
Ledger-write custody change: seats write their own `sessions.csv` row at checkout; the `kit-for-seat` proxy that used to write on a seat's behalf is retired — kit now only originates the `exited` row (when a seat's process dies before it can check out itself).

## Why
Custody was split ambiguously between the seat and the kit, which is exactly the kind of dead-process-but-row-not-yet-closed lag that later produced the staff-wake mis-binding defect (see the `staff-wake-mint-mismatch` entry, same component). Making the seat the sole writer of its own checkout row removes one of the two writers racing on the same ledger.

## How to use & where wired
`ignite/team-kit/coord.py` — the checkout path now writes `sessions.csv` directly from the seat's own process; `ignite/CLAUDE.md` documents the custody rule inline (commit `e56d8704`, "ledger custody — seats write checkout; kit originates exited only"). Commit `85f0a30a` ("seats write sessions.csv at checkout; retire kit-for-seat proxy") is the larger companion change (net -589/+213 lines across `coord.py`, `jobs/goal-watcher-job.py`, `team-kit/probes/probe-checkout-disposition.py`) that actually retires the kit-for-seat proxy path.

## commit
e56d8704,85f0a30a

## deployed
yes

## pin
NONE

## ATTENTION
- This narrows the dead-process-row-not-closed window that caused the 2026-08-19 staff-wake mis-binding (see `staff-wake-mint-mismatch`) but does not eliminate it — the kit still originates `exited` rows for seats that die before checkout.
- `probe-checkout-disposition.py` was touched in the same commit (`85f0a30a`) — re-check it if this custody boundary moves again.
- Narrows but does not eliminate the dead-process-row-not-closed window behind staff-wake-mint-mismatch
- probe-checkout-disposition.py touched in 85f0a30a; recheck if custody boundary moves
