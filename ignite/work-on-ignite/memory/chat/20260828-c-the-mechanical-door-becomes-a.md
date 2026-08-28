# 20260828-c-the-mechanical-door-becomes-a — the mechanical door becomes a pause-resume sender

kind: change
component: chat
date: 2026-08-28
commit: 8b44d806
deployed: no
pin: ignite/chat/probes/probe-chat-pause-resume.js
components: bridges,gateway,supervisor

## Motivation
The mechanical door was built (5b6762f9) against four INJECTABLE ports — `endingStore`,
`listSeats`, `listLiveGoals` and later `rearmCounters` — that nothing in production could
legally supply: the bridge is a separate process forbidden a store handle by
`probes/probe-chat-boundary.js`, and the 2026-08-24 ruling that minted `start-execution`
declined the pause-word intent that would have let those acts cross. So the door parsed and
targeted correctly and applied nothing, and the branch that reported the missing applier
returned before posting, so it also said nothing (entry
`20260828-i-the-mechanical-pause-resume-ve`). The owner reversed the deferral on 2026-08-28
~02:00Z and directed the intent to be minted.

## Design
The door becomes a SENDER built from the forwarder the bridge already holds, always — the
`start-execution.js` shape exactly, and for the same argument: an injectable applier is the
seam where somebody writes `{applied: true}` to make a test pass, after which the bridge tells
the owner a goal is paused while it runs. `createPauseResume` now REFUSES at construction
without `forwarder` or without `isAuthorizedSender`, rather than defaulting either.

The wire contract was fixed before either half was built, so the daemon side could be built in
parallel: intent `pause-resume`, payload `{verb: 'pause'|'resume', goal}`, result
`{verb, goal, applied, actions, refusals: [{row, text, seat?}]}` — deliberately the return
shape `applyPause`/`applyResume` already had, so `summarize()` renders it unchanged and the
renderer, the one part the owner actually reads, was not rewritten to suit a new wire format.
Rejected: a per-verb pair of intents (the verb admits no judgment, so one payload key carries
it), and keeping the ports injectable with the sender as their default (the seam above).

The resume-semantics table (`spec-recovery` §4 [C-14]) moves whole to the daemon. No second
copy of it, or of its refusal prose, survives in `chat/` — two processes deciding one fact
drift, and the table is the fact.

## How it works
`handle({text, channelId, threadTs, channelGoal, liveGoals, senderId})` parses with
`reply-grammar.js` as before. A first token that is not `pause`/`resume` returns
`{mechanical: false}` and the caller continues to the master doors [T5-R14]. Otherwise the
sender is checked FIRST, before any post and any call: an unauthorized sender also gets
`{mechanical: false}` and falls through. A grammar failure posts the verbatim §4.5 NACK.
Otherwise `forwarder.forward('pause-resume', {verb, goal})` crosses the boundary, and the
answer decides the line: `NOT_FOUND` is the §4.2 ambiguity and gets the same verbatim NACK;
anything else — `UNKNOWN_INTENT`, an authorization refusal, a `TRANSPORT` timeout, a throw, or
an `ok` whose result carries no `actions`/`refusals` arrays — posts
`pause <goal> was NOT applied — <error>`; a well-formed result is rendered by `summarize()`
and returned to the caller with `actions`/`refusals`/`instructions` intact, which is what the
approval-thread release path reads for resume-with-instructions [C-14].

`chat-bridge.js` builds it beside `createExecutionStart`, passing `forwarder` and
`isAuthorizedSender: (id) => allowlist.isAdmitted(id)` — the same object built from
`config.allowlist` that feeds `ask-thread.js#authorizedSenders`, never a second list, and the
non-mutating predicate rather than `allowlist.check`, which would mint a pending-pairing record
the fall-through path should mint instead. Both call sites now pass `senderId`: the top-level
goal-channel/DM path passes `rawMsg.chatUserId`, the ask-thread release path passes
`chatMsg.chatUserId`.

## Consequences
Deleted from `chat/`: `applyPause`, `applyResume`, `seatsOf`, `rearmCounterRows`,
`blockedOnHumanRefusal`, `gateCapRefusal`, the four diagnostic constants and the
`evidencePointer` option — with them, every write this process was pretending it could make.
Deleted from the wiring: the `endingStore`, `listSeats`, `listLiveGoals` and `rearmCounters`
constructor arguments in `chat-bridge.js` and `chat/index.js`, the `liveGoalNames()` helper,
and both files' "NOT WIRED IN PRODUCTION" headers. `liveGoalNames()`'s other caller —
`askDoor.release`'s `liveGoals` argument — now passes the literal `null`, which is what it
always evaluated to, since no probe and no production path ever supplied `listLiveGoals`.

The module's exports changed: `createPauseResume` and `NACK_MECHANICAL` remain, `INTENT` and
`refusalLine` are new, and the six table symbols are gone. Nothing outside `chat/` imported
them, so no caller broke — but `supervisor/component.md:463` and `supervisor/exhaustion.js:165`
still describe the deleted `applyResume`/`rearmCounters` shape in prose, outside this change's
walls and surfaced rather than fixed.

Requires a BRIDGE restart (`rbtv-chat-bridge`, which boot-loads `chat/*` from the deploy
worktree) and, separately, a DAEMON carrying the `pause-resume` executor. Neither was done
here.

## Verification
`probes/probe-chat-pause-resume.js` rewritten around a fake forwarder, 23 checks EXIT 0
(2026-08-28 02:44Z), replacing 19 checks that drove the real ending store — the right harness
now, because this module applies nothing and the table it used to apply is asserted daemon-side
against the real store. Proven: one call, one payload, no extra key; every action and every
refusal rendered as a line; the §4.5 NACK byte-compared against an independently transcribed
copy of the spec; five failure arms each asserting `posts.length === 1`; three arms proving an
unauthorized sender gets no call, no post and no NACK; grammar A1-A6; both construction
refusals. Red-armed by mutation on the live file and restored byte-identically: the old early
return reddens the five silence arms, a no-op sender check reddens the three admission arms.
`probe-chat-boundary` reports the identical 2 standing hits before and after, which is what
proves the forwarder added no forbidden capability. `probe-chat-approval` 24/24,
`probe-chat-bus-ferry` 64/64, `probe-chat-glance-wiring` 20/20, unchanged. Commit 8b44d806.
NOT DEPLOYED.

## ATTENTION
1. NO SECOND COPY OF THE RESUME-SEMANTICS TABLE MAY REAPPEAR IN `chat/`. A diagnostic name or a lane refusal string added back here means two processes decide one fact, and the bridge's copy is the one nobody will remember to update — that is how the two pause records (`goal_states.stored` vs the `execution-lane` file) diverged before.
2. THE RESULT SHAPE IS THE CONTRACT, AND `summarize()` IS ITS ONLY READER. Changing a `row` value or renaming `actions`/`refusals` daemon-side silently degrades the owner's line to the malformed-result refusal — which is loud, but it is a refusal for a verb that actually worked.
3. AN INJECTABLE APPLIER PORT MUST NOT BE RE-OPENED, and neither constructor argument may gain a default. Both refusals exist because a stub applier lets the door answer as if it acted; that is the one lie this surface cannot tell about a live goal.
4. THE SENDER CHECK RUNS BEFORE BOTH PARSE ARMS ON PURPOSE. Moving it after the NACK arm to "answer politely" tells an unadmitted principal that the door exists and which goals it can resolve.
5. `chat/index.js#buildBridge` NO LONGER ACCEPTS THE FOUR PORTS. A probe or embedder still passing `endingStore`/`listSeats`/`listLiveGoals` is silently ignored by object destructuring rather than refused — if one is found doing so, it is testing a door that has not existed since this commit.
- No second copy of the resume-semantics table may reappear in chat/ — the table now lives only behind the pause-resume intent
