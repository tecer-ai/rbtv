# 20260901-c-registry-records-at-spawn-not — Registry records at spawn, not check-in (7.555/N2)

kind: creation
component: supervisor
date: 2026-09-01
commit: 8a156a0a
deployed: no
pin: ignite/coord/coord_selftest.py
components: coord

## Motivation
`coord-capacity` (task 101, `a6b946cc`) migrated the tmux-lane capacity census onto the supervisor
registry and closed the stale-census deferral, but left three incident-driven protections red:
`7.555`/D5 (incident G-2335: a live, pre-check-in seat pinned a room in `CAP NOT CONSULTED`
indefinitely), N1 (unaccounted pane) and N2 (cross-goal pane). Each depended on the deleted pane
sensor resolving an unidentified process's raw cwd against `seats/` before it "checked in" — a
question the registry, keyed by `(goal, seat)` from the moment a row is written, cannot ask the
same way. Owner ruling `d-ask10-build-the-replacement`: build the replacement (have the registry
record a session AT SPAWN rather than at check-in) rather than accept the loss or revert the
migration.

## Design
The actual "console-uncaged" chokepoint for a tmux-lane launch is not a bare human-run `claude`
(`doors.js`'s own comment: "nobody witnesses this birth") — it is `launch.py#launch_seat`, which
opens the pane itself and can resolve its pid the instant it exists. `doors.js`/`registry.js`
already had the write-moment machinery (`recordSpawn`/`recordCheckIn`, `superviseSpawn`/
`markUnsupervised`/`registerCheckIn`) fully built since 2026-08-24 — but `markUnsupervised` and
`registerCheckIn` had ZERO production callers (only their own selftest called them). The fix is
wiring, not new mechanism: `launch_seat` calls the registry at spawn, `cmd_checkin` calls it at
check-in, both through a new Python door (`supervisor_door.record_spawn`/`record_checkin`) rather
than a second implementation.

N2's old raw-cwd walk becomes a direct `(goal, seat)` comparison once every row carries both from
birth — no new sensor, just a full-registry scan (`all_liveness()`) instead of the goal-scoped one.
N1 (a live process with NO descriptor anywhere) is a genuine, permanent casualty: a registry row
cannot represent an identity nobody ever wrote, by construction. Closing it without a second
observation source means restoring the deleted pane sensor, which two prior owner rulings bar.
Left red, documented, not faked.

## How it works
`ignite/supervisor/launch.py#launch_seat`: right after the pane opens (`coord.set_pane_title`),
before `coord.wake()` sends the harness command, calls `coord.supervisor_door.record_spawn(pkg,
seat, coord.tmux_pane_pid(pane))` — `supervision` defaults `unsupervised` (this door is not one of
`doors.js`'s WRAPPED six). Loud-and-swallowed on failure, matching `spawn.js`'s own write-moment-(i)
posture.

`ignite/coord/checkout.py#cmd_checkin`: inside the `is_tmux_pane(pane)` branch, calls
`supervisor_door.record_checkin(package_dir(args), args.agent, tmux_pane_pid(pane))` — re-derives
the SAME pane's pid rather than trusting a value carried in, so the flip re-affirms the identity
`record_spawn` already established.

`ignite/coord/supervisor_door.py` gains `record_spawn`/`record_checkin`, thin wrappers over
`supervisor_op("recordSpawn"/"recordCheckIn", ...)` — the same `node supervisor/cli.js` door
`death_stamp`/`confirm_and_reap` already use.

`ignite/coord/liveness.py` gains `all_liveness()` — every registry row across every goal, as a
LIST (never a dict keyed by seat: two goals can declare a same-named seat and a dict would drop
one). `ignite/supervisor/probe.js` gains `probeAll()` and a `--all` CLI flag to answer it.

`ignite/supervisor/launch.py`'s capacity block: D5 needed ZERO changes downstream — once a row
exists at spawn, an alive-but-unsupervised registry row for a declared seat already lands in
`counted` through the ordinary `discover_workers()`-crossed-with-`goal_liveness_strict()` path
`a6b946cc` wrote; `census()` never read the `supervision` flag at all. N2 is fed: for each
`all_liveness()` row alive under a DIFFERENT goal whose seat name is one of THIS goal's own
declared names, a synthetic `no-seat`/`cwd=<foreign seat folder>` row is appended to `_cap_seats`
before `census()` runs — `resolve_descriptor` walks it to the foreign goal's real `seat.md`,
landing it in `cross_goal`, and the EXISTING `_cap_in_run`/`_cap_cross_out` path-prefix split
(written by `a6b946cc`, never fed a nonempty input until now) correctly excludes it from this run's
cap with zero new arithmetic.

## Consequences
Nothing in `budget.py#census()`'s arithmetic changed — only what feeds it (same discipline
`a6b946cc` established). The capacity migration itself is untouched: 7.278/7.363/D1-D4/BREACH rows
are unmodified and stayed green. `coord_selftest.py`'s three `_c3_state(...)`-driven 7.555/N2 checks
are replaced with registry-fixture-driven ones (`_c3_registry` gained `unsupervised=`/`foreign=`/
`dead=` parameters); a NEW check proves a stale present-but-dead row still spends nothing. N1's
check is untouched, still red, now with an inline comment naming why and what would close it (a
process-tree sweep AT THE GATE, never persisted — new scope, not built here).

## Verification
`python3 coord.py selftest`: 1051 checks both before and after (1027 ok/24 FAIL baseline -> 1030
ok/21 FAIL after) — diffed the FAIL sets: exactly the three targeted rows (7.555 D5, 7.555
transient-twin, N2) flip green, N1 stays red as designed, ZERO new failures anywhere else, `dag-10
RS-4`'s five rows unaffected (untouched code, confirmed by `git diff`). Standalone functional proof
against a throwaway `test-` goal: `goal_liveness` empty pre-spawn, `alive:true supervised:false`
immediately after `record_spawn`, `supervised:true` after `record_checkin`, visible in
`all_liveness()` with the right goal. LIVE proof against a REAL tmux pane in an isolated throwaway
session (`tmux new-session -d -s test-registry-spawn-e2e`, never touching any live goal session):
the pane's own pid reads alive+unsupervised in the registry within ~40ms of `record_spawn`
returning (measured, 5 runs, mean 0.045s/max 0.070s — the node subprocess round trip, not a
network or lock wait), and reads dead once the session is killed. NOT deployed — worktree branch
`ignite/core-daemon`, commit `8a156a0a`.

## ATTENTION
1. `markUnsupervised`/`registerCheckIn` (the JS functions doors.js already exposed) still have NO
   production caller — the fix went through the NEW Python door (`supervisor_door.record_spawn`/
   `record_checkin`) instead, because the real console-lane chokepoint (`launch.py#launch_seat`,
   `checkout.py#cmd_checkin`) is Python, not JS. A future JS-side console launch path must wire
   THIS door's JS twins itself; they are not reached transitively.
2. N1 is a PERMANENT, NAMED gap, not a deferred fix: a registry keyed by `(goal, seat)` cannot represent a
   process nobody ever wrote an identity for, by construction — no future registry-only change
   closes it. Closing it needs a second observation source, which is exactly what two prior owner
   rulings (`ignite/work-on-ignite/memory/supervisor/20260828-i-pane-census-deferred-every-dae.md`
   and this plan's own walls) bar. Do not re-attempt without a fresh owner ruling.
3. `launch.py`'s capacity block now runs an EXTRA `node` subprocess call (`all_liveness()`, the N2
   scan) on every `cmd_launch` invocation, including daemon-lane goals that never read the result
   (the `_lane == "daemon"` branch is checked AFTER this block, same pre-existing waste pattern the
   D5 correction already had). ~40ms measured overhead, not gated on lane.
4. The `_c3_out` selftest fixture at `c3-other-goal/seats/cap3` was RENAMED from `elsewhere` to
   `cap3` (a real declared seat name in the fixture) — the new N2 mechanism matches by seat-NAME
   collision across goals, never by raw path, so a non-colliding foreign name never reaches the
   predicate at all. A future edit to the `cap*` fixture seat names must keep this one in sync.
- N1 is a permanent, named gap — a registry keyed by (goal, seat) cannot represent a process nobody ever wrote an identity for
