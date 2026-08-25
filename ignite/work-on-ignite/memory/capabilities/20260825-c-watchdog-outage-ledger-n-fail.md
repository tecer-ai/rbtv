# 20260825-c-watchdog-outage-ledger-n-fail — watchdog outage ledger, N-fail alarm, dead-man

kind: creation
component: capabilities
date: 2026-08-25
commit: 0cbbb555
deployed: no
pin: ignite/capabilities/daemon-watchdog/probes/probe-watchdog-bit7-silence.py
components: observation

## Motivation
[T4-R9, C-17] give the external watchdog three duties it did not have: a persistent record of every
restart DECISION including the withheld ones, an alarm on N consecutive failed probes even when the
restart is withheld, and one non-Slack channel that still signals when Slack is unreachable. The
driver is BIT-7 (see the sibling issue entry `20260825-i-bit-7-unknown-was-a-silent-sta`): a 3h05m
daemon outage on 2026-08-19 during which this component's snapshot state file read `restarts: 0`
and no owner alarm fired. The diagnosis fixes why the existing paths were silent; these three
creations are what stops the same class of silence from having only one detector.

## Design
Three additions to `capabilities/daemon-watchdog`, plus one new file and one new probe.

APPEND-ONLY LEDGER, not more fields on the snapshot. `.rbtv/runtime/watchdog/daemon.json`,
`state.json` and `failcount.json` all go through `write_json_atomic()` and are REWRITTEN each pass,
so they can only ever answer "what is true now". `ledger()` writes
`.rbtv/runtime/watchdog/outage-ledger.jsonl` in append mode, one JSON object per line, so a decision
taken at 18:19 is still readable at 21:30 and across any number of watchdog and daemon restarts.
Rejected: extending `daemon.json` (a snapshot cannot hold history) and a rotating log (nothing here
needs rotation yet, and a rotation policy is a second thing to get wrong). `ledger()` never raises:
record-keeping that can abort the pass would be a new way for a liveness component to go blind.

THE ALARM GOES THROUGH THE ONE EMITTER, VIA A SHIM IN THIS COMPONENT'S OWN TREE. This tool is
Python and `ignite/observation/emitter.js` is JavaScript. Rejected: a Python alarm composed here —
that is exactly the "alarms composed at whatever call site noticed the condition" defect the emitter
was built to end, and it would have been a second emitter within a day of the first landing.
Rejected also: adding a CLI entry point inside `observation/` — that module is a wall to be
consumed, not extended, so a caller needing a different process owns its own bridge to it. Taken:
`tool/watchdog-alarm.js`, a ~100-line shim in the watchdog's tree that marshals one finished
observation from stdin into `emit()` and prints what the emitter answered.

DEAD-MAN BY ABSENCE. The CP1-ruled choice in spec-owner-io §8: a healthchecks-style HTTPS ping on
every determinately-healthy pass, where the MISSED ping is the alert. This is the only shape that
covers the branch no in-band alarm can — the watchdog itself being dead — and it needs no new
process, because the 60s systemd timer that fires this pass already exists.

## How it works
`daemon_health_streak(st, ident, dry)` runs as a third row of `daemon_verdicts()` and counts
consecutive non-determinately-healthy readings in the persisted daemon state (`unhealthy_streak`,
`unhealthy_since`). On health it clears the streak, records `last_outage_seconds` /
`last_outage_ended_at` / `last_outage_passes` when one was standing, ledgers `recovered`, and calls
`deadman_ping()`. On non-health it increments, ledgers `observed-not-healthy`, and at
`streak >= STRIKES` calls `emit_alarm()` once per episode (`alarmed_unhealthy_at` guards the
repeat, and is popped on recovery so a SECOND episode alarms). `emit_alarm()` runs
`RBTV_WATCHDOG_NODE` (default `node`) against `RBTV_WATCHDOG_ALARM_SHIM` (default the sibling
`tool/watchdog-alarm.js`), signature class `watchdog-daemon-unhealthy`, subject
`{type: "daemon", id: <unit>}`, `immediate: true`, evidence pointer = the ledger path. The shim
builds the outbox over `bridges/chat/outbox.js` with an unwired `send`, so every post is minted and
held `pending-delivery` [C-17] until the chat bridge lands its transport. `daemon_restart_gate()`
ledgers all four of its arms; `main()`'s action path ledgers `restart-taken` with the reprobe
verdict for EVERY row, not just `daemon`. `deadman_ping()` checks `RBTV_WATCHDOG_NOTIFY_FILE`
BEFORE `RBTV_WATCHDOG_DEADMAN_URL`; with the sink set it appends a
`{"deadman": "would-have-pinged", "url": …}` record and makes no request at all. New environment
knobs, all documented in `daemon-watchdog.md` § Environment and all resolved at runtime with no
hardcoded endpoint: `RBTV_WATCHDOG_LEDGER`, `RBTV_WATCHDOG_DEADMAN_URL`, `RBTV_WATCHDOG_ALARM_SHIM`,
`RBTV_WATCHDOG_NODE`, `RBTV_SYSTEM_CHANNEL_ID`.

## Consequences
Nothing was deleted or replaced: the restart gate, the 6h re-alert ceiling, the R1 exit-code ruling
and the `unknown`-never-claims-DOWN calibration all stand unchanged. `daemon_verdicts()` returns
three rows instead of two, so `probes/probe-g188-daemon-identity.py` had its row-set assertion
updated to name the third row by name rather than loosen its count. The watchdog now has an
optional `node` dependency on its alarm path only — absent or failing, the pass ledgers
`alarm-emit-failed` and retries next pass. `ignite/observation/component.md` gained one appended
section registering this caller; no code in `observation/` was touched. One open seam surfaced, not
closed here: the outbox's Slack transport is the chat bridge's to wire, so watchdog alarms currently
stop at a `pending-delivery` record.

## Verification
`probes/probe-watchdog-bit7-silence.py`, 20 checks, exit 0 — one open row in the emitter's signature
registry with the four required fields and `emission_count: 1`, one `pending-delivery` alarm in the
durable outbox, one reasoned ledger row per withheld arm and per non-healthy pass, a `recovered` row
carrying the incident's real 11 115-second duration, and the dead-man's closed-port URL proven
unreachable in dry mode (with the sink removed the same URL reports `failed`, so the dry arm is a
wall rather than an absent endpoint). All four pre-existing probes of this component stay green,
including `probe-g188-daemon-identity.py` at 112/112 and `probe-watchdog-staged-failure.py`'s full
down→restarted→notified→recovered chain. NOT deployed: landed on the worktree branch
`ignite/core-redesign`; no unit was restarted and no live endpoint was contacted.

## ATTENTION
1. The dead-man's whole signal is the ABSENCE of a ping, so ANY test or rehearsal path that can
   reach the real endpoint silently disarms it for the length of its own period.
   `RBTV_WATCHDOG_NOTIFY_FILE` and `--dry-run` are therefore hard walls checked before the URL, and
   the BIT-7 probe points its configured URL at a closed local port so a stray ping shows up as a
   failure instead of passing unnoticed.
2. `tool/watchdog-alarm.js` lives in the WATCHDOG's tree on purpose. Do not move it into
   `ignite/observation/` for tidiness: that module is consumed, never extended, and a caller in a
   different language owning its own bridge is what keeps the emitter's surface from growing one
   entry point per caller.
3. The alarm is ONE emission per episode by design (spec-owner-io §9.2) — the 2-hourly system
   digest re-surfaces the open condition. A "why did it only tell me once" report is not a bug here;
   check whether the digest is wired before adding a repeat.
4. `emit_alarm()` and `ledger()` both swallow their own failures on purpose. A pass that dies while
   raising an alarm is the exact failure this component exists to prevent, so a subprocess error
   must never propagate — a failed emission is ledgered as `alarm-emit-failed` and deliberately does
   NOT stamp the episode, which is what makes the next pass retry.
5. Everything added to `daemon_verdicts()` must honour its `dry` flag on every side effect. It is
   invoked with `persist=False` from `--dry-run`, and a diagnostic verb that writes a ledger row,
   pings the dead-man or emits an alarm is a verb nobody dares run.
- the dead-man's signal is the ABSENCE of a ping — any test path reaching the real endpoint disarms it
- watchdog-alarm.js belongs in the watchdog tree, not in observation/ — the emitter is consumed, never extended
