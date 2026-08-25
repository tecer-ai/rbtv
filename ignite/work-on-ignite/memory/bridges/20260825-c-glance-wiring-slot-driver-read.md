# 20260825-c-glance-wiring-slot-driver-read — glance wiring: slot driver, readers, status transport

kind: creation
component: bridges
date: 2026-08-25
commit: b3d3425c
deployed: no
pin: ignite/bridges/chat/probes/probe-chat-glance-wiring.js
components: gateway,server,cli,state-store,observation

## Motivation
`system-digest.js` (§5) and `status-line.js` (§6) landed on 2026-08-24 BUILT AND PROVEN and
unreachable: their own creation entry says so — "`index.js#main()` wires no slot driver, no
ask/condition readers and no Slack status port". Every port was injected and nothing injected
them, so the digest never ran, the status line answered `no-status-port` on every trigger, and
the owner had neither of the two phone-glance surfaces [T5-R13, C-12, D-6-ruling] the baseline
deleted the old ones for.

## Design
ONE new module, `bridges/chat/glance.js`, holding the composition and nothing else — no
rendering, no schedule arithmetic, no trigger list. It is a separate file from `index.js` for a
testability reason that is load-bearing: `main()` resolves credentials and opens a Socket-Mode
connection, so a wiring probe could never drive the clock, the readers and the status port
through it. `buildBridge` constructs the glance; `main()` starts its clock.

The slot beat is 30 s, not 60. A slot is the instant `minute === 0` at America/Sao_Paulo, so a
one-per-minute driver must keep phase for the life of the process; one skipped beat under load
silences a whole slot. `isSlot` is asked FIRST, so every non-slot beat costs no gateway call.

Open conditions come from `observation/emitter.js`'s OWN `readOpenConditions`, over the registry
file the daemon writes, with `reload()` before every read — the emitter loads its rows once at
construction and the WRITER is another process. Rejected: a local reader of that JSON, which
would be the "second source of alarm truth" the digest's own entry rejected. The emitter instance
here is handed a `post` that THROWS, so the bridge reads alarms and can never compose one
[T4-R10].

## How it works
`createGlance({ outbox, askRecord, setStatusText, systemChannelId, workspaceRoot, … })` returns
`{ digest, statusLine, checkSlot, start, stop, onTrigger, readOpenConditions }` and takes the
bridge's OWN parts: `bridge.outbox` (so an unacked digest leaves the same `pending-delivery`
record every other post leaves [C-17]) and `bridge.askRecord` (newly exposed on the bridge, so
the read and the two writes travel one intent through one forwarder). `checkSlot` asks `isSlot`,
then reads the asks, then hands the digest a per-check snapshot through a closed-over cell.
`start()` arms the beat with a re-entrancy guard and unrefs the timer, in the bus-ferry's and
reply-leg's house style; `checkEveryMs` is injectable so a probe can watch it fire. The status
transport is a new `setStatusText` on `slack-socket-mode.js` — `users.profile.set` carrying
`status_text` ONLY, so the bot's emoji and every other profile field are untouched; another
outbound POST on the bot token, so the outbound-only property stands. `RBTV_SYSTEM_CHANNEL_ID`
(or `system_channel_id` in the bridge config) resolves the channel in `config.js`, the SAME env
name the daemon and the watchdog shim read.

⚠ An unreadable ask set SKIPS the slot. `ask-store.js#listOpenAsks` answers `null` on a refusal
and `[]` when nothing waits; `system-digest.js` collapses both to `[]` by construction
(`(await readOpenAsks()) || []`), so the distinction is drawn in `checkSlot` BEFORE the digest is
asked anything — otherwise a gateway outage posts "• none open", moves the baseline on Slack's
ack, and re-posts everything when the daemon returns.

## Consequences
Nothing was replaced or deleted; `system-digest.js` and `status-line.js` are untouched. The
bridge gained a require on `../../observation/emitter` — a cross-component read inside `ignite/`,
which `probe-chat-boundary.js` still passes (its sibling-reach pattern names `server|gateway|cli`,
and the emitter is a consumed wall, not a capability). `chat-bridge.js` now returns `askRecord`.
Two named loose ends, deliberately NOT invented here: the §6 triggers are constructed but not
FIRED (they live in the ask door, the mechanical door and the reply leg, and each needs its own
`glance.onTrigger(...)` at its own moment — an eighth trigger or a mistimed one is a poll loop
against Slack), and `readBlockedCount` stays at its default `0` because no read door for
blocked-on-human lanes or paused goals exists from this process.

## Verification
`bridges/chat/probes/probe-chat-glance-wiring.js` — 20 checks, exit 0, mocked Slack (injected
`fetchImpl`), mocked clock, fake forwarder, no socket and no live post. It proves the driver
fires by itself on a slot and stays silent at 03:00, that the post reaches the transport in the
system channel, that a daemon-emitted alarm becomes visible to the bridge AFTER construction,
that a refused and a thrown ask read both skip the slot with the baseline unmoved while an EMPTY
set still posts, that an unacked digest retries the same outbox record, and that a §6 trigger
writes the status text while a non-trigger does not. Four mutations were run by hand and each
reddened exactly the rows that claim to cover it: dropping the null-guard, dropping `reload()`,
removing `setStatusText` from the transport, and firing the driver on every beat. Full
`bridges/chat/probes`: 27/27 GREEN. Not deployed: worktree `5-workbench/rbtv-redesign`, branch
`ignite/core-redesign`.

## ATTENTION
1. The distinction between `null` (could not read) and `[]` (nothing is waiting) must stay in the
   WIRING. The digest cannot make it — it ors the reader's answer with `[]` — so any future
   caller that hands the digest a reader directly re-opens the empty-digest-then-re-post defect.
2. `reload()` before every condition read is not defensive habit. The writer is the daemon in
   another process, so a version without it renders the alarm set as it stood when the bridge
   last started, which is indistinguishable from "nothing is wrong".
3. The glance's emitter instance must keep a throwing `post`. It exists to READ; the moment it
   can emit, the bridge is a second alarm composer and [T4-R10] is undone across a process
   boundary rather than inside one.
4. Do not start the slot driver from `buildBridge`. Construction happens in every probe; a live
   2-hourly clock acquired as a side effect of building a bridge is a post nobody asked for.
5. `setStatusText` sends `status_text` and nothing else on purpose. Adding `status_emoji` — which
   looks like a completeness fix — CLEARS the bot's emoji on every one of the seven triggers.
- null (could not read) vs [] (nothing waiting) must stay in the WIRING — the digest cannot make that distinction
- the bridge's emitter instance must keep a throwing post: it reads alarms, it never composes one
