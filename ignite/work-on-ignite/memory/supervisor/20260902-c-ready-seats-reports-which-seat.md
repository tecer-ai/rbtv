# 20260902-c-ready-seats-reports-which-seat — ready-seats reports which seats daemon skips launching

kind: creation
component: supervisor
date: 2026-09-02
commit: f6c5a80829bdd83c2cca5506e95a1a4ddc64b99b
deployed: yes
pin: NONE
components: coord

## Motivation
`lane-watch.js#runLaneWatch` decides, every 10s daemon cadence, which registered taskforce seats it
will NOT launch this pass (a row with no `seats/<seat>/` folder, or one with no harness/model cast —
`laneSkips`, C-9) — but that decision lived in process memory only. A chair running `supervise
ready-seats` (a separate, on-demand Python CLI) had no way to see a seat was being silently skipped
without host journal access — task 121's owner-ruled criterion 3.

## Design
Deliberately ADDITIVE, never a verdict change: `dag-10 RS-4` (`coord_selftest.py`) rules on purpose
that a registered-but-unbuilt seat reads `READY`, stays a valid `launch --only` stub, and stays
census-addressable — that invariant is untouched. An earlier attempt inside this same task (by a
sibling seat, `freeze-scope`) tried a verdict-level `UNBUILT` fix and found it directly regressed
RS-4's own assertions; it was reverted. This design instead has `lane-watch.js` persist its own
`laneSkips` map to `<goalFolder>/coordination/lane-skips.json` every pass — including when empty, so a
seat that gets built or cast between passes clears the report too — and `ready.py#daemon_lane_skips`
reads that file and attaches the result as an ADDITIVE `daemon-skip` field on the row, present (as
`None` when not skipped) on EVERY row rather than only on skipped ones, so it can never be
misread as a term of the verdict.

## How it works
`lane-watch.js`: after computing `laneSkips` for the pass, writes `{written_at, skips: {seat: reason}}`
to `coordination/lane-skips.json` via a tmp-file-then-rename (atomic write), fail-soft — a write error
is logged at `debug` and never fails the pass, since the launch decision itself already ran correctly.
`ready.py#daemon_lane_skips(pkg)` reads that file once per `ready_seat_rows` call (hoisted, not re-read
per seat), maps each raw reason (`unbuilt-seat`, `uncast-seat`) to a human-readable
`blocked-by-uninstalled-milestone`/`blocked-by-uncast-seat` note via `DAEMON_LANE_SKIP_NOTE`, and
returns `{}` on any absence, corruption, or pre-C-9 daemon (no file yet) — informational only, so a
`ready-seats` read against a scratch fixture, a console-only goal, or a stale snapshot never raises.
Each row in `ready_seat_rows`'s output gets a `daemon-skip` key computed with NO read of `verdict` —
`verdict` is computed with no read of this field either, keeping the two fully independent.

## Consequences
No change to what launches or to any existing row field's meaning. `dag-10 RS-4`'s three assertions
(registered-unbuilt reads READY, is a valid `launch --only` stub, stays census-addressable) are
unaffected by construction — this report only adds a sibling field. An earlier, verdict-level attempt
at the same criterion (same task, sibling seat) was built, proven red/green, then correctly reverted
after it was found to regress RS-4 — that reverted patch is preserved at
`1-projects/build-ignite/build/redesign-continue-1/seats/freeze-scope/rs4b-full.patch` for reference,
not applied.

## Verification
The commit's own author ran the full `coord.py selftest` twice with both `ok` and RS-4 specifically
`ok` before committing (per the plan's loose-ends record). No dedicated automated pin/selftest exists
for THIS report's own behaviour yet — the pinning patch (`RS-4b`: an additive-with-file check and an
absence-without-file check) was written and verified applying cleanly, but deliberately NOT committed
in this same change (see ATTENTION 1). Deployed live on deploy tree `e8524c31` (`ignite/core-daemon`).

## ATTENTION
1. **This shipped behaviour was deliberately left UNPINNED at commit time.** The seat that built it
   wrote a pinning patch (`RS-4b`, two checks: additive-with-file, absence-without-file) but refused to
   commit it because `coord_selftest.py` carried ~300 lines of a sibling seat's unrelated,
   uncommitted, in-progress work at the time — committing the file would have published that work
   under this seat's message. Before assuming this report is regression-protected, check whether
   `coord_selftest.py` now contains the RS-4b arms (search for `RS-4b` / the additive-with-file /
   absence-without-file check names) — if absent, nothing currently fails if a future change removes
   the `daemon-skip` field or stops writing `lane-skips.json`, and this task-121 visibility fix can
   silently regress with no test catching it.
2. `daemon_lane_skips` must stay read-only and fail-soft (`{}` on any error) — `ready-seats` is used
   against fixtures and stale snapshots with no live daemon, and this field must never turn a clean
   `ready-seats` read into a raised exception.
3. `daemon-skip` is explicitly NOT a verdict term — `dag-10 RS-4` governs `verdict`/`built` and must
   stay untouched by this field; do not let a future change start gating `verdict` on `daemon-skip`,
   which would reopen the exact regression the sibling seat's reverted attempt hit.
- shipped UNPINNED; RS-4b patch at seats/freeze-scope/rs4b-full.patch
