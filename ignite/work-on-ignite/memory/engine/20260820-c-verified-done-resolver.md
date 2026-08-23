# 20260820-c-verified-done-resolver — Verified done resolver

kind: creation
component: engine
date: 2026-08-20
commit: feba5fba,d813ebcc,3a112282
deployed: yes
pin: engine/probes/probe-reconcile.js; team-kit/probes/probe-checkout-disposition.py
components: team-kit
seeded: true

## What it is
Resolver: watcher relaunches a seat-declared-incomplete row by name, bounded, then stuck.

`reconcile.js` gains a resolver path for seats that checked out `incomplete`/`unverified` — the watcher relaunches them by name up to the retry-policy bound (see the `watcher-retry-policy` entry), then marks the row `stuck` (see `stuck-becomes-brake`). `coord.py`'s rule-disposition now admits four legal from-states (D32/D33(b)), and coord.py gains a third ending state `unverified`, replacing the old incomplete/exited overload.

## Why
D32/D33: incomplete/done/exited were overloaded state words with no resolver path.

`fix-inventory.csv` D32/D33 — "incomplete"/"done"/"exited" were overloaded state words (redesign-plan-seed#3 theme 1); a resolver was needed so the watcher could act on a seat-declared-incomplete row instead of leaving it stranded, bounded to a fixed number of mechanical retries. `feba5fba` ("a CLEAR does not re-seed — the leader relaunches it", D39) lands in the same window and threads into this same area.

## How to use & where wired
reconcile.js checks disposition via coord.py, relaunches by name up to the retry bound.

`reconcile.js`'s watcher loop checks disposition via coord.py's rule-disposition, relaunches unverified/incomplete rows by name, and stops at the retry bound.

## commit
feba5fba,d813ebcc,3a112282

## deployed
yes

## pin
engine/probes/probe-reconcile.js; team-kit/probes/probe-checkout-disposition.py

## ATTENTION
- D5 → D32 (`incomplete`/`exited` amended to `unverified`) touches probe files that were touched AGAIN by D81 later (`unverified-into-dispositions`) — read both before changing disposition vocabulary again.
- This resolver's retry bound is the SAME counter fixed in `watcher-retry-policy` — don't tune one without checking the other.
- D32 unverified vocabulary was touched again by D81 later; read both before changing disposition words
- shares its retry bound with watcher-retry-policy; don't tune one without the other
