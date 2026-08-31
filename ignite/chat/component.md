---
description: Read before touching the Slack bridge - the reply leg, the ask and approval threads, the outbox, the bus ferry, the digest and the chat session config that all live in this one component.
---

# chat

The chat bridge. Law is `1-projects/build-ignite/redesign/specs/spec-component-map.md`
§1 under [D22], [T4-R11], [C-15]: the old `bridges/` wrapper held exactly one child,
so the child IS the component now. Same tree, moved with history; nothing was
reshaped and no symbol changed.

Arrived with the same move (`spec-component-map` §2): `chat/bus-answer.js` (the
bus-answer leg), `chat/chat-session-settings.json` and `chat/senders.example.yaml`
(the chat session config that had no other home).

The module inventory below is append-only and predates the move.

## Inventory (append-only)

## reply-grammar

`reply-grammar.js` — parse an owner Slack reply into a canonical first-token
outcome plus comments, or a parse-failure that names which verbatim §4.5 NACK
applies. Law: `spec-owner-io` §4. Pure function. Probe:
`probes/probe-chat-reply-grammar.js`.

## outbox

`outbox.js` — durable Slack outbox [C-17]: every post starts `pending-delivery`
and flips `delivered` only on Slack ack. Query by state / kind / channel_id /
goal_id / ask_id (newest-first) and get-by-`outbox_id`. Store:
`.rbtv/runtime/ignite/outbox.json`. Probe: `probes/probe-chat-outbox.js`.

## ask-thread

`ask-thread.js` — thread-per-ask posting and the ONE door that releases an ask
(`spec-owner-io.md` §2.1, §2.4, §3). Every ask batch opens a NEW thread in the
goal's channel [D18, T5-R8]; the opening message's `thread_ts` IS the ask id
[D-8], so the message is posted and then rewritten (`transport.updateMessage`,
`chat.update`) to carry the §3 line `{marker} {display_suffix} · {seat_name} ·
{label}` — the suffix cannot be composed before Slack mints the id. Only ❓ mints
a record (through `ask-store.js`, the `record-owner-ask` gateway sender); 💭
mints none. A non-interact seat's ask is refused at this door [T2-R14].

Release is §2.4 in order: the reply must be in the EXACT thread and its sender
must be in the instance-config authorized set (never repo content) — anything
else is a silent no-op; an unrecognized first token gets the verbatim NACK
in-thread through the outbox and the ask stays `open`; a recognized outcome
persists the reply beside the daemon's ask copy
(`.rbtv/goals/<goal>/coordination/asks/<ask>.reply.txt`, what the relaunched
seat reads) and reaps the wait + fires the relaunch in ONE act. The pre-D89
"oldest still open ask" and `re: <n>` release doors are DELETED [D-4-ruling,
C-3, T1-R12] — a reply that names no thread this module owns releases nothing.
Probe: `probes/probe-chat-ask-release.js`.

**How it is reached in production.** `chat-bridge.js` constructs the module and
holds the one map it needs: `askThreads`, `<channel>:<threadTs>` → the ask's goal,
seat and id, persisted additively in the bridge state file (`STATE_VERSION`
unchanged). The ask's own STATE lives in `open_asks`, daemon-side; what the map
carries are the bridge's facts about the THREAD — `kind` (which dispatch a parsed
token takes), `paused` (a reject-and-paused approval) and `released` (this bridge
already released this thread's ask).

**A released thread is MARKED, never deleted** [G-second-brain-43-0828-2119,
owner-ordered 2026-08-30]. Deleting it made the owner's next message in that thread
unrecognizable, so it fell through to the goal-channel forward path and summoned a
goal-master sitting that read a bare `a` as a check-in (3× on 2026-08-28). A later
authorized, parsed reply in a released thread is refused IN the thread — `already
answered`, naming the outcome recorded — with no reap, no approval dispatch and no
forward. Bound on the map's growth: a count, not a timer. At most `RELEASED_KEEP`
(200) released entries are kept and the oldest by `releasedAt` are evicted when a
new one is marked; evicting one only restores the pre-fix fall-through for a reply
to a months-old answered thread. An entry written before `released` existed has none
of these keys, loads as `released: false`, and behaves exactly as it did — the state
file needs no migration.

**The ✅ landed-answer ack.** When a reply actually releases an ask
(`released === true`, the same condition the journal's `authorized reply RELEASED
the ask` line reports), the bridge stamps `white_check_mark` on the owner's own
message through `transport.react`. It is deliberately NOT the ⏳ pending marker: ⏳
means "accepted, an agent will answer you" and is removed when that answer lands,
while ✅ means "your answer landed" and is never removed. Every §2.4 refusal gets no
ack — each already has its own visible outcome or is silent by ruling. Best-effort
on the shared reaction chain, like every other reaction here.

Outbound: the bus ferry posts every `to: owner` row through the bridge's
`postOwnerAsk`, which resolves the goal's channel and calls `postAsk`. The three
park rungs that used to swallow such a row are deleted (see the README's gate
section); the ONE outcome that posts nothing is the [T2-R14] refusal, which is
logged and leaves the row on the bus rather than sweeping it away.

⚑ **A row carrying `approve-commit: <sha>` is posted as an APPROVAL** (2026-08-27).
The ferry reads the header key, passes `kind: 'approval'` + `commitId` to
`postOwnerAsk`, and composes the body with `approval-thread.js#composeApprovalBody`
(the row body is the digest payload) — which is what makes the owner's `approve`
in that thread start execution instead of being delivered to the seat as a word.
The AUTHORITY is checked once, at `coord.py cmd_send` (`--approve-commit`: a
`human-interactive:` seat, an approve-package on the goal, that exact
`bound_commit`; no `--force`), because that is where identity resolves; the ferry
only fails CLOSED on a malformed sha, sending the row as an ordinary ask. Header
key only — no body sigil, so digest text can never open the door. Arm 11 of
`probes/probe-chat-bus-ferry.js`.

Inbound: `onChatMessage` checks `askThreads` BEFORE every other leg. A message in
an ask's thread is handled at the release door and does not fall through — a
fall-through would mint a sitting on an unauthorized remark, answer an authorized
one twice, and (on a thread already released) buy a goal-master sitting for a
re-send.

## approval-thread

`approval-thread.js` — the §3 approval first message and the §4.2 post-parse
dispatch (`spec-owner-io.md`; law `DESIGN-BASELINE.md` v2 §Planning approval
rows). `composeApprovalBody` puts the **GOAL NAME** and the **IRREVERSIBLE
EFFECT** on their own bold lead lines before any other body, then the digest, the
bound `commit_id` [T5-R5], the canvas link and the six accepted tokens; it
refuses to compose without a goal name or a commit.

`createApprovalDispatch` forks on the ask's `kind`, never on the token
[D-5-ruling, CF-7]: `approve` in a `kind=approval` thread is the D12 trigger, the
same word elsewhere is an outcome delivered to the seat. reject-and-close /
close close the planning goal; reject-and-pause pauses it and keeps the thread as
the sole door out, whose only later exits are `retry with:` / `approve` / `close`
[T3-R22]; reject-and-retry and `retry with:` relaunch draft + verify with the
comments as the findings list [T3-R21]. Every effect is a port — the bridge may
not spawn `planning/path_b.py` or write a lane — and a refusing port reports back
into the SAME approval thread [C-16]. Probe: `probes/probe-chat-approval.js`.

## start-execution

`start-execution.js` — the sender for the FOURTEENTH gateway intent
`start-execution` (owner ruling 2026-08-24, option (b),
`redesign-implementation/decisions.md`), which fills `approval-thread.js`'s D12
`materialize` port. The payload is the planning goal, the approval thread and the
bound commit [T5-R5] and nothing else: WHAT gets built is the approve-package the
planning goal carries, read daemon-side, and the daemon-side executor
(`state-store/heart/start-execution.js`) validates the approval binding before running
the supervised Path-B birth. The call carries a per-call timeout override
(`live-feed`'s precedent) because a birth is scaffold + mint, not a store write.
`chat-bridge.js` builds this port from its own forwarder ALWAYS and REFUSES an
injected `materialize` at construction — a stub `{ok:true}` there would tell the
owner an execution started when nothing did. Probes:
`probes/probe-chat-approval.js`, `runtime/internal-api/probes/probe-start-execution.js`.

## pause-resume

`pause-resume.js` — the mechanical door (`spec-owner-io.md` §4.2/§4.4/§4.5).
GRAMMAR + SENDER + POSTER, and nothing else. A first token of `pause`/`resume` is
the daemon's and bypasses the goal master [T5-R14]. A bare verb in a goal channel
targets that goal; elsewhere the slug is required, and a grammar failure gets the
verbatim §4.5 mechanical NACK with nothing sent. Otherwise the verb crosses the
daemon boundary as the gateway intent `pause-resume`, payload
`{verb: 'pause'|'resume', goal, chat_user}` (`chat_user` = the authorized Slack sender's
id, forwarded for the daemon's evidence text only — owner re-ruling D-4(a), 2026-08-30),
and the daemon's result
`{verb, goal, applied, actions, refusals}` is rendered back into the channel or
thread the verb arrived in. Neither verb flips an ask off `open`. No store handle,
no lane enumerator, no counter port: the resume-semantics table (`spec-recovery.md`
§4 [C-14]) lives daemon-side behind the intent, and NO SECOND COPY OF IT MAY EXIST
HERE. Built from the bridge's own forwarder, always — `start-execution.js` is the
precedent. Probe: `probes/probe-chat-pause-resume.js`.

⚠ EVERY OUTCOME ANSWERS; NONE IS SILENT. `NOT_FOUND` (the slug names no live goal)
is the §4.2 ambiguity and gets the verbatim §4.5 NACK. Every OTHER error —
`UNKNOWN_INTENT` from a daemon deployed without the executor, an authorization
refusal, a transport timeout, a throw, a malformed result — gets an honest one-line
refusal, `pause <goal> was NOT applied — <error>`. The defect this replaces is the
door returning before any post when it had no applier: the owner typed `pause X` in
Slack and got nothing back at all.

⚠ THE DOOR ADMITS ONLY AN AUTHORIZED SENDER, AND THAT GATE IS LOAD-BEARING.
`chat-bridge.js` runs this door BEFORE the forward path's per-principal admission
gate (`forward-path.js#onChatMessage` → `allowlist.check`), because a mechanical
verb never forwards. With the intent live, any Slack workspace member who could DM
the bot would otherwise pause a goal stamped `who_stamped: 'owner'`. The door asks
the SAME predicate object the ask door authorizes with (`config.allowlist`, via
`allowlist.isAdmitted`) — never a second list — and an unauthorized sender's
`pause X` returns `{mechanical: false}`, falls through to the ordinary path and is
refused at that gate, with no answer from this door.

⚠ THE DAEMON HALF IS A SEPARATE DEPLOY. The bridge is useless for these verbs until
a daemon carrying the `pause-resume` executor is deployed; before that every verb
answers `UNKNOWN_INTENT: unknown intent: pause-resume` — honestly, in the channel.

⚠ The approval door's D12 effect is likewise reachable through an intent: the owner
minted the fourteenth intent `start-execution` on 2026-08-24 (option (b)) and
`chat-bridge.js` builds that sender itself. The approval door's other three ports
(`closeGoal`, `pauseGoal`, `relaunchDraftVerify`) are still unwired and still
report [C-16].

## system-digest

`system-digest.js` — the ONE changed-only SYSTEM digest (`spec-owner-io.md` §5
[T5-R13, C-12]). Checks the ten America/Sao_Paulo slots (00, 06, 08, 10, 12, 14,
16, 18, 20, 22 — no check in 00:00–06:00 beyond the 24:00 slot itself); builds the
§5 snapshot of `(open ask ids + one_liners + open condition signatures)` and posts
only when it differs from the last DELIVERED payload. Age is rendered but is not in
the snapshot, so an ageing ask alone never posts. Unchanged → nothing is posted.
The baseline is persisted and moves only on Slack's ack, so a restart does not
re-post an unchanged digest and an unacked digest is re-offered at the next slot.
One post, system channel only, `kind=digest` through the outbox, ordered asks →
conditions → links. Open conditions come from an injected READ port over the
alarm-signature registry (impl-alarms owns the emitter, `ignite/observation/`);
with that interface absent the digest reads an empty set and renders `• none open`.
No emitter and no stand-in registry here. Probe: `probes/probe-chat-glance.js`.

## status-line

`status-line.js` — the one standing glance surface (`spec-owner-io.md` §6
[T4-R5, D-6-ruling]). Renders exactly `N waiting · oldest Xh · M blocked` (zero
case `0 waiting · oldest 0h · 0 blocked`) from injected readers: open ask-records
across all goals, and blocked-on-human lanes plus paused goals as one count.
`Xh` is floored whole hours since the oldest open ask. It NEVER posts — it writes
the bot's Slack status text through an injected port, and only on the seven §6
triggers (ask minted / answered / closed, blocked-on-human stamp / clear, pause
success, resume success). Any other event is refused. Unwired port → a warn, never
a silent no-op. Probe: `probes/probe-chat-glance.js`.

## glance-wiring

`glance.js` — what makes §5 and §6 REACHABLE. Both surfaces above were built and
proven with every port injected and nothing injecting them: `index.js#main()`
wired no clock, no readers and no status transport, so the digest never ran and the
status line reported `no-status-port` forever. This module composes them from parts
the bridge already holds and `index.js#buildBridge` constructs it; `main()` starts
the clock.

The three seams it closes:

- **The slot driver.** A 30-second beat calling the §5 slot check (twice a minute,
  so one skipped beat under load cannot silence a whole slot); `isSlot` is asked
  FIRST, so the other ~2,870 beats a day cost no gateway call at all. Re-entrant
  passes are refused. Started only from `main()` — building a bridge never acquires
  a live 2-hourly clock.
- **The readers.** Open asks come back over the gateway (`ask-store.js#listOpenAsks`
  → the `inspect asks` target); open conditions come from
  `observation/emitter.js`'s OWN `readOpenConditions`, reloaded off the
  daemon-written registry before every read (a constructor-time snapshot would
  render the alarm set as it stood when the bridge last started). The emitter
  instance here is handed a `post` that THROWS: the bridge reads alarms and may
  never compose one [T4-R10].
- **The status transport.** `slack-socket-mode.js#setStatusText`
  (`users.profile.set`, `status_text` only).

⚠ AN UNREADABLE ASK SET SKIPS THE SLOT. `listOpenAsks` answers `null` on a refusal
and `[]` when nothing waits; `system-digest.js` collapses both to `[]` by
construction, so the distinction is made HERE, before the digest is asked anything
— otherwise a gateway outage would post "• none open", move the baseline on Slack's
ack, and re-post everything when the daemon came back.

⚠ NO SYSTEM CHANNEL IS A LOUD REFUSAL: `createGlance` returns `null` and warns
(`RBTV_SYSTEM_CHANNEL_ID`, or `system_channel_id` in the bridge config). It never
picks a channel, and the bridge still carries every message it carried before.

Still open, and deliberately not invented here: the §6 triggers are not FIRED yet
(they live in the ask door, the mechanical door and the reply leg — each needs a
`glance.onTrigger(...)` call at its own moment), and `readBlockedCount` stays at its
default `0` because no read door for blocked-on-human lanes or paused goals exists
from this process. Probe: `probes/probe-chat-glance-wiring.js`.

## bus-ferry-completion

`bus-ferry.js` + `chat-bridge.js` — the finish edge's completion notice
(`spec-owner-io.md` §1 [T5-R16]). A `type: completion` bus row whose body OPENS
with `records.py`'s `FINISH_MARKER` and whose `from:` is the `leader` chair is the
ONE row this ferry carries that is not addressed to the owner: it is posted as
ONE 3-line message, TOP-LEVEL in the goal's own channel [T5-R11], through the
bridge's `postGoalChannel` and the outbox as `kind: completion` — the kind
`outbox.js` had declared since [C-17] and nothing had ever produced.

Never the ❓ ask door (a completion is a notification [T2-R16]; `postAsk` would
mint a record nobody can answer and hold the kill clock open), never the owner DM
(it carries no goal traffic at all, `d-escalation-surface` part 4 — the unreachable-channel
alarm is suppressed for this row too, since a finished goal is not a blocked escalation),
never `#system-channel`. Line 1 is the outcome and comes from the row;
line 2 is counted off the goal's `executions.csv`; line 3 names every
`goal-writes:` output that is on disk AND non-empty — D21 creates them empty at
spawn, so existence is not delivery. Idempotence is the ordinary cursor. The
marker is duplicated across Python and JS with no shared constant, and W9 PIN in
`probes/probe-chat-bus-ferry.js` reads `records.py` to keep the two from drifting.
Arm W9 of `probes/probe-chat-bus-ferry.js`.

## goal-channel-cli

`goal-channel-cli.js` — the Slack goal-channel `ensure` / `list` / `post` / `retire`
verbs. **dual** audience (§7.1, transcribed in `ignite/ignite-cli/cli-audience-map.md`):
the ticker calls `ensure` as the daemon, and a console calls `post` / `retire` by hand.

It carries a `method=path` row on `exposure.csv` (`d-exposure-method-path`,
`spec-component-map` §7.3 — the census found it reachable by full path only, discoverable
through nothing). `rbtv-cli` and `description` stay empty on that row: the tool
self-documents via `-h`.
