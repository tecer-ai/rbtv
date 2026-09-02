# 20260902-i-re-reply-settles-only-addresse — re: reply settles only addressee/sender's own row

kind: issue
component: coord
date: 2026-09-02
commit: ed02fecdbfed217e868103f0a198e58fba8e92c8
deployed: yes
pin: ignite/coord/coord_selftest.py

## Observed
`open_escalations`/`open_asks` (`ignite/coord/messages.py`) treated ANY message carrying `re: <n>`
from ANY sender as settling row `<n>` — so a peer's reply silently retired a halt or ask addressed to
someone else. Measured live on stools escalations #237, #248 and #270: each was addressed to `owner`,
and each was closed by `goal-master`, a peer worker, never by the owner. Separately, `cmd_pending`
kept showing an ask forever once its asking seat had finished or exited (#165/#473 stayed open
indefinitely), and an ask addressed to `owner` by another seat was invisible to `pending` for
everyone except `owner` itself or a broadcast recipient (`to: all`) — a peer's `to: owner` ask
matched neither the "asks waiting on you" section nor the broadcast section, for any reader.

## Mechanism
The old settlement test was purely textual: `{b["re"] for b in blocks if b["re"] is not None and
b["type"] in ("answer", "verdict")}` — any row with the right `re:` number and the right type
retired the target, with zero check on WHO sent it. This let a third seat, wearing neither the
addressee's nor the original sender's hat, close a row it had no standing over. `cmd_pending`
separately never checked whether an ask's SENDER was still an active roster member, so an ask never
expired on the asking seat's own lifecycle — it stayed "open" as long as the message log kept the row,
regardless of whether anyone was left to receive an answer. And `cmd_pending`'s four rendering
sections partitioned asks by "is this to me" / "is this broadcast to all" / "is this from me" — an ask
`to: owner` sent by a different seat fell into none of those buckets unless the reader happened to be
`owner`.

## Attempts
First attempt at this problem — checked: `git log -- ignite/coord/messages.py` around
`open_escalations`/`open_asks`/`cmd_pending`; no earlier attempt at a sender/addressee check on `re:`
settlement, or at an active-roster filter on asks, was found. `coord_selftest.py`'s existing W4 arm 7
was found to have ENCODED the bug as expected behaviour (closing a row via a bystander sender) —
already committed corrected by a parallel session in `f616be02` by the time this commit landed; this
commit's own arm 7/7b additions build on that correction rather than duplicate it.

## Fix
A single shared predicate, `_reply_settles(reply, target)`: a reply settles its target only when
`reply["sender"]` equals the target's `to` (the addressee answering) or the target's own `sender` (the
asker/escalator recording on the bus that it is settled — e.g. `leader` transcribing "the owner
ruled" onto its own escalation). `_settled_nums(blocks)` wraps this as the one shared derivation used
by both `open_escalations` and `open_asks` (G-134 criterion 2: reuse the predicate rather than grow a
second opinion). `open_asks` gained an optional `base=` parameter: when given, it drops any ask whose
SENDER seat has since finished or exited, read off the roster's own `active` column — a sender with NO
roster row at all is kept (a foreign, cross-package sender, not a finished one; only `active: no` is
evidence of "finished"). `cmd_pending` now passes `base=base` and gained a fifth rendering section,
"open asks to the owner," so an ask `to: owner` from any sender is visible to whichever seat reads
`pending`, not only to `owner` itself or a broadcast recipient.

## Consequences
Both `open_escalations` and `open_asks` now share one settlement authority instead of two independent
textual checks that could silently drift apart. `cmd_pending`'s ask list no longer accumulates asks
from seats that have since left, closing #165/#473's class of stale entries. The new fifth section
means an owner-addressed ask from a peer seat is now visible to any reader of `pending`, closing
`G-leader-0823-0238`'s sibling gap. Filed loose end: the sender/addressee filter in `_reply_settles`
was applied at the `open_escalations`/`open_asks` predicate only — one call site — and not
independently swept across other readers that might apply their own `re:` logic (that sweep is what
`cfcc9278`, filed separately the same day, later covers for `open_asks`'s `base=` specifically, though
not for `_reply_settles` itself).

## Verification
`coord_selftest.py`'s W4 arm 7 (already corrected in the parallel commit `f616be02` to close via the
legitimate `owner` sender) and the new arm 7b (red-first, proving a peer's `re:` leaves an
owner-addressed halt open) both pass. `python3 coord.py selftest` passes with 0 failures at this
commit (per the commit message). Deployed — `ignite/coord/messages.py`, branch `ignite/core-daemon`,
live on deploy tree `e8524c31`.

## ATTENTION
1. `_reply_settles`/`_settled_nums` are now the ONE shared settlement authority for both
   `open_escalations` and `open_asks` — a future change to either function that reimplements its own
   `re:` matching instead of calling `_settled_nums` reintroduces the exact bystander-settlement
   defect this commit closed.
2. `open_asks`'s `base=` filter reads "finished" off the roster's `active` column, and treats "no
   roster row at all" as a FOREIGN sender (kept, not dropped) rather than a finished one — a future
   change that conflates "no row" with "finished" would incorrectly drop every cross-package ask.
3. The sender/addressee filter closes settlement for `open_escalations`/`open_asks` specifically; it
   is not a sweep of every `re:`-consuming reader in the codebase. A future audit should confirm no
   other reader independently re-derives "is this settled" from raw `re:` matching.
