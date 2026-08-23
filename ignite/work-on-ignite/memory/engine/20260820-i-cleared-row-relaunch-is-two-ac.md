# 20260820-i-cleared-row-relaunch-is-two-ac — Cleared row relaunch is two acts

kind: issue
component: engine
date: 2026-08-20
commit: feba5fba,d813ebcc
deployed: yes
pin: engine/probes/probe-reconcile.js (D39 arms)
components: team-kit
seeded: true

## Seen
A CLEAR verb was treated as if it also re-seeded/relaunched the row.

A CLEAR verb on a stuck/dead row was being treated as if it also re-seeded/relaunched the row automatically — collapsing "clear the row" and "relaunch it" into one act, so a cleared row could silently come back through seeding instead of an explicit leader decision.

## Missed
none recorded in sources.

## Held
Split CLEAR (coord.py) from relaunch (leader, explicit) — two acts, not one.

`feba5fba` (fix(coord): a CLEAR does not re-seed — the leader relaunches it, D39) splits the two acts: coord.py's CLEAR verb only clears; the leader must separately, explicitly relaunch. `d813ebcc`'s reconcile.js companion tells the leader clearing and relaunching are two acts and stops the retry counter resetting on a bare clear.

## commit
feba5fba,d813ebcc

## files
ignite/team-kit/coord.py; ignite/engine/reconcile.js

## deployed
yes

## pin
engine/probes/probe-reconcile.js (D39 arms)

## ATTENTION
- Do not re-merge CLEAR and relaunch into one verb — that was the exact defect. Any convenience wrapper that auto-relaunches after a clear reopens D39.
- Shares commits with `verified-done-resolver` and `watcher-retry-policy` — this is the same D39/D40 landing referenced by all three; read them together before touching reconcile.js's retry/clear logic.
- do not re-merge CLEAR and relaunch into one verb, that was the defect
- shares commits with verified-done-resolver and watcher-retry-policy, read together
