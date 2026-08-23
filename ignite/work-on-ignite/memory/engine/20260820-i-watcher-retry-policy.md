# 20260820-i-watcher-retry-policy — Watcher retry policy

kind: issue
component: engine
date: 2026-08-20
commit: d813ebcc,2233233a,23de241f,d813146d
deployed: yes
pin: engine/probes/probe-reconcile.js (D34/D40 arms)
seeded: true

## Seen
The retry counter reset on every launch attempt instead of on progress.

`reconcile.js`'s mechanical relaunch loop (built in the `selfheal-to-reconcile` creation) had a retry counter that reset on every launch attempt rather than on actual progress, so a seat stuck in a no-progress loop could be relaunched indefinitely without ever tripping the bound.

## Missed
D15's 3-attempt bound counted launches, not progress; amended to 2 by D34.

`system-problems.md#5` records this was wrong on two axes: the count needed lowering from 3 to 2 (D34), and — more importantly — it needed to count NO PROGRESS, not "a launch happened," because a seat can launch successfully every time and still make zero progress. `d813ebcc` (D39/D40) first stopped the counter resetting on a bare re-clear; `2233233a` (D33a/D34/D35) then split "class A" no-progress detection by word and made the counter measure progress directly, replacing the numeric mail cursor (see the `unread-mail-cursor` entry).

## Held
Count consecutive no-progress launches, bounded at 2, before the row goes `stuck`.

`23de241f` + `2233233a` together: the watcher counts consecutive NO-PROGRESS launches (not launch attempts), reset only when real progress is observed, bounded at 2 before the row becomes `stuck`. `d813146d` records the landing in status.md as "the D39/D40 reconcile landing and the in-flight coord.py follow-up."

## commit
d813ebcc,2233233a,23de241f,d813146d

## files
ignite/engine/reconcile.js; ignite/engine/reconcile.selftest.js (D34/D40 arms)

## deployed
yes

## pin
engine/probes/probe-reconcile.js (D34/D40 arms)

## ATTENTION
- The fix-inventory explicitly flags this as a two-step amendment (D15→D34): any code or docs still citing "3 mechanical attempts" are citing the SUPERSEDED value — the live bound is 2, counted on no-progress.
- This retry bound is shared machinery with `verified-done-resolver` and `stuck-becomes-brake` — the three form one loop; changing the count here changes when `stuck` fires.
- D15's 3-attempt bound is SUPERSEDED; live bound is 2, counted on no-progress
- shared machinery with verified-done-resolver and stuck-becomes-brake
