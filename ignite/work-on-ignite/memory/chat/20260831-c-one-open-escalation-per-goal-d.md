# 20260831-c-one-open-escalation-per-goal-d — one open escalation per goal (d-escalation-surface 8)

kind: creation
component: chat
date: 2026-08-31
commit: 77fc4695
deployed: no
pin: ignite/chat/probes/probe-chat-bus-ferry.js

## Motivation
Owner ruling `d-escalation-surface` part 8, from the 2026-08-31 interview into the same incident
`esc-door-split` fixed the admission half of: goal `transcript-summarizer-build` raised three
blocking escalations in seventeen minutes, and the second withdrew a claim the first had made
("I said (a) unblocks m1-m6, m8, m9. Wrong about m2."). Had all three been open threads at once,
the owner could have ruled on the first using evidence the second had already retracted. The
ruling: a goal holds at most ONE open, posted escalation ask at a time; later ones queue on the
bus and post only after the open one is answered.

## Design
The gate sits in `bus-ferry.js`'s per-row loop, right where a new escalation would otherwise mint
an ask via the injected `postAsk`. It reads a NEW injected `listOpenAsks` (fleet-wide, the same
`ask-store.js#listOpenAsks` -> gateway `inspect asks` -> `open_asks` the system digest already
uses), filters to the row's own goal, and HOLDS (does not post, does not advance the cursor past
the row) when the goal already carries an open escalation.

The central design problem: `open_asks` (`state-store/tables.sql`) has no column that discriminates
an escalation from any other `label: 'recovery'` row. `label` is a two-value digest taxonomy
(`work-content`/`recovery`); an admitted ordinary `leader` message and a `recovery-poster.js`
daemon-decided exhausted-lane ask both also carry `label: 'recovery'`. `kind: 'escalation'` IS
computed in this same module (`isEscalation`) and reaches `ask-thread.js#postAsk`, but only for the
[T2-R14] door — `state-store/heart/ask-record.js#openAsk` never receives it and the row is never
stamped with it. Adding a column is an owner-gated schema change (out of this seat's custody, per
its own wall) and was explicitly NOT made.

Rejected: inventing a bridge-side in-memory flag ("this goal has an open escalation") — the exact
failure class a sibling defect in this subsystem measured (`seed/slack-duplicate-replies.md` defect
1: two bridge lineages, forked in-memory state, both answering one thread). A restart or a revive
would let two ferry passes each believe they hold the only open escalation.

Adopted instead: the ONE signal that does survive to disk without a schema change — the ask's own
header. `formatMessage`'s `agentLead` branch renders `... · ${row.type} · #...`, literally the word
"escalation" for an escalation row, and `postAsk`'s body is always
`splitAskBody(formatMessage(row, {..., agentLead: true, ...}))`, so the header is always the FIRST
line of the persisted ask copy — read back as `one_liner` by
`state-store/heart/ask-record.js#listOpenAsks`. This is the SAME weakest-available text-marker
fallback `system-digest.js#sortAsksBlockingFirst` (`digest-blocking-sort`, same day, same
subsystem) already uses for its own missing structural field, applied here rather than invented.

## How it works
`isEscalationOneLiner(oneLiner)` checks for the substring `' · escalation · #'`. The gate:
`if (isEscalation && !chatThread && listOpenAsks)` — `!chatThread` excludes a reply INTO an
already-open ask's own thread (never a new mint) — calls `listOpenAsks()` fresh, filters by
`String(a.goal) === String(goalId)` and `isEscalationOneLiner(a.one_liner)`; if any match, logs
`bus ferry HELD a new escalation`, sets `stuckAt = row.id` (if not already set, reusing the exact
head-of-line bookkeeping an ordinary stuck row uses) and `continue`s — never entering the delivery
try-block, so a held escalation never accrues an attempt and is never force-delivered to the DM at
the attempt cap (that path is for TRANSPORT failures; this is a deliberate, working queue).

Critical wiring found only by red-then-green testing: `sizes.delete(key)` (mirroring the existing
retry ladder's own `sizes.delete(key)` a few lines below, at the "post failed — will retry next
pass" branch) is REQUIRED inside the hold branch too. Without it, `_runOnce`'s unchanged-file
short-circuit (`if (cursors.has(key) && sizes.get(key) === st.size) continue`) would skip the goal
entirely on the pass after the held escalation, since nothing new was appended to the bus — the
held row would never be re-evaluated once its blocking escalation closed, with no other bus traffic
to force a re-read. Found by the RESUME arm going red (row never re-minted) before this line was
added.

The three-way interaction with the existing head-of-line JUMP (`isEscalation` lets an escalation
post past a stuck ordinary row): a new escalation still clears that test (unchanged), reaches this
gate, and is held there instead — the opposite force. `stuckAt` is shared bookkeeping: whichever of
the stuck ordinary row or the held escalation is FIRST sets it, and the cursor stays behind both.
No deadlock: the ordinary row keeps retrying on its own independent attempts ladder untouched by
this gate, and the held escalation is re-read every pass; FIFO order across multiple held
escalations falls out of the loop's own id order with no queue of its own to get out of sync.

## Consequences
Nothing deleted. `postAsk`'s `kind` parameter (used by `esc-door-split`'s door) is unchanged; this
gate reads a SEPARATE signal (the persisted one_liner) because `kind` itself never reaches disk.
`listOpenAsks` is a new injected dependency on `createBusFerry`, defaulting to `null` (no-op,
behaviour unchanged from before this seat) — NOT yet wired at the production call site,
`chat-bridge.js` (out of this seat's custody, `esc-dm-ban`'s row) — see ATTENTION.

## Verification
`node ignite/deploy/probe-suite.js --dir chat/probes` — 26/29 PASS, exit 1 (suite-level RED from 3
PRE-EXISTING failures: `probe-chat-boundary`, `probe-chat-live-session`, `probe-owner-ask-hold` —
same three `esc-door-split` documented the same day, none reference `bus-ferry.js`).
`node ignite/chat/probes/probe-chat-bus-ferry.js` — 76 checks (was 60), PASS, exit 0. New arms
W10-RED (gate unwired: 3 escalations from one goal all mint, reproducing the incident),
W10-GREEN (gate wired: exactly 1 mints, 2 HELD, cursor stops at the row before the first held one),
W10-RESUME (closing the open escalation mints the 2nd on the very next pass; the 3rd stays held),
W10-DISCRIMINATE (an open `work-content`-shaped ask does not block a new escalation),
W10-JUMP-HOLD (open escalation + stuck ordinary row + new escalation: nothing posts, cursor stays
behind both, no deadlock; once both clear, a later pass delivers both in order). Not deployed —
committed to `ignite/core-daemon` only, per this plan's no-mid-plan-deploy rule.

## ATTENTION
- `listOpenAsks` is UNWIRED at the real call site. `chat-bridge.js#createBusFerry(...)` (around its
  `postAsk: (args) => postOwnerAsk(args)` line) needs one additive line —
  `listOpenAsks: () => askRecord.listOpenAsks(),` (the same `askRecord` already constructed there
  for `postAsk`/`reapAsk`) — before this gate does anything in production. That file is
  `esc-dm-ban`'s custody row, not this seat's; until that line lands the gate is a documented no-op.
- The marker is TEXT, not a column — a future reword of `formatMessage`'s `agentLead` header
  format (`... · ${row.type} · #...`) silently breaks `isEscalationOneLiner` with no test failure
  unless `ESCALATION_ONE_LINER_MARK` is updated to match. Grep both together before editing either.
- `open_asks` still has no `kind`/`type` column. The smallest owner-gated fix, if ever wanted: add
  a `kind TEXT` column (values mirroring `postAsk`'s existing `kind` set: `ordinary|escalation|
  recovery|approval`), written once at `state-store/heart/ask-record.js#openAsk`'s insert from the
  value `ask-thread.js#postAsk` already receives and currently discards after the door check. That
  would let this gate (and any future reader) query structurally instead of on rendered text.
- listOpenAsks unwired at chat-bridge.js (esc-dm-ban custody) — the gate is a no-op until that one line lands
- the marker is TEXT (formatMessage's agentLead header), not a column — reword it and isEscalationOneLiner breaks silently
