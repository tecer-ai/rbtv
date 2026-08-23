# 20260820-i-chat-live-holder-fix — chat-live-holder-fix

kind: issue
component: bridges
date: 2026-08-20
commit: 63413504,22301f66
deployed: yes
pin: NONE
seeded: true

## Seen
The live-holder branch claimed delivery to a busy seat and lost the message; a delivered reply still fired the slow-notice hourglass.

Defect 1 (63413504), measured 2026-08-20 01:20:35Z on `meet-transcript-summarizer`: a top-level owner post found a live sitting at the goal-master seat. The branch logged "writing the bus and nudging", got `no-warm-session` back, logged "bus write still stands" and returned `forwarded:true`. Both claims were false — `recordBusAnswer` is `kind:'agent'` only by design, so on a goal route it returned null before writing anything, and nothing was enqueued or mapped. A whole-goal-folder scan found no trace of the text.

Defect 2 (22301f66), owner-reported 2026-08-20 ~03:50Z: both goal channels received their real replies (execs 30193/30188, 03:46:54Z and 03:47:04Z) and STILL got the "⏳ still working — 5 minutes so far" notice ~3 min later.

## Missed
none recorded in sources.

## Held
Live-holder branch now requires PROOF of delivery before claiming it; the delivery-success branch also spends the slow-notice budget.

63413504: the branch now requires PROOF of delivery — a recorded bus row (agent route) or a fed warm session. Neither → it falls through to the ordinary session-create, whose `on_seat_busy: queue` makes a busy seat lossless. A fed nudge also maps the thread and binds the holder's exec-id, so the reply leg can ferry the answer back — it armed nothing before. The two misleading log lines now say what actually happened. `probe-chat-live-holder.js`: 3 arms + a mutation arm that cuts the fall-through and requires the loss to reproduce.

22301f66 root cause: the delivery-success branch reset `armedAt`/`revives`/`compacted`/`disarmedAt` but never spent `slowNoticed`, so the P3 rung fired at `turnStartedAt+300s` on an already-answered turn. One flag now set in the delivery branch; `arm()` already re-opens the budget on the next real owner turn. Probe: new t3 arm in `probe-chat-reply-leg` (RED pre-fix — reproduced the hourglass post-delivery; GREEN post-fix). Control u3 (unanswered turn still gets the notice) unchanged green.

## commit
63413504,22301f66

## files
ignite/bridges/chat/forward-path.js (live-holder branch); ignite/bridges/chat/probes/probe-chat-live-holder.js (new); ignite/bridges/chat/reply-leg.js (slow-notice budget); ignite/bridges/chat/probes/probe-chat-reply-leg.js (arm t3)

## deployed
yes — rbtv HEAD ac1c08d8, deployed 2026-08-21 18:14:37Z; no ignite JS commits land after it.

## pin
NONE

## ATTENTION
- The live-holder branch must never claim `forwarded:true` without one of the two proofs (recorded bus row or fed warm session) — a future edit that removes either check reintroduces silent message loss with no error surfaced.
- Any new success/delivery branch in `reply-leg.js` must explicitly spend `slowNoticed` — it is not reset automatically by a delivered reply, only by `arm()` on the next real owner turn.
