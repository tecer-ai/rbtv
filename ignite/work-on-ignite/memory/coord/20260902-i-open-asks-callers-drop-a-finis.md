# 20260902-i-open-asks-callers-drop-a-finis — open_asks callers drop a finished seat's stale ask

kind: issue
component: coord
date: 2026-09-02
commit: cfcc92781f6879febba47c3720341ece70a4175a
deployed: yes
pin: ignite/coord/coord_selftest.py

## Observed
`open_asks(blocks, base=...)` gained an optional `base` parameter (commit `ed02fecd`, same day,
earlier) that drops an ask whose sender seat has since finished or exited, and `cmd_pending` was
updated to pass it. Three OTHER readers of `open_asks` were not swept to the same fix: `cmd_read`'s
answer-hint (`ignite/coord/messages.py`), `cmd_status`'s "asks waiting on you" count (same file), and
`owed-answers.py`'s owner-debt digest. All three called `open_asks(blocks)` with no `base=`, so an
ask from a seat that had already finished kept surfacing in all three as if someone were still
waiting on an answer. Measured live before the fix: `coordinate status` reported `asks waiting on
you: 1` against a finished seat's stale ask; `owed-answers` reported `1 owed answer` the same way.

## Mechanism
`ed02fecd` fixed the general shape (a `re:` reply settling a row, and a finished sender's ask never
expiring) at the predicate level for `pending` only, by threading `base=` through to `open_asks` at
that one call site. The other three call sites were not touched in that commit — the same defect
class (`open_asks` called without `base=`) simply had more callers than the one that was fixed. This
is the `signature change includes its callers` failure shape: a function's contract changed (an
optional filter that narrows correctness), but not every existing caller was swept to opt into it.

## Attempts
First attempt at sweeping ALL `open_asks` callers — checked: `ed02fecd`'s own diff (which fixed only
`cmd_pending`) and a repo-wide grep for `open_asks(` turned up the three unfixed readers named above.
No earlier attempt at this specific sweep existed.

## Fix
`cmd_read`'s answer-hint and `cmd_status`'s "asks waiting on you" count (both in `messages.py`) and
`owed-answers.py`'s `collect()` now all call `open_asks(blocks, base=base)` (the two `messages.py`
sites) or `open_asks(blocks, to=OWNER, base=base)` (`owed-answers.py`, keeping its existing `to=`
filter). A grep-based selftest guard was added (`coord_selftest.py`): it scans every production
`.py` file under `ignite/coord/` and `ignite/supervisor/` (excluding selftest files, which
deliberately assert the raw, unfiltered predicate) for a call matching `open_asks(blocks` with no
`base=` on the same line, and fails loud if one is found — a textual invariant chosen over an AST
walk because the invariant itself is textual: every call site literally either carries `base=` or it
does not.

## Consequences
No behaviour changed for a caller that already had no stale-ask problem; the three fixed readers now
agree with `pending` about what counts as "still open." The new guard arm means any FUTURE caller of
`open_asks(blocks, ...)` in `coord/` or `supervisor/` that omits `base=` now goes red at selftest
time, closing the class rather than only the three instances found. `owed-answers.py`'s comment at
the call site documents explicitly that this is the SAME narrowing `pending` applies, not a widen of
`p-owed-answers-locus`'s protected predicate.

## Verification
Real CLI output before/after, not unit assertions: `coordinate status` went `asks waiting on you: 1`
-> `0`; `owed-answers` went `1 owed answer` -> `no owed answers`, both against the same finished-seat
fixture. The new guard arm was proven to discriminate: RED against a scratch copy with the bug
re-introduced (a call site missing `base=`), GREEN on the real tree. Deployed — `ignite/coord/`,
branch `ignite/core-daemon`, live on deploy tree `e8524c31`.

## ATTENTION
1. The guard scans `ignite/coord/` and `ignite/supervisor/` only, by directory — a future
   `open_asks` caller added anywhere ELSE in the tree is not covered by this grep and could
   reintroduce the same stale-ask defect silently.
2. The guard matches the literal text `open_asks(blocks` with `base=` absent from the SAME line —
   a call reformatted across multiple lines (e.g. `base=` on its own following line) would read as a
   false positive or, worse, a call site that omits `base=` but happens to have the substring
   elsewhere on the line would false-negative. Keep `open_asks(blocks, ...)` calls single-line.
3. `owed-answers.py`'s `to=OWNER` filter and `base=` filter are independent and both required —
   dropping `to=OWNER` while keeping `base=` (or vice versa) changes which asks the owner-debt
   digest reports, not just whether stale ones are dropped.
