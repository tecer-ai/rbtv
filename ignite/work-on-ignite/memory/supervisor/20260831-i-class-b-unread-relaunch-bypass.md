# 20260831-i-class-b-unread-relaunch-bypass — Class B unread relaunch bypassed a live seat hold

kind: issue
component: supervisor
date: 2026-08-31
commit: bb1e6350
deployed: no
pin: ignite/supervisor/reconcile.selftest.js

## Observed
A live hold did not stop class-B relaunches. `meet-transcript-summarizer-planning/leader` held 2026-08-30 18:04:23Z; the 18:07:33Z pass logged `heldExcluded` naming it AND launched it via `classB` — two paid sittings (`ed9ffb12`, `e60bb439`). Ruling: `build/role-action-program/decisions.md`; register filing under `.rbtv/goals/_archive/ignite-engine/register/open/`.

## Mechanism
`classifyOwed`'s class-B loop never consulted `holdMap` → the same `holdMap` class A and class E already read. Its own header comment stated the omission as intended ("Class B is untouched"), which was the defect's own documentation, not a ruling. A chair excluded from class A by name stayed a live class-B target on the identical pass, because the two classes decided the same exclusion independently instead of sharing it.

## Attempts
First attempt held — checked: `build/role-action-program/decisions.md` (the hold-bypass ruling: filed as loose-ends + register entry, no fix seat ran before this one); `a340bb28` (readCursor NEWEST-row fix, a distinct defect in the same incident window — it fixed which mail counts as unread, not whether a held chair can be woken by it).

## Fix
Added `if (holdMap.has(chair)) continue;` to the class-B loop in `classifyOwed`, in the same position class A uses relative to its other exclusions (dead, summoned, then held). No second hold check was added at the launch/reconcile.js level — `reconcile.js` only logs `heldExcluded` and launches `derived.classB` as returned by the classifier, so the fix belongs solely in the one place that DECIDES class membership, not in a second agreeing rule at the call site (the class-A comment already warns against "two agreeing rules"). Updated the class-A/B exclusion comment block to state the SEAT-level (not reason-class-level) scope explicitly, and cited the live incident inline so a future reader cannot reintroduce the same "class B is untouched" reasoning. `component.md`'s hold section gained one sentence noting class B is now covered.

## Consequences
No other call site changed. `classE`'s hold exclusion (already present) is unaffected. The class-A hold selftest arms (control, release, new-ending, RED) are untouched and still pass their own arms.

## Verification
`ignite/supervisor/owed-from-endings.selftest.js` — unaffected, ALL PASS (`node ignite/supervisor/owed-from-endings.selftest.js`). `ignite/supervisor/reconcile.selftest.js` gained one hold arm (control + 2 held passes + RED mutation) for class B, verified correct via a standalone scratch-script probe reproducing the exact selftest logic against the committed source (the full suite itself is blocked end-to-end by an unrelated PRE-EXISTING failure at line ~393, "leader payload never names ... BOOT-PROMPT-BODY", confirmed present at HEAD with zero uncommitted changes anywhere in the tree via `git stash` — a shared-file defect, not touched by this fix, surfaced separately). Not yet deployed — committed `bb1e6350` on `ignite/core-daemon`, deploy owned by the plan orchestrator per `read-first.md`.

## ATTENTION
1. The class-A/class-B/class-E hold exclusions must all read the SAME `holdMap` computed once per `classifyOwed` call — adding a fourth "owed" class later must consult it too, or this exact bypass recurs under a new name.
2. `reconcile.js` deliberately does NOT re-check holds at the launch site — it trusts `classifyOwed`'s class membership entirely. A future change that adds launch logic outside `classifyOwed` (e.g. a new caller of `owedFromLedgers`/`deriveOwed`) must not skip this classifier or it bypasses every hold silently.
3. `reconcile.selftest.js` currently has a PRE-EXISTING unrelated failure (D33(a) leader-payload assertion, around line 393) that aborts the whole suite before reaching the hold arms — this blocks full-suite verification of ANY change to this file until fixed by whoever owns that region; it predates this fix and was not introduced by it.
4. The shared working tree wiped this fix's uncommitted edits mid-session (another party's `git restore`/checkout on the same files) — re-applied and committed immediately after re-verifying; anyone resuming this task should re-check the file state on disk against `bb1e6350` before assuming further work is needed.
- share one holdMap across class A/B/E
