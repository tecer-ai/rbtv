# 20260824-c-thread-per-ask-posting-and-the — thread-per-ask posting and the one ask-release door

kind: creation
component: bridges
date: 2026-08-24
commit: 3477c6bf
deployed: no
pin: bridges/chat/probes/probe-chat-ask-release.js
components: team-kit

## Motivation
`spec-owner-io` §2 and §3 pin thread-per-ask and one release rule, and neither had an
implementation. Every ask batch must open a NEW thread in the goal channel [D18, T5-R8], the
opening message must carry the §3 line, and — the part the redesign exists for — an ask must be
released ONLY by an authorized sender replying in that EXACT thread [D-4-ruling, C-3, T1-R12].
The pre-D89 door guessed instead: `ask-store.js#markAnswered` defaulted to the oldest open ask and
`messages.open_escalations` retired a seat's oldest still-open halt on ANY unnumbered owner answer,
so a reply about one question closed a different one, HEAD-only, invisible in Slack.

## Design
One module, `bridges/chat/ask-thread.js`, holding exactly two acts and no state. It is a CALLER of
things that already exist rather than a second copy of any of them: `reply-grammar.js` parses,
`outbox.js` posts, `ask-store.js` sends the thirteenth gateway intent `record-owner-ask`, and the
daemon stamps the row. Nothing here holds a store handle, spawns a child, or requires a sibling —
`probes/probe-chat-boundary.js` enforces that and stayed green.

The ask id IS the Slack `thread_ts` [D-8], so the `display_suffix` in the §3 line cannot exist
before Slack answers. Three shapes were weighed: a placeholder suffix (rejected — a lie in the one
field that tells two open asks apart), posting the lead line as a thread reply (rejected — §3 says
one message), and POST-THEN-REWRITE. The third was taken: `transport.updateMessage`
(`chat.update`) was added to `slack-socket-mode.js` for this one caller, and `createAskThreads`
REFUSES construction without it, so a wiring gap fails at boot rather than silently at the first
ask.

The authorized-sender set is injected from instance config (`config.js#allowlist`), never repo
content, and an EMPTY set authorizes nobody — "none configured" must not read as "everyone".

## How it works
`postAsk` refuses a non-designated seat at the door [T2-R14], posts the body with `thread_ts: null`
(a new thread, always), takes the acked `ts` as the ask id, rewrites that message to
`{marker} {display_suffix} · {seat_name} · {label}` + body, then calls `askRecord.openAsk`.
`postNote` does the same with the 💭 marker and deliberately calls nothing after — §2.1: only ❓
mints a record, so a note can never read as `open`.

`release` runs §2.4 in its own order. A reply whose `threadTs` is not `===` the `askId` is a
no-op; an unauthorized sender (including this bot) is a SILENT no-op — a NACK there would let
anyone in the channel make the bot talk back. An unrecognized first token posts the verbatim §4.5
NACK through the outbox in the SAME thread and the ask stays `open`. `pause`/`resume` are
recognized but release nothing (§4.2). A recognized outcome writes the reply to
`.rbtv/goals/<goal>/coordination/asks/<ask>.reply.txt` FIRST — §2.4.5 has the relaunched seat read
it from disk, and the reap fires the relaunch in the same act, so the seat can be reading before
the reap call returns — then calls `askRecord.reapAsk`, which is the ONE act that reaps the wait
and signals the relaunch (§2.8).

## Consequences
The reply copy is a plain file written by the bridge process, beside the daemon's ask copy that
`server/heart/ask-record.js#askCopyPath` writes. It is NOT a second writer of one fact: the reap
payload deliberately carries no corpus, and widening that intent's schema would have been an owner
act plus a concurrent edit to `server/heart`. Two files, two facts, one writer each.

`ask-store.js` needed no change — it had already lost `markAnswered` and its oldest-open default
when the thirteenth intent landed. `reply-leg.js` needed none either: its release already runs
through `chat-bridge.js#deliverToOwner` with the exact `chatThreadId`.

NOT WIRED YET. `chat-bridge.js` does not construct this module and no inbound path calls
`release`, so the ask door is built and proven but not yet reachable in production. That wiring and
the `bus-ferry.js` park deletion are named in this seat's report as the two open ends.

## Verification
`probes/probe-chat-ask-release.js`, new, 18 checks, EXIT=0: the §3 line byte-exact for both
markers, a new thread per ask with `thread_ts: null` and the acked ts as the id, the line stamped
onto that message, exactly one record for ❓ and none for 💭, a non-interact refusal that posts
nothing, a re-ask minting a fresh id and a second record, wrong thread / unauthorized sender / bot
self-reply each releasing nothing and NACKing nothing, an unparsed token producing the verbatim
NACK in-thread with zero reaps, a recognized token reaping EXACTLY once with the reply on disk, and
`pause {goal}` releasing nothing. The whole `bridges/chat` probe directory is 23/23 GREEN including
`probe-chat-boundary`. No live Slack post and no daemon: outbox, ask sender and `chat.update` are
injected fakes. Not deployed — worktree branch `ignite/core-redesign`.

## ATTENTION
1. The ask id is the Slack thread and Slack mints it on the way back, so the §3 opening line CANNOT be composed before the post. Any future edit that tries to build the line first will either invent a suffix or drop the field; the post-then-rewrite order is the whole design, not an optimization.
2. `createAskThreads` throws without `updateMessage`. That is deliberate — a bridge that cannot rewrite cannot post a conforming ask — so an embedder adding this module must wire the transport, not stub the hook.
3. An empty authorized-sender list authorizes NOBODY. A deployment that forgets `allowlist` gets a bridge that ignores every reply, which is the correct fail-closed direction but reads exactly like a broken parser. Check the config before debugging the grammar.
4. An unauthorized reply is ignored in SILENCE, never NACKed. A NACK there is a reply-amplification door: anyone in the channel could make the bot post on demand.
5. There is no oldest-open and no `re:` fallback in this module and there must never be one. `release` refuses without an exact thread match, which is what stops a reply to one question closing another.
- the ask id is the Slack thread Slack mints on the way back, so the opening line is stamped by rewriting the posted message, never composed before it
