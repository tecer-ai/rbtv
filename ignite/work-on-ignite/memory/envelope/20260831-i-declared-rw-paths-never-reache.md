# 20260831-i-declared-rw-paths-never-reache — declared rw-paths never reached the composed cage

kind: issue
component: envelope
date: 2026-08-31
commit: d6b59389
deployed: no
pin: ignite/supervisor/spawn/probes/probe-envelope-walls.js
components: supervisor
register-id: G-plan-designer-0828-1822

## Observed
On `ignite-engine-planning` and in stools filing `G-plan-designer-0828-1822` (2026-08-28), a seat's `rw-paths:` changed the pre-enqueue admission verdict but never reached the composed bind list. Redesign-continue-1 seed task 163 restated it as the `rbtv-and-mirror` carve hole plus this inert grant. Reproduced 2026-08-31 on HEAD before this commit, against a throwaway fixture under `/var/tmp` (not a live build seat): `resolveRwPathGrants` returned the declared mirror path, `admitLaunch` without `extraPaths` spawned with `grantBind=null`, and a real `bwrap` write failed `Read-only file system` both through that bind list and through `composeCageFor` (`COMPOSE_HAS_RW_BIND false`). Deployed daemon copy was not touched.

## Mechanism
The live cage is the envelope compiler's bind list. `composeCageFor` called `admitLaunch` with workspace/goal/seatDir and no `extraPaths`. `consumeLaunch` took `extraPaths` only from `{goal}/envelope.json`; a fixture or planning goal with no fill ran `compilePlanning`, which forced `extraPaths: []`. Admission still drove the legacy `composeSeatCage` template (`bind:{grant:rwPath}`), so the declaration passed the gate and bought no bind. Family `rbtv-and-mirror` no longer exists: the 2026-08-30 split (`fix-mirror-family-split`, `c962f09f`) left `mirror` with an rw carve and `rbtv-repo` with none — that compile-time hole was already closed; the remaining defect was that seat-declared grants never entered `compile()` at all.

## Attempts
First attempt held — checked: `G-plan-designer-0828-1822` (call-graph confirmed 2026-08-28, no live cage probe, left open); `c9615ca2` (envelope launch replaced the 14-source grant array with `admitLaunch` and stopped calling `resolveRwPathGrants` from compose); `c962f09f` / `20260830-i-family-6-admitted-no-plan-writ` (split family 6 so a plan rw path under `{mirror}` compiles, and explicitly refused to carve `rbtv-repo` — a different hole). None of those threaded seat `rw-paths` into compile `extraPaths`.

## Fix
`composeCageFor` now resolves `rw-paths` through the same `resolveRwPathGrants` admission already used, and passes them as `extraPaths` into `admitLaunch`. `consumeLaunch` merges those with envelope.json extraPaths. `compilePlanning` still zeros plan fill-ins (`namedRepos` / `projectFolder` / `credentialNames`) but keeps `extraPaths`, because a seat grant is not a plan fill-in. After admit, a declared grant missing from the rw bind list is `E_LAUNCH_REFUSED` (`declared grant was not composed`) rather than a silent read-only launch. Rejected: adding an `rbtv-repo` carve (the 2026-08-30 split forbade it; E20/E25 stay blocked). Rejected: filling the legacy `SeatBinds` `{grant:rwPath}` slot — `composeCageFor` does not use that template. Rejected: skipping `exposedCliConflict` when extraPaths land as binds — task 122's same-directory collision must still refuse.

## Consequences
Planning/fixture goals without `envelope.json` can now compose a declared workspace/mirror rw path. A declared path inside the rbtv SOURCE repo still compiles `kind:conflict` (no carve). `resolveCliWriteRootGrants` and `resolveGoalWriteGrants` remain defined and uncalled — tasks 162 and 155. Admission still judges via `composeSeatCage`, so a grant the compiler would conflict can still look admissible at enqueue; compose is now the loud refuse. Archive filing `G-plan-designer-0828-1822` is the matching open register row (not closed here).

## Verification
Red-first fixture: before, `bwrap` write to `.rbtv/mirror/x` → `Read-only file system` / `onDisk=ABSENT`; after `d6b59389`, `composeCageFor` has the `--bind`, write exit 0, `onDisk=RED-WRITE`. `node ignite/envelope/envelope-compiler.selftest.js` — `extraPaths-rw-under-mirror`, `extraPaths-rw-under-rbtv-repo-refuses`, `compilePlanning-keeps-seat-extraPaths`. `envelope-launch.selftest.js` — `seat-extraPaths-composed`. `probe-envelope-walls.js` legs 11–13: caged write lands `GRANTED`; rbtv-repo extraPath refuses `kind:conflict`; rw-paths + `exposedCliCode` on the same directory still refuses `kind:conflict`. Not deployed.

## ATTENTION
1. `composeCageFor` must keep passing seat `extraPaths` into `admitLaunch` — admission's `composeSeatCage` `{grant:rwPath}` slot is not the live cage, and dropping the pass recreates a declaration that admits and buys no bind.
2. `compilePlanning` zeros plan fill-ins on purpose; wiping `extraPaths` there again makes every no-envelope.json goal (fixtures, planning) silently read-only on declared `rw-paths`.
3. `authorizedCarve` still has no `rbtv-repo` clause (`fix-mirror-family-split`, 2026-08-30) — a write path inside the rbtv SOURCE repo must refuse; do not add that carve to make E20/E25 executable.
4. After extraPaths land as binds, `exposedCliConflict` still runs over `admitted.binds`; skipping it to "let the grant through" is the task-122 later-wins collision this sitting was forbidden to allow.
5. `family`/`origin` must keep riding into `exposedCliConflict` from `admitted.binds` — trimmed as decoration, `authorizedCarve` authorizes nothing and every exposed-CLI seat false-refuses again.
- composeCageFor must keep passing seat extraPaths into admitLaunch — admission's composeSeatCage {grant:rwPath} slot is not the live cage, and dropping the pass recreates a declaration that admits and buys no bind.
- compilePlanning zeros plan fill-ins on purpose; wiping extraPaths there again makes every no-envelope.json goal (fixtures, planning) silently read-only on declared rw-paths.
- authorizedCarve still has no rbtv-repo clause (fix-mirror-family-split, 2026-08-30) — a write path inside the rbtv SOURCE repo must refuse; do not add that carve to make E20/E25 executable.
- After extraPaths land as binds, exposedCliConflict still runs over admitted.binds; skipping it to let the grant through is the task-122 later-wins collision this sitting was forbidden to allow.
- family/origin must keep riding into exposedCliConflict from admitted.binds — trimmed as decoration, authorizedCarve authorizes nothing and every exposed-CLI seat false-refuses again.
