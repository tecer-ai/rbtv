# 20260902-c-digest-open-ask-rows-get-a-rea — digest open-ask rows get a real Slack link

kind: creation
component: chat
date: 2026-09-02
commit: f96d14e6d5599f3cf370bfe8e94e05c009d884de
deployed: yes
pin: ignite/chat/probes/probe-chat-glance-wiring.js

## Motivation
The system digest's "open asks" section listed each waiting question as plain text with no way to
jump to it in Slack — the owner had to search the channel by hand. Owner ruling `d-digest-ui`
called for a real, tappable Slack link on each row. `open_asks` on disk carries three different id
shapes (a thread timestamp, a Slack channel id, or a minted `recovery-` id for an ask that never
reached Slack), and each demands a different treatment — a naive "always link" would either throw
on the shapes that cannot be linked or fabricate a link that goes nowhere.

## Design
`glance.js#checkSlot` now resolves and attaches `ask.link` BEFORE the digest renders, rather than
`system-digest.js` resolving it itself — `system-digest.js` only renders an already-set `ask.link`,
keeping the rendering layer free of Slack-shape knowledge. `linkForAsk` classifies the id by regex
(`ASK_ID_CHANNEL_RE` for a Slack channel id, `ASK_ID_THREAD_TS_RE` for a thread timestamp) and
treats each shape differently: a thread-ts id resolves the goal's channel through an injected
`resolveGoalChannel` and builds a thread permalink via `forward-path.js`'s existing
`slackThreadPermalink` (exported for reuse rather than re-derived, so the `<channel>/p<ts>`
transform has exactly one author); a channel-shaped id links the channel directly (the goal-master
approval flow posts to the channel itself, not a thread); a `recovery-` id or anything unrecognized
gets NO link — a dead link is worse than no link, since the owner cannot tell which he tapped.
Resolution failure (no resolver wired, the goal has no channel yet, the resolver throws) degrades
to no link and never throws out of `linkForAsk` — a missing link must never cost the digest slot.

## How it works
`index.js#buildBridge` wires `resolveGoalChannel` into `createGlance` from the `goalChannels` map
the bridge already builds (`async (goalId) => (await goalChannels.resolveChannel(goalId)).channelId`);
`chat-bridge.js` needed no change since it already exposed `goalChannels`. `checkSlot` maps every
open ask through `linkForAsk` with `Promise.all` before handing the array to
`digest.check(at)`. `forward-path.js`'s `slackThreadPermalink` was previously private to that file
and is now exported via `module.exports` for this reuse — additive, not a behaviour change to
`forward-path.js` itself.

## Consequences
No pre-existing assertion needed changing in `probe-chat-glance-wiring.js` — only its `ask()`
fixture helper gained an optional 5th `extra` parameter (additive, default `{}`). The seat that
built this (`digest-ask-link`) deviated from the plan text, which named `chat-bridge.js` as the
file to wire `resolveGoalChannel` from; by content, `createGlance` is actually constructed in
`index.js#buildBridge`, not `chat-bridge.js`, so the wiring landed there instead — flagged in the
seat's own report, not corrected against the plan text. Landed alongside sibling commit
`829a7b43` (goal-scoped condition rows get a channel link via a separate path,
`system-digest.js#renderConditionRow`) — the two share the `d-digest-ui` ruling but touch disjoint
code (asks vs. conditions) and were built by different seats running concurrently; no shared file
required coordination.

## Verification
`node ignite/chat/probes/probe-chat-glance-wiring.js` → `EXIT=0 PASS=true CHECKS=27` (was 20 checks
before this change; +7 for the four id-shape cases plus the resolution-failure degrade path).
`node ignite/chat/probes/probe-chat-glance.js` → `EXIT=0 PASS=true CHECKS=30` (unrelated file,
unaffected). Manually verified against the LIVE `open_asks` table
(`.rbtv/runtime/ignite/heart.db`, read 2026-08-31): a real thread-ts ask
(`1788115731.908659`, goal `meet-transcript-summarizer-planning`) resolved its channel via
`stools read --workspace ignite-owner --list-channels` and the resulting permalink
(`https://slack.com/archives/C0BUBKJQ3FA/p1788115731908659`) read back the exact expected Slack
thread via `stools read --permalink`. Committed `f96d14e6`, deployed on branch
`ignite/core-daemon` (live tree `e8524c31` carries this commit).

## ATTENTION
1. `linkForAsk` classifies by REGEX on the id shape alone (`ASK_ID_CHANNEL_RE` /
   `ASK_ID_THREAD_TS_RE`), never by an explicit type field — a future ask-id format must either
   match one of these two shapes or fall into "no link", by design. Adding a new id shape that
   should link requires a new regex branch here, not just a new writer of `open_asks`.
2. Resolution failures (no resolver, no channel yet, a throwing resolver) MUST keep degrading to
   `link: null` and must never let an exception escape `checkSlot` — a digest slot must always
   post even when a link cannot be built. Do not add a `try/catch`-free resolver call here.
3. `forward-path.js#slackThreadPermalink` is now a shared export reused by `glance.js` — do not
   re-derive the `<channel>/p<ts>` transform a second time anywhere else; import it instead.
- linkForAsk classifies by id-shape regex; failures must degrade to link:null
- slackThreadPermalink is the shared export
