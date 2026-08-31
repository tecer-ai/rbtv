# 20260831-i-finished-goals-resurrected-aft — finished goals resurrected after finish edge

kind: issue
component: supervisor
date: 2026-08-31
commit: 34d5b018
deployed: no
pin: ignite/supervisor/finish-gate.selftest.js
register-id: G-leader-0830-1800

## Observed

`stools-canvas-audio-elevenlabs-close` fired its finish edge 2026-08-30 16:43 (message #48), which killed its tmux room — yet the room was rebuilt ~70 min later at the 17:53 daemon restart, and post-finish goal-master sittings ran 08-30 22:21–22:28 and 08-31 11:51. Companion `stools-canvas-audio-elevenlabs-planning` launched sittings 9–11 after finish 2026-08-28 21:15; sitting 9 re-fired `finish-goal` (refused); 11 sat out attempt 3 of n=3. A 17:53:00 code-deploy re-arm cleared the unread brake. Reproduced on HEAD 2026-08-31 against the repo tree (deployed daemon still unfixed): a fixture with `FINISH_MARKER` completion, dead room, and staff-addressed unread made `reconcileGoal` (force, recoverFn recording) enqueue the leader and emit `room-rebuilt`. Live `heart.db` (`/.rbtv/runtime/ignite/heart.db`) has zero `goal_states.stored='finished'` rows.

## Mechanism

No finished-goal check existed on the daemon path. `reconcileGoal` gated only on cadence and `laneIsPaused`; then if `derived.owed` and the room was dead/empty it rebuilt under the leader chair. `classifyOwed` / `deriveOwed` / `runLaneWatch` never asked `goal_finished` / `FINISH_MARKER`. The finish edge (`fire_finish_edge` in `coord/records.py`) appends a `completion` whose body opens with `FINISH_MARKER = "goal-finished: the finish edge fired"` and tears the room down second — so the intermediate state is "finished, room still up", which watchers must read from the EVENT. `isGoalFinished` (`row.stored === 'finished'`) has no daemon-path consumer and nothing stamps it. A finished goal with any staff-addressed unread, or a re-arm that deletes the attempt counter, therefore bought another n empty sittings. A leader woken this way has no sanctioned door to tear the wrongly-rebuilt room down (`coordinate finish-goal` refuses re-fire).

## Attempts

First attempt held — checked: `20260830-i-readcursor-answered-the-first` (`a340bb28`, the first-row-wins cursor, already on HEAD: `readCursor` walks every matching row and returns the newest numeric; `owed-from-endings.selftest.js` arm (5) green, so that clause is STALE and was not rebuilt), `20260830-i-class-b-unread-test-read-check` (`fa89fa75`, checkin-vs-cursor — distinct, sibling unread-cursor), `20260828-c-the-finish-edge-s-3-line-compl` (ferry already consumes the marker for Slack, never the daemon), `20260828-i-a-code-deploy-wiped-the-counte` (re-arm is an amplifier, not the cause). Store-as-canonical was rejected because live heart.db has zero `stored='finished'` rows, so existing finished goals would keep resurrecting without a backfill, and F5 forbids the lease learning a stored status.

## Fix

One canonical source: the EVENT. `finishEvent(goalFolder)` in `owed-from-endings.js` scans `messages.md` for a `completion` whose body opens with `FINISH_MARKER` (byte-identical to `records.py`, PIN'd). `classifyOwed` returns empty owed, `deriveOwed` zeros class R as well, `reconcileGoal` early-skips `{ skipped: 'finished' }` like pause, `runLaneWatch` skips seeding. The lease stays blind (F5 intact; `records.py` / `writeGoalWord` untouched). A red mutation that makes `finishEvent` always return false resurrects the same fixture.

## Consequences

No store stamp, no backfill, no `isGoalFinished` on the daemon path. `bus-ferry.js` already held a second JS copy of the marker (PIN'd there too); supervisor now has its own copy rather than importing chat. `readCursor` first-row-wins was not rebuilt. Sibling seats (hold-classb, unread-cursor, finish-no-leader) were not touched. `reconcile.selftest.js` still aborts at a pre-existing D33(a) payload needle (`No runtime ruling instrument exists`); finish-gate arms live in `finish-gate.selftest.js` and are required from the historical suite so they run first.

## Verification

`node ignite/supervisor/finish-gate.selftest.js` ALL PASS (PIN, finished fixture stays down, running control still recovers, CODE_DEPLOY/RESUME re-arm still skips, red mutation resurrects). `node ignite/supervisor/owed-from-endings.selftest.js` ALL PASS including arm (5) and first-row-return red mutation. `python3 ignite/coord/probes/probe-finish-edge.py` 13/13 PASS including F5. `node ignite/supervisor/probes/probe-reconcile.js` exit 0 (keyed on finish-gate; historical suite still red at D33(a)). Commit `34d5b018` on `ignite/core-daemon`. NOT DEPLOYED — zombie room `stools-canvas-audio-elevenlabs-close` must not be torn down until the orchestrator's exclusive deploy window.

## ATTENTION

- The EVENT answers "was it DECLARED finished?" from the append-only log; the LEASE answers "is it EXECUTING?" from the room and must stay blind (`probe-finish-edge.py` F5). Wiring `isGoalFinished` / `stored='finished'` on the daemon path rebuilds the 7.608 deadlock one file over.
- `finishEvent` is the ONE JS reader. Do not add a second scan of `messages.md` in `reconcile.js` or `lane-watch.js` — they already call it. A completion that does not OPEN with the marker is not a finish event (F4).
- `reconcile.selftest.js` aborts at a stale D33(a) needle (`No runtime ruling instrument exists`) that predates this fix; D35 would fail next (checkin-vs-cursor, sibling unread-cursor). Finish-gate proof is `finish-gate.selftest.js`.
- Do not kill the live `stools-canvas-audio-elevenlabs-close` room before deploy: killing it before the gate ships just re-arms the resurrection.
- `rearm` (CODE_DEPLOY / RESUME) deletes attempt counters and is not a reopen. The finish gate must hold through a re-arm or each deploy buys another n empty sittings.
- The EVENT answers was it DECLARED finished from the append-only log; the LEASE answers is it EXECUTING from the room and must stay blind (probe-finish-edge F5). Wiring isGoalFinished on the daemon path rebuilds the 7.608 deadlock.
- finishEvent is the ONE JS reader. Do not add a second scan of messages.md in reconcile.js or lane-watch.js. A completion that does not OPEN with the marker is not a finish event (F4).
- reconcile.selftest.js aborts at a stale D33(a) needle that predates this fix; finish-gate proof is finish-gate.selftest.js.
- Do not kill the live stools-canvas-audio-elevenlabs-close room before deploy: killing it before the gate ships just re-arms the resurrection.
- rearm (CODE_DEPLOY / RESUME) deletes attempt counters and is not a reopen. The finish gate must hold through a re-arm or each deploy buys another n empty sittings.
