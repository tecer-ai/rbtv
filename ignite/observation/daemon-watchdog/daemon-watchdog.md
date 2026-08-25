# daemon-watchdog — the ignite LIVENESS surface (CMP-28)

A tiny, agentless, independent watchdog: a systemd user timer firing one deterministic
pass — `tool/rbtv-ignite-watchdog` — that PROBES the deployment, RESTARTS through the
services' own units what is down, and NOTIFIES the owner's chat DM only when it acted or
when a restart did not restore the subject. Silence means healthy.

The component's contract, its three invariants and its differentiation from every
neighbour live on the registry record `CMP-28-daemon-watchdog` in the merge-refactor
campaign's `system-definition/architecture/`. Not restated here (`PRIN-11`).

## What it is NOT, in one line each

| Not | Because |
|-----|---------|
| the daemon's own reconcile loop | that runs INSIDE the ignite daemon (`engine/reconcile.js`), so it can watch everything except ignite being down — the hole this fills |
| the scheduled probe suite | that grades CORRECTNESS on an hourly sweep; this grades LIVENESS every 60s and restores it |
| `Restart=on-failure` | unit-level restart policy catches a crashing process, not a hung one, a dead timer, or a service that exited cleanly into wrongness |
| the daemon-operator | that is the OPERATOR surface a human or a script drives by hand. This CALLS it — the restart-and-verify implementation is not written twice |

## The probe table

Three rows. Each is `probe → restart action → notify condition`, and the notify condition is
identical on every row: **acted, or acted and it did not come back.** Nothing notifies on green.

| Row | Probe | Restart action |
|-----|-------|----------------|
| `daemon` | `POST /` `{intent:"inspect", payload:{target:"daemon"}}` at the gateway with a Bearer token. Connect failure / timeout / non-200 = **down**. HTTP 401 = **alarm**, never down: the daemon is up and answering, the token is not accepted — restarting cannot fix that and would loop | `RBTV_IGNITE_UNIT=<daemon unit> rbtv-ignite-daemon restart`, **through the restart gate below** |
| `bridge` | `is-active`, AND the newest Socket-Mode lifecycle line in the last 200 journal lines. `active` only proves the Node process exists — Slack's socket can die under it. The bridge's own `reconnect()` is the first line of self-heal, so what this catches is that **backoff loop being stuck**: newest marker is a reconnect failure with no later hello. Neither marker present is NOT a fault; a healthy bridge is quiet | `RBTV_IGNITE_UNIT=<bridge unit> rbtv-ignite-daemon restart` |
| `probe-suite` | `<workspace>/.rbtv/runtime/probe-suite/latest.json`: `now - fired_at > stale_after_seconds`. **Liveness first, then correctness**: a LIVE artifact whose `verdict` is anything other than `GREEN`/`UNKNOWN` is an **alarm**, never a down — a failing or ungraded suite is not a liveness problem and no restart fixes it. That covers `RED` (`d-probe-suite-verdict-delivery`, 2026-08-10) and the runner-grade-broken set — `ERROR` · `COVERAGE-MISMATCH` · `ARTIFACT-PATH-MISMATCH` · `ARTIFACT-MISSING` · `INCOMPLETE` (owner ruling 2026-08-11), which carry a `note`/`error` instead of a `failed` count and were previously reported as healthy | `RBTV_IGNITE_UNIT=<timer> rbtv-ignite-daemon restart` — see § The row that used to bypass the operator |

## The daemon row's RESTART GATE — the one place this component interprets before it acts

Owner ruling 2026-08-14 (`hand-notes/daemon-issues.md` §2 ratification). **Amends CMP-28
invariant 2 for this row only**: the `daemon` row now consults evidence and may WITHHOLD its
restart. Everything else still probes, restarts and reports without interpreting.

**Why.** `probe_daemon()` grades an unanswered 10s gateway call as `down`. But the daemon parks
its event loop in `execFileSync` under load, so an unanswered call is an expected condition of a
**busy** daemon and no evidence at all of a dead one. On 2026-08-14 that mapping fired **57
`restart rc=0` passes against a daemon that was alive the whole time**, and each restart reaped
the shared tmux server — every pane on the box, including the owner's live sessions. The
disproving datum (`daemon_identity()`) was already in the file, one step *downstream* of the act.

Three gates, in order, before any `restart_via_operator(DAEMON_UNIT)` on a `down` verdict:

| Gate | Rule |
|------|------|
| **Liveness** | `daemon_identity()` says `ActiveState=active` with a live `MainPID` ⇒ **alarm, never restart**. This alone would have prevented all 57. `stopped` and `unknown` fall through — `unknown` is a measurement failing and must not *authorize* an act either, so it still has to spend the strikes |
| **3 strikes** | a restart needs `RBTV_WATCHDOG_STRIKES` (default 3) **consecutive** failed passes, counted in `.rbtv/runtime/watchdog/failcount.json` — its own file, written through the tool's one atomic state-file path, because the alert-dedupe `state.json` is cleared on every green pass. One `up` verdict resets the streak |
| **Backoff** | within `RBTV_WATCHDOG_RESTART_BACKOFF_SECONDS` (default 600) of a restart, a still-`down` verdict is REPORTED, not re-restarted. The journal showed `reprobe=down` immediately after each of the 57: the remedy was visibly not working and was re-applied anyway |

**The restart lever stays** — a unit systemd reports `stopped`, with the strikes spent and no
recent restart, is still restarted. It is not behind a flag. A gate that swallowed that case
would leave the box unmonitored in exactly the case monitoring exists for.

⚠ **The gate sits on the ACTION path, between the verdict and the operator call** — never on the
notify path. The 6h repeat-suppression window gates the DM leg only, which is structurally
downstream of the restart and can therefore never throttle an act.

A `--dry-run` restarts nothing and so never reaches the gate: the counter is not consumed.

## The fourth row: daemon IDENTITY — RESTARTED · CRASH-LOOP · IDENTITY · STALE CODE

The three rows above answer *is it up*. This one answers *is it the SAME one, and is it running
the code on disk* — the questions `ignite/coord/watch.py` used to answer before it was deleted
(task 7.35, run decision D8), and which nothing else in the repo asks.

**Why it could not just ride the `daemon` row.** That row asks the GATEWAY, and the gateway's
answer carries `pid` / `uptime_ms` / `last_tick` and **no identity that can be correlated across
passes**. A pid printed and compared to nothing is how a swapped-out process reads as continuous
health. So this row reads systemd for the daemon unit — one `systemctl --user show` per pass —
and compares it against the previous pass's reading on disk.

| Verdict | Decided by |
|---------|-----------|
| **RESTARTED** | the unit's `InvocationID` differs from the previous pass's. Keyed on the NEW invocation, never on a change record existing, so one restart is announced exactly once — including a restart that happened while the watchdog itself was down |
| **CRASH-LOOP** | systemd's own `NRestarts` CLIMBING across passes. A steady outage is binary and is announced once; a crash loop is monotonic (2026-07-27: `NRestarts=32`, climbing every 5s, found by hand) and re-announces while it worsens. Read from systemd's counter, never counted from this pass's sampling — a 60s watchdog counting a 5s loop would undercount by two orders of magnitude |
| **IDENTITY** | `MainPID` **and** `InvocationID` compared against the previous pass — not merely printed. A pid that moved under an unchanged invocation is reported as CHANGED, never folded into "same" |
| **STALE CODE** | `.rbtv/runtime/daemon-code.json` (written at boot by `ignite/server/code-fingerprint.js`) correlated **`InvocationID`-FIRST**, then the named files re-hashed from disk |

**Two rules that are load-bearing and must not be "simplified".**

* **`--user` is in the argv, not in a comment.** The unit is user-scoped, and the SYSTEM bus
  answers `LoadState=not-found ActiveState=inactive MainPID=0 exit 0` — byte-identical to the user
  bus's answer for a unit that genuinely does not exist. ⇒ `not-found` is reported **UNKNOWN, never
  absent**, and UNKNOWN never pushes a DM: a measurement failing is not an event.
* **Identity before bytes, three verdicts never collapsed.** The boot marker is a FILE and outlives
  the process that wrote it. Hashing first would return a false `current` across a
  restart-without-redeploy, so a marker whose `InvocationID` does not match the live unit is
  `unknown` — never `stale`, never `current`.

It is a REPORT row and sits **outside the restart table on purpose**: no restart fixes any of the
four, and the `daemon` row already owns the only restart lever this unit has (CMP-28 invariant 2 —
probe · restart · report; the sole interpretation this component performs is the `daemon` row's
restart gate above). Its alert texts carry their dedupe key **before** the
em-dash (`[restarts N]`, `[inv X]`), because the pass-level dedupe fingerprints on the head of each
alert: without the key a climbing crash loop and a second restart would both read as an unchanged
repeat and stay suppressed for the whole re-alert window.

`--dry-run` reads these verdicts and **persists nothing** — consuming the prior-pass identity would
swallow the very restart the next real pass exists to announce.

**The former `goal-watcher` row is GONE (2026-08-21).** `goal-watcher` watched the periodic queue row of
`jobs/goal-watcher-job.py` (CMP-21). That row was dequeued 2026-08-17, the arm was scoped off
the pass the same day, and on 2026-08-21 the program itself was deleted under the owner ruling
*"if the program is dead, delete it — there must be no dead code"*. The arm, its
`RBTV_WATCHDOG_WATCH_JOB` variable and `probes/probe-watchdog-goal-watcher-arm.py` went with it.
Goal-level health is now the daemon's own per-goal reconcile pass (`engine/reconcile.js`, D1/D15),
which is INSIDE the daemon and therefore covered by the `daemon` row above. Four rulings died with
the arm and are recorded here only so nobody re-derives them: the job had no systemd unit of its
own (the only lever was a full daemon restart); its overdue bar was read from the queue row's own
`interval_seconds`, never written here; NOT SCHEDULED was an `alarm`, never a `skip` (owner ruling
2026-08-11); and an N-consecutive-failure outcome alarm was ruled OUT (2026-08-15) because the job
was deliberately red against a seatless goal. `RBTV_WATCHDOG_TARGETS` survives as the test-override
hook and as the recorded-disarm surface for whatever row is disarmed next.

## The row that used to bypass the operator, and why it no longer does

`rbtv-ignite-daemon`'s act verbs verify SURVIVAL: they re-read `MainPID` after a settle
window and fail loud when it moved or is zero. A `.timer` unit has no `MainPID` — it is
always 0 — so that check could never hold for the probe-suite row, measured on a throwaway
timer 2026-08-08 (wrapper exit `1`, *"did not survive 2s — MainPID 0 -> 0"*; bare
`systemctl --user restart` exit `0`), and that row called `systemctl` directly. Commit
`7127713` made the wrapper judge non-service units on `ActiveState` alone, with the unit
type read from `systemctl show -p Id` rather than the name string. Re-measured on a
throwaway timer the same day: wrapper exit `0`, unit active after. **The bypass is deleted,
not kept** — every row now goes through the operator, and there is exactly one
restart-and-verify implementation (`PRIN-11`).

## Silence, and how it survives a subject that cannot be restored

Invariant 3 says notify on action or failure-to-restore, never on a green pass. At a 60s
cadence a permanently-unrestorable subject would honour that rule and still DM the owner
~1440 times a day — the invariant violated by volume rather than by rule. So the pass keeps
a small state file (`<workspace>/.rbtv/runtime/watchdog/state.json`) holding the previous
alert's fingerprint, when it first fired, and when the owner was last told; it re-notifies
when the fingerprint CHANGES. An all-green pass clears it, so the next occurrence of the
same fault does notify.

**Dedupe alone fails the other way, and that is the trap this component is most likely to
fall into.** A condition that never clears — the gateway sender not yet minted, a subject
that never comes back — would send ONE DM and then be silent forever on the only channel
that pushes. Silence is this component's word for healthy, so a stuck watchdog would be
indistinguishable from a working one. An unchanged alert is therefore suppressed for at
most `RBTV_WATCHDOG_REALERT_SECONDS` (default 6h → at most 4 DMs/day), then re-sent marked
`STILL UNRESOLVED, first alerted Nm ago`. The suppression window is measured from the last
DM, the "first alerted" figure from the first — so a re-alert does not then fire every pass.

## Verbs and exit codes

`rbtv-ignite-watchdog [--dry-run]` — one pass, then exit. `--dry-run` probes and reports
what it WOULD restart without restarting anything, **and cannot DM the owner under any
verdict**: it prints the message it would have sent and returns not-sent, so the dedupe
state is never consumed either. The guard sits on `notify()` itself rather than on the
`--dry-run` branch in `main()`, because an `alarm` row reaches the notify block without
passing that branch — which is how a `--dry-run` DM'd a real person until 2026-08-14.
Guarded by `probes/probe-watchdog-dry-run-no-dm.py`.

⚠ **AMENDED 2026-08-15, owner ruling R1: an alarm is NOT a systemd failure.**

| Exit | Means |
|------|-------|
| `0` | the pass RAN — all green, it acted, a subject is still down, an alarm stands, the notify failed. Every one of those is a completed pass |
| `2` | usage error |
| anything else | **the watchdog itself broke** (an unhandled exception) |

The verdict of a pass is carried by the owner DM and by the state file
(`RBTV_WATCHDOG_STATE`, written on EVERY alerting pass — including a suppressed repeat and
a failed notify), never by the exit code. WHY R1: the timer re-fires every ~60s, so an
alarm reported as exit `1` made systemd log `rbtv-watchdog.service: Failed with result
exit-code` once a minute for as long as the alarm stood — `systemctl --user --failed` was
useless as a signal for exactly the window something was wrong, and a watchdog correctly
alarming was indistinguishable at a glance from a watchdog that had crashed.

Nothing is whitelisted in the unit (`SuccessExitStatus` was rejected, not forgotten): the
exit-0 change belongs on the tool side precisely so a real failure — this component dying —
still shows FAILED. A blanket whitelist would have masked that too. Guarded by
`probes/probe-watchdog-alarm-exit-zero.py`, whose control arm proves the nonzero path is
still reachable — without it "exit 0" would be indistinguishable from an exit code nothing
can move.

## Environment

Every per-instance value is resolved at runtime; nothing is baked into the code.

| Variable | Default |
|----------|---------|
| `RBTV_WATCHDOG_WORKSPACE` | CWD — the workspace root that carries `.rbtv/` |
| `RBTV_WATCHDOG_GATEWAY` | `http://127.0.0.1:7431/` |
| `IGNITE_WATCHDOG_TOKEN` | unset. **No fallback to another sender's token, deliberately** — borrowing one would file every probe under the wrong sender id in the gateway's audit columns AND would silently satisfy the mint that § Enabling this thing exists to force. Absent = `alarm`, re-alerted on the ceiling below until someone mints it |
| `RBTV_WATCHDOG_DAEMON_UNIT` · `_BRIDGE_UNIT` · `_PROBE_TIMER` | `rbtv-ignite.service` · `rbtv-chat-bridge.service` · `rbtv-probe-suite.timer` |
| `RBTV_WATCHDOG_TARGETS` | all three rows. **The test-override hook** — mirrors `RBTV_IGNITE_UNIT`: a probe scopes the pass to one row and points that row's unit variable at a throwaway unit, instead of editing the real probe table. **Also the recorded-disarm surface**: set persistently in `units/rbtv-watchdog.service` to omit a row that is disarmed ON PURPOSE, with the reason commented above it. Refuses an unknown name with exit `2` — never a silent no-op |
| `RBTV_WATCHDOG_OPERATOR` | the sibling component `operator/daemon-operator/tool/rbtv-ignite-daemon`, else `rbtv-ignite-daemon` on PATH |
| `RBTV_WATCHDOG_STATE` | `<workspace>/.rbtv/runtime/watchdog/state.json` |
| `RBTV_WATCHDOG_DAEMON_STATE` | `<workspace>/.rbtv/runtime/watchdog/daemon.json` — the prior-pass daemon identity the RESTARTED / CRASH-LOOP / IDENTITY verdicts compare against. Its OWN file: `RBTV_WATCHDOG_STATE` above is cleared to `null` on every all-green pass, which is exactly the pass a restart has to be detected ACROSS |
| `RBTV_WATCHDOG_REALERT_SECONDS` | `21600` (6h) — how long an UNCHANGED alert stays suppressed before it is re-sent. `0` re-notifies every pass |
| `RBTV_WATCHDOG_NOTIFY_FILE` | unset. **Test double** — when set, notifications are appended there as JSON lines and Slack is never called |
| `RBTV_WATCHDOG_NOTIFY_PREFIX` | empty — prepended to every message; how a TEST DM is marked as one |
| `RBTV_WATCHDOG_LEDGER` | `<workspace>/.rbtv/runtime/watchdog/outage-ledger.jsonl` — the append-only outage ledger below |
| `RBTV_WATCHDOG_DEADMAN_URL` | unset. The healthchecks-style check URL the dead-man pings. **No default and no hardcoded endpoint**: unset means the out-of-band channel is NOT armed, and the pass says so on its own row rather than skipping silently |
| `RBTV_WATCHDOG_ALARM_SHIM` | the sibling `tool/watchdog-alarm.js` — the route to the ONE alarm emitter |
| `RBTV_WATCHDOG_NODE` | `node` — the interpreter that runs the shim |
| `RBTV_SYSTEM_CHANNEL_ID` | unset. The system channel daemon-level events post to [T5-R1]. Read by the shim; absent = the alarm is refused there and the refusal is ledgered, never swallowed |
| `SLACK_BOT_TOKEN`, `IGNITE_CHAT_BRIDGE_CONFIG` | the notify credential, and the bridge's own config — read ONLY to resolve WHO the owner is (explicit `bus_ferry_dm_user`, else the first allowlist entry), so the two components can never disagree about it. `SLACK_BOT_TOKEN` is ALSO what arms the alarm shim's transport (below); absent, the alarm is minted `pending-delivery` and says so |
| `SLACK_API_BASE` | `https://slack.com/api` — the shim's Slack base, so a probe can point it at a mock. Never a default that reaches a real workspace from a test |

**The notify client is the watchdog's own two Slack calls** (`conversations.open`, then
`chat.postMessage`), not the bridge's. It has to be: this must reach the owner when the
chat bridge is the thing that is down, so it can depend on neither the bridge process nor
its bus-poll loop. The accepted consequence is stated plainly — if the bridge is down at
the instant of the alert, Slack itself may be unreachable and that pass's DM fails; the
NEXT pass 60s later re-attempts, so the message is delayed by one cadence, never lost.

## The three BIT-7 duties: ledger · N-fail alarm · dead-man [T4-R9, C-17]

Added 2026-08-25. The incident: on 2026-08-19 the ignite daemon was down
18:18:44Z→21:24:59Z (3h05m) and BOTH halves of this component were silent — no ledger row
and no owner alarm. The diagnosed mechanism is recorded at the top of
`tool/rbtv-ignite-watchdog` beside the code that fixes it, in one sentence here:
**the four identity verdicts fire only on a DETERMINATE `stopped`, and `_daemon_change()`
refuses to claim a change when either side is `unknown` — so an outage whose identity read
could not be resolved determinately produced no note and no change record at all.**
`unknown` was a silent state. The proof is the artifact the incident left behind: at 21:30,
six passes after the daemon returned at 21:23:39 on a fresh invocation id, `daemon.json`
still carried no `notified_daemon_invocation` key, which is reachable only when
`_daemon_change()` returned `None`, which requires the previously persisted reading to have
been non-determinate.

**What is KEPT.** `unknown` still never claims a DOWN. The calibration in
`check_daemon()` is deliberate and unchanged: a measurement that failed must never be
dressed up as an outage observed. What changed is that it is now reported AT ALL, in its own
words, on its own row.

### 1. The persistent outage ledger — `ledger()`

`.rbtv/runtime/watchdog/outage-ledger.jsonl`, append-only, one JSON object per line, never
rewritten. `daemon.json` is a SNAPSHOT — it can only say what is true this pass — so it can
never answer "what happened between 18:18 and 21:24". This file can, and it survives both
watchdog and daemon restarts. Decisions written:

| `decision` | Written when |
|---|---|
| `restart-withheld` | EVERY withheld restart, with the arm (`unit-alive` · `backoff` · `strikes`) and the reason in plain words. **This is the row whose absence made the 3h05m invisible** — a ledger that recorded only actions is silent in exactly the case it exists for |
| `restart-allowed` | The strikes are spent and the gate permits the restart |
| `restart-taken` | The restart ran, with its `rc` and the REPROBE verdict — every row, not only `daemon` |
| `observed-not-healthy` | Every pass the daemon unit did not read determinately running, with the consecutive count and the threshold |
| `alarmed` / `alarm-emit-failed` | The N-fail alarm reached the emitter, or did not — a failed emission is a fact, and NOT stamping the episode is what makes the next pass retry |
| `recovered` | The unit reads determinately running again, carrying `outage_seconds` — the duration task #113 asked for, recorded as a first-class field instead of left derivable by hand from two `since` stamps |

`ledger()` NEVER raises. Record-keeping that can abort the pass would be a new way for this
component to go blind.

### 2. The N-consecutive-fail alarm — `daemon_health_streak()`

N = `RBTV_WATCHDOG_STRIKES` (3), the threshold this component already had; spec-owner-io §8
keeps it. N consecutive non-determinately-healthy daemon readings raise ONE alarm **even
when the restart is withheld** — which is the whole point, since the withheld arms are the
ones that never acted and therefore never announced.

It is routed through the ONE alarm emitter (`ignite/observation/emitter.js`) as an ordinary
caller, via the sibling `tool/watchdog-alarm.js` shim — this tool is Python and the emitter
is JavaScript, and a second alarm path in Python is exactly the defect the emitter exists to
end. Signature class `watchdog-daemon-unhealthy`; `immediate: true`, because spec-owner-io
§9.2 makes system-health alarms digest-exempt for their first post [CF-9, T5-R11]. The post
goes through the durable outbox, so an unreachable Slack leaves a queryable
`pending-delivery` record rather than a lost alarm [C-17].

**The shim's transport is WIRED** (integration pass, 2026-08-25). `resolveSend()` builds the
chat bridge's OWN sender (`bridges/chat/slack-socket-mode.js#sendToOwner`, one outbound
`chat.postMessage` on `SLACK_BOT_TOKEN`) rather than composing a second `chat.postMessage`
here; `createSlackSocketMode` opens nothing until `start()`, which this process never calls,
so no Socket-Mode session is held. Two walls stand in front of it, in this order:

1. `RBTV_WATCHDOG_NOTIFY_FILE` — the "send nothing" sink — is checked BEFORE the token, for
   `deadman_ping()`'s reason: a probe or a rehearsal that reached real Slack because the shell
   happened to carry a bot token would post into the owner's workspace from a test.
2. No `SLACK_BOT_TOKEN` is a refusal, not a drop: the record is minted `pending-delivery` with
   the reason on the row, which is the behaviour every prior pass had.

Proof: `probes/probe-watchdog-alarm-transport.js` (mock Slack on an ephemeral loopback port —
delivered-with-ts, pending-delivery-without-token, the dry wall beating a present token, and
both pre-existing refusals unchanged).

ONE emission per episode, re-armed on recovery: §9.2 gives one alarm per condition-signature
and hands re-surfacing to the 2-hourly system digest, so a second emission would be volume,
not coverage.

### 3. The non-Slack dead-man — `deadman_ping()`

The CP1-ruled channel (spec-owner-io §8): a healthchecks-style HTTPS ping to
`RBTV_WATCHDOG_DEADMAN_URL`, fired on every pass that reads the daemon determinately
healthy. **The signal is the ABSENCE of a ping** — the check service alerts out-of-band
(email/SMS, configured on that check) when one is missed. It is the only alert still
standing when Slack is unreachable, when the outbox cannot deliver, and when this watchdog
is itself dead — the branch no in-band alarm can cover.

**Dry mode is a hard wall, checked before the URL.** `RBTV_WATCHDOG_NOTIFY_FILE` set → no
request is ever made and a `{"deadman": "would-have-pinged", "url": …}` record is appended to
that file instead. `--dry-run` likewise pings nothing. A real check pinged by a test is a
dead-man that can never fire.

## Enabling this thing — the gate, in order

The units ship **installed and DISABLED**. Enabling is a deliberate act, and it has a
prerequisite that fails silently if skipped.

1. **Mint the watchdog's gateway sender** — the sanctioned way, per the deployment
   runbook's § Sender registry: generate a token on this box, hash it with
   `printf %s "$T" | sha256sum` (no trailing newline), append a row to the sender registry
   with `kind: agent`, and put the plaintext in the machine's gitignored env surface as
   `IGNITE_WATCHDOG_TOKEN`. Never a CLI flag — argv leaks into process lists.
2. **Restart the daemon.** The sender registry is read ONCE at startup; there is no live
   reload. Until this happens the new token is not accepted and every pass reports
   `alarm: 401 AUTH_REFUSED`.
3. Substitute and install both units from `units/`, then
   `systemctl --user daemon-reload && systemctl --user enable --now rbtv-watchdog.timer`.
4. `systemctl --user list-timers rbtv-watchdog.timer` — confirm `NEXT` is populated.

⚠ **Steps 1–2 are the gate, not step 3.** Enabling the timer before the sender is minted and
loaded produces a watchdog that alarms on its own credentials. It fails LOUD by construction:
there is no fallback to another sender's token (so it cannot quietly run under a borrowed
identity), and the re-alert ceiling re-sends the standing alarm every 6h (so it cannot go
quiet under repeat-suppression and read as a healthy system).

## Proving it

`probes/probe-watchdog-staged-failure.py`, run through the enumerator
(`node deploy/probe-suite.js --only probe-watchdog-staged-failure`), stages a real failure
end to end: down → detected → restarted → notified → recovered, then a clean pass proven
SILENT — and the silence proven BOUNDED: an unchanged alert suppressed, then re-sent past
the re-alert ceiling marked `STILL UNRESOLVED`. It creates and removes its own throwaway
unit and routes notify to a test double;
**it never starts, stops or restarts the three live units, and never messages the owner** —
the same non-interference guarantee `rbtv-ignite-daemon selftest` established for this
capability family. A real-DM confirmation is a one-time manual step
(`RBTV_WATCHDOG_NOTIFY_PREFIX` marks it), never part of the repeatable check.

`probes/probe-g188-daemon-identity.py` proves the fourth row — 96 checks over the four
verdicts, every systemd answer substituted and every file in a temp dir, so it runs on any
host and never touches the live unit or the real `.rbtv/runtime/`. It carries a red-first
control of its own: `RBTV_WATCHDOG_TOOL_PATH=<another copy>` points it at a different
watchdog, and a watchdog missing the verdicts is reported as four named red arms rather than
one traceback.

`probes/probe-runner-grade-verdicts.py` proves the `probe-suite` row's grading — a fixture
`latest.json` per verdict (`RED`, `ERROR`, `COVERAGE-MISMATCH`, `GREEN`, `UNKNOWN`) with a
fresh `fired_at`, asserting alarm/alarm/alarm/up/up and that each alarm message names its
verdict without an unresolved placeholder (the broken verdicts carry no `failed` count, so
the RED wording cannot be reused for them). Same red-first control: against a pre-widening
copy via `RBTV_WATCHDOG_TOOL_PATH` the two runner-grade rows go red.

`probes/probe-watchdog-bit7-silence.py` is the BIT-7 regression — 20 checks pinning the
2026-08-19 silence itself. It substitutes a non-determinate identity reading carrying NO
restart count (the incident's own shape, and why `restarts: 0` stayed clean), drives the
pass directly, and asserts the RED and GREEN halves in one run: the pre-fix path
(`check_daemon`) is still SILENT on that reading, while the ledger, the emitter registry and
the durable outbox all now carry the condition. It also proves the withheld-restart rows,
the recorded outage duration against the incident's real 11 115 seconds, and that the
dead-man's configured URL — a closed local port — is never reached in dry mode. No real
unit, gateway, endpoint or `.rbtv/runtime/` is touched.

`probes/probe-watchdog-alarm-transport.js` proves the shim's SEND — the seam that stood open
while `resolveSend()` was a stub. Mock Slack on an ephemeral loopback port (`SLACK_API_BASE`),
a scratch workspace per leg, and a clean environment per run so an ambient `SLACK_*` in the
operator's shell cannot decide what it measures: with a token the alarm reaches
`chat.postMessage` in the system channel and the outbox flips to `delivered` carrying Slack's
own ts; without one it is `pending-delivery` with the reason on the row; with
`RBTV_WATCHDOG_NOTIFY_FILE` set NOTHING is sent even though a token is present; and both
pre-existing refusals (no `RBTV_SYSTEM_CHANNEL_ID`, a half-composed alarm) still exit 1 having
posted and minted nothing. Red-first control: against the pre-wiring `resolveSend` stub the
delivery arms go red. No real unit, endpoint or live outbox is touched.

## Retirement

Nothing retires this yet. It is not a stand-in: unlike `daemon-operator`, it has no
successor in the `rbtv` CLI and no home waiting for it in the `CMP-5` component layer — a
watchdog is a scheduled act, not a verb a human types. If the `rbtv` CLI ever grows a
`rbtv ignite watchdog run` verb it should **exec this script** the way
`rbtv ignite daemon` execs the operator, which would make this folder a dependency rather
than a predecessor. Retire it only when nothing execs it and no timer fires it.
