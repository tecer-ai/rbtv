# 20260825-c-frozen-tick-driver-post-restar — frozen tick driver + post-restart alarm suppression

kind: creation
component: engine
date: 2026-08-25
commit: 256b91ae
deployed: no
pin: ignite/engine/probes/probe-frozen-driver.js
components: observation,server,supervisor,capabilities

## Motivation
`observation/frozen.js` landed proven and UNCALLED — its own entry says "wiring itself is not
done here — nothing calls either module yet", and `frozen_window_min` had no reader on that path
at all. So the one surviving liveness alarm [T1-R15] could not fire, for any goal, ever.
Separately, task #113 criterion 2 stands open from incident BIT-7: across the 2026-08-19 restart
a relaunch grant's pickup latency swung from 17 s to 10 m 35 s, and every latency-shaped check
read that swing as a stall — the queue the daemon woke to was three hours deep and everything in
it was late by definition.

## Design
TWO small modules in `engine/`, plus a fact collector in the pass that already computes the
facts.

`frozen-pass.js` is the driver and only the driver: it decides nothing about what frozen means.
It reads `frozen_window_min` through `supervisor/recovery-config.js#loadRecoveryConfig` — the ONE
reader of that file — and a pass that cannot read it arms NOTHING and says so, exactly as
`ticker.js`'s deferred counter does. There is no fallback window anywhere on the path
[spec-recovery §2.1].

The FACTS come from `engine/lane-watch.js`, because that pass already runs once a cadence over
exactly the goals the daemon drives and already knows, per goal, the goal-state row, the pause,
what it just enqueued and what the provider lanes say. `frozenFactsFor` collects them where they
are known; re-deriving them in the driver would make it a second scheduler, which is what
`frozen.js` refuses to be one level down. Only goals the pass actually SEEDED are observed — a
goal it stepped over (console lane, no taskforce, unreadable casts, a live console run) is not
reported as frozen OR as healthy, because frozen counts nothing in by exception and the pass
already says out loud why it skipped.

`restart-window.js` answers "may a latency alarm fire right now?" off the WATCHDOG's append-only
outage ledger. A daemon that has just restarted cannot know it restarted — its process-lifetime
state is precisely what the restart erased — so the fact has to come from a process that stayed
up. TWO ledger decisions count and no others: `recovered` and `restart-taken`. The withheld-restart
arms and `observed-not-healthy` are NOT restarts: the daemon never went away, nothing about its
queue depth changed, and suppressing on them would be silence bought with no event.

The suppression window is `RBTV_RESTART_ALARM_SUPPRESS_MIN`, deliberately NOT a ninth key in
`recovery.json`: spec-recovery §2.1 pins that schema at eight keys and its loader REFUSES extras,
so adding one would be a spec change and would redden that loader's own selftest. Unset means NO
suppression — today's behaviour — because a window nobody configured must never silence a real
page. Rejected: reusing `frozen_window_min` because it also happens to be 15.

## How it works
`server/index.js` calls `frozenPass(laneWatchPass())` once a cadence, immediately after the lane
watch and before the tick, and never awaits it into the tick's latency. `runFrozenPass` refuses
without a workspace root, without `RBTV_SYSTEM_CHANNEL_ID` and without a readable recovery
config; then it asks `restartSuppression`, and a suppressed pass returns having checked nothing —
the WHOLE pass, not one alarm, because after a restart every goal is late for the same reason.
Otherwise it builds the durable outbox, the emitter and `createFrozenInvariant` with the config's
window and a persisted hold clock at `.rbtv/runtime/ignite/frozen-holds.json`, and calls
`checkOne` per observation, adding `channel_id` — the system channel [T5-R1], because a goal's own
Slack channel id is not knowable daemon-side (the bridge holds that map, in its own process). A
refused observation is logged and skipped: one malformed goal must not take the daemon's tick
down. The outbox `send` is UNWIRED on purpose (`r-cutover-gated`): the post is minted
`pending-delivery` with that reason on the row, and the owner reads the condition through the
2-hourly digest, which re-surfaces it [§9.2]. `restart-window.js` reads the ledger's last 64 KB
from the end and takes the newest matching `at`, so a never-rotated ledger cannot turn into a
growing per-cadence cost.

## Consequences
`runLaneWatch` returns a third key, `frozenFacts`; `adopted`/`skipped` are unchanged and nothing
in the pass acts on the new one. `laneIsPaused`, `bindEnding` and `laneFacts` are consumed
read-only. Nothing in `ignite/observation/` was touched — `component.md` gained one appended
section registering this caller, exactly as the watchdog's did. Two knobs are now read from the
environment in `server/index.js` and neither has an in-code default:
`RBTV_SYSTEM_CHANNEL_ID` and `RBTV_RESTART_ALARM_SUPPRESS_MIN`. A deployment that sets neither
gets what it has today: no frozen alarm, and no suppression.

## Verification
`engine/probes/probe-frozen-driver.js` — 29 checks, exit 0, fixture workspace with injected
clock, registry and ledger files. It proves the hold clock across three cadences (nothing at 0,
nothing one minute inside the window, one alarm past it), one open registry row keyed on
condition-class + subject, the durable `pending-delivery` post carrying the r-cutover-gated
reason, the dedupe on the next cadence, the [C-5] backoff exclusion clearing a standing row, both
"not armed" refusals (no recovery config, no system channel), the suppression pair (the SAME goal
at the SAME instant alarms without a ledger row and is suppressed with one 5 minutes old), the
window elapsing, the decision allow-list, the bounded tail read over a 4 000-row ledger, and
`frozenFactsFor`'s four facts against a real store. Three mutations run by hand each reddened
exactly the claiming rows: ignoring the suppression, admitting `observed-not-healthy` as a
restart, and giving the window a hardcoded 15-minute fallback. `observation/frozen.selftest.js`
and `emitter.selftest.js` still ALL PASS; `supervisor/*.selftest.js` (13) all exit 0;
`engine/probes`, `server/ticker/probes` and `server/heart/probes` re-run green. Not deployed:
worktree `5-workbench/rbtv-redesign`, branch `ignite/core-redesign`.

## ATTENTION
1. The facts must keep coming from the pass that computes them. `eligible_launch` is
   `pickup.enqueued` — the seed's own answer — and re-deriving it with a second `deriveOwed` call
   would put two answers to one question on two cadences, which is the state `supervisor/owed.js`
   was written to end.
2. Suppression is per-PASS, not per-alarm. After a restart every goal's latency is wrong for the
   same reason, so filtering alarm by alarm is arithmetic over a fact that applies to all of them
   — and it would let the first goal checked page before the filter had anything to compare.
3. Never add the suppression window to `recovery.json`. That schema is closed at eight keys by
   spec-recovery §2.1 and its loader refuses extras; a ninth key breaks every instance file that
   does not carry it, including the seeded default.
4. Only `recovered` and `restart-taken` are restarts. Admitting `observed-not-healthy` would
   suppress alarms for as long as the daemon is UNHEALTHY — the exact window in which the owner
   most needs them.
5. The daemon's outbox `send` stays unwired. Arming a credentialed transport in the daemon is a
   cutover (`r-cutover-gated`), and the alarm already reaches the owner: the digest re-surfaces
   the open condition, which is the designed path, not a degradation.
- suppression is per-PASS, not per-alarm: after a restart every goal is late for the same reason
- never add the suppression window to recovery.json — that schema is closed at eight keys and its loader refuses extras
- only `recovered` and `restart-taken` are restarts; `observed-not-healthy` would mute the window the owner most needs
