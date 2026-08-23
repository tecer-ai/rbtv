# 20260820-i-staff-wake-mint-mismatch — staff-wake-mint-mismatch

kind: issue
component: team-kit
date: 2026-08-20
commit: 05490c92,e5a8e0de,8fcc3b76,a3b58eaf,165114ec
deployed: yes
pin: NONE remaining by design; retired probe arms' ABSENCE is the proof
components: engine,server
seeded: true

## Seen
A staff wake was stamped spent but no leader ever fired (2026-08-19, meet-transcript-summarizer).

`plan-3-plan-task-definer`'s checkout at 2026-08-19 03:12:46Z minted a leader staff-wake bound to session `f2b151ce` — the leader's PREVIOUS sitting (ended 03:02), not the sitting `55d7c7ce` that had exited 10 seconds earlier at 03:12:36. `ready-seats` drops any unspent grant whose session-id is not the seat's last-ended id, so once the closer stamped `55d7c7ce` as last-ended, the grant became permanently invisible — burned (`spent-at 03:12`) with no corresponding daemon fire. `mint_staff_wake`'s own docstring (`coord.py:15567`) records the SAME defect class measured once already on this same goal, 2026-08-15 (grant `46d185eb…` minted mid-sitting, orphaned).

## Missed
2026-08-15 fix (mint_staff_wake, cited in its own docstring) closed only the LIVE-SITTING window — bind to the OPEN session instead of the last-ended one. It did not close the PROCESS-DEAD-BUT-ROW-NOT-YET-CLOSED window: `sessions_sitting_id` (coord.py:15487) requires the session row be OPEN and its (pid, pid-starttime) name a live process; at 03:12:46 the leader's harness process was already dead so it fell through to `sessions_last_ended`, which had not yet been re-stamped by the kit-for-seat closer and so still read the leader's second-to-last sitting. Any seat whose checkout lands inside that lag reproduces the mis-bind. (Source: `handoff-frozen-goals-2026-08-19.md`, "known defect class" section.)

## Held
D12: the whole grant machinery was deleted outright rather than patching the bind window again.

3 stores, 4 predicates, a TTL, and a suppression latch, across `engine/relaunch-grants.js` (deleted), `attached-execution.js`, `seeding.js`, `spawn.js`, `ticker.js`, and `team-kit/coord.py` (net -2805 lines in `e5a8e0de` alone). Companion commits `8fcc3b76` (retire the grant probe arms and the docs that taught them) and `a3b58eaf` (no comment describes a deleted grant mechanism) followed the next day. `165114ec` fixed a stray `CLAUDE.md` reference to the deleted `sessions_sitting_id` machinery.

## commit
05490c92,e5a8e0de,8fcc3b76,a3b58eaf,165114ec

## files
ignite/team-kit/coord.py (grant-reading code removed); ignite/engine/relaunch-grants.js (deleted); ignite/engine/attached-execution.js, seeding.js; ignite/server/spawn/spawn.js; ignite/server/ticker/ticker.js

## deployed
yes

## pin
NONE remaining by design — the retired probe arms (probe-relaunch-grant.js, probe-disposition-grants.py) were themselves deleted/retired in `8fcc3b76`; their ABSENCE is the proof, not a passing arm.

## ATTENTION
- fix-inventory notes D12 deleted the grant machinery on an UNVERIFIED claim that reconcile already relaunched seats by name — it did not (only the leader did) — reopening the exact stranding problem the deletion was meant to close (`redesign-plan-seed.md` §4, `rca-resolve-and-refresh-2026-08-20.md` A6). Do not assume D12 fully closed the class; check whether reconcile's by-name relaunch was ever actually built before relying on this.
- A deletion's correctness is the absence of the deleted surface — verify with a grep-for-resurrection sweep, not a probe run, before trusting this is still gone.
- This is the same defect class (dead-process-but-row-not-closed) that `record-ledger-custody` (2026-08-19, same component) narrows from the other side — read both together.
- D12 deleted on an unverified claim reconcile already relaunched by name; check that before trusting this fully closed
- A deletion's correctness is an absence-of-surface grep sweep, not a probe run
