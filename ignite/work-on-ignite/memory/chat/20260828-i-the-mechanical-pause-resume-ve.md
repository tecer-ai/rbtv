# 20260828-i-the-mechanical-pause-resume-ve — the mechanical pause/resume verb answered nothing at all

kind: issue
component: chat
date: 2026-08-28
commit: 8b44d806
deployed: no
pin: ignite/chat/probes/probe-chat-pause-resume.js
components: bridges,gateway

## Observed
An owner typing `pause {goal}` or `resume {goal}` into Slack got NOTHING back — not an
answer, not a NACK, not an error. Measured by the live acceptance wave as tests 8/9/10 (row
`wave-c-steer`, `build/live-acceptance-tests/`), and recorded in that folder's
`loose-ends.md` line 5 as the silence defect. Deployed and HEAD were the same commit
(28ad5a22) when this was fixed, so the deployed bridge carried exactly the code below. The
goal was never paused either — but the wave's finding is the silence, because a verb that
answers nothing cannot be told apart from a bridge that is down.

## Mechanism
Two causes stacked, and the second is the one the owner met.

`chat/index.js#buildBridge` passed none of `endingStore`, `listSeats` or `listLiveGoals` to
`createChatBridge`, which passed them straight into
`chat-bridge.js#createPauseResume({store: endingStore, listSeats, ...})`. So the door was
constructed with `store === null` in production and always had been: the ports were
INJECTABLE and nothing anywhere injected them. That was by design at the time — the bridge
is a separate process holding no store handle (`probes/probe-chat-boundary.js` enforces it),
and the 2026-08-24 ruling that minted `start-execution` deliberately declined the pause-word
intent (see `gateway/20260824-c-14th-intent-start-execution` ATTENTION-5), so the door was
built against a port that could not legally exist in that process.

The silence itself is `pause-resume.js:260-265`. `handle()` parsed the verb, resolved the
target, then computed `hasApplier = store || (verb === 'resume' && typeof rearmCounters ===
'function')`, and on false did `log('warn', ...)` and returned
`{mechanical: true, ok: false, applied: false, reason: 'no-store', ...}` — BEFORE any call to
`post()`. `chat-bridge.js`'s caller reads `mech.mechanical === true` and returns
`{forwarded: false, leg: 'mechanical'}`, so the message was consumed by the door and never
reached the forward path either. The warn went to the bridge journal, which the owner does
not read. The module's own header stated the contract being broken, at `:81-83`: post is
"Required — a mechanical verb that answers nothing is the silence [F-owner-ux-2] forbids".
The wrong behaviour is born at `:264`, the return statement: the contract established by the
module's own header and by `spec-owner-io` §4.5 (which specifies a posted string for the
UNPARSEABLE case, so the parseable-but-inapplicable case cannot be quieter) requires an
answer where the verb arrived, and that branch drops it.

## Attempts
First attempt held — checked: 5b6762f9 (`bridges/20260824-c-mechanical-pause-resume-door-r`),
which BUILT this door and chose the loud-degradation branch deliberately, writing "NOT
REACHABLE IN PRODUCTION … With no port the door parses and targets correctly and applies
NOTHING, logging a warn — chosen over a stub that would answer as if it worked". That choice
was right about the stub and wrong about the log: a warn in a journal is not an answer to a
person. a49f9df8/dae7b4f5 (the fourteenth intent) faced the identical wall for D12 and solved
it the way this fix now does, but its ruling explicitly excluded the pause verb, so the door
was left as found. 84238318 and 4c13b853 touched `chat-bridge.js` for the escalation and
completion legs and did not reach this branch.

## Fix
Commit 8b44d806, under the owner's direction of 2026-08-28 ~02:00Z (recorded in the
role-action-program `decisions.md`), which reverses the 2026-08-24 deferral. `pause-resume.js`
becomes grammar + sender + poster: it parses as before, checks the sender, then sends the
gateway intent `pause-resume` with payload `{verb, goal}` through the forwarder the bridge
already holds, and posts what comes back. `applyPause`, `applyResume`, the resume-semantics
table and its two refusal-prose functions are DELETED from `chat/` and move behind the intent
into the daemon, so exactly one copy of that table exists.

Why a sender and not a wired port: an injectable applier is the seam where somebody writes
`{applied: true}` to make a test pass, and the door then tells the owner a goal is paused
while it runs. `start-execution.js:42-45` refuses to exist without the forwarder for that
reason and this door now does the same — both constructor arguments are refused at
construction rather than defaulted.

Every exit now posts. `NOT_FOUND` from the daemon is the §4.2 ambiguity and gets the verbatim
§4.5 NACK; every other outcome — `UNKNOWN_INTENT`, an authorization refusal, a transport
timeout, a throw, or an `ok` carrying no `actions`/`refusals` — posts
`pause <goal> was NOT applied — <error>`. The last case is not defensive padding: `summarize()`
reads those two arrays, so an empty result would have rendered "nothing to change." for a
daemon that did nothing at all, which is the same lie in a new place.

## Consequences
Four constructor ports are gone from `chat-bridge.js` and `chat/index.js` — `endingStore`,
`listSeats`, `listLiveGoals`, `rearmCounters` — along with the `liveGoalNames()` helper and
the "NOT WIRED IN PRODUCTION" prose in both files' headers. `liveGoalNames()` had one other
caller, `askDoor.release`'s `liveGoals` argument; it provably always returned null (no probe
and no production path ever supplied `listLiveGoals`), so that argument is now the literal
`null` and behaviour is unchanged.

A second-order hole opened and was closed in the same commit. `chat-bridge.js` runs the
mechanical door BEFORE the forward path's per-principal admission gate
(`forward-path.js#onChatMessage` -> `allowlist.check`), because a mechanical verb never
forwards. That ordering was inert while the door applied nothing; with the intent live it
would have let any Slack workspace member who can DM the bot pause a goal, stamped
`who_stamped: 'owner'`. The door now takes `senderId` and asks `allowlist.isAdmitted` — the
same object built from `config.allowlist` that feeds `ask-thread.js#authorizedSenders`, not a
second list — and an unauthorized sender's `pause X` returns `{mechanical: false}` and falls
into the ordinary path, which refuses it at that existing gate.

The verbs remain non-functional until the DAEMON half is deployed: the gateway's intent set is
closed, so a daemon without the executor answers `UNKNOWN_INTENT` and the door posts that
verbatim. Two stale citations of the deleted functions were left outside this change's walls
and are surfaced, not fixed: `supervisor/component.md:463` (the resume row still cites
`chat/pause-resume.js#applyResume` and its `rearmCounters` port) and `supervisor/exhaustion.js:165`
(a comment stating `chat/index.js#main()` wires no port).

## Verification
`probes/probe-chat-pause-resume.js` was rewritten around a FAKE forwarder that records the
crossing and answers a script — the right harness now, because the module applies nothing and
the daemon side asserts the table against the real ending store. 23 checks, EXIT 0
(2026-08-28 02:44Z), the previous version being 19 checks driving the real store. The arms
that matter: exactly one `pause-resume` call with payload `{verb, goal}` and no other key; every
action and every refusal rendered as its own line; `NOT_FOUND` producing a NACK byte-compared
against an independently transcribed copy of `spec-owner-io` §4.5; five failure arms
(`UNKNOWN_INTENT`, `UNAUTHORIZED_SENDER`, `TRANSPORT`, a throw, a malformed result) each
asserting `posts.length === 1`; three arms proving an unauthorized sender gets no call, no
post and no NACK; the A1-A6 grammar arms; and both construction refusals.

Red-armed by mutation on the live file, not assumed: restoring the pre-fix early return
reddens all five silence arms (plus the three success arms); replacing the sender check with a
no-op reddens all three admission arms. The file was restored byte-identically after each and
re-run green. `probe-chat-boundary` reports exactly the same 2 hits before and after (both
`bus-answer.js` `child_process`, the standing red), which is what proves the forwarder added
no forbidden capability. `probe-chat-approval` 24/24, `probe-chat-bus-ferry` 64/64,
`probe-chat-glance-wiring` 20/20 — identical before and after. The `chat/probes` suite ran
28 discovered / 26 passed; the second red, `probe-chat-ask-release` E7, was confirmed red at
HEAD with these four files checked out, so it is not this change's. `node --check` exit 0 on
every touched file; `tmux ls` byte-identical. NOT DEPLOYED by this commit.

## ATTENTION
1. THE BRIDGE IS USELESS FOR THESE VERBS UNTIL A DAEMON CARRYING THE `pause-resume` EXECUTOR IS ALSO DEPLOYED, and the failure mode is legible on purpose: the gateway's intent set is closed, so an older daemon answers `UNKNOWN_INTENT` and the owner reads `pause X was NOT applied — UNKNOWN_INTENT: unknown intent: pause-resume` in the channel. Deploying the bridge alone is safe but changes nothing the owner wanted.
2. THE SENDER CHECK IS THE ONLY GATE ON THIS PATH. The door runs ahead of `forward-path.js`'s `allowlist.check` because a mechanical verb never forwards, so nothing downstream would ever see the message. Dropping `senderId` at either call site in `chat-bridge.js`, or defaulting `isAuthorizedSender` to true, hands goal pausing to every member of the Slack workspace who can DM the bot, stamped as the owner.
3. `isAdmitted` AND NOT `check` IS DELIBERATE. `allowlist.check` mints a pending-pairing record as a side effect; the door asks the non-mutating predicate so the fall-through path records the pairing request exactly once, where the refusal actually happens.
4. AN UNAUTHORIZED SENDER GETS NO NACK EITHER, WHICH LOOKS LIKE A MISSING BRANCH AND IS NOT. The admission check sits before both parse arms so an unadmitted principal cannot learn from a NACK that this door exists or which goals it knows.
5. `NOT_FOUND` IS THE ONLY ERROR CODE WITH A SPECIFIED ANSWER. Routing any other code into the §4.5 NACK would tell the owner their goal does not exist when the daemon is merely old, down, or refusing the token — three different acts with three different next steps.
- The bridge is useless for pause/resume until a daemon with the pause-resume executor is deployed too — until then every verb answers UNKNOWN_INTENT, honestly, in the channel
