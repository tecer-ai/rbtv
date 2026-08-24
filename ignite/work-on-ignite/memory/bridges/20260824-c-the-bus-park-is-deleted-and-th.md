# 20260824-c-the-bus-park-is-deleted-and-th — the bus park is deleted and the ask door is wired

kind: change
component: bridges
date: 2026-08-24
commit: a94d6f61,9a52de31
deployed: no
pin: bridges/chat/probes/probe-chat-ask-release.js
components: team-kit

## Motivation
A `to: owner` row on the coordination bus could be SWALLOWED by any of three gates in
`bus-ferry.js` — the goal's `execution-mode`, the sending seat's `human-interactive:` flag, or
that seat's own `fallback: park` arm. "Parking on the bus" is not a queue: nothing was posted on
any surface, the cursor ADVANCED, and no retry, replay or view ever surfaced the row again. The
autonomous goals the ferry exists for are exactly the ones whose seats are never flagged, so a
work-content question from the seat nobody was watching died in silence. That is the failure the
core redesign exists to end [D24, T2-R17, D-7-ruling].

Beside it, the ask door built in `3477c6bf` was reachable by nothing: `chat-bridge.js` neither
constructed `ask-thread.js` nor called `release` from any inbound path, so thread-per-ask and the
one release rule were proven in a probe and absent from production.

## Design
Every park rung is answered by a RULING rather than by a gate, so the rungs are deleted rather
than loosened. Goal-level interactive/autonomous mode is dead [D24] — interactivity is a per-seat
property and a goal may not mute a seat. A non-interact seat's work-content question becomes a
daemon-posted ask [T2-R17, D-7-ruling], which is a real ❓ thread. `fallback: park` described an
owner who could not be REACHED; under thread-per-ask he can be, so `fallback:` survives as a
render mark only and the mark table deliberately carries no entry for `park`.

`goalExecutionMode`, `seatIsHumanInteractive` and `seatFallback` stay EXPORTED. Deleting a gate is
not deleting a predicate — other consumers hold all three, and `seatIsHumanInteractive` is
immediately re-used as the [T2-R14] send-time designation check at the ask door.

The wiring is one map and one injection, not a second ask model. `postAsk` is INJECTED into the
ferry, so an embedder that wires nothing gets the agent-thread and DM legs unchanged, and the
bridge holds the goal→channel resolution and the ask-record sender the ask module deliberately
does not. `goalChannelFor` was extracted because a second copy of the `resolveChannel` call is
exactly where a later edit would quietly put the in-memory channel map back in charge.

## How it works
Outbound: the ferry renders the row, labels it `recovery` for the leader's traffic and any
escalation and `work-content` for everything else [D-7-ruling], and calls the injected `postAsk`.
`chat-bridge.js#postOwnerAsk` resolves the goal's channel and calls `ask-thread.js#postAsk`, then
records `askThreads[<channel>:<threadTs>] = { goalId, seat, askId, label }` and the thread's reply
address. A 💭 note is NOT entered in the map — it mints no record [§2.1], so there is nothing to
release. On `seat-not-interact` the ferry posts NOTHING and logs the refusal naming the seat:
[T2-R14] refused at send, and still not a park, because the cursor does not move and the bounded
retry keeps the row.

Inbound: `onChatMessage` looks the raw event's `<_channel>:<_threadTs>` up in `askThreads` BEFORE
every other leg and hands a hit to `release`. It does not fall through — a fall-through would mint
a sitting on an unauthorized remark and answer an authorized one twice. The key is the raw event's
because for goal traffic the routed conversation id IS the channel and cannot tell one ask thread
from another. The map entry is dropped only on an ACTUAL release; wrong thread, unauthorized
sender, unparsed token and a mechanical verb all leave the ask `open`.

`askThreads` is persisted additively in the bridge state file with `STATE_VERSION` unchanged, and
carries no ask STATE — state is `open_asks`, daemon-side.

## Consequences
`bus-ferry.js` emits no `PARKED` line at all, and the two mutation entries whose anchors no longer
exist — `gates-removed` and `fallback-park-rung-removed` — were deleted with the rungs they
mutated, since an absent anchor is not applied and the arm would report "anchor missing" while
measuring nothing. `probe-chat-agent-thread` arms 2, 3, 4b and its three S-13 checks were inverted
to measure that the row TRAVELS, and `probe-chat-bus-ferry`'s W8-A likewise. The chat README's
"two gates" section is kept as a record of the deleted behaviour rather than removed, so a reader
of older code or of the `messages.md` history can still tell what the rungs were.

`probe-chat-agent-thread` unwires the ask door (`postAsk: null`, the documented unwired
configuration) — wired, every `to: owner` row in that file would become a ❓ thread and the probe
would stop measuring its own subject, the per-AGENT thread, which is still the leg a row takes
when the ask door refuses it.

`ask-thread.js` now accepts a botUserId GETTER. The bot identity is resolved from Slack at
`start()`, long after the module is constructed, so the captured value was `null` forever and the
self-reply guard was dead code that read as live.

## Verification
`probes/probe-chat-ask-release.js`, 27 checks, EXIT=0 — the 18 module-level checks from `3477c6bf`
plus a new section E of 9 driving the REAL bridge with a fake transport and forwarder: a
work-content bus row becoming a ❓ thread with the §3 lead line on the fixture that was a
guaranteed park under the old ladder, the `record-owner-ask` intent, a reply in the wrong thread,
an unauthorized sender refused silently at the door with nothing posted and nothing minted, the
verbatim NACK posted in-thread, the release with the reap counted at EXACTLY once and the reply on
disk, a free re-ask in a fresh thread, the [T2-R14] refusal proven distinct from a park (logged,
cursor not swept, no `/PARK/i` line anywhere), and a release that still works after a restart off
the persisted map. The whole `bridges/chat` probe directory is 23/23 GREEN, `probe-chat-boundary`
included. No live Slack post and no daemon. Not deployed — worktree branch `ignite/core-redesign`.

The team-kit half of the same deletion (`messages.open_escalations`' oldest-open arm) is verified
directly rather than through `coord.py selftest`, which today ABORTS at check 644 inside another
seat's in-flight renew-gate work, long before the reworked W8 rows at ~15130 can run: on a
two-halt fixture an UNNUMBERED owner answer leaves both rows open and `re: <n>` removes only the
row it names.

## ATTENTION
1. `goalExecutionMode`, `seatIsHumanInteractive` and `seatFallback` are still exported and still read by other consumers. Seeing them in `bus-ferry.js` does NOT mean a gate survived — grep for a caller inside the row loop before concluding anything about parking.
2. The inbound ask door must stay keyed on the RAW event's `_channel`/`_threadTs`. `route.conversationId` for goal traffic is the CHANNEL, so keying on it would match every message in the channel, or none.
3. An ask-thread hit does NOT fall through to the other legs, and that is deliberate. A "fix" that lets it continue mints a sitting on an unauthorized remark and answers an authorized reply twice.
4. `askThreads` must stay in the state file. Lose it and the owner's answer after a restart is handled as ordinary goal traffic, the ask is never released, and the seat waits forever — the pre-redesign silence rebuilt by accident.
5. The ask door is UNWIRED in `probe-chat-agent-thread` on purpose. Wiring it there does not make that probe stronger; it makes it stop measuring the per-agent thread leg entirely.
- a to: owner row can no longer be swallowed — the three park rungs are gone and the ferry emits no PARKED line at all
