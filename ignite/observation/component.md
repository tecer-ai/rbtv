---
description: Read before emitting any alarm to the owner, before adding a new alarm condition, and before asking why a frozen goal did or did not page - the one schema-enforced emitter, its persisted signature registry, and the frozen scheduler invariant.
---

# observation

Alarms. Law is `1-projects/build-ignite/redesign/specs/spec-owner-io.md` §9 under
[T4-R10], [T1-R15], [CF-9], [C-5], [T5-R11], [CF-2], [F-simplicity-4]; the folder
home is `spec-component-map`'s.

Every alarm the daemon raises is composed HERE. Before this component there was no
"here": each call site that noticed something wrote its own Slack text, with its own
dedup and no schema, and the results were an alarm reading `undefined` that stood for
13 hours, a 10-second alarm loop, and a real freeze nothing paged at all.

## The four required fields, and why a throw

`emitter.js` refuses to compose an alarm missing any of:

| Field | Rule |
|---|---|
| `condition` | Plain words. Never empty, never a bare code token. |
| `subject` | A concrete `{ type, id }` — a goal, a seat, or a lane. |
| `evidence_pointer` | A path or query key a human can open. |
| `what_would_clear_it` | Plain words, or the explicit value `unknown`. |

Absence throws at the emitting call site and posts NOTHING. A missing field is the
EMITTING CODE'S bug [T4-R10]: a half-composed alarm on the owner's phone is
indistinguishable from a real one, while a throw is a stack trace naming the line that
failed to say what it observed.

`immediate` is required too, and is the one field beyond the spec's four. System-health
alarms (daemon down, provider quota, watchdog N-fail, cross-goal freeze) are exempt from
waiting on the 2-hourly digest [CF-9], and a caller that never states which kind it is has
left that exemption to be guessed. An explicit `false` is a fine answer; silence is not.

## The signature registry is PERSISTED

`signature` = condition-class + subject, and deliberately NOT the condition text — the
text is what change-detection compares, so folding it into the key would mint a new row on
every reworded observation and dedup would silently stop deduping.

One emission per open signature. A second emit of the same signature returns
`{ posted: false, reason: 'deduped' }`. It re-posts only when the condition TEXT changes,
or when the caller passed `repeat_every_ms` and that window has elapsed — and a repeat
updates `last_emitted_at` on the SAME row, never a second row.

The store is runtime state (`{workspace}/.rbtv/runtime/ignite/alarm-registry.json`, or any
path a caller hands in). The deleted `goal-stall-alarm.js` held this in a process-lifetime
`Map`, so a daemon restart re-paged everything it had already paged — and a restart is
exactly the event most likely to happen while something is wrong.

Rows carry `signature`, `state` (`open` | `cleared`), `first_emitted_at`, `last_emitted_at`
alongside the four fields, the `immediate` mark, and the channel.

## The published read interface

`readOpenConditions()` returns `[{ signature, condition, subject, first_emitted_at,
evidence_pointer }]` — the exact shape `bridges/chat/system-digest.js` documents and renders
under "Open conditions". `subject` flattens to the bare id there; the full `{ type, id }`
stays on the registry row. The digest RE-SURFACES an open condition; that is not a second
emission [T4-R10].

`clear(signature)` is silent by design. The owner is told a condition EXISTS, never that one
of a hundred transient observations went away; the row simply stops appearing in the digest.

## Alarms are one-way

Nothing here writes mail, enqueues, or touches the owed set. An alarm never counts as unread
work that wakes a seat, a master or a leader [T4-R10].

Every post goes through the durable outbox (`bridges/chat/outbox.js`) with `kind: 'alarm'`
stamped here, never by the caller — so a bridge outage leaves a `pending-delivery` record
rather than a lost alarm [C-17].

## The frozen invariant is an INVARIANT, not a timer

`frozen.js`. A goal that is `running`, with (a) no live seat, (b) no eligible launch, (c) no
open ask, (d) not paused, held for the configured window → ONE alarm saying what was
observed, repeated hourly while it holds [T1-R15]. Any one arm being false means the system
is working and there is nothing to say. The window only stops a one-tick gap between a seat
ending and the next launching from paging the owner.

**Liveness is read from the supervisor registry and nowhere else** [T4-R8]. No pane, no tick
counter, no ledger status, no transcript — a fourth disjoint liveness predicate here is the
thing C6 exists to delete. Every other fact is HANDED IN by the caller that already computes
it (`supervisor/owed.js` answers `owed`; the ask store answers `open_ask`; the goal state row
answers `paused`). This module re-derives none of them.

**Two exclusions, absolute** [C-5]. A lane waiting out a provider backoff, and a lane skipped
pending a reroute, are waiting ON PURPOSE. They look identical to frozen from outside and are
its opposite. They are excluded at the predicate, never swept in and filtered later. Nothing
here stamps `incomplete:` and nothing kills; spec-recovery excludes this designed hourly
repeat from the attempt counter for that reason.

The hold clock is persisted beside the registry, so a restart mid-freeze does not restart the
15 minutes.

`frozen_window_min` is REQUIRED from the caller and has no default, not even a silent one:
spec-recovery §2.1 puts all five recovery knobs in one config file
(`{workspace}/.rbtv/config/ignite/recovery.json`) and forbids a hardcoded fallback, so a
number the owner tuned there cannot be quietly overridden by a constant in a module. Read it
with `supervisor/recovery-config.js#loadRecoveryConfig` and hand the number in — that is the
one reader of that file, and this component deliberately is not a second one. The hourly
repeat is NOT a knob — [T1-R15] rules it, and it is absent from that file on purpose.

## Adding an alarm

Be an ordinary caller of `emit`. Choose a stable `signature_class`, say what `immediate` is,
and hand in the four fields. There is no registration step and no second emitter.

## Registered caller: the daemon watchdog [T4-R9]

Appended by `impl-alarms-watchdog`. `capabilities/daemon-watchdog` is an ordinary caller of
`emit`, and the first one from outside this process: it is Python, so it reaches the emitter
through its own sibling shim (`capabilities/daemon-watchdog/tool/watchdog-alarm.js`) rather
than through a second emitter. Nothing in this component changed to admit it.

| | |
|---|---|
| `signature_class` | `watchdog-daemon-unhealthy` |
| `subject` | `{ type: "daemon", id: <the systemd unit name> }` |
| `immediate` | `true` — system-health, digest-exempt for the first post [CF-9, T5-R11] |
| Condition | N consecutive watchdog passes on which the daemon unit did not read determinately healthy, N = the watchdog's existing strike threshold (spec-owner-io §8) |
| `evidence_pointer` | the watchdog's append-only outage ledger, `.rbtv/runtime/watchdog/outage-ledger.jsonl` — every restart decision and every WITHHELD restart with its reason |
| Emission | ONE per episode, re-armed when the unit reads determinately running again. The 2-hourly system digest re-surfaces the open condition; the watchdog never re-emits it |

The watchdog also carries the non-Slack dead-man (spec-owner-io §8) — a healthchecks-style
ping whose ABSENCE is the alert. That is deliberately NOT an alarm and never reaches this
emitter: it is the channel that has to work when this whole path, Slack included, does not.

## Registered caller: the frozen invariant's tick driver [T1-R15]

Appended by the integration pass of 2026-08-25. `frozen.js` shipped uncalled — nothing
supplied it observations and nothing read `frozen_window_min` for it. Its caller is
`engine/frozen-pass.js`, run once a cadence from the daemon loop (`server/index.js`)
IMMEDIATELY AFTER the lane watch, on the facts that pass already computed. Nothing in this
component changed to admit it.

| | |
|---|---|
| Facts | `engine/lane-watch.js#frozenFactsFor`, one observation per goal the pass actually SEEDED — the goal-state row, the pause, `pickup.enqueued` as `eligible_launch`, `countOpenAsks` as `open_ask`, and the two [C-5] exclusions off the provider lanes. A goal the pass stepped over is not observed at all |
| Window | `supervisor/recovery-config.js#loadRecoveryConfig` → `frozen_window_min`. A pass that cannot read that file arms NOTHING and says so; there is no fallback window anywhere on this path |
| Channel | `RBTV_SYSTEM_CHANNEL_ID` [T5-R1]. A goal's OWN channel id is not knowable daemon-side (the bridge holds that map, in its own process), so a goal alarm posts in the system channel — stated, not guessed. Unset ⇒ not armed |
| Delivery | The daemon resolves no Slack credential (`r-cutover-gated`), so the post is minted `pending-delivery` in the durable outbox with the reason on the row [C-17], and the owner reads the condition through the 2-hourly digest, which re-surfaces it [§9.2] |
| Suppression | A stall/latency alarm inside the window of a WATCHDOG-DETECTED daemon restart is held (task #113 criterion 2). The whole pass is suppressed, not one alarm — after a restart every goal is late for the same reason. The fact is read off the watchdog's append-only outage ledger (`engine/restart-window.js`), because the daemon's own memory is what the restart erased. The window is `RBTV_RESTART_ALARM_SUPPRESS_MIN`, deliberately NOT a ninth key in `recovery.json` (spec-recovery §2.1 closes that schema at eight and its loader refuses extras); unset ⇒ no suppression at all |
| Proof | `engine/probes/probe-frozen-driver.js` |

## The published read interface has a wired consumer

`bridges/chat/glance.js` builds an emitter instance over the registry FILE this component
writes and asks it `readOpenConditions()` — reloading before every read, because the writer is
the daemon and a constructor-time snapshot would render the alarm set as it stood when the
bridge last started. That instance is handed a `post` that THROWS: the bridge reads alarms and
never composes one, which is what keeps [T4-R10]'s single composer true across a process
boundary.

## Not this component

Liveness itself (`supervisor/`). The watchdog, the outage ledger and the non-Slack dead-man
(`capabilities/daemon-watchdog/`). The digest, the status line, the reply grammar and the
outbox transport (`bridges/chat/`). Kill triggers, attempt counters and the provider tables
(`supervisor/` + spec-recovery).
