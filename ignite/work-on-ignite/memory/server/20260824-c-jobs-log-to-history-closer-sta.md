# 20260824-c-jobs-log-to-history-closer-sta — jobs_log to history; closer stamps failed:crash

kind: change
component: server
date: 2026-08-24
commit: acd780e3
deployed: no
pin: server/heart/probes/probe-seam-closed-set.js
components: engine,bridges,cli,gateway,team-kit

## Motivation
`jobs_log.status` (`launching running done blocked failed stalled killed`) was one of four independent
machines answering "what is the state of this seat", and the ONE the daemon's own code kept asking for
LIVENESS. A process that dies unobserved leaves its row reading `running` until some sweep gets to it,
so every reader that took the column at its word reported a dead seat as working. [T4-R8] settles the
column as HISTORY: an audit/turn log of what a fired execution last recorded about itself, writable on
`jobs_log` and nowhere else, and never a scheduling input.

## Design
No column was dropped and no read was deleted — the change is that every reader now STATES which
question it is asking and of which surface, and the two questions the column may no longer answer are
routed by name: MEASURED liveness to the supervisor registry, the WORK ending to `seat_endings` in the
ending store, and wait/launchability to the derived predicates of `spec-state-store` §2. The
alternative — deleting the column and re-homing the turn audit — was rejected: the process layer
genuinely needs a turn log, and the defect was never the record, it was readers inferring a live fact
from a stale one.

`ticker.js`'s `liveTurns()` is renamed `openTurnRows()`, because the old NAME was the claim: it
asserted liveness in the identifier, so every call site inherited the wrong reading for free.

## How it works
Each reader carries the contract inline where it reads: `heart-store.js#listExecutionsByStatus` (the
listing API itself), `ticker.js#openTurnRows` and its blocked-slot re-dispatch, `spawn.js#orphanRescan`
(which re-asks `systemdStatus` one line down — the measured fact), `warnings-check.js`,
`server/index.js`'s retention fence (which reads the column the only way it is safe to: as proof the
artifacts are NOT yet settled history, so the conservative direction is the point),
`dispatch.js#handleInspectDaemon`, `cli/commands/inspect.js`, `engine/run-board.js`,
`bridges/chat/chat-bridge.js` (row PRESENCE only) and `reply-leg.js` (`profile` is an audit column like
every other on the row). `ignite/CLAUDE.md`'s terminology section is retitled and carries the
three-question table that names the surface for each.

The same change moves the `attest-exit --force-dead` closer onto the ending store's system stamp:
`spawn.js#closeSeatSessionRow` gains `exitCode` and `logPath`, builds the pointer through
`crashEvidence()` and passes it as a new `--evidence` flag, so the `failed`/`reason_class=crash` row
carries the exit code and transcript-tail path §1.4 requires of a crash. The ticker's sweep reads its
exit marker and the live-session closer passes its end reason; neither can any longer produce a
reason-less `exited`.

## Consequences
`liveTurns` was named by hand in two probe manifests — `probe-seam-closed-set.js`'s level-crossing
table and `probe-consumer-closure.js`'s declared-consumer list — and both went red on the rename; the
closure probe additionally lost the two consumers it reached THROUGH that function, which looked like
two unrelated deletions. Swept in commit 55e5f78c.

`bridges/chat/ask-store.js` was NOT migrated: see the sibling entry.

## Verification
`probe-seam-closed-set` and `probe-consumer-closure` (the two level/closure manifests) PASS;
`probe-hot-path-scan` PASS after being taught that the costly all-status pair now spans `seeding.js`
and `ending-reads.js`; `probe-chat-boundary` PASS; the 60-probe `server/spawn` + `server/ticker` chunk
and the 39-probe `bridges/chat` + `gateway` + `cli` chunk are green but for reds owned elsewhere;
`engine/reconcile.selftest.js`, `state-store/ending-store.selftest.js`, `probe-suite --selftest` and
`probe-self-isolate` all exit 0. Not deployed — worktree branch `ignite/core-redesign`.

## ATTENTION
1. `RBTV_IGNITE_SRC` is set to the LIVE repo in any shell inherited from the ignite service environment. Probes that shell out (`probe-trace-header`, the five `rbtv run` engine probes) then load LIVE code against a WORKTREE store and fail on a schema-version or header mismatch that says nothing about the code under test. Point it at the worktree before believing any red from a probe that spawns.
2. A rename inside a closure still has hand-written callers: probe manifests name sites as STRINGS, so no compiler, no `node --check` and no grep of `require` will find them. Grep the old identifier across `probes/` in the same change.
3. `jobs_log.status` may be READ freely — the rule is about the QUESTION, not the access. Reading it to enumerate rows to re-check is correct; reading it as the answer is the defect. Every new read should say which of the two it is, or the next reader will assume the wrong one.
4. The crash stamp REFUSES an empty evidence pointer. A caller that closes a seat row without passing `exitCode`/`logPath` still writes a row, but one whose pointer names no observed death — which is the state §4.5 exists to prevent.
- RBTV_IGNITE_SRC points at the LIVE repo in service-inherited shells — subprocess probes then test the wrong tree
