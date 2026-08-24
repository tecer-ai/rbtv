# 20260824-i-readiness-fixture-wrote-the-re — Readiness fixture wrote the retired ending surface

kind: issue
component: team-kit
date: 2026-08-24
commit: 60358b9a
deployed: no
pin: team-kit/probes/probe-coord-selftest-notmux.py

## Observed
`coord.py selftest` reported 53 failures and then ABORTED at check 644 with `TypeError: 'NoneType' object is not subscriptable`. An abort is worse than the failures it hides: every row after it never ran, and an unrun row is indistinguishable from a passing one in the exit code — G-121 inside the suite written to catch G-121. Both `team-kit/probes/probe-coord-selftest-notmux.py` and `-tmuxpane.py` were red on it.

## Mechanism
Two surfaces moved out from under the fixture, and both times the suite kept reading the old one.

`_rs_make` — the shared readiness-fixture builder every `dag-10 RS-*` row rests on — wrote the seat's disposition to `sessions.csv` and nowhere else. `ready.py#terminal_disposition` no longer reads that file: it asks `ending_store.get_current_ending`, the ONE ending store. So every readiness row was handed a package carrying NO ending at all and read absence where it had set up a disposition.

The abort had the same root one layer along. `ready.py`'s renew gate keys on a raw `renew` disposition, and the ending store's vocabulary is `done|incomplete|failed` (`state-store/vocabulary.js` `ENDINGS`), so `rec["renewal"]` is `None` on every row. The RG rows indexed `None["state"]` inside a `check(...)` ARGUMENT — evaluated before the harness could convert it to a verdict, so it escaped `harness_outcome`'s protection entirely.

## Attempts
First attempt held — checked: the doors seat's handover diagnosis (three named causes: the shared fixture, the deleted awaiting/set_awaiting/exited enums, the `--rerun`/`--declare-only`/E22 door rows), `git log` on `coord_selftest.py` and `ready.py`, `state-store/vocabulary.js` `ENDINGS`, and memory `20260822-c-admission-brake-door`. No earlier fix of this abort is recorded anywhere in the memory tree.

## Fix
`_rs_make` now also calls `seed_ending(p, seat, disposition=d)` for each session row. That helper already existed at the head of the same file and already holds the ONE mapping from a legacy disposition word to a stored ending — `renew`/`incomplete` to `incomplete`, `exited`/`unverified` to `failed` with a reason class, everything else to `done`. Calling it rather than re-spelling the mapping is deliberate: a second copy of that table is the two-computers shape the redesign is removing everywhere else.

The three `["renewal"]["state"]` reads became `(… or {}).get("state")`. The claims are untouched and the rows stay RED; what changed is that they fail as verdicts instead of killing the run.

## Verification
`dag-10 RS-2`, `RS-3`, `RS-4`, `RS-6` and `RS-7` go green on the fixture change alone. The abort moved from check 644 to check 758, so 114 further rows are now measured rather than unknown — and that exposed the NEXT abort in the chain (`KeyError: 'oc2'` at the `load_awaiting` row), which is the retired `awaiting-close.json` surface and is recorded as open work, not fixed here. Failure count went 53 to 70 because more of the suite runs; that is the honest direction.

## Consequences
The residual reds are not fixture bugs. They are rows asserting a vocabulary another change deleted — `renew`, `revive`, `exited`, `unverified` as record dispositions, `set_awaiting`/`load_awaiting`/`awaiting-close.json` as the live ending surface, and the `exited` from-state the `--rerun`/`--declare-only`/E22 door rows are written against. Retargeting them is a ruling on the new state vocabulary and belongs with spec-state-store, not with a fixture repair.

## ATTENTION
- A raising expression inside a `check(...)` ARGUMENT is evaluated before `check` runs, so `harness_outcome`'s termination-to-verdict conversion cannot protect it. Any read of a field that a vocabulary change can turn `None` must be null-safe at the call site.
- `_rs_make` writing `sessions.csv` is NOT the durable ending any more. A new readiness fixture that sets a disposition must seed the ending store, and must do it through `seed_ending` rather than a second mapping.
- `ready.py`'s renew gate is unreachable, not merely untested: `terminal_disposition` can no longer return `renew`, so `RENEWING`/`RENEW-BLOCKED` cannot be produced by any input.
