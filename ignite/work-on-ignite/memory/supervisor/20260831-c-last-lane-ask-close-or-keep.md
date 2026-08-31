# 20260831-c-last-lane-ask-close-or-keep — the close-or-keep ask on a goal's last dropped lane

kind: creation
component: supervisor
date: 2026-08-31
commit: 37743970 (own files); reconcile.js call site landed inside a peer commit, 4196440e — see ATTENTION 1
deployed: no
pin: ignite/supervisor/last-lane-ask.selftest.js
components: state-store, chat

## Motivation
`d-recovery-last-lane-asks` + `d-recovery-waiting-goal-freeze` (owner ruling, 2026-08-31, "the two
dead recovery replies get seated"): when `drop-lane` abandons the goal's LAST lane that still had
work, the system must not close the goal on its own and must not go silent either — it raises ONE
close-or-keep question in the goal's own channel, and while it is open the shutdown clock stays
suspended.

## Premise re-verified, and corrected
The seat.md framed the auto-close risk as "reconcile.js calls `finishOnCompletion`, gated on
`last_milestone_complete`." Read against the tree, that gate is `taskforce.csv`-derived (every
LAST-MILESTONE seat must have posted an actual, non-finish `completion` message in
`coordination/messages.md`) and is COMPLETELY ORTHOGONAL to owed/abandoned state — an abandoned
seat never posts a completion, so `finishOnCompletion` cannot fire BECAUSE of an abandonment either
way. Read further: `reconcileGoal`'s `if (derived.owed && !leader) {} else if (derived.owed) {}`
chain has NO trailing `else` before this change — when `!derived.owed`, the pass did NOTHING: no
question, no close, just silence. The real, corrected finding: nothing today prevents the goal from
being left in this state, and beyond an hourly generic FROZEN-goal alarm (`observation/frozen.js`,
which posts NO specific question and, by its own header, "nothing kills") nothing ever tells the
owner why. This seat's ask is what closes that silence.

The "shutdown clock" language in this ruling and in `d-escalation-surface` is this codebase's name
for `observation/frozen.js`'s alarm suppression. `goalWaitingOnOwner` (the predicate that would be
the literal "kill clock") has NO production caller anywhere — only `lane-watch.js:312`'s `openAsk`
(`api.countOpenAsks(goal) > 0`, feeding `frozenFactsFor`'s `open_ask` field) is live. Confirmed
independently against `20260828-c-the-finish-edge-s-3-line-compl.md` (chat memory): "a record for a
notification nobody can answer suspends the kill clock" — the SAME mechanism, corroborated from a
completely separate investigation.

## Design
`derived.owed` and `derived.abandonedSeats` are `owed.js#deriveOwed` / `reconcile.js#owedFromLedgers`'s
OWN return fields — `owed-from-endings.js#classifyOwed` already excludes an abandoned seat from
`classA`/`classB`/`pending` (`dl-abandoned-outcome`, LIVE today for reconcile's ledger half; no
extra wiring needed — `owedFromLedgers` never passes a `graph`, so class R, the still-unwired half,
never enters `reconcile.js`'s own `owed` value at all). `lastLaneAbandoned(derived)` in the new file
`ignite/supervisor/last-lane-ask.js` is `!derived.owed && derived.abandonedSeats.length > 0` — a
goal that finished ordinarily has an empty `abandonedSeats`, so it never fires.

Minting (`mintLastLaneAsk`) follows `exhaustion.js#recordGroupedAsk`'s exact shape: a JSON record
under `.rbtv/runtime/ignite/asks/<id>.json` (id stable per goal — `disposition-<sha256(goal)[:12]>`,
idempotent: `d-recovery-drop-is-one-lane-permanent` makes "last lane abandoned" a state a goal
reaches at most once) plus an `open_asks` row via the GENERIC `store.insertAsk`/`store.getAsk`
(label `'recovery'`, NOT recovery-specific machinery — `insertAsk`'s label check only distinguishes
`work-content`/`recovery`, the digest taxonomy). `writeAskRecord` was not exported from
`exhaustion.js`; exporting it (one line) let this file reuse the ONE writer instead of copying it.

## Consequences / what was deliberately NOT built
Posting to Slack (flipping the `open_asks` row's `posted` to 1, via the GENERIC `store.postAsk`) and
honouring the reply (`close`/`keep`) were NOT built. Both require touching `ignite/chat/`'s
`ask-thread.js` (the `seatIsInteractive` bypass needs a THIRD `kind` alongside `escalation`/
`recovery`, since reusing `kind:'recovery'` for posting would make the REPLY parse against the
wrong 3-word ladder), `reply-grammar.js` (a new closed vocabulary branch), and `chat-bridge.js`'s
dispatch-construction/routing (~line 235, ~line 342-359) — none of which are this seat's custody,
and `chat-bridge.js`+`recovery-thread.js`+`reply-grammar.js` were under ACTIVE concurrent edit by
`dl-teardown-wire`/`rr-port-wire`'s cluster for the whole of this seat's run (confirmed via
`ListAgents` and `git log`: `8c1023af` landed mid-seat). Building a parallel poster there risked
exactly the "second design surface, half-built" this seat's own DoD warns against for clause 5.
The suspension chain itself (`countOpenAsks`) is proven directly against the real store instead —
see Verification.

## Verification
`ignite/supervisor/last-lane-ask.selftest.js`, ALL PASS (6 cases), against the REAL
`classifyOwed`/`open_asks`/`seat_abandonments` store, no stand-ins: (1) last owed lane abandoned →
mints ONE ask, the pass fires no finish event and relaunches/rebuilds nothing, a second pass mints
nothing more; (2) CONTROL — another lane still owed → no ask; (3) CONTROL — ordinary completion, no
abandonment → no ask; (4) the suspension chain: minted-not-posted → `countOpenAsks` reads 0; the
SAME row after the generic `store.postAsk` flip → reads 1 (the exact predicate `lane-watch.js:312`
consumes); (5) stored goal state stays neither `paused` nor `finished`. `probe-last-lane-ask.js`
(new, follows `probe-reconcile.js`'s thin-wrapper shape) EXIT=0. `probe-reconcile` still EXIT=0
(one pre-existing, unrelated `reconcile.selftest.js:846` failure, same one `dl-abandoned-outcome`
already documented — reproduced, not introduced, and outside this seat's `reconcile.js` custody to
fix). `probe-daemon-lane-watch` and `probe-owner-ask-hold` are RED at HEAD, unrelated to anything
this seat touched (neither `lane-watch.js` nor `ignite/chat/` was edited here) — see this seat's
report for the exact failures.

## ATTENTION
1. **`ignite/supervisor/reconcile.js`'s hunk for this feature is NOT in this seat's own commit.**
   A concurrent peer session (`dl-reconcile-honour`) ran a pathspec commit on `reconcile.js` while
   this seat's edit was sitting uncommitted in the SAME working tree (both non-overlapping regions
   of the same file); their pathspec commit staged the FULL current file content, sweeping this
   seat's `else if (lastLaneAbandoned(derived))` branch + import line into `4196440e` (message:
   "supervisor: reconcile pass and lane-watch honour a dropped lane's abandonment" — does not
   mention this feature at all). Confirmed via `git show 4196440e -- ignite/supervisor/reconcile.js`
   carrying this seat's exact lines. `git diff -- ignite/supervisor/reconcile.js` is empty — there
   is nothing left to commit on that path. NOT re-committed, NOT amended (amending a commit another
   commit already sits on top of is a separate hazard). Any future reader of `4196440e`'s diff
   should know it carries TWO unrelated features.
2. **A new `kind` for `ask-thread.js`'s `seatIsInteractive` bypass is the exact remaining shape**
   for wiring the Slack post + reply. Whoever builds it: `kind !== 'escalation' && kind !== 'recovery'`
   is the bypass condition (`ask-thread.js` ~line 199) — a fourth value (e.g. `'goal-disposition'`,
   the `DISPOSITION_KIND` this file already exports) needs adding there, PLUS a
   `reply-grammar.js#parseReply` branch keyed on that same `kind` with its own two-word vocabulary
   (`close`/`keep`) and NACK text, PLUS a `chat-bridge.js` dispatch-construction + routing entry
   mirroring `recoveryDispatch` (~line 235, ~line 342-359) — a `createDispositionDispatch`-shaped
   module, `recovery-thread.js`'s own precedent, with a `close`/`keep` arm reusing the goal-close/
   keep-open acts once they exist, and NO shape that ever treats a timeout or silence as an answer
   (`#d-auto-proceed-declined`).
3. **The `seat` column on `open_asks` is `NOT NULL`** — `mintLastLaneAsk` stamps it with the FIRST
   abandoned seat's name (`abandonedSeats[0].seat`), since the ask is goal-scoped and no sentinel
   seat exists in this schema. `countOpenAsks`/`goalWaitingOnOwner` only filter on `goal`, so this
   choice does not affect the suspension predicate.
