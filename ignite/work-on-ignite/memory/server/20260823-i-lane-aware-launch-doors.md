# 20260823-i-lane-aware-launch-doors — Lane aware launch doors

kind: issue
component: server
date: 2026-08-23
commit: a554197b
deployed: yes
pin: NONE (unproven at deploy)
components: team-kit
seeded: true

## Seen
Leader launch doors were console-era tmux composers, lane-blind and cage-blind.

The leader's launch doors (`--rerun` built in the `relaunch-instrument-rerun` entry, `--declare-only`, `--reopen`) were console-era: they composed and fired an uncaged tmux pane directly, regardless of which lane (console vs daemon) the goal was actually running on.

## Missed
A crashed seat on a daemon-lane goal parked the owner back on a console pane.

Per `engine-goal/decisions.md#E21`, a crashed seat needing `--rerun` on a daemon-lane goal parked the owner back on a console pane to fire it manually — the exact failure this fix closes. This was this program's own trigger: the day before this fix, a dedicated investignosis pass (6 investigator outputs + diagnosis) named the root cause as "lane-blind leader launch doors" (E21).

## Held
On a daemon-lane goal, the doors enqueue a caged headless sitting via the daemon instead.

On a daemon-lane goal, `--rerun`/`--declare-only`/`--reopen` now enqueue a caged, briefed headless sitting via the daemon's gateway (`gateway enqueue-job`) instead of composing an uncaged tmux pane; `ticker.js` composes the boot prompt at dispatch time for this prompt-less daemon-lane seat; `gateway_client.py` reads the sender token from `.rbtv/config/sender-token.env`.

## commit
a554197b

## files
ignite/team-kit/coord.py; ignite/server/ticker/ticker.js; ignite/server/ticker/probes/probe-boot-prompt-fallback.js; ignite/team-kit/gateway_client.py; ignite/team-kit/protocol.md

## deployed
yes

## pin
NONE (unproven at deploy — first real caged-leader firing not yet observed)

## ATTENTION
- This fix is UNPROVEN IN PRODUCTION as filed — no pin exists yet because the first real caged-leader firing hadn't happened at deploy time. Check whether that first live firing has since occurred before building further on this path.
- This directly supersedes `relaunch-instrument-rerun`'s `--rerun` door (built console-era) — do not revert to that shape; the whole point of this fix is that the console-era door was lane-blind.
- The `ignite-engine` goal this fix serves was PAUSED the same window specifically because of this launch-door class of defect — check whether the goal has since been un-paused/rewired before assuming this is still the live behavior.
- unproven in production as filed; check if the first live caged-leader firing has occurred
- supersedes the console-era --rerun door; do not revert to that shape
- ignite-engine goal was paused the same window over this defect class
