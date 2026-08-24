# 20260824-c-delete-team-monitor-cli-and-te — delete team-monitor CLI and teamview [T4-R8]

kind: change
component: team-kit
date: 2026-08-24
commit: 549a0f8b
deployed: no
pin: NONE
components: orchestration,capabilities

## Motivation
Design-baseline v2 [T4-R8, C-15, C6] settles "is it alive" on the supervisor registry alone — a
terminal pane is a viewport, never a heartbeat, and a standalone monitor process is superseded.
This is the third of the four D19 observer deletions this seat (del-observers) performs; the
orchestrator also added `orchestration/teamview/` to scope (owner ruling 2026-08-24) since it only
ever rendered team-monitor's snapshot and has no independent data source.

## Design
Delete the whole `orchestration/team-monitor/` component tree (`team_monitor.py`, `ctx_monitor.py`,
`component.md`, `exposure.csv`, tool docs) and `orchestration/teamview/` (`teamview.py`,
`component.md`, `exposure.csv`, README). In `ignite/team-kit/coord.py`: delete
`team_monitor_holder`, `team_monitor_last_seen`, `ensure_team_monitor`, `append_sensor_event` and
`render_monitor_report` (the last two existed only to serve `ensure_team_monitor`'s reporting).
KEPT `load_state_snapshot` — its two other callers (`state_agent_types`, a refusal path in
`attest_exit_blockers`) already treat a missing snapshot as their ordinary fail-safe direction, so
deleting it too would just mean re-deriving the same `state.json` parse a second time. The
`launch` command's only call site (`ensure_team_monitor(args, session=...)` + its report print)
was deleted outright — it only started the sensor, so per the ruling nothing replaces it.

## How it works
Every room now reads the census (`state.json`) as permanently absent — nothing writes it any
more. The existing "cold-start admission" logic (7.406, in `coord.py`'s launch-gates capacity
term) already treats an absent/unreadable census as a valid, handled state (it used to only fire
on a virgin package that had never had a sensor run against it); it now fires on every room,
unchanged in its own logic. The `CAP UNENFORCEABLE` pickup-lane message that used to say "restore
the census (`team_monitor.py once --package {pkg}`)" now says the census sensor is retired with no
replacement built yet — pointing an operator at a deleted binary would have been worse than saying
nothing.

## Consequences
Deleted probes whose entire subject was the deleted sensor: `team-kit/probes/probe-sensor-cold-
boot.py`, `probe-7555-window-session.py` (both named in the seat's brief), plus three more found
by the same root cause — `probe-g158-stale-code.py` (asserted `team_monitor.cmd_run`'s staleness
detector), `probe-hollow-room-relaunch.py` and `probe-one-room-relaunch-ladder.py` (both asserted
`team_monitor.relaunch_room`'s bounded-relaunch ladder — the surviving hollow-room-recovery path is
`jobs/recover-room.py`, shelled directly by `engine/reconcile.js`'s `strike()`, untouched), and
`acceptance-room.py` (an unimported Stage 4 acceptance substrate whose own docstring already said
"deleting it breaks nothing" — its whole premise was a `state.json` produced by a real
`team_monitor.py capture`). `jobs/probes/probe-team-monitor-{activity-fallback,approval-title,
homings}.py` were named directly in the seat's brief and deleted too.
`probe-finish-edge.py` survives — F1-F6 test coord's own finish-edge logic — but its F7 arm (a
byte-for-byte cross-check against `team_monitor.py`'s copy of `FINISH_MARKER`) is deleted; that
constant now has only coord's own copy.

Docs-in-sync touched: root `CLAUDE.md`'s CLI-placement example, `ignite/team-kit/CLAUDE.md`'s
selftest instruction (used to tell an agent to run a now-deleted binary's `selftest` verb),
`daemon-operator`'s `--help` text, `starter-set/budget.json`'s `_tmp_free_warn_scope` doc field
(named the deleted `team_monitor.tmp_canary_write` as the binding probe for `box.tmp_quota`, which
no longer exists), and `orchestration/module.md` (rewritten — the module now hosts only the
unplaced `hooks/` folder, a separate matter pending owner ruling, untouched).

## Verification
`python3 -c "compile(...)"` on every touched `.py` file. `python3 coord.py selftest` from
`ignite/team-kit/` — PASS (0 failures) after two follow-up fixes the selftest itself caught: a
policy-number digit (`T4-R8`) landing inside a string a "contains no digit at all" assertion reads
(7.363 CRITERION 7), and two literal-string checks (`"PICKUP LANE: restore the census"`) against
the pickup-lane message I'd already reworded. `python3 probe-finish-edge.py` and 13 other
`team-kit`/`jobs` baseline probes run directly — all PASS. Deployed: no (worktree only,
`5-workbench/rbtv-redesign`, branch ignite/core-redesign; live repo untouched).

## ATTENTION
1. `coord.py`'s own selftest is the ONLY thing that caught the digit-in-a-no-digit-assertion
   regression and the two stale literal-string checks — a syntax check alone would have shipped
   both. Always run `python3 coord.py selftest` after any edit near the capacity/census messages,
   not just `compile()`.
2. `state.json`/census-derived fields (`ctx_refresh`'s old "consumed by team_monitor.py" claim,
   `counting._rule`'s "team-monitor is the room's only raw sensor" in `starter-set/budget.json`,
   and similar prose in `roles.md`/`budget.py`/`system-design.md`/`materialize-seats.py`) were
   NOT swept — only the load-bearing/functional references this seat's DoD grep targeted were
   fixed. A future reader should not assume every "team-monitor" mention in the tree is current;
   many are now-stale historical prose left as a disclosed loose end.
3. `orchestration/` has no live components left after this — only `hooks/` (unplaced, pending
   owner ruling, untouched by this seat). A future seat placing a new orchestration component
   should not assume `team-monitor`/`teamview`'s old conventions (CMP-20/CMP-24 registry records)
   still describe anything live.
