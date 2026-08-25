# 20260825-c-the-watchdog-alarm-shim-s-slac — the watchdog alarm shim's Slack transport, behind two walls

kind: creation
component: capabilities
date: 2026-08-25
commit: b3f71a70
deployed: no
pin: ignite/capabilities/daemon-watchdog/probes/probe-watchdog-alarm-transport.js
components: bridges,observation

## Motivation
`tool/watchdog-alarm.js` shipped on 2026-08-25 with `resolveSend()` returning a refusal BY
DESIGN, and its own creation entry named the seam: "the outbox's Slack transport is the chat
bridge's to wire, so watchdog alarms currently stop at a `pending-delivery` record". That record
is durable [C-17] and no alarm is lost — but a durable record is not an alarm the owner ever
sees, and the whole component exists because a 3h05m outage produced nothing the owner saw.

## Design
ONE line, by the shim's own design: `resolveSend()` builds the chat bridge's OWN sender
(`bridges/chat/slack-socket-mode.js#sendToOwner`) rather than composing a second
`chat.postMessage` here — the same argument that put this shim in the watchdog's tree instead of
minting a second emitter. `createSlackSocketMode` opens nothing until `start()`, which this
process never calls, so no Socket-Mode session is held and the outbound-only property
`probe-chat-outbound` proves is untouched. The constructor's WebSocket requirement is satisfied
with a stand-in that throws if anything ever tries to open one: a watchdog that could not raise
an alarm because the runtime lacked a global `WebSocket` would be blind for a reason that has
nothing to do with the alarm path.

TWO WALLS, IN ORDER. `RBTV_WATCHDOG_NOTIFY_FILE` — this tool's "send nothing, write what you
would have sent" sink — is checked BEFORE the token, for `deadman_ping()`'s exact reason: a probe
or a rehearsal that reached real Slack because the shell happened to carry a bot token would post
into the owner's workspace from a test. Absent `SLACK_BOT_TOKEN` is a refusal, not a drop: the
record is minted `pending-delivery` with the reason on the row, which is the behaviour every
prior pass had.

## How it works
`resolveSend()` returns a sink-refusing sender when `RBTV_WATCHDOG_NOTIFY_FILE` is set, a
token-refusing sender when `SLACK_BOT_TOKEN` is unset, and otherwise
`createSlackSocketMode({ botToken, apiBase: SLACK_API_BASE, onMessage: () => {} }).sendToOwner`.
`createOutbox` already mints the record BEFORE calling it, so the three arms differ only in what
the row's `state` and `last_error` end up saying. `onMessage` is a no-op and must stay one: this
process is outbound-only, and a callback here would be a second consumer of owner messages living
outside the bridge that owns that path. Nothing else in the shim changed —
`RBTV_SYSTEM_CHANNEL_ID` is still read from the environment with its loud refusal, and the
emitter still throws on a half-composed alarm.

## Consequences
Nothing was replaced or deleted. `probe-watchdog-bit7-silence.py` still asserts a
`pending-delivery` record and still passes, because it sets `RBTV_WATCHDOG_NOTIFY_FILE` and the
new wall answers before the token is ever read — which is exactly why that wall is first.
`daemon-watchdog.md` § Environment gained `SLACK_API_BASE` and now states that `SLACK_BOT_TOKEN`
also arms the shim's transport. The daemon-side caller of the same emitter deliberately does NOT
get a token (`r-cutover-gated`): its alarms stay `pending-delivery` and reach the owner through
the 2-hourly digest.

## Verification
`capabilities/daemon-watchdog/probes/probe-watchdog-alarm-transport.js` — 11 checks, exit 0. Mock
Slack on an ephemeral loopback port via `SLACK_API_BASE`, a scratch workspace per leg, and a
CLEAN environment per run so an ambient `SLACK_*` in the operator's shell cannot decide what it
measures. It proves: with a token the alarm reaches `chat.postMessage` in the system channel and
the record flips to `delivered` carrying Slack's own ts; without one it is `pending-delivery`
naming the missing token; with the sink set a PRESENT token sends nothing; and both pre-existing
refusals (no system channel, a half-composed alarm) still exit 1 having posted and minted
nothing. Red-first control run by hand: restoring the pre-wiring `resolveSend` stub reddens the
delivery arms, and checking the sink AFTER the token reddens the dry-wall arms. The four
pre-existing probes of this component re-run green. NOT deployed: worktree
`5-workbench/rbtv-redesign`, branch `ignite/core-redesign`; no unit was restarted and no real
Slack workspace was contacted.

## ATTENTION
1. The "send nothing" sink must stay ahead of the token check. Reversed, every probe and every
   rehearsal on a box whose shell carries `SLACK_BOT_TOKEN` posts into the owner's real
   workspace — and the BIT-7 probe would start passing for the wrong reason.
2. `start()` is never called on the transport this shim builds, and must not be. The watchdog is
   a 60-second one-shot; a Socket-Mode session opened here would outlive nothing, hold a
   connection nobody reads, and give a liveness tool a network dependency it does not need.
3. A delivered alarm is still ONE emission per episode (spec-owner-io §9.2). Wiring the transport
   did not make the alarm repeat; "why did it only tell me once" is answered by the digest, not
   by a second emission here.
4. The daemon does NOT get this treatment. `r-cutover-gated` keeps a credentialed transport out
   of the daemon process; the asymmetry is deliberate, because this tool must speak when the
   daemon and the bridge are the things that are down.
- the send-nothing sink is checked BEFORE the token — reversed, every probe posts into the owner's real workspace
- the daemon deliberately gets no token (r-cutover-gated); the asymmetry with this tool is the point
