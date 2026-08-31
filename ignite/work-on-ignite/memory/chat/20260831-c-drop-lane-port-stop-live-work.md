# 20260831-c-drop-lane-port-stop-live-work — drop-lane port: stop live work, then abandon

kind: creation
component: chat
date: 2026-08-31
commit: 8c1023afeaa45474f85a0f3a09a25ecc266e61ed
deployed: no
pin: ignite/chat/probes/probe-chat-recovery-dispatch.js
components: gateway,runtime,state-store

## Motivation
`d-recovery-drop-stops-live-work` (owner ruling, 2026-08-31): a `drop-lane` recovery reply must stop
anything still live for the `(goal, seat)` lane, THEN mark it abandoned — never the other order, and
never half-complete (a stopped-but-unmarked lane still reads OWED and gets relaunched; a marked-but-
running lane writes results into a lane the counters were told to ignore). `recovery-thread.js`
already dispatched to a `dropLane` port; `chat-bridge.js` passed none, so `call()` returned
`no dropLane port is wired` and the owner got a truthful "did not run".

## Design
The port is TWO wire calls in order, composed entirely from ports/intents this seat did not
otherwise touch or widen. Step 1 (stop) reuses two EXISTING, unmodified intents: `inspect` (target
`ticker`) to find the lane's live turn by its `workdir` (a second, disclosed copy of `heart-
store.js#enqueueHomeOf`'s path pattern — the bridge may not require heart-store at all), then
`kill-session` on that turn's `exec_id`. Nothing live is a clean no-op straight to step 2 — the same
path a RETRY takes after a stop already succeeded. Step 2 (mark) is the new `drop-lane` intent
(component `gateway`, same commit), called only if step 1 succeeded or found nothing. A stop failure
returns `ok:false` WITHOUT ever attempting the mark — the ruling's "never both true" in code.

## How it works
`chat-bridge.js`'s `createRecoveryDispatch({...})` call now passes a `dropLane` closure: `await
findLiveExecIdForLane(forwarder, goalId, seat)` (new module-level helper, `inspect` + a workdir
regex) -> if found, `forwarder.forward('kill-session', {id})`, propagating a stop failure as
`ok:false` with no mark attempted -> `forwarder.forward('drop-lane', {goal, seat})`, propagating a
mark failure as `ok:false` with text naming the lane as NOT marked and possibly relaunched. On full
success, `{ok:true, result}`. `recovery-thread.js`'s `drop-lane` case now posts that error text
verbatim on failure (replacing the deleted "did not run" line) and a new success confirmation
("...dropped: live work stopped and the lane is permanently marked abandoned. This cannot be
undone.") on success — `retry-with-change`'s identical "did not run" line and `pause-goal`'s success
text are untouched (each outcome owns only its own line). The module header comment no longer claims
`dropLane` is unwired.

## Consequences
`retry-with-change` stays unwired exactly as before (owned by `rr-port-wire`) — this change touches
nothing in that case. `pause-goal` is unchanged (still the direct `pause-resume` sender). No existing
chat probe assertion was edited; three ran green unchanged (`probe-chat-boundary` — pre-existing red
elsewhere, see below; `probe-chat-reply-grammar`; `probe-chat-ask-release`).

## Verification
New probe `ignite/chat/probes/probe-chat-recovery-dispatch.js`, 13 checks, PASS: (A) a LIVE lane —
`inspect` then `kill-session` then `drop-lane`, in that exact order, `kill-session` targeting the
found `exec_id`; (B) nothing live — `inspect` then `drop-lane`, no `kill-session` call; (C) half-
completion — mark refused, dispatch `ok:false`, thread text says NOT marked / may be relaunched,
never "did not run", no success text posted; (D) retry on the SAME lane after that failure completes
the mark; (E) an already-abandoned lane (mark reports `idempotent:true`) succeeds as a no-op; (F) the
discriminating control — `pause-goal` on the SAME fixture (even with a live lane present) fires ONLY
`pause-resume`, never `inspect`/`kill-session`/`drop-lane`. `node ignite/chat/probes/probe-chat-
boundary.js` still fails — PRE-EXISTING, `bus-answer.js:55,158` `execFile` (untouched by this change,
last committed 2026-08-25); this change's own files show zero forbidden-pattern hits. Committed, not
deployed (8c1023afeaa45474f85a0f3a09a25ecc266e61ed).

## ATTENTION
1. `findLiveExecIdForLane`'s workdir regex is a SECOND COPY of `heart-store.js#enqueueHomeOf`'s path
   shape, deliberately — `probe-chat-boundary.js` forbids requiring heart-store from any `chat/`
   runtime file. If that path shape ever changes (e.g. seats stop being homed at
   `.rbtv/goals/<goal>/seats/<seat>`), this copy must be updated by hand; nothing enforces the two
   staying in sync.
2. NO SUCCESS TEXT existed for `drop-lane` (or `retry-with-change`) before this change — only
   `pause-goal` posted a confirmation. This change adds one for `drop-lane`'s full-success arm only;
   `retry-with-change` still posts nothing on success (`rr-port-wire`'s to fix, not touched here).
3. The probe's fake forwarder answers `record-owner-ask` generically (same shape `probe-chat-
   approval.js`'s fixture uses) — it is not testing the ask-open/reap mechanism, only what happens
   after a recovery reply releases; do not read its PASS as proof of the ask ledger's own behaviour.
- pre-existing probe-chat-boundary red is bus-answer.js execFile, unrelated to this change
