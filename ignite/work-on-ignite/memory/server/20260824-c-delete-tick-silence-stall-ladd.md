# 20260824-c-delete-tick-silence-stall-ladd — delete tick-silence stall ladder [T4-R1]

kind: change
component: server
date: 2026-08-24
commit: c72ba544
deployed: no
pin: NONE
components: capabilities,engine

## Motivation
Design-baseline v2 [T4-R1, CF-2] settles no-progress detection on work-product
(`last_progress_at`, built by a later seat), never on ticks of silence. `server/ticker/ticker.js`'s
per-execution "stall ladder" (`stall_warn_ticks`/`stall_halt_ticks`/`stall_kill_ticks`, and the
hung-kill rung riding on top of it) measured exactly that — silence of log growth / chat messages
— and is superseded. This is the second of the four D19 observer deletions this seat
(del-observers) performs; see also [[20260824-c-delete-goal-stall-alarm-module]].

## Design
Delete the three tick knobs from `ticker.js` DEFAULT_CONFIG and the entire silenceTicks
warn/halt/hung-kill loop inside `enforce()` (per-session `lastActivityTick`/`lastLogSize`/
`lastCpuNsec` tracking, `lastEnforceSessions()`, `getLogSize()`, `hasMessagesSinceStart()` — all
dead once their only caller, the ladder, is gone). Crash-sweep (dead-process detection via
`spawnManager.status().live`) and the row-less-unit scan are untouched — they are a different
mechanism (a process fact, not a silence measurement) that happened to sit in the same function.
`enforce()` keeps exactly one unconditional closing action, `{ phase: 'enforce', action: 'state' }`
with no payload — this is NOT part of the ladder; it is the proof a caller needs that `enforce()`
ran to completion this tick rather than aborting partway (crash-sweep and the rowless-unit scan
both only push actions when they find something, so without an unconditional marker a healthy
"nothing happened" tick is indistinguishable from an abandoned one — `probe-argv-template.js`'s
S2e already asserted exactly this literal string before this change and still does).

Knobs removed from `server/internal-api/dispatch.js`'s two `inspect ticker` config echoes, and
from `capabilities/ticker-settings/`'s `set-interval` cadence-preview (`rbtv-ignite-ticker`'s
`ladderAt`/`printLadder`, which used to print all four tick-denominated durations and now prints
only the one real one left, `warnings.js`'s standing-warning re-announce).

## How it works
Nothing sets execution status to `stalled` any more. Existing consumers of that status value
(crash-sweep's `listExecutionsByStatus('stalled')` concat, dispatch's owner-halted exclusion,
doc mentions) are untouched and remain correct for any pre-existing `stalled` row or one a future
mechanism writes — `stalled` as a STATUS VALUE is not deleted, only its one producer is.

## Consequences
Two probes existed only to assert the deleted rungs and are deleted outright:
`server/ticker/probes/probe-hung-kill.js` (the kill rung) and `probe-stall.js` (warn/halt).
`probe-stalled-crash-sweep.js` survives — it proves crash-sweep still sweeps a `stalled` row — but
its setup now writes `heartStore.updateExecutionStatus(execId, { status: 'stalled' })` directly
instead of riding 30 ticks of the (now-deleted) ladder to reach that state.
`engine/probes/probe-engine-library.js` dropped its `stall_warn_ticks`/`stall_halt_ticks` regex
assertion (kept the rest of that check: ticks are still recorded by the attached lane's real
ticker, proving it is not a stub). `server/ticker/probes/probe-seat-queue.js`,
`probes/lib.js`, `probe-reserved-interactive-slot.js` and `probe-warning-lifecycle.js` had
now-inert `stall_*_ticks` keys removed from their fixture `config` objects (ticker.js silently
ignored them once DEFAULT_CONFIG dropped the keys — harmless but misleading test setup).
`capabilities/ticker-settings/probes/probe-ticker-settings.js`'s ladder-preview assertion was
retargeted from `stall halt @24 ticks x 15s = 360s` to `standing-warning re-announce @6 ticks x
15s = 90s`, the one row that remains.

## Verification
`node --check` on every touched .js file. Full `server/ticker/probes/*.js` sweep (28 probes,
excluding lib.js) — all green after the fix. `engine/probes/*.js`,
`capabilities/ticker-settings/probes/*.js` (incl. selftest.js), `cli/probes/probe-cli-ticker.js` —
all green. Deployed: no (worktree only, `5-workbench/rbtv-redesign`, branch ignite/core-redesign;
live repo untouched).

## ATTENTION
1. `enforce()`'s unconditional `{ phase: 'enforce', action: 'state' }` action carries NO payload
   any more — a reader that used to pull `sessions` off it (nothing in this tree did, verified by
   grep) would get `undefined`, not an empty object.
2. `stalled` is still a live, reachable execution status — only its ONE producer (the ladder) is
   gone. Do not read "stall ladder deleted" as "the `stalled` status is gone"; crash-sweep,
   dispatch's owner-halted exclusion, and every doc mention of `stalled` as a state are unchanged
   and still correct.
3. A future supervisor-registry/last_progress_at mechanism (impl-supervisor/impl-recovery,
   explicitly out of this seat's scope) is the intended replacement for "is it alive" and
   "is it stuck" — nothing here builds it. `capabilities/ticker-settings/`'s `ladderAt` is now a
   single-row array; a future emitter adding new tick-denominated config back onto this surface
   should extend that array, not resurrect the deleted three-knob shape.
