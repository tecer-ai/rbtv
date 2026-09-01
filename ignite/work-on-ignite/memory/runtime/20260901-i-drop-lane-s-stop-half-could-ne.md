# 20260901-i-drop-lane-s-stop-half-could-ne — drop-lane's stop-half could never authorize (kill-session)

kind: issue
component: runtime
date: 2026-09-01
commit: 2493b697fa090f88c6d7bae825ed18ad671c97b3
deployed: no
pin: ignite/runtime/internal-api/probes/probe-drop-lane.js
components: chat,gateway,state-store

## Observed
`dl-live-proof` (2026-09-01) ran `drop-lane` end to end against the RUNNING production daemon
(deploy HEAD `b2877ec0`, ancestor of `8c1023af`). A real owner recovery reply against a genuinely
live seat (`worker-p`, pid `1111542`, verified alive) produced `drop-lane failed: live work was NOT
stopped, so the lane was NOT dropped: UNAUTHORIZED_SENDER` — and the session ran to its own natural
completion 3+ minutes later, completely untouched. Every prior probe (bridge-level, over an injected
fake forwarder) had passed, because the fake never enforced the real `authz.js`.

## Mechanism
Original shape (`8c1023af`): the `dropLane` port composed its two ruled steps CLIENT-SIDE, in
`chat-bridge.js`, as two wire calls — `inspect` (find the exec_id) then `kill-session` (stop it).
`kill-session`'s authorization (`authz.js#canKillSession`) admits ONLY `sender.kind === 'owner'` or
a `creator-seat` match (`enqueued_by`/`enqueuing_seat` compared to the AUTHENTICATED sender's own
id/seat — resolved from the connection's TOKEN, never from a payload field). The chat bridge always
authenticates as `kind: 'bridge'`, and a goal seat's live turn is never enqueued BY the bridge — so
that call could never succeed, for ANY goal, ANY seat, under ANY payload shape.

## Attempts
The live prover's own theorized fix (`dl-live-proof`'s report: "thread `chat_user` through
`kill-session`, the way `chat/pause-resume.js:177` does for `pause-resume`") did NOT hold up.
Verified independently, twice, BEFORE it was applied (scratch `git worktree add`, never `git
stash` — the plan's standing prohibition): (1) `gateway/parse.js#parseKillSession` rejects any
field beyond `id` outright (`kill-session: unknown field "chat_user"`) — the field could not even be
added without a schema change of its own; (2) `authz.js#canKillSession` never reads a payload field
at all, ever. `chat/pause-resume.js:177`'s own comment states `chat_user` "rides along as the
reporting sender only... never asks the daemon to re-decide who is allowed" — it was NEVER an
authorization input anywhere in this tree. This attempt was rejected before being written, not after.

## Fix
Both ruled steps now run IN-PROCESS inside the ALREADY-authorized `drop-lane` intent handler
(`canDropLane`, bridge-only — the SAME gate the whole intent already passed), using the SAME
`heartStore`/`spawnManager` handles `handleKillSession` already holds. This is the existing
daemon-side-executor pattern (`state-store/heart/pause-resume.js`'s own shape: effects happen
in-process behind ONE authorization gate, never a second gateway hop back out) — applied to the one
step that was wrongly left client-side. `authz.js` is UNCHANGED — no widening of `canKillSession` or
any other rule; `kill-session` the intent is untouched and still `owner`/`creator-seat`-only for its
OWN callers (ad-hoc job kills), which is correct and was never the bug.

`ignite/state-store/heart/drop-lane.js#dropLane()` is now `async` and takes `heartStore`/
`spawnManager` in addition to `workspaceRoot`/`goal`/`seat`/`askId`. Step 1:
`findLiveExecutionForLane()` (new, in this file) scans `heartStore.listExecutionsByStatus('running'/
'launching')` — the SAME two calls `dispatch.js#handleInspectTicker` already makes — filtered by
`args.workdir === <workspaceRoot>/.rbtv/goals/<goal>/seats/<seat>`; if found, `await
spawnManager.kill(execId)`. A throw here returns `{found:true, stopFailed:true, stopError}` and
`abandonSeat` is NEVER called. Step 2 (unchanged): `store.abandonSeat(...)`; a throw here (rare — a
raw store failure, input already validated) returns `{found:true, markFailed:true, markError}`,
distinct from `stopFailed` so the caller's text always names the correct half. `dispatch.js#handle
DropLane` is now `async`, passes `heartStore`/`spawnManager` through, and turns `stopFailed`/
`markFailed` into two distinctly-worded `InternalApiError(INTERNAL, ...)`s. `chat-bridge.js`'s
`dropLane` port collapses to ONE forwarder call (`forwarder.forward('drop-lane', {goal, seat})`) —
the client-side `inspect`+`kill-session` composition and its now-dead `findLiveExecIdForLane`/
`LANE_WORKDIR_RE` helper are deleted.

## Consequences
`kill-session` the intent, `authz.js`, `gateway/parse.js`'s `parseKillSession` — all UNCHANGED.
`chat/pause-resume.js`, `rr-port-wire`'s `retry-with-change` wiring, `pause-goal` — all unaffected
(verified: their probe checks in the shared `probe-chat-recovery-dispatch.js` file still pass
unchanged). The bridge-level probe's job narrowed: it no longer asserts an order between wire calls
(there is only one now), only that the daemon's outcome is relayed faithfully.

## Verification
`node ignite/runtime/internal-api/probes/probe-drop-lane.js` (NEW) — 15/15 PASS. Real
`parse+dispatch+authz.js` over a scratch ending store, with scriptable `heartStore`/`spawnManager`
stubs that RECORD call order: stop-then-mark order (A), nothing-live no-op (B), stop-failure
half-completion with NOTHING marked (C), retry-after-stop-failure completes the mark (D), idempotent
re-drop (E), the bridge-only authorization boundary — owner AND agent senders both `UNAUTHORIZED_
SENDER`, bridge admitted (F) — and an independent, code-level re-disproof of the prover's specific
`chat_user` mechanism (G). `node ignite/chat/probes/probe-chat-recovery-dispatch.js` — rewritten
sections for the new one-call shape, 21/21 PASS (12 mine + `rr-port-wire`'s 9 retry-with-change
checks, untouched and still green). `node ignite/runtime/internal-api/probes/probe-intent-drift.js`
— PASS, still 16/16/16 (no intent-set change, only the handler's body). `node ignite/state-store/
ending-store.selftest.js`, `node ignite/deploy/probe-suite.js --only probe-pause-resume` — both
still ALL PASS/GREEN (untouched). `node ignite/chat/probes/probe-chat-boundary.js` — still the SAME
pre-existing red (`bus-answer.js:55,158` `execFile`, untouched, last committed 2026-08-25; my files
show 0 hits). NOT live-verified — committed, not deployed (`2493b697`); needs its own deploy window
and its own live-fire re-proof (this defect was found BY a live-fire test; a unit-green result alone
is not sufficient evidence it is actually fixed in production).

## ATTENTION
1. UNIT/PROBE COVERAGE OVER AN INJECTED PORT CANNOT PROVE AUTHORIZATION. This defect shipped past a
   passing bridge-level probe (`8c1023af`) because the fake forwarder answered `kill-session`
   unconditionally — it never ran `authz.js`. Any future port whose real counterpart is
   authorization-gated needs a probe that exercises the REAL `authz.js` (like `probe-drop-lane.js`,
   `probe-pause-resume.js`), not just a scripted stand-in, or a live-fire proof — a green unit result
   over a stand-in is not evidence the gate will ever open.
2. `findLiveExecutionForLane` in `drop-lane.js` is a SECOND, DISCLOSED read of the same non-terminal
   `jobs_log` rows `handleInspectTicker` scans (filtered by `args.workdir`) — not `heart-
   store.js#findSeatHolder` (the seat-BUSY gate, a different question: "may a NEW job fire here",
   with its own pending-row arm this act has no use for). If a future refactor changes how a goal
   seat's `workdir` is recorded at spawn time, this filter and `handleInspectTicker`'s both need
   updating together — nothing enforces them staying in sync.
3. A PEER'S DIAGNOSIS CAN BE RIGHT ABOUT THE SYMPTOM AND WRONG ABOUT THE MECHANISM. `dl-live-proof`
   correctly found and precisely located the observable defect (`UNAUTHORIZED_SENDER` on a live
   kill-session call); its theorized fix (thread `chat_user` through) was independently proven false
   at the code level before being applied. Verify a peer's specific mechanism claim against the real
   code before implementing it, even when the underlying finding is solid.
- unit coverage over an injected kill-session port never enforces authz.js — use the real policy module or a live-fire proof
