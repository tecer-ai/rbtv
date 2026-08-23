# 20260821-i-d48-probe-fix-batch — D48 probe fix batch

kind: issue
component: engine
date: 2026-08-21
commit: 0c505934,f00aba41,bb13d3a9,4d47c796,d27c44f4,3303c80e
deployed: yes
pin: self-pinning, all scheduled
components: team-kit,server,deploy
seeded: true

## Seen
Six probes were red after wave-2 audit; D48 approved fixing all six as one batch.

Six independent probes were red after the redesign-plan's wave-2 audit: `probe-store-ready-suppression.py` pointed at a stale tasks store; `probe-enqueue-record.js` Arm E migrated from the wrong baseline (LATEST-1 instead of pre-v6); `dispatch.js` still carried a stale NOT_WIRE_REACHABLE row (E_CAGE_GROUND_TRUTH); `probe-suite.js` could quote a prior run's stale `.out` when a probe wrote no fresh capture; `probe-daemon-lane-watch.js`'s mutation copies were unbounded and could hang at arms L8/L9.

## Missed
none recorded in sources — D48 approved fixing all six as one batch.

## Held
Fix each probe/file at its own root cause; daemon-lane-watch needed two same-day follow-ups.

Each fixed at its own root cause: `0c505934` repoints the store probe at the live tasks store; `f00aba41` fixes the migration baseline; `bb13d3a9` drops the stale dispatch row; `4d47c796` stops probe-suite quoting stale captures; `d27c44f4` bounds daemon-lane-watch's mutation copies and flushes `.out` live; `3303c80e` (same day) stops the same probe hanging at L8/L9.

## commit
0c505934,f00aba41,bb13d3a9,4d47c796,d27c44f4,3303c80e

## files
ignite/team-kit/probes/probe-store-ready-suppression.py; ignite/engine/probes/probe-enqueue-record.js; ignite/server/internal-api/dispatch.js; ignite/deploy/probe-suite.js; ignite/engine/probes/probe-daemon-lane-watch.js

## deployed
yes

## pin
self-pinning, all scheduled

## ATTENTION
- probe-daemon-lane-watch.js needed TWO follow-up commits the same day — its mutation-copy/hang behavior is fragile; test under load (many arms), not just a quick single-arm run, before trusting a green result.
- probe-suite.js's stale-.out bug means a probe that silently produces no fresh capture could previously masquerade as passing on old output — if a probe run looks suspiciously identical to the last one, verify this fix is still in place.
- probe-daemon-lane-watch.js needed two same-day follow-ups; test under load, not one arm
- probe-suite.js's stale-.out bug could have masqueraded a no-capture probe as passing
