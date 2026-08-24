# 20260824-c-supervisor-door-list-the-one-l — Supervisor door list + the one liveness probe

kind: creation
component: engine
date: 2026-08-24
commit: 758ecd4b
deployed: no
pin: ignite/supervisor/doors.selftest.js
components: team-kit,server

## Motivation
Launches were ad hoc and liveness had three answers. Seeding enqueued, reconcile enqueued,
`launch --rerun` composed its own pane or its own enqueue, and a bare console `claude` was born
with nobody watching — four births, no common door, so "what did this daemon spawn?" had no answer
that survived a restart. Meanwhile "is this seat alive?" was answered by a tmux pane
(`live_panes`/`cmd_status`), the cgroup carrier (`carrier_self_session`) and tick silence, three
disjoint predicates that could disagree. The registry landed by the registry seat was written by
NOTHING: `recordSpawn` had no caller outside its own selftest, so a persisted liveness surface that
only some launch paths wrote to would have lied by omission. [T4-R7] [T4-R8] [C-15]

## Design
Two files beside the registry. `doors.js` is spec-supervisor §3's table as code — six rows, each
`wrapped` or `marked-unsupervised` — plus `superviseSpawn` (registry write moment (i)),
`markUnsupervised`, `registerCheckIn` and `refuseLaunch`. `probe.js` is the ONE
`(goal, seat)` liveness answer, composing "find the row, then probe it" once instead of at each of
the seven legacy consumers.

The door NAME is DERIVED, not passed: seeding's and reconcile's enqueues already stamp
`enqueued_by` on the queue row, `ticker.js#launchAgent` already threads `queueRow.enqueued_by` into
`spawn()`, and `--rerun`'s daemon-lane composer already carries its own `leader-<door>-…` reason
token. So no call frame gained a parameter, and the seeding/reconcile launcher strings are now READ
OFF the door list rather than spelled locally — two spellings is a launch that silently registers
unsupervised the day either side is edited. Rejected: threading an explicit `door` argument through
four frames (the value was already travelling), and refusing an unmapped launcher (a process is
already running at that point, so refusing would be a lie — it is marked instead).

## How it works
`superviseSpawn` is called on BOTH spawn doors — headless `spawn()` and headed `spawnSeat()` — on
the first line after the pid + `/proc` start-time pair resolves, and deliberately AHEAD of the
`sessions.csv` row and the heart-store status update: those are records ABOUT the launch, and a
crash between the spawn and them left a live process no restart could re-adopt. `launch_token` is
the session id, the daemon-minted identity, never the pane and never the cgroup [T2-R8].

`probeSitting` answers three-valued: `true`, `false`, or `null` for NO ROW. `null` is UNSUPERVISED
and is never collapsed — into `true` it re-invents the pane, into `false` it re-opens the
mass-restamp hole. `team-kit/liveness.py` is the python door (`node supervisor/probe.js`, one call
per goal for a roster render) and its `occupied()` collapses the three values once, for the
double-launch walls, failing CLOSED on the unknown arm. The seven consumers: `tmux.py` and
`carrier.py` keep their predicates for what they actually are (a viewport; identity), `messages.py`
renders `DEAD` off the registry and `UNREACHABLE` when only the pane has anything to say,
`checkout.py` and `launch.py` walls ask `occupied`, `cli_main.py`'s help stops teaching the retired
vocabulary, and `ticker.js`'s crash sweep forks on the registry instead of `spawnManager.status().live`.

`--rerun`'s from-state moved with it: `exited` written by the kit becomes `failed` + reason class
`crash`/`provider-error` read off the ending store. NOT widened — `failed`/`outputs-missing` is
still refused and routed by name.

## Consequences
`registry.jsonl` now gets written on every daemon launch, so boot re-adopt finally has rows to
re-adopt. `closeout.py`'s pane-walking reaper is DELETED: its debt file was gone, its two-sighting
ledger `confirm_reap` referenced the deleted `awaiting_path` and would have raised NameError inside
a lock, and the supervisor arm beside it already confirms by probing and waiting. `awaiting_debts`
now derives from `supervisor.awaitingReap`, so the reaper finds debts again (G-134). Three helpers
of the deleted reaper — `reap_blockers`, `pane_harness_idents`, `verify_pids_gone` — are left
UNCALLED and are a named loose end: their `coord_selftest` rows still assert them.

## Verification
`node supervisor/doors.selftest.js` — 4 cases, ALL PASS, exit 0, every arm on REAL child
processes: (a) each wrapped door's launcher lands a SUPERVISED row and the sitting probes alive,
with the control that an unmapped launcher is marked instead; (b) console-uncaged reads
`{supervised:false, alive:null}` before any row, `alive:true`+`supervised:false` while marked and
running, and FLIPS on check-in without adding a second row; (c) `E_GOAL_NOT_LIVE` refuses with
`spawned/stamped/enqueued` all false AND no registry file created at all; (d) the door list is
§3's six rows with exactly one marked. Red-ability MEASURED: forcing `superviseSpawn` to write
`supervised` unconditionally reddens (a)'s control alone — one FAIL, three PASS.
`node deploy/probe-suite.js --dir server/spawn/probes --dir server/ticker/probes --dir engine/probes --dir supervisor`
— 72/75, the 3 reds pre-existing and measured so (two are the heart-store schema-10 bump from the
state-store seat; `probe-trace-header` reddens identically with this change stashed out).
`coord.py selftest` — the inherited 53 failures and the 644-check abort are UNCHANGED by this work
(same rows, same abort site). NOT deployed — worktree branch `ignite/core-redesign`.

## ATTENTION
1. `probeSitting` returning `null` is UNSUPERVISED, not "probably dead". Every one of the seven
   consumers branches on all three values; a future consumer that writes `if (!alive)` treats an
   unregistered console seat as a corpse and reopens C-15 from the consumer side.
2. `superviseSpawn` is called with the pid ALREADY RUNNING. Its failure is warned and swallowed on
   purpose — a bookkeeping throw there would lose a live process — which means a registry write
   that silently fails costs re-adoptability, not the launch. Read the `warn` line, it names it.
3. The door name is DERIVED from `enqueued_by` / the `--rerun` reason token. Renaming either string
   at its source without adding it to `doors.js` does not break anything loudly: the launch simply
   registers `unsupervised`. That is the failure mode to grep for.
4. Deleting `closeout.py`'s reaper left `reap_blockers`, `pane_harness_idents` and
   `verify_pids_gone` with no caller. They are still asserted by `coord_selftest` rows, so removing
   them is a test change too — do both or neither.
- a null liveness answer is UNSUPERVISED, never dead
