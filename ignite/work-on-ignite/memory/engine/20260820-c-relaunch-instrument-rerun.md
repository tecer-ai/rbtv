# 20260820-c-relaunch-instrument-rerun — Relaunch instrument rerun

kind: creation
component: engine
date: 2026-08-20
commit: e3fc940f
deployed: yes
pin: engine/probes/probe-reconcile.js (D42 arms); engine/probes/probe-enqueue-record.js Arm E; team-kit/probes/probe-checkout-disposition.py
components: team-kit
seeded: true

## What it is
The `--rerun` relaunch instrument, an anchored HOLD, and a `--hold` verb.

`reconcile.js` + `coord.py` (862-line coord.py diff) add the `--rerun` relaunch instrument — the crashed-row door — plus an anchored HOLD state and a `--hold` verb, and correct F-3's wording (D42).

## Why
D42: needed an explicit, owner-invokable re-run door before cutting over to daemon relaunch.

`fix-inventory.csv` D42 — before any lane could cut over to daemon-driven relaunch, there needed to be an explicit, owner-invokable instrument for re-running a crashed row rather than only automatic mechanical retry.

## How to use & where wired
`coord.py --rerun <row>` re-runs a crashed row; `--hold` anchors a row against the watcher.

`coord.py --rerun <row>` re-runs a crashed row through the launch door; `--hold` anchors a row so the watcher won't touch it.

## commit
e3fc940f

## deployed
yes

## pin
engine/probes/probe-reconcile.js (D42 arms); engine/probes/probe-enqueue-record.js Arm E; team-kit/probes/probe-checkout-disposition.py

## ATTENTION
- `--rerun` here is the CONSOLE-era door — the `lane-aware-launch-doors` entry (server, 2026-08-23) found this exact door (along with `--declare-only`/`--reopen`) was lane-blind and cage-blind, a tmux composer that broke on daemon-lane goals. Check that entry before assuming this is still how `--rerun` behaves.
- `--hold` anchors a row against the watcher; verify a held row is excluded from the `watcher-retry-policy` counters, or a hold can be silently overridden by mechanical relaunch.
- console-era door; lane-aware-launch-doors (server, 08-23) found it lane-blind and cage-blind, check that entry first
- --hold must be excluded from watcher-retry-policy counters or a hold can be overridden
