# 20260902-i-materialize-seats-can-t-write — materialize-seats can't write successor-gate columns

kind: issue
component: planning
date: 2026-09-02
commit: 9a9845fb131c7a3a786f7cee7791f2a82422f786
deployed: yes
pin: ignite/supervisor/probes/probe-failed-upstream-gate.py

## Observed
`ready.py` (the code that decides whether a successor seat may launch) already read optional `gate-
artifact`/`gate-required` columns from `taskforce.csv` (a goal's table of who runs on which seat),
landed in commit `48c86e40` and recorded in `supervisor/20260831-i-successor-launched-on-
sitting.md`. But `ignite/planning/materialize-seats.py` (the writer of `taskforce.csv`) still exact-
matched the old 8-column header byte-for-byte, so no goal's `taskforce.csv` could ever actually
carry those two columns — the reader shipped with no writer able to feed it. Named as `redesign-
continue-1` loose-ends.md entry 8, and flagged as a known limitation in the reader's own memory
entry's ATTENTION section ("Extra columns are not in TASKFORCE_HEADER; materialize still exact-
matches the eight-column header and will refuse a live goal that carries them").

## Mechanism
`materialize-seats.py`'s header-acceptance check compared the file's header against
`TASKFORCE_HEADER` (the fixed 8-column list) with a byte-exact match. Any extra trailing column,
including the gate columns `ready.py` needed, caused the check to refuse the file. The writer had no
code path to add those columns when creating a new goal's `taskforce.csv`, and no code path to
populate their cell values per-row even if the header did carry them.

## Attempts
First attempt held — checked: `48c86e40`/`supervisor/20260831-i-successor-launched-on-sitting.md`
itself, which built the READER side only and explicitly named the writer-side gap as future work,
not yet done. No prior commit touched `materialize-seats.py`'s header validation for this purpose.

## Fix
Header acceptance is now a prefix/column-set match instead of byte-exact: the file's header must
start with the base 8 columns from `TASKFORCE_HEADER`, and any trailing columns must be exactly one
of no-gate-columns, `gate-artifact` alone, `gate-required` alone, or both (`TASKFORCE_GATE_COLUMNS`)
— never an arbitrary widened set. A brand-new goal's header is widened to include the gate columns
only when the caller's bindings file actually declares a gate for at least one seat, peeked before
the package-creation step (which runs ahead of the real bindings load). Each row's gate cells are
read off that seat's own binding and matched to whichever gate columns the header carries; a seat
that declares a gate the header lacks is refused (`gate-column-absent`) rather than silently
dropped. `gate-artifact`/`gate-required` joined `ALLOWED_BINDING_KEYS` as registry-only data, never
written into a seat's own instruction file — the same shape the existing `after` key already uses.

## Consequences
Existing (already-materialized) goals' `taskforce.csv` files are untouched — `append_taskforce_rows`
deliberately leaves existing bytes, header included, byte-unchanged, so an already-running goal
cannot retroactively widen its header. A goal that wants the gate feature must declare it in the
bindings used at the goal's FIRST materialize call. This is a documented design limit, not a follow-
up gap.

## Verification
Scratch copy of a real, unmodified goal's `taskforce.csv` (`.rbtv/goals/system-
health/taskforce.csv`) round-tripped through the changed validation code: accepted, zero rows
planned, header read back unchanged. End-to-end on a throwaway fixture goal: writer produced a
header carrying both gate columns; a row with declared gate cells (`gate-evidence.json` /
`verdict=PASS`) round-tripped correctly; a row with no gate declared came back with blank gate
cells; `ready-seats` read a FAIL evidence artifact as BLOCKED and a PASS artifact as READY off the
same writer output. Pinned probe `ignite/supervisor/probes/probe-failed-upstream-gate.py`: PASS, run
twice. `materialize-seats.py --selftest`: zero FAIL lines through the dag-04/dag-05/dag-06
acceptance suites this change touches (the run's later, unrelated crash in
`run_staff_mint_acceptance` is the separate, pre-existing `ending_store.EndingStoreError` gap fixed
by commit `0e33e00c`). Not deployed — no daemon restart dependency; `rbtv ignite daemon deploy`
makes it live.

## ATTENTION
1. `supervisor/20260831-i-successor-launched-on-sitting.md`'s ATTENTION section is now STALE on this
   one point — it still says materialize "exact-matches the eight-column header and will refuse a
   live goal that carries them." That is no longer true as of this commit; a future editor should
   not trust that line without checking this entry too. 2. Gate columns can only be added to a
   goal's `taskforce.csv` at its FIRST materialize call — there is no retrofit path for an
   already-running goal. 3. A seat that declares a gate the header does not carry is refused
   loudly (`gate-column-absent`), never silently dropped — do not weaken this to a silent skip.
- supervisor/20260831-i-successor-launched-on-sitting.md ATTENTION now STALE (claims materialize refuses the columns)
