# 20260828-c-the-finish-edge-s-3-line-compl — the finish edge's 3-line completion notice

kind: creation
component: chat
date: 2026-08-28
commit: 4c13b853
deployed: no
pin: ignite/chat/probes/probe-chat-bus-ferry.js
components: coord

## Motivation
A goal that finished told nobody. Measured on `seat-cage-tool-inventory`, finished 2026-08-28
01:31Z: the finish edge fired (`coordination/messages.md` #4, `CLAUDE.md` FINISHED banner, ending
store `leader=done`) and NOTHING reached Slack — not the goal channel, not the owner DM, not
`#system-channel`; `outbox.json` held zero `completion` rows against 29 notification / 6 ask /
5 alarm / 3 digest / 1 nack. `outbox.js` had declared the `completion` kind since the durable
outbox [C-17] and no producer in `ignite/` had ever existed; `forward-path.js` reads `type:
completion` bus rows for the CMP-8 chain verdict and posts nothing for them; `bus-ferry.js` named
the gap in its own `[deliver:]` header ("issue `i-no-completion-nudge` — the owner is not told").
`spec-owner-io.md` §1 [T5-R16] specifies one 3-line channel message. Owner ruled CP-B
(2026-08-28 01:54Z): build it before the failure-injection wave.

## Design
The root cause is one line of address matching: `fire_finish_edge` (`coord/records.py:761`) appends
its row `to: all`, and the ferry's row walk disposes of every row that is neither `to: owner` nor
naming a chat thread — cursor advanced, nothing posted, no log line. So the notice is produced
where the row already passes.

Producer (a), the FERRY, over (b), the finish act sending a `to: owner` note. (b) does not work on
the existing rails: a `to: owner` row reaches `postAsk`, which refuses a staff chair [T2-R14] — and
loosening that door is exactly what the `20260827-i-a-refused-escalation-retried-2` fix refused to
do, because `postAsk` MINTS AN ASK RECORD and a record for a notification nobody can answer
suspends the kill clock and reads as open forever in the digest and the status count. A completion
is a notification, visibly distinct from an ❓ ask [T2-R16]. (a) is one branch placed before the
address test, plus one injected delivery leg.

What identifies the event is the MARKER, not the type: every seat sends `--type completion` at
check-out. The finish event is a `completion` whose body OPENS with `records.py`'s `FINISH_MARKER`,
the same first-line test `goal_finished()` uses. The sender is checked too, against the `leader`
chair — normally a second, weaker authority (see the `approve-commit` header's own note), but here
the ONLY one: nothing in `coord.py cmd_send` guards the marker, so any seat can type that string
into a completion body and announce a goal over.

Rejected: reusing `routeToAgentThread` — it anchors and then replies INSIDE one agent's thread, and
a goal ending is the room's news, not a seat's message [T5-R11]. Rejected: a DM fallback when the
channel is unresolvable — the DM is the escalation/alarm surface; the row is held and retried
instead, and the missing-channel DM notice is suppressed for it. Rejected: a new module — the
composition is ~90 lines beside `formatMessage`, and `chat/` reaches into no sibling module
(`probe-chat-boundary`), so the three frontmatter readers already local to `bus-ferry.js` set the
precedent for a fourth.

## How it works
`parseHeader` (`ignite/chat/bus-ferry.js`) now captures the header's trailing wall-clock stamp as
`at`, read BY SHAPE against `ROW_STAMP_RE` rather than by position — the module's own additive-
grammar rule, since a keyed field may be inserted anywhere before it. `isFinishRow(row)` is the
marker test; `LEADER_CHAIR` is the sender test. In `_runOnce`, `const isFinish = !chatThread &&
isFinishRow(row) && row.from === LEADER_CHAIR` is computed immediately before the
`!addressesOwner(row.to)` disposal, which now reads `!isFinish` too; a marker-carrying row from any
other seat falls into that branch and gets one warn line naming the withholding.

`composeCompletionNotice({ goalDir, goalId, row })` returns exactly three lines: (1) the goal, that
it FINISHED, `row.from` and `row.at`; (2) `executionHeadline` — distinct seats, row count, and the
min-start-to-max-end window, all counted off `<goal>/executions.csv` through `readCsvRows`, which
reads BY HEADER NAME and SKIPS any row whose field count disagrees with the header rather than
misattributing a quoted comma; (3) `declaredOutputs` — every `goal-writes:` token in each seat's
`seat.md` frontmatter, resolved once against the goal dir (`spawn/seat-grants.js#resolveGoalWriteGrants`
does `path.resolve(goalDir, entry)` and refuses anything absolute or escaping), kept only when the
path is a file with bytes in it.

Delivery is a new injected option `postGoalChannel`, wired by `chat-bridge.js` to `goalChannelFor`
+ `postSlack({ kind: 'completion', threadTs: null })` — top-level, through the outbox, no thread
recorded. It is taken FIRST inside the try block, so setting `res` skips every leg beneath it. That
required adding `!res` to the `postAsk` test, which alone among the legs did not read it: without
that, the finish row was posted TWICE, once as its channel notice and once as an ❓ ask thread.
Idempotence is the ordinary cursor — the row is behind it after the posting pass, and `_runOnce`
re-reads the whole `messages.md` on every size change.

## Consequences
Nothing was deleted and no existing disposition changed: `res` is null at the `postAsk` test for
every row that is not a finish row, so the added `!res` is behaviour-neutral, and the `at` field is
inert for `supervisor/execution-record.js#openOwnerAsks`, the only other consumer of
`parseMessages` (it reads `from`/`to`/`type` only). `exposure.csv` gained no row: the ferry has
never had one and nothing new is reachable to a new caller — and its `exposure-canon` lint is
already red on all 16 existing rows (`part-kind: library` is outside the closed vocabulary),
pre-existing and untouched. NOT DEPLOYED: `rbtv-chat-bridge` must restart. The daemon also loads
`bus-ferry.js` (through `supervisor/execution-record.js`) but needs no restart for this — its use
of the module is unchanged.

## Verification
`ignite/chat/probes/probe-chat-bus-ferry.js` gains arm W9 (nine checks: one top-level goal-channel
post and zero DM posts; one outbox row `kind: completion`, `thread_ts: null`, `state: delivered`;
three lines with the goal/sender/stamp on line 1; line 2 byte-exact against a hand-counted
`executions.csv`; line 3 naming the written deliverable and NOT the declared-but-empty one; zero
ask records; an idle pass and a whole-file RE-READ neither re-posting; the non-leader marker
withheld with its warn line; an ordinary marker-less completion from the leader posting nothing;
and a cross-language PIN reading `coord/records.py` to hold `FINISH_MARKER` byte-identical).
54 -> 64 checks, `PROBE probe-chat-bus-ferry EXIT=0 PASS=true CHECKS=64`.

Five red mutations, each reddening only W9 arms and never one of the 54 that predate it:
`isFinish = false` -> 8 reds; drop `&& row.from === LEADER_CHAIR` -> 2; drop `!res` from the
postAsk test -> 5; alter the marker string -> 1 (the PIN alone); drop the `st.size === 0` filter
-> 1 (line 3 alone). Green beside it: `probe-chat-approval` 24, `probe-chat-outbox` 16,
`probe-chat-agent-thread` 83, `probe-chat-goal-channel` 31, `coord/probes/probe-finish-edge.py`
13/13, and the whole `ignite/chat/probes/` suite bar two reds that are red at HEAD too
(`probe-chat-boundary` — `bus-answer.js` `execFile`; `probe-chat-ask-release` E7). Composed against
the real finished goal read-only: three lines, `*3* seats run · *5* sittings · 16m
(2026-08-28T01:19:39Z -> 2026-08-28T01:36:00Z)`, `Deliverables: tool-inventory.md`. That goal will
not re-post on restart — its persisted cursor in `chat-bridge-state.json` is
`seat-cage-tool-inventory/no-stamp: 5`, past the finish row #4.

## ATTENTION
- The `postAsk` leg did NOT read `res` while every leg beneath it did. Anything that sets `res`
  before it is posted twice — once by its own leg and once as an ❓ ask thread. That asymmetry was
  invisible until a leg was added above it.
- A `type: completion` row is NOT the finish event. Every seat sends one at check-out; the event is
  the body OPENING with `records.py`'s `FINISH_MARKER`. A future reader that keys on the type alone
  will announce every seat's check-out to the owner's channel.
- Nothing at `coord.py cmd_send` guards that marker. Any seat can put the string in a completion
  body, and `goal_finished()` will then read the goal as finished. The ferry's `leader` sender test
  is the only thing standing in front of the owner's channel — do not remove it as a redundant
  second authority; there is no first one.
- A declared `goal-writes` output that EXISTS proves nothing. D21 creates every one of them empty
  at spawn so the cage bind has a source, so any deliverable list built on existence alone names
  files no seat ever wrote.
- The marker is a string in two languages with no shared constant. `probe-chat-bus-ferry.js`'s W9
  PIN reads `records.py` and compares; if it ever reddens, the marker moved and the ferry has gone
  blind — every later goal finishes in silence again, exactly the defect this entry closed.
- a completion row is not the finish event — the marker is; the send door guards neither
