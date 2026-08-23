# 20260822-i-ro-mask-private-scope-fix — Ro mask private scope fix

kind: issue
component: server
date: 2026-08-22
commit: 6b55b1c4
deployed: yes
pin: NONE
seeded: true

## Seen
The private-scope visible() predicate didn't excuse read-only mask covers.

`private-scope.js`'s `visible()` predicate did not account for read-only mask covers on cage mounts; a daemon-fired leader spawn using a read-only mount would die because the predicate treated the ro-masked path as invisible/inaccessible rather than excusing the cover (#576, also referenced by the system-problems digest §4 as a repeated launch-death cause: "a read-only-filesystem mkdir failure on a different path after the first fix landed").

## Missed
none recorded in sources for this exact bug beyond the recurring #576 pattern.

The system-problems digest names a sibling defect in the same cage/fence family (#665 cage-cgroup) as "closed, then re-opened as closed on stale proof" — the same PATTERN of a cage fix appearing closed and recurring, though that is a different defect than this one.

## Held
Excuse ro-mask covers in the visible() predicate explicitly.

`cage.js` and `private-scope.js`'s `visible()` predicate now excuses ro-mask covers explicitly; `probe-private-scope.js` extended (33 lines) to cover the case.

## commit
6b55b1c4

## files
ignite/server/spawn/cage.js; ignite/server/spawn/private-scope.js; ignite/server/spawn/probes/probe-private-scope.js

## deployed
yes

## pin
NONE

## ATTENTION
- This is the SECOND launch-death cause found on the same fence/cage lineage (first was the D3 fence's own EROFS class) — per system-problems digest, "same launcher, two failure modes across time." Treat any NEW read-only-mount failure on this launcher as a plausible third instance of the same family, not necessarily a fresh root cause.
- No pin (NONE) beyond the extended probe-private-scope.js — if #576 recurs, that's the first place to check, but there is no standing scheduled regression guard beyond it.
- second launch-death cause on the same fence lineage; treat any new ro-mount failure as plausibly the same family
- no scheduled regression guard beyond the extended probe-private-scope.js
