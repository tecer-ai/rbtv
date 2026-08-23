# 20260820-i-same-minute-sitting-not-supers — Same minute sitting not superseded

kind: issue
component: engine
date: 2026-08-20
commit: 2ddb8644
deployed: yes
pin: NONE
seeded: true

## Observed
On 2026-08-20 three meet sittings — `plan-3-plan-check-consistency`, `-edges`, `-resources`, sat 05:38–05:40 — were invisible to the reconcile watcher: `deriveOwed` never put them in class (a), so they were not owed work. A stools seat that exited in under 60 s the same day also dropped out of class (a) and swept its own strike counter. `2ddb8644` (18:21:53Z, Henrique / Claude Opus 5) recorded the shape: `started: '2026-08-20T05:38:40Z'` against `ended: '2026-08-20 05:38'` (coord's second-vs-minute write). No goal folder is named; the selftest later reused the edges seat and those timestamps as the verbatim fixture. At HEAD `laterSitting` is still gone and the F-1 comment still sits above `lastBySeat`; engine JS is inert until `rbtv ignite daemon deploy`. Header `deployed: yes` was not re-checked against a deploy log.

## Mechanism
`deriveOwed` walks `lastBySeat(sessions)`, which already keeps the row with the MAXIMUM `started` per seat. Immediately after `if (!ended) continue;` it then called `laterSitting(sessions, seat, ended)` and `continue`d on a hit — meaning "a later sitting of this seat exists, so this row is superseded." `laterSitting` was `rows.some(r => same seat && tsAfter(r.started, afterEnded))`. `tsAfter` runs `normTs` (swap `T` for space, strip `Z`) then a string `>`. After that, `2026-08-20T05:38:40Z` is `2026-08-20 05:38:40` and `2026-08-20 05:38` is unchanged, so the row's own `started` compares AFTER its own `ended`. Because `lastBySeat` already picked the latest start, no other row of that seat could satisfy the predicate — the only possible hit was self. The sitting vanished from class (a).

## Attempts
First attempt held — checked: `git log -S laterSitting -- ignite/engine/reconcile.js` has only two hits: `808902df` (2026-08-19 21:23Z, "feat(engine): reconcile owed work from the ledgers (D1/D15)"), which introduced `laterSitting`, `tsAfter`, and the `deriveOwed` call site together, and this delete. No intermediate commit touched the predicate. `missed_trials_source` is empty; no earlier memory entry names `laterSitting` or `2ddb8644`. This was a bug in the original D1/D15 derivation, not a later regression.

## Fix
`2ddb8644` deleted `laterSitting` and the call site. No replacement: `lastBySeat`'s max-`started` selection already guarantees no later sitting exists for the row it returns, so the predicate was dead even when the timestamps had matched precision. Patching `laterSitting` to skip self, or normalizing `ended` to second precision, would have kept a function that could never return true for a `lastBySeat` row. The trade-off is that a future editor who wants a real "superseded by a later sitting" check has to re-derive it from something other than `lastBySeat`'s output — which is the point. No D-id or E-id names this; F-1 is the commit's own tag. A ⚠ comment was added directly above `lastBySeat` recording the invariant.

## Consequences
Nothing else was rewritten in `2ddb8644` besides the new F-1 selftest arm. Same-day later commits (`e3fc940f` D42, `23de241f` D43/D44) and the 08-22 reconcile work (`23578584` D81, `affceae2` D52/D66/D70) do not mention F-1 or restore `laterSitting`; D42's hold-skip now occupies the line after `if (!ended) continue;` where the deleted guard sat. `git log -S laterSitting` after 2ddb8644 is empty. No follow-up issue was filed. Shared `probe-reconcile` grew the F-1 say-block; it is not a dedicated pin (header `pin: NONE`).

## Verification
`reconcile.selftest.js` gained say-block `── F-1: a sitting that starts and ends inside ONE minute is still class (a) ──`. GREEN: fixture seat `plan-3-plan-check-edges`, `started: '2026-08-20T05:38:40Z'`, `ended: '2026-08-20 05:38'`, `disposition: 'exited'`; asserts `deriveOwed(...).classA` still contains that seat and `owed === true`. RED: reads live `reconcile.js`, locates the anchor `if (!ended) continue;`, `_compile`s a copy with the deleted `sessions.some(... tsAfter(r.started, ended))` spliced back, and asserts `classA === []` and `owed === false` — the arm fails if it cannot discriminate the bug. `probe-reconcile.out` records both ok lines and `exit: 0`. Header `deployed: yes`.

## ATTENTION
- After `lastBySeat`, a "superseded by a later sitting" check can only ever match the row against itself. Reintroducing `laterSitting` (or any `tsAfter(started, ended)` walk of the same seat) will drop same-minute sittings out of class (a) again. The in-code ⚠ above `lastBySeat` exists because this already happened (F-1).
- coord writes `started` at second precision (`2026-08-20T05:38:40Z`) and `ended` at minute precision (`2026-08-20 05:38`). `tsAfter` / `normTs` then string-compare them; any same-minute sitting's own `started` sorts AFTER its own `ended`. New timestamp ordering in this file that mixes the two columns will reproduce the collision even without `laterSitting`.
- The F-1 RED arm in `reconcile.selftest.js` proves discrimination by splicing the old guard into a `Module._compile` copy of the live source (anchor `if (!ended) continue;`). Deleting that arm as redundant with GREEN leaves the test unable to tell a working `deriveOwed` from one that never saw the same-minute shape.
