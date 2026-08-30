# 20260830-i-class-b-unread-test-read-check — class B unread test read check-in, not the cursor

kind: issue
component: supervisor
date: 2026-08-30
commit: fa89fa75
deployed: no
pin: ignite/supervisor/owed-from-endings.selftest.js

## Observed
`stools-canvas-audio-elevenlabs-close`, 2026-08-28: message #45 (boundary-auditor → leader,
`type: completion`, stamped `2026-08-28 22:17`, minute precision) drove the unread-mail wake at
22:17:32 that launched leader sitting 10 at 22:17:39Z. Sitting 10 checked in ("checked in: leader
(sid:b6731ba8…) (cursor kept at #43)"), ran `coordinate read` (which showed it #45 in full, and
would have advanced its `lastread` cursor to 45), then died on an HTTP 429 39 s later. Every
`reconcile: pass` from 22:18 onward read `classB:[]` — the wake was gone, and nothing in
`owed-from-endings.js` could re-derive it, so the goal stayed frozen with no self-healing path even
though defect A's swallow was a separate, compounding cause.

## Mechanism
`classifyOwed`'s class B loop computed `since = checkinOf(last.get(chair))` — the chair's last
CHECK-IN timestamp, at MINUTE granularity (`sessions.csv`'s `checkin` column) — and filtered
`unread = messages.filter(... !since || tsAfter(m.ts, since))`. Check-in and `coordinate read` land
in the same daemon-lane sitting, seconds apart, so a message stamped in that SAME MINUTE as
check-in reads as "after check-in" and is filed READ FOREVER from the very next pass — regardless
of whether the sitting ever actually called `read`, let alone acted on the mail. Merely checking in
discharged the wake; nothing verified progress. In THIS incident the sitting DID call `read` before
dying, so the cursor genuinely advanced to 45 — meaning the fix does not by itself recover this
specific goal (that needed defect A); the fix's value is the hypothetical it closes: a sitting that
checks in and dies BEFORE ever calling `read` would, under the old logic, have its wake silently and
permanently discharged by the check-in alone.

## Attempts
First attempt held — checked the diagnosis at
`1-projects/build-ignite/build/role-action-program/seats/diag-stools-close-unfired/report.md`
(orchestrator-verified, 2026-08-30, "Option 2"), and `20260827-i-new-staff-mail-counted-as-a-re`
(a related but distinct defect in the SAME file's attempt-counting, already fixed and not touched
here).

## Fix
Class B now reads the chair's own READ CURSOR — `workers.md`'s `lastread` cell
(`coord/records.py#persist_cursor`, advanced ONLY by `coordinate read`'s unfiltered non-peek path,
never by `checkin`) — via a new `readCursor(goalFolder, chair)`, and compares a message's own
NUMBER against it (`cursor === null || m.num > cursor`) instead of a timestamp against a check-in
moment. An integer comparison against the exact cursor `coordinate read` maintains is precise where
a minute-stamp comparison against a different act (check-in) could only ever be approximate. A
chair with no roster row, an unreadable `workers.md`, or a blank/non-numeric cursor is owed ALL its
mail (`cursor === null`) — the same "no evidence of a read yet" default the old `checkinOf`
fallback used for a chair with no session.

`checkinOf`/`tsAfter` stay in `classifyOwed`'s destructured parameter list even though the function
body no longer calls them: `reconcile.selftest.js`'s pre-existing F-1 red-mutation arm (same-minute
sitting) splices a line calling `tsAfter(...)` verbatim into this function's own source and
re-compiles it, relying on that name resolving through THIS closure. Removing either name breaks
only that one mutant, silently (discovered mid-fix: a first pass that dropped both params passed
every other selftest and crashed `reconcile.selftest.js` with `ReferenceError: tsAfter is not
defined` at a line that does not exist in this file's own source — the mutant's SPLICED line).

The existing attempt-counter brake (`attempt-counters.js`, `RECONCILE_RESPAWN` driver,
`reasonClass: 'unread'`, wired generically in `reconcile.js:983-991/1187-1206`, unedited) needed NO
change: it already keys its owed-item marker on class B's own `#lastNum` field, unchanged by this
fix, so a chair that keeps dying on the same unread mail across passes still disarms at the
recovery config's `attempt_counter_n`.

## Consequences
None outside `owed-from-endings.js`. `classifyEnding`, class A, class E, and the hold exclusion are
untouched. No caller signature changed — `classifyOwed(goalFolder, opts)` still accepts every field
`reconcile.js#owedFromLedgers` passes; it simply reads two of them (`checkinOf`, `tsAfter`) for a
different, narrower reason now (mutation-harness compatibility, not production logic).

## Verification
New `node owed-from-endings.selftest.js` — 5 arms, `ALL PASS`: (1) a message stamped in the
check-in MINUTE but after the read cursor wakes the chair (the exact incident shape); (2) a message
the cursor has already passed does not wake the chair; (3) composing the fixed class B output with
the real, untouched `attempt-counters.js` API across `attempt_counter_n` identical dead passes on
the same mail reaches `exhausted: true`, counter row named
`reconcile-respawn / <goal>/leader / unread`; two RED mutations — reverting to the pre-fix
checkin/tsAfter comparison reproduces the freeze (arm 1 flips to not-woken), and a cursor read that
ignores `workers.md` (hardcoded to `0`) over-wakes on already-read mail (arm 2 flips to woken). Full
`ignite/supervisor/*.selftest.js` sweep unchanged before/after; `reconcile.selftest.js` still aborts
at its pre-existing `:392` assertion, same PASS count (6) before and after — its F-1 mutation arm
(`:294-301`, needs `tsAfter` reachable) still passes; its class-B anchor arm (`:828-835`, anchors the
literal deleted `&& (!since || tsAfter(m.ts, since)));` line) is now permanently RED once the suite
reaches it, but the suite currently aborts at `:392` before ever reaching `:828` — see ATTENTION 1.
NOT deployed at filing; commit `fa89fa75` on `ignite/core-daemon`. No `.rbtv/` planted under the
repo root.

## ATTENTION
1. `reconcile.selftest.js:828-835` anchors the OLD class-B line
   (`&& (!since || tsAfter(m.ts, since)));`) verbatim and mutates it to prove a DIFFERENT, already-
   fixed regression (`m.num > (Number(since) || 0)`, a plausible-but-wrong bug from an earlier
   attempt at this same fix). That anchor string no longer exists in `owed-from-endings.js`; the
   `assert.ok(src.includes(ANCHOR), ...)` will fail the moment a future fix lifts the pre-existing
   `:392` abort that currently hides it. `reconcile.selftest.js` is outside this seat's walls
   (`ignite/supervisor/death-stamp.js`, `owed-from-endings.js`, `attempt-counters.js` only) — this
   is a surfaced, not fixed, loose end for whoever next edits that file.
2. In THIS incident the fix alone does not recover the frozen goal: sitting 10 genuinely called
   `coordinate read` before dying, so its cursor legitimately advanced past #45. The fix's
   self-healing value is for a sitting that dies BEFORE ever calling `read` — do not expect this
   change alone to unfreeze `stools-canvas-audio-elevenlabs-close`; that recovery depends on defect
   A (`20260824-c-supervisor-death-stamp`'s stale-done fix, filed alongside this entry).
- reconcile.selftest.js:828-835 anchors the deleted checkin/tsAfter line; goes red once its own pre-existing :392 abort is lifted
