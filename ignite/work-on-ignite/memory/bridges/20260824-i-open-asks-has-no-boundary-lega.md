# 20260824-i-open-asks-has-no-boundary-lega — open_asks has no boundary-legal writer from the bridge

kind: issue
component: bridges
date: 2026-08-24
commit: 16fdc15f
deployed: no
pin: bridges/chat/probes/probe-chat-boundary.js
components: team-kit,engine,gateway

## Observed
Migrating `bridges/chat/ask-store.js` off its `owner-asks.json` file onto the daemon-owned `open_asks`
table (spec-state-store §3) reddened `probe-chat-boundary` immediately: the rewrite required
`../../server/heart/heart-store`, which the boundary scan forbids by name. Measured 2026-08-24 on
branch `ignite/core-redesign`, one probe, one rule — `sibling reach-out (server/gateway/cli)`.

## Mechanism
The probe is not being fussy about an import path; it is enforcing a process boundary.
`bridges/chat/index.js` states it: the bridge runs as a SEPARATE PROCESS from the daemon and reaches it
ONLY over the gateway HTTP API as an authenticated sender. The scan therefore forbids a store handle
(`openHeartStore|heart-store`), a child process (`child_process|spawn|execFile|execSync`), an inbound
listener, a sibling require and a raw store write — every mechanism by which that subtree could reach
the daemon's state directly. `open_asks` lives inside the daemon's `heart.db`, so ANY write of it from
the bridge process is a second writer process into that file, which spec §7's "one writer path per row"
forbids for exactly the reason the wall exists. The two rules agree; the spec row simply has no
boundary-legal implementation today.

## Attempts
First attempt held on the diagnosis — checked: `bridges/chat/index.js`'s process header,
`probe-chat-boundary.js`'s six rules, `spec-state-store` §3 and §7, and the precedent of the twelfth
gateway intent `record-bus-answer` (which is how the bridge already asks the daemon to write a file it
may not touch: it validates, the daemon acts, `engine/bus-answer.js` shells to coord). Three shapes were
weighed: (a) a thirteenth gateway intent plus a daemon-side writer; (b) leaving the file and surfacing;
(c) keeping the direct store access. (c) was rejected outright — it breaks a ruled wall AND creates the
dual writer the redesign exists to end. (a) is the correct end state but a new gateway intent is an
owner-ruled act: the twelfth cites ruling 2026-08-11 by name, and inventing a thirteenth unasked would
be a design decision taken inside an implementation seat.

## Fix
Reverted whole — `ask-store.js` and the two Python readers that had followed it onto the store
(`unanswered_ask_block`'s boot-prompt re-inject and `owed-answers.py`'s digest arm) are back on the
file. What was KEPT is the blocker itself, written at both call sites (`chat-bridge.js#deliverToOwner`
and `forward-path.js#onChatMessage`), so the next reader who greps `owner-asks.json` finds the wall
rather than an unexplained gap. Also kept from the attempt: `ending_store.py` now coerces
`evidence_pointer` and `diagnostic` to text at the one door that already coerced `declared_outputs` — a
`Path` evidence pointer (which `attest-exit` legitimately holds, straight off `export_transcript`) was
aborting the whole kit selftest with `TypeError: Object of type PosixPath is not JSON serializable`
after 133 checks.

## Consequences
`owner-asks.json` survives DoD 2's kill-list grep in three files, deliberately and disclosed. The
`open_asks` table remains written by nobody, so §2.1's derived `waiting-on-owner` predicate — which
`engine/ending-reads.js#recordView` already reads — is permanently false while `team-kit/ready.py`'s
`HELD` verdict still keys on bus `held-asks`. That divergence is what reddens
`engine/probes/probe-owner-ask-hold.js` (`verdicts {"alpha":"HELD"} · blockedOnOwner []`): one fact,
two sources. It closes when the ask record does.

## Verification
`probe-chat-boundary` PASS after the revert (it FAILED on the migrated shape — a real red arm, not an
assumed one). `owed-answers.py --selfcheck` exits 0 on the restored reader. The 39-probe
`bridges/chat` + `gateway` + `cli` chunk is green. Not deployed — worktree branch.

## ATTENTION
1. The bridge subtree may hold NO store handle, NO child process and NO sibling require — it is a separate process. Any spec row that asks it to write daemon state needs a gateway intent first; there is no shortcut that `probe-chat-boundary` will not catch.
2. A new gateway intent is owner-ruled, not an implementation detail. The twelfth cites its ruling by name in `gateway/parse.js`. Adding a thirteenth to satisfy a spec row is a design act, not a migration.
3. `ending_store.py` is the ONE kit door onto the store and it is where type coercion belongs. It coerced `declared_outputs` but not `evidence_pointer`, and the partial coercion read as complete — which is worse than none, because the door LOOKS like it normalizes.
4. `engine/probes/probe-owner-ask-hold.js` is red for this reason and not for an engine bug. Do not chase it inside `seeding.js` or `ending-reads.js`: both already read §2.1 correctly.
- The bridge is a separate process: no store handle, no child process, no sibling require — a spec row asking it to write daemon state needs a gateway intent, which is owner-ruled

2026-08-31 addendum: superseded on the store location — since 361a56f2, openAsk/reapAsk/listOpenAsks resolve the workspace ending store (`<workspace>/.rbtv/runtime/ignite/heart.db`); the lane-store `open_asks` copy was drained (rows copied over, table emptied) on 2026-08-31. Read the store location from `ask-record.js`, not from this note.
