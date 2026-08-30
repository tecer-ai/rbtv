# 20260830-i-readcursor-answered-the-first — readCursor answered the first workers.md row, not the newest

kind: issue
component: supervisor
date: 2026-08-30
commit: a340bb28
deployed: no
pin: ignite/supervisor/owed-from-endings.selftest.js

## Observed
Live, post-deploy (daemon `26773c34`, 2026-08-30 17:53Z UTC): on `meet-transcript-summarizer-planning`,
`workers.md` carries 8 leader rows (one per sitting, append-only). `readCursor` answered the
FIRST matching row's cursor — sitting 1 (session `ddeb2959`), lastread `0` — instead of the newest,
sitting 8 (session `cf59debf`), lastread `25`. Every message #1-#25 therefore read as unread on
every reconcile pass, and the leader was relaunched twice with no new mail (`cf59debf` 17:57Z,
`c82409d8` 18:02Z; journal `reconcile: pass … classB:["leader"]` at 18:02:26Z, right after
`cf59debf` had already checked out with cursor 25). The orchestrator placed a `supervise hold` on
the leader at 18:04Z to stop the loop; the attempt-counter brake (`44228d94`, N=3) would have
allowed one more paid sitting before it engaged.

## Mechanism
`readCursor(goalFolder, chair)` (`20260830-i-class-b-unread-test-read-check`'s own fix) iterated
`workers.md` top-to-bottom and `return`ed inside the loop on the FIRST line whose agent column
matched the chair. `workers.md` is append-only per sitting — `coord/checkout.py#cmd_checkin` never
rewrites an existing row, it always appends a fresh one, and `coord/messages.py#current_row`
("Latest row for an agent — last check-in wins") is `mine[-1]`, the LAST match in file order. A
chair with more than one sitting therefore has more than one row, and the first-match return read
the OLDEST sitting's cursor forever, never advancing as later sittings actually read mail.

## Attempts
First attempt held — checked `20260830-i-class-b-unread-test-read-check` (this function's own
creation, which assumed — untested against a multi-sitting fixture — that a chair has at most one
`workers.md` row) and `20260830-i-class-b-stopped-waking-an-exha` (the attempt-counter brake,
unaffected: it read whatever `readCursor` handed it and the brake's own logic is correct — the
input was wrong).

## Fix
`readCursor` now scans every matching row and keeps the LAST one's own value (numeric or not).
This is the exact invariant `cmd_checkin` (coord/checkout.py) already writes: a new row inherits
`max(every prior row's lastread for the SAME agent)` — "the read cursor belongs to the SEAT, not to
one session of it" — so the cursor is monotonic across that seat's sittings and the newest row's
own value is authoritative whenever it is numeric. A non-numeric/blank cursor on the newest row (a
row not written by `cmd_checkin` — the only writer this invariant binds) falls back to the highest
numeric cursor found on any EARLIER row of the same chair, rather than jumping straight to "owed
all mail": that number is still the seat's last known truth per `cmd_checkin`'s own inheritance
rule. Only a chair with NO numeric cursor anywhere in its history gets the "owed all" fallback
(`null`) — matching the pre-existing "no evidence of a read yet" default for a chair with no
roster row at all.

Rejected: filtering to the `active: yes` row only (a chair with no currently-live sitting — the
exact case here, since sitting 8 had already checked out — would have no active row and fall back
to "owed all," reintroducing the same defect); re-deriving the cursor from `sessions.csv`'s
`checkin` column instead of `workers.md`'s `lastread` (this is precisely the check-in-vs-read
conflation the ORIGINAL Defect-B fix, `fa89fa75`, closed).

## Consequences
None outside `readCursor`'s own body — its signature (`readCursor(goalFolder, chair)`) and every
caller are unchanged. `unreadFrontierExhausted` (`44228d94`) and every other class-B consumer now
receive a correct cursor for a multi-sitting chair.

## Verification
`node owed-from-endings.selftest.js` — 9 arms, `ALL PASS`: a new arm (5) builds a 3-row `workers.md`
(cursors 0, 9, 25) and asserts `readCursor` answers 25 directly, then that mail up to #25 is NOT
owed and mail #26 IS, naming the true frontier; a RED mutation reverts to the first-match `return`
and reproduces the incident exactly (`readCursor` answers 0 against the same 3-row fixture). Full
`ignite/supervisor/*.selftest.js` sweep unchanged before/after: `reconcile.selftest.js` still aborts
at its pre-existing `:392` assertion, 6 PASS before it — identical across `fa89fa75`, `44228d94`,
and this fix. NOT deployed at filing; commit `a340bb28` on `ignite/core-daemon`. No `.rbtv/` planted
under the repo root.

## ATTENTION
1. `workers.md` being append-only-per-sitting is a fact of `coord/checkout.py#cmd_checkin`, not of
   `owed-from-endings.js` — any future reader of that file that assumes "one row per chair" (as
   this function's own first version did) reproduces this exact class of defect. `current_row`'s
   `mine[-1]` convention is the one true rule; a new reader should call out to it or restate it
   explicitly, never re-derive "the" row by name lookup alone.
2. The non-numeric-newest-row fallback (scan history for the max prior number) is UNTESTED against
   a real corrupt/foreign-writer row in production — it is a defensive branch for a shape
   `cmd_checkin` itself never produces (every row it writes is numeric by construction), so it has
   no live incident behind it, only the orchestrator's explicit instruction to handle it this way.
- workers.md is append-only per sitting (cmd_checkin never rewrites a row); any reader assuming one row per chair reproduces this
