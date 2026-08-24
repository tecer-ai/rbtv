# 20260824-c-delete-the-oldest-open-escalat — delete the oldest-open escalation release door [D-4-ruling]

kind: change
component: team-kit
date: 2026-08-24
commit: 7672db10
deployed: no
pin: NONE
components: bridges

## Motivation
`messages.open_escalations` carried a third settle arm (W8, adv, C78): any unnumbered `type:
answer` from `owner`, addressed to an escalating seat, retired that seat's OLDEST still-open halt.
It was added because the owner's Slack reply came back through `engine/bus-answer.js` with `re:
null` — an escalation opens no ask-hold (C45), so the transport had no number to carry — and
without it the `pending` nag view never stopped nagging on a halt that had actually been answered.

The arm was right about the gap and wrong about the fix. Retiring "the oldest" is a GUESS: a reply
about one halt silently closed a different one, the rule was HEAD-only, and nobody watching Slack
could see which row it had taken. The redesign settles this at [D-4-ruling, C-3, T1-R12, C8]:
release binds to the Slack THREAD plus an authorized sender, and to nothing else.

## Design
The arm is deleted rather than repaired, because the fact it was reconstructing now lives
somewhere else entirely — the daemon's `open_asks` row, released by
`bridges/chat/ask-thread.js` against the thread the ask was posted in (`spec-owner-io` §2.4,
`spec-state-store` §3). Nothing on the coordination bus releases anything any more.

`re:` SURVIVES, as a log field and only as a log field. It says which numbered row an answer was
written about, and `open_escalations` still honours it so a numbered reply stops nagging. That is a
RENDER: it opens no hold, reaps no wait, fires no relaunch and flips no stored state — `open_asks`
filters `type == "ask"` and an escalation is never one. Keeping it costs nothing and dropping it
would have left a numbered reply nagging forever, which is the defect the C78 arm was built for.

## How it works
`open_escalations` now returns the escalation/marker rows that are neither superseded nor named by
an answer's `re:`, and stops. The docstring states the deletion and its ruling ids at the point of
deletion, so the next reader meets the wall rather than an unexplained gap. `cmd_send`'s escalation
dedup comment is retargeted: it releases when the row is settled BY NUMBER or superseded, since the
unnumbered-answer settle no longer exists.

`coord_selftest.py`'s W8 arm 4 is INVERTED rather than deleted — it sends the identical unnumbered
owner answer and now asserts BOTH halts stay open, with the red-first mutation named in the comment
(restore `rows.remove(mine[0])` and the count goes 2 -> 1). Arm 5, which proved the dedup is
at-most-once rather than once-ever, needed a settle that still exists: it now refuses the duplicate
key while the halt is open, settles by `--re`, and raises the same key again.

## Consequences
`owed-answers.py` and `pending` inherit the change with no edit — both only READ this view, and an
unanswered halt now stays visible until someone names it or supersedes it, which is the honest
reading. `checkout.py` was already off this door (its `block-and-queue` hold reads the store and
its comment already said `--re` no longer lifts it), and `ask-store.js` had already lost
`markAnswered`'s oldest-open default when the thirteenth gateway intent landed. So the deletion
completes a retirement three earlier commits had started from the other end.

## Verification
`node --check` is not applicable; `py_compile` clean on both files. The door itself was measured
directly, since `coord.py selftest` cannot reach the W8 arms: on a temp package, two escalations
from `leader` to `owner`, open = [1, 2]; the C78 return leg verbatim (unnumbered `type: answer`
from `owner` to `leader`) leaves open = [1, 2] — the arm is gone; an answer carrying `re: 1` leaves
open = [2] — the named settle still drops exactly the row it names.

`coord.py selftest` ABORTS at check 389 on `NameError: awaiting_path` at `coord_selftest.py:4113`.
That is PRE-EXISTING and not this change: `awaiting_path` is defined in NO kit module at HEAD (the
ending-store migration deleted it and left four call sites in the awaiting-close-debt block), and
stubbing past it reaches a second pre-existing red at check 391 (`KeyError: 'free2'`). Surfaced,
not worked around. Not deployed — worktree branch `ignite/core-redesign`.

## ATTENTION
1. A settle rule that picks "the oldest" is a guess wearing a policy's clothes. It is indistinguishable from correct behaviour on a seat holding ONE open row, which is why this one survived months: the failure needs two open halts and nobody reads the log when there is one.
2. `re:` is a LOG FIELD now and must stay one. Honouring it in a RENDER is safe; wiring it to a hold, a reap or a relaunch would rebuild the door this deleted, by a different name.
3. `coord.py selftest` cannot run to completion at HEAD — it aborts at check 389 on a symbol the ending-store migration removed. Any seat that reports the kit selftest green after touching `coord_selftest.py` has not run it; the arms past 389 are UNKNOWN, not passing.
4. The W8 arms were INVERTED, not deleted. A probe that asserts an absence is worth more than one that is missing, and arm 4 now carries its own red-first mutation so it cannot go vacuous.
- coord.py selftest aborts at check 389 on a pre-existing NameError (awaiting_path); every arm past it is UNKNOWN, not passing
