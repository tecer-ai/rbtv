# 20260901-c-listseatswithendings-the-missi — listSeatsWithEndings — the missing side of getCurrentEnding

kind: creation
component: state-store
date: 2026-09-01
commit: 3a2e28e6
deployed: no
components: supervisor

## Motivation
`classifyOwed`'s candidate set needed a way to ask "which seats does the ending store hold a row for" without already knowing the seat names — the missing half of `getCurrentEnding`, which needs a name to look one row up.

## Design
A plain `SELECT seat FROM seat_endings WHERE goal = ? ORDER BY seat` in `ignite/state-store/predicates.js`, matching the shape of the sibling list query `listSeatHolds` right above it.

Considered returning full ending rows (saving `endingsForSeats`'s later per-seat re-fetch) and rejected it: `classifyOwed` already has `endingsForSeats` as its one ending-row reader, and a second reader of the same table would be two sources for one fact — exactly the pattern `heldSeats`'s own header comment warns against. A name-only list keeps `getCurrentEnding` the sole reader of a row's content.

## How it works
Exported from `predicates.js`, wired into `bind()` in `ignite/state-store/index.js` as `api.listSeatsWithEndings({goal})`. `owed-from-endings.js#classifyOwed` calls it once per pass (when no `endings` Map was injected) to compute `endingOnly = listSeatsWithEndings(...).filter(seat => !last.has(seat))`.

## Consequences
Nothing replaced or deleted — this is purely additive alongside the existing `getCurrentEnding`/`listSeatHolds` readers. No other caller exists yet beyond `classifyOwed`; a future caller wanting the same list should reuse this function rather than writing a second `SELECT ... FROM seat_endings` against the same table.

## Verification
`node ignite/state-store/ending-store.selftest.js` — 14/14 PASS, no regression. Exercised indirectly by `owed-from-endings.selftest.js`'s new `caseInvisibleEndingSeatBecomesClassA` arm (14/14 PASS). Committed `3a2e28e6`, not deployed.

## ATTENTION
1. Unfiltered by liveness or exclusion state (unlike `listSeatHolds`, which filters through `seatHeld`) — it returns every seat name with ANY row, done/incomplete/failed alike. A caller wanting only non-terminal seats must filter after calling it, not assume it already did.
