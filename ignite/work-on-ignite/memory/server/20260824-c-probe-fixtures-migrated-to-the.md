# 20260824-c-probe-fixtures-migrated-to-the — probe fixtures migrated to the envelope model

kind: change
component: server
date: 2026-08-24
commit: ea10c914,bddb247d,1fa6e8dc,5f3c5871
deployed: no
pin: ignite/server/spawn/probes/probe-envelope-walls.js
components: bridges,capabilities

## Motivation
The envelope redesign changed what a launch demands of a workspace, and ten probe fixtures across `server/spawn`, `server/ticker`, `bridges/chat` and `capabilities` still modelled the retired per-seat grant world. Two shapes broke: a fixture workspace with no `.rbtv/mirror` (family 6 ro-binds it and the compiler refuses a baked path that does not resolve), and a fixture workspace rooted under `/tmp` (families 4 and 7 bake `/tmp` and `{tmpdir}` RW for every seat, so the workspace is RW and RO at once). One probe leg also asserted a mount the envelope no longer emits.

## Design
`server/spawn/probes/lib.js#fixtureRoot(prefix)` is the single fixture-root maker and it roots at `/var/tmp`, which is in no baked family — the ticker and chat fixtures call it rather than each hardcoding a path. Every fixture that composes a cage also mkdirs `{workspace}/.rbtv/mirror/x`. `probe-seat-launch-gate` leg P9-launch asserted `--tmpfs {goalDir}/seats` (the retired template's peer-seat mask) and now asserts `--ro-bind {goalDir}/seats`, which is what a daemon-owned directory carve emits. `probe-envelope-walls` leg 4 moved off `{goal}/scratch` (the daemon creates it now) onto the mirror path, and gained leg 6 for the materialization. Rejected: teaching `cage.js#lastCovering` the compiler's carve rules — that predicate is launch custody, and no real workspace sits inside the scratch family, so the fixture is where the wrong shape is.

## How it works
`fixtureRoot` mkdirs `/var/tmp` and `mkdtempSync`es under it. `probe-job-seat-launch`'s launch spec pinned `workdir_root: '/tmp'` and follows its fixture to `/var/tmp`, or the ticker refuses the seat home as outside the profile root.

## Consequences
`server/spawn` went 20/32 to 30/32, `server/ticker` 13/27 to 27/27, `bridges/chat` 21/22 to 22/22. Any NEW probe that composes a cage must use `fixtureRoot` and seed a mirror; a fixture that quietly goes back to `os.tmpdir()` will refuse with `conflict rw:/tmp vs ro:<ws>` and read as a launch defect.

## Verification
`node ignite/deploy/probe-suite.js --dir server/ticker/probes` — 27/27, `SUITE-COMPLETE verdict=GREEN exit=0`. `--dir bridges/chat/probes` — 22/22 GREEN. `--dir server/spawn/probes` — 30/32; the two residuals are `probe-tmux-seat-live` and `probe-trace-header` on the tmux argv ceiling, which is `cage.js` custody. Deployed no.

## ATTENTION
- A cage-composing fixture workspace must never live under `/tmp` or `os.tmpdir()` — families 4 and 7 bake both RW and the launch refuses mixed access at the workspace root.
- A fixture workspace needs `.rbtv/mirror` or the compiler refuses `unresolved <ws>/.rbtv/mirror` before anything under test runs.
- Peer seat folders are RO-bound now, not tmpfs-masked; a probe asserting the tmpfs is testing deleted behavior.
