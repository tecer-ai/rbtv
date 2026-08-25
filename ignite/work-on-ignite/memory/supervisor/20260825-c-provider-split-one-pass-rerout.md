# 20260825-c-provider-split-one-pass-rerout — Provider split, one-pass reroute, per-lane skip

kind: creation
component: supervisor
date: 2026-08-25
commit: 213cea90
deployed: no
pin: ignite/supervisor/provider-lanes.selftest.js
components: engine,launch-profiles

## Motivation
One bad lane froze the whole goal, and provider errors were not classified at all.

One unbuilt or quota-blocked lane froze the WHOLE goal, and provider errors were not classified at all. `lane-watch.js` `continue`d the entire goal when `uncastSeats` was non-empty and again for a registered-but-unbuilt row, so one bad seat stopped every healthy sibling (ST-20). And the same refusal path counted every launch failure identically: a transient quota outage struck the seat toward a dead end for something no seat did (ST-10), while a plan-declared bad slug got a silent no-strike dead end with the model pin never surfaced (ST-19). Three defects, one shape: the wrong thing was being asked about a single failure.

## Design
Three small modules: the word, what the word does, and the shared table.

Three concerns split into three small modules under `ignite/supervisor/`, because each is edited by a different person for a different reason. `provider-classify.js` reads two versioned owner-editable JSON lists (`provider-transient.json`, `provider-configuration.json`) and decides only the WORD; `provider-lanes.js` decides what that word does to a lane; `routing-table.js` reads the shared routing table. Rejected: one `provider.js` doing all three — a recognition-list edit would then have to reach into behaviour, and behaviour would grow a second opinion about what an error text means. The classifier fails CLOSED in both ambiguous directions (both lists hit, or neither hit) to CONFIGURATION, because a strike an owner can see beats a silent reroute that hides a pin. The per-lane skip is an INVERSION, not a new gate: `uncastSeats` stays a whole-goal computer and every door still asks it the same question; only its readers changed.

## How it works
`lane-watch.js` builds a `seat -> reason` Map from the unbuilt and uncast lists and threads it as `seedGoal({ laneSkips })`; `seeding.js#launchOwed` skips exactly those lanes at `warn`, seeds every sibling, and reports them back as `laneSkipped` (the fifth held-for-a-reason set). `reconcile.js` carries the provider-classification hookup in one thin function (`classifyRefusal`) that reads the seat DESCRIPTOR (`seatCast`) and its BINDING (`readTaskforce`), hands both to `provider-lanes.js#seatModelOverride`, and passes the decision on — nothing counter-internal is touched. TRANSIENT returns `strike: false` and either one reroute off `routing-table.js#eligibleAlternates` (`mode=cli` + `use=route`, minus the lane's own pin and anything in `tried`) or, when the one pass is spent, a `provider_backoff_until` computed by `backoffMinutes` from the recovery config's three backoff knobs. CONFIGURATION returns `strike: true` and the ordinary counter path spends it. `laneFacts()` exposes `provider_backoff_until`, `provider_backoff_waiting`, `reroute_pending` and the recorded `reroutes`.

## Consequences
`core/sub-agents/tool/models.csv` moved to `ignite/supervisor/models.csv` and `cast`'s `lib/route.js#CSV_LOCAL` was repointed with it, so the table is ONE file with two readers — otherwise the daemon could reroute onto a model `cast` cannot launch. That move dragged `test_route.js`'s shipped-table assertion, `lib/help.js`, `catalog.js` and the two component docs, all in the same commit. `reconcile.selftest.js`'s mutation red arm anchors on the counting branch's first source line, which the split's two new arms changed — the anchor was repointed rather than the branch reshaped. Its counter fixture also gained a `lanesFile` so a fixture pass never writes the module-default ledger into the repo, and `.gitignore` gained `provider-lanes.json` for the reason `attempt-counters.json` is there. Swept the now-dead `launched.kind === 'braked'` ternary in `seeding.js` — the admission brake died with the byte-equality brakes.

## Verification
`node --test ignite/supervisor/provider-classify.selftest.js` (8 pass), `provider-lanes.selftest.js` (12 pass, incl. the kill-clock pause read through `kill-clock.js#killDecision` and the loader-supplied backoff arithmetic), `ignite/engine/lane-skip.selftest.js` (4 pass, with a RED arm proving the empty skip set enqueues both seats and a source arm proving no whole-goal `continue` survives on either list), `ignite/engine/reconcile.selftest.js` (pass, mutation red arm intact), `node core/sub-agents/tool/test_route.js` (pass). Commit 213cea90. NOT deployed — worktree `ignite/core-redesign`, cutover is a later seat's act.

## ATTENTION
1. A recognition-list edit is a `config-change` named re-arm [spec-recovery §5] — `listsFingerprint()` exists so the boot/config-change path can detect it. Editing a list without re-arming leaves lanes disarmed on a classification the list no longer gives.
2. The override is measured as a DESCRIPTOR-vs-BINDING disagreement (`seat.md` model vs the `taskforce.csv` row), not a new frontmatter key. A future seat that adds a real override declaration must change `seatModelOverride` and not add a second predicate beside it.
3. `provider_backoff_until` is spelled exactly that way because `kill-clock.js#pauseState` reads that field name, and `provider_backoff_waiting` / `reroute_pending` because `observation/frozen.js#predicate` reads those. Renaming one silently un-pauses a kill clock or re-lights a frozen alarm through an outage.
4. `uncastSeats` is a COMPUTER, never a goal verdict. `reconcile.js#launchSitting` always read it per-seat and was right; only `lane-watch.js` was wrong. Do not re-add a whole-goal `continue` on that list.
5. The one pass through alternates is mechanical via `tried`, which only a backoff or a successful launch clears. A caller that clears it itself reinstates the infinite reroute the ONE-pass rule exists to bound.
- provider_backoff_until / provider_backoff_waiting / reroute_pending are contract names read by kill-clock.js and observation/frozen.js
