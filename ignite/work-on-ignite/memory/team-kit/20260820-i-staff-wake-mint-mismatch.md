# 20260820-i-staff-wake-mint-mismatch — staff-wake-mint-mismatch

kind: issue
component: team-kit
date: 2026-08-20
commit: 05490c92,e5a8e0de,8fcc3b76,a3b58eaf,165114ec
deployed: yes
pin: NONE remaining by design; retired probe arms' ABSENCE is the proof
components: engine,server
seeded: true

## Observed
On `meet-transcript-summarizer` at 2026-08-19 03:12 UTC a staff-wake grant was written, stamped `spent-at`, and produced no leader sitting. A console session diagnosing the owner's "why are these two goals not running?" recorded it ~11:30 UTC as a read-only finding (`handoff-frozen-goals-2026-08-19.md`); nothing was minted or recovered at write time. Daemon health was fine (`healthy` since 01:57, `n_restarts: 0`). At diagnosis the goal sat 35 DONE / 31 BLOCKED / 0 READY.

Timeline, all UTC. 03:06 `plan-3-plan-resource-definer` checks out and mints a leader staff-wake bound to `f2b151ce` (the leader's last-ended sitting, ended 03:02). 03:07 the grant is spent and the daemon fires leader session `55d7c7ce`. 03:12:36 that leader exits 0 `done`; its last message (#322) says Link 7 waits on the still-running task-definer. Ten seconds later, 03:12:46, `plan-3-plan-task-definer` (session `86a5af71`) checks out and mints the leader's staff-wake again. The row written:

`leader,f2b151ce-8c31-483e-983e-2dfaaeeb46d9,staff-wake,plan-3-plan-task-definer,2026-08-19 03:12,2026-08-19 03:12,,`

`f2b151ce` is the leader sitting that ended at 03:02, not the sitting that had just exited. Last `seat-meet-transcript-summarizer-leader` in the daemon store stays 03:07:26; no leader fire since. The same goal had already measured this class four days earlier: grant `46d185eb` minted 23:36 mid-sitting of `6a4a0ce4`, orphaned at 23:41, leader DONE with unread #70 (`05490c92` commit message).

Header `deployed: yes`. Inventory D12: YES at rbtv `ac1c08d8` (deployed 2026-08-21 18:14:37Z). `coord.py` is live-tree Python (effective on commit). Engine/server JS is inert until `rbtv ignite daemon deploy`.

## Mechanism
`mint_staff_wake` had four bind cases. The 03:12:46 mint fell in the gap between two of them (`handoff-frozen-goals-2026-08-19.md` Issue 1).

The sitting branch (`sessions_sitting_id`) required the session row OPEN *and* its `(pid, pid-starttime)` to name a live process via `ident_is_live_process` — the same liveness pair the session-closer's term (b) uses, added so a crashed abandoned OPEN row cannot capture a grant. At 03:12:46 the leader harness was already dead, so that read returned `''`. The fallback `sessions_last_ended` ignores open rows. The `kit-for-seat` closer had not yet stamped `55d7c7ce`'s `ended` cell, so last-ended still read `f2b151ce`. Net: the grant bound to a sitting two generations old.

Then `ready-seats` dropped any unspent grant whose `session-id` was not the seat's last-ended id. The instant the closer stamped `55d7c7ce`, last-ended ≠ `f2b151ce` and the grant became permanently invisible. The row carries `spent-at 03:12` with no corresponding daemon fire — authorization burned without a sitting. That is absorbing: a mis-bound grant cannot self-correct; the only recovery was to mint another, which races the same closer-lag.

Two stores had to agree. `relaunch-grants.csv` is what `ready-seats` reads (the daemon door). The bare `relaunch-grants` file is what `engine/relaunch-grants.js` → `seeding.js#executionsByJob` reads (hides finished history). `mint_staff_wake` wrote both; a wake on one only stalled on the other.

## Attempts
`05490c92` (2026-08-15 15:03Z) closed the *live-sitting* window: `mint_staff_wake` stopped reading `sessions_last_ended` while a chair was mid-sitting and instead bound to the OPEN session via the new `sessions_sitting_id` (OPEN row plus the live `(pid, pid-starttime)` pair). That is the 08-15 `46d185eb` / `6a4a0ce4` case. It did not close the process-dead-but-row-not-yet-closed window the 08-19 mint landed in. Any checkout inside the lag between a chair's process exit and its closer stamping `ended` reproduces the mis-bind. The handoff's immediate unblock was "one correctly-bound leader wake" — another mint of the same token, not a redesign.

Six further patches hardened the same grant subsystem before D12 (`git log --before=2026-08-20` on `coord.py` + `relaunch-grants.js`): `b0b41b18` (08-17, leader mints disposition grants because it cannot write ro-bound `sessions.csv`), `c5c7e1ff` (08-17, pause writes the park ruling; revoke retires grants), `12da2ded` (08-18, `spendCoordTwin` adopts coord's three-cell predicate), `c955c578` (08-18, a half-written wake no longer reports success), `2e4d64aa` (08-18, relocate the engine wake grant into `coordination/`, D6), `0c07b144` (08-19, lane-reach admission + goal-live check before spend, D5/D9). No RCA ties any of those six to a recurrence of *this* bind; they are the trail of a latch that kept needing repair. No deletion attempt predates D12 — `grant-deletion-inventory-2026-08-19.md` is the scoping doc *for* the deletion, not a prior trial.

## Fix
Owner ruling D12 (`redesign-plan/decisions.md`, 2026-08-19 planning interview): delete the grant machinery outright — three stores, four predicates, TTL/expiry, suppression latch. The manual override is "message the goal master". No grant survives as an override. Another bind-window patch was rejected: `05490c92` had already proved the class has more windows than one patch closes, and a single-use session-bound token stays absorbing the next time the fact it names changes between mint and read.

`e5a8e0de` (2026-08-20 12:28Z) is the deletion. Commit rationale (RC-B): goal advance hung on single-use, session-bound, non-idempotent authorizations with an absorbing failure state; 16,865 refused mint/spend calls recorded; the mint-suppression latch froze goals in both directions. Successor is per-goal reconciliation from the ledgers (`engine/reconcile.js`, D1/D15) — readiness computed fresh every pass, not consumed as a token. `rule-disposition --go` was reduced to write `sessions.csv` directly: store 3 existed only because "leader cannot write ro-bound sessions.csv" (`b0b41b18`); the D3 fence made the ledgers writable, so the grant hop died with its reason. Store *files* already sitting in goal folders were left as inert history no runtime path opens.

Same sitting, not the next day: `8fcc3b76` (12:45Z) retired grant probe arms surgically (Arm G of `probe-lane-at-birth.py`, grant-release halves of `probe-cross-lane-resume.js`, etc.) and retargeted docs at the goal watcher; `a3b58eaf` (12:55Z) swept eleven surviving prose citations of deleted machinery (two user-facing: `ready-seats` IDLE reason, `launch` deferral refusal) and re-pointed each at the successor; `165114ec` (same timestamp, own pathspec) retargeted `ignite/CLAUDE.md`'s PID-namespace note from the deleted `sessions_sitting_id` onto `ident_is_live_process`, the reader that still exists.

## Consequences
`e5a8e0de` is 15 files, +266/−5098 (`coord.py` −2805). Gone with the stores: both minters (`mint_staff_wake`, `mint_loop_refire`) and every call site (W8 of `cmd_send`, `close_staff_mail_arm`, `cmd_verdict` below-bar FAIL, `cmd_route_fail`), `ready-seats`' DONE→READY grant flip, CLI verbs `rule-relaunch` / `revoke-relaunch` / `seat-retry` / `apply-disposition-grants` / `rbtv-goal relaunch` / `launch --relaunch-ruled` / `rbtv run --relaunch`, `engine/relaunch-grants.js` whole, seeding's grant-masking, spawn's unspent-grant scan, the ticker's per-tick drain. CAGE/sandbox grants (`CAGE_GRANTS`, `resolveSeatGrants`) were left intact — different vocabulary.

D12's own justifying claim was false for one class. `rca-resolve-and-refresh-2026-08-20.md` A6: pre-D12 the only recovery door for a seat-written `incomplete` was the leader minting `rule-relaunch` + `launch --relaunch-ruled` (12 such grants on meet; task-definer 5×). The commit said reconcile "is live and relaunching seats on both production goals"; reconcile launched only the LEADER for non-terminal rows, and the stranded seat's name never reached `launchSitting`. CP4 never exercised a non-leader `incomplete`. redesign-plan-seed §4 names this as a fix re-done: the deletion reopened the stranding it was meant to close.

The deletion itself stood — no revert of the four D12 commits through 2026-08-23. The reopened door was rebuilt without grants, same day: `feba5fba` (17:33Z, D39) corrected eight `coord.py` statements (including `rule-disposition --help`) that had claimed an empty disposition cell re-arms a relaunch through seeding — the row comes back only via `launch --only <seat> --declare-only <anchor>`. `e3fc940f` (19:23Z, D42) added `launch --only <seat> --rerun <LEADER-ANCHOR>` for a kit-written `exited` row (escalation #655: six revival paths, all shut). That commit's own line: "D12 intact: no grant, no store, no latch, no TTL." Later `342ab357` (08-22, D81) is a further stale-citation sweep; the 08-22 cleanup audit still found remnants `a3b58eaf` missed (`route-fail -h` still taught both grant stores; `goal-stall-alarm.js` still named mint/spend).

Same-component `20260819-c-record-ledger-custody` (one day earlier) narrows the same closer-lag from the writer side: seats now write their own `sessions.csv` checkout row instead of a `kit-for-seat` proxy. Its ATTENTION already points here and says the window is narrowed, not gone.

## Verification
`05490c92` (the window that did not hold) pinned itself: `probe-staff-wiring` A-SIT + control (RED when the sitting-id read is reverted); `materialize-seats` SM-10/SM-11/SM-12 as ROW_ARMS row `staff-mint-debt`; `coord.py` selftest 0 failures; `materialize-seats.py --selftest` 59/59. Those probes died with the minter.

D12's pin is an absence, not a passing arm. `probe-relaunch-grant.js` (600 lines) and `probe-staff-wiring.py` (478) were deleted in `e5a8e0de`; remaining grant-only arms were retired in `8fcc3b76`. `fix-inventory.csv` D12: "the retired probe arms were themselves deleted/retired in 8fcc3b76; their ABSENCE is the proof, not a passing arm." The `delete-grants` seat's own checks (orchestrator re-verified at tip `165114ec`): zero-reference sweep by grep *and* python per symbol group; P4 a non-terminal row derived owed and enqueued `enqueued_by goal-watcher` with no grant file at any depth; P5 a HAS-SAT chair wakes on unread mail alone (`wakes: 0 delivered, 1 skipped`); live `ready-seats --json` `grant-keys: []` on both production goals; not one grant file written in 3h16m across three leader sittings that pre-D12 would each have minted one. Probe suite through the enumerator: 210 attempted, 204 pass, failing set byte-identical to the 12:00 pre-change baseline.

Deployed 2026-08-21 18:14:37Z at `ac1c08d8`. `coord.py` was live at `e5a8e0de` commit time.

## ATTENTION
- D12 deleted the grants on the commit's own claim that `reconcile.js` already relaunched seats by name. That was true only for the LEADER (`rca-resolve-and-refresh-2026-08-20.md` A6). The non-leader stranded-seat door is `e3fc940f`'s `launch --only <seat> --rerun <LEADER-ANCHOR>` (D42, same day), not D12. Treating the deletion as having closed the class reopens the stranding.
- Proof that the grant surface is still gone is a grep-for-resurrection, not a probe run — the probes that measured it were deleted with it. `a3b58eaf` found eleven surviving prose refs on the first sweep; the 08-22 audit still found more (`route-fail -h`, `goal-stall-alarm.js`). Hits on `CAGE_GRANTS` / `resolveSeatGrants` / `resolveRwPathGrants` are sandbox permission grants, a different vocabulary, and are supposed to remain.
- The process-dead-but-row-not-closed lag is the same window `20260819-c-record-ledger-custody` narrows from the writer side (seat writes its own checkout row). Read both before assuming either closed it; the kit still originates `exited` rows for seats that die before checkout.
- "D12" here is `redesign-plan/decisions.md` D12 (grant deletion). Three independent D-number series collide on the same integers — the installer strand and the decision-review strand each have an unrelated D12 / D-12.
