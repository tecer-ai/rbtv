# 20260831-c-retrywithchange-write-correcti — retryWithChange — write correction, then re-arm the lane

kind: change
component: chat
date: 2026-08-31
commit: a1f26096
deployed: no
pin: ignite/chat/probes/probe-chat-recovery-dispatch.js
components: supervisor,gateway

## Motivation
`d-recovery-retry-scope` + `d-recovery-correction-lands-in-instructions` (owner ruling
2026-08-31, `redesign-continue-1/decisions.md`, "the two dead recovery replies get seated"):
a Slack `retry-with-change` reply on a stuck lane must (1) write the owner's free text into
the RESTARTED seat's own next boot prompt, marked as an owner correction, and (2) re-arm the
ONE named `(goal, seat)` lane, never the whole goal. Measured against the tree before this
change: `createRecoveryDispatch` (`recovery-thread.js`) dispatched all three recovery outcomes
through injected ports, but `chat-bridge.js`'s construction site only supplied `pauseGoal` and
`postBack` — `retryWithChange` was absent, so `retry-with-change` parsed, settled the ask, and
reported `retry-with-change did not run: no retryWithChange port is wired` every time. Two
sibling seats built the two capabilities this port needed to call: `rr-lane-rearm` widened the
existing `pause-resume` intent with an optional `seat` field (45b74a04), and `rr-correction-carry`
built `writeRetryCorrection` (`ignite/supervisor/retry-correction.js`, bff066ac) as the direct
JS-callable handle for the correction write.

## Design
`retryWithChange` is a direct in-process function, not a second gateway call layered on top of
the two existing acts — it calls `writeRetryCorrection` (a plain filesystem write, no store
handle, so it does not trip `probe-chat-boundary.js`'s forbidden-capability scan) FIRST, then
`forwarder.forward('pause-resume', {verb:'resume', goal, seat})` SECOND. The order is the whole
point, not a style choice: the lane-scoped resume only UNBLOCKS the lane (clears the counter,
arms the ending) — the actual relaunch happens later, on the supervisor's own next reconcile
pass (`reconcile.js#counterDisarmed` → `launchSitting`). If the correction were written after
the re-arm, or not before that later pass fires, a relaunch could read a boot prompt with no
owner correction in it, reproducing the exact silent-discard failure the whole recovery-reply
feature exists to end.

A correction-write failure REFUSES THE WHOLE CALL rather than re-arming the lane anyway. This
mirrors `dropLane`'s own two-step "must not half-complete" design (`d-recovery-drop-stops-live-work`):
re-arming without the correction landing would silently ship the owner's `retry-with-change` as
a plain retry, which is the half-built feature the port exists to avoid. Empty/absent/whitespace
`comments` is NOT treated as a failure — `writeRetryCorrection`'s own no-op contract (nothing
written, `{ok:true, written:false}`) is honored, and the re-arm still fires; most `retry-with-change`
replies carry no free text, and that path must behave exactly like a bare retry.

`goalFolder` is derived as `path.join(workspaceRoot, '.rbtv', 'goals', String(goalId))` —
the SAME literal pattern already inlined at four other sites in `ignite/chat/` (`ask-thread.js#replyCopyPath`,
`forward-path.js#resolveGoalSeat`, `bus-answer.js#recordBusAnswer`, `bus-ferry.js`'s several
`goalDir` builds). This is a pre-existing duplicated pattern across the component, not one this
change introduced; a fifth inline copy follows the codebase's own established idiom rather than
inventing a new shared helper nobody asked for. Absence of `workspaceRoot` is refused explicitly
(`no-workspace-root-configured`) rather than silently writing to a relative path under cwd —
the same guard `resolveGoalSeat` and `recordBusAnswer` already take.

## How it works
`chat-bridge.js` requires `writeRetryCorrection` from `../supervisor/retry-correction` (a plain
JS module, no `heart-store`/`node:sqlite`/`child_process`/server import — outside every pattern
`probe-chat-boundary.js` forbids) and adds it as the `retryWithChange` key in the
`createRecoveryDispatch({...})` construction call. On a call, it builds `goalFolder`, calls
`writeRetryCorrection({goalFolder, seat: String(seat), comments})`; on failure it returns
`{ok:false, error: 'owner correction was not saved, lane NOT re-armed: ...'}` without ever
calling the gateway. On success (written or no-op) it forwards `pause-resume` with
`{verb:'resume', goal: String(goalId), seat: String(seat)}` and maps the response the same way
`pauseGoal` already does: `{ok:true, result}` or `{ok:false, error: res.error.code || 'unknown'}`.

`recovery-thread.js`'s `retry-with-change` failure arm posts `retry-with-change failed: ${out.error}`
instead of the retired `retry-with-change did not run: ...` wording — the exact same retirement
pattern `dl-teardown-wire` applied to `drop-lane`'s message in the immediately preceding commit
(8c1023af) on this same file. `out.error` already names which half refused (the correction write
or the re-arm); the door only relays it, same as `dropLane`'s arm. The `if (!out.ok)` structure,
logging, and return shape are all unchanged — only the message text and a header comment.

## Consequences
Nothing deleted. The header comment block at the top of `recovery-thread.js` (the `⚑ retryWithChange
IS NOT WIRED...` paragraph) is rewritten to state it IS wired, matching the file's own established
convention of documenting each outcome's wiring state inline (the `dropLane` paragraph beside it
follows the same shape).

`ignite/chat/` remains PINNED to the deploy worktree (R10) — this commit is correct-and-INERT
until a deploy window runs. `d-recovery-staging` (owner ruling) requires stage 1 (`retry-with-change`)
to deploy and run BEFORE stage 2 (`drop-lane`) begins — that ordering was already broken by
scheduling before this seat started: `dl-teardown-wire` (stage 2) landed its own commit (8c1023af,
wiring `dropLane`) on this exact tree WHILE this seat was still reading craft-binding references,
before `retry-with-change` had even been built, let alone deployed. Both capabilities are now on
the branch tip together, pre-deploy — flagged for the orchestrator in the filing seat's own report,
not resolved here (not this seat's call to make).

## Verification
RED-first, isolated with a saved `git diff`/`git apply` round-trip (never a stash, per this plan's
standing hazard) rather than a worktree, since the RED proof needed the EXACT shared-tree source
state: `git checkout -- ignite/chat/chat-bridge.js ignite/chat/recovery-thread.js` reverted to the
pre-fix commit (8c1023af) while the extended probe (with its new G/H/I arms already in place)
stayed; `node ignite/chat/probes/probe-chat-recovery-dispatch.js` → 15/22, EXIT=1, failing exactly
G1–G5, H2, I2 — the seven arms that exercise the new port — with every pre-existing arm (A–F, H1,
I1) still green. `git apply` restored the fix; same command → 22/22, EXIT=0.

`node ignite/chat/probes/probe-chat-boundary.js` → EXIT=1, but the 2 hits are both in
`bus-answer.js` (`child_process`/`execFile`), a file this change never touched — a pre-existing,
already-documented condition (`20260828-c-the-mechanical-door-becomes-a`'s own Verification section
names "the identical 2 standing hits before and after" as what proves a forwarder-based change adds
no forbidden capability). Neither `chat-bridge.js` nor `recovery-thread.js` appears in the hits list.

`node ignite/runtime/internal-api/probes/probe-pause-resume.js` → 67/67, EXIT=0 — proves the
lane-scoped act this port calls still exists and answers, unmodified by this change.
`node --test ignite/supervisor/retry-correction.selftest.js` → 7/7 pass — the write half this
port calls, unmodified by this change. `probe-chat-glance-wiring` 27/27, `probe-chat-ask-release`
40/40, `probe-chat-reply-leg` PASS, `probe-esc-replay` PASS (25 checks) — all unrelated recovery/chat
probes green, unchanged. Commit a1f26096 on `ignite/core-daemon`. NOT DEPLOYED (`ignite/chat/` is
pinned to the deploy worktree, R10).

## ATTENTION
1. WRITE THE CORRECTION BEFORE THE RE-ARM, NEVER THE OTHER ORDER. The re-arm only unblocks; the
   supervisor's own next reconcile pass performs the actual relaunch and reads the correction file
   at that time, which can be arbitrarily soon after the re-arm returns. Reversing the two calls
   reopens the exact race `d-recovery-correction-lands-in-instructions` was ruled to close.
2. A CORRECTION-WRITE FAILURE MUST REFUSE THE WHOLE retryWithChange CALL. Falling through to the
   re-arm anyway on a write failure would silently turn `retry-with-change <text>` into a plain
   retry with the owner's text dropped on the floor — the exact half-built-feature failure mode
   this port exists to prevent, mirroring `dropLane`'s own two-step all-or-nothing shape.
3. THE CORRECTION PAYLOAD NEVER AUTO-CLEARS (inherited from `rr-correction-carry`'s own ATTENTION-2,
   now reachable in production for the first time through this port). A seat relaunched again later
   for an UNRELATED reason will still see the same stale owner correction folded into its boot
   prompt. Deliberately not diverged from the pre-existing `route-payloads` precedent, which has the
   same behavior; not fixed here.
4. `d-recovery-staging`'S DEPLOY-ORDERING WAS ALREADY BROKEN BY SCHEDULING BEFORE THIS COMMIT, NOT
   BY IT. `dropLane` (stage 2) landed on this same tree (8c1023af) before `retryWithChange` (stage 1)
   did. Whoever opens the next deploy window is shipping both stages together regardless of what
   happens here — this is a fact about the branch tip's history, not something a later edit to this
   port can undo.
5. THE "did not run" WORDING FOR `retry-with-change` IS GONE FOR GOOD — recovering it would be a
   regression to the honest-wiring-gap message for a port that is now actually wired and can
   actually refuse; a wired port whose refusals render the pre-wiring text lies about why it failed.
- Write the correction BEFORE the re-arm, never the other order — the supervisor's next reconcile pass can relaunch arbitrarily soon after the re-arm returns
- A correction-write failure must refuse the whole retryWithChange call, never re-arm anyway
- d-recovery-staging's deploy ordering (stage 1 before stage 2) was already broken by scheduling before this commit landed — flagged for the orchestrator, not fixed here
