# 20260827-i-daemon-lane-goal-s-first-room — Daemon-lane goal's first room had no opener

kind: issue
component: supervisor
date: 2026-08-27
commit: 9cdb472e
deployed: no
pin: ignite/supervisor/probes/probe-lane-room-open.js
components: runtime,operator

## Observed
`scratch-cli-reach-report` was created 2026-08-27 ~14:43Z through the goal-creation
REQUEST route (acceptance-wave test 4 re-run #4) and was born correctly: a 7-row
`taskforce.csv`, 7 seat folders, `execution-lane` = `daemon`. It was then NEVER seeded.
From 14:55:12Z the daemon journalled, every 10 s, `goal NOT seeded this pass — the goal
is not LIVE, and seeding it would spend grants on launches the spawn door refuses`, with
evidence `goal scratch-cli-reach-report has NO live room (tmux session named
`scratch-cli-reach-report`) … Start the room (`rbtv run`)`. Deployed and HEAD agreed —
this was not a deploy lag. The goal's `sessions.csv` never existed, so not one seat ever
launched. The same state was reachable by any goal the daemon lane creates: at the time
of the fix, `scratch-cli-reach-report` was the only live instance, because every other
daemon-lane goal either had a room already (`goal-memory-management`), was paused, or had
no `taskforce.csv`.

## Mechanism
`ignite/supervisor/seeding.js#seedGoal` reads `deriveLease({workspaceRoot, goal}).live`
FIRST (the D9 seed gate, 2026-08-19) and returns with nothing enqueued when it is false.
`live` is `rooms.length > 0` (`ignite/runtime/lease/lease.js`), and `roomNamesForGoal`
matches a tmux session whose name is EXACTLY the goal name. So a goal with no room can
never be seeded — correctly, since the spawn door would refuse every launch
`E_GOAL_NOT_LIVE`.

No daemon-side path opened a FIRST room. Three candidates and why each misses:
`reconcile.js` rebuilds a room (`recover-room.py --seat`), but only inside
`if (derived.owed)`, and `supervisor/owed.js#deriveOwed` is false by construction for a
goal that never launched a seat — the watcher hands in only the LEDGER half, whose seat
set is `[...lastBySeat(loadSessions(goalFolder)).keys()]`, and `sessions.csv` does not
exist. Room selfheal was unarmed at creation on 2026-08-20 (retire-health) precisely
because reconcile was said to cover it — it covers REBUILD, never FIRST OPEN.
`runtime/cockpit.js` opens only the fixed `rbtv-cockpit` session. And the code that DID
open a goal's first room, `workflow_launcher.py`, was deleted by 7.778 (2026-08-12): its
own note in `operator/goal-creation-request/tool/goal_creation_request.py` reads "WHAT
OPENS THE ENTRY SEAT NOW: the LANE … A `console` goal opens when a human types `rbtv
run`" — the lane was handed the job and never given a room-opener. That missing half is
where the wrong state is born.

## Attempts
First attempt held — checked: `git log` on `ignite/supervisor/seeding.js`,
`lane-watch.js` and `runtime/cockpit.js`; `grep -rn 'new-session' ignite/` (only
`cockpit.js:261`, `runtime/jobs/recover-room.py:256` and probes — no third opener ever
existed); the build memory (`supervisor/20260826-i-direct-created-daemon-goal-ski` fixed
the ADJACENT half — a daemon goal with no taskforce — and left the room untouched;
`server/20260823-i-lane-aware-launch-doors` records "On the daemon lane these doors
enqueue via `launch_daemon_lane`; they do not open panes", which is the same absence seen
from the leader's side). The FAILURE-INVENTORY row `not-live / E_GOAL_NOT_LIVE | No —
owner `rbtv run` | IE-1` is a record of the DEFECT, not a ruling: its own table is
"is there a working automatic clear", and its summary is that only one of 24 live states
has one. No owner ruling that the room must be a human act exists in the redesign specs,
the baseline, or this plan's decisions — searched for `R15`, `RUN-scoped`, `IE-1`.
`R15` in the specs is `[T1-R15]` (frozen window), `[T2-R15]` (envelope config) and
`[T3-R15]` (handoff contents); the settle-ledger R15 quoted in `cockpit.js` says "A goal's
tmux room is RUN-scoped: created at run start, torn down at run close" — a LIFECYCLE
statement that the lane's first seeding pass satisfies, not a who-may-create rule.

## Fix
`lane-watch.js#openGoalRoom`, called immediately before `engine.seedGoal`, opens the room
itself and the goal seeds in the SAME cadence.

WHY IN THE LANE AND NOT IN `seeding.js`: `seedGoal` is deliberately lane-agnostic — its
own header, "It is deliberately a FUNCTION AND NOT A TRIGGER" — and the attached lane and
the probes call it. An opener there would open rooms for lanes that own their own. The
call site was chosen because every lane-shaped guard is already established there: the
goal is `daemon`-assigned (a `paused ` marker's whole text is not `daemon`, so it
flattens to `console` and never reaches this point), `taskforce.csv` exists, and no
console run is live.

FOUR REMAINING GUARDS, each a state a room must not be opened in: no launchable row
(every seat unbuilt or uncast → a room nothing can use); an UNREADABLE lease (refused on
ignorance, the same posture `seedGoal` takes); a LIVE room (the idempotence — never a
second room, whoever opened the first); and `sessions.csv` carrying rows. The last is the
"owner closed it" test: seats HAVE run in a room here, so its absence is a closure after
the fact, which is `reconcile.js`'s owed/rebuild subject. Re-opening from here would race
that path AND re-open a room the owner deliberately closed.

ONE OPENER, NOT A COPY: `supervisor/spawn/tmux.js#composeDetachedSession` was extracted
from `cockpit.js`'s inline vector and both callers now use it (the cockpit's argv is
byte-identical — it passes `windowName`, the lane omits it). Rejected: reusing
`recover-room.py` (it requires `--seat` and launches a recovery harness; the lane wants
the room only, and seeding launches through the ordinary door), and widening
`buildScopeArgv` (it emits `--quiet`, no `--collect`, takes seat caps and names units
`rbtv-seat-*` — widening it would change every seat's argv).

`seeding.js`'s not-live refusal text was rewritten: it named `rbtv run` unconditionally,
which is false for a daemon-lane goal. It now names who opens the room per lane.

## Consequences
`cockpit.js` no longer composes its own `new-session` vector and no longer calls
`assertTmuxName` directly (both reached through `composeDetachedSession`); the argv is
unchanged byte for byte and `probe-cockpit` is 40/40. `runLaneWatch` gained a `roomsOpened`
array in its return and an optional `runTmux` executor seam (the probes' injection point,
`ensureCockpit`'s own pattern); production passes neither. Nothing else changed behaviour.

The change is NOT DEPLOYED — the deploy advance and daemon restart belong to the
orchestrator. At restart exactly ONE goal wakes that does not today: `scratch-cli-reach-report`
(daemon lane, 7-row taskforce, no room, 0 sessions) gets its room and its first wave —
`plan-understander`, `leader`, `goal-master`, all cast `claude/claude-opus-5` — spawns,
which is paid work. Every other goal in the tree is untouched: `goal-memory-management`
already has a room, four goals are `paused daemon`, three daemon-lane goals have no
`taskforce.csv`, and two are console-lane.

## Verification
New probe `ignite/supervisor/probes/probe-lane-room-open.js`, 22 checks, EXIT 0
(WALL_MS 11076). It drives the REAL `runLaneWatch` / `openGoalRoom` /
`composeDetachedSession` / `deriveLease` against REAL tmux over six fixture goals on a
scratch goals root under `/tmp`: the never-live daemon-lane goal gets a real session named
after it, one `room opened by the daemon lane (first seeding)` journal line, and the real
lease then reports live at the exact threshold seeding reads; the paused, taskforce-less,
console-lane, uncast-only and already-run goals are untouched; a second pass runs no tmux
command at all. Six mutation arms (live-room guard, daemon-lane guard, launchable-row
guard, first-seeding guard, opener-not-called, journal-silenced) each go RED, compiled in
memory with every anchor asserted present first. A seventh arm is deliberately NOT dressed
as a red arm and says so: the taskforce-less goal is protected by three independent guards,
so removing only the first changes nothing.

Only the ENGINE is substituted, and it is disclosed in the probe header: the stub
`seedGoal` re-asks the real `deriveLease` at the production threshold rather than
simulating an answer.

The probe's tmux server is PRIVATE — `TMUX_TMPDIR` is a scratch dir, `TMUX`/`TMUX_PANE`
are cleared before any module loads, and the wrapper inherits that env (verified directly:
a `systemd-run --user --scope`-wrapped `new-session` landed only on the private socket
while the default server's 12 sessions were unchanged). The server is killed in `finally`
and every fixture goal — hence every session — is named `probe-*`. The box's default tmux
session list was byte-identical before and after all work.

Regression, run individually after the change: `runtime/probes/probe-cockpit.js` 40/40
PASS, `supervisor/spawn/probes/probe-tmux-seat.js` exit 0,
`supervisor/probes/probe-seed-gates.js` PASS, `runtime/lease/probes/probe-lease.js` 29/29
PASS. `supervisor/probes/probe-daemon-lane-watch.js` and `supervisor/probes/probe-reconcile.js`
are RED — both were already red in the 14:00:08Z scheduled suite run taken BEFORE any edit,
on the byte-identical failing check (`L9 M9 the prompt key REMOVED from the enqueue` and
`reconcile.selftest.js:392` respectively). The 15:00:01Z suite's non-PASS set is identical
to the 14:00:08Z set, row for row.

## ATTENTION
1. The room-opener is guarded on `sessions.csv` being EMPTY, and that guard is what keeps
   the lane off a room the owner closed. A goal with session rows and no room belongs to
   `reconcile.js`'s owed/rebuild path. Do not "simplify" the two into one opener — they
   answer different questions and reconcile's rebuild launches a recovery SEAT into the
   room it creates.
2. `composeDetachedSession` must stay `systemd-run --user --scope --collect`-wrapped. An
   unwrapped `tmux new-session` from the daemon forks the tmux SERVER into
   `rbtv-ignite.service`'s `KillMode=control-group` cgroup, and the next restart reaps
   every pane on the box including the owner's own sessions (measured 2026-08-14).
3. The goal room takes NO `-n` window name and NO command after `-c`. The absent command
   is what makes the pane unable to exit; the absent window name is what makes a
   daemon-opened room indistinguishable from a human-opened one.
4. `probe-daemon-lane-watch.js` injects `fixtureLiveLease`, which reports EVERY goal's
   room live. That substitution is why this defect was invisible to the probe that covers
   the lane pass — do not treat that probe as coverage of the room's existence.
5. `FAILURE-INVENTORY.md`'s `not-live … No — owner `rbtv run` | IE-1` row is an inventory
   of a BROKEN state, not a ruling that a human must open the room. Do not cite it as one.
- sessions.csv-empty is the guard that keeps the lane off a room the owner closed
