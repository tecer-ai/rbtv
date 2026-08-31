# 20260831-c-pause-resume-grows-an-optional — pause-resume grows an optional seat — lane-scoped re-arm

kind: change
component: gateway
date: 2026-08-31
commit: 45b74a04
deployed: no
pin: ignite/runtime/internal-api/probes/probe-pause-resume.js
components: runtime,state-store,supervisor

## Motivation
`d-recovery-retry-scope` (owner ruling 2026-08-31, `redesign-continue-1/decisions.md`): the
recovery reply `retry-with-change` needs to re-arm ONE stuck `(goal, seat)` lane, never the whole
goal. Measured against the tree: `pauseResume` (`state-store/heart/pause-resume.js`) took a `goal`
and nothing else; `applyResume` swept every seat via `seatsOf(goalDir, log)`; `rearmScope`
(`supervisor/exhaustion.js`) filtered the attempt-counter ledger by `{goal}` alone. But the store
primitives underneath — `getCurrentEnding({goal, seat})`, `fireNamedEvent({goal, seat, ...})` — were
already seat-addressable, and `applyResume`'s own seat loop already called them per-seat. The
missing piece was a door exposing ONE seat as a target, not a new mechanism.

## Design
Widened the existing fifteenth intent (`pause-resume`) with an OPTIONAL `seat` field, rather than
minting a sixteenth intent. Exact precedent: `chat_user` was added to this same intent the same way
at c1e3a864 (`20260830-c-pause-resume-carries-the-slack`) — one optional wire field, shape-checked
at both gateway copies, threaded through as a new `pauseResume` parameter, absent path byte-for-byte
unchanged. Reused rather than duplicated: `BUS_NAME_RE` (parse.js's own comment already calls it "a
goal id AND a seat name, SHAPE ONLY"), `isSafeName` (pause-resume.js's existing third independent
check), and `applyResume`'s existing per-seat loop body (rows 2/3/1) — only what feeds `seats` and
whether ROW 4 runs changed.
`seat` is refused with `verb: 'pause'` (VALIDATION_FAILED, both gateway copies): `applyPause` has no
per-lane effect, and an unusable field is a refusal here, never quiet dead input (the thirteenth
intent's own `comments`-refusal precedent, reused verbatim for this field).
Lane-scoped resume skips ROW 4 (the goal pause/resume word) entirely rather than flipping it
alongside the lane: the DoD's own wording is "re-arms ONLY that lane", and the goal word is the
GOAL's row, not any one lane's — flipping it would resume every OTHER lane's launch eligibility too,
which is the exact defect this ruling exists to end.
Rejected: building a parallel resume engine beside this one (`no-duplicate.md`) — the store
primitives were already seat-addressable, so a new mechanism would have been a second implementation
of a capability that already existed everywhere except the parameter list.

## How it works
`gateway/parse.js#parsePauseResume` and `internal-api/dispatch.js#handlePauseResume` both admit
`seat` as an optional key (same `BUS_NAME_RE` shape check as `goal`), and both refuse it when
`verb !== 'resume'`. `dispatch.js` threads `payload.seat` into `pauseResume({...})` and echoes
`out.seat` back in the result only when present (`...(out.seat !== undefined ? {seat: out.seat} : {})`
— the goal-only response shape is untouched). `authz.canPauseResume` is UNCHANGED: it authorizes on
`sender.kind === 'bridge'` alone and never reads `seat`, exactly as it never read `chat_user`.
`pause-resume.js#pauseResume` gained `seat = undefined`, checked a third time with `isSafeName`
(same reason `goal` is: both become path segments / ledger keys downstream), and threads it into
`applyResume({..., seat})`. `applyResume` computes
`seats = targetSeat !== undefined ? [targetSeat] : seatsOf(goalDir, log)` — a named target skips the
taskforce-roster read entirely, so a stale or unreadable `taskforce.csv` cannot stand between the
owner and the one seat they named. ROW 4 (the goal word) is gated on `targetSeat === undefined`.
`rearmCounterRows` gained a `seat` argument forwarded straight to `rearmScope({store, goal, seat,
event})`. `exhaustion.js#rearmScope` gained `seat = null` and an `inScope` filter
(`seat === null || row.seat === seat`) applied to both the `before` and `after` `listCounters` reads
— `row.seat` is the same field `attempt-counters.js#countAttempt` already stamps on every counter
row, so no second parse of `<goal>/<seat>` was needed. `seat === null` (the default) makes the
filter a no-op, so the wide-event callers (`code-deploy`, `config-change`) and the existing
goal-wide `resume` path are unaffected — proven by `probe-code-deploy-rearm` staying 21/21.

## Consequences
Nothing deleted. `probe-pause-resume.js`'s two mutation-anchored red-proofs (R0d/R4 on the
`pauseResume` signature, R0e/R5 on the hoisted `seats` enumeration) had their anchor strings widened
in the same change, following the c1e3a864 precedent exactly — an anchor pinned to a stale signature
stops proving the defect it exists for, silently.
Relaunch is NOT triggered by this act — only unblocked. `reconcile.js`'s per-target dispatch loop
(`counterDisarmed()`, `reconcile.js:644-651`, reading `counters.peekCounter` — the SAME ledger row
`rearmScope` clears) is what decides, on its OWN next pass over the goal's taskforce, whether a lane
falls through to `launchSitting(...)` (the actual relaunch, `reconcile.js` ~1183) or stays on the
`skip-disarmed` branch. This act clears the counter row and arms the ending
(`fireNamedEvent`) so that the NEXT reconcile pass's `counterDisarmed()` returns `false` for that
seat — identical to how the pre-existing goal-wide resume already worked (ATTENTION-4 of
`20260827-c-the-four-named-re-arm-events-g`: "the mechanical resume gains nothing in production" by
itself, wiring only unblocks). Lane-scoping changes WHICH seat gets unblocked, not the unblock/
relaunch split.

## Verification
`runtime/internal-api/probes/probe-pause-resume.js`: 67/67 (was 59/59; +8 arms, section (i)). RED
proven first: source (`parse.js`, `dispatch.js`, `pause-resume.js`, `exhaustion.js`) reverted via
`git stash push -- <4 paths>` with the probe's new arms and widened anchors left in place — 59/67,
EXIT=1. Arm i3 is the defect itself: targeting `lane-a` on a 2-seat goal where BOTH seats are
counter-exhausted the identical way left `lane-b`'s ending `armed:1` (should stay 0) and its counter
row gone (should stay at N) — a resume "targeting" one lane silently re-armed both. i1/i5/i6/i7 red
too (no `seat` echoed back; the field refused as unknown at both gateway copies instead of on the
verb-coupling rule). Restored via `git stash pop`; re-run 67/67, EXIT=0.
`chat/probes/probe-chat-pause-resume.js` 24/24 EXIT=0 (unchanged — the bridge forwards `verb`/`goal`
only, no `seat` port on this side yet; `rr-port-wire`'s to wire).
`runtime/internal-api/probes/probe-intent-drift.js` PASS, all three copies still at 15 — a field
widened, not a new intent, so the lockstep is unaffected by construction.
`runtime/probes/probe-code-deploy-rearm.js` 21/21 EXIT=0 — the wide-event (`code-deploy`) path
through `rearmScope` is provably untouched by the new `seat` filter (default `null` = no-op).
Not deployed at filing (`ignite/chat/` is pinned to the deploy worktree, R10; this seat does not
deploy).

## ATTENTION
1. `authz.canPauseResume` NEVER READS `seat`, same as it never reads `chat_user` — it authorizes on
   the bridge's bearer-token identity alone. A future change that lets `seat` (or any payload field)
   influence that decision reopens the hole D-4(a) closed for `chat_user`.
2. LANE-SCOPED RESUME SKIPS THE GOAL WORD ENTIRELY. `ROW 4` (`paused`→`running`) only runs when
   `seat` is absent. A caller expecting a lane-scoped resume to also un-pause a paused GOAL will be
   surprised — that is deliberate ("re-arms ONLY that lane"), not an oversight.
3. THIS ACT UNBLOCKS, IT DOES NOT RELAUNCH. The targeted seat is only actually re-spawned on
   `reconcile.js`'s own next pass over the goal's taskforce (`counterDisarmed()` → `launchSitting`).
   A caller (`rr-port-wire`) reading `applied:true` as "the seat is running again" is reading it
   wrong — it means "the block affecting a launch attempt of that seat is now gone".
4. `pause-resume.js` VALIDATES `seat` A THIRD TIME (`isSafeName`) EVEN THOUGH BOTH GATEWAY COPIES
   ALREADY DID. This is the SAME defense-in-depth reason `goal` is checked three times: `seat`
   becomes a directory-scan/ledger key downstream (`getCurrentEnding`, the counter subject), and
   gateway origin is not trust (DEC-3).
5. THE PROBE'S TWO MUTATION ANCHORS (SIG, HOIST) MOVE WITH THE SIGNATURE. Any future parameter added
   to `pauseResume`, or any future rewrite of the `seats =` line, MUST update these two literal
   strings in `probe-pause-resume.js` in the SAME change or R0d/R0e silently stop proving anything —
   this is now the second time this has happened (first at c1e3a864).
- authz.canPauseResume never reads seat — same rule as chat_user, keep it that way
- lane-scoped resume skips the goal word entirely — ROW 4 only runs when seat is absent
- this act unblocks, it does not relaunch — reconcile.js's next pass performs the actual launchSitting
