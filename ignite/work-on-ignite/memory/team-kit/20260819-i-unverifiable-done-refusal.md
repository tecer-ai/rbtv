# 20260819-i-unverifiable-done-refusal — unverifiable-done-refusal

kind: issue
component: team-kit
date: 2026-08-19
commit: 88f1b361
deployed: yes
pin: team-kit/probes/probe-checkout-disposition.py;reconcile.selftest.js:91
seeded: true

## Seen
A seat could checkout `done` on its say-so alone, with no check that declared outputs existed.

Fix-inventory D5: checkout accepted `done` with no verification of declared outputs.

## Missed
None recorded in sources.

## Held
Checkout refuses an unverifiable `done`; records `incomplete`/outputs-unverified instead.

Commit `88f1b361` ("refuse unverifiable done; record incomplete outputs-unverified (D5)") added ~100 lines of verification logic to the checkout-disposition path. The word `outputs-unverified` was later amended to `unverified` by ruling D32 in the same probe/selftest files — the pin stays valid, it just checks the current word.

## commit
88f1b361

## files
ignite/team-kit/coord.py — checkout disposition path (search `unverified` / `outputs-unverified` in the done-checkout branch)

## deployed
yes

## pin
team-kit/probes/probe-checkout-disposition.py; reconcile.selftest.js:91 (D5 marker, wrapped by probe-reconcile.js)

## ATTENTION
- The wording changed from `outputs-unverified` to `unverified` under D32 — grep for the current word (`unverified`), not the original, when checking whether this gate still fires.
- This is the origin of the "verifiable outputs" doctrine that D24/D29/D30 later carve summoned-chair exemptions into — read those before assuming every checkout path enforces this the same way.
- Wording changed outputs-unverified to unverified under D32; grep the current word
- Origin of the verifiable-outputs doctrine that D24/D29/D30 later exempt summoned chairs from
