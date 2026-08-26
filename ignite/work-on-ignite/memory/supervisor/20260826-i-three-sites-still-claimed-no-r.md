# 20260826-i-three-sites-still-claimed-no-r — three sites still claimed no ruling instrument exists

kind: issue
component: supervisor
date: 2026-08-26
commit: f3aa3f16
deployed: no
pin: NONE
components: chat,operator,engine

## Observed
impl-leader-verbs (commit d7841291, 2026-08-26) wired the leader's ruling acts (`supervise accept`,
`supervise instruct`) and fixed six sites that told a reader no ruling instrument exists — but three
more sites survived unfixed: `ignite/supervisor/reconcile.js`'s `nontermPayload` (~line 346),
`ignite/chat/README.md` (~line 373), and
`ignite/operator/attached-execution/attached-execution.md` (~line 543), each still saying "no
runtime ruling instrument exists" / "that door is not wired here yet."

## Mechanism
`reconcile.js`'s `nontermPayload` wakes the leader for rows with an ENDING nothing can advance on
(exited/unverified/incomplete) — exactly the case `supervise instruct`/`accept` now rule on
(`ignite/coord/ruling.py`: "`instruct` a seat's ended session out of the state that keeps
re-waking the chair"). `chat/README.md` and `attached-execution.md`, by contrast, both describe a
SEAT HELD ON AN OPEN OWNER-ASK — not an ending at all (the seat has not checked out) — a case
`supervise instruct`/`accept` do NOT reach, since both operate on `store.getCurrentEnding`.
`leader.md` §4 confirms this gap is real: its "one existing exception" note states there is
otherwise no sanctioned way for a leader to force-close a stale unanswered ask, only its own
`escalation` to the owner.

## Attempts
First attempt held — checked: d7841291's `launch.py`/`attest.py` hunks (the wording pattern this
fix's reconcile.js hunk mirrors) and `ignite/coord/ruling.py`'s docstring (confirms `instruct`/
`accept` are scoped to an ENDED session, not an open ask hold — this is why README.md/
attached-execution.md got a DIFFERENT fix than reconcile.js rather than the same verb-substitution).

## Fix
`reconcile.js`: replaced the "not wired here yet" sentence with the same `supervise accept`/
`supervise instruct` pointer d7841291 used elsewhere, text-only, no logic touched. `chat/README.md`
and `attached-execution.md`: did NOT claim `supervise accept`/`instruct` fixes the hold-release gap
(that would be a new false claim) — instead stated plainly that this is a standing gap with no
replacement, that the two ruling verbs are scoped to endings and do not reach an open-ask hold, and
pointed at the leader's own `escalation` (`meta/leader/prompts/leader.md` §4/§5) as the actual
sanctioned recourse when an ask will never be answered.

## Consequences
No logic changed in any of the three files — text only. `ignite/engine/probes/probe-reconcile.out`
(a stale duplicate baseline under the OLD pre-move `engine/` location, referencing
`engine/reconcile.selftest.js` and the deleted `rule-disposition` command) was checked for live
consumers and found orphaned — grep across `*.md`/`*.py`/`*.js`/`*.csv` found no reference to that
path, and no `probe-reconcile.js` script exists at `engine/probes/` to regenerate it. NOT deleted
(out of this run's grant); surfaced as a loose end instead.

## Verification
Read `ignite/coord/ruling.py`'s module docstring and `relaunch-budget.js`'s `executeLeaderInstruction`
(both confirm the ended-row scope) before choosing different fixes for reconcile.js vs the other
two. `grep -rln probe-reconcile` across the repo (excluding node_modules) to confirm no consumer of
the engine/ copy.

## ATTENTION
1. `supervise accept`/`supervise instruct` rule an ENDED session's row — they do NOT release a seat
   held on an open, unanswered owner ask. Do not port the same fix pattern between the two cases;
   they are different mechanisms with different (in the ask-hold case, currently absent)
   remedies.
2. `ignite/engine/probes/probe-reconcile.out` is a dead leftover from before `reconcile.js` moved
   to `ignite/supervisor/` — it is stale (pre-dates the ending/disposition vocabulary rename) and
   has no `.js` counterpart at that path to regenerate it. Orphaned, not deleted.
- supervise accept/instruct rule an ENDED row only, never an open ask hold
