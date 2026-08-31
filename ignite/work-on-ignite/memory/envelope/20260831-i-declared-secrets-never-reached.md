# 20260831-i-declared-secrets-never-reached — declared secrets never reached cages

kind: issue
component: envelope
date: 2026-08-31
commit: 071687e7
deployed: no
pin: ignite/envelope/probes/probe-credential-injection.js
components: planning
register-id: G-plan-designer-0828-1815

## Observed
On 2026-08-28 the stools-canvas-audio-elevenlabs-planning plan-designer filed `G-plan-designer-0828-1815`: every live goal compiled `credentialNames: []`, so no secret reached any caged seat. First blocked consumer was `ELEVENLABS_API_KEY`. Reproduced 2026-08-31 on HEAD before `071687e7` against a throwaway `/tmp` then `/var/tmp` fixture (not a live goal): `admitLaunch` with no `envelope.json` returned `credentialNames: []`; a caged `python3 -c` print of `ELEVENLABS_API_KEY` was `ABSENT` even with that name present in the fixture store; `admitLaunch` with `credentialNames: ['NO_SUCH_FIXTURE_KEY']` still returned `spawn: true` while `resolveCredentials` itself returned `{ok:false}`. Deployed daemon copy was not touched.

## Mechanism
The injection channel (`injectDeclaredEnv` → bwrap `--setenv` in `composeCageFor`) was already built. Two producers of the empty list sat upstream. `loadFillIns` is the sole reader of `{goal}/envelope.json`; absent that file, `consumeLaunch` falls to `compilePlanning`, which hardcodes `credentialNames: []`. Path-B birth (`path_b.py#_land_envelope`, `7d8cb4a2`) copies the file from the bound commit when present, but nothing in planning authored it, so the birth copied nothing. Separately, `resolveCredentials` had no production caller — only its definition, export, and `envelope-launch.selftest.js` — so a declared-but-missing store key skipped `injectDeclaredEnv` and spawned unset.

## Attempts
First attempt held — checked: `20260824-c-envelope-launch-refuse-and-inj` (built `resolveCredentials` and documented an approval-time check that nothing ran); `20260824-c-delete-credential-pierce-role` (T2-R11/D19, credentials are env-injected, never caged — `private-scope.js` still refuses credential pierces); `20260831-i-path-b-birth-writes-its-own-en` (`7d8cb4a2`, the birth consumer of a bound `envelope.json`, explicitly not the planning producer); `20260831-i-declared-rw-paths-never-reache` (`d6b59389`, the sibling 1822 rw-paths compose hole, not credential names). None of those authored `credentialNames` into plan artifacts or called `resolveCredentials` at launch.

## Fix
`admitLaunch` now calls `resolveCredentials` against `loadCentralStore(workspaceRoot)` after a successful compile and own-seat punch. A missing or empty declared name returns `{spawn:false, refuse:{kind:'missing-credential'}}`; `composeCageFor` already throws `LaunchRefused` on that shape, so `spawn.js` was not edited (shared with in-flight seats). Planning gained `plan_envelope.py` as the producer of `<plan-artifacts>/envelope.json` — a planning seat writes it before the bound commit is taken; `_land_envelope` remains the mint consumer. Rejected: deleting the dormant path and documenting "no secret reaches a cage" (owner needs ELEVENLABS in the cage). Rejected: a new `approve_package.py` `credentialNames` field (would be a second source next to the bound artifact birth-envelope already consumes). Rejected: credential file binds / editing `private-scope.js` (T2-R11/D19). Rejected: a prose parser over `draft-plan.md`.

## Consequences
`compilePlanning` still zeros plan fill-ins, including `credentialNames` — a goal with no `envelope.json` still launches with no secrets, which is the no-declaration case. Already-live goals are not retroactively filled; they need a bound `envelope.json` and a re-birth, or a hand-placed `{goal}/envelope.json`. `injectDeclaredEnv` still skips absent names if called without the gate (pre-existing belt). Filename `envelope.json` is now spelled in three places (`launch.js#FILL_IN_NAME`, `path_b.ENVELOPE_ARTIFACT_NAME`, `plan_envelope.ENVELOPE_ARTIFACT_NAME`) — pre-existing JS/Python split, a third copy added because `path_b.py` is a no-touch consumer.

## Verification
Red-first fixture (no envelope.json): caged print `ABSENT`. After `071687e7`: `node ignite/envelope/envelope-launch.selftest.js` prints `PASS missing-credential-refuses`; `node ignite/envelope/probes/probe-credential-injection.js` L1–L4 ALL LEGS PASS (absent print, missing-key `E_LAUNCH_REFUSED`, fixture token present inside bwrap, canonical `.env` read fails); `python3 -B ignite/planning/probes/probe-plan-envelope.py` 5/5 PASS (writer → bound commit → `bound_envelope_fillins` reads `["ELEVENLABS_API_KEY"]`). Not deployed.

## ATTENTION
1. `admitLaunch` must keep calling `resolveCredentials` after compile — skipping it recreates the silent unset spawn `injectDeclaredEnv` still performs on a missing name.
2. `plan_envelope.py` writes the bound-commit artifact; `_land_envelope` copies it at mint. Do not have the producer land `{goal}/envelope.json` itself, and do not have birth start authoring fill-ins.
3. `compilePlanning` zeros `credentialNames` on purpose. Putting names only in `admitLaunch` extra fields without an `envelope.json` will not survive a no-fill compile.
4. T2-R11/D19 still stands: never bind `.env` / `credentials/` into the cage to "make the key visible". Env injection is the only channel.
5. A plan that needs a secret must run `plan_envelope.py` BEFORE the bound commit is taken. Writing the file onto the planning goal after `approve-package.json` names a commit does not put it in that tree.
- admitLaunch must keep calling resolveCredentials
- plan_envelope.py authors the bound artifact; _land_envelope copies at mint
- T2-R11/D19: env injection only, never bind credential files
