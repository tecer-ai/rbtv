# 20260828-i-a-code-deploy-wiped-the-counte — a code deploy wiped the counters it had not caused

kind: issue
component: supervisor
date: 2026-08-28
commit: a7603764
deployed: no
pin: ignite/runtime/probes/probe-code-deploy-rearm.js
components: runtime

## Observed
Every daemon boot whose `ignite/` code digest differed from the last boot's wiped the ENTIRE
attempt-counter ledger, including the counters that measure a seat's own ending. Measured
2026-08-28 on `/home/henri/.local/state/rbtv-deploy/ignite/supervisor/attempt-counters.json` (mtime
10:44Z) and the daemon journal: `goal-memory-management/leader` carried
`(reconcile-respawn, nonterm) attempts=3, first_at 06:29:21Z, last_at 06:39:21Z,
owed_items ["distill-ignite-memory"], disarm_announced_at 06:39:21Z`, and the boot marker
`.rbtv/runtime/daemon-code.json` recorded a boot at 06:26:58Z immediately before those three
counted passes. The same three-sitting cycle had already run after the 03:20Z and 03:55Z deploys —
nine paid opus-5 leader sittings on one goal in one night (sessions `8d88b603`, `a09c8926`,
`ca3a4cf3`, `6d7029e9`, `15d7a6d3`, `14e7ba4e`, `d453b73c`, `7c52728f`, `e412ed7f`), every one of
them posting the same HOLD verdict and checking out `done`. Deployed tree and HEAD agreed on the
code quoted here.

## Mechanism
`runtime/index.js` calls `runtime/code-deploy-rearm.js#rearmOnCodeDeploy` at boot, which fires
`exhaustion.js#rearmScope({event: 'code-deploy'})` → `supervisor/attempt-counters.js#rearm`, where
`wide = event === RE_ARM.CODE_DEPLOY || event === RE_ARM.CONFIG_CHANGE` made the loop `delete
rows[key]` for EVERY key with no further test. The justification for that scope is the file's own
premise (`code-deploy-rearm.js:19-22`: "A RESTART IS NOT A DEPLOY. The same bytes hash to the same
digest") — the event fires because the CODE CHANGED, so the world a counter was measuring changed
with it. That justification holds only as far as the failure being counted was caused by the code.
It does not hold for `reconcile-respawn` / `nonterm`: that counter counts how many times the LEADER
was woken to rule ANOTHER seat's `failed` ending — a row in the ending store, written before this
daemon booted, which new daemon bytes do not touch and which a fourth wake is no likelier to
resolve than the third. So the deploy re-bought three leader sittings for a failure it had not
changed, and the cycle repeated on the next deploy.

## Attempts
First attempt at THIS problem held — checked before building:
`20260827-c-the-four-named-re-arm-events-g` (the entry that BUILT this producer; its ATTENTION 5
states "`rearm` WITH A WIDE EVENT CLEARS EVERY ROW, disarmed or not — that is the module's own
ruled scope, not an oversight of this pass", and its ATTENTION 3 already warned that the first boot
after a deploy re-arms every lane on the instance and that each is a real, paid sitting),
`20260827-i-new-staff-mail-counted-as-a-re` (the owed-item marker, which is the OTHER half of "what
counts as a retry" and is deliberately untouched here), and
`20260828-i-the-engine-never-held-the-endi`. This change NARROWS that ruled scope on the owner's
own later ruling (2026-08-28, decision 4 option (c), after the three read-only diagnosis seats in
`build/role-action-program/seats/diag-leader-nonterm/`); it is not a correction of that pass.

## Fix
The scope stays the EVENT's and only the CAUSE class is narrowed.
`attempt-counters.js#DEPLOY_IMMUNE` is a declared list of (driver, reason class) pairs — today the
single pair `reconcile-respawn` / `nonterm` — and `rearm` skips those rows when, and only when, the
event is `code-deploy`. Declared rather than spelled at the call site so a reviewer can read the
whole exception in one place, and so the boot pass can report what it kept.
Rejected: filtering in `code-deploy-rearm.js` (the caller would carry a second copy of the rule and
`rearmScope`'s per-subject sweep would still delete through it); filtering on `attempts >= N` (that
needs a second copy of the N, which `recovery-config.js` exists to be the only home of, and would
leave a row at N-1 counting through a deploy that changed the code it was counting refusals from —
`rearmScope`'s own header says so).
`config-change` is deliberately left alone: it has no producer at all, and what a config edit means
for an ending-caused counter has not been ruled. Lane-scoped events are unchanged, because a person
asking for a lane back (`resume {goal}`, an owner/leader act) is a fact about the LANE and never
about the code.
`rearm` now also returns `kept`, and the boot pass journals one `info` per kept row saying why —
a lane that stays disarmed THROUGH a deploy is a lane whose next wake is not coming, and that must
be as audible as a re-arm or the operator reads the silence as "it was cleared".

## Consequences
Nothing was deleted; `rearm`'s return gained a `kept` array and `rearmOnCodeDeploy`'s gained the
same, on every return path. `rearmScope` needed no change — it reports `cleared` from a before/after
diff of the ledger, so kept rows simply do not appear in it.
THE BLAST RADIUS IS REAL AND IS THE POINT: on the next boot, the two live `reconcile-respawn/nonterm`
rows survive — `goal-memory-management/leader` at 3 (already disarmed, and it now STAYS disarmed
through the deploy) and `scratch-death-recovery-1-exec/leader` at 2 (its next `nonterm` wake is the
third and disarms it). The two `unread` rows are still cleared. A disarmed `nonterm` lane can now
be re-armed only by `resume {goal}` (wired since 2026-08-28) or an owner/leader act (no producer);
that is the designed owner-visible exit, not a new stall, but it is no longer undone by a restart
with new bytes. Filed together with the leader HOLD (commit c29b2f43), the other half of the same
owner ruling: with a HOLD available, a leader that cannot rule a row no longer has to burn the
attempts this filter now preserves.

## Verification
`runtime/probes/probe-code-deploy-rearm.js` 21/21 EXIT=0, was 15/15. A2/A2b/A3/A3b and C1 were
retargeted onto the new truth (a deploy clears the two code-caused rows of the seeded four, the two
`nonterm` rows survive with `attempts=3`, one `info` per cleared row AND one per kept row, and a
first boot filters the same way). New section F states the fact on its own fixture: F1 the
`reconcile-respawn/nonterm` row persists with its attempts, F2 the `crash` row is cleared, F3 every
other class and driver keeps the wide behaviour, F4 the immune pair is declared and `deployImmune`
answers it, F5 an owner/leader act still clears the same row, F6 is the RED — the filter removed
from a compiled copy of the live source wipes the `nonterm` row again, so F1/F3 discriminate.
`attempt-counters.selftest.js` 7/7, `relaunch-budget` 8/8, `lane-skip` 5/5, `recovery-config` green,
`probe-leader-wake-counter` 26/26 PASS (its arm 3 re-arm expectation uses a lane-scoped event and is
unaffected). `probe-daemon-lane-watch` 1 failing check, L9 M9, documented pre-existing.
No nested `.rbtv/` created; tmux session list byte-identical. NOT DEPLOYED at filing.

## ATTENTION
1. THE EXCEPTION IS A CAUSE TEST, NOT A DISARM TEST. It keeps a `reconcile-respawn/nonterm` row at ANY count, not only at N. A row at 1 survives a deploy too — that is deliberate (the ending it counts did not change) and is why no `attempt_counter_n` read appears in `rearm`.
2. A DISARMED `nonterm` LANE NO LONGER UN-STICKS ITSELF ON A DEPLOY. Restarting the daemon with new bytes was the de-facto way those lanes came back; it is not any more. The wired escape is `resume {goal}`; `owner-leader-act` still has no producer. Do not report a lane re-armed on the strength of a deploy.
3. `config-change` IS UNTOUCHED AND STILL WIDE — it just has no producer, so nothing fires it. A future producer would clear the ending-caused rows this filter protects, which has not been ruled either way.
4. THE `kept` JOURNAL LINE IS THE ONLY PLACE A SURVIVING DISARM IS ANNOUNCED AT BOOT. `announceDisarm`'s once-marker rides the counter row, and a row that is no longer deleted is a row whose disarm is never re-announced — so removing the kept-row logging would make a permanently disarmed lane completely silent.
- a disarmed reconcile-respawn/nonterm lane no longer un-sticks itself on a deploy — resume {goal} is the wired escape
