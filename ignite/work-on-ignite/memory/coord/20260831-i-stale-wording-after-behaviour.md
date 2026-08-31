# 20260831-i-stale-wording-after-behaviour — Stale wording after behaviour moved (5 sites, comment-only)

kind: issue
component: coord
date: 2026-08-31
commit: 94f35812
deployed: no
pin: NONE
components: runtime,supervisor

## Observed

Four files carried comments/operator-facing strings asserting the OPPOSITE of shipped
behaviour, collected in `1-projects/build-ignite/build/redesign-continue-1/loose-ends.md`
("Comments and operator-facing strings...", `#d/easy`): `ignite/runtime/ticker/one-live-run.js`
(moved from the seed's cited `runtime/lease/`) said "ancestry-verified" after `lease.js`
(944782cc) widened the occupant set to include paneless daemon-lane seats; `ignite/coord/records.py`
still documented the deleted `RECORD_DISPOSITION_WRITER` enum and `exited` as a live,
kit-writable value; `ignite/supervisor/launch.py` carried a capacity-census comment claiming
`state.json`/team-monitor as the live source, three lines above a ruling (`d-capacity-registry-liveness`)
in the SAME file saying the opposite; `ignite/coord/budget.py` (docstring, `STALE_AFTER_S` comment,
and the `render()` "Restart team-monitor" operator string) all named team-monitor as the live sensor —
deleted 2026-08-24 [T4-R8, del-observers] with no replacement.

## Mechanism

Each site's underlying behaviour was changed by a separate commit (944782cc for the lease occupant
set, T4-R8/del-observers for team-monitor's deletion, T1-R3/T4-R7 for `exited`'s retirement) and the
prose beside the changed code was never revisited in the same change. `ignite/supervisor/spawn/spawn.js`
turned out to be a false positive: commit 33631543 (same day, later) deleted the dead
`resolveBusWriteGrants` function and its detailed pane-ancestry-only comment block as part of an
unrelated dead-code removal — coincidentally fixing the staleness this task was seeded to find.

## Attempts

First attempt held — checked: `d802079d` (protocol-rerun-door) had already fixed the launch.py D42
`exited` block named in the seed; this entry's launch.py fix is a DIFFERENT stale paragraph in the
same file (the capacity-census single-read rationale), found by re-grepping `team-monitor` in
launch.py rather than assumed from the seed's summary.

## Fix

Corrected each stale claim in place, keeping the surrounding historical/design prose intact:
one-live-run.js's reason string now says "verified occupant" instead of "ancestry-verified";
records.py gained a banner at the top of the retired dag-08 block naming the ending store as the
live replacement (`who_stamped`/`ENDING_VOICE_SEAT`/`ENDING_VOICE_SYSTEM`) without rewriting the
~115-line historical body; launch.py's stale single-read justification was corrected to cite the
surviving reason (double-counting panes THIS act just opened) instead of the dead team-monitor-lag
reason; budget.py's docstring/comment/operator string were reworded to say `state.json` is now
PERMANENTLY absent (not occasionally stale) since team-monitor has no replacement writer.
Comment/docstring/string-literal text only — no logic changed anywhere.

## Consequences

None structural. spawn.js needed no edit (already fixed). No other `exited`/`team-monitor`
occurrences in these five files were left uncorrected after grep — the ones NOT touched (e.g.
records.py:2062, launch.py:2566, spawn.js:645's subprocess-exit-code use) were verified to already
state the current, correct fact and were left as-is.

## Verification

`python3 -m py_compile` on records.py/budget.py/launch.py; `node --check` on one-live-run.js;
`budget.py --selftest` (16 + 12 checks OK); `probe-one-live-run.js` exits 0. Not deployed this
session (comment-only, no deploy authorized under this plan's rules).

## ATTENTION

- The seed task's file paths were pre-refactor: `ignite/runtime/lease/one-live-run.js` no longer
  exists — the file is `ignite/runtime/ticker/one-live-run.js`. Re-locate by content/grep, not by
  the path a task or loose-end entry cites.
- `ignite/coord/records.py`'s dag-08/dag-09 block (`RECORD_DISPOSITION_WRITER`,
  `awaiting-close.json`) is ENTIRELY retired design history now, not just the `exited` line — the
  whole ~115-line paragraph describes a deleted mechanism. Do not extend or "fix" values in that
  enum; the live vocabulary is the ending store's (`state-store/vocabulary.js`).
