# 20260827-i-a-refused-escalation-retried-2 — a refused escalation retried 20x before reaching the owner

kind: issue
component: chat
date: 2026-08-27
commit: 84238318
deployed: no
pin: ignite/chat/probes/probe-chat-bus-ferry.js
components: meta-leader

## Observed
`leader`'s escalation #12 on the paused goal `scratch-tool-reach-note`, live on the deploy
worktree at 5c641b04, 2026-08-27 19:36–19:37Z: the bridge journal carries TWENTY consecutive
`owner-ask REFUSED — this seat is not designated to reach the owner [T2-R14]` lines for the one
row, and only after the twentieth does the owner get the content-bearing DM
(https://ignite-alfa.slack.com/archives/D0BJ50Y1DC6/p1787859476057659). The delivery itself is
correct and designed — W8-C's `postOwner kind:'alarm'` leg, which carries the escalation's text
because there is no retry behind it. What was wrong is that it took ~90 seconds and twenty
identical log lines to get there, on the one message type whose purpose is to interrupt a human.
Deployed and HEAD were the same commit at the time.

## Mechanism
`bus-ferry.js` states at its ladder header that an `escalation` PASSES EVERY GATE, and it does —
but the ask door is not on that ladder. The row still went through `postAsk`, and
`ask-thread.js#postAsk` refuses a seat whose `seat.md` carries no `human-interactive:`
([T2-R14]); staff chairs deliberately carry none (`meta/leader/component.md` says so in as many
words). The ferry answered that refusal with `res = { delivered: false, reason:
'seat-not-interact' }` — a TRUTHY `res`, which both skipped the remaining delivery legs and made
the row look like an ordinary failed post. It therefore entered the bounded retry
(`DEFAULT_MAX_ATTEMPTS = 20`), where every pass re-asked a question whose answer is a file on
disk: the sending seat's own descriptor. Nothing about a `seat-not-interact` refusal can differ
between passes, so all twenty were the same answer, and the cap was simply the slowest possible
route to the disposition the first pass already knew.

## Attempts
First attempt held — checked: 8f299bc6 (the approval ask rides the bus row), which added the
`approve-commit` key and the `kind: 'approval'` fork at this exact call site and left the refusal
branch as it found it; the W8 family in `probe-chat-bus-ferry.js` (W8-A/B/C, added with the
escalation transport contract), none of which reached the ask door — W8-A's fixture has no
resolvable goal channel, so `postOwnerAsk` returns `no-channel` and the refusal branch never
fires; and the deleted three park rungs [D24, T2-R17, D-7-ruling], which removed the gates that
used to swallow this row and left [T2-R14] standing at its own door.

## Fix
The refusal is now TERMINAL wherever it is handled (84238318). A new `terminalRefusal` flag is
set in the `seat-not-interact` branch, and a block after the delivered-continue disposes of the
row on the FIRST pass: for an `escalation`, by W8-C's content-bearing owner DM; for any other
row, by one report line and an advanced cursor. Both callers of that DM — the first-pass refusal
and the attempt cap — now share one `deliverEscalationInFull`, so the words the owner reads
cannot drift between the two.

`postAsk` was NOT loosened to admit `label: recovery` escalations, which was the other candidate
and is the wrong one: `postAsk` MINTS AN ASK RECORD, and a record for a seat that cannot be
replied to is an ask that can never be released — it would suspend the kill clock and read as
open forever in the digest and the status count. [T2-R14] refuses at that door for exactly that
reason, and the content-bearing DM is the leg it refuses TOWARD. Also rejected: skipping
`postAsk` for escalations entirely, which would have taken the real ❓ thread away from an
escalation raised by a seat that IS `human-interactive`.

## Consequences
Nothing was deleted. The cap branch is byte-equivalent in behaviour: its own text is preserved
verbatim through the `why` argument, and W8-C's two arms still pass unchanged. `_attempts` is now
exposed on the ferry's returned object beside `_cursors` and `_jumped` so a probe can assert that
no retry was left behind — a test seam, joining two that already existed. The sibling class was
fixed in the same act rather than left: an ORDINARY row refused at the same door also spent
twenty passes before its silent give-up, and now gets its single report line on the first.

## Verification
`ignite/chat/probes/probe-chat-bus-ferry.js` gains W8-D (four checks: one ask attempt, one
content-bearing DM naming [T2-R14], no attempt left behind, cursor advanced, exactly one refusal
line and zero `will retry next pass` / `NOT delivered` lines, and no second delivery on a later
pass) and W8-E (the ordinary row: nothing posted, one report, cursor advanced). 49 → 54 checks,
`PROBE probe-chat-bus-ferry EXIT=0 PASS=true CHECKS=54`. Red mutation — delete
`terminalRefusal = true;` — reddens exactly those five and no other, `EXIT=1 PASS=false`.
`probe-chat-approval` 24/24 PASS before and after; `coord.py selftest` 1014 ok, `PASS (0
failure(s))`, before and after. NOT DEPLOYED: `rbtv-chat-bridge` must restart for this.

## ATTENTION
- The ask door is NOT on the gate ladder the module's header describes. "An escalation passes
  every gate" is true and still leaves `postAsk` in front of it — reading the header alone will
  tell you a refused escalation is impossible.
- A truthy `res` in this loop means "a leg answered", not "delivered". Setting `res` to a failure
  object skips every remaining leg AND feeds the retry counter; that dual meaning is what turned
  one deterministic refusal into twenty.
- Do not make `postAsk` admit non-interactive seats to fix a delivery problem. It mints an ask
  record, and a record nobody can reply to holds the kill clock open forever.
- The W8 fixtures do not reach the ask door by default: `makeBridge`'s fake Slack has no channel
  surface, so `postOwnerAsk` answers `no-channel`. A new arm about the ask door must inject
  `postAsk` through `busFerryOptions` (the real door's own refusal is pinned at
  `probe-chat-ask-release.js:119`).
- the ask door is not on the gate ladder the module header describes
