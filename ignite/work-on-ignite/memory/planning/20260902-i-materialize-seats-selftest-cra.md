# 20260902-i-materialize-seats-selftest-cra — materialize-seats selftest crashes: no install record

kind: issue
component: planning
date: 2026-09-02
commit: 0e33e00c5db225d37275e56a719bfec2653e80d0
deployed: yes
pin: NONE

## Observed
`ignite/planning/materialize-seats.py --selftest` (the tool that assembles a goal's seats, self-
testing on 63 rows of internal checks) crashed with an unhandled `EndingStoreError` traceback
partway through, at the "SM" block (`run_staff_mint_acceptance`), after roughly 381 checks. Measured
2026-08-31 during seat `selftest-aborts` (`redesign-continue-1`), confirmed reproducible on a clean
HEAD before any fix.

## Mechanism
Two of the file's own selftest fixture builders, `build_fixture()` (line 6196) and
`_staff_fixture()` (line 8780), each mint a throwaway tmp workspace but never write
`.rbtv/modules/ignite/server.json` — the install-record file `ending_store.workspace_root()`
(`ignite/coord/ending_store.py:31-59`) requires to resolve a workspace. Any selftest arm that drives
a real `coord.py`/mint call reaching the ending store — SC-1's launch coupling, the SM block's
`stamp_seat_declare` — walks the fixture tree up to the filesystem root, finds nothing, and
`ending_store_db()` raises `EndingStoreError` at `ending_store.py:76`, crashing the selftest run
outright once that block is reached.

## Attempts
First attempt held — checked: `cli_main.py`'s own selftest fixture, which already provisions this
same install-record file for the identical reason. No prior fix targeted `materialize-seats.py`'s
two fixture builders specifically; they were simply missing it.

## Fix
Both `build_fixture()` and `_staff_fixture()` now write the install record
(`_es().INSTALL_RECORD_REL`, contents `"{}"`) at fixture-build time, matching the existing
`cli_main.py` pattern. A third fixture builder in the same file, `_pf_fixture()` (line 8691), was
checked and left untouched — it never creates a `.rbtv/` tree at all, so it never reaches
`ending_store` and is not a sibling instance of this cause. No check weakened or deleted.

## Consequences
None outside the two fixture builders — the change adds one file write each, touching no production
(non-selftest) code path.

## Verification
`materialize-seats.py --selftest` now completes cleanly: `PASS — 0 failed check(s), 0 failed row(s)
of 63`, where it previously crashed with an unhandled traceback after ~381 checks. Confirmed the
SM-1 through SM-13 rows that used to crash now print `ok`. Not deployed — fixture/harness-only
change, no product behaviour touched, nothing to restart.

## ATTENTION
1. Any NEW selftest fixture builder added to `materialize-seats.py` that drives a real
   `coord.py`/mint call must also write the install-record file at build time, or it will hit the
   same `EndingStoreError` at `ending_store.py:76`. 2. `_pf_fixture()` is a deliberate exception
   — it never touches `.rbtv/` and does not need the install record. Do not add it there by
   reflex. 3. `coord.py selftest` still ends `FAIL (24 failure(s))` on unrelated, pre-existing
   reds (e.g. `7.555`, `7.278 N1/N2`, the `P2/T4/P26/P12/T2` message-cursor cluster) — separate
   from this fix, tracked for `probe-suite-green` triage.
- no entry describes build_fixture missing the install record
