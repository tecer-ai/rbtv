# 20260820-i-frozen-goal-alarm-fix — Frozen goal alarm fix

kind: issue
component: engine
date: 2026-08-20
commit: 079e08ec,0c07b144,fc34fb16,f45c3887,0c39fdfb,005c3c0c
deployed: yes
pin: engine/probes/probe-frozen-frontier.js + probe-verdict-vocabulary.js + server/ticker/probes/probe-reserved-interactive-slot.js
components: server
seeded: true

## Observed
The frozen-goal owner alarm (`server/ticker/goal-stall-alarm.js#conditionOf` reading `pickup.frozen` first, fed by `engine/seeding.js#seedGoal`) is the Slack page that fires when a goal cannot make progress. It shipped 2026-08-19 01:52Z in `079e08ec` (LE-13 / LE-10) and then failed three distinct ways in 23 hours.

First it stayed silent. The 08-19 `meet-transcript-summarizer` freeze had coord answering 66 rows and ruling 0 READY; `readyRows.length` was 66 (truthy), so the empty-frontier branch never ran. redesign-plan-seed §4: the guard "stayed silent through 5 more freezes."

Then it fired on healthy goals. At 2026-08-19 15:34:01Z, seconds after the daemon restarted onto `fc34fb16` (the first repair), Slack got `goal frozen AT seeding — ready-seats ruled NO seat READY…` for `stools-canvas-audio-elevenlabs` with 16 pending seats. The freeze-alarm seat reported this as live confirmation; that reading was wrong. Of those 16 non-`done` rows, 14 were a `planning-mode` variant that can never run (and its `after`-chain); only 2 were real work (the audio-lane block, D21, a different defect). `meet-transcript-summarizer` showed the same shape: roughly 13 of 31 BLOCKED rows dead, polarity inverted on the `plan-3` lane. Found by the redesign-plan console session after that seat had already flipped `done`; recorded in `dead-branch-mode-guards-2026-08-19.md`.

Third class, 2026-08-20: idle standing chairs (`goal-master`, `consultant` — summoned on demand, D24) re-lit the alarm as a live 10-second Slack loop. Discovered because CP4 check-2 (Slack posts in both goal channels) went silent: queue rows 943/944 deferred `global-cap` 121/118 consecutive ticks behind meet's six-checker wave on a hardcoded cap of 2. Owner ruled D25 at 00:55Z.

Header `deployed: yes`. D22 and D25 inventory rows both say YES at rbtv `ac1c08d8` (deployed 2026-08-21 18:14:37Z); all six header commits predate that deploy. Engine JS stays inert until `rbtv ignite daemon deploy`.

## Mechanism
Three stacked bugs in the same `pendingUnseeded` expression, each hidden until the previous was patched.

`079e08ec` computed `pendingUnseeded = (readyRows.length || moving) ? [] : seats.filter(s => states[s] !== 'done')` and handed `frozen: {kind:'seeding-empty', seats, detail}` to the alarm. Bug 1: `readyRows.length` is the raw count of rows `coordinate ready-seats` answered (any verdict). On the real freeze it was 66, so the `? []` branch skipped the filter and the alarm never armed.

Bug 2 (D22): once `fc34fb16` swapped the token to `ready.size` (rows coord actually ruled READY), the filter still counted every seat `!== 'done'`, with no reachability. A goal's `taskforce.csv` registers one seat per `planning-mode` variant (`full` vs `collapsed`); only the lane's chosen variant can ever run. The other variant — and everything `after`-chained downstream — stays `!== 'done'` forever. Their reasons read `<no check-out>`, indistinguishable from a seat waiting its turn. stools at measurement: 31 rows, 15 DONE, 16 BLOCKED, 0 READY; 14 of the 16 were this dead branch. meet: 66 rows, 35 DONE, 31 BLOCKED; the unprefixed lane runs `collapsed` (so `full` is dead) while `plan-3` runs `full` (so `collapsed` is dead). A goal-level read of `planning-mode.json` gets one of those lanes backwards.

Bug 3 (D25): after excluding `done` and `dead`, the filter was still "everything except the things I know are harmless." A third unrecognized state — IDLE standing chairs — fell through as pending and re-lit the 10-second Slack loop. Same subtract-the-known-harmless arithmetic that D25 says "guarantees a fourth."

The cap-2 starvation is a separate mechanism that surfaced in the same CP4 check: `ticker.js` defaulted `max_live_agent_sessions` to 2 (never chosen for this machine), so a checker wave filled the cap and owner-summoned chat-bridge rows queued behind it.

## Attempts
`079e08ec` (2026-08-19 01:52Z) is the birth of this alarm, not a prior fix. `0c07b144` (01:25Z the same day) is D5/D9 lane-reach admission + a goal-live lease check before grant spend; it touches `seedGoal` (the lease gate before the ready-row loop) but does not change the frozen predicate. redesign-plan-seed §4 pairs the two SHAs as "shipped a frozen-goal alarm"; the silent-through-5-freezes failure is `079e08ec`'s `readyRows.length` token, not `0c07b144`.

`fc34fb16` (15:33Z) swapped `readyRows.length` → `ready.size` and added `probe-frozen-frontier.js`. Verified by replaying the recorded 08-19 meet freeze snapshot: unpatched stays silent, patched alarms. Correct, incomplete: it exposed bug 2, which had been invisible while the alarm was silently broken. The freeze-alarm seat flipped `done`; 61 seconds later the "live confirmation" on stools was the next defect.

`0c39fdfb` (20:34Z) + `f45c3887` (20:47Z) added coord's derived `dead` field and excluded it from `pendingUnseeded`. Held for dead branches (meet 31→18 named seats, stools 16→4; remaining rows genuinely owed, including stools' D21 audio lane). Did not hold: the next unknown class (IDLE chairs, minted later that night under D24) fell through the same exclude-known-harmless filter. D25 names this the third incident of the guard misreading a verdict it did not know.

`005c3c0c` (2026-08-20 01:01Z) is the third repair and the one that held. No attempt predates `079e08ec` — `git log --before=2026-08-19 --grep=frozen` on `seeding.js` and `goal-stall-alarm.js` is empty; the missed-trials source frames 15:34Z as the alarm's first live firing.

## Fix
Four pieces, across the six header commits, each rejecting a named alternative.

The alarm itself (`079e08ec`): `seedGoal` classifies a zero-READY frontier over pending seats as `frozen:seeding-empty`; `goal-stall-alarm.js#conditionOf` reads `pickup.frozen` before its existing skew / ready-no-live arms. Pre-seeding continues (taskforce-unreadable, unbuilt-seats, and the rest) now hand the same shaped object so a goal frozen before seed also pages.

The one-token comparison (`fc34fb16`): test `ready.size`, not `readyRows.length`. Left untouched by every later patch — comments in `seedGoal` still mark it as freeze-alarm's landed fix.

Derived `dead` (D22: `0c39fdfb` then `f45c3887`). Owner picked option (a) of three: derived state in the one readiness predicate. Rejected (b) persist ("no ledger writes, nothing to drift") and (c) a seeding.js-only patch (would re-derive the `after` / guard-values grammar in JS, PRIN-11). The name is `dead`, not "standby": standby implies it might wake, which is the misreading that produced the 15:34 false alarm. `coord.py#mark_dead_rows` / `dead_after_entry` derive at read time: predecessor `done` + a `guard-values.csv` ruling that differs from the required value. Unruled and unfinished stay alive (fail-safe). Alternates (`a|b`) are dead only when every limb is; AND is any-member, iterated to a fixpoint so the downstream `<no check-out>` chain reports dead. Resolved per guarded member against that predecessor's own ruling row — per-lane correct for free. `planning-mode.json` is never read ("zero consumers by design"). A field, not a new verdict: the row stays BLOCKED / `unmet-predecessor`. `f45c3887` consumes `r.dead` and re-derives nothing; an absent field reads false, so an older coord.py degrades to the false positive, never to a hole in the alarm. `frozen.detail` now states how many rows were discounted — that string is what reaches Slack.

Invert the arithmetic + cap (D25: `005c3c0c`). Fix A: `CLASSIFIED_VERDICTS` names, per coord verdict, `waitable` (READY), `waitable-if-alive` (BLOCKED and not dead), or `not-waitable` (IDLE, DONE, HELD, RUNNING, SKEW, RENEWING, RENEW-BLOCKED, UNBUILT, UNDECLARED, STOPPED — and any future unknown verdict, by omission). `isWaitableWork` is the one classifier; `pendingUnseeded` becomes `waitableSeats`. An unknown class falls out of the alarm, never into it. Fix B: `max_live_agent_sessions` 2→14, plus `RESERVED_INTERACTIVE_SLOTS = 1` (`ticker.js#isReservedInteractiveRow`) so a batch/checker wave cannot starve an owner chat-bridge summons. Owner's words: "cap at 14 + 1". `dispatch.js` `?? 2` fallbacks bumped to `?? 14` to match.

## Consequences
No later commit rewrites the frozen-at-seeding classifier. `git log --since=2026-08-20` on `seeding.js`, `goal-stall-alarm.js`, `probe-frozen-frontier.js`, and `probe-verdict-vocabulary.js` shows only D12 grant-deletion comment cleanup (`e5a8e0de`, `a3b58eaf`) and a D81 citation retarget (`656da5d2`) — none touch `CLASSIFIED_VERDICTS` or `pendingUnseeded`. No revert through 2026-08-23.

The watcher risk named in the 08-19 root-cause doc (§4: if watcher re-derives "pending" it will churn on dead branches every five minutes) was closed as a decision by D22's placement: `dead-branches` before `watcher`, "the watcher now launches with the `dead` predicate already landed." `reconcile.js#deriveOwed` later consumes `r.dead === true` the same way (skip, report `deadExcluded`) — that is the intended inheritance, not a follow-up fix of this guard. A new consumer that re-derives "owed" from `!== 'done'` would reopen the false-positive class.

`probe-frozen-frontier.js`'s original red-arm anchor was a whole-statement match on `const pendingUnseeded = (ready.size || moving) ? []`; D22 split that into two lines and the arm silently stopped measuring. `f45c3887` re-anchored it. Same class as the alarm itself: a check whose failure is indistinguishable from success.

D23 corrected CP3 check 4's expected value from `dead 14` to `rows 31 dead 12` (stools) — the 14 was inherited from the root-cause doc calling an 11-row chain "13 downstream." Not a regression of this fix; a checkpoint that would have failed a correct system.

`0c07b144` is in the header because the seed digest and the original seeded entry grouped it with `079e08ec`. Its lane-reach / lease-gate work is not this issue.

## Verification
`fc34fb16` added `probe-frozen-frontier.js`. Discriminating pair driven through real `coord.py`, not a stub: FROZEN fixture (`onlyseat` after `missing-dep` UNDECLARED → `frozen` non-null) vs CONTROL (`onlyseat` READY → `frozen` null). Red arm mutates `ready.size` → `readyRows.length` on the same frozen fixture and asserts silence.

`f45c3887` extended it: DEAD-ONLY (every not-done seat is a dead mode-variant or downstream) → `frozen` null, and the wire carries `dead: true` / verdict BLOCKED from coord; PLUS-ONE (same fixture + one genuinely pending seat) → `frozen` names that seat and the detail states the excluded count. D22 red arm (`waitable-if-alive` returns true, ignoring `dead`) alarms on DEAD-ONLY. Pre-existing red arm re-anchored onto the two-line call site.

`0c39fdfb` added coord selftest RS-30…RS-33 (mismatch dead + transitive; unruled/unfinished not dead; live alternate alive; all-limbs-dead alternate dead); all four verified RED against pre-change coord.py on a copy of HEAD.

`005c3c0c` added D25 arms (IDLE-ONLY consultant+goal-master → `frozen` null; IDLE-PLUS-ONE names the pending seat, not the chairs; D25 red arm drives IDLE-ONLY through the pre-D25 `seats.filter(!== done && !dead)` and asserts it alarms) plus two new probes: `probe-verdict-vocabulary.js` extracts coord's live verdict vocabulary (AST of `CLASS_TO_VERDICT` + `rec["verdict"]` assignments — never a hardcoded copy) and asserts every value is a key of `CLASSIFIED_VERDICTS`, with a red arm that drops IDLE from a copy; `probe-reserved-interactive-slot.js` pins the reserved slot and asserts the production default is 14. fix-inventory D25: "Best-pinned ruling in the set — 3 independent scheduled probes."

Deployed: inventory rows D22 and D25 both YES at `ac1c08d8` (2026-08-21 18:14:37Z).

## ATTENTION
- Three stacked miscounts, each patch's own probe green. Any edit to `seedGoal`'s ready/frozen path must run all three pinning probes together (`probe-frozen-frontier.js`, `probe-verdict-vocabulary.js`, `probe-reserved-interactive-slot.js`), not the one nearest the touched line. The first probe shipped with no dead-branch arm, which is why the 15:34 false positive went green.
- Consume coord's `dead` field (`mark_dead_rows` / `dead_after_entry`). A JS re-derivation needs the `after` grammar, `guard-values.csv`, and the alternate/conjunct arithmetic — the duplication D22 and PRIN-11 rejected. An absent or older-coord field degrades to the pre-D22 false positive, never to a silent hole. `reconcile.js` already consumes the same field; a third copy will drift.
- `planning-mode.json` is not a signal for this guard ("zero consumers by design"). Polarity is per-lane: meet's unprefixed lane is `collapsed`, `plan-3` is `full`. A goal-level read gets one lane backwards and will mark live work dead (or dead work live). Resolve against that predecessor's own `guard-values.csv` ruling row.
- Count in only what coord positively classifies as waitable (READY, or BLOCKED and not dead). An unknown verdict must fall out. Adding a coord verdict without a `CLASSIFIED_VERDICTS` key is supposed to fail `probe-verdict-vocabulary` at commit time; classifying a new verdict as waitable-by-default, or subtracting another "known harmless" class, reopens the 10-second Slack loop D25 named as the guaranteed fourth incident.
- `ready.size` is freeze-alarm's landed fix and is independent of the waitable filter. Swapping it back to `readyRows.length` silences the real freeze (coord answered 66, ruled 0 READY) even if `CLASSIFIED_VERDICTS` is perfect. The probe's original red arm died once when the call site gained a second line — re-anchor, do not assume the whole-statement match still measures.
