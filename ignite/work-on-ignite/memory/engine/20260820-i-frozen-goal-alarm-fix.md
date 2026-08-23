# 20260820-i-frozen-goal-alarm-fix — Frozen goal alarm fix

kind: issue
component: engine
date: 2026-08-20
commit: 079e08ec,0c07b144,fc34fb16,f45c3887,0c39fdfb,005c3c0c
deployed: yes
pin: engine/probes/probe-frozen-frontier.js + probe-verdict-vocabulary.js + server/ticker/probes/probe-reserved-interactive-slot.js
components: server
seeded: true

## Seen
Frozen-goal alarm's own guard predicate was inverted and miscounted dead branches.

The frozen-goal owner alarm (`server/ticker/goal-stall-alarm.js` reads engine seeding state) was firing wrong. Per the redesign-plan-seed digest §4: "the ready-seats alarm fixed, then found still wrong: 0c07b144/079e08ec shipped a frozen-goal alarm 2026-08-19; the guard's own predicate (readyRows.length vs ready.size) was wrong and stayed silent through 5 more freezes before dead-branch-mode-guards-2026-08-19.md found the ALSO-wrong 'counts dead mode-variant rows as pending.'"

## Missed
Fixed three times before it held; each patch passed its own narrow test.

`079e08ec` (frozen-goal owner alarm reaches pre-seeding branches, LE-13/LE-10) and `0c07b144` (lane-reach admission + goal-live check, D5/D9) shipped a guard comparing the wrong collection sizes — silently wrong through 5 more freeze incidents (`dead-branch-mode-guards-2026-08-19.md`). `fc34fb16` tried again ("frozen-frontier guard tests filtered READY size, not raw row count") and still didn't close it: `f45c3887` immediately follows, finding the guard ALSO counted unsatisfiable mode-variant branches as pending (D22). `0c39fdfb` had to add a `dead` state to ready-seats in coord.py so seeding.js could tell a dead branch from a pending one. Even after that, `005c3c0c` found the guard's core comparison was inverted (D25) and added a reserved-owner interactive slot (cap 14+1) as a companion fix.

## Held
Derive a `dead` state for unsatisfiable branches; fix the inverted comparison; reserve an owner slot.

The frozen-frontier guard now (a) derives an explicit `dead` state for mode-variant branches unsatisfiable at seeding (coord.py ready-seats), (b) compares the correct ready-set sizes (not inverted), and (c) reserves one interactive slot so the owner is never starved out by the cap. Verdict vocabulary was also tightened (probe-verdict-vocabulary.js) and dispatch.js/ticker.js adjusted to match.

## commit
079e08ec,0c07b144,fc34fb16,f45c3887,0c39fdfb,005c3c0c

## files
ignite/engine/seeding.js; ignite/engine/attached-execution.js; ignite/engine/lane-watch.js; ignite/engine/cage-admission.js; ignite/team-kit/coord.py (ready-seats `dead` state); ignite/server/ticker/goal-stall-alarm.js; ignite/server/ticker/ticker.js; ignite/server/internal-api/dispatch.js; ignite/engine/probes/probe-frozen-frontier.js; ignite/engine/probes/probe-verdict-vocabulary.js; ignite/server/ticker/probes/probe-reserved-interactive-slot.js

## deployed
yes

## pin
engine/probes/probe-frozen-frontier.js + probe-verdict-vocabulary.js + server/ticker/probes/probe-reserved-interactive-slot.js (all scheduled)

## ATTENTION
- This alarm was patched 3 times before it actually held — each earlier patch passed its own narrow test while the inverted comparison and dead-branch miscount stayed live. Any future change to seeding.js's ready/frozen logic should run ALL THREE pinning probes together, not just the one nearest the edited line.
- Root cause per dead-branch-mode-guards-2026-08-19.md: a guard whose failure mode (silently wrong) was indistinguishable from its meaningful value (silently fine) — the same class flagged generally in redesign-plan-seed#3 theme 6.
- patched 3 times before it held; run all three pinning probes together on any future seeding.js change
- root cause: a guard whose silent-wrong failure mode was indistinguishable from silent-fine
