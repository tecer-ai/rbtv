# 20260830-i-stale-done-from-an-earlier-sit — stale done from an earlier sitting swallows a 429 death

kind: issue
component: supervisor
date: 2026-08-30
commit: fa89fa75
deployed: no
pin: ignite/supervisor/death-stamp.selftest.js

## Observed
`stools-canvas-audio-elevenlabs-close` (goal), 2026-08-28: leader sitting 9 checked out `done` at
22:10:11 (`seat_endings` row, `who_stamped=seat`). Leader sitting 10 (session `b6731ba8…`, launched
22:17:39Z by the unread-mail driver over message #45) died 39 s later on an Anthropic HTTP 429
session-limit before it could run `coordinate finish-goal`. The daemon journal at 22:18:20 logged
`supervisor death stamp: confirm-and-reap — the seat's own \`done\` stands · reaped` and
`staff mail: NOT minted — the seat declared \`done\`; the reap is not a failure`. No `failed` ending
was ever stamped, no strike, no recovery relaunch entered, and the goal stayed frozen 40 h with no
`goal_states` row and an empty `state.csv`. Deployed HEAD at incident time: `5771be33`; repo HEAD at
diagnosis: `442c506e` — `ignite/supervisor/death-stamp.js` unchanged between the two.

## Mechanism
`death-stamp.js#stampDeath` reads `store.getCurrentEnding({ goal, seat })` — keyed `(goal, seat)`,
never `(goal, seat, session)`, because `seat_endings`'s own schema carries no session column for a
`done`/`incomplete` row (`stamp_seat_declare`, coord/checkout.py, writes an `evidence_pointer` that
is a declared-output path or the literal `checkout:<seat>`, never a session id). The guard treats
`declared === 'done' || declared === 'incomplete'` as "the seat already spoke" and returns
`confirm-and-reap`/`declared-ending-stands` BEFORE the `providerShaped(...)` classification below it
ever runs. Sitting 10 died while the store still held sitting 9's `done` from 22:10:11; the guard
read that stale row and declared the death normal. `PROVIDER_MARKERS` already contains `'rate_limit'`
and `'http 429'`, so the 429 WOULD have classified `failed: provider-error` and entered the recovery
ladder — it was unreachable, not unhandled. The file's own contract table ("a `done` checkout is
confirm-and-reaped for EVERY seat") is per-SITTING; the storage lookup is per-SEAT.

## Attempts
First attempt held — checked `20260824-c-supervisor-death-stamp` (the death-stamp path's own
creation entry, which designed the table this bug lives inside) and the diagnosis at
`1-projects/build-ignite/build/role-action-program/seats/diag-stools-close-unfired/report.md`
(orchestrator-verified, 2026-08-30, which named this exact cause and recommended the fix taken
here as "Option 1").

## Fix
`declaredEndingIsStale(current, evidence)`: a declared `done`/`incomplete` stands only when it could
be THIS sitting's own. `seat_endings` carries no session to compare directly, so `sessions.csv` is
the fallback source of the dying sitting's identity — `evidence.session` (the id its own closer
already passes: `close_session_seat` in coord/attest.py, unedited) names the row, and that row's
`started` column is trusted as when the sitting began. A declared ending `stamped_at` BEFORE that
start cannot be this sitting's own and falls through to the existing crash/provider table.
`sessions.csv`'s location is resolved via `RBTV_IGNITE_WORKSPACE_ROOT` (the daemon's own systemd
unit sets it; every closer the daemon spawns inherits it down the execFileSync/subprocess.run
chain — the same variable `runtime/index.js` already reads). Any missing piece (no session in
evidence — the tmux-lane closer passes none today, no workspace root, no readable sessions.csv, no
matching row) falls back to today's behaviour (the declaration stands) rather than guessing:
a fallback comparison must fire only on real evidence.

Rejected: adding a session column to `seat_endings` (touches the ending store's schema and every
door that reads it, for a fact only this one guard needs); comparing wall-clock "now" against
`stamped_at` with a fixed staleness window (a guess with no principled bound, unlike "before this
sitting existed").

Reaching the classification table for a seat that already carries a `done`/`incomplete` row also
needed `stampSystem({ ..., replace: true })` on the ROWS 3-5 write: the ending store's write-once
guard (`writeEnding`, spec-state-store §1) throws `E_WRITE_ONCE` on any write over an existing row
unless the caller says `replace: true`. `replace: true` is a no-op when no row exists yet (ROWS
3-5's ordinary case) and is required the one case it is not.

## Consequences
None outside `death-stamp.js`: `confirmAndReap`, `buildEvidence`, `providerShaped` and the
ROWS-3-5 classification are unchanged in shape, only reached for one more case now. No caller
signature changed — `stampDeath(evidence, deps)` is unchanged; the fix reads a field already
present in production evidence for the daemon lane (`evidence.session`) and a workspace env var
already set on the daemon's unit.

## Verification
`node death-stamp.selftest.js` — 11 arms, `ALL PASS`: a direct unit check on
`declaredEndingIsStale` (before-start is stale, after-start stands, no-session stands); the live
incident reproduced offline (a `done` stamped before the dying sitting's own `started` → the same
429-shaped death now stamps `failed:provider-error`, not `confirm-and-reap`); the original case
(the SAME sitting's own `done`, sessions.csv `started` before its `stamped_at`) still
`confirm-and-reap`s; one RED mutation (revert `declaredEndingIsStale` to always `false`) reproduces
the incident (`confirm-and-reap`, `stamped: false`) proving the fix is load-bearing. Full
`ignite/supervisor/*.selftest.js` sweep and `probe-daemon-lane-watch.js` unchanged before/after
(82 ok/1 pre-existing FAIL both times; `reconcile.selftest.js` still aborts at its pre-existing
`:392` red, same PASS count 6 before and after). NOT deployed at filing; commit `fa89fa75` on
`ignite/core-daemon`. No `.rbtv/` planted under the repo root.

## ATTENTION
1. `evidence.session` is populated ONLY by the daemon-lane closer (`close_session_seat`,
   coord/attest.py) today — the tmux-lane closer (`attest_exit_seat`) never passes one, so this
   fix is currently inert for tmux-lane deaths. It fails safe (declaration stands, today's
   behaviour) rather than guessing, but a stale-`done` swallow on the tmux lane is NOT closed by
   this change.
2. The comparison trusts `RBTV_IGNITE_WORKSPACE_ROOT` being set and correctly inherited down every
   closer's subprocess chain (execFileSync → python subprocess.run → node). It is set on the
   daemon's own systemd unit today; a caller that clears its environment before shelling out to
   `supervisor/cli.js` silently loses this fix (falls back to "declaration stands", not a crash).
3. `stampSystem`'s new `replace: true` on the ROWS 3-5 write means ANY seat reaching that branch
   now overwrites an existing ending row rather than refusing — verified harmless today because
   ROWS 3-5 was previously reachable only when `current` was already null, but a future edit that
   widens what reaches ROWS 3-5 inherits this permissive write silently.
- evidence.session is only populated by the daemon-lane closer today; tmux-lane stale-done swallow is NOT closed
