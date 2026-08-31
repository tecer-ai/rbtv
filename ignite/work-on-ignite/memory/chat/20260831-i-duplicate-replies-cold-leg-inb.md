# 20260831-i-duplicate-replies-cold-leg-inb — duplicate replies: cold-leg inboundMsgId wiring landed

kind: issue
component: chat
date: 2026-08-31
commit: b72092f1
deployed: no
pin: ignite/chat/probes/probe-chat-duplicate-idempotency.js

## Observed
Follow-up to `20260831-i-duplicate-replies-timeout-inve.md` (commit 10ad7956): that commit wired `chat-bridge.js#deliverToOwner`'s per-inbound-message idempotency guard for the warm leg only. The cold leg's own delivery (`reply-leg.js`'s per-exec `deliver()` call) never passed an `inboundMsgId`, so a duplicate delivery for a message the cold leg had already answered was NOT refused — proven red on a clean worktree with the wiring absent: a direct duplicate call for the same conversation posted a third message where two were expected.

## Mechanism
`deliverToOwner`'s guard reads `inboundMsgId` as an explicit call argument, never a lookup — by design, to avoid the stale-map bug class this component's `_issues.md` (see the prior entry) already measured. `reply-leg.js#arm(chatThreadId)` had no second parameter to carry that identity into its own `deliver()` call, so the cold leg's real delivery always passed `inboundMsgId: undefined`, leaving the guard permanently dormant on that leg.

## Attempts
First attempt held for the warm leg only (10ad7956) — deliberately: at that commit, `reply-leg.js` carried a large, unrelated, in-flight uncommitted edit (`dup-revive-lineage`'s session-lineage-fork fix, later committed as `1f7e3fcf`) and completing the cold-leg wiring then would have required editing the same file mid-flight. Held until that file was free.

## Fix
`arm(chatThreadId, inboundMsgId = null)` now stores `inboundMsgId` on `p` (both the new-entry and re-arm branches). The per-exec delivery block's `deliver({...})` call passes `inboundMsgId: p.inboundMsgId`. On a SUCCESSFUL delivery, `p.inboundMsgId` is cleared to `null` immediately — this is the part that is NOT obvious and was caught by this seat's own extended probe before landing: `pending` entries in `reply-leg.js` persist across MANY execs on one conversation with no fresh `arm()` in between (wakes, a revive's corrective turn, multi-page log continuations — `probe-chat-reply-leg.js` checks g/h/i/j/k/l/n/o/p/q are all exactly this shape). Leaving `p.inboundMsgId` set after the first delivery would make every one of those legitimate later execs read as "answering an already-answered message" and get wrongly refused — replacing the intended duplicate-suppression with wrongful silence on ordinary reply-leg traffic. Clearing it the moment the FIRST answer for a cycle lands scopes the guard to exactly the race it is meant to catch (a second delivery attempt racing the same still-open cycle) without touching anything reply-leg's own revive/wake/compaction machinery already owns.

## Consequences
Built against `reply-leg.js` as landed by `1f7e3fcf` (the store-status-terminal revive gate) — that fix's own logic (the `storeCaughtUp` branch) is untouched; the `inboundMsgId` threading sits entirely in `arm()` and the pre-existing successful-delivery branch, touching none of `1f7e3fcf`'s lines. `probe-chat-reply-leg.js` re-run clean, unmodified, after this edit.

## Verification
`probe-chat-duplicate-idempotency.js` scenario (d): a real `onChatMessage` → `arm()` → ticker-scripted exec → `status`/`logs` → `replyLeg.tick()` pass, asserting (d0) the cold leg's own `deliver()` posts the real answer, (d1) a system notice on that same conversation does not disturb anything, (d2) a direct duplicate carrying the SAME `inboundMsgId` the cold leg just answered with is refused, (d3) a genuinely new follow-up on the same conversation still gets answered afterward (the guard did not latch the whole conversation shut). Red-first: a `git worktree add HEAD` copy with only `reply-leg.js` left at its pre-wiring state reproduces d2's duplicate exactly (3 posts instead of 2); restored, all 20 checks (a–d) pass. `node ignite/deploy/probe-suite.js --only probe-chat-reply-leg` green throughout. Not yet deployed.

## ATTENTION
1. `p.inboundMsgId` is cleared on the FIRST successful delivery of a cycle, not held for the cycle's whole life — do not "fix" this by holding it longer; that reintroduces the g/h/i/j/k/l/n/o/p/q false-refusal class measured in the prior entry.
2. The guard still requires `answersOwnerAsk: true` on BOTH the marking call and the checking call (unchanged from the prior entry) — a P3 notice never carries `inboundMsgId` in the FIRST place at any of reply-leg's `postNotice`/give-up/dead-air call sites, so it can never participate in this guard either way; this was verified again on the cold path specifically (d1).
3. `arm(chatThreadId, inboundMsgId)`'s second argument is optional and defaults to `null` — the two bus-ferry-originated `arm()` calls (`routeBusRowToMaster`/`routeToAgentThread`) still call it with one argument and are correctly left unguarded (no owner-message identity exists for them to guard on).
- clear inboundMsgId on first success only — do not hold it for the whole cycle, see prior entry's g/h/i/j/k/l/n/o/p/q false-refusal class
- built against reply-leg.js 1f7e3fcf (store-status-terminal gate) — untouched by this fix
