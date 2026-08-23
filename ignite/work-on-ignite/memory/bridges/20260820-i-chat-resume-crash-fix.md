# 20260820-i-chat-resume-crash-fix — chat-resume-crash-fix

kind: issue
component: bridges
date: 2026-08-20
commit: d491c8f0,91e287ca
deployed: yes
pin: bridges/chat/probes/probe-chat-summon-halted.js;server/ticker/probes/probe-chain-resume.js arm F
components: server
seeded: true

## Seen
Two chat-bridge defects (D28): a foreign-harness resume ref never resumes; a note on a halted chain also silently rots.

Defect 1 — resume crash (measured exec 30110, 2026-08-20 02:34:44Z): a seat re-cast across harnesses (D26/D27) handed `claude` its opencode predecessor's cwd-implicit `session_ref` — the seat FOLDER — and `claude -p --resume …/seats/goal-master` exited 1; the crash sweep owner-halted the chain and the reply leg delivered the fallback stub, in `ignite/server/ticker/ticker.js` (chain decision).

Defect 2 — silent notes (measured msgs 33266/33306, `routed_at_tick` NULL): a follow-up on a mapped conversation only filed a note, and a `failed` tail is the one verdict the daemon's wake-redispatch never wakes — owner questions rotted unread, in `ignite/bridges/chat/forward-path.js` (`forwardFollowUp`).

## Missed
none recorded in sources.

## Held
Refuse foreign-harness resume; summon on a mapped conversation whose chain tail failed with no live holder.

The ticker's chain decision now refuses a ref whose minting harness (`jobs_log.profile`'s key harness, bindingOf-shaped) differs from the harness that would resume: reason `session-ref-foreign-harness`, falling back to a transcript-embedding fresh session — the path that works. `forwardFollowUp` now ALSO summons on the owner/chat routes when the chain tail's last completion is `failed`, no live sitting holds the seat (that case is owned by the live-holder branch, see `20260820-i-chat-live-holder-fix.md`), and no create for the conversation is already queued: it drops the dead mapping and enqueues the ordinary session-create, so a sitting spawns and the reply leg arms for it. The note write stays (persistence); agent-route semantics untouched. RED-first: `probe-chain-resume` arm F and `probe-chat-summon-halted` (new, arms A–F incl. mutation) both reproduced the defects against pre-fix code, green after.

## commit
d491c8f0,91e287ca

## files
ignite/bridges/chat/forward-path.js (forwardFollowUp); ignite/server/ticker/ticker.js (chain resume decision); ignite/bridges/chat/probes/probe-chat-summon-halted.js (new); ignite/server/ticker/probes/probe-chain-resume.js (arm F)

## deployed
yes — rbtv HEAD ac1c08d8, deployed 2026-08-21 18:14:37Z; no ignite JS commits land after it.

## pin
bridges/chat/probes/probe-chat-summon-halted.js;server/ticker/probes/probe-chain-resume.js arm F

## ATTENTION
- A resumed seat's `session_ref` must be checked against the CURRENT resume harness before use — a cross-harness handoff (e.g. opencode → claude) that skips this check reproduces the crash silently (fallback masks it as a normal reply).
- The `failed`-tail summon only fires when no live sitting holds the seat and no create is already queued — widening or narrowing those two guards changes double-spawn risk; re-run `probe-chat-summon-halted` arms A–F after any touch to `forwardFollowUp`.
