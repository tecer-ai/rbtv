# 20260819-i-honour-goal-pause-in-reconcile — Honour goal pause in reconcile

kind: issue
component: engine
date: 2026-08-19
commit: 2058b965
deployed: yes
pin: engine/probes/probe-reconcile.js
seeded: true

## Seen
reconcile.js's watcher ignored `rbtv goal pause`, kept acting on paused goals.

`reconcile.js`'s mechanical watcher loop kept acting (relaunching/escalating) on goals the owner had explicitly paused via `rbtv goal pause` — the pause command's intent wasn't read by the newly-built reconcile loop.

## Missed
none recorded in sources.

## Held
lane-watch.js and reconcile.js now check goal-pause state before acting.

`lane-watch.js` and `reconcile.js` now check goal-pause state before acting; `reconcile.selftest.js` gained 67 lines of arms covering a paused goal.

## commit
2058b965

## files
ignite/engine/lane-watch.js; ignite/engine/reconcile.js; ignite/engine/probes/probe-reconcile.js; ignite/engine/reconcile.selftest.js

## deployed
yes

## pin
engine/probes/probe-reconcile.js

## ATTENTION
- This is exactly the mechanism this program's own coordinating goal (`ignite-engine`) now depends on to stay inert while paused (`rbtv goal pause ignite-engine`, per this program's read-first.md) — do not weaken this check, or a paused goal would resume being acted on by the watcher.
- ignite-engine's own pause relies on this check; do not weaken it
