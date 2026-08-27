# 20260827-c-the-four-named-re-arm-events-g — the four named re-arm events get their first producers

kind: creation
component: supervisor
date: 2026-08-27
commit: 5aa80168
deployed: no
pin: ignite/runtime/probes/probe-code-deploy-rearm.js
components: runtime,chat

## Motivation
`spec-recovery` §5 closes the re-arm list at four named events — code deploy, config change,
owner/leader act, mechanical `resume {goal}` — and says a counter "resets ONLY on a named re-arm
event". Not one of the four had a PRODUCER. `counters.rearm` had exactly one caller
(`exhaustion.js#consumeDisarmed`), and that caller had zero. So a driver that reached N was
disarmed FOREVER: `reconcile.js#counterDisarmed` skipped its lane on every pass, through every
restart and through every deploy of the very code whose refusals it had counted. Seven live lanes
were in that state on 2026-08-27 across three goals, including `scratch-tool-reach-note`'s leader,
whose planning chain the acceptance wave was waiting on. 348ebf7e had just made the disarm audible;
nothing could undo it.

## Design
One scope function, two producers.

`supervisor/exhaustion.js#rearmScope({store, goal, event})` answers "this named event happened,
re-arm what it owns" and RETURNS the rows it cleared, so the caller can say what it did. Scope is
the EVENT's, never the caller's preference — the rule `counters.rearm` already carries: `code-deploy`
and `config-change` change the world for every driver and clear everything; `resume` and
`owner-leader-act` are about a lane. It calls `consumeDisarmed` per subject so the ending half
(`fireNamedEvent`) and the counter half (`counters.rearm`) stay ONE act. `store` became optional
there because nothing in the deployed tree sets `engine.endingStore`: a disarmed lane on this
instance exists ONLY as a counter row, and demanding a store would have kept the half the reconcile
loop actually reads unreachable for as long as the ending store stays unwired.
`attempt-counters.js` gained `listCounters` (read-only, no key rule touched) — the rows must be read
BEFORE `rearm` deletes them or the journal can only report intent.

Rejected for the resume half: a direct `require('../supervisor/exhaustion')` from
`chat/pause-resume.js`. The bridge is a separate PROCESS and holds no sibling reach — the wall
`probe-chat-boundary.js` enforces and that entry `20260824-i-open-asks-has-no-boundary-lega`
records a whole migration being reverted over. The counter half therefore arrives as an injected
`rearmCounters` port, exactly as the ending store does, and is consequently NOT WIRED in production.

Rejected for the boot half: comparing the marker's published `code` digest. That capture is rooted
at `ignite/runtime`, so a deploy touching only `supervisor/` leaves it byte-identical and the
re-arm would never fire for the commits most likely to need it — a detector that cannot fire over
the case it exists for. A second WIDE capture over the whole `ignite/` closure is taken instead and
stored on the same marker as `deploy` (digest and count only; the entry map would be ten times the
marker's size).

## How it works
At boot, `runtime/index.js` captures the wide fingerprint and calls
`runtime/code-deploy-rearm.js#rearmOnCodeDeploy` BEFORE `writeCodeMarker` — reading the marker after
the write would compare the boot against itself and never fire. A differing digest fires
`rearmScope({event:'code-deploy'})`, journals one `info` per cleared row
(`re-armed by code-deploy: <subject> <class> (was N=…)`) plus one summary line carrying both digests,
and the new digest is recorded by the marker's own existing write — no second ledger. Same digest =
a restart, which re-arms nothing and says nothing. A null fingerprint is UNKNOWN, never "changed".
No recorded digest at all fires it (a deploy happened by definition) and says `first_boot`.

`chat/pause-resume.js#applyResume` runs the counter half FIRST and runs it with or without a store,
pushing one `row: 'counter'` action per cleared row into the answer it posts; the ending-store seat
loop is unchanged and still owns `fireNamedEvent`, so the two halves never both report one act.

## Consequences
Nothing was replaced. `config-change` is deliberately left WITHOUT a producer: there is no
config-reload path to hook — `loadRecoveryConfig` is re-read at each use, with no watcher, no SIGHUP
and no cache to invalidate, so no moment IS the change; `seedRecoveryConfig` seeds on a miss and
would fire on a first boot rather than on an owner edit. `owner-leader-act` is out of scope.
The mechanical `resume` gains nothing in production: `chat/index.js#main()` wires no ports at all
(no `endingStore`, no `listSeats`, no `approvalPorts`), so the door still applies nothing there.
The seven disarmed lanes are unstuck by the BOOT event only.

## Verification
`runtime/probes/probe-code-deploy-rearm.js`, new, 13/13 EXIT=0: a deploy clears all four seeded rows
with one `info` each carrying the count; a restart clears nothing and journals nothing; a first boot
fires and says `first_boot`; a null digest is UNKNOWN and leaves all four rows; an unwritable ledger
returns `rearm-failed` instead of throwing out of the boot path; and a static arm asserts
`index.js` CALLS it, before the marker write. Three red mutations, each run and reverted: removing
the digest compare reddens the three restart arms; making it never fire reddens eight arms; deleting
the call from `index.js` reddens the wiring arm.
`chat/probes/probe-chat-pause-resume.js` 19/19 (was 12): every counter row of every lane of the goal
cleared, another goal's row untouched, the ending half still firing, each cleared row reported in
the posted text, and the no-store path still performing the counter half. Red mutation: stubbing
`rearmScope`'s row list reddens three of them, green again on restore.
Supervisor selftests 12/13. Reds carried, each reproduced on a pristine `git archive HEAD` tree:
`reconcile.selftest.js:392` and `probe-reconcile` (one assertion, BOOT-PROMPT-BODY),
`probe-daemon-lane-watch` L9 M9, `probe-engine-library` C1 ×2, `probe-chat-boundary` (bus-answer.js's
`child_process`), `probe-daemon-code-fingerprint` 29/30. tmux session list byte-identical.
NOT DEPLOYED at filing.

## ATTENTION
1. A RESTART IS NOT A DEPLOY, and the compare is the only thing holding that line. Re-arming on every boot would restore the unbounded retry the attempt counter replaced, because restarting is the owner's own remedy for a stuck daemon.
2. THE MARKER CARRIES TWO DIGESTS AND THEY ANSWER DIFFERENT QUESTIONS. `code` is "which bytes is this daemon RUNNING", rooted at `ignite/runtime` and re-hashed file-by-file by the watchdog; `deploy` is "was anything in this daemon's code deployed since the last boot". Using `code` for the re-arm silently excludes every supervisor-only commit.
3. THE FIRST BOOT AFTER A DEPLOY RE-ARMS EVERY LANE ON THE INSTANCE, not just the one that was being fixed. Before advancing the deploy, read `supervisor/attempt-counters.json` and know which leaders will wake — each is a real, paid sitting.
4. THE RESUME HALF IS BUILT AND UNREACHABLE. The port exists and is proven, but `chat/index.js#main()` wires nothing, and wiring it needs a gateway intent — an owner-ruled act, not an implementation detail (`20260824-i-open-asks-has-no-boundary-lega`). Do not read the probe's green as "resume works in production".
5. `rearm` WITH A WIDE EVENT CLEARS EVERY ROW, disarmed or not — that is the module's own ruled scope, not an oversight of this pass. A caller wanting only the rows at N must filter on `attempt_counter_n` itself, and `recovery-config.js` is the only place that N lives.
- A restart is not a deploy: the digest compare is what keeps the counter from becoming an unbounded retry again
