# 20260825-c-one-alarm-emitter-frozen-invar — One alarm emitter + frozen invariant [T4-R10, T1-R15]

kind: creation
component: engine
date: 2026-08-25
commit: bd954a96,3d653ce9
deployed: no
pin: ignite/observation/frozen.selftest.js
components: server,bridges

## Motivation
[T4-R10] settles alarms behind ONE schema-enforced emitter, and C6 names the sensor/alarm class as
NEW work: three disjoint liveness predicates and no single alarm composer. Each call site that
noticed a condition wrote its own Slack text with its own dedup and no schema. The frozen pager
(`server/ticker/goal-stall-alarm.js`, deleted 2026-08-24) is the worked example: an alarm reading
`frozen: undefined` stood for 13 hours, its process-lifetime dedup Map was wiped by every daemon
restart so it re-paged what it had already paged, and it stayed silent through five real freezes.
[T1-R15] separately settles that "frozen" is a SCHEDULER INVARIANT, not the tick-silence timer the
same batch deleted.

## Design
Two modules under the new `ignite/observation/` component (`spec-component-map`'s home), and no
third. `emitter.js` composes every alarm; `frozen.js` is one ordinary caller of it.

The schema gate THROWS. `condition`, `subject` (a concrete `{type,id}`), `evidence_pointer` and
`what_would_clear_it` are required (spec-owner-io §9.1); absence raises at the emitting call site and
posts nothing, because a half-composed alarm on the owner's phone is indistinguishable from a real
one while a throw is a stack trace naming the line that failed to say what it observed. `unknown` is
a legal VALUE of `what_would_clear_it`; absence is not. A fifth field, `immediate`, is required
beyond the spec's four: system-health alarms are digest-exempt [CF-9] and a caller that never states
which kind it is has left that exemption to be guessed. Rejected: a registry of system-health
signature classes the emitter would consult — it would have made the sibling watchdog seat a
special caller instead of an ordinary one, which is the property the single-emitter ruling is for.

The signature is condition-class + subject and deliberately NOT the condition text: the text is what
change-detection compares, so folding it into the key would mint a new row per reworded observation
and dedup would silently stop deduping. The registry is a PERSISTED JSON file, never a Map — that is
the half of the deleted module's design that does not carry over.

`frozen.js` is a conjunction, every arm positively true: `running` + no live seat + no eligible
launch + no open ask + not paused. Rejected: the inverse arithmetic ("everything except the classes
I know are harmless"), which is precisely what re-lit the 10-second Slack loop in the deleted alarm
(`engine/20260820-i-frozen-goal-alarm-fix`). Liveness is read from the supervisor registry and
nowhere else [T4-R8]; every other fact is HANDED IN by the caller that already computes it
(`supervisor/owed.js` answers `owed`), so this module is a reader of scheduler facts, not a second
scheduler.

## How it works
`createAlarmEmitter({ storePath, post, systemChannelId, now })` returns `emit` / `clear` /
`readOpenConditions` / `reload`. `emit` validates, keys on `signatureOf()`, and on an already-open
signature returns `{posted:false, reason:'deduped'}` — re-posting only when the condition TEXT
changed or when the caller's `repeat_every_ms` window elapsed, and either way updating
`last_emitted_at` on the SAME row. `post` is the outbox's own `post` (`bridges/chat/outbox.js`) with
`kind:'alarm'` stamped by the emitter, never the caller, so a bridge outage leaves a
`pending-delivery` record instead of a lost alarm [C-17]. `clear(signature)` is silent: the row just
stops appearing in the digest. `readOpenConditions()` returns
`[{signature, condition, subject, first_emitted_at, evidence_pointer}]` — the exact shape
`bridges/chat/system-digest.js` documents; `subject` flattens to the bare id there because the digest
row already reads as a sentence.

`createFrozenInvariant({ emitter, frozenWindowMin, registryFile, holdsPath, now })` exposes
`check(observations)`. Each observation carries the nine facts `OBSERVATION_FIELDS` names and is
validated the same throwing way. `predicate()` tests the two [C-5] exclusions FIRST
(`provider_backoff_waiting`, `reroute_pending`), then the goal word, paused, eligible launch, open
ask, and only then counts live registry rows for that goal. The hold clock is persisted beside the
registry, so a restart mid-freeze does not restart the window. On the window elapsing it calls
`emitter.emit` with `repeat_every_ms: HOURLY_REPEAT_MS` — the hourly repeat is therefore one row with
a rising `emission_count`, not one row per hour. `frozenWindowMin` is REQUIRED with no fallback:
spec-recovery §2.1 puts the five recovery knobs in one config file and forbids a hardcoded default,
even a silent one.

## Consequences
`ignite/observation/` is a new component: `ignite/module.md` gained its row in both tables and the
component carries `component.md` + `exposure.csv`. No README — `component.md` is the entry-point doc
and a second copy of the same facts would drift (PRIN-11).

The recovery config reader is NOT landed: no `recovery.json` loader and no
`ignite/supervisor/recovery.defaults.json` seed exist at this commit, so `frozen_window_min` has to
be supplied by whoever wires the invariant into the tick driver. Wiring itself is not done here —
nothing calls either module yet; `bridges/chat/system-digest.js` still defaults `readOpenConditions`
to an empty reader until a caller passes the emitter's.

Four prose references to the deleted `goal-stall-alarm.js` / `alarmOnStall` were repointed in the
same commit set (`engine/seeding.js` x3, `server/ticker/ticker.js`, `server/heart/heart-store.js`) —
comment-only, no behaviour change. One of them read as a PRECEDENT for a process-lifetime dedup Map
and now says the opposite.

## Verification
`node ignite/observation/emitter.selftest.js` — ALL PASS, exit 0: eight cases, including one arm per
required field dropped (each throws, names the field, posts nothing and registers nothing), dedup
(two emits → one row, one post), dedup read back from DISK through a SECOND emitter instance
(the restart case), condition-change re-post, the repeat window at 59 and 61 minutes on an injected
clock, and the digest read shape key by key.

`node ignite/observation/frozen.selftest.js` — ALL PASS, exit 0: FIXTURE A (running, no live seat, no
eligible launch, no open ask, not paused, held past 15 min on an injected clock → exactly one alarm,
one row, and two further passes inside the hour stay silent) against FIXTURE B (identical facts plus
provider-backoff → zero alarms, zero rows) as a discriminating pair; plus reroute-pending, each of
the four arms suppressing alone, a REAL live pid on the supervisor registry suppressing and the same
goal alarming once that row is dropped, the hourly repeat, and the persisted hold surviving a
rebuilt instance. Red arm run by hand: deleting the `provider_backoff_waiting` line from a scratch
copy reddens FIXTURE B (exit 1) while FIXTURE A stays green.

Touched-module probes: `server/heart/probes` 23/23 GREEN, `server/ticker/probes` 27/27 GREEN,
`engine/probes` 14/15 with `probe-foreground-carrier` RED on a wall-clock arm (3028ms against a
2000ms budget on a loaded box; its seat-failed arm passed on re-run) — not this change, whose every
edited line outside the new folder is a comment.

Deployed: no. Worktree `5-workbench/rbtv-redesign`, branch `ignite/core-redesign`; the live repo was
not touched and nothing was restarted.

## ATTENTION
1. Do not add a second emitter for a "special" alarm class. The watchdog, and anything after it, is
   an ordinary caller: pick a `signature_class`, state `immediate`, hand in the four fields. A second
   composer re-creates by construction the state [T4-R10] exists to delete.
2. Never key the signature on the condition TEXT. It is condition-class + subject on purpose — the
   text is the change detector, so a text-keyed signature mints a row per rewording and dedup dies
   silently, which is indistinguishable from working.
3. Never give `frozen_window_min` a default here, not even a fallback constant. spec-recovery §2.1
   makes the five knobs one config file precisely so a number the owner tuned cannot be overridden by
   a module constant. The HOURLY repeat is the opposite case: it is [T1-R15]'s ruling, absent from
   that file on purpose, and is not a knob.
4. The two [C-5] exclusions are tested FIRST in the predicate, before anything else, and must stay
   there. A backoff-waiting or reroute-pending lane is waiting on purpose and looks identical to
   frozen from outside; "sweep it in and filter later" is how it reaches the owner anyway.
5. `readOpenConditions()`'s five keys are a CONTRACT with `bridges/chat/system-digest.js`, which
   documents them in its own comment. Renaming one here makes the digest render an empty
   "Open conditions" section with no error anywhere.
- Alarms have ONE composer: a new alarm is an ordinary emit() caller, never a second emitter
