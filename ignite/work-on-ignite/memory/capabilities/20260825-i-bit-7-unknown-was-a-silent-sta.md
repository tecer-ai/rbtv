# 20260825-i-bit-7-unknown-was-a-silent-sta — BIT-7: unknown was a silent state

kind: issue
component: capabilities
date: 2026-08-25
commit: 0cbbb555
deployed: no
pin: ignite/capabilities/daemon-watchdog/probes/probe-watchdog-bit7-silence.py
components: observation

## Observed
`capabilities/daemon-watchdog` observed a 3h05m ignite-daemon outage and produced NOTHING —
neither of its two record surfaces fired. Incident BIT-7: 2026-08-19, 18:18:44Z→21:24:59Z, the
`meet-transcript-summarizer` goal executed no row for the whole window (`executions.csv` density
before it was one row every few minutes), and the leader chair that noticed at 21:30 filed
`G-leader-0819-2130` after finding `.rbtv/runtime/watchdog/daemon.json` reading
`{"daemon_restarts_flagged": 0, "daemon": {"state": "running", "restarts": 0, "since": "Wed
2026-08-19 21:23:39 UTC", "invocation": "179483a159ca4eacb7c5fb19ebbdcce2"}}` — a state file that
reads CLEAN across a three-hour outage. No owner DM fired either. Recurred twice; the same
snapshot is what task #113 was written against. The box did not reboot (uptime spans the window)
and `user@1000.service` has `Linger=yes` with `NRestarts=0` since 2026-08-14, so the user manager —
and with it the 60s watchdog timer — never went away.

## Mechanism
`unknown` was a SILENT state, on both surfaces at once.

`daemon_identity()` returns one of `running` / `stopped` / `unknown`, and deliberately collapses
every non-determinate answer into `unknown` (`LoadState != loaded` is reported as unknown, never as
absent, because a wrong-bus answer is byte-identical to a missing unit). Downstream of that:

1. `check_daemon()` fires its DOWN note only on a DETERMINATE `stopped`. The `unknown` branch is an
   explicit fall-through — "no note, and NOTHING IS CLEARED" — so no alert was appended, so
   `main()`'s alert list stayed empty on the identity path and the notify leg never ran.
2. `_daemon_change()` returns `None` whenever either side of the comparison is `unknown`, so no
   restart/change record was ever persisted and `restarts` stayed at systemd's own `NRestarts` —
   an EVENT counter that reads 0 through a straight outage nobody tried to restart.

The proof is in the artifact the incident left. At 21:30, six passes after the daemon returned at
21:23:39 on a FRESH invocation id, `daemon.json` still carried NO `notified_daemon_invocation` key.
That key is only ever SET (never popped), and it is set exactly when `check_daemon()` emits its
RESTARTED note — which requires `_daemon_change()` to have returned non-`None`. Its absence rules
out both alternatives: a watchdog that had been dead through the outage would have compared the
pre-outage `running`/old-invocation reading against the new one and emitted; a watchdog that had
read `stopped` would likewise have emitted (and would have DM'd DOWN on pass one). Only a
previously-persisted NON-DETERMINATE reading produces `None` there. So the watchdog ran, and read
`unknown`, for the whole window.

## Attempts
First attempt held on the silence itself — checked: the whole git history of
`tool/rbtv-ignite-watchdog` and every neighbouring commit named in task #113's staleness check (an
unrelated 2026-07-27 restart-count probe and a 2026-08-21 dead-code deletion; no commit since
2026-08-18 touches `restarts`, `daemon.json`, downtime or grant-pickup latency). Two EARLIER
amendments to this same row are load-bearing context and were deliberately NOT reversed: the
2026-08-14 restart gate (added after 57 false restarts reaped the shared tmux server) and the
2026-08-15 R1 exit-code ruling (an alarm is not a systemd failure). The `unknown`-never-pushes
calibration is itself a deliberate earlier decision — it is KEPT, not undone; see ATTENTION 1.

## Fix
Report ABSENCE OF HEALTH, never wait for a determinate `stopped`. A new
`daemon_health_streak(st, ident, dry)` runs as a third row of `daemon_verdicts()` and counts
CONSECUTIVE non-determinately-healthy identity readings in the persisted daemon state. Three duties
hang off it:

- `ledger()` writes `.rbtv/runtime/watchdog/outage-ledger.jsonl`, append-only, one JSON object per
  line, never rewritten: every restart TAKEN, every restart WITHHELD with its arm (`unit-alive` /
  `backoff` / `strikes`) and reason, every non-healthy reading, and on recovery an `outage_seconds`
  duration (also mirrored to `daemon.json` as `last_outage_seconds` — the field task #113 asked
  for). WHY a second file rather than more fields on `daemon.json`: that file is a SNAPSHOT
  rewritten every pass, so it can only ever say what is true now. A withheld restart is the
  decision that made BIT-7 invisible, and a ledger recording only actions is silent in exactly the
  case it exists for. `ledger()` never raises — record-keeping that can abort the pass would be a
  new way for this component to go blind.
- N consecutive non-healthy passes (N = the existing `RBTV_WATCHDOG_STRIKES`, kept per
  spec-owner-io §8) raise ONE alarm even when the restart is withheld, through the ONE alarm
  emitter (`ignite/observation/emitter.js`) as an ordinary caller. Rejected: a Python alarm
  composed here — that is precisely the "alarms composed at whatever call site noticed" defect the
  emitter was built to end. Taken instead: a sibling Node shim, `tool/watchdog-alarm.js`, in the
  WATCHDOG's own tree rather than in `observation/`, because the emitter is a wall to be consumed,
  not extended. Signature class `watchdog-daemon-unhealthy`, `immediate: true` (system-health is
  digest-exempt for its first post, spec §9.2), posted through the durable outbox so an unwired or
  unreachable Slack leaves a `pending-delivery` record instead of a lost alarm.
- `deadman_ping()` — the CP1-ruled non-Slack channel: a healthchecks-style HTTPS ping on every
  determinately-healthy pass, so a MISSED ping is the out-of-band alert. This is the only signal
  that still fires when Slack is unreachable AND when the watchdog itself is dead — the branch no
  in-band alarm can cover, and the branch this diagnosis could not fully exclude on its own.

ONE emission per episode, re-armed on recovery: spec §9.2 gives one alarm per condition-signature
and hands re-surfacing to the 2-hourly system digest, so a second emission would be volume rather
than coverage.

## Consequences
`daemon_verdicts()` now returns THREE rows, not two — `probes/probe-g188-daemon-identity.py`'s
row-set assertion was updated to name the third row rather than loosen its count. Nothing was
deleted: the restart gate, the 6h re-alert ceiling, the R1 exit codes and the `unknown`-never-
claims-DOWN calibration are all unchanged. Two runtime dependencies are NEW and both are optional
and loud when absent: `node` plus `RBTV_SYSTEM_CHANNEL_ID` for the alarm route (a failure is
ledgered as `alarm-emit-failed` and retried next pass, never swallowed), and
`RBTV_WATCHDOG_DEADMAN_URL` for the dead-man (unset says on its own row that the out-of-band
channel is NOT armed). The Slack transport behind the outbox is still unwired by the chat bridge,
so every watchdog alarm currently mints a `pending-delivery` outbox record and stops there.

## Verification
`probes/probe-watchdog-bit7-silence.py`, 20 checks, exit 0 — it substitutes a non-determinate
identity reading carrying NO restart count (the incident's own shape) and asserts the RED and GREEN
halves in one run: `check_daemon()` still emits nothing on that reading, while the ledger, the
emitter's signature registry (exactly one open row, `watchdog-daemon-unhealthy`, `immediate: true`,
`emission_count: 1`) and the durable outbox (one `alarm` record, `pending-delivery`) all carry the
condition. It also pins the recovered duration against the incident's real 11 115 seconds, proves
each withheld-restart arm writes a reasoned row, and proves the dead-man's configured URL — a
closed local port, so a stray ping would show as `failed` rather than pass unnoticed — is never
reached in dry mode. The four pre-existing probes of this component stay green:
`probe-g188-daemon-identity.py` 112/112, `probe-watchdog-staged-failure.py`,
`probe-watchdog-alarm-exit-zero.py`, `probe-watchdog-dry-run-no-dm.py`,
`probe-runner-grade-verdicts.py`, all exit 0. NOT deployed: this landed on the worktree branch
`ignite/core-redesign`, not on the live tree, and no unit was restarted.

## ATTENTION
1. `unknown` still NEVER claims a DOWN, and that is not an oversight to tidy up later. A failed
   measurement dressed up as an observed outage is what trains a reader to discount the next alarm.
   The new row says what was actually read — "not determinately healthy for N passes, last reading
   `unknown`: <why>" — and the fix is that it is reported AT ALL, not that it is reclassified.
2. `restarts` in `daemon.json` is systemd's `NRestarts` and MUST stay that. It is an event counter,
   it reads 0 through any outage nobody tried to restart, and the cure is the separate
   `last_outage_seconds` / ledger fields — never a redefinition of that field, which would silently
   change what every existing reader of it believes.
3. `RBTV_WATCHDOG_NOTIFY_FILE` now gates the dead-man as well as the owner DM, and it is checked
   BEFORE the URL. A real healthchecks endpoint pinged by a probe or a rehearsal is a dead-man that
   can never fire — its whole signal is the ABSENCE of a ping, so any test path that could reach it
   silently disarms it for the length of its own period. `--dry-run` pings nothing for the same
   reason.
4. The alarm route shells out to `node`. This tool is otherwise pure Python stdlib on purpose —
   it has to run when everything else is down — so the shim call is wrapped, never raises, and a
   failure is ledgered and retried rather than stamped as alarmed. Do not "simplify" that by
   letting the subprocess error propagate: the pass that dies is the pass that was raising an alarm.
5. `daemon_health_streak()` is called from `daemon_verdicts()`, which a `--dry-run` invokes with
   `persist=False`. Anything added there must honour the `dry` flag on EVERY side effect (ledger
   write, ping, alarm) — a diagnostic verb with a side effect on the owner's inbox or on the
   dead-man's period is a verb nobody dares run.
- unknown still never claims a DOWN — the fix is that it is reported at all, not reclassified
- RBTV_WATCHDOG_NOTIFY_FILE gates the dead-man before the URL: a real check pinged by a test can never fire
