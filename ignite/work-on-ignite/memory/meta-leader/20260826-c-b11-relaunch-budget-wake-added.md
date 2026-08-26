# 20260826-c-b11-relaunch-budget-wake-added — B11 relaunch-budget wake added to leader.md

kind: change
component: meta-leader
date: 2026-08-26
commit: f3aa3f16
deployed: no
pin: NONE
components: supervisor

## Motivation
B11 (the retry-budget handoff to the leader, wired 2026-08-26, `ignite/supervisor/relaunch-budget.js`)
gave the leader a fifth wake reason — a seat's recovery relaunch budget exhausted — but
`meta/leader/prompts/leader.md` §1 ("You were woken by mail") still enumerated only the original
four causes (staff mail, mid-run ask, routed FAIL, executor-failure alarm). A leader woken this way
had no prompt text explaining what the wake meant or how to answer it.

## Design
Added a fifth bullet to the same enumerated list, in the same voice and format as the other four,
rather than a separate section — the wake IS one more thing that "arrives here" per §1's own framing,
and a seat that reads unread mail queue-first should meet it in the same place as the rest.

## How it works
The bullet states the trigger (relaunch budget exhausted), the bound (ONE attempt), the closed
instruction list, and the answer mechanism (write the JSON file the wake names). Verified against
the live code rather than trusted from spec: `relaunch-budget.js`'s `INSTRUCTIONS` object gives the
four kind strings (`rewrite-brief`, `reassign`, `blocked-pending-plan-gap`, `escalate`) and
`LEADER_INSTRUCTIONS_REL` gives the path (`.rbtv/runtime/ignite/leader-instructions`), both quoted
verbatim into the bullet.

## Consequences
Purely additive — no other wording in leader.md changed. "Four things arrive here" became "Five
things arrive here" in the same sentence.

## Verification
Read `relaunch-budget.js` lines defining `INSTRUCTIONS`, `LEADER_INSTRUCTIONS_REL`, and
`leaderInstructionPath` directly; the bullet's path and four names match byte-for-byte. No selftest
exists over prompt prose (leader.md is not code); the match against the source module is the
verification.

## ATTENTION
1. The instruction names are a CLOSED list enforced in code (`INSTRUCTION_LIST`) — if a fifth kind
   is ever added there, this bullet goes stale silently since nothing lints prompt prose against it.
- Instruction names are closed-list code; prompt prose is not linted against a future 5th kind
