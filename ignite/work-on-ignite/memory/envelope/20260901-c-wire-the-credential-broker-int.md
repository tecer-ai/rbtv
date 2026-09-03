# 20260901-c-wire-the-credential-broker-int — wire the credential broker into the live launch path

kind: creation
component: envelope
date: 2026-09-01
commit: e233584b
deployed: no
pin: ignite/envelope/probes/probe-credential-broker-lifecycle.js
components: supervisor,chat,planning

## Motivation
`d-hold5-wire-the-broker` (owner ruling, 2026-09-01): the credential token broker
(`ignite/envelope/credential-broker.js`, commit `14fe57d0`) was built and proven 6/6 on a
fixture but never wired into the live launch path, so the owner-approved goal
`transcript-summarizer-build` could not launch a single credentialed seat — `admitLaunch()`
refused `missing-credential: pessoal, tecer, ignite`. This entry is that wiring: steps 1, 2
and 4 of the loose end's own ordering (spawn.js lifecycle, `plan_envelope.py`'s typed
manifest shape, and the mid-run alarm from `d-broker-midrun-alert`, design §10b).

## Design
The broker is PER-GOAL, not per-seat, but `spawn.js` has no existing "goal ended" hook — its
`createSpawnManager` instance is long-lived (one per daemon process, serving every concurrent
goal), and `composeCageFor` is called once per SEAT spawn, many times per goal. Rather than
change `admitLaunch`'s contract (it stays fully synchronous, per `credential-broker.js`'s own
header reasoning) or restructure `composeCageFor`'s return shape (an array of bwrap flags today,
read by every existing caller), the broker's lifecycle is tracked in a module-level
`goalBrokers` Map keyed by `goalDir`: `ensureGoalBroker` fires (never awaits) a broker start the
moment `admitLaunch` resolves `accountCredentials`, memoized per goal so a second seat of the
same goal reuses the in-flight/listening broker rather than racing to start a second one on the
same socket. The two launch doors (`spawn()`, `spawnSeat()`) separately `await`
`brokerReadyFor(goalDir)` right before the seat actually execs — decoupling "start" (inside the
synchronous `composeCageFor`) from "must be ready before this specific exec" (in the async launch
doors) without threading a promise through `composeCageFor`'s return value at all.

`stopGoalBroker`/`endGoalBroker` are NOT called from anywhere: the code that detects a goal has
ended lives in `reconcile.js`/`ignite/coord/`, outside this seat's custody row (`spawn.js` +
`bwrap.js` + `envelope/*` + the alarm surface only). This is the deliberate, named integration
point for whoever owns that detection — exactly the same shape `credential-broker.js`'s own
header already used for its own unwired half before this entry landed.

`d-broker-midrun-alert` (§10b) is wired by REUSING `bus-ferry.js`'s existing `postOwner({kind:
'alarm', channel: systemChannelId, ...})` surface — the same one `postUnreachableChannelAlarm`
already posts through for the OTHER daemon-level fault this ferry knows (an unreachable goal
channel) — rather than inventing a second alarm shape. A new function, `scanCredentialBrokerLog`,
tails each goal's `scratch/credential-broker.log` (the durable half `credential-broker.js`
already writes) with a per-goal line-count cursor, mirroring the SAME cursor/size pattern the
message ferry already uses for `coordination/messages.md` — deliberately a SEPARATE pass over
`buses`, not interleaved with the messages.md loop, because that loop's early `continue`s are
messages.md-specific and would wrongly skip a goal with a live broker but no bus traffic yet.

## How it works
- `ignite/supervisor/spawn/spawn.js`: `ensureGoalBroker(goalDir, workspaceRoot, accounts,
  minterOverride)` — module-level `goalBrokers` Map, idempotent per goal, `minterOverride`
  defaults to the real `gtoolsTokenMinter`. `brokerReadyFor(goalDir)` — the promise a launch
  door awaits. `stopGoalBroker(goalDir)` — the goal-end integration point, exported on the
  manager as `endGoalBroker`. Called from `composeCageFor` right after `admitLaunch` succeeds;
  awaited in `spawn()` and `spawnSeat()` right before `buildBwrapArgv`/`composeSeatSpawn`. A
  broker-start failure logs a warning and does NOT refuse the seat's launch — its own mint calls
  fail loud on connect instead, the same "stay synchronous, stay narrow" posture `admitLaunch`
  itself already takes.
- `ignite/planning/plan_envelope.py#_credential_names` — accepts a bare env-var-name string
  (unchanged) or `{"type": "gtools-account", "account": "<name>"}`, validated in lockstep with
  `envelope/credentials.js#isAccountCredentialEntry` (the one other reader of this shape).
- `ignite/chat/bus-ferry.js#scanCredentialBrokerLog(goalId)` — reads
  `<goalDir>/scratch/credential-broker.log`, tracks lines already scanned in
  `credLogLinesSeen` (per-process, not persisted — same as `sizes`), and posts one alarm per
  `ok:false` line it has not already reported. Called once per goal per `_runOnce` pass.

## Consequences
`credential-broker.js`'s own header comment ("NOT WIRED INTO THE LIVE LAUNCH PATH YET") is now
stale and was updated in this same change. `probe-credential-broker.js`'s GREEN leg used to call
`startBroker` directly with its own fixture minter — once `composeCageFor` started auto-starting
a REAL-minter broker for the same `goalDir`, the two raced for the same socket and the probe's
fixture-minter broker lost (measured while landing this). Fixed at the root — not by weakening
either side — by routing the probe's fixture minter through the SAME `ensureGoalBroker` registry
via the new `minterOverride` parameter, so there is exactly one authority over any given goal's
broker regardless of caller.

Step 3 of the loose end ("update `transcript-summarizer-build`'s own Google-calling tool code")
was investigated and found to be its own, unscoped design surface, not a small edit: the goal
has NO tool code that reads `token.json` directly anywhere in its mirror component
(`.rbtv/mirror/office/meeting-summarizer/`) — its seats shell out to the `gtools` CLI
(`3-resources/tools/gtools/`, a separate, shared tool outside this goal's ownership and this
seat's custody row), and `gtools` itself reads the account's login files via its OWN `auth.py`.
Making that path broker-aware is cross-cutting (every `gtools` consumer, not just this goal) and
was not attempted here — named precisely in the seat's report, not silently skipped. Separately:
the LIVE goal's own `envelope.json` still declares `credentialNames` as bare strings
(`["pessoal","tecer","ignite"]`), not the typed shape this entry adds support for — re-authoring
it is a live-goal mutation outside this seat's walls, and is a real remaining blocker even after
deploy.

## Verification
`probe-credential-broker.js` (6/6, unchanged assertions, rerouted plumbing only),
`probe-credential-broker-lifecycle.js` (new, 11/11 — start-at-launch via `composeCageFor` itself,
reuse across two seats of one goal, a REAL mint through `gtools-token-minter.js` +
`gtools_mint_token.py` via a fixture `scripts/auth.py`, never exercised end-to-end before this
probe, and stop via `stopGoalBroker`), `probe-credential-account-admission.js` (new, 2/2 — the
exact `pessoal`/`tecer`/`ignite` refusal reproduced, then admitted once fixture account files
exist), `probe-chat-credential-broker-alarm.js` (new, 6/6 — a forced failure alarms, a success
does not, no double-fire, a second distinct failure alarms again), `probe-envelope-walls.js`
(13/13 unchanged), `probe-chat-bus-ferry.js` (75/75 unchanged), all four `envelope/*.selftest.js`
green, `probe-plan-envelope.py` (5/5 unchanged). Committed `e233584b`. NOT deployed — `spawn.js`
and `ignite/chat/` are pinned to the deploy worktree; this is inert until an orchestrator-owned
deploy window.

## ATTENTION
1. `execFileSync` blocks the Node event loop the in-process broker answers requests on — a
   broker-dependent probe leg must use async `execFile`/`execFileAsync`, never the sync form.
   Already known (cred-account-shape's own memory), re-confirmed: `probe-credential-broker-
   lifecycle.js`'s caged-mint legs use `cagedRunAsync`, never `execFileSync`.
2. Two independent code paths (a hand-called `startBroker` and `composeCageFor`'s own
   auto-start) racing for the SAME goal's socket is a real, measured failure mode, not a
   theoretical one — `ensureGoalBroker`'s `minterOverride` parameter exists specifically so a
   test harness registers through the one shared registry instead of calling `startBroker`
   directly.
3. Unix domain socket paths are capped at 108 bytes on Linux — a fixture goalId/mkdtemp prefix
   that is descriptive-but-long (`test-cred-broker-lifecycle`, `cred-broker-lifecycle-`) produces
   `listen EINVAL` with a message that does not mention the length limit at all; keep fixture
   goalIds and mkdtemp prefixes short when a broker socket lives under the fixture's `scratch/`.
4. `stopGoalBroker`/`endGoalBroker` is unwired — nothing calls it. A future seat wiring it into
   the real goal-end detection (`reconcile.js`/`ignite/coord/`) should read this entry first
   rather than re-deriving why the hook exists but nothing calls it.
5. The live `transcript-summarizer-build` goal's own `envelope.json` still carries the OLD
   bare-string `credentialNames` shape — this wiring alone does not unblock it; it also needs
   re-authoring into the typed shape, which is a live-goal mutation this seat's walls forbade.
- execFileSync blocks the broker's event loop -- use async execFile in any broker-dependent probe leg
- two independent startBroker callers for the same goalDir race the socket -- route test harnesses through ensureGoalBroker's minterOverride, never a bare startBroker call
- Unix socket paths cap at 108 bytes on Linux -- listen EINVAL with no length-related message is the symptom; keep fixture goalIds/mkdtemp prefixes short
