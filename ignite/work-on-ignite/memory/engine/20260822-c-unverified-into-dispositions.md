# 20260822-c-unverified-into-dispositions — Unverified into dispositions

kind: change
component: engine
date: 2026-08-22
commit: 23578584,0afe6f88,c666cb9b,243f3aa1,acd38230
deployed: yes
pin: NONE
seeded: true

## What it is
D81 audit cleanup: five small commits — enum move, fixture alignment, dead re-exports, stale docs.

Five small D81 audit-cleanup commits: `23578584` moves `unverified` (the D32 disposition) into the formal RECORD_DISPOSITIONS enum instead of an ad-hoc list; `0afe6f88` aligns SESSIONS_HEADER test fixtures with the D42 hold-anchor; `c666cb9b` drops unused re-exports from index.js/run-board.js/substrate.js; `243f3aa1` fixes stale probe-count denominators and a deleted-probe citation in docs; `acd38230` fixes coord.py's sweep_lifecycle/clear_lifecycle docstrings' incorrect close-run claim.

## Why
D81: wave-2 code audit confirmed findings; hygiene cleanup, no behavior change beyond the enum move.

`redesign-plan/decisions.md#D81` — the wave-2 code audit (redesign-plan-seed digest §1, orchestrate2.sh) found these as confirmed findings; audit hygiene cleanup, no behavior change beyond the `unverified` enum move.

## How to use & where wired
RECORD_DISPOSITIONS is now the single source of truth for disposition strings.

RECORD_DISPOSITIONS in reconcile.js is now the single source of truth for disposition values including `unverified` — any code checking disposition strings against an ad-hoc list should use this enum instead.

## commit
23578584,0afe6f88,c666cb9b,243f3aa1,acd38230

## deployed
yes

## pin
NONE

## ATTENTION
- `unverified` (D32/D33) has now moved location twice (introduced by the `verified-done-resolver` entry, formalized here) — grep for the STRING "unverified" rather than assuming it lives in one place if auditing disposition handling again.
- This is a batch of five otherwise-unrelated one-line fixes bundled under one audit ruling (D81) — if any single one needs reverting, check it doesn't share the commit with others before reverting a whole commit.
- unverified enum has moved twice; grep the string rather than assuming one location
- five unrelated fixes share one commit batch; check before reverting any single one
