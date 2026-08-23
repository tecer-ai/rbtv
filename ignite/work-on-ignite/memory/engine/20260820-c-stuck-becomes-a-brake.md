# 20260820-c-stuck-becomes-a-brake — Stuck becomes a brake

kind: creation
component: engine
date: 2026-08-20
commit: 23de241f
deployed: yes
pin: engine/probes/probe-reconcile.js (D44 arms, many)
seeded: true

## What it is
`stuck` becomes a hard brake keyed on (seat, reason, signature).

`reconcile.js`'s `stuck` state (already used as an end-state marker) is upgraded to a hard brake: once emitted for a given (seat, reason, signature) tuple, mechanical relaunch permanently stops for that exact signature — clearable only by an explicit act. Same commit ships D43 (paneless launch identity).

## Why
D44: without a brake, an unchanged-signature stuck row could still be mechanically relaunched.

`fix-inventory.csv` D44 — without a brake, a stuck row with an unchanged reason/signature could still be relaunched by mechanical policy on the next tick, burning tokens on a failure mode already known not to resolve itself (redesign-plan-seed#3 theme 4 / dead-sittings-diagnosis-2026-08-21.md).

## How to use & where wired
reconcile.js checks the (seat,reason,signature) triple before mechanical relaunch.

`reconcile.js` checks the (seat, reason, signature) triple before mechanical relaunch; coord.py's launch identity corroboration (D43, same commit) ensures the signature check can't be spoofed by a paneless/caged seat claiming another chair's identity.

## commit
23de241f

## deployed
yes

## pin
engine/probes/probe-reconcile.js (D44 arms, many)

## ATTENTION
- The brake keys on the EXACT (seat, reason, signature) triple — if a later fix changes how "reason" or "signature" is computed/formatted, existing brakes silently stop matching and mechanical relaunch resumes on rows that were meant to stay braked.
- This is the terminal state for the retry loop built across `verified-done-resolver`/`watcher-retry-policy`/`cleared-row-relaunch` — read all together before changing reconcile.js's state-transition logic.
- brake keys on the exact (seat,reason,signature) triple; a format change silently unmatches it
- terminal state of the retry loop; read with verified-done-resolver, watcher-retry-policy, cleared-row-relaunch
