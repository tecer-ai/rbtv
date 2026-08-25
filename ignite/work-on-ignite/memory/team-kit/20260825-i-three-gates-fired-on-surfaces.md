# 20260825-i-three-gates-fired-on-surfaces — three gates fired on surfaces with no writer

kind: issue
component: team-kit
date: 2026-08-25
commit: 489fa4ec,df716f29
deployed: no
pin: team-kit/probes/probe-coord-selftest-notmux.py
components: engine

## Observed
`coord.py selftest` ABORTED at check 758 with `KeyError: 'oc2'` and 70 failures — the abort inherited
from the sitting before it, which had moved it from check 644. Behind that suite failure sat three
LIVE gates in the kit, each of which refused correct work every time it ran, and none of which any
probe could see because the suite never reached them.

The first is the one the handover named: every `checkout --renew` forked its detached lifecycle
executor, and the executor died at step 7 with `'<seat>' has NO EXPORTED TRANSCRIPT recorded for
this checkout (exported=False, path=(none))` — on a renewal that had exported a perfectly good
transcript seconds earlier. `lifecycle_alarm` exits, so the renewal ended there.

The second and third were found while retargeting the rows that cover them, and neither was in the
handover. `launch --only <seat>` refused EVERY seat that had ever checked out, with `session
'<sid>' ENDED with an EMPTY disposition — NOT LAUNCHED`. And a seat whose declared output the kit
had just verified PRESENT (`outputs check: 1 declared output(s) verified present`) was stamped
`failed` / `outputs-missing` in the same command, its evidence pointer naming
`{package}/workers/{seat}/out/report.md` — a path that seat never used. Measured on a `seats/`-layout
package, which is the v2 layout every `_rs_make` fixture and the live goals both use.

## Mechanism
One mechanism, three sites: a reader left pointing at a surface spec-state-store §4.1 deleted, so
its answer became a constant and the gate built on it became unconditional.

`lifecycle_exec`'s step 7 asked `load_awaiting(base)` for the transcript its checkout had exported.
`awaiting-close.json` went with §4.1's second ending writer, so that stub had answered a permanent
`{}` since — `exported` False and `transcript` empty BY CONSTRUCTION on every checked-out act. The
first of the step's three alarms is unconditional on those two fields.

`records.undeclared_endings` read `sessions.csv`'s `disposition` cell to decide whether an ended
session had declared an ending. That column lost its last writer in the same change:
`session_close`'s `disposition` argument is accepted and ignored, `close_session_row_by_id` passes
`""`, and `cmd_checkout` stamps the store instead. `if not disp` was therefore true of every ended
row, and its one consumer — `cmd_launch`'s UNDECLARED gate — refuses by name.

`checkout.stamp_checkout_ending` re-derived a base for a relative declared output,
`{package}/workers/{seat}`, and handed the result to `stampSeatDeclare`, which re-runs the
mechanical output check (§1.3) against whatever pointer it is given. The kit's own presence check
resolves against TWO bases — the seat's `cwd`, already absolutized at `discover_workers`, and the
goal root for a bare or D90 dot-slash token — and picks the candidate that exists. Two graders of
one fact, looking at different files: the kit said present, the store said missing, and the store's
answer is the one that reached the record.

## Attempts
First attempt held — checked: `git log` on `lifecycle_exec.py`, `checkout.py` and `records.py`;
memory `20260824-c-kit-endings-via-store-client` (whose ATTENTION predicted the third defect exactly
— "Pass absolute output paths into `stampSeatDeclare`… Relative `./file.md` stamps
`failed:outputs-missing` even when the file exists" — as a caller-side caution rather than as a bug
in the stamp), `20260824-i-readiness-fixture-wrote-the-re` (the predecessor abort, which recorded
the residual reds as a vocabulary retarget and did not reach these), and
`20260824-c-persisted-supervisor-registry` (which recorded `load_awaiting` answering `{}` as a known
consequence, without a reader inventory). No earlier fix of any of the three is recorded anywhere in
the memory tree.

## Fix
Each reader moved to the surviving surface, and in two of the three the move exposed a second
question that had to be answered rather than carried over.

Step 7 now reads the ending row's `evidence_pointer` through `ending_transcript`, which answers "the
transcript, or nothing" from the pointer's SHAPE — a transcript pointer is an absolute path, every
`<kind>:<seat>` fallback is not. Tested as a path rather than string-matched against the writer's
literal, so a fallback spelling nobody greps for cannot read as a live path. The separate `exported`
flag has no successor because it never carried anything the pointer does not; that pair WAS the dual
record. The freshness half needed its own ruling: `stamped_at` is ISO-8601 UTC to the millisecond
while the old `since` was a minute-truncated local string, and the export always precedes the stamp
that points at it — so comparing raw would have made the alarm always-true again, by a precision
upgrade. The tolerance is now `TRANSCRIPT_PRECEDES_STAMP_SLACK_S`, set at the bound the truncation
already forgave, so nothing newly refused.

`undeclared_endings` asks the store per seat and treats an unreadable store as NO undeclared seats —
its own pre-existing can-not-answer direction, and the only safe one on a path whose consumer
refuses work. The migration is deliberately BEHAVIOUR-PRESERVING and is not the ruling the spec
invites: §1.1 and §2.6 say absence of an ending is launchable, which read literally retires this
gate and `--declare-only` with it. That is `cmd_launch`'s owner's call; this moved the read and
nothing else.

The output-candidate rule is now ONE function, `output_candidates`, with the presence check and the
stamp both on it. Rejected: teaching the stamp the seat's `cwd` (a third spelling of a two-base
rule), and dropping `declared_outputs` from the payload so the store stops grading (that check is
§1.3's and `probe-checkout-disposition` pins it).

## Consequences
`load_awaiting` and `clear_awaiting` are deleted with all six of their call sites, so no third
instance of this shape can be sitting behind them. `reap_blockers` went too — dead code with a live
selftest block in front of it — and two owner-level claims did NOT survive its move to
`supervisor.confirmAndReap`: the `relays:` human-door exemption (`r-owner-afk-liaison-parked`) and
#259's transcript precondition. Both are named at the deletion site and are the supervisor seat's.

The suite's own coverage moved with the surfaces: the SKEW rows (RS-5, 7.481, RS-20 arm 3) and six
7.274 rows lost their subjects and are deleted, each with its loss stated where it stood. Q2a's
per-seat containment claim is left untested and says so.

## Verification
`python3 -B coord.py selftest` from `ignite/team-kit/` with `TMUX` unset: ABORTED after 758 checks /
70 failures before, and afterwards it COMPLETES — 1014 checks discovered, no abort. Each defect was
also reproduced and re-measured in isolation before and after its fix, off the suite: the renewal
executor driven end to end through `run_lifecycle_sequence` (step list went from dying at step 7 to
`transcript-verified:<path>` followed by `successor-alive` and `state: done`);
`undeclared_endings` on a package whose seat closed a session and stamped `done` (`{'zz': …}` before,
`{}` after, and still `{'zz': …}` when no ending is stamped, so the gate discriminates in BOTH
directions); and `stamp_checkout_ending` on a `seats/`-layout package with a cwd-relative and a
goal-relative declared output (`failed`/`outputs-missing` before, `done` with the right pointer
after, on both bases). Every edited `.py` compiled with `py_compile.compile(..., doraise=True)`.
Not deployed: worktree branch `ignite/core-redesign`, no daemon restart.

## ATTENTION
- A stub that answers a constant is not a disabled gate, it is an ALWAYS-FIRING one. All three of
  these read as tidy migrations in review — the call site is unchanged and the function still exists
  — and all three refuse correct work on every run. When a surface is deleted, the stub is the
  liability; grep its readers and delete it in the same change, which is why both are gone here.
- The ending store CREATES its db lazily, on the first READ. Any row that proves a command "wrote
  nothing" by hashing a package before and after must materialize the store first, or it reports a
  read as a write — RS-11 did exactly that, and the fix is to prime the db, never to exclude it from
  the hash, because a stray ending write is the thing that hash exists to catch.
- `stampSeatDeclare` RE-GRADES the outputs it is handed. It is not a recorder — passing it a pointer
  resolved by any rule other than the presence check's silently overturns a verified `done` into a
  strike. Anything that computes a declared-output path must go through `output_candidates`.
- A precision upgrade can reintroduce the bug it was part of fixing. `stamped_at` is more exact than
  the `since` it replaced, and comparing it raw makes the staleness alarm fire on every honest
  checkout, because the export legitimately precedes its own record. Any comparison across those two
  clocks needs a declared tolerance, not a truncation nobody wrote down.
- a stub that answers a constant is an ALWAYS-FIRING gate, not a disabled one — delete the stub with its surface
- stampSeatDeclare RE-GRADES the outputs it is handed; resolve declared paths only through output_candidates
- the ending store creates its db on first READ — a wrote-nothing hash must prime it, never exclude it
