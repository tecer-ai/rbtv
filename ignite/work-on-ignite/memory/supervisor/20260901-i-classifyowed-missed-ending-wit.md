# 20260901-i-classifyowed-missed-ending-wit — classifyOwed missed ending-without-session seats

kind: issue
component: supervisor
date: 2026-09-01
commit: 3a2e28e6
deployed: no
pin: ignite/supervisor/owed-from-endings.selftest.js
components: state-store

## Observed
`classifyOwed` never surfaced a seat whose ending was stamped with zero `sessions.csv` rows.

Measured live on `.rbtv/goals/test-retry-proof/` (`rr-live-proof`, 2026-09-01): `worker-a` carries a real `incomplete/armed:1` ending row and zero session rows, and never once appeared in `classA`/`classB`/`classE` across six real reconcile passes (23:21:58Z-00:00:45Z). No exclusion reason was logged anywhere, because the seat was never a candidate — not excluded, never asked about.

## Mechanism
The candidate set was built from `sessions.csv` alone, so an ending-only seat was structurally unreachable.

`const seats = [...last.keys()]` (`owed-from-endings.js:279`), `last = lastBySeat(loadSessions(goalFolder))`. The classA loop iterated `last` directly. In the normal daemon path this never bites — a `sessions.csv` row is written AT LAUNCH TIME, before the process runs, even for a seat that crashes in the first second. The gap only opens for an ending stamped with no launch ever recorded: an external/admin tool, or a hand-built fixture (how `rr-live-proof` reproduced `worker-a`, deliberately, in an earlier sitting).

## Attempts
First attempt held — checked: `rr-live-proof`'s prior sitting (root-caused the gap, no code change, `1-projects/build-ignite/build/redesign-continue-1/seats/rr-live-proof/report-resume.md`) and this plan's `loose-ends.md`. No earlier fix attempt exists.

## Fix
Rejected widening to the full `taskforce.csv` seat set; built the narrow ending-row-only alternative instead.

A healthy goal is full of seats that simply have not launched yet (verified: `system-health` carries 14), and classA cannot tell those apart from a real candidate without a session row — that widening would flood class A on every pass, every goal. New `listSeatsWithEndings(db, {goal})` (`ignite/state-store/predicates.js`, exported through `bind()`) answers "which seat names does the ending store hold a row for" — the complement of `getCurrentEnding`. `classifyOwed` unions `last.keys()` with that list minus what `last` already has; the classA loop reads `last.get(seat) || null` and falls back to the ending row's own `stamped_at` for `ended` when no session row exists. A seat with no ending row is unaffected either way — `classifyEnding` already returns `null` for it.

## Consequences
`endingMap`/`holdMap`/`abandonedMap`/classE's `pending` loop now also see ending-only seats, since they share the widened `seats` variable — a hold or abandonment on an ending-only seat is now respected too. The returned `seats` field now reports the true universe instead of a stale `[...last.keys()]` recompute. No caller reads `.seats` today (checked `reconcile.js`, `owed.js`, `lane-watch.js`).

## Verification
`node ignite/supervisor/owed-from-endings.selftest.js` — 14/14 PASS (new arm `caseInvisibleEndingSeatBecomesClassA`, red-proven against a scratch `git worktree add <tmp> HEAD` of the pre-fix commit). `node ignite/state-store/ending-store.selftest.js` — 14/14 PASS, no regression. `node ignite/supervisor/reconcile.selftest.js` — 24 arms PASS before the PRE-EXISTING `:846` stale mutation-anchor abort (documented in this plan's `loose-ends.md`, confirmed unrelated — the anchor string is absent from `owed-from-endings.js` both before and after this change). Direct real-fixture proof on `test-retry-proof`: `worker-a` now in `classA`; `worker-b`/`worker-c` unchanged; `leader` (also ending-only, `armed:0`) enters the candidate set but stays correctly excluded by `classifyEnding`. False-positive control on the live `system-health` goal (14 never-launched, zero-ending-row seats): identical before/after. Committed `3a2e28e6` on `ignite/core-daemon`, not deployed (deploy tree pinned `e60ee8f9`).

## ATTENTION
1. A caller that injects `endings` directly (this file's own selftest, `reconcile.selftest.js`'s `endingsMap(...)`) bypasses the store — reads `[...endings.keys()]` instead of `listSeatsWithEndings`, so an ending-only seat must be a key of that Map, not just present in the real store.
2. `ended` for an ending-only candidate is the ending row's `stamped_at` (ISO), not the minute-precision `sessions.csv` `ended` cell a launched seat carries — the two have no shared clock, do not compare them literally.
3. Do not confuse this with `test-retry-proof`'s OTHER known defect (missing envelope compile, cage lacks the `claude` binary bind) — a separate, unrelated `rr-live-proof` finding, out of this fix's scope.
- endings-injected callers bypass the store, must key their Map by the ending-only seat too
