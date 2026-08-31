# 20260831-i-paneless-renew-places-a-caged — Paneless renew places a caged daemon-lane successor

kind: issue
component: supervisor
date: 2026-08-31
commit: 82d724a4
deployed: no
pin: ignite/supervisor/seeding.selftest.js
components: coord

## Observed
On 2026-08-18 a paneless `checkout --renew` (daemon-lane roster cell `sid:<uuid>`) printed an `is_tmux_pane` refusal into a dying session, wrote nothing durable about the missing successor, and the lineage ended. `ea56f75c` made that refusal loud (`lifecycle-inflight.json` FAILED + bus alarm); `3b43bda1` classified it `RENEW-BLOCKED`. Acceptance "never silent" held; the successor still never came back. Reproduced 2026-08-31 on HEAD before this commit: `fork_lifecycle_renewal` on pane `sid:pl-red-1` exited 2, marker `state: FAILED`, no `placement-requests.json`. Repo HEAD, not the deployed daemon copy.

## Mechanism
`lifecycle_fork_target` requires a `%N`. A daemon-lane row never has one, so the function correctly returns empty rather than letting tmux resolve a blank `-t` to the most recent session (measured as the live console room). `fork_lifecycle_renewal` treated every empty target as `lifecycle_no_successor`. There was no other door that could enqueue a caged successor on the seat's own daemon lane. The killed `revival_target` candidate had returned uncaged into the console room; that is why the empty-target refusal stayed.

## Attempts
First attempt at loudness held as a refusal, not a placement — checked: `ea56f75c` (paneless-renew signal), `3b43bda1` (renew-gate RENEW-BLOCKED), park-wait `86e276df` / memory `coord/20260831-i-parked-wait-is-incomplete-not` (explicitly declined this door), `renew-gate` declined because it changes how gates READ a renew, crash-rerun-door is crashed-row admission not `--renew`. Silent-freeze-fixes LE-8 left the feature unbuilt.

## Fix
A healthy `sid:` renew now writes `coordination/placement-requests.json` (`kind: daemon-lane`, workdir `seats/<seat>`) and stamps the inflight marker `place: daemon-lane` / `state: done` so `renewal_state` stays successor-pending (RENEWING, not RENEW-BLOCKED). `seedGoal` consumes that file through the existing `launchThroughDoor` (job_id `seat-<goal>-<seat>`, session_mode headless, seeding launcher). Spawn is unchanged: `composeCageFor` + `buildBwrapArgv` at dispatch. Rejected: tmux respawn, console-room recovery, making RENEWING launchable in `VERDICT_DOOR` (would double-launch pane renewals), JS parsing `lifecycle-inflight.json` (one reader remains Python). Empty pane / unwritable request still take `lifecycle_no_successor`; `is_tmux_pane` is untouched.

## Consequences
`checkout --renew` on a paneless seat now exits 0 and tells the seat a seed pass will relaunch it caged. s3-09 (7) recast from FAILED-refusal to placement-request; (7c) keeps the empty-pane loud refusal; (7b) still proves `lifecycle_fork_target` returns empty for `sid:`. Shared seeding/spawn with room-selfheal and crash-rerun-door: only placement-request consumption was added.

## Verification
Red fixture: paneless `fork_lifecycle_renewal` → exit 2, FAILED, no placement file. Green: same pane → return `daemon-lane`, marker `done`/`place: daemon-lane`, `placement-requests.json` present, `renewal_state` successor-pending; empty pane still exit 2 FAILED. `node ignite/supervisor/seeding.selftest.js` ALL PASS including consume (job_id/headless/seat workdir/no tmux) and RENEWING-without-request not enqueued. `python3 coord.py selftest` from `ignite/coord/`: s3-09 (7)/(7c)/(7b) ok; suite still FAIL 24 on pre-existing unrelated rows (P2/T4/P26/…), matching prior seats' pristine-HEAD red. Not deployed.

## ATTENTION
- Do not make `VERDICT_DOOR.RENEWING` launchable — pane renewals already fork via lifecycle-exec; the placement file is the only extra offer.
- Do not parse `lifecycle-inflight.json` from JS; successor-pending stays `renewal_state`. The actuator is `placement-requests.json`.
- Never fill an empty tmux target as a fallback. That is the revival_target hazard: uncaged into the live console room.
- `is_tmux_pane` remains the error-path predicate. Only a truthy `sid:` cell takes the placement success path.
